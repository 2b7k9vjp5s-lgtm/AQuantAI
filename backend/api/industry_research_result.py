"""Read-only API for accepted industry research result assembly."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.api.industry_analysis import get_industry_analysis_session_factory
from industry_alpha.industry_research_result_query import (
    DEFAULT_OPTION_LIMIT,
    MAX_OPTION_LIMIT,
    IndustryResearchResultError,
    IndustryResearchResultQueryService,
)
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    IndustryThesisOwnerAcceptanceError,
)

router = APIRouter(
    prefix="/industry-analysis/api",
    tags=["industry-research-result"],
)


def _boundary(cutoff: date, value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "industry_research_result_boundary_invalid",
                "message": "记录时间必须是明确的 UTC 时间。",
                "recovery_action": "请从精确研究历史重新打开结果。",
            },
        )
    result = value.astimezone(timezone.utc)
    if cutoff > result.date():
        raise HTTPException(
            status_code=422,
            detail={
                "code": "industry_research_result_boundary_invalid",
                "message": "信息截止日不能晚于记录时间。",
                "recovery_action": "请检查双时间边界。",
            },
        )
    return result


def _domain_error(exc: RuntimeError) -> HTTPException:
    code = getattr(exc, "code", "industry_research_result_unavailable")
    return HTTPException(
        status_code=409,
        detail={
            "code": code,
            "message": str(exc),
            "technical_message": str(exc),
            "recovery_action": "保留精确 accepted 结果，移除无效候选快照或重新打开本地历史。",
        },
    )


@router.get("/output-link-revisions/{output_link_revision_id}/assembled-result")
def get_assembled_industry_research_result(
    output_link_revision_id: UUID,
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    investment_candidate_snapshot_revision_id: UUID | None = Query(default=None),
    option_limit: int = Query(
        default=DEFAULT_OPTION_LIMIT,
        ge=1,
        le=MAX_OPTION_LIMIT,
    ),
    session_factory: sessionmaker[Session] = Depends(
        get_industry_analysis_session_factory
    ),
) -> dict[str, Any]:
    boundary = _boundary(as_of_cutoff, as_of_recorded_at_utc)
    try:
        with session_factory() as session:
            return IndustryResearchResultQueryService(session).get_assembled_result(
                output_link_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=boundary,
                investment_candidate_snapshot_revision_id=(
                    investment_candidate_snapshot_revision_id
                ),
                option_limit=option_limit,
            )
    except (IndustryResearchResultError, IndustryThesisOwnerAcceptanceError) as exc:
        raise _domain_error(exc) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "industry_research_result_database_unavailable",
                "message": "本地研究成果读取失败。",
                "technical_message": "local database query failed",
                "recovery_action": "检查本地数据库和迁移后手动重试。",
            },
        ) from exc
