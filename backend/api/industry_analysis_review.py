"""Thin local web adapters for Industry Thesis review and exact result."""

from __future__ import annotations

import base64
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.api.industry_analysis import (
    _validated_json_body,
    get_industry_analysis_session_factory,
    get_industry_analysis_write_factory,
)
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.industry_thesis_models import (
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_review import (
    ACCEPTANCE_PLAN_VERSION,
    IndustryThesisProposalReviewService,
    IndustryThesisReviewedPlanQueryService,
)
from industry_alpha.industry_thesis_review_workbench import (
    IndustryThesisReviewWorkbenchQueryService,
)
from industry_alpha.industry_thesis_rules import (
    IndustryThesisError,
    IndustryThesisNotFound,
    stored_utc,
)
from industry_alpha.models import ResearchCase

api_router = APIRouter(prefix="/industry-analysis/api", tags=["industry-analysis-review"])
page_router = APIRouter(tags=["industry-analysis-pages"])
_STATIC_DIR = Path(__file__).resolve().parents[2] / "industry_analysis" / "static"

DecisionValue = Literal[
    "selected_for_acceptance",
    "rejected_by_user",
    "unresolved",
]
ExposureValue = Literal["direct", "conditional", "indirect", "conceptual"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OwnerContextRequest(_StrictModel):
    industry_map_revision_id: UUID


class ReviewDecisionRequest(_StrictModel):
    candidate_revision_id: UUID
    expected_latest_revision_number: int = Field(ge=1)
    decision: DecisionValue
    final_proposed_exposure_type: ExposureValue | None = None
    rationale_text: str = Field(min_length=1, max_length=2000)
    uncertainty_state: str = Field(min_length=1, max_length=64)
    uncertainty_note: str = Field(min_length=1, max_length=2000)


class ReviewRequest(_StrictModel):
    expected_session_latest_revision_number: int = Field(ge=1)
    acceptance_plan_version: str = Field(min_length=1, max_length=128)
    owner_context: OwnerContextRequest
    decisions: list[ReviewDecisionRequest] = Field(min_length=1)
    revision_note: str = Field(min_length=1, max_length=1000)


def _review_http_error(exc: IndustryThesisError) -> HTTPException:
    not_found = {
        "industry_thesis_session_not_found",
        "industry_thesis_session_revision_not_found",
        "industry_thesis_candidate_revision_not_found",
        "industry_thesis_identity_not_found",
        "industry_thesis_not_visible",
    }
    conflicts = {
        "industry_thesis_revision_conflict",
        "industry_thesis_review_stale_universe",
        "industry_thesis_duplicate_review",
        "industry_thesis_duplicate_selected_identity",
        "industry_thesis_chronology_invalid",
    }
    chinese = {
        "industry_thesis_session_not_found": "未找到精确的本地研究记录。",
        "industry_thesis_session_revision_not_found": "未找到与当前链接匹配的精确研究修订。",
        "industry_thesis_candidate_revision_not_found": "未找到精确的候选修订。",
        "industry_thesis_not_visible": "审阅记录不在当前数据边界内。",
        "industry_thesis_revision_conflict": "研究或候选版本已变化，请保留当前选择并重新读取后确认。",
        "industry_thesis_review_stale_universe": "候选池已变化，必须重新打开完整候选池后审阅。",
        "industry_thesis_review_incomplete": "每条完整候选路径都必须明确选择一个审阅状态。",
        "industry_thesis_review_invalid": "审阅状态、研究归属、暴露类型、理由或不确定性不符合要求。",
        "industry_thesis_owner_context_invalid": "请选择一个当前数据边界内的精确研究案例与产业地图版本。",
        "industry_thesis_duplicate_review": "同一候选不能在一次审阅中重复提交。",
        "industry_thesis_duplicate_selected_identity": "多个纳入项指向同一正式公司身份，请保留不同来源但只纳入其中一条。",
        "industry_thesis_identity_invalid": "纳入后续研究需要唯一且已接受的精确公司身份。",
        "industry_thesis_identity_not_found": "精确公司身份已不可用。",
        "industry_thesis_graph_incomplete": "本地审阅图不完整，无法安全继续。",
        "industry_thesis_input_invalid": "审阅请求字段、版本或时间边界无效。",
        "industry_thesis_unknown_field": "请求包含未授权字段。",
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
            "message": chinese.get(exc.code, "审阅处理失败，请检查完整候选后重试。"),
            "technical_message": str(exc),
        },
    )


def _database_failure(message: str, exc: Exception) -> HTTPException:
    del exc
    return HTTPException(
        status_code=503,
        detail={
            "code": "industry_analysis_review_database_unavailable",
            "message": message,
        },
    )


def _result_path(
    *,
    session_id: str,
    reviewed_session_revision_id: str,
    information_cutoff_date: str,
    complete_recorded_at_utc: str,
) -> str:
    query = urlencode(
        {
            "as_of_cutoff": information_cutoff_date,
            "as_of_recorded_at_utc": complete_recorded_at_utc,
        }
    )
    return (
        f"/industry-analysis/sessions/{session_id}/revisions/"
        f"{reviewed_session_revision_id}/result?{query}"
    )


def _normalized_command(
    *,
    session_revision_id: UUID,
    payload: ReviewRequest,
) -> dict:
    decisions: list[dict] = []
    for index, item in enumerate(payload.decisions):
        rationale = item.rationale_text.strip()
        uncertainty_state = item.uncertainty_state.strip()
        uncertainty_note = item.uncertainty_note.strip()
        if not rationale or not uncertainty_state or not uncertainty_note:
            raise IndustryThesisError(
                "industry_thesis_review_invalid",
                f"decision {index} requires explicit rationale and uncertainty",
            )
        if item.decision == "selected_for_acceptance":
            if item.final_proposed_exposure_type is None:
                raise IndustryThesisError(
                    "industry_thesis_review_invalid",
                    "selected candidates require an explicit final exposure type",
                )
        elif item.final_proposed_exposure_type is not None:
            raise IndustryThesisError(
                "industry_thesis_review_invalid",
                "only selected candidates may set a final exposure type",
            )
        decisions.append(
            {
                "candidate_revision_id": str(item.candidate_revision_id),
                "expected_latest_revision_number": item.expected_latest_revision_number,
                "decision": item.decision,
                "final_proposed_exposure_type": item.final_proposed_exposure_type,
                "rationale": {"user_review_rationale": rationale},
                "uncertainty": {
                    "state": uncertainty_state,
                    "note": uncertainty_note,
                },
            }
        )
    return {
        "session_revision_id": str(session_revision_id),
        "expected_session_latest_revision_number": (
            payload.expected_session_latest_revision_number
        ),
        "acceptance_plan_version": payload.acceptance_plan_version,
        "owner_context": {
            "industry_map_revision_id": str(
                payload.owner_context.industry_map_revision_id
            )
        },
        "decisions": decisions,
        "revision_note": payload.revision_note.strip(),
    }


def _explicit_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "as_of_recorded_at_utc must be explicit UTC",
        )
    return value.astimezone(timezone.utc)


