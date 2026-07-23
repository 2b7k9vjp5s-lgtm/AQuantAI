"""Isolated local web adapters for Personal Research Workbench UI Phase 1C/1D."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.api.industry_analysis import (
    _validated_json_body,
    get_industry_analysis_session_factory,
    get_industry_analysis_write_factory,
)
from industry_alpha.industry_thesis_candidate_workbench import (
    IndustryThesisCandidateWorkbenchService,
    IndustryThesisWorkbenchCandidateCommandService,
)
from industry_alpha.industry_thesis_query import IndustryThesisQueryService
from industry_alpha.industry_thesis_rules import IndustryThesisError, IndustryThesisNotFound

api_router = APIRouter(prefix="/industry-analysis/api", tags=["industry-analysis-candidates"])
page_router = APIRouter(tags=["industry-analysis-pages"])
_STATIC_DIR = Path(__file__).resolve().parents[2] / "industry_analysis" / "static"


class CandidateBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_session_latest_revision_number: int
    selected_candidate_pool_revision_ids: list[UUID]


def _candidate_http_error(exc: IndustryThesisError) -> HTTPException:
    not_found = {
        "industry_thesis_session_not_found",
        "industry_thesis_session_revision_not_found",
        "industry_thesis_source_not_found",
        "industry_thesis_identity_not_found",
        "industry_thesis_not_visible",
    }
    conflicts = {
        "industry_thesis_revision_conflict",
        "industry_thesis_duplicate_source",
        "industry_thesis_no_change",
        "industry_thesis_chronology_invalid",
    }
    chinese = {
        "industry_thesis_session_not_found": "未找到精确的本地研究记录。",
        "industry_thesis_session_revision_not_found": "未找到与当前链接匹配的精确研究修订。",
        "industry_thesis_not_visible": "该记录不在当前数据边界内。",
        "industry_thesis_source_not_found": "未找到精确的候选来源记录。",
        "industry_thesis_identity_not_found": "未找到精确的公司身份记录。",
        "industry_thesis_revision_conflict": "研究版本已变化，请重新打开精确页面后再确认。",
        "industry_thesis_duplicate_source": "候选来源重复，未执行写入。",
        "industry_thesis_workflow_invalid": "当前研究修订尚未准备好构建候选池。",
        "industry_thesis_source_required": "请至少保留一个精确公司种子，或明确选择一个冻结候选池修订。",
        "industry_thesis_source_invalid": "候选来源与已保存的精确范围不匹配。",
        "industry_thesis_graph_incomplete": "本地候选来源图不完整，无法安全继续。",
        "industry_thesis_later_information": "候选来源超出了当前数据边界。",
        "industry_thesis_identity_invalid": "候选公司的精确身份绑定无效。",
        "industry_thesis_unknown_field": "请求包含未授权字段。",
        "industry_thesis_input_invalid": "候选构建请求字段或类型无效。",
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
            "message": chinese.get(exc.code, "候选池处理失败，请检查精确来源后重试。"),
            "technical_message": str(exc),
        },
    )


def _database_failure(message: str, exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "industry_analysis_candidate_database_unavailable",
            "message": message,
        },
    )


def _review_path(
    *,
    session_id: str,
    session_revision_id: str,
    as_of_cutoff: str,
    as_of_recorded_at_utc: str,
) -> str:
    query = urlencode(
        {
            "as_of_cutoff": as_of_cutoff,
            "as_of_recorded_at_utc": as_of_recorded_at_utc,
        }
    )
    return (
        f"/industry-analysis/sessions/{session_id}/revisions/"
        f"{session_revision_id}/review?{query}"
    )


def _reject_multiple_contributing_pools_per_map(command: dict) -> None:
    pools_by_map: dict[str, set[str]] = {}
    for proposal in command.get("proposals", []):
        if proposal.get("source_kind") != "existing_industry_map_revision":
            continue
        reference = proposal.get("source_reference")
        if not isinstance(reference, dict):
            continue
        map_revision_id = reference.get("industry_map_revision_id")
        pool_revision_id = reference.get("candidate_pool_revision_id")
        if map_revision_id is None or pool_revision_id is None:
            continue
        pools_by_map.setdefault(str(map_revision_id), set()).add(str(pool_revision_id))
    if any(len(pool_ids) > 1 for pool_ids in pools_by_map.values()):
        raise IndustryThesisError(
            "industry_thesis_duplicate_source",
            "one candidate build may use at most one contributing frozen pool revision per exact map",
        )


@page_router.get(
    "/industry-analysis/sessions/{session_id}/revisions/{session_revision_id}/review",
    include_in_schema=False,
)
def candidate_review_page(session_id: UUID, session_revision_id: UUID) -> FileResponse:
    """Serve one exact candidate-build/complete-universe page."""

    del session_id, session_revision_id
    return FileResponse(_STATIC_DIR / "candidate_review.html", media_type="text/html")


@api_router.get("/session-revisions/{session_revision_id}/candidate-source-options")
def get_candidate_source_options(
    session_revision_id: UUID,
    session_id: UUID = Query(),
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(get_industry_analysis_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return IndustryThesisCandidateWorkbenchService(session).candidate_source_options(
                session_id=session_id,
                session_revision_id=session_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
    except IndustryThesisError as exc:
        raise _candidate_http_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_failure("候选来源读取失败，请检查本地数据库和迁移状态。", exc) from exc


@api_router.get("/session-revisions/{session_revision_id}/candidates")
def get_complete_candidate_universe(
    session_revision_id: UUID,
    session_id: UUID = Query(),
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(get_industry_analysis_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            result = IndustryThesisQueryService(session).list_candidate_revisions(
                session_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
        if result["session_id"] != str(session_id):
            raise IndustryThesisError(
                "industry_thesis_session_revision_not_found",
                "exact route-owned session revision was not found",
            )
        result["as_of_cutoff"] = as_of_cutoff.isoformat()
        result["as_of_recorded_at_utc"] = as_of_recorded_at_utc.isoformat()
        result["universe_label"] = "当前已构建本地范围全量候选"
        result["review_enabled"] = result["candidate_count"] > 0
        result["review_phase"] = "Phase 1D"
        result["review_path"] = _review_path(
            session_id=str(session_id),
            session_revision_id=str(session_revision_id),
            as_of_cutoff=as_of_cutoff.isoformat(),
            as_of_recorded_at_utc=as_of_recorded_at_utc.isoformat(),
        )
        return result
    except IndustryThesisError as exc:
        raise _candidate_http_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_failure("完整候选池读取失败，请检查本地数据库和迁移状态。", exc) from exc


@api_router.post("/session-revisions/{session_revision_id}/candidate-builds")
async def build_candidate_universe(
    session_revision_id: UUID,
    request: Request,
    session_id: UUID = Query(),
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    dry_run: bool = Query(default=True),
    read_factory: sessionmaker[Session] = Depends(get_industry_analysis_session_factory),
    write_factory: sessionmaker[Session] = Depends(get_industry_analysis_write_factory),
) -> dict:
    payload = await _validated_json_body(request, CandidateBuildRequest)
    try:
        with read_factory() as session:
            command, composition = IndustryThesisCandidateWorkbenchService(
                session
            ).compose_candidate_build(
                session_id=session_id,
                session_revision_id=session_revision_id,
                expected_session_latest_revision_number=(
                    payload.expected_session_latest_revision_number
                ),
                selected_candidate_pool_revision_ids=(
                    payload.selected_candidate_pool_revision_ids
                ),
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
        _reject_multiple_contributing_pools_per_map(command)
        result = IndustryThesisWorkbenchCandidateCommandService(
            write_factory
        ).build_candidates(command, dry_run=dry_run)
        result["composition"] = composition
        result["universe_label"] = "当前已构建本地范围全量候选"
        result["review_enabled"] = (not dry_run) and result["candidate_count"] > 0
        result["review_phase"] = "Phase 1D"
        result["review_path"] = _review_path(
            session_id=result["session_id"],
            session_revision_id=result["session_revision_id"],
            as_of_cutoff=result["information_cutoff_date"],
            as_of_recorded_at_utc=result["recorded_at_utc"],
        )
        return result
    except IndustryThesisError as exc:
        raise _candidate_http_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_failure("候选池写入失败，请先回到精确页面确认是否已写入。", exc) from exc
