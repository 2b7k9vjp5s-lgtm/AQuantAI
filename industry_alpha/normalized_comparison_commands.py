"""Transactional historical and peer valuation-comparison commands."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price_models import ListedInstrumentRevision
from industry_alpha.normalized_financial_rules import NormalizedMetricError
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
    NormalizedValuationMetricRevision,
    ValuationComparisonMember,
    ValuationComparisonSet,
    ValuationComparisonSetRevision,
)
from industry_alpha.normalized_valuation_rules import (
    NORMALIZED_COMPARISON_RULE_VERSION,
    NORMALIZED_VALUATION_RULE_VERSION,
    CALCULATED_STATES,
    ComparisonMember,
    calculate_historical_context,
    calculate_peer_context,
)
from industry_alpha.stage2_models import Stage2CompanyResearchRevision


HISTORICAL_PURPOSE = "normalized_valuation_historical_context_v1"
PEER_PURPOSE = "normalized_valuation_peer_context_v1"

COMPARISON_FIELDS = {
    "comparison_key",
    "comparison_kind",
    "subject_company_research_id",
    "subject_instrument_id",
    "metric_code",
    "target_period_key",
    "period_basis",
    "accounting_scope",
    "formula_version",
    "purpose_code",
    "rule_version",
    "rationale",
    "subject_metric_revision_id",
    "information_cutoff_date",
    "recorded_at_utc",
    "recorded_by",
    "expected_latest_revision_id",
    "members",
}
COMPARISON_REQUIRED = COMPARISON_FIELDS - {"expected_latest_revision_id"}
MEMBER_FIELDS = {
    "member_key",
    "company_research_revision_id",
    "instrument_revision_id",
    "metric_revision_id",
    "is_subject",
    "missing_reason_codes",
}
MEMBER_REQUIRED = MEMBER_FIELDS - {"company_research_revision_id", "metric_revision_id"}


def parse_comparison_command(raw: dict[str, Any]) -> dict[str, Any]:
    require_keys(raw, COMPARISON_FIELDS, COMPARISON_REQUIRED)
    comparison_kind = bounded_text(raw["comparison_kind"], "comparison_kind", 16)
    if comparison_kind not in {"historical", "peer"}:
        raise NormalizedMetricError(
            "normalized_comparison_input_invalid", "unsupported comparison_kind"
        )
    formula_version = bounded_text(raw["formula_version"], "formula_version", 96)
    rule_version = bounded_text(raw["rule_version"], "rule_version", 96)
    purpose_code = bounded_text(raw["purpose_code"], "purpose_code", 80)
    expected_purpose = HISTORICAL_PURPOSE if comparison_kind == "historical" else PEER_PURPOSE
    if formula_version != NORMALIZED_VALUATION_RULE_VERSION:
        raise NormalizedMetricError(
            "normalized_comparison_input_invalid", "unsupported formula_version"
        )
    if rule_version != NORMALIZED_COMPARISON_RULE_VERSION or purpose_code != expected_purpose:
        raise NormalizedMetricError(
            "normalized_comparison_input_invalid", "unsupported comparison rule or purpose"
        )
    raw_members = raw["members"]
    if not isinstance(raw_members, list) or not raw_members:
        raise NormalizedMetricError(
            "normalized_comparison_input_invalid", "members must be a non-empty explicit list"
        )
    members: list[dict[str, Any]] = []
    for position, item in enumerate(raw_members):
        require_keys(item, MEMBER_FIELDS, MEMBER_REQUIRED)
        if not isinstance(item["is_subject"], bool):
            raise NormalizedMetricError(
                "normalized_comparison_input_invalid", "is_subject must be boolean"
            )
        raw_reasons = item["missing_reason_codes"]
        if not isinstance(raw_reasons, list) or any(
            not isinstance(reason, str) or not reason.strip() or len(reason.strip()) > 80
            for reason in raw_reasons
        ):
            raise NormalizedMetricError(
                "normalized_comparison_input_invalid",
                "missing_reason_codes must be bounded explicit strings",
            )
        reasons = tuple(sorted(set(reason.strip() for reason in raw_reasons)))
        metric_revision_id = parse_uuid(
            item.get("metric_revision_id"), "metric_revision_id", optional=True
        )
        if metric_revision_id is None and not reasons:
            raise NormalizedMetricError(
                "normalized_comparison_input_invalid",
                "member without metric revision requires missing_reason_codes",
            )
        members.append(
            {
                "position": position,
                "member_key": bounded_text(item["member_key"], "member_key", 160),
                "company_research_revision_id": parse_uuid(
                    item.get("company_research_revision_id"),
                    "company_research_revision_id",
                    optional=True,
                ),
                "instrument_revision_id": parse_uuid(
                    item["instrument_revision_id"], "instrument_revision_id"
                ),
                "metric_revision_id": metric_revision_id,
                "is_subject": item["is_subject"],
                "missing_reason_codes": reasons,
            }
        )
    if len({member["member_key"] for member in members}) != len(members):
        raise NormalizedMetricError(
            "normalized_comparison_universe_mismatch", "member keys must be unique"
        )
    if sum(member["is_subject"] for member in members) != 1:
        raise NormalizedMetricError(
            "normalized_comparison_universe_mismatch", "subject must appear exactly once"
        )
    if comparison_kind == "peer" and any(
        member["company_research_revision_id"] is None for member in members
    ):
        raise NormalizedMetricError(
            "normalized_comparison_universe_mismatch",
            "peer members require exact Company Research revisions",
        )
    return {
        "comparison_key": bounded_text(raw["comparison_key"], "comparison_key", 220),
        "comparison_kind": comparison_kind,
        "subject_company_research_id": parse_uuid(
            raw["subject_company_research_id"], "subject_company_research_id"
        ),
        "subject_instrument_id": parse_uuid(
            raw["subject_instrument_id"], "subject_instrument_id"
        ),
        "metric_code": bounded_text(raw["metric_code"], "metric_code", 24),
        "target_period_key": bounded_text(
            raw["target_period_key"], "target_period_key", 128
        ),
        "period_basis": bounded_text(raw["period_basis"], "period_basis", 24),
        "accounting_scope": bounded_text(
            raw["accounting_scope"], "accounting_scope", 40
        ),
        "formula_version": formula_version,
        "purpose_code": purpose_code,
        "rule_version": rule_version,
        "rationale": bounded_text(raw["rationale"], "rationale", 4000),
        "subject_metric_revision_id": parse_uuid(
            raw["subject_metric_revision_id"], "subject_metric_revision_id"
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
        "members": members,
    }


class ValuationComparisonCommandService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_comparison_set(
        self, raw: dict[str, Any], *, dry_run: bool = False
    ) -> dict[str, Any]:
        data = parse_comparison_command(raw)
        return execute_command(
            session_factory=self._session_factory,
            kind="valuation_comparison_set",
            key=data["comparison_key"],
            dry_run=dry_run,
            action=lambda session: self._record(session, data, dry_run),
        )

    def _record(
        self, session: Session, data: dict[str, Any], dry_run: bool
    ) -> dict[str, Any]:
        persisted_members: list[dict[str, Any]] = []
        calculation_members: list[ComparisonMember] = []
        for member in data["members"]:
            instrument_revision = session.get(
                ListedInstrumentRevision, member["instrument_revision_id"]
            )
            if instrument_revision is None:
                raise NormalizedMetricError(
                    "normalized_comparison_universe_mismatch",
                    "exact member instrument revision is missing",
                )
            require_visible(
                instrument_revision,
                data["information_cutoff_date"],
                data["recorded_at_utc"],
            )
            if data["comparison_kind"] == "historical" and (
                instrument_revision.instrument_id != data["subject_instrument_id"]
            ):
                raise NormalizedMetricError(
                    "normalized_comparison_universe_mismatch",
                    "historical members must bind the subject instrument",
                )
            if member["company_research_revision_id"] is not None:
                research_revision = session.get(
                    Stage2CompanyResearchRevision,
                    member["company_research_revision_id"],
                )
                if research_revision is None:
                    raise NormalizedMetricError(
                        "normalized_comparison_universe_mismatch",
                        "exact peer Company Research revision is missing",
                    )
                require_visible(
                    research_revision,
                    data["information_cutoff_date"],
                    data["recorded_at_utc"],
                )

            metric_revision = None
            metric_identity = None
            eligible = False
            value = None
            valuation_date = data["information_cutoff_date"]
            period_end_date = data["information_cutoff_date"]
            reasons = set(member["missing_reason_codes"])
            if member["metric_revision_id"] is not None:
                metric_revision = session.get(
                    NormalizedValuationMetricRevision, member["metric_revision_id"]
                )
                if metric_revision is None:
                    raise NormalizedMetricError(
                        "normalized_comparison_universe_mismatch",
                        "exact normalized metric revision is missing",
                    )
                metric_identity = session.get(
                    NormalizedValuationMetric, metric_revision.metric_id
                )
                if metric_identity is None:
                    raise NormalizedMetricError(
                        "normalized_comparison_universe_mismatch",
                        "normalized metric identity is missing",
                    )
                require_visible(
                    metric_revision,
                    data["information_cutoff_date"],
                    data["recorded_at_utc"],
                )
                compatible = (
                    metric_identity.instrument_id == instrument_revision.instrument_id
                    and metric_identity.metric_code == data["metric_code"]
                    and metric_identity.target_period_key == data["target_period_key"]
                    and metric_identity.period_basis == data["period_basis"]
                    and metric_identity.accounting_scope == data["accounting_scope"]
                    and metric_identity.formula_version == data["formula_version"]
                )
                if not compatible:
                    reasons.add("incompatible_metric_definition")
                elif (
                    metric_revision.calculation_state in CALCULATED_STATES
                    and metric_revision.normalized_value is not None
                ):
                    eligible = True
                    value = metric_revision.normalized_value
                else:
                    reasons.update(metric_revision.reason_codes)
                    reasons.add(metric_revision.calculation_state)
                valuation_date = metric_identity.valuation_as_of_date
                period_end_date = metric_revision.financial_period_end_date

            calculation_members.append(
                ComparisonMember(
                    member_id=member["member_key"],
                    value=value,
                    valuation_date=valuation_date,
                    period_end_date=period_end_date,
                    eligible=eligible,
                    reason_codes=tuple(sorted(reasons)),
                )
            )
            persisted_members.append(
                {
                    **member,
                    "metric_revision": metric_revision,
                    "eligibility_state": "eligible" if eligible else "excluded",
                    "normalized_value": value,
                    "valuation_date": valuation_date if metric_revision is not None else None,
                    "financial_period_end_date": (
                        period_end_date if metric_revision is not None else None
                    ),
                    "reason_codes": tuple(sorted(reasons)),
                }
            )

        subject_member = next(member for member in data["members"] if member["is_subject"])
        if subject_member["metric_revision_id"] != data["subject_metric_revision_id"]:
            raise NormalizedMetricError(
                "normalized_comparison_universe_mismatch",
                "subject member does not bind subject_metric_revision_id",
            )
        subject_key = subject_member["member_key"]
        result = (
            calculate_historical_context(
                subject_member_id=subject_key, members=tuple(calculation_members)
            )
            if data["comparison_kind"] == "historical"
            else calculate_peer_context(
                subject_member_id=subject_key, members=tuple(calculation_members)
            )
        )

        identity = session.scalar(
            select(ValuationComparisonSet)
            .where(ValuationComparisonSet.comparison_key == data["comparison_key"])
            .with_for_update()
        )
        if identity is not None and not (
            identity.comparison_kind == data["comparison_kind"]
            and identity.subject_company_research_id
            == data["subject_company_research_id"]
            and identity.subject_instrument_id == data["subject_instrument_id"]
            and identity.metric_code == data["metric_code"]
            and identity.target_period_key == data["target_period_key"]
            and identity.period_basis == data["period_basis"]
            and identity.accounting_scope == data["accounting_scope"]
            and identity.formula_version == data["formula_version"]
            and identity.purpose_code == data["purpose_code"]
            and identity.rule_version == data["rule_version"]
        ):
            raise NormalizedMetricError(
                "normalized_comparison_identity_mismatch",
                "comparison key is already bound to a different exact identity",
            )
        latest = latest_revision(
            session,
            ValuationComparisonSetRevision,
            ValuationComparisonSetRevision.comparison_set_id,
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
                    ValuationComparisonSet(
                        id=identity_id,
                        comparison_key=data["comparison_key"],
                        comparison_kind=data["comparison_kind"],
                        subject_company_research_id=data[
                            "subject_company_research_id"
                        ],
                        subject_instrument_id=data["subject_instrument_id"],
                        metric_code=data["metric_code"],
                        target_period_key=data["target_period_key"],
                        period_basis=data["period_basis"],
                        accounting_scope=data["accounting_scope"],
                        formula_version=data["formula_version"],
                        purpose_code=data["purpose_code"],
                        rule_version=data["rule_version"],
                        created_at_utc=data["recorded_at_utc"],
                    )
                )
            session.add(
                ValuationComparisonSetRevision(
                    id=revision_id,
                    comparison_set_id=identity_id,
                    revision_no=revision_no,
                    subject_metric_revision_id=data["subject_metric_revision_id"],
                    comparison_state=result.comparison_state,
                    rationale=data["rationale"],
                    total_member_count=result.total_member_count,
                    eligible_member_count=result.eligible_member_count,
                    excluded_member_count=result.excluded_member_count,
                    minimum_value=result.minimum,
                    maximum_value=result.maximum,
                    median_value=result.median,
                    subject_percentile=result.subject_percentile,
                    information_cutoff_date=data["information_cutoff_date"],
                    recorded_at_utc=data["recorded_at_utc"],
                    recorded_by=data["recorded_by"],
                    supersedes_revision_id=None if latest is None else latest.id,
                )
            )
            session.add_all(
                [
                    ValuationComparisonMember(
                        id=uuid4(),
                        comparison_revision_id=revision_id,
                        position=member["position"],
                        member_key=member["member_key"],
                        member_company_research_revision_id=member[
                            "company_research_revision_id"
                        ],
                        member_instrument_revision_id=member[
                            "instrument_revision_id"
                        ],
                        normalized_metric_revision_id=member["metric_revision_id"],
                        eligibility_state=member["eligibility_state"],
                        normalized_value=member["normalized_value"],
                        valuation_date=member["valuation_date"],
                        financial_period_end_date=member[
                            "financial_period_end_date"
                        ],
                        is_subject=member["is_subject"],
                        reason_codes=list(member["reason_codes"]),
                        recorded_at_utc=data["recorded_at_utc"],
                    )
                    for member in persisted_members
                ]
            )
            session.flush()

        return {
            "dry_run": dry_run,
            "rule_version": NORMALIZED_COMPARISON_RULE_VERSION,
            "comparison_set_id": str(identity_id),
            "revision_id": str(revision_id),
            "revision_no": revision_no,
            "comparison_kind": data["comparison_kind"],
            "comparison_state": result.comparison_state,
            "total_member_count": result.total_member_count,
            "eligible_member_count": result.eligible_member_count,
            "excluded_member_count": result.excluded_member_count,
            "minimum_value_text": decimal_text(result.minimum, 4),
            "maximum_value_text": decimal_text(result.maximum, 4),
            "median_value_text": decimal_text(result.median, 4),
            "subject_percentile_text": decimal_text(result.subject_percentile, 2),
        }
