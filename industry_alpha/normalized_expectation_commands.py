"""Transactional normalized expectation-gap commands."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price_models import ListedInstrumentRevision
from industry_alpha.normalized_expectation_rules import (
    NORMALIZED_EXPECTATION_RULE_VERSION,
    calculate_normalized_expectation_gap,
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
    NormalizedExpectationGap,
    NormalizedExpectationGapRevision,
    StructuredFinancialObservation,
    StructuredFinancialObservationRevision,
)
from industry_alpha.stage2_models import Stage2CompanyResearch, Stage2CompanyResearchRevision


EXPECTATION_FIELDS = {
    "gap_key",
    "company_research_id",
    "company_research_revision_id",
    "instrument_id",
    "instrument_revision_id",
    "metric_code",
    "target_period_key",
    "expected_source_kind",
    "rule_version",
    "expected_observation_revision_id",
    "actual_observation_revision_id",
    "calculation_as_of_date",
    "information_cutoff_date",
    "recorded_at_utc",
    "recorded_by",
    "expected_latest_revision_id",
}
EXPECTATION_REQUIRED = EXPECTATION_FIELDS - {"expected_latest_revision_id"}


def parse_expectation_gap_command(raw: dict[str, Any]) -> dict[str, Any]:
    require_keys(raw, EXPECTATION_FIELDS, EXPECTATION_REQUIRED)
    rule_version = bounded_text(raw["rule_version"], "rule_version", 96)
    if rule_version != NORMALIZED_EXPECTATION_RULE_VERSION:
        raise NormalizedMetricError(
            "normalized_expectation_rule_invalid", "unsupported expectation-gap rule"
        )
    expected_source = bounded_text(
        raw["expected_source_kind"], "expected_source_kind", 24
    )
    if expected_source not in {"guidance", "consensus", "research_assumption"}:
        raise NormalizedMetricError(
            "normalized_expectation_input_invalid", "unsupported expected_source_kind"
        )
    return {
        "gap_key": bounded_text(raw["gap_key"], "gap_key", 220),
        "company_research_id": parse_uuid(
            raw["company_research_id"], "company_research_id"
        ),
        "company_research_revision_id": parse_uuid(
            raw["company_research_revision_id"], "company_research_revision_id"
        ),
        "instrument_id": parse_uuid(raw["instrument_id"], "instrument_id"),
        "instrument_revision_id": parse_uuid(
            raw["instrument_revision_id"], "instrument_revision_id"
        ),
        "metric_code": bounded_text(raw["metric_code"], "metric_code", 40),
        "target_period_key": bounded_text(
            raw["target_period_key"], "target_period_key", 128
        ),
        "expected_source_kind": expected_source,
        "rule_version": rule_version,
        "expected_observation_revision_id": parse_uuid(
            raw["expected_observation_revision_id"],
            "expected_observation_revision_id",
        ),
        "actual_observation_revision_id": parse_uuid(
            raw["actual_observation_revision_id"], "actual_observation_revision_id"
        ),
        "calculation_as_of_date": parse_date(
            raw["calculation_as_of_date"], "calculation_as_of_date"
        ),
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


class NormalizedExpectationGapCommandService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_expectation_gap(
        self, raw: dict[str, Any], *, dry_run: bool = False
    ) -> dict[str, Any]:
        data = parse_expectation_gap_command(raw)
        return execute_command(
            session_factory=self._session_factory,
            kind="normalized_expectation_gap",
            key=data["gap_key"],
            dry_run=dry_run,
            action=lambda session: self._record(session, data, dry_run),
        )

    def _record(
        self, session: Session, data: dict[str, Any], dry_run: bool
    ) -> dict[str, Any]:
        research_revision = session.get(
            Stage2CompanyResearchRevision, data["company_research_revision_id"]
        )
        instrument_revision = session.get(
            ListedInstrumentRevision, data["instrument_revision_id"]
        )
        if research_revision is None or instrument_revision is None:
            raise NormalizedMetricError(
                "normalized_expectation_identity_mismatch",
                "exact Company Research or instrument revision is missing",
            )
        research = session.get(Stage2CompanyResearch, research_revision.company_research_id)
        if research is None or research.id != data["company_research_id"]:
            raise NormalizedMetricError(
                "normalized_expectation_identity_mismatch",
                "Company Research revision does not match exact identity",
            )
        if instrument_revision.instrument_id != data["instrument_id"]:
            raise NormalizedMetricError(
                "normalized_expectation_identity_mismatch",
                "instrument revision does not match exact identity",
            )
        require_visible(
            research_revision, data["information_cutoff_date"], data["recorded_at_utc"]
        )
        require_visible(
            instrument_revision, data["information_cutoff_date"], data["recorded_at_utc"]
        )

        expected_revision, expected_identity, expected = self._observation(
            session, data["expected_observation_revision_id"], data
        )
        actual_revision, actual_identity, actual = self._observation(
            session, data["actual_observation_revision_id"], data
        )
        for identity in (expected_identity, actual_identity):
            if (
                identity.company_research_id != data["company_research_id"]
                or identity.instrument_id != data["instrument_id"]
                or identity.metric_code != data["metric_code"]
                or identity.target_period_key != data["target_period_key"]
            ):
                raise NormalizedMetricError(
                    "normalized_expectation_identity_mismatch",
                    "expectation inputs do not match exact gap identity",
                )
        if expected_identity.source_kind != data["expected_source_kind"]:
            raise NormalizedMetricError(
                "normalized_expectation_identity_mismatch",
                "expected observation source does not match gap identity",
            )

        result = calculate_normalized_expectation_gap(
            expected=expected,
            actual=actual,
            calculation_as_of_date=data["calculation_as_of_date"],
        )

        identity = session.scalar(
            select(NormalizedExpectationGap)
            .where(NormalizedExpectationGap.gap_key == data["gap_key"])
            .with_for_update()
        )
        if identity is not None and not (
            identity.company_research_id == data["company_research_id"]
            and identity.instrument_id == data["instrument_id"]
            and identity.metric_code == data["metric_code"]
            and identity.target_period_key == data["target_period_key"]
            and identity.expected_source_kind == data["expected_source_kind"]
            and identity.rule_version == data["rule_version"]
        ):
            raise NormalizedMetricError(
                "normalized_expectation_identity_mismatch",
                "gap key is already bound to a different exact identity",
            )
        latest = latest_revision(
            session,
            NormalizedExpectationGapRevision,
            NormalizedExpectationGapRevision.gap_id,
            None if identity is None else identity.id,
        )
        require_expected_latest(data["expected_latest_revision_id"], latest)
        require_append_chronology(
            data["information_cutoff_date"], data["recorded_at_utc"], latest
        )

        identity_id = uuid4() if identity is None else identity.id
        revision_id = uuid4()
        revision_no = 1 if latest is None else latest.revision_no + 1
        if not dry_run:
            if identity is None:
                session.add(
                    NormalizedExpectationGap(
                        id=identity_id,
                        gap_key=data["gap_key"],
                        company_research_id=data["company_research_id"],
                        instrument_id=data["instrument_id"],
                        metric_code=data["metric_code"],
                        target_period_key=data["target_period_key"],
                        expected_source_kind=data["expected_source_kind"],
                        rule_version=data["rule_version"],
                        created_at_utc=data["recorded_at_utc"],
                    )
                )
            session.add(
                NormalizedExpectationGapRevision(
                    id=revision_id,
                    gap_id=identity_id,
                    revision_no=revision_no,
                    company_research_revision_id=data[
                        "company_research_revision_id"
                    ],
                    instrument_revision_id=data["instrument_revision_id"],
                    expected_observation_revision_id=expected_revision.id,
                    actual_observation_revision_id=actual_revision.id,
                    gap_state=result.gap_state,
                    absolute_gap=result.absolute_gap,
                    percentage_gap=result.percentage_gap,
                    direction=result.direction,
                    reason_codes=list(result.reason_codes),
                    calculation_as_of_date=data["calculation_as_of_date"],
                    information_cutoff_date=data["information_cutoff_date"],
                    recorded_at_utc=data["recorded_at_utc"],
                    recorded_by=data["recorded_by"],
                    supersedes_revision_id=None if latest is None else latest.id,
                )
            )
            session.flush()

        return {
            "dry_run": dry_run,
            "rule_version": NORMALIZED_EXPECTATION_RULE_VERSION,
            "gap_id": str(identity_id),
            "revision_id": str(revision_id),
            "revision_no": revision_no,
            "metric_code": data["metric_code"],
            "gap_state": result.gap_state,
            "absolute_gap_text": decimal_text(result.absolute_gap, 6),
            "percentage_gap_text": decimal_text(result.percentage_gap, 4),
            "direction": result.direction,
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
                "normalized_expectation_input_missing",
                "exact structured observation revision is missing",
            )
        identity = session.get(StructuredFinancialObservation, revision.observation_id)
        if identity is None:
            raise NormalizedMetricError(
                "normalized_expectation_input_missing",
                "structured observation identity is missing",
            )
        require_visible(
            revision, data["information_cutoff_date"], data["recorded_at_utc"]
        )
        return (
            revision,
            identity,
            StructuredObservationInput(
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
            ),
        )
