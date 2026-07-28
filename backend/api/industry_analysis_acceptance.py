"""Local ordinary-user API and pages for Owner Context v2 acceptance."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.api.industry_analysis import (
    _validated_json_body,
    get_industry_analysis_session_factory,
    get_industry_analysis_write_factory,
)
from industry_alpha.industry_research_e2e_rules import (
    ACCEPTANCE_VIEW_SNAPSHOT_CONTRACT_VERSION,
    SNAPSHOT_BODY_MISMATCH_CODE,
    acceptance_view_snapshot_content_sha256,
)
from industry_alpha.industry_thesis_models import IndustryThesisSessionRevision
from industry_alpha.industry_thesis_owner_acceptance import (
    IndustryThesisOwnerAcceptanceService,
)
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    IndustryThesisOwnerAcceptanceError,
)
from industry_alpha.industry_thesis_owner_acceptance_query import (
    IndustryThesisAcceptedOutputQueryService,
)
from industry_alpha.industry_thesis_owner_acceptance_workbench import (
    IndustryThesisOwnerAcceptanceWorkbenchQueryService,
)
from industry_alpha.industry_thesis_rules import (
    IndustryThesisError,
    json_value,
    stored_utc,
)

api_router = APIRouter(
    prefix="/industry-analysis/api",
    tags=["industry-analysis-owner-acceptance"],
)
page_router = APIRouter(tags=["industry-analysis-pages"])
_STATIC_DIR = Path(__file__).resolve().parents[2] / "industry_analysis" / "static"
_ALLOWED_SEMANTIC_OPERATIONS = {"none", "reuse_exact_semantic_revision"}


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
    acceptance_view_snapshot_contract_version: str = Field(
        min_length=1,
        max_length=128,
    )
    acceptance_view_snapshot_content_sha256: str = Field(
        min_length=64,
        max_length=64,
    )


class OwnerAcceptanceCommitRequest(OwnerAcceptancePlanRequest):
    preview_fingerprint_sha256: str = Field(min_length=64, max_length=64)


def _http_error(exc: IndustryThesisError) -> HTTPException:
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
        SNAPSHOT_BODY_MISMATCH_CODE,
    }
    recovery = {
        "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE": "重新读取精确审核结果并再次预览。",
        "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED": "返回审核结果，重新确认冻结的研究归属。",
        "INDUSTRY_THESIS_ACCEPTANCE_MAP_REVISION_MISMATCH": "重新打开精确审核结果，不要替换产业地图版本。",
        "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT": "保留填写内容，刷新正式记录后再次预览。",
        "INDUSTRY_THESIS_ACCEPTANCE_STAGE1_BINDINGS_REQUIRED": "补齐精确产业地图断言和研究主张绑定。",
        "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH": "重新确认 supported 后续研究池操作。",
        "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE": "停止使用当前链接并执行本地完整性检查。",
        SNAPSHOT_BODY_MISMATCH_CODE: "保留填写内容并重新读取接受页面，再次预览。",
    }
    status = 404 if code in not_found else 409 if code in conflicts else 422
    detail = getattr(exc, "detail", None)
    message = (
        "接受页面内容已变化，不能使用旧预览提交。"
        if code == SNAPSHOT_BODY_MISMATCH_CODE
        else str(exc)
    )
    return HTTPException(
        status_code=status,
        detail={
            "code": code,
            "message": message,
            "technical_message": detail or str(exc),
            "recovery_action": recovery.get(
                code,
                "检查当前明确选择和精确时间边界后再次预览。",
            ),
            "preserve_form": status in {409, 422, 503},
        },
    )


def _database_failure(message: str) -> HTTPException:
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
    result = payload.model_dump(mode="json")
    result.pop("acceptance_view_snapshot_contract_version", None)
    result.pop("acceptance_view_snapshot_content_sha256", None)
    return result


def _load_view(
    session: Session,
    *,
    session_id: UUID,
    reviewed_session_revision_id: UUID,
    as_of_cutoff: date,
    as_of_recorded_at_utc: datetime,
) -> dict[str, Any]:
    view = IndustryThesisOwnerAcceptanceWorkbenchQueryService(
        session
    ).get_acceptance_view(
        session_id=session_id,
        reviewed_session_revision_id=reviewed_session_revision_id,
        as_of_cutoff=as_of_cutoff,
        as_of_recorded_at_utc=as_of_recorded_at_utc,
    )
    view["information_cutoff_date"] = as_of_cutoff.isoformat()
    view["as_of_cutoff"] = as_of_cutoff.isoformat()
    view["as_of_recorded_at_utc"] = as_of_recorded_at_utc.isoformat()
    view["output_metadata_defaults"] = {
        "output_title": view["thesis_title"],
        "output_scope": view["industry_map"]["scope"],
    }
    view["candidate_pool_operation_contract"]["create_contract"] = {
        "mode": "create_supported_handoff",
        "pool_key": f"industry-thesis-acceptance-v2:{reviewed_session_revision_id}",
        "title_default": f"{view['thesis_title']} · supported 后续研究",
        "scope_default": "仅包含本次接受后 Stage 1 状态为 supported 的精确成员。",
    }
    view["acceptance_view_snapshot_contract_version"] = (
        ACCEPTANCE_VIEW_SNAPSHOT_CONTRACT_VERSION
    )
    view["acceptance_view_snapshot_content_sha256"] = (
        acceptance_view_snapshot_content_sha256(view)
    )
    return view


def _snapshot_body_mismatch() -> IndustryThesisOwnerAcceptanceError:
    return IndustryThesisOwnerAcceptanceError(
        SNAPSHOT_BODY_MISMATCH_CODE,
        "submitted acceptance-view snapshot does not match the authoritative body",
    )


def _validate_route_and_snapshot(
    route_revision_id: UUID,
    payload: OwnerAcceptancePlanRequest,
    view: dict[str, Any],
) -> None:
    if payload.reviewed_session_revision_id != route_revision_id:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE",
            "route reviewed revision does not equal body reviewed revision",
        )
    if (
        payload.acceptance_view_snapshot_contract_version
        != view["acceptance_view_snapshot_contract_version"]
        or payload.acceptance_view_snapshot_content_sha256
        != view["acceptance_view_snapshot_content_sha256"]
    ):
        raise _snapshot_body_mismatch()

    expected = {
        "reviewed_session_revision_id": view.get("reviewed_session_revision_id"),
        "expected_session_latest_revision_number": view.get(
            "expected_session_latest_revision_number"
        ),
        "reviewed_plan_fingerprint_sha256": view.get(
            "reviewed_plan_fingerprint_sha256"
        ),
        "research_case_id": view["owner_context"]["research_case_id"],
        "map_mode": view["owner_context"]["map_mode"],
        "industry_map_id": view["owner_context"]["industry_map_id"],
        "industry_map_revision_id": view["owner_context"][
            "industry_map_revision_id"
        ],
        "information_cutoff_date": view["information_cutoff_date"],
        "owner_acceptance_plan_version": view["owner_acceptance_plan_version"],
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
    if not mismatched:
        return
    if mismatched == ["industry_map_revision_id"]:
        code = "INDUSTRY_THESIS_ACCEPTANCE_MAP_REVISION_MISMATCH"
    elif {
        "research_case_id",
        "map_mode",
        "industry_map_id",
        "industry_map_revision_id",
    }.intersection(mismatched):
        code = "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED"
    else:
        code = "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE"
    raise IndustryThesisOwnerAcceptanceError(
        code,
        "request differs from the exact acceptance view: "
        + ", ".join(sorted(mismatched)),
    )


def _validate_bindings(
    payload: OwnerAcceptancePlanRequest,
    view: dict[str, Any],
) -> None:
    members = {
        member["reviewed_candidate_revision_id"]: member
        for member in view.get("members", [])
    }
    submitted = {
        str(binding.get("reviewed_candidate_revision_id"))
        for binding in payload.candidate_owner_bindings
    }
    if set(members) != submitted:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE",
            "candidate bindings must cover the exact reviewed member set",
        )
    for binding in payload.candidate_owner_bindings:
        member = members[str(binding.get("reviewed_candidate_revision_id"))]
        stage1 = binding.get("stage1")
        if not isinstance(stage1, dict):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE"
            )
        operation = binding.get("stage1_operation")
        matched_reuse = None
        if operation == "reuse_exact_beneficiary_revision":
            matched_reuse = next(
                (
                    option
                    for option in member.get("stage1_reuse_options", [])
                    if option.get("beneficiary_id") == stage1.get("beneficiary_id")
                    and option.get("beneficiary_revision_id")
                    == stage1.get("beneficiary_revision_id")
                    and option.get("stock_basic_record_id")
                    == stage1.get("stock_basic_record_id")
                ),
                None,
            )
            if matched_reuse is None:
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT",
                    "reused Stage 1 revision is outside the exact reviewed context",
                )
        elif operation == "append_beneficiary_revision":
            if not any(
                option.get("beneficiary_id") == stage1.get("beneficiary_id")
                and option.get("expected_latest_revision_id")
                == stage1.get("expected_latest_revision_id")
                and option.get("stock_basic_record_id")
                == stage1.get("stock_basic_record_id")
                for option in member.get("stage1_append_options", [])
            ):
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT",
                    "append target is outside the exact reviewed context",
                )
        elif operation == "create_beneficiary_identity_and_revision":
            contract = member.get("stage1_create_contract") or {}
            if (
                contract.get("available") is not True
                or contract.get("stock_basic_record_id")
                != stage1.get("stock_basic_record_id")
                or contract.get("source") != stage1.get("source")
                or contract.get("stock_code") != stage1.get("stock_code")
            ):
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED",
                    "create target is outside the exact reviewed context",
                )
        else:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE",
                "unsupported Stage 1 operation",
            )

        semantic_operation = binding.get("semantic_operation")
        if semantic_operation not in _ALLOWED_SEMANTIC_OPERATIONS:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_PAYLOAD_INCOMPLETE",
                "ordinary-user acceptance only permits none or exact semantic reuse",
            )
        if semantic_operation == "reuse_exact_semantic_revision":
            if matched_reuse is None:
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_REVISION_MISMATCH"
                )
            semantic = binding.get("semantic") or {}
            if not any(
                item.get("profile_id") == semantic.get("profile_id")
                and item.get("profile_revision_id")
                == semantic.get("profile_revision_id")
                for item in matched_reuse.get("semantic_reuse_options", [])
            ):
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_REVISION_MISMATCH"
                )

    pool = payload.candidate_pool_operation
    mode = pool.get("mode")
    contract = view["candidate_pool_operation_contract"]
    if mode == "append_supported_handoff":
        valid = any(
            option.get("candidate_pool_id") == pool.get("candidate_pool_id")
            and option.get("expected_latest_revision_id")
            == pool.get("expected_latest_revision_id")
            for option in contract.get("append_options", [])
        )
    elif mode == "reuse_exact_supported_handoff":
        valid = any(
            option.get("candidate_pool_id") == pool.get("candidate_pool_id")
            and option.get("candidate_pool_revision_id")
            == pool.get("candidate_pool_revision_id")
            for option in contract.get("reuse_options", [])
        )
    else:
        valid = mode in {
            "create_supported_handoff",
            "none_no_supported_members",
        }
    if not valid:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH",
            "candidate-pool operation is outside the exact reviewed context",
        )


def _result_path(
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


def _resolve_output_revision_id(
    session: Session,
    *,
    session_id: UUID,
    accepted_session_revision_id: UUID,
    as_of_cutoff: date,
    as_of_recorded_at_utc: datetime,
) -> UUID:
    accepted = session.get(
        IndustryThesisSessionRevision,
        accepted_session_revision_id,
    )
    if (
        accepted is None
        or accepted.session_id != session_id
        or accepted.workflow_state != "accepted_outputs_linked"
        or accepted.information_cutoff_date > as_of_cutoff
        or stored_utc(accepted.recorded_at_utc) > as_of_recorded_at_utc
    ):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
            "exact accepted session revision is missing or outside the boundary",
        )
    graph = json_value(accepted.draft_graph_json, "accepted draft graph")
    try:
        return UUID(graph["output_link_revision_id"])
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
        ) from exc


def _compose_result(
    service: IndustryThesisAcceptedOutputQueryService,
    output_revision_id: UUID,
    *,
    session_id: UUID,
    as_of_cutoff: date,
    as_of_recorded_at_utc: datetime,
) -> dict[str, Any]:
    output = service.get_output(
        output_revision_id,
        as_of_cutoff=as_of_cutoff,
        as_of_recorded_at_utc=as_of_recorded_at_utc,
    )
    result = service.get_result(
        output_revision_id,
        as_of_cutoff=as_of_cutoff,
        as_of_recorded_at_utc=as_of_recorded_at_utc,
    )
    readiness = service.get_readiness(
        output_revision_id,
        as_of_cutoff=as_of_cutoff,
        as_of_recorded_at_utc=as_of_recorded_at_utc,
    )
    readiness_by_revision = {
        item["beneficiary_revision_id"]: item for item in readiness["items"]
    }
    for member in result["members"]:
        member["readiness"] = readiness_by_revision[member["beneficiary_revision_id"]]
    supported = [
        member
        for member in result["members"]
        if member["included_in_supported_handoff"]
    ]
    semantic_count = sum(
        member["readiness"]["typed_semantics"]["state"] != "missing"
        for member in result["members"]
    )
    company_count = sum(
        member["readiness"]["company_research"]["state"] != "missing"
        for member in result["members"]
    )
    result.update(
        {
            "session_id": str(session_id),
            "reviewed_session_revision_id": output["reviewed_session_revision_id"],
            "accepted_session_revision_id": output["accepted_session_revision_id"],
            "research_case_id": output["research_case_id"],
            "industry_map_id": output["industry_map_id"],
            "industry_map_revision_id": output["industry_map_revision_id"],
            "supported_handoff_members": supported,
            "semantic_covered_count": semantic_count,
            "company_research_ready_count": company_count,
            "largest_missing_prerequisite": (
                "部分成员尚未建立精确候选池归属的 Company Research"
                if company_count < len(result["members"])
                else "部分成员尚未绑定类型化语义"
                if semantic_count < len(result["members"])
                else "暂无"
            ),
            "facts": [
                {"label": "完整成员", "value": len(result["members"])},
                {"label": "supported 后续研究", "value": len(supported)},
                {
                    "label": "类型化语义覆盖",
                    "value": f"{semantic_count}/{len(result['members'])}",
                },
                {
                    "label": "Company Research 已存在",
                    "value": f"{company_count}/{len(result['members'])}",
                },
                {"label": "研究用途", "value": "不构成投资建议"},
            ],
            "technical_details": output,
        }
    )
    return result


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
            return _load_view(
                session,
                session_id=session_id,
                reviewed_session_revision_id=reviewed_session_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
    except IndustryThesisError as exc:
        raise _http_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_failure("研究成果接受准备读取失败。") from exc


async def _preview_or_commit(
    *,
    reviewed_session_revision_id: UUID,
    request: Request,
    session_id: UUID,
    as_of_cutoff: date,
    as_of_recorded_at_utc: datetime,
    read_factory: sessionmaker[Session],
    write_factory: sessionmaker[Session],
    commit: bool,
) -> dict[str, Any]:
    model = OwnerAcceptanceCommitRequest if commit else OwnerAcceptancePlanRequest
    payload = await _validated_json_body(request, model)
    try:
        with read_factory() as session:
            view = _load_view(
                session,
                session_id=session_id,
                reviewed_session_revision_id=reviewed_session_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
        _validate_route_and_snapshot(reviewed_session_revision_id, payload, view)
        _validate_bindings(payload, view)
        service = IndustryThesisOwnerAcceptanceService(write_factory)
        result = (
            service.commit(_raw_plan(payload))
            if commit
            else service.preview(_raw_plan(payload))
        )
        result["acceptance_view_snapshot_contract_version"] = view[
            "acceptance_view_snapshot_contract_version"
        ]
        result["acceptance_view_snapshot_content_sha256"] = view[
            "acceptance_view_snapshot_content_sha256"
        ]
        if not commit:
            result["primary_action"] = (
                {"kind": "commit", "label": "确认接受研究成果"}
                if result.get("commit_ready")
                else {"kind": "correct", "label": "检查并修正接受字段"}
            )
            return result
        accepted_id = result.get("accepted_session_revision_id")
        if not accepted_id:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "commit did not return an accepted session revision",
            )
        result["accepted_result_path"] = _result_path(
            session_id=str(session_id),
            accepted_session_revision_id=accepted_id,
            information_cutoff_date=payload.information_cutoff_date.isoformat(),
            recorded_at_utc=result["recorded_at_utc"],
        )
        result["history_path"] = "/industry-analysis"
        return result
    except IndustryThesisError as exc:
        raise _http_error(exc) from exc
    except SQLAlchemyError as exc:
        message = (
            "研究成果提交失败，请重新打开精确结果确认是否已经写入。"
            if commit
            else "研究成果预览失败。"
        )
        raise _database_failure(message) from exc


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
    return await _preview_or_commit(
        reviewed_session_revision_id=reviewed_session_revision_id,
        request=request,
        session_id=session_id,
        as_of_cutoff=as_of_cutoff,
        as_of_recorded_at_utc=as_of_recorded_at_utc,
        read_factory=read_factory,
        write_factory=write_factory,
        commit=False,
    )


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
    return await _preview_or_commit(
        reviewed_session_revision_id=reviewed_session_revision_id,
        request=request,
        session_id=session_id,
        as_of_cutoff=as_of_cutoff,
        as_of_recorded_at_utc=as_of_recorded_at_utc,
        read_factory=read_factory,
        write_factory=write_factory,
        commit=True,
    )


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
            output_revision_id = _resolve_output_revision_id(
                session,
                session_id=session_id,
                accepted_session_revision_id=accepted_session_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
            return _compose_result(
                IndustryThesisAcceptedOutputQueryService(session),
                output_revision_id,
                session_id=session_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
    except IndustryThesisError as exc:
        raise _http_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_failure("已接受研究成果读取失败。") from exc
