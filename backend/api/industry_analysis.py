"""Local JSON adapter for Personal Research Workbench UI Phase 1B."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from typing import Any, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from industry_alpha.industry_thesis_rules import (
    IndustryThesisError,
    IndustryThesisNotFound,
)
from industry_alpha.industry_thesis_service import (
    IndustryThesisCommandService,
    IndustryThesisQueryService,
)
from industry_alpha.industry_thesis_workbench import (
    IndustryThesisWorkbenchError,
    IndustryThesisWorkbenchQueryService,
    validate_workbench_boundary,
)

router = APIRouter(
    prefix="/industry-analysis/api",
    tags=["industry-analysis"],
)

_MAX_BODY_BYTES = 1_048_576
_Model = TypeVar("_Model", bound=BaseModel)

_MODULES = (
    {"key": "today-market", "label": "今日市场", "state": "future", "path": None},
    {"key": "industry-analysis", "label": "产业研究", "state": "active", "path": "/industry-analysis"},
    {"key": "follow-track", "label": "关注与跟踪", "state": "future", "path": None},
    {"key": "research-portfolio", "label": "研究组合", "state": "future", "path": None},
    {"key": "settings", "label": "系统设置", "state": "active", "path": "/workbench/settings"},
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MarketScopeRequest(_StrictModel):
    market_namespace: str
    exchange_namespace: str | None = None
    security_type: str
    include_status: str
    listed_instrument_ids: list[UUID]


class SessionPayloadRequest(_StrictModel):
    thesis_text_original: str
    thesis_title_reviewed: str | None = None
    driver_type: str
    analysis_horizon_kind: str
    analysis_start_date: date | None = None
    analysis_end_date: date | None = None
    market_scope: list[MarketScopeRequest]
    chain_boundary: Any
    exclusions: Any
    seed_companies: Any
    seed_products: Any
    seed_technologies: Any
    seed_bottlenecks: Any
    draft_graph: Any
    coverage_state: str
    workflow_state: str
    information_cutoff_date: date
    revision_note: str


class SessionPatchRequest(_StrictModel):
    thesis_text_original: str | None = None
    thesis_title_reviewed: str | None = None
    driver_type: str | None = None
    analysis_horizon_kind: str | None = None
    analysis_start_date: date | None = None
    analysis_end_date: date | None = None
    market_scope: list[MarketScopeRequest] | None = None
    chain_boundary: Any | None = None
    exclusions: Any | None = None
    seed_companies: Any | None = None
    seed_products: Any | None = None
    seed_technologies: Any | None = None
    seed_bottlenecks: Any | None = None
    draft_graph: Any | None = None
    coverage_state: str | None = None
    workflow_state: str | None = None
    information_cutoff_date: date | None = None


class SessionRevisionRequest(_StrictModel):
    expected_latest_revision_number: int
    changes: SessionPatchRequest
    revision_note: str


def _database_available() -> bool:
    engine = None
    try:
        engine = build_engine()
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        return True
    except (RuntimeError, SQLAlchemyError):
        return False
    finally:
        if engine is not None:
            engine.dispose()


def _database_unavailable(_exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "industry_analysis_database_unavailable",
            "message": "产业研究数据库不可用，请检查本地数据库配置和迁移状态。",
        },
    )


def _domain_http_error(exc: IndustryThesisError) -> HTTPException:
    not_found = {
        "industry_thesis_session_not_found",
        "industry_thesis_session_revision_not_found",
        "industry_thesis_not_visible",
    }
    conflicts = {
        "industry_thesis_revision_conflict",
        "industry_thesis_no_change",
        "industry_thesis_chronology_invalid",
    }
    chinese = {
        "industry_thesis_session_not_found": "未找到精确的本地研究记录。",
        "industry_thesis_session_revision_not_found": "未找到精确的研究修订。",
        "industry_thesis_not_visible": "该研究修订不在当前数据边界内。",
        "industry_thesis_revision_conflict": "研究状态已变化，请重新读取后再确认。",
        "industry_thesis_no_change": "研究范围没有发生可记录的变化。",
        "industry_thesis_chronology_invalid": "信息截止日或修订时间不能向后移动。",
        "industry_thesis_unknown_field": "请求包含未授权字段。",
        "industry_thesis_market_scope_required": "请明确确认至少一个市场范围。",
        "industry_thesis_graph_incomplete": "本地研究历史不完整，无法安全继续。",
    }
    if isinstance(exc, IndustryThesisNotFound) or exc.code in not_found:
        status = 404
    elif exc.code in conflicts:
        status = 409
    else:
        status = 422
    return HTTPException(
        status_code=status,
        detail={
            "code": exc.code,
            "message": chinese.get(exc.code, "研究范围校验失败，请检查输入后重试。"),
            "technical_message": str(exc),
        },
    )


async def _validated_json_body(request: Request, model: type[_Model]) -> _Model:
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type.lower():
        raise HTTPException(
            status_code=400,
            detail={
                "code": "industry_analysis_json_required",
                "message": "请求必须使用 application/json。",
            },
        )
    body = await request.body()
    if len(body) > _MAX_BODY_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "industry_analysis_body_too_large",
                "message": "请求内容超过 1 MiB 限制。",
            },
        )
    try:
        return model.model_validate_json(body)
    except ValidationError as exc:
        if any(error.get("type") == "json_invalid" for error in exc.errors()):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "industry_analysis_json_invalid",
                    "message": "请求不是有效 JSON。",
                },
            ) from exc
        raise HTTPException(
            status_code=422,
            detail={
                "code": "industry_analysis_request_invalid",
                "message": "请求字段或类型不符合研究范围契约。",
                "error_count": exc.error_count(),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "industry_analysis_json_invalid",
                "message": "请求不是有效 JSON。",
            },
        ) from exc


@router.get("/bootstrap")
def get_workbench_bootstrap() -> dict:
    return {
        "product": "AQuantAI",
        "surface": "personal_research_workbench",
        "phase": "ui_phase_1b",
        "language": "zh-CN",
        "database_available": _database_available(),
        "modules": list(_MODULES),
        "capabilities": {
            "thesis_history": True,
            "scope_entry_preview": False,
            "local_option_reads": True,
            "session_write": True,
            "session_revision_write": True,
            "candidate_build": False,
            "candidate_review": False,
            "accepted_output_write": False,
            "network_acquisition": False,
            "ai_assistance": False,
            "portfolio": False,
            "trading": False,
        },
        "notices": {
            "local_first": True,
            "research_only": True,
            "not_investment_advice": True,
        },
    }


def get_industry_analysis_session_factory(
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
) -> Iterator[sessionmaker[Session]]:
    try:
        validate_workbench_boundary(as_of_cutoff, as_of_recorded_at_utc)
    except IndustryThesisWorkbenchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    engine = None
    try:
        engine = build_engine()
        yield build_session_factory(engine)
    except (RuntimeError, SQLAlchemyError) as exc:
        raise _database_unavailable(exc) from exc
    finally:
        if engine is not None:
            engine.dispose()


def get_industry_analysis_write_factory() -> Iterator[sessionmaker[Session]]:
    engine = None
    try:
        engine = build_engine()
        yield build_session_factory(engine)
    except (RuntimeError, SQLAlchemyError) as exc:
        raise _database_unavailable(exc) from exc
    finally:
        if engine is not None:
            engine.dispose()


@router.get("/sessions")
def list_industry_thesis_sessions(
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    limit: int = Query(default=50, ge=1, le=100),
    session_factory: sessionmaker[Session] = Depends(get_industry_analysis_session_factory),
) -> dict:
    try:
        boundary = validate_workbench_boundary(as_of_cutoff, as_of_recorded_at_utc)
        with session_factory() as session:
            return IndustryThesisWorkbenchQueryService(session).list_sessions(
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=boundary,
                limit=limit,
            )
    except IndustryThesisWorkbenchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "industry_analysis_query_failed",
                "message": "产业研究历史读取失败，请检查本地数据库和迁移状态。",
            },
        ) from exc


@router.get("/local-options/maps")
def list_local_map_options(
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=20, ge=1, le=20),
    session_factory: sessionmaker[Session] = Depends(get_industry_analysis_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return IndustryThesisWorkbenchQueryService(session).list_map_options(
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
                query=q,
                limit=limit,
            )
    except IndustryThesisWorkbenchError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "industry_analysis_option_query_invalid", "message": str(exc)},
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "industry_analysis_option_query_failed", "message": "本地产业地图读取失败。"},
        ) from exc


@router.get("/local-options/companies")
def list_local_company_options(
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    q: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=20, ge=1, le=20),
    session_factory: sessionmaker[Session] = Depends(get_industry_analysis_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return IndustryThesisWorkbenchQueryService(session).list_company_options(
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
                query=q,
                limit=limit,
            )
    except IndustryThesisWorkbenchError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "industry_analysis_option_query_invalid", "message": str(exc)},
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "industry_analysis_option_query_failed", "message": "本地公司身份读取失败。"},
        ) from exc


@router.get("/session-revisions/{session_revision_id}")
def get_exact_session_revision(
    session_revision_id: UUID,
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(get_industry_analysis_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return IndustryThesisQueryService(session).get_session_revision(
                session_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
    except IndustryThesisError as exc:
        raise _domain_http_error(exc) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "industry_analysis_query_failed", "message": "精确研究修订读取失败。"},
        ) from exc


def _edit_scope_path(result: dict) -> str | None:
    if result["session_revision_id"] is None:
        return None
    return (
        "/industry-analysis/new"
        f"?session_id={result['session_id']}"
        f"&session_revision_id={result['session_revision_id']}"
        f"&revision_number={result['revision_number']}"
        f"&as_of_cutoff={result['information_cutoff_date']}"
        f"&as_of_recorded_at_utc={result['recorded_at_utc']}"
    )


@router.post("/sessions")
async def create_industry_thesis_session(
    request: Request,
    dry_run: bool = Query(default=True),
    session_factory: sessionmaker[Session] = Depends(get_industry_analysis_write_factory),
) -> dict:
    payload = await _validated_json_body(request, SessionPayloadRequest)
    try:
        result = IndustryThesisCommandService(session_factory).create_session(
            payload.model_dump(mode="json"),
            dry_run=dry_run,
        )
    except IndustryThesisError as exc:
        raise _domain_http_error(exc) from exc
    result["history_path"] = "/industry-analysis"
    result["edit_scope_path"] = _edit_scope_path(result)
    return result


@router.post("/sessions/{session_id}/revisions")
async def revise_industry_thesis_session(
    session_id: UUID,
    request: Request,
    dry_run: bool = Query(default=True),
    session_factory: sessionmaker[Session] = Depends(get_industry_analysis_write_factory),
) -> dict:
    payload = await _validated_json_body(request, SessionRevisionRequest)
    raw = {
        "session_id": str(session_id),
        "expected_latest_revision_number": payload.expected_latest_revision_number,
        "changes": payload.changes.model_dump(mode="json", exclude_unset=True),
        "revision_note": payload.revision_note,
    }
    try:
        result = IndustryThesisCommandService(session_factory).revise_session(
            raw,
            dry_run=dry_run,
        )
    except IndustryThesisError as exc:
        raise _domain_http_error(exc) from exc
    result["history_path"] = "/industry-analysis"
    result["edit_scope_path"] = _edit_scope_path(result)
    return result
