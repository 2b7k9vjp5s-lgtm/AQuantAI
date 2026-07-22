"""Exact-ID, dual-as-of normalized valuation and expectation reads."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from industry_alpha.normalized_financial_rules import NormalizedMetricError
from industry_alpha.normalized_valuation_models import (
    NormalizedExpectationGap,
    NormalizedExpectationGapRevision,
    NormalizedValuationMetric,
    NormalizedValuationMetricInputLink,
    NormalizedValuationMetricRevision,
    StructuredFinancialObservation,
    StructuredFinancialObservationClaimLink,
    StructuredFinancialObservationEvidenceLink,
    StructuredFinancialObservationRevision,
    ValuationComparisonMember,
    ValuationComparisonSet,
    ValuationComparisonSetRevision,
)


class NormalizedMetricNotFound(NormalizedMetricError):
    """Requested exact revision is absent or outside the requested boundaries."""


def _stored_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _visible(row: Any, cutoff: date, recorded_at: datetime) -> None:
    information = getattr(row, "information_cutoff_date", None)
    recorded = getattr(row, "recorded_at_utc", None)
    if information is not None and information > cutoff:
        raise NormalizedMetricNotFound(
            "normalized_metric_not_visible", "record is outside the information cutoff"
        )
    if recorded is not None and _stored_utc(recorded) > recorded_at:
        raise NormalizedMetricNotFound(
            "normalized_metric_not_visible", "record is outside the recorded-time boundary"
        )


def _decimal(value: Decimal | None, scale: int) -> str | None:
    return None if value is None else format(value, f".{scale}f")


def _uuid(value: UUID | None) -> str | None:
    return None if value is None else str(value)


class NormalizedValuationQueryService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_financial_observation_revision(
        self,
        revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        revision = self._session.get(StructuredFinancialObservationRevision, revision_id)
        if revision is None:
            raise NormalizedMetricNotFound(
                "normalized_financial_observation_not_found",
                "structured financial observation revision was not found",
            )
        _visible(revision, as_of_cutoff, as_of_recorded_at_utc)
        identity = self._session.get(StructuredFinancialObservation, revision.observation_id)
        if identity is None:
            raise NormalizedMetricError(
                "normalized_metric_graph_incomplete", "financial observation graph is incomplete"
            )
        claims = list(
            self._session.scalars(
                select(StructuredFinancialObservationClaimLink)
                .where(
                    StructuredFinancialObservationClaimLink.observation_revision_id
                    == revision.id
                )
                .order_by(StructuredFinancialObservationClaimLink.position)
            )
        )
        evidence = list(
            self._session.scalars(
                select(StructuredFinancialObservationEvidenceLink)
                .where(
                    StructuredFinancialObservationEvidenceLink.observation_revision_id
                    == revision.id
                )
                .order_by(StructuredFinancialObservationEvidenceLink.position)
            )
        )
        return {
            "observation_id": str(identity.id),
            "observation_revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "observation_key": identity.observation_key,
            "company_research_id": str(identity.company_research_id),
            "company_research_revision_id": str(revision.company_research_revision_id),
            "instrument_id": str(identity.instrument_id),
            "instrument_revision_id": str(revision.instrument_revision_id),
            "metric_code": identity.metric_code,
            "source_kind": identity.source_kind,
            "observation_state": revision.observation_state,
            "source_value_text": revision.source_value_text,
            "standardized_value_text": revision.standardized_value_text,
            "currency_code": identity.currency_code,
            "unit_code": identity.unit_code,
            "target_period_key": identity.target_period_key,
            "period_basis": revision.period_basis,
            "accounting_scope": identity.accounting_scope,
            "period_start_date": None
            if revision.period_start_date is None
            else revision.period_start_date.isoformat(),
            "period_end_date": revision.period_end_date.isoformat(),
            "fiscal_year": revision.fiscal_year,
            "observation_as_of_date": revision.observation_as_of_date.isoformat(),
            "effective_start_date": None
            if revision.effective_start_date is None
            else revision.effective_start_date.isoformat(),
            "effective_end_date": None
            if revision.effective_end_date is None
            else revision.effective_end_date.isoformat(),
            "rationale": revision.rationale,
            "falsification_condition": revision.falsification_condition,
            "information_cutoff_date": revision.information_cutoff_date.isoformat(),
            "recorded_at_utc": _stored_utc(revision.recorded_at_utc).isoformat(),
            "recorded_by": revision.recorded_by,
            "supersedes_revision_id": _uuid(revision.supersedes_revision_id),
            "claim_revision_ids": [str(link.claim_revision_id) for link in claims],
            "evidence_links": [
                {
                    "position": link.position,
                    "claim_revision_id": str(link.claim_revision_id),
                    "claim_evidence_link_id": str(link.claim_evidence_link_id),
                    "evidence_id": str(link.evidence_id),
                }
                for link in evidence
            ],
        }

    def get_metric_revision(
        self,
        revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        revision = self._session.get(NormalizedValuationMetricRevision, revision_id)
        if revision is None:
            raise NormalizedMetricNotFound(
                "normalized_valuation_metric_not_found",
                "normalized valuation metric revision was not found",
            )
        _visible(revision, as_of_cutoff, as_of_recorded_at_utc)
        identity = self._session.get(NormalizedValuationMetric, revision.metric_id)
        if identity is None:
            raise NormalizedMetricError(
                "normalized_metric_graph_incomplete", "normalized metric graph is incomplete"
            )
        links = list(
            self._session.scalars(
                select(NormalizedValuationMetricInputLink)
                .where(NormalizedValuationMetricInputLink.metric_revision_id == revision.id)
                .order_by(NormalizedValuationMetricInputLink.position)
            )
        )
        return {
            "metric_id": str(identity.id),
            "metric_revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "metric_key": identity.metric_key,
            "instrument_id": str(identity.instrument_id),
            "instrument_revision_id": str(revision.instrument_revision_id),
            "metric_code": identity.metric_code,
            "valuation_as_of_date": identity.valuation_as_of_date.isoformat(),
            "target_period_key": identity.target_period_key,
            "period_basis": identity.period_basis,
            "accounting_scope": identity.accounting_scope,
            "formula_version": identity.formula_version,
            "calculation_state": revision.calculation_state,
            "normalized_value_text": _decimal(revision.normalized_value, 4),
            "equity_value_text": _decimal(revision.equity_value, 6),
            "enterprise_value_text": _decimal(revision.enterprise_value, 6),
            "currency_code": revision.currency_code,
            "output_unit_code": revision.output_unit_code,
            "price_trade_date": revision.price_trade_date.isoformat(),
            "financial_period_end_date": revision.financial_period_end_date.isoformat(),
            "reason_codes": revision.reason_codes,
            "information_cutoff_date": revision.information_cutoff_date.isoformat(),
            "recorded_at_utc": _stored_utc(revision.recorded_at_utc).isoformat(),
            "recorded_by": revision.recorded_by,
            "supersedes_revision_id": _uuid(revision.supersedes_revision_id),
            "inputs": [self._metric_input(link) for link in links],
        }

    def get_comparison_set_revision(
        self,
        revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        revision = self._session.get(ValuationComparisonSetRevision, revision_id)
        if revision is None:
            raise NormalizedMetricNotFound(
                "normalized_valuation_comparison_not_found",
                "valuation comparison-set revision was not found",
            )
        _visible(revision, as_of_cutoff, as_of_recorded_at_utc)
        identity = self._session.get(ValuationComparisonSet, revision.comparison_set_id)
        if identity is None:
            raise NormalizedMetricError(
                "normalized_metric_graph_incomplete", "comparison-set graph is incomplete"
            )
        members = list(
            self._session.scalars(
                select(ValuationComparisonMember)
                .where(ValuationComparisonMember.comparison_revision_id == revision.id)
                .order_by(ValuationComparisonMember.position)
            )
        )
        return {
            "comparison_set_id": str(identity.id),
            "comparison_set_revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "comparison_key": identity.comparison_key,
            "comparison_kind": identity.comparison_kind,
            "subject_company_research_id": str(identity.subject_company_research_id),
            "subject_instrument_id": str(identity.subject_instrument_id),
            "subject_metric_revision_id": str(revision.subject_metric_revision_id),
            "metric_code": identity.metric_code,
            "target_period_key": identity.target_period_key,
            "period_basis": identity.period_basis,
            "accounting_scope": identity.accounting_scope,
            "formula_version": identity.formula_version,
            "purpose_code": identity.purpose_code,
            "rule_version": identity.rule_version,
            "comparison_state": revision.comparison_state,
            "rationale": revision.rationale,
            "total_member_count": revision.total_member_count,
            "eligible_member_count": revision.eligible_member_count,
            "excluded_member_count": revision.excluded_member_count,
            "minimum_value_text": _decimal(revision.minimum_value, 4),
            "maximum_value_text": _decimal(revision.maximum_value, 4),
            "median_value_text": _decimal(revision.median_value, 4),
            "subject_percentile_text": _decimal(revision.subject_percentile, 2),
            "information_cutoff_date": revision.information_cutoff_date.isoformat(),
            "recorded_at_utc": _stored_utc(revision.recorded_at_utc).isoformat(),
            "recorded_by": revision.recorded_by,
            "supersedes_revision_id": _uuid(revision.supersedes_revision_id),
            "members": [
                {
                    "position": member.position,
                    "member_key": member.member_key,
                    "company_research_revision_id": _uuid(
                        member.member_company_research_revision_id
                    ),
                    "instrument_revision_id": str(member.member_instrument_revision_id),
                    "metric_revision_id": _uuid(member.normalized_metric_revision_id),
                    "eligibility_state": member.eligibility_state,
                    "normalized_value_text": _decimal(member.normalized_value, 4),
                    "valuation_date": None
                    if member.valuation_date is None
                    else member.valuation_date.isoformat(),
                    "financial_period_end_date": None
                    if member.financial_period_end_date is None
                    else member.financial_period_end_date.isoformat(),
                    "is_subject": member.is_subject,
                    "reason_codes": member.reason_codes,
                }
                for member in members
            ],
        }

    def get_expectation_gap_revision(
        self,
        revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        revision = self._session.get(NormalizedExpectationGapRevision, revision_id)
        if revision is None:
            raise NormalizedMetricNotFound(
                "normalized_expectation_gap_not_found",
                "normalized expectation-gap revision was not found",
            )
        _visible(revision, as_of_cutoff, as_of_recorded_at_utc)
        identity = self._session.get(NormalizedExpectationGap, revision.gap_id)
        if identity is None:
            raise NormalizedMetricError(
                "normalized_metric_graph_incomplete", "expectation-gap graph is incomplete"
            )
        return {
            "gap_id": str(identity.id),
            "gap_revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "gap_key": identity.gap_key,
            "company_research_id": str(identity.company_research_id),
            "company_research_revision_id": str(revision.company_research_revision_id),
            "instrument_id": str(identity.instrument_id),
            "instrument_revision_id": str(revision.instrument_revision_id),
            "metric_code": identity.metric_code,
            "target_period_key": identity.target_period_key,
            "expected_source_kind": identity.expected_source_kind,
            "rule_version": identity.rule_version,
            "expected_observation_revision_id": str(
                revision.expected_observation_revision_id
            ),
            "actual_observation_revision_id": str(
                revision.actual_observation_revision_id
            ),
            "gap_state": revision.gap_state,
            "absolute_gap_text": _decimal(revision.absolute_gap, 6),
            "percentage_gap_text": _decimal(revision.percentage_gap, 4),
            "direction": revision.direction,
            "reason_codes": revision.reason_codes,
            "calculation_as_of_date": revision.calculation_as_of_date.isoformat(),
            "information_cutoff_date": revision.information_cutoff_date.isoformat(),
            "recorded_at_utc": _stored_utc(revision.recorded_at_utc).isoformat(),
            "recorded_by": revision.recorded_by,
            "supersedes_revision_id": _uuid(revision.supersedes_revision_id),
        }

    @staticmethod
    def _metric_input(link: NormalizedValuationMetricInputLink) -> dict[str, Any]:
        targets = {
            "canonical_price_revision_id": link.canonical_price_revision_id,
            "comparison_eligibility_revision_id": link.comparison_eligibility_revision_id,
            "financial_observation_revision_id": link.financial_observation_revision_id,
        }
        present = [(name, value) for name, value in targets.items() if value is not None]
        if len(present) != 1:
            raise NormalizedMetricError(
                "normalized_metric_graph_incomplete", "metric input lacks one exact target"
            )
        target_name, target_id = present[0]
        return {
            "position": link.position,
            "input_role": link.input_role,
            "target_field": target_name,
            "revision_id": str(target_id),
        }
