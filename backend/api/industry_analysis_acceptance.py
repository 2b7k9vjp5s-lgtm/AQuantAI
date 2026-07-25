"""Local ordinary-user API and pages for Industry Thesis owner acceptance."""

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
from industry_alpha.industry_thesis_owner_acceptance import (
    IndustryThesisOwnerAcceptanceService,
)
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    IndustryThesisOwnerAcceptanceError,
)
from industry_alpha.industry_thesis_owner_acceptance_workbench import (
    IndustryThesisOwnerAcceptanceWorkbenchQueryService,
)
from industry_alpha.industry_thesis_rules import IndustryThesisError


api_router = APIRouter(tags=["industry-analysis-owner-acceptance"])
page_router = APIRouter(tags=["industry-analysis-pages"])
_STATIC_DIR = Path(__file__).resolve().parents[2] / "industry_analysis" / "static"


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
            return IndustryThesisOwnerAcceptanceWorkbenchQueryService(
                session
            ).get_acceptance_view(
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
        with read_factory() as session:
            IndustryThesisOwnerAcceptanceWorkbenchQueryService(
                session
            ).get_acceptance_view(
                session_id=session_id,
                reviewed_session_revision_id=reviewed_session_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
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
        with read_factory() as session:
            IndustryThesisOwnerAcceptanceWorkbenchQueryService(
                session
            ).get_acceptance_view(
                session_id=session_id,
                reviewed_session_revision_id=reviewed_session_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
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
            return IndustryThesisOwnerAcceptanceWorkbenchQueryService(
                session
            ).get_accepted_result_view(
                session_id=session_id,
                accepted_session_revision_id=accepted_session_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
    except IndustryThesisError as exc:
        raise _acceptance_http_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_failure("已接受研究成果读取失败。", exc) from exc
