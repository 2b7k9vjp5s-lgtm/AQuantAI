"""Local ordinary-user API and pages for Industry Thesis owner acceptance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.api.industry_analysis import (
    _validated_json_body,
    get_industry_analysis_session_factory,
    get_industry_analysis_write_factory,
)
from industry_alpha.industry_thesis_owner_acceptance import (
    IndustryThesisOwnerAcceptanceService,
)
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    IndustryThesisOwnerAcceptanceError,
)
from industry_alpha.industry_thesis_owner_acceptance_workbench import (
    IndustryThesisOwnerAcceptanceWorkbenchQueryService,
)
from industry_alpha.industry_thesis_rules import IndustryThesisError, stored_utc
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


api_router = APIRouter(tags=["industry-analysis-owner-acceptance"])
page_router = APIRouter(tags=["industry-analysis-pages"])
_STATIC_DIR = Path(__file__).resolve().parents[2] / "industry_analysis" / "static"
_ALLOWED_ORDINARY_SEMANTIC_OPERATIONS = {
    "none",
    "reuse_exact_semantic_revision",
}


@dataclass
class _LoadedAcceptanceGraph:
    beneficiaries: dict[UUID, Stage1Beneficiary] = field(default_factory=dict)
    beneficiary_revisions: dict[UUID, Stage1BeneficiaryRevision] = field(
        default_factory=dict
    )
    candidate_pools: dict[UUID, Stage1CandidatePool] = field(default_factory=dict)
    candidate_pool_revisions: dict[UUID, Stage1CandidatePoolRevision] = field(
        default_factory=dict
    )
    candidate_pool_memberships: dict[UUID, Stage1CandidatePoolMembership] = field(
        default_factory=dict
    )
    company_research: dict[UUID, Stage2CompanyResearch] = field(default_factory=dict)
    company_research_revisions: dict[UUID, Stage2CompanyResearchRevision] = field(
        default_factory=dict
    )

    def capture(self, instance: object) -> None:
        if isinstance(instance, Stage1Beneficiary):
            self.beneficiaries[instance.id] = instance
        elif isinstance(instance, Stage1BeneficiaryRevision):
            self.beneficiary_revisions[instance.id] = instance
        elif isinstance(instance, Stage1CandidatePool):
            self.candidate_pools[instance.id] = instance
        elif isinstance(instance, Stage1CandidatePoolRevision):
            self.candidate_pool_revisions[instance.id] = instance
        elif isinstance(instance, Stage1CandidatePoolMembership):
            self.candidate_pool_memberships[instance.id] = instance
        elif isinstance(instance, Stage2CompanyResearch):
            self.company_research[instance.id] = instance
        elif isinstance(instance, Stage2CompanyResearchRevision):
            self.company_research_revisions[instance.id] = instance


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OwnerAcceptancePlanRequest(_StrictModel):
    reviewed_session_revision_id: UUID
    expected_session_latest_revision_number: int = Field(ge=1)
    reviewed_plan_fingerprint_sha256: str = Field(min_length=64, max_length=64)
    research_case_id: UUID
    map_mode: str = Field(min_length=1, max_length=96)
    industry_map_id: UUID
    industry_map_revision_id: UUID
    candidate_owner_bindings: list[dict[str, Any]] = Field(min_length=1)
    candidate_pool_operation: dict[str, Any]
    output_title: str = Field(min_length=1, max_length=300)
    output_scope: str = Field(min_length=1, max_length=4000)
    information_cutoff_date: date
    revision_note: str = Field(min_length=1, max_length=1000)
    owner_acceptance_plan_version: str = Field(min_length=1, max_length=128)


class OwnerAcceptanceCommitRequest(OwnerAcceptancePlanRequest):
    preview_fingerprint_sha256: str = Field(min_length=64, max_length=64)


def _acceptance_http_error(exc: IndustryThesisError) -> HTTPException:
    code = exc.code
    not_found = {
        "industry_thesis_session_not_found",
        "industry_thesis_session_revision_not_found",
        "industry_thesis_not_visible",
    }
    conflicts = {
        "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE",
        "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT",
        "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_ALREADY_EXISTS",
        "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_CONFLICT",
    }
    recovery = {
        "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE": "重新读取精确研究结果并再次生成预览。",
        "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT": "保留当前填写内容，重新读取正式记录后再次预览。",
        "INDUSTRY_THESIS_ACCEPTANCE_STOCK_IDENTITY_REQUIRED": "返回候选审核，补齐冻结的正式公司记录。",
        "INDUSTRY_THESIS_ACCEPTANCE_LISTED_INSTRUMENT_ONLY": "返回候选审核，将证券身份解析为正式股票基础记录。",
        "INDUSTRY_THESIS_ACCEPTANCE_STAGE1_BINDINGS_REQUIRED": "选择完整的产业地图断言和研究主张后再次预览。",
        "INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_PAYLOAD_INCOMPLETE": "普通用户接受仅允许不绑定或复用精确类型化语义记录。",
        "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH": "重新确认全局后续研究池操作。",
        "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE": "停止使用当前链接并执行本地完整性检查。",
    }
    if code in not_found:
        status = 404
    elif code in conflicts:
        status = 409
    else:
        status = 422
    detail = getattr(exc, "detail", None)
    return HTTPException(
        status_code=status,
        detail={
            "code": code,
            "message": str(exc),
            "technical_message": detail or str(exc),
            "recovery_action": recovery.get(
                code,
                "检查当前明确选择和精确时间边界后再次预览。",
            ),
            "preserve_form": status in {409, 422, 503},
        },
    )


def _database_failure(message: str, _exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "industry_analysis_acceptance_database_unavailable",
            "message": message,
            "technical_message": "local database operation failed",
            "recovery_action": "保留当前填写内容，检查本地数据库后手动重试。",
            "preserve_form": True,
        },
    )


def _raw_plan(payload: OwnerAcceptancePlanRequest) -> dict[str, Any]:
    return payload.model_dump(mode="json")


def _validate_route_body(
    route_revision_id: UUID,
    payload: OwnerAcceptancePlanRequest,
) -> None:
    if payload.reviewed_session_revision_id != route_revision_id:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE",
            "route reviewed revision does not equal body reviewed revision",
        )


def _validate_ordinary_semantic_modes(
    payload: OwnerAcceptancePlanRequest,
) -> None:
    for index, binding in enumerate(payload.candidate_owner_bindings):
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


def _capture_workbench_call(
    session: Session,
    call: Any,
) -> tuple[dict[str, Any], _LoadedAcceptanceGraph]:
    graph = _LoadedAcceptanceGraph()

    def loaded(_session: Session, instance: object) -> None:
        graph.capture(instance)

    event.listen(session, "loaded_as_persistent", loaded)
    try:
        result = call()
    finally:
        event.remove(session, "loaded_as_persistent", loaded)
    return result, graph


def _require_single_exact_owner_context(
    graph: _LoadedAcceptanceGraph,
    view: dict[str, Any],
    *,
    as_of_cutoff: date,
    as_of_recorded_at_utc: datetime,
) -> None:
    stock_ids = {
        int(binding["stock_basic_record_id"])
        for member in view.get("members", [])
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
    contexts: set[tuple[UUID, UUID, UUID]] = set()
    for revision in graph.beneficiary_revisions.values():
        if (
            revision.stock_basic_record_id not in stock_ids
            or revision.assessment_status == "rejected"
            or revision.information_cutoff_date > as_of_cutoff
            or stored_utc(revision.recorded_at_utc) > as_of_recorded_at_utc
        ):
            continue
        beneficiary = graph.beneficiaries.get(revision.beneficiary_id)
        if beneficiary is None:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "loaded Stage 1 revision is missing its exact beneficiary identity",
            )
        contexts.add(
            (
                beneficiary.case_id,
                beneficiary.map_id,
                revision.selected_map_revision_id,
            )
        )
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


def _load_exact_acceptance_view(
    session: Session,
    *,
    session_id: UUID,
    reviewed_session_revision_id: UUID,
    as_of_cutoff: date,
    as_of_recorded_at_utc: datetime,
) -> dict[str, Any]:
    service = IndustryThesisOwnerAcceptanceWorkbenchQueryService(session)
    view, graph = _capture_workbench_call(
        session,
        lambda: service.get_acceptance_view(
            session_id=session_id,
            reviewed_session_revision_id=reviewed_session_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=as_of_recorded_at_utc,
        ),
    )
    _require_single_exact_owner_context(
        graph,
        view,
        as_of_cutoff=as_of_cutoff,
        as_of_recorded_at_utc=as_of_recorded_at_utc,
    )
    return view


def _validate_payload_against_view(
    payload: OwnerAcceptancePlanRequest,
    view: dict[str, Any],
) -> None:
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


def _validate_reuse_pool_selection(
    payload: OwnerAcceptancePlanRequest,
    view: dict[str, Any],
) -> None:
    operation = payload.candidate_pool_operation
    if operation.get("mode") != "reuse_exact_supported_handoff":
        return
    members = {
        member.get("reviewed_candidate_revision_id"): member
        for member in view.get("members", [])
        if isinstance(member, dict)
    }
    supported_revision_ids: list[str] = []
    for binding in payload.candidate_owner_bindings:
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
                "exact pool reuse is unavailable when a supported member is created or appended",
            )
    if not supported_revision_ids:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH",
            "exact pool reuse requires at least one supported exact-reuse member",
        )
    selected_pool = next(
        (
            option
            for option in (
                view.get("candidate_pool_operation_contract", {}).get(
                    "reuse_options", []
                )
            )
            if option.get("candidate_pool_id")
            == operation.get("candidate_pool_id")
            and option.get("candidate_pool_revision_id")
            == operation.get("candidate_pool_revision_id")
        ),
        None,
    )
    if selected_pool is None or sorted(
        selected_pool.get("beneficiary_revision_ids", [])
    ) != sorted(supported_revision_ids):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH",
            "selected pool membership does not equal the final supported exact-reuse set",
        )


def _apply_exact_company_research_readiness(
    graph: _LoadedAcceptanceGraph,
    result: dict[str, Any],
    *,
    as_of_cutoff: date,
    as_of_recorded_at_utc: datetime,
) -> dict[str, Any]:
    members = result.get("members")
    if not isinstance(members, list):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
        )
    pool_revision_text = result.get("accepted_candidate_pool_revision_id")
    supported = [
        member
        for member in members
        if isinstance(member, dict)
        and member.get("included_in_supported_handoff") is True
    ]
    latest_by_beneficiary_revision: dict[
        UUID, tuple[Stage2CompanyResearch, Stage2CompanyResearchRevision]
    ] = {}
    if pool_revision_text is not None and supported:
        pool_revision_id = UUID(pool_revision_text)
        pool_revision = graph.candidate_pool_revisions.get(pool_revision_id)
        pool = (
            None
            if pool_revision is None
            else graph.candidate_pools.get(pool_revision.candidate_pool_id)
        )
        if pool_revision is None or pool is None:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "accepted pool graph was not loaded with the exact result",
            )
        memberships = {
            membership.beneficiary_revision_id: membership
            for membership in graph.candidate_pool_memberships.values()
            if membership.candidate_pool_revision_id == pool_revision_id
        }
        member_by_revision = {
            UUID(member["beneficiary_revision_id"]): member for member in supported
        }
        if set(memberships) != set(member_by_revision):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "accepted pool membership differs from supported output membership",
            )
        technical = result.get("technical_details") or {}
        expected_case_id = UUID(technical["research_case_id"])
        expected_map_id = UUID(technical["industry_map_id"])
        expected_map_revision_id = UUID(technical["industry_map_revision_id"])
        revisions_by_research: dict[
            UUID, list[Stage2CompanyResearchRevision]
        ] = {}
        for revision in graph.company_research_revisions.values():
            if (
                revision.information_cutoff_date <= as_of_cutoff
                and stored_utc(revision.recorded_at_utc)
                <= as_of_recorded_at_utc
            ):
                revisions_by_research.setdefault(
                    revision.company_research_id, []
                ).append(revision)
        for research in graph.company_research.values():
            member = member_by_revision.get(research.beneficiary_revision_id)
            if member is None:
                continue
            membership = memberships[research.beneficiary_revision_id]
            if (
                research.candidate_pool_revision_id != pool_revision_id
                or research.candidate_pool_membership_id != membership.id
                or research.candidate_pool_id != pool.id
            ):
                continue
            if (
                membership.beneficiary_id != research.beneficiary_id
                or membership.beneficiary_revision_id
                != research.beneficiary_revision_id
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
                    "Company Research is not attached through the exact accepted pool membership",
                )
            revisions = revisions_by_research.get(research.id, [])
            if not revisions:
                continue
            latest_revision = max(revisions, key=lambda item: item.revision_no)
            current = latest_by_beneficiary_revision.get(
                research.beneficiary_revision_id
            )
            if current is None or latest_revision.revision_no > current[1].revision_no:
                latest_by_beneficiary_revision[
                    research.beneficiary_revision_id
                ] = (research, latest_revision)

    company_ready_count = 0
    semantic_covered_count = 0
    for member in members:
        if member.get("semantic", {}).get("state") != "missing":
            semantic_covered_count += 1
        revision_id = UUID(member["beneficiary_revision_id"])
        company_pair = latest_by_beneficiary_revision.get(revision_id)
        if (
            pool_revision_text is None
            or member.get("included_in_supported_handoff") is not True
        ):
            company_state = {
                "state": "missing",
                "company_research_id": None,
                "company_research_revision_id": None,
                "reason": "no_supported_handoff_pool",
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

    supported_members = [
        member for member in members if member.get("included_in_supported_handoff")
    ]
    result["supported_handoff_members"] = supported_members
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
        {"label": "supported 后续研究", "value": len(supported_members)},
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


def _accepted_result_path(
    *,
    session_id: str,
    accepted_session_revision_id: str,
    information_cutoff_date: str,
    recorded_at_utc: str,
) -> str:
    query = urlencode(
        {
            "as_of_cutoff": information_cutoff_date,
            "as_of_recorded_at_utc": recorded_at_utc,
        }
    )
    return (
        f"/industry-analysis/sessions/{session_id}/revisions/"
        f"{accepted_session_revision_id}/accepted-result?{query}"
    )


@page_router.get(
    "/industry-analysis/sessions/{session_id}/revisions/"
    "{reviewed_session_revision_id}/acceptance",
    include_in_schema=False,
)
def owner_acceptance_page(
    session_id: UUID,
    reviewed_session_revision_id: UUID,
) -> FileResponse:
    del session_id, reviewed_session_revision_id
    return FileResponse(_STATIC_DIR / "owner_acceptance.html", media_type="text/html")


@page_router.get(
    "/industry-analysis/sessions/{session_id}/revisions/"
    "{accepted_session_revision_id}/accepted-result",
    include_in_schema=False,
)
def accepted_result_page(
    session_id: UUID,
    accepted_session_revision_id: UUID,
) -> FileResponse:
    del session_id, accepted_session_revision_id
    return FileResponse(_STATIC_DIR / "accepted_result.html", media_type="text/html")


@api_router.get(
    "/session-revisions/{reviewed_session_revision_id}/owner-acceptance-view"
)
def get_owner_acceptance_view(
    reviewed_session_revision_id: UUID,
    session_id: UUID = Query(),
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(
        get_industry_analysis_session_factory
    ),
) -> dict[str, Any]:
    try:
        with session_factory() as session:
            return _load_exact_acceptance_view(
                session,
                session_id=session_id,
                reviewed_session_revision_id=reviewed_session_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
    except IndustryThesisError as exc:
        raise _acceptance_http_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_failure("研究成果接受准备读取失败。", exc) from exc


@api_router.post(
    "/session-revisions/{reviewed_session_revision_id}/owner-acceptance/preview"
)
async def preview_owner_acceptance(
    reviewed_session_revision_id: UUID,
    request: Request,
    session_id: UUID = Query(),
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    read_factory: sessionmaker[Session] = Depends(
        get_industry_analysis_session_factory
    ),
    write_factory: sessionmaker[Session] = Depends(
        get_industry_analysis_write_factory
    ),
) -> dict[str, Any]:
    payload = await _validated_json_body(request, OwnerAcceptancePlanRequest)
    try:
        _validate_route_body(reviewed_session_revision_id, payload)
        _validate_ordinary_semantic_modes(payload)
        with read_factory() as session:
            view = _load_exact_acceptance_view(
                session,
                session_id=session_id,
                reviewed_session_revision_id=reviewed_session_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
        _validate_payload_against_view(payload, view)
        _validate_reuse_pool_selection(payload, view)
        result = IndustryThesisOwnerAcceptanceService(write_factory).preview(
            _raw_plan(payload)
        )
        result["primary_action"] = (
            {
                "kind": "commit",
                "label": "确认接受研究成果",
            }
            if result.get("commit_ready")
            else {
                "kind": "correct",
                "label": "检查并修正接受字段",
            }
        )
        return result
    except IndustryThesisError as exc:
        raise _acceptance_http_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_failure("研究成果预览失败。", exc) from exc


@api_router.post(
    "/session-revisions/{reviewed_session_revision_id}/owner-acceptance/commit"
)
async def commit_owner_acceptance(
    reviewed_session_revision_id: UUID,
    request: Request,
    session_id: UUID = Query(),
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    read_factory: sessionmaker[Session] = Depends(
        get_industry_analysis_session_factory
    ),
    write_factory: sessionmaker[Session] = Depends(
        get_industry_analysis_write_factory
    ),
) -> dict[str, Any]:
    payload = await _validated_json_body(request, OwnerAcceptanceCommitRequest)
    try:
        _validate_route_body(reviewed_session_revision_id, payload)
        _validate_ordinary_semantic_modes(payload)
        with read_factory() as session:
            view = _load_exact_acceptance_view(
                session,
                session_id=session_id,
                reviewed_session_revision_id=reviewed_session_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
        _validate_payload_against_view(payload, view)
        _validate_reuse_pool_selection(payload, view)
        result = IndustryThesisOwnerAcceptanceService(write_factory).commit(
            _raw_plan(payload)
        )
        accepted_session_revision_id = result["accepted_session_revision_id"]
        if not accepted_session_revision_id:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "commit did not return an accepted session revision",
            )
        result["accepted_result_path"] = _accepted_result_path(
            session_id=str(session_id),
            accepted_session_revision_id=accepted_session_revision_id,
            information_cutoff_date=payload.information_cutoff_date.isoformat(),
            recorded_at_utc=result["recorded_at_utc"],
        )
        result["history_path"] = "/industry-analysis"
        return result
    except IndustryThesisError as exc:
        raise _acceptance_http_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_failure(
            "研究成果提交失败，请先重新打开精确结果确认是否已经写入。",
            exc,
        ) from exc


@api_router.get(
    "/session-revisions/{accepted_session_revision_id}/accepted-result-view"
)
def get_accepted_result_view(
    accepted_session_revision_id: UUID,
    session_id: UUID = Query(),
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(
        get_industry_analysis_session_factory
    ),
) -> dict[str, Any]:
    try:
        with session_factory() as session:
            service = IndustryThesisOwnerAcceptanceWorkbenchQueryService(session)
            result, graph = _capture_workbench_call(
                session,
                lambda: service.get_accepted_result_view(
                    session_id=session_id,
                    accepted_session_revision_id=accepted_session_revision_id,
                    as_of_cutoff=as_of_cutoff,
                    as_of_recorded_at_utc=as_of_recorded_at_utc,
                ),
            )
            return _apply_exact_company_research_readiness(
                graph,
                result,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
    except IndustryThesisError as exc:
        raise _acceptance_http_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_failure("已接受研究成果读取失败。", exc) from exc
