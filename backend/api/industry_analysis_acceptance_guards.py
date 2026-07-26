"""Strict ordinary-user guards over the accepted owner-acceptance core."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    IndustryThesisOwnerAcceptanceError,
)
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryRevision,
    Stage1CandidatePool,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
)

_ALLOWED_ORDINARY_SEMANTIC_OPERATIONS = {
    "none",
    "reuse_exact_semantic_revision",
}


def validate_ordinary_semantic_modes(candidate_owner_bindings: list[dict[str, Any]]) -> None:
    """Reject semantic authoring modes that are outside the ordinary-user v1 slice."""

    for index, binding in enumerate(candidate_owner_bindings):
        if not isinstance(binding, dict):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_PAYLOAD_INCOMPLETE",
                f"candidate_owner_bindings[{index}] must be an object",
            )
        operation = binding.get("semantic_operation")
        if operation not in _ALLOWED_ORDINARY_SEMANTIC_OPERATIONS:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_PAYLOAD_INCOMPLETE",
                (
                    f"semantic operation {operation!r} is outside the ordinary-user "
                    "v1 slice"
                ),
            )


def validate_exact_owner_context(
    session: Session,
    view: dict[str, Any],
    *,
    as_of_cutoff: date,
    as_of_recorded_at_utc: datetime,
) -> None:
    """Require one exact persisted Case/Map/Map Revision for all frozen identities."""

    members = view.get("members")
    if not isinstance(members, list):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED",
            "acceptance view members are malformed",
        )
    # The production workbench rejects an empty reviewed selection before returning.
    # Keeping an empty projection pass-through preserves isolated adapter test doubles.
    if not members:
        return

    stock_ids = {
        int(binding["stock_basic_record_id"])
        for member in members
        if isinstance(member, dict)
        for binding in [member.get("frozen_stock_binding")]
        if isinstance(binding, dict)
        and binding.get("state") == "available"
        and binding.get("stock_basic_record_id") is not None
    }
    if not stock_ids:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED",
            "reviewed result does not freeze a reachable owner context",
        )

    context_rows = session.execute(
        select(
            Stage1Beneficiary.case_id,
            Stage1Beneficiary.map_id,
            Stage1BeneficiaryRevision.selected_map_revision_id,
        )
        .join(
            Stage1BeneficiaryRevision,
            Stage1BeneficiaryRevision.beneficiary_id == Stage1Beneficiary.id,
        )
        .where(
            Stage1BeneficiaryRevision.stock_basic_record_id.in_(stock_ids),
            Stage1BeneficiaryRevision.assessment_status != "rejected",
            Stage1BeneficiaryRevision.information_cutoff_date <= as_of_cutoff,
            Stage1BeneficiaryRevision.recorded_at_utc <= as_of_recorded_at_utc,
        )
        .distinct()
    ).all()
    contexts = {
        (row.case_id, row.map_id, row.selected_map_revision_id)
        for row in context_rows
    }
    if len(contexts) != 1:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED",
            (
                "ordinary-user acceptance requires one uniquely frozen exact "
                f"owner context; found {len(contexts)}"
            ),
        )
    try:
        returned_context = (
            UUID(view["research_case"]["id"]),
            UUID(view["industry_map"]["id"]),
            UUID(view["industry_map"]["revision_id"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED",
            "acceptance view did not return one complete exact owner context",
        ) from exc
    if contexts != {returned_context}:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED",
            "acceptance view context differs from the uniquely frozen owner context",
        )


def validate_payload_against_view(payload: Any, view: dict[str, Any]) -> None:
    """Bind all server-owned flat-body fields to one exact acceptance snapshot."""

    expected = {
        "reviewed_session_revision_id": view.get("reviewed_session_revision_id"),
        "expected_session_latest_revision_number": view.get(
            "expected_session_latest_revision_number"
        ),
        "reviewed_plan_fingerprint_sha256": view.get(
            "reviewed_plan_fingerprint_sha256"
        ),
        "research_case_id": (view.get("research_case") or {}).get("id"),
        "map_mode": view.get("map_mode"),
        "industry_map_id": (view.get("industry_map") or {}).get("id"),
        "industry_map_revision_id": (view.get("industry_map") or {}).get(
            "revision_id"
        ),
        "information_cutoff_date": view.get("information_cutoff_date"),
        "owner_acceptance_plan_version": view.get(
            "owner_acceptance_plan_version"
        ),
    }
    actual = {
        "reviewed_session_revision_id": str(payload.reviewed_session_revision_id),
        "expected_session_latest_revision_number": (
            payload.expected_session_latest_revision_number
        ),
        "reviewed_plan_fingerprint_sha256": (
            payload.reviewed_plan_fingerprint_sha256
        ),
        "research_case_id": str(payload.research_case_id),
        "map_mode": payload.map_mode,
        "industry_map_id": str(payload.industry_map_id),
        "industry_map_revision_id": str(payload.industry_map_revision_id),
        "information_cutoff_date": payload.information_cutoff_date.isoformat(),
        "owner_acceptance_plan_version": payload.owner_acceptance_plan_version,
    }
    mismatched = [key for key in expected if expected[key] != actual[key]]
    if mismatched:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE",
            "request differs from the exact acceptance-view snapshot: "
            + ", ".join(sorted(mismatched)),
        )


def validate_reuse_pool_selection(
    candidate_owner_bindings: list[dict[str, Any]],
    candidate_pool_operation: dict[str, Any],
    view: dict[str, Any],
) -> None:
    """Allow exact pool reuse only for an all-reuse supported membership match."""

    if candidate_pool_operation.get("mode") != "reuse_exact_supported_handoff":
        return
    members = {
        member.get("reviewed_candidate_revision_id"): member
        for member in view.get("members", [])
        if isinstance(member, dict)
    }
    supported_revision_ids: list[str] = []
    for binding in candidate_owner_bindings:
        member = members.get(binding.get("reviewed_candidate_revision_id"))
        if member is None:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE",
                "candidate binding is absent from the exact acceptance view",
            )
        stage1_operation = binding.get("stage1_operation")
        stage1 = binding.get("stage1")
        if not isinstance(stage1, dict):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE"
            )
        if stage1_operation == "reuse_exact_beneficiary_revision":
            revision_id = stage1.get("beneficiary_revision_id")
            exact_option = next(
                (
                    option
                    for option in member.get("stage1_reuse_options", [])
                    if option.get("beneficiary_revision_id") == revision_id
                    and option.get("beneficiary_id") == stage1.get("beneficiary_id")
                    and option.get("stock_basic_record_id")
                    == stage1.get("stock_basic_record_id")
                ),
                None,
            )
            if exact_option is None:
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT",
                    "reused Stage 1 revision is absent from the exact view",
                )
            if exact_option.get("assessment_status") == "supported":
                supported_revision_ids.append(str(revision_id))
        elif stage1.get("assessment_status") == "supported":
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH",
                "exact pool reuse is unavailable for supported create or append",
            )
    if not supported_revision_ids:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH",
            "exact pool reuse requires at least one supported exact-reuse member",
        )
    selected_pool = next(
        (
            option
            for option in view.get(
                "candidate_pool_operation_contract", {}
            ).get("reuse_options", [])
            if option.get("candidate_pool_id")
            == candidate_pool_operation.get("candidate_pool_id")
            and option.get("candidate_pool_revision_id")
            == candidate_pool_operation.get("candidate_pool_revision_id")
        ),
        None,
    )
    if selected_pool is None or sorted(
        selected_pool.get("beneficiary_revision_ids", [])
    ) != sorted(supported_revision_ids):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH",
            "selected pool membership does not equal the final supported reuse set",
        )


def apply_exact_company_research_readiness(
    session: Session,
    result: dict[str, Any],
    *,
    as_of_cutoff: date,
    as_of_recorded_at_utc: datetime,
) -> dict[str, Any]:
    """Attach Company Research only through the accepted exact pool membership."""

    members = result.get("members")
    if not isinstance(members, list):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
        )
    supported = [
        member
        for member in members
        if isinstance(member, dict)
        and member.get("included_in_supported_handoff") is True
    ]
    pool_revision_text = result.get("accepted_candidate_pool_revision_id")
    latest_by_revision: dict[
        UUID, tuple[Stage2CompanyResearch, Stage2CompanyResearchRevision]
    ] = {}

    if pool_revision_text is not None and supported:
        pool_revision_id = UUID(pool_revision_text)
        supported_ids = {
            UUID(member["beneficiary_revision_id"]) for member in supported
        }
        rows = session.execute(
            select(
                Stage2CompanyResearch,
                Stage2CompanyResearchRevision,
                Stage1CandidatePoolMembership,
                Stage1CandidatePoolRevision,
                Stage1CandidatePool,
            )
            .join(
                Stage2CompanyResearchRevision,
                Stage2CompanyResearchRevision.company_research_id
                == Stage2CompanyResearch.id,
            )
            .join(
                Stage1CandidatePoolMembership,
                Stage1CandidatePoolMembership.id
                == Stage2CompanyResearch.candidate_pool_membership_id,
            )
            .join(
                Stage1CandidatePoolRevision,
                Stage1CandidatePoolRevision.id
                == Stage2CompanyResearch.candidate_pool_revision_id,
            )
            .join(
                Stage1CandidatePool,
                Stage1CandidatePool.id == Stage2CompanyResearch.candidate_pool_id,
            )
            .where(
                Stage2CompanyResearch.candidate_pool_revision_id
                == pool_revision_id,
                Stage2CompanyResearch.beneficiary_revision_id.in_(supported_ids),
                Stage2CompanyResearchRevision.information_cutoff_date
                <= as_of_cutoff,
                Stage2CompanyResearchRevision.recorded_at_utc
                <= as_of_recorded_at_utc,
            )
        ).all()
        member_by_revision = {
            UUID(member["beneficiary_revision_id"]): member for member in supported
        }
        technical = result.get("technical_details") or {}
        try:
            expected_case_id = UUID(technical["research_case_id"])
            expected_map_id = UUID(technical["industry_map_id"])
            expected_map_revision_id = UUID(technical["industry_map_revision_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "accepted result omitted exact owner context",
            ) from exc

        for research, revision, membership, pool_revision, pool in rows:
            member = member_by_revision.get(research.beneficiary_revision_id)
            if member is None:
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
                )
            if (
                membership.candidate_pool_revision_id != pool_revision_id
                or membership.beneficiary_revision_id
                != research.beneficiary_revision_id
                or pool_revision.id != pool_revision_id
                or pool_revision.candidate_pool_id != pool.id
                or research.candidate_pool_id != pool.id
                or pool.case_id != expected_case_id
                or pool.map_id != expected_map_id
                or pool_revision.selected_map_revision_id
                != expected_map_revision_id
                or research.case_id != expected_case_id
                or research.map_id != expected_map_id
                or research.selected_map_revision_id
                != expected_map_revision_id
                or str(research.beneficiary_id) != member.get("beneficiary_id")
                or str(research.beneficiary_revision_id)
                != member.get("beneficiary_revision_id")
                or research.stock_basic_record_id
                != member.get("stock_basic_record_id")
            ):
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                    "Company Research is not attached through the exact accepted membership",
                )
            current = latest_by_revision.get(research.beneficiary_revision_id)
            if current is None or revision.revision_no > current[1].revision_no:
                latest_by_revision[research.beneficiary_revision_id] = (
                    research,
                    revision,
                )

    semantic_covered_count = 0
    company_ready_count = 0
    for member in members:
        if member.get("semantic", {}).get("state") != "missing":
            semantic_covered_count += 1
        revision_id = UUID(member["beneficiary_revision_id"])
        company_pair = latest_by_revision.get(revision_id)
        if pool_revision_text is None:
            company_state = {
                "state": "missing",
                "company_research_id": None,
                "company_research_revision_id": None,
                "reason": "no_supported_handoff_pool",
            }
        elif member.get("included_in_supported_handoff") is not True:
            company_state = {
                "state": "missing",
                "company_research_id": None,
                "company_research_revision_id": None,
                "reason": "not_in_supported_handoff",
            }
        elif company_pair is None:
            company_state = {
                "state": "missing",
                "company_research_id": None,
                "company_research_revision_id": None,
                "reason": "exact_company_research_not_found",
            }
        else:
            company_state = {
                "state": company_pair[1].conclusion_status,
                "workflow_state": company_pair[1].workflow_state,
                "company_research_id": str(company_pair[0].id),
                "company_research_revision_id": str(company_pair[1].id),
                "reason": None,
            }
            company_ready_count += 1
        member["company_research"] = company_state
        reasons = {
            reason
            for reason in member.get("readiness_reason_codes", [])
            if reason != "company_research_missing"
        }
        if company_state["state"] == "missing":
            reasons.add("company_research_missing")
        member["readiness_reason_codes"] = sorted(reasons)
        member["ready_for_later_explicit_handoff"] = bool(
            member.get("included_in_supported_handoff")
            and member.get("semantic", {}).get("state") != "missing"
            and company_state["state"] != "missing"
        )

    largest_gap = "暂无"
    if company_ready_count < len(members):
        largest_gap = "部分成员尚未建立精确候选池归属的 Company Research"
    elif semantic_covered_count < len(members):
        largest_gap = "部分成员尚未绑定类型化语义"
    result["company_research_ready_count"] = company_ready_count
    result["semantic_covered_count"] = semantic_covered_count
    result["largest_missing_prerequisite"] = largest_gap
    result["facts"] = [
        {"label": "完整成员", "value": len(members)},
        {"label": "supported 后续研究", "value": len(supported)},
        {
            "label": "草稿或争议成员",
            "value": result.get("draft_or_disputed_count", 0),
        },
        {
            "label": "类型化语义覆盖",
            "value": f"{semantic_covered_count}/{len(members)}",
        },
        {
            "label": "Company Research 已存在",
            "value": f"{company_ready_count}/{len(members)}",
        },
        {"label": "最大准备度缺口", "value": largest_gap},
        {"label": "研究用途", "value": "不构成投资建议"},
    ]
    return result
