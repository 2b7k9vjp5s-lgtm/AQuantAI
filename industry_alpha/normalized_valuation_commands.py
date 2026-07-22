"""Transactional normalized valuation metric commands."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price_models import (
    CanonicalPrice,
    CanonicalPriceRevision,
    ComparisonEligibilityAssessment,
    ComparisonEligibilityMember,
    ComparisonEligibilityRevision,
    ListedInstrumentRevision,
)
from industry_alpha.normalized_financial_rules import (
    NormalizedMetricError,
    StructuredObservationInput,
)
from industry_alpha.normalized_valuation_command_utils import (
    bounded_text,
    decimal_text,
    execute_command,
    latest_revision,
    parse_date,
    parse_utc,
    parse_uuid,
    require_append_chronology,
    require_expected_latest,
    require_keys,
    require_visible,
)
from industry_alpha.normalized_valuation_models import (
    NormalizedValuationMetric,
    NormalizedValuationMetricInputLink,
    NormalizedValuationMetricRevision,
    StructuredFinancialObservation,
    StructuredFinancialObservationRevision,
)
from industry_alpha.normalized_valuation_rules import (
    NORMALIZED_VALUATION_RULE_VERSION,
    PRICE_PURPOSE_CODE,
    CanonicalPriceInput,
    evaluate_normalized_valuation,
)


VALUATION_FIELDS = {
    "metric_key",
    "instrument_id",
    "instrument_revision_id",
    "metric_code",
    "valuation_as_of_date",
    "target_period_key",
    "period_basis",
    "accounting_scope",
    "formula_version",
    "canonical_price_revision_id",
    "comparison_eligibility_revision_id",
    "diluted_shares_revision_id",
    "denominator_revision_id",
    "net_debt_revision_id",
    "information_cutoff_date",
    "recorded_at_utc",
    "recorded_by",
    "expected_latest_revision_id",
}
VALUATION_REQUIRED = VALUATION_FIELDS - {
    "net_debt_revision_id",
    "expected_latest_revision_id",
}


def parse_valuation_command(raw: dict[str, Any]) -> dict[str, Any]:
    require_keys(raw, VALUATION_FIELDS, VALUATION_REQUIRED)
    formula_version = bounded_text(raw["formula_version"], "formula_version", 96)
    if formula_version != NORMALIZED_VALUATION_RULE_VERSION:
        raise NormalizedMetricError(
            "normalized_valuation_formula_invalid", "unsupported formula_version"
        )
    metric_code = bounded_text(raw["metric_code"], "metric_code", 24)
    net_debt_id = parse_uuid(
        raw.get("net_debt_revision_id"), "net_debt_revision_id", optional=True
    )
    if metric_code == "ev_ebitda" and net_debt_id is None:
        raise NormalizedMetricError(
            "normalized_valuation_input_invalid", "ev_ebitda requires net_debt_revision_id"
        )
    if metric_code != "ev_ebitda" and net_debt_id is not None:
        raise NormalizedMetricError(
            "normalized_valuation_input_invalid",
            "net_debt_revision_id is only valid for ev_ebitda",
        )
    return {
        "metric_key": bounded_text(raw["metric_key"], "metric_key", 220),
        "instrument_id": parse_uuid(raw["instrument_id"], "instrument_id"),
        "instrument_revision_id": parse_uuid(
            raw["instrument_revision_id"], "instrument_revision_id"
        ),
        "metric_code": metric_code,
        "valuation_as_of_date": parse_date(
            raw["valuation_as_of_date"], "valuation_as_of_date"
        ),
        "target_period_key": bounded_text(
            raw["target_period_key"], "target_period_key", 128
        ),
        "period_basis": bounded_text(raw["period_basis"], "period_basis", 24),
        "accounting_scope": bounded_text(
            raw["accounting_scope"], "accounting_scope", 40
        ),
        "formula_version": formula_version,
        "canonical_price_revision_id": parse_uuid(
            raw["canonical_price_revision_id"], "canonical_price_revision_id"
        ),
        "comparison_eligibility_revision_id": parse_uuid(
            raw["comparison_eligibility_revision_id"],
            "comparison_eligibility_revision_id",
        ),
        "diluted_shares_revision_id": parse_uuid(
            raw["diluted_shares_revision_id"], "diluted_shares_revision_id"
        ),
        "denominator_revision_id": parse_uuid(
            raw["denominator_revision_id"], "denominator_revision_id"
        ),
        "net_debt_revision_id": net_debt_id,
        "information_cutoff_date": parse_date(
            raw["information_cutoff_date"], "information_cutoff_date"
        ),
        "recorded_at_utc": parse_utc(raw["recorded_at_utc"], "recorded_at_utc"),
        "recorded_by": bounded_text(raw["recorded_by"], "recorded_by", 100),
        "expected_latest_revision_id": parse_uuid(
            raw.get("expected_latest_revision_id"),
            "expected_latest_revision_id",
            optional=True,
        ),
    }


class NormalizedValuationMetricCommandService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_metric(
        self, raw: dict[str, Any], *, dry_run: bool = False
    ) -> dict[str, Any]:
        data = parse_valuation_command(raw)
        return execute_command(
            session_factory=self._session_factory,
            kind="normalized_valuation_metric",
            key=data["metric_key"],
            dry_run=dry_run,
            action=lambda session: self._record(session, data, dry_run),
        )

    def _record(
        self, session: Session, data: dict[str, Any], dry_run: bool
    ) -> dict[str, Any]:
        instrument_revision = session.get(
            ListedInstrumentRevision, data["instrument_revision_id"]
        )
        if instrument_revision is None or instrument_revision.instrument_id != data["instrument_id"]:
            raise NormalizedMetricError(
                "normalized_valuation_identity_mismatch",
                "instrument revision does not match exact instrument identity",
            )
        require_visible(
            instrument_revision, data["information_cutoff_date"], data["recorded_at_utc"]
        )

        price_input = self._price_graph(session, data)
        shares_revision, shares_identity, shares = self._observation(
            session, data["diluted_shares_revision_id"], data
        )
        denominator_revision, denominator_identity, denominator = self._observation(
            session, data["denominator_revision_id"], data
        )
        debt_revision: StructuredFinancialObservationRevision | None = None
        debt_identity: StructuredFinancialObservation | None = None
        debt: StructuredObservationInput | None = None
        if data["net_debt_revision_id"] is not None:
            debt_revision, debt_identity, debt = self._observation(
                session, data["net_debt_revision_id"], data
            )

        identities = [shares_identity, denominator_identity]
        if debt_identity is not None:
            identities.append(debt_identity)
        if any(identity.instrument_id != data["instrument_id"] for identity in identities):
            raise NormalizedMetricError(
                "normalized_valuation_identity_mismatch",
                "financial observation instrument does not match valuation instrument",
            )
        company_ids = {identity.company_research_id for identity in identities}
        if len(company_ids) != 1:
            raise NormalizedMetricError(
                "normalized_valuation_identity_mismatch",
                "valuation inputs must belong to one exact Company Research identity",
            )

        result = evaluate_normalized_valuation(
            metric_code=data["metric_code"],
            valuation_as_of_date=data["valuation_as_of_date"],
            target_period_key=data["target_period_key"],
            period_basis=data["period_basis"],
            accounting_scope=data["accounting_scope"],
            price=price_input,
            shares=shares,
            denominator=denominator,
            net_debt=debt,
        )

        identity = session.scalar(
            select(NormalizedValuationMetric)
            .where(NormalizedValuationMetric.metric_key == data["metric_key"])
            .with_for_update()
        )
        if identity is not None and not (
            identity.instrument_id == data["instrument_id"]
            and identity.metric_code == data["metric_code"]
            and identity.valuation_as_of_date == data["valuation_as_of_date"]
            and identity.target_period_key == data["target_period_key"]
            and identity.period_basis == data["period_basis"]
            and identity.accounting_scope == data["accounting_scope"]
            and identity.formula_version == data["formula_version"]
        ):
            raise NormalizedMetricError(
                "normalized_valuation_identity_mismatch",
                "metric key is already bound to a different exact identity",
            )

        latest = latest_revision(
            session,
            NormalizedValuationMetricRevision,
            NormalizedValuationMetricRevision.metric_id,
            None if identity is None else identity.id,
        )
        require_expected_latest(data["expected_latest_revision_id"], latest)
        require_append_chronology(
            data["information_cutoff_date"], data["recorded_at_utc"], latest
        )

        identity_id = uuid4() if identity is None else identity.id
        revision_id = uuid4()
        revision_no = 1 if latest is None else latest.revision_no + 1
        output_unit = "percent" if data["metric_code"] == "fcf_yield" else "multiple"
        if not dry_run:
            if identity is None:
                session.add(
                    NormalizedValuationMetric(
                        id=identity_id,
                        metric_key=data["metric_key"],
                        instrument_id=data["instrument_id"],
                        metric_code=data["metric_code"],
                        valuation_as_of_date=data["valuation_as_of_date"],
                        target_period_key=data["target_period_key"],
                        period_basis=data["period_basis"],
                        accounting_scope=data["accounting_scope"],
                        formula_version=data["formula_version"],
                        created_at_utc=data["recorded_at_utc"],
                    )
                )
            session.add(
                NormalizedValuationMetricRevision(
                    id=revision_id,
                    metric_id=identity_id,
                    revision_no=revision_no,
                    instrument_revision_id=data["instrument_revision_id"],
                    calculation_state=result.calculation_state,
                    normalized_value=result.normalized_value,
                    equity_value=result.equity_value,
                    enterprise_value=result.enterprise_value,
                    currency_code=price_input.currency_code,
                    output_unit_code=output_unit,
                    price_trade_date=price_input.trade_date,
                    financial_period_end_date=denominator.period_end_date,
                    reason_codes=list(result.reason_codes),
                    information_cutoff_date=data["information_cutoff_date"],
                    recorded_at_utc=data["recorded_at_utc"],
                    recorded_by=data["recorded_by"],
                    supersedes_revision_id=None if latest is None else latest.id,
                )
            )
            links: list[NormalizedValuationMetricInputLink] = [
                NormalizedValuationMetricInputLink(
                    id=uuid4(),
                    metric_revision_id=revision_id,
                    position=0,
                    input_role="canonical_price",
                    canonical_price_revision_id=data["canonical_price_revision_id"],
                    recorded_at_utc=data["recorded_at_utc"],
                ),
                NormalizedValuationMetricInputLink(
                    id=uuid4(),
                    metric_revision_id=revision_id,
                    position=1,
                    input_role="price_eligibility",
                    comparison_eligibility_revision_id=data[
                        "comparison_eligibility_revision_id"
                    ],
                    recorded_at_utc=data["recorded_at_utc"],
                ),
                NormalizedValuationMetricInputLink(
                    id=uuid4(),
                    metric_revision_id=revision_id,
                    position=2,
                    input_role="diluted_shares",
                    financial_observation_revision_id=shares_revision.id,
                    recorded_at_utc=data["recorded_at_utc"],
                ),
                NormalizedValuationMetricInputLink(
                    id=uuid4(),
                    metric_revision_id=revision_id,
                    position=3,
                    input_role="financial_denominator",
                    financial_observation_revision_id=denominator_revision.id,
                    recorded_at_utc=data["recorded_at_utc"],
                ),
            ]
            if debt_revision is not None:
                links.append(
                    NormalizedValuationMetricInputLink(
                        id=uuid4(),
                        metric_revision_id=revision_id,
                        position=4,
                        input_role="net_debt",
                        financial_observation_revision_id=debt_revision.id,
                        recorded_at_utc=data["recorded_at_utc"],
                    )
                )
            session.add_all(links)
            session.flush()

        return {
            "dry_run": dry_run,
            "formula_version": NORMALIZED_VALUATION_RULE_VERSION,
            "metric_id": str(identity_id),
            "revision_id": str(revision_id),
            "revision_no": revision_no,
            "metric_code": data["metric_code"],
            "calculation_state": result.calculation_state,
            "normalized_value_text": decimal_text(result.normalized_value, 4),
            "equity_value_text": decimal_text(result.equity_value, 6),
            "enterprise_value_text": decimal_text(result.enterprise_value, 6),
            "reason_codes": list(result.reason_codes),
        }

    @staticmethod
    def _observation(
        session: Session, revision_id: UUID, data: dict[str, Any]
    ) -> tuple[
        StructuredFinancialObservationRevision,
        StructuredFinancialObservation,
        StructuredObservationInput,
    ]:
        revision = session.get(StructuredFinancialObservationRevision, revision_id)
        if revision is None:
            raise NormalizedMetricError(
                "normalized_valuation_input_missing", "financial observation revision is missing"
            )
        identity = session.get(StructuredFinancialObservation, revision.observation_id)
        if identity is None:
            raise NormalizedMetricError(
                "normalized_valuation_input_missing", "financial observation identity is missing"
            )
        require_visible(
            revision, data["information_cutoff_date"], data["recorded_at_utc"]
        )
        observation = StructuredObservationInput(
            instrument_id=str(identity.instrument_id),
            company_research_id=str(identity.company_research_id),
            metric_code=identity.metric_code,
            source_kind=identity.source_kind,
            observation_state=revision.observation_state,
            value_text=revision.source_value_text,
            value=revision.value_decimal,
            currency_code=identity.currency_code,
            unit_code=identity.unit_code,
            period_basis=revision.period_basis,
            target_period_key=identity.target_period_key,
            accounting_scope=identity.accounting_scope,
            observation_as_of_date=revision.observation_as_of_date,
            period_start_date=revision.period_start_date,
            period_end_date=revision.period_end_date,
            fiscal_year=revision.fiscal_year,
            effective_start_date=revision.effective_start_date,
            effective_end_date=revision.effective_end_date,
        )
        return revision, identity, observation

    @staticmethod
    def _price_graph(session: Session, data: dict[str, Any]) -> CanonicalPriceInput:
        price_revision = session.get(
            CanonicalPriceRevision, data["canonical_price_revision_id"]
        )
        eligibility = session.get(
            ComparisonEligibilityRevision,
            data["comparison_eligibility_revision_id"],
        )
        if price_revision is None or eligibility is None:
            raise NormalizedMetricError(
                "normalized_valuation_price_missing",
                "exact canonical price or eligibility revision is missing",
            )
        require_visible(
            price_revision, data["information_cutoff_date"], data["recorded_at_utc"]
        )
        require_visible(
            eligibility, data["information_cutoff_date"], data["recorded_at_utc"]
        )
        price_identity = session.get(CanonicalPrice, price_revision.canonical_price_id)
        assessment = session.get(ComparisonEligibilityAssessment, eligibility.assessment_id)
        linked = session.scalar(
            select(ComparisonEligibilityMember.id).where(
                ComparisonEligibilityMember.eligibility_revision_id == eligibility.id,
                ComparisonEligibilityMember.canonical_price_revision_id == price_revision.id,
            )
        )
        if price_identity is None or assessment is None or linked is None:
            raise NormalizedMetricError(
                "normalized_valuation_price_ineligible", "price eligibility graph is incomplete"
            )
        if price_revision.instrument_revision_id != data["instrument_revision_id"]:
            raise NormalizedMetricError(
                "normalized_valuation_identity_mismatch",
                "canonical price does not bind the exact instrument revision",
            )
        return CanonicalPriceInput(
            instrument_id=str(data["instrument_id"]),
            value=price_revision.value_decimal,
            currency_code=price_revision.currency_code,
            unit_code=price_revision.unit_code,
            trade_date=price_revision.trade_date,
            canonical_status=price_revision.canonical_status,
            price_kind=price_identity.price_kind,
            adjustment_basis=price_identity.adjustment_basis,
            eligibility_state=eligibility.state,
            eligibility_purpose=assessment.purpose_code,
        )
