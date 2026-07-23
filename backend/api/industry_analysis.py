"""Thin local JSON adapter for the Personal Research Workbench UI Phase 1A."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from industry_alpha.industry_thesis_workbench import (
    IndustryThesisWorkbenchError,
    IndustryThesisWorkbenchQueryService,
    validate_workbench_boundary,
)

router = APIRouter(prefix="/industry-analysis/api", tags=["industry-analysis"])

_MODULES = (
    {
        "key": "today-market",
        "label": "今日市场",
        "state": "future",
        "path": None,
    },
    {
        "key": "industry-analysis",
        "label": "产业研究",
        "state": "active",
        "path": "/industry-analysis",
    },
    {
        "key": "follow-track",
        "label": "关注与跟踪",
        "state": "future",
        "path": None,
    },
    {
        "key": "research-portfolio",
        "label": "研究组合",
        "state": "future",
        "path": None,
    },
    {
        "key": "settings",
        "label": "系统设置",
        "state": "active",
        "path": "/workbench/settings",
    },
)


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


@router.get("/bootstrap")
def get_workbench_bootstrap() -> dict:
    """Return deterministic shell capabilities without creating product state."""

    return {
        "product": "AQuantAI",
        "surface": "personal_research_workbench",
        "phase": "ui_phase_1a",
        "language": "zh-CN",
        "database_available": _database_available(),
        "modules": list(_MODULES),
        "capabilities": {
            "thesis_history": True,
            "scope_entry_preview": True,
            "session_write": False,
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
    """Validate boundaries before constructing local database resources."""

    try:
        validate_workbench_boundary(as_of_cutoff, as_of_recorded_at_utc)
    except IndustryThesisWorkbenchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        engine = build_engine()
    except (RuntimeError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "industry_analysis_database_unavailable",
                "message": (
                    "产业研究数据库不可用，请检查本地数据库配置和迁移状态。"
                ),
            },
        ) from exc
    try:
        yield build_session_factory(engine)
    finally:
        engine.dispose()


@router.get("/sessions")
def list_industry_thesis_sessions(
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    limit: int = Query(default=50, ge=1, le=100),
    session_factory: sessionmaker[Session] = Depends(
        get_industry_analysis_session_factory
    ),
) -> dict:
    """Return a bounded deterministic history under explicit dual-as-of boundaries."""

    try:
        boundary = validate_workbench_boundary(
            as_of_cutoff,
            as_of_recorded_at_utc,
        )
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
                "message": (
                    "产业研究历史读取失败，请检查本地数据库和迁移状态。"
                ),
            },
        ) from exc
