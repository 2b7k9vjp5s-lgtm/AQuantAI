"""Atomic strict historical and peer comparison command for Slice 5."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price_models import ListedInstrumentRevision
from industry_alpha.normalized_comparison_commands import (
    HISTORICAL_PURPOSE,
    PEER_PURPOSE,
    parse_comparison_command,
)
from industry_alpha.normalized_financial_rules import NormalizedMetricError
from industry_alpha.normalized_valuation_command_utils import (
    decimal_text,
    execute_command,
    latest_revision,
    require_append_chronology,
    require_expected_latest,
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
    CALCULATED_STATES,
    NORMALIZED_COMPARISON_RULE_VERSION,
    ComparisonMember,
    ComparisonResult,
)
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
)

FOUR_PLACES = Decimal("0.0001")
TWO_PLACES = Decimal("0.01")
HUNDRED = Decimal("100")


class StrictValuationComparisonCommandService:
    """Validate and append one complete comparison graph in one transaction."""

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
        subject_member = next(member for member in data["members"] if member["is_subject"])
        if subject_member["metric_revision_id"] != data["subject_metric_revision_id"]:
            raise NormalizedMetricError(
                "normalized_comparison_universe_mismatch",
                "subject member does not bind subject_metric_revision_id",
            )

        subject_revision, subject_identity = self._metric_graph(
            session,
            data["subject_metric_revision_id"],
            data,
        )
        if subject_identity.instrument_id != data["subject_instrument_id"]:
            raise NormalizedMetricError(
                "normalized_comparison_universe_mismatch",
                "subject metric does not bind subject_instrument_id",
            )

        revision_ids = [member["instrument_revision_id"] for member in data["members"]]
        if len(set(revision_ids)) != len(revision_ids) and data["comparison_kind"] == "peer":
            raise NormalizedMetricError(
                "normalized_comparison_universe_mismatch",
                "peer members must use distinct listed-instrument revisions",
            )
        research_revision_ids = [
            member["company_research_revision_id"]
            for member in data["members"]
            if member["company_research_revision_id"] is not None
        ]
        if data["comparison_kind"] == "peer" and len(set(research_revision_ids)) != len(
            research_revision_ids
        ):
            raise NormalizedMetricError(
                "normalized_comparison_universe_mismatch",
                "peer members must use distinct Company Research revisions",
            )

        persisted_members: list[dict[str, Any]] = []
        calculation_members: list[ComparisonMember] = []
        peer_research_ids: list[UUID] = []
        peer_instrument_ids: list[UUID] = []
        subject_research_id: UUID | None = None
        subject_instrument_id: UUID | None = None

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

            research_revision = None
            research = None
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
                research = session.get(
                    Stage2CompanyResearch, research_revision.company_research_id
                )
                if research is None or research.stock_code != instrument_revision.canonical_symbol:
                    raise NormalizedMetricError(
                        "normalized_comparison_universe_mismatch",
                        "peer Company Research stock code does not match the listed instrument",
                    )
                if data["comparison_kind"] == "peer":
                    peer_research_ids.append(research.id)
                    peer_instrument_ids.append(instrument_revision.instrument_id)
                    if member["is_subject"]:
                        subject_research_id = research.id
                        subject_instrument_id = instrument_revision.instrument_id

            metric_revision = None
            metric_identity = None
            eligible = False
            value = None
            valuation_date = data["information_cutoff_date"]
            period_end_date = data["information_cutoff_date"]
            reasons = set(member["missing_reason_codes"])
            if member["metric_revision_id"] is not None:
                metric_revision, metric_identity = self._metric_graph(
                    session, member["metric_revision_id"], data
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
                if metric_revision.currency_code != subject_revision.currency_code:
                    reasons.add("currency_mismatch")
                if metric_revision.output_unit_code != subject_revision.output_unit_code:
                    reasons.add("unit_mismatch")
                if (
                    not reasons
                    and metric_revision.calculation_state in CALCULATED_STATES
                    and metric_revision.normalized_value is not None
                ):
                    eligible = True
                    value = metric_revision.normalized_value
                else:
                    reasons.update(metric_revision.reason_codes)
                    if metric_revision.calculation_state not in CALCULATED_STATES:
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
                    "eligibility_state": "eligible" if eligible else "excluded",
                    "normalized_value": value,
                    "valuation_date": valuation_date if metric_revision is not None else None,
                    "financial_period_end_date": (
                        period_end_date if metric_revision is not None else None
                    ),
                    "reason_codes": tuple(sorted(reasons)),
                }
            )

        if data["comparison_kind"] == "peer":
            if len(set(peer_research_ids)) != len(peer_research_ids):
                raise NormalizedMetricError(
                    "normalized_comparison_universe_mismatch",
                    "peer members must represent distinct Company Research identities",
                )
            if len(set(peer_instrument_ids)) != len(peer_instrument_ids):
                raise NormalizedMetricError(
                    "normalized_comparison_universe_mismatch",
                    "peer members must represent distinct listed instruments",
                )
            if subject_research_id != data["subject_company_research_id"]:
                raise NormalizedMetricError(
                    "normalized_comparison_universe_mismatch",
                    "subject member does not match subject_company_research_id",
                )
            if subject_instrument_id != data["subject_instrument_id"]:
                raise NormalizedMetricError(
                    "normalized_comparison_universe_mismatch",
                    "subject member does not match subject_instrument_id",
                )

        result = self._calculate_context(
            data["comparison_kind"],
            subject_member["member_key"],
            tuple(calculation_members),
        )

        identity = session.scalar(
            select(ValuationComparisonSet)
            .where(ValuationComparisonSet.comparison_key == data["comparison_key"])
            .with_for_update()
        )
        if identity is not None and not (
            identity.comparison_kind == data["comparison_kind"]
            and identity.subject_company_research_id == data["subject_company_research_id"]
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
                        subject_company_research_id=data["subject_company_research_id"],
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
                        member_instrument_revision_id=member["instrument_revision_id"],
                        normalized_metric_revision_id=member["metric_revision_id"],
                        eligibility_state=member["eligibility_state"],
                        normalized_value=member["normalized_value"],
                        valuation_date=member["valuation_date"],
                        financial_period_end_date=member["financial_period_end_date"],
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

    @staticmethod
    def _metric_graph(
        session: Session, revision_id: UUID, data: dict[str, Any]
    ) -> tuple[NormalizedValuationMetricRevision, NormalizedValuationMetric]:
        revision = session.get(NormalizedValuationMetricRevision, revision_id)
        if revision is None:
            raise NormalizedMetricError(
                "normalized_comparison_universe_mismatch",
                "exact normalized metric revision is missing",
            )
        identity = session.get(NormalizedValuationMetric, revision.metric_id)
        if identity is None:
            raise NormalizedMetricError(
                "normalized_comparison_universe_mismatch",
                "normalized metric identity is missing",
            )
        require_visible(
            revision, data["information_cutoff_date"], data["recorded_at_utc"]
        )
        return revision, identity

    @staticmethod
    def _calculate_context(
        comparison_kind: str,
        subject_member_id: str,
        members: tuple[ComparisonMember, ...],
    ) -> ComparisonResult:
        if not members:
            raise NormalizedMetricError(
                "normalized_comparison_members_required", "comparison members are required"
            )
        ids = [member.member_id for member in members]
        if len(set(ids)) != len(ids) or ids.count(subject_member_id) != 1:
            raise NormalizedMetricError(
                "normalized_comparison_universe_mismatch",
                "comparison member keys and subject must be exact",
            )
        eligible = tuple(
            member for member in members if member.eligible and member.value is not None
        )
        subject = next(member for member in members if member.member_id == subject_member_id)
        if comparison_kind == "historical":
            eligible_dates = [member.valuation_date for member in eligible]
            if len(set(eligible_dates)) != len(eligible_dates):
                raise NormalizedMetricError(
                    "normalized_comparison_duplicate_date",
                    "eligible historical valuation dates must be unique",
                )
            span_days = (
                (max(eligible_dates) - min(eligible_dates)).days
                if eligible_dates
                else 0
            )
            sufficient = (
                subject.eligible
                and subject.value is not None
                and len(eligible) >= 8
                and span_days >= 730
                and len({member.period_end_date for member in eligible}) >= 4
            )
            state = "calculated" if sufficient else "insufficient_history"
        else:
            if len({member.valuation_date for member in eligible}) > 1:
                raise NormalizedMetricError(
                    "normalized_comparison_valuation_date_mismatch",
                    "eligible peer members require one common valuation date",
                )
            sufficient = subject.eligible and subject.value is not None and len(eligible) >= 3
            state = "calculated" if sufficient else "insufficient_peer_members"
        if state != "calculated":
            return ComparisonResult(
                comparison_state=state,
                total_member_count=len(members),
                eligible_member_count=len(eligible),
                excluded_member_count=len(members) - len(eligible),
                minimum=None,
                maximum=None,
                median=None,
                subject_percentile=None,
                members=members,
            )
        values = sorted(member.value for member in eligible if member.value is not None)
        assert subject.value is not None
        with localcontext() as context:
            context.prec = 28
            count_less = sum(value < subject.value for value in values)
            count_equal = sum(value == subject.value for value in values)
            percentile = (
                (Decimal(count_less) + Decimal("0.5") * Decimal(count_equal))
                / Decimal(len(values))
                * HUNDRED
            ).quantize(TWO_PLACES, rounding=ROUND_HALF_EVEN)
            middle = len(values) // 2
            median = (
                values[middle]
                if len(values) % 2
                else (values[middle - 1] + values[middle]) / Decimal("2")
            ).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        return ComparisonResult(
            comparison_state="calculated",
            total_member_count=len(members),
            eligible_member_count=len(eligible),
            excluded_member_count=len(members) - len(eligible),
            minimum=values[0].quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN),
            maximum=values[-1].quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN),
            median=median,
            subject_percentile=percentile,
            members=members,
        )


__all__ = ("StrictValuationComparisonCommandService",)
