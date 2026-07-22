"""Exact-ID, dual-as-of Investment Candidate Intelligence v1 reads."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import StockBasicRecord
from industry_alpha.investment_candidate_commands import INPUT_TARGETS
from industry_alpha.investment_candidate_models import (
    InvestmentCandidateComponentAssessment,
    InvestmentCandidateComponentInputLink,
    InvestmentCandidateComponentRevision,
    InvestmentCandidateMember,
    InvestmentCandidateMemberComponentLink,
    InvestmentCandidateMemberReasonCode,
    InvestmentCandidateSnapshot,
    InvestmentCandidateSnapshotRevision,
)
from industry_alpha.investment_candidate_rules import (
    InvestmentCandidateError,
    InvestmentCandidateNotFound,
)
from industry_alpha.stage1_models import Stage1BeneficiaryRevision


def _stored_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _visible(row: Any, cutoff: date, recorded_at: datetime) -> None:
    information = getattr(row, "information_cutoff_date", None)
    recorded = getattr(row, "recorded_at_utc", None)
    if information is not None and information > cutoff:
        raise InvestmentCandidateNotFound(
            "investment_candidate_not_visible", "record is outside the requested information cutoff"
        )
    if recorded is not None and _stored_utc(recorded) > recorded_at:
        raise InvestmentCandidateNotFound(
            "investment_candidate_not_visible", "record is outside the requested recorded-time boundary"
        )


def _value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return format(value, ".2f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _input_target(link: InvestmentCandidateComponentInputLink) -> tuple[str, UUID]:
    for kind, (_model, column) in INPUT_TARGETS.items():
        value = getattr(link, column)
        if value is not None:
            return kind, value
    raise InvestmentCandidateError(
        "investment_candidate_input_invalid", "component input link lacks exact target"
    )


class InvestmentCandidateQueryService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_component_revision(
        self,
        component_revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        revision = self._session.get(InvestmentCandidateComponentRevision, component_revision_id)
        if revision is None:
            raise InvestmentCandidateNotFound(
                "investment_candidate_component_not_found", "component revision was not found"
            )
        _visible(revision, as_of_cutoff, as_of_recorded_at_utc)
        assessment = self._session.get(
            InvestmentCandidateComponentAssessment, revision.component_assessment_id
        )
        if assessment is None:
            raise InvestmentCandidateError(
                "investment_candidate_graph_incomplete", "component assessment graph is incomplete"
            )
        links = list(
            self._session.scalars(
                select(InvestmentCandidateComponentInputLink)
                .where(InvestmentCandidateComponentInputLink.component_revision_id == revision.id)
                .order_by(InvestmentCandidateComponentInputLink.position)
            )
        )
        inputs = []
        for link in links:
            kind, target_id = _input_target(link)
            inputs.append({"position": link.position, "kind": kind, "revision_id": str(target_id)})
        return {
            "component_assessment_id": str(assessment.id),
            "component_revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "assessment_key": assessment.assessment_key,
            "beneficiary_id": str(assessment.beneficiary_id),
            "beneficiary_revision_id": str(revision.beneficiary_revision_id),
            "company_research_revision_id": str(revision.company_research_revision_id),
            "component_code": assessment.component_code,
            "assessment_state": revision.assessment_state,
            "verification_state": revision.verification_state,
            "verification_material": revision.verification_material,
            "source_score_text": revision.source_score_text,
            "score_value": _value(revision.score_value),
            "missing_reason": revision.missing_reason,
            "rationale": revision.rationale,
            "falsification_condition": revision.falsification_condition,
            "falsification_state": revision.falsification_state,
            "information_cutoff_date": revision.information_cutoff_date.isoformat(),
            "recorded_at_utc": _stored_utc(revision.recorded_at_utc).isoformat(),
            "recorded_by": revision.recorded_by,
            "supersedes_revision_id": _value(revision.supersedes_revision_id),
            "inputs": inputs,
        }

    def get_snapshot_revision(
        self,
        snapshot_revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        revision = self._session.get(InvestmentCandidateSnapshotRevision, snapshot_revision_id)
        if revision is None:
            raise InvestmentCandidateNotFound(
                "investment_candidate_snapshot_not_found", "snapshot revision was not found"
            )
        _visible(revision, as_of_cutoff, as_of_recorded_at_utc)
        snapshot = self._session.get(InvestmentCandidateSnapshot, revision.snapshot_id)
        if snapshot is None:
            raise InvestmentCandidateError(
                "investment_candidate_graph_incomplete", "snapshot graph is incomplete"
            )
        members = list(
            self._session.scalars(
                select(InvestmentCandidateMember)
                .where(InvestmentCandidateMember.snapshot_revision_id == revision.id)
                .order_by(
                    InvestmentCandidateMember.priority_ordinal.is_(None),
                    InvestmentCandidateMember.priority_ordinal,
                    InvestmentCandidateMember.beneficiary_id,
                )
            )
        )
        member_ids = [row.id for row in members]
        beneficiary_ids = [row.beneficiary_revision_id for row in members]
        beneficiary_rows = {
            row.id: row
            for row in self._session.scalars(
                select(Stage1BeneficiaryRevision).where(Stage1BeneficiaryRevision.id.in_(beneficiary_ids))
            )
        }
        stock_ids = [row.stock_basic_record_id for row in beneficiary_rows.values()]
        stocks = {
            row.id: row
            for row in self._session.scalars(
                select(StockBasicRecord).where(StockBasicRecord.id.in_(stock_ids))
            )
        }
        component_links = list(
            self._session.scalars(
                select(InvestmentCandidateMemberComponentLink)
                .where(InvestmentCandidateMemberComponentLink.member_id.in_(member_ids))
                .order_by(
                    InvestmentCandidateMemberComponentLink.member_id,
                    InvestmentCandidateMemberComponentLink.component_code,
                )
            )
        ) if member_ids else []
        component_revision_ids = [row.component_revision_id for row in component_links]
        component_revisions = {
            row.id: row
            for row in self._session.scalars(
                select(InvestmentCandidateComponentRevision).where(
                    InvestmentCandidateComponentRevision.id.in_(component_revision_ids)
                )
            )
        } if component_revision_ids else {}
        assessment_ids = [row.component_assessment_id for row in component_revisions.values()]
        assessments = {
            row.id: row
            for row in self._session.scalars(
                select(InvestmentCandidateComponentAssessment).where(
                    InvestmentCandidateComponentAssessment.id.in_(assessment_ids)
                )
            )
        } if assessment_ids else {}
        reason_rows = list(
            self._session.scalars(
                select(InvestmentCandidateMemberReasonCode)
                .where(InvestmentCandidateMemberReasonCode.member_id.in_(member_ids))
                .order_by(
                    InvestmentCandidateMemberReasonCode.member_id,
                    InvestmentCandidateMemberReasonCode.ordinal,
                )
            )
        ) if member_ids else []
        components_by_member: dict[UUID, list[dict[str, Any]]] = {row.id: [] for row in members}
        reasons_by_member: dict[UUID, list[str]] = {row.id: [] for row in members}
        for link in component_links:
            component_revision = component_revisions.get(link.component_revision_id)
            assessment = None if component_revision is None else assessments.get(
                component_revision.component_assessment_id
            )
            if component_revision is None or assessment is None:
                raise InvestmentCandidateError(
                    "investment_candidate_graph_incomplete", "member component graph is incomplete"
                )
            _visible(component_revision, as_of_cutoff, as_of_recorded_at_utc)
            components_by_member[link.member_id].append(
                {
                    "component_code": link.component_code,
                    "component_revision_id": str(component_revision.id),
                    "assessment_state": component_revision.assessment_state,
                    "verification_state": component_revision.verification_state,
                    "falsification_state": component_revision.falsification_state,
                    "score_value": _value(component_revision.score_value),
                    "rule_weight": format(link.rule_weight, ".4f"),
                    "contribution_amount": _value(link.contribution_amount),
                }
            )
        for reason in reason_rows:
            reasons_by_member[reason.member_id].append(reason.reason_code)
        output_members = []
        for member in members:
            beneficiary = beneficiary_rows.get(member.beneficiary_revision_id)
            stock = None if beneficiary is None else stocks.get(beneficiary.stock_basic_record_id)
            if beneficiary is None:
                raise InvestmentCandidateError(
                    "investment_candidate_graph_incomplete", "beneficiary graph is incomplete"
                )
            output_members.append(
                {
                    "member_id": str(member.id),
                    "candidate_pool_membership_id": str(member.candidate_pool_membership_id),
                    "beneficiary_id": str(member.beneficiary_id),
                    "beneficiary_revision_id": str(member.beneficiary_revision_id),
                    "beneficiary_kind": beneficiary.beneficiary_kind,
                    "stock_code": None if stock is None else stock.stock_code,
                    "stock_name": None if stock is None else stock.stock_name,
                    "company_research_revision_id": _value(member.company_research_revision_id),
                    "typed_beneficiary_revision_id": _value(member.typed_beneficiary_revision_id),
                    "canonical_price_revision_id": _value(member.canonical_price_revision_id),
                    "comparison_eligibility_revision_id": _value(member.comparison_eligibility_revision_id),
                    "base_score": _value(member.base_score),
                    "business_quality_score": _value(member.business_quality_score),
                    "risk_penalty_points": _value(member.risk_penalty_points),
                    "final_score": _value(member.final_score),
                    "candidate_status": member.candidate_status,
                    "priority_ordinal": member.priority_ordinal,
                    "reason_codes": reasons_by_member[member.id],
                    "components": components_by_member[member.id],
                }
            )
        return {
            "snapshot_id": str(snapshot.id),
            "snapshot_revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "snapshot_key": snapshot.snapshot_key,
            "candidate_pool_id": str(snapshot.candidate_pool_id),
            "candidate_pool_revision_id": str(revision.candidate_pool_revision_id),
            "purpose_code": revision.purpose_code,
            "rule_version": revision.rule_version,
            "information_cutoff_date": revision.information_cutoff_date.isoformat(),
            "recorded_at_utc": _stored_utc(revision.recorded_at_utc).isoformat(),
            "recorded_by": revision.recorded_by,
            "member_count": len(output_members),
            "members": output_members,
        }