def _decode_context_cursor(value: str | None) -> tuple[str, str, int, UUID] | None:
    if value is None:
        return None
    try:
        padding = "=" * (-len(value) % 4)
        raw = json.loads(base64.urlsafe_b64decode(value + padding).decode("utf-8"))
        if not isinstance(raw, list) or len(raw) != 4:
            raise ValueError("invalid cursor shape")
        return str(raw[0]), str(raw[1]), int(raw[2]), UUID(str(raw[3]))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "owner-context cursor is invalid",
        ) from exc


def _encode_context_cursor(value: tuple[str, str, int, UUID]) -> str:
    payload = json.dumps(
        [value[0], value[1], value[2], str(value[3])],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


@page_router.get(
    "/industry-analysis/sessions/{session_id}/revisions/"
    "{reviewed_session_revision_id}/result",
    include_in_schema=False,
)
def review_result_page(
    session_id: UUID,
    reviewed_session_revision_id: UUID,
) -> FileResponse:
    """Serve one exact reviewed-plan result page."""

    del session_id, reviewed_session_revision_id
    return FileResponse(_STATIC_DIR / "review_result.html", media_type="text/html")


@api_router.get("/session-revisions/{session_revision_id}/review-view")
def get_review_view(
    session_revision_id: UUID,
    session_id: UUID = Query(),
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(
        get_industry_analysis_session_factory
    ),
) -> dict:
    try:
        with session_factory() as session:
            return IndustryThesisReviewWorkbenchQueryService(session).get_review_view(
                session_id=session_id,
                session_revision_id=session_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
    except IndustryThesisError as exc:
        raise _review_http_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_failure("完整候选审阅读取失败，请检查本地数据库。", exc) from exc


@api_router.get("/session-revisions/{session_revision_id}/owner-context-options")
def get_owner_context_options(
    session_revision_id: UUID,
    session_id: UUID = Query(),
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    cursor: str | None = Query(default=None, max_length=1000),
    limit: int = Query(default=25, ge=1, le=100),
    text_filter: str | None = Query(default=None, max_length=200),
    session_factory: sessionmaker[Session] = Depends(
        get_industry_analysis_session_factory
    ),
) -> dict:
    try:
        boundary = _explicit_utc(as_of_recorded_at_utc)
        cursor_value = _decode_context_cursor(cursor)
        with session_factory() as session:
            revision = session.get(IndustryThesisSessionRevision, session_revision_id)
            identity = session.get(IndustryThesisSessionIdentity, session_id)
            if (
                revision is None
                or identity is None
                or revision.session_id != session_id
                or identity.latest_revision_number != revision.revision_number
            ):
                raise IndustryThesisNotFound(
                    "industry_thesis_session_revision_not_found",
                    "exact latest route-owned session revision was not found",
                )
            if (
                revision.information_cutoff_date > as_of_cutoff
                or stored_utc(revision.recorded_at_utc) > boundary
            ):
                raise IndustryThesisNotFound(
                    "industry_thesis_not_visible",
                    "session revision is outside the requested as-of boundaries",
                )
            if revision.workflow_state not in {
                "candidate_build_ready",
                "awaiting_review",
                "reviewed_plan_ready",
            }:
                raise IndustryThesisError(
                    "industry_thesis_review_invalid",
                    "session revision is not eligible for Owner Context selection",
                )
            if revision.workflow_state == "reviewed_plan_ready":
                reviewed = IndustryThesisReviewedPlanQueryService(
                    session
                ).get_reviewed_plan(
                    session_revision_id,
                    as_of_cutoff=as_of_cutoff,
                    as_of_recorded_at_utc=boundary,
                )
                if reviewed["acceptance_capability"]["state"] != (
                    "legacy_owner_context_missing"
                ):
                    raise IndustryThesisError(
                        "industry_thesis_review_invalid",
                        "a v2 reviewed plan cannot be re-reviewed only to replace context",
                    )

            statement = (
                select(ResearchCase, IndustryMap, IndustryMapRevision)
                .join(IndustryMap, IndustryMap.case_id == ResearchCase.id)
                .join(IndustryMapRevision, IndustryMapRevision.map_id == IndustryMap.id)
                .where(
                    IndustryMapRevision.information_cutoff_date
                    <= revision.information_cutoff_date,
                    IndustryMapRevision.information_cutoff_date <= as_of_cutoff,
                    IndustryMapRevision.recorded_at_utc <= boundary,
                )
            )
            filter_value = (text_filter or "").strip()
            if filter_value:
                pattern = f"%{filter_value}%"
                statement = statement.where(
                    or_(
                        ResearchCase.case_key.ilike(pattern),
                        IndustryMap.map_key.ilike(pattern),
                        IndustryMapRevision.title.ilike(pattern),
                        IndustryMapRevision.scope.ilike(pattern),
                    )
                )
            if cursor_value is not None:
                case_key, map_key, revision_no, revision_id = cursor_value
                statement = statement.where(
                    or_(
                        ResearchCase.case_key > case_key,
                        and_(
                            ResearchCase.case_key == case_key,
                            IndustryMap.map_key > map_key,
                        ),
                        and_(
                            ResearchCase.case_key == case_key,
                            IndustryMap.map_key == map_key,
                            IndustryMapRevision.revision_no < revision_no,
                        ),
                        and_(
                            ResearchCase.case_key == case_key,
                            IndustryMap.map_key == map_key,
                            IndustryMapRevision.revision_no == revision_no,
                            IndustryMapRevision.id > revision_id,
                        ),
                    )
                )
            rows = list(
                session.execute(
                    statement.order_by(
                        ResearchCase.case_key.asc(),
                        IndustryMap.map_key.asc(),
                        IndustryMapRevision.revision_no.desc(),
                        IndustryMapRevision.id.asc(),
                    ).limit(limit + 1)
                )
            )
            has_more = len(rows) > limit
            visible = rows[:limit]
            items = [
                {
                    "industry_map_revision_id": str(map_revision.id),
                    "ordinary_label": (
                        f"{research_case.case_key} · {industry_map.map_key} · "
                        f"第 {map_revision.revision_no} 版"
                    ),
                    "case_key": research_case.case_key,
                    "map_key": industry_map.map_key,
                    "revision_number": map_revision.revision_no,
                    "title": map_revision.title,
                    "scope": map_revision.scope,
                    "information_cutoff_date": (
                        map_revision.information_cutoff_date.isoformat()
                    ),
                    "recorded_at_utc": stored_utc(
                        map_revision.recorded_at_utc
                    ).isoformat(),
                    "technical_details": {
                        "research_case_id": str(research_case.id),
                        "industry_map_id": str(industry_map.id),
                        "industry_map_revision_id": str(map_revision.id),
                    },
                }
                for research_case, industry_map, map_revision in visible
            ]
            next_cursor = None
            if has_more and visible:
                last_case, last_map, last_revision = visible[-1]
                next_cursor = _encode_context_cursor(
                    (
                        last_case.case_key,
                        last_map.map_key,
                        last_revision.revision_no,
                        last_revision.id,
                    )
                )
            return {
                "session_id": str(session_id),
                "session_revision_id": str(session_revision_id),
                "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
                "explicit_confirmation_required": True,
                "automatic_default": None,
                "items": items,
                "next_cursor": next_cursor,
            }
    except IndustryThesisError as exc:
        raise _review_http_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_failure("研究归属选项读取失败，请检查本地数据库。", exc) from exc


@api_router.post("/session-revisions/{session_revision_id}/reviews")
async def review_candidate_universe(
    session_revision_id: UUID,
    request: Request,
    session_id: UUID = Query(),
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    dry_run: bool = Query(default=True),
    read_factory: sessionmaker[Session] = Depends(
        get_industry_analysis_session_factory
    ),
    write_factory: sessionmaker[Session] = Depends(
        get_industry_analysis_write_factory
    ),
) -> dict:
    payload = await _validated_json_body(request, ReviewRequest)
    try:
        if payload.acceptance_plan_version != ACCEPTANCE_PLAN_VERSION:
            raise IndustryThesisError(
                "industry_thesis_input_invalid",
                "unsupported acceptance-plan version",
            )
        with read_factory() as session:
            if session.get(IndustryThesisSessionRevision, session_revision_id) is None:
                raise IndustryThesisNotFound(
                    "industry_thesis_session_revision_not_found",
                    "exact session revision was not found",
                )
            try:
                view = IndustryThesisReviewWorkbenchQueryService(
                    session
                ).get_review_view(
                    session_id=session_id,
                    session_revision_id=session_revision_id,
                    as_of_cutoff=as_of_cutoff,
                    as_of_recorded_at_utc=as_of_recorded_at_utc,
                )
                expected_ids = {
                    item["candidate_revision_id"] for item in view["candidates"]
                }
            except IndustryThesisError:
                reviewed = IndustryThesisReviewedPlanQueryService(
                    session
                ).get_reviewed_plan(
                    session_revision_id,
                    as_of_cutoff=as_of_cutoff,
                    as_of_recorded_at_utc=as_of_recorded_at_utc,
                )
                if (
                    reviewed["session_id"] != str(session_id)
                    or reviewed["acceptance_capability"]["state"]
                    != "legacy_owner_context_missing"
                ):
                    raise
                plan = reviewed["acceptance_plan"]
                expected_ids = {
                    str(item["candidate_revision_id"])
                    for item in plan.get("selected_candidates", [])
                }
                expected_ids.update(
                    str(value)
                    for value in plan.get(
                        "rejected_candidate_revision_ids", []
                    )
                )
                expected_ids.update(
                    str(value)
                    for value in plan.get(
                        "unresolved_candidate_revision_ids", []
                    )
                )
        submitted_ids = {str(item.candidate_revision_id) for item in payload.decisions}
        if len(submitted_ids) != len(payload.decisions):
            raise IndustryThesisError(
                "industry_thesis_duplicate_review",
                "one review request cannot contain the same candidate revision twice",
            )
        if submitted_ids != expected_ids:
            raise IndustryThesisError(
                "industry_thesis_review_incomplete",
                "review decisions must cover the complete exact latest universe",
            )

        command = _normalized_command(
            session_revision_id=session_revision_id,
            payload=payload,
        )
        result = IndustryThesisProposalReviewService(
            write_factory
        ).review_candidates(command, dry_run=dry_run)
        plan = result["acceptance_plan"]
        result["selected_count"] = len(plan.get("selected_candidates", []))
        result["rejected_count"] = len(
            plan.get("rejected_candidate_revision_ids", [])
        )
        result["unresolved_count"] = len(
            plan.get("unresolved_candidate_revision_ids", [])
        )
        result["ownership_notice"] = (
            "审阅计划已冻结精确研究归属，但尚未写入 Stage 1 受益公司或投资候选快照。"
        )
        result["result_path"] = None
        if not dry_run:
            result["result_path"] = _result_path(
                session_id=result["session_id"],
                reviewed_session_revision_id=result[
                    "reviewed_session_revision_id"
                ],
                information_cutoff_date=result["information_cutoff_date"],
                complete_recorded_at_utc=result["candidate_recorded_at_utc"],
            )
        return result
    except IndustryThesisError as exc:
        raise _review_http_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_failure(
            "审阅计划写入失败，请先重新打开精确页面确认是否已写入。",
            exc,
        ) from exc


@api_router.get("/reviewed-plans/{reviewed_session_revision_id}")
def get_reviewed_plan_result(
    reviewed_session_revision_id: UUID,
    session_id: UUID = Query(),
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(
        get_industry_analysis_session_factory
    ),
) -> dict:
    try:
        with session_factory() as session:
            return IndustryThesisReviewWorkbenchQueryService(session).get_result_view(
                session_id=session_id,
                reviewed_session_revision_id=reviewed_session_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
    except IndustryThesisError as exc:
        raise _review_http_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_failure("精确审阅结果读取失败，请检查本地数据库。", exc) from exc
