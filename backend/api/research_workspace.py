"""Local-only HTTP boundary for the V1 research product workspace."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.api.document_import import require_local_csrf, require_local_host
from backend.api.industry_alpha import get_industry_alpha_session_factory
from industry_alpha.guarded_ai_contracts import GuardedAIError
from industry_alpha.product_workspace import ProductWorkspaceError, ProductWorkspaceService
from industry_alpha.product_workspace_ai import ProductWorkspaceAIService


router = APIRouter(prefix="/api/v1", tags=["v1-research-workspace"])


class CaseCreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_key: str = Field(min_length=1, max_length=96)
    case_type: str
    title: str = Field(min_length=1, max_length=300)
    research_question: str = Field(min_length=1, max_length=2000)
    created_by: str = Field(min_length=1, max_length=128)
    information_cutoff_date: date
    content: dict[str, str] = Field(default_factory=dict)
    industry_theme: str | None = Field(default=None, max_length=300)
    company_name: str | None = Field(default=None, max_length=300)
    stock_code: str | None = Field(default=None, max_length=32)
    recorded_at_utc: datetime | None = None


class RevisionCreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_latest_revision_no: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=300)
    research_question: str = Field(min_length=1, max_length=2000)
    created_by: str = Field(min_length=1, max_length=128)
    information_cutoff_date: date
    workflow_state: str
    conclusion_status: str
    content: dict[str, str]
    evidence_ids: list[UUID] = Field(default_factory=list, max_length=200)
    change_summary: str | None = Field(default=None, max_length=2000)
    recorded_at_utc: datetime | None = None


class AIDraftBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    expected_manifest_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    confirm_remote_transmission: StrictBool


def _service(factory: sessionmaker[Session]) -> ProductWorkspaceService:
    return ProductWorkspaceService(factory)


def _call(callback):
    try:
        return callback()
    except ProductWorkspaceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.public_message},
        ) from exc
    except GuardedAIError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.failure_code, "message": exc.public_message},
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "research_workspace_database_unavailable",
                "message": "Research Workspace database is unavailable. Verify local configuration and migrations.",
            },
        ) from exc


@router.get("/workspace/dashboard")
def dashboard(
    _guard: None = Depends(require_local_host),
    factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, Any]:
    return _call(lambda: _service(factory).dashboard())


@router.get("/research-cases")
def list_cases(
    case_type: str | None = Query(default=None),
    _guard: None = Depends(require_local_host),
    factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, Any]:
    return _call(lambda: _service(factory).list_cases(case_type=case_type))


@router.post("/research-cases", status_code=201)
def create_case(
    body: CaseCreateBody,
    _guard: None = Depends(require_local_csrf),
    factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, Any]:
    return _call(lambda: _service(factory).create_case(**body.model_dump()))


@router.get("/research-cases/{case_id}")
def get_case(
    case_id: UUID,
    _guard: None = Depends(require_local_host),
    factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, Any]:
    return _call(lambda: _service(factory).get_case(case_id))


@router.post("/research-cases/{case_id}/revisions", status_code=201)
def append_revision(
    case_id: UUID,
    body: RevisionCreateBody,
    _guard: None = Depends(require_local_csrf),
    factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, Any]:
    return _call(lambda: _service(factory).append_revision(case_id, **body.model_dump()))


@router.get("/evidence")
def evidence_ledger(
    status: str | None = Query(default=None),
    _guard: None = Depends(require_local_host),
    factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, Any]:
    return _call(lambda: _service(factory).evidence_ledger(status=status))


@router.get("/documents")
def documents(
    _guard: None = Depends(require_local_host),
    factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, Any]:
    return _call(lambda: _service(factory).documents())


@router.get("/sources")
def sources(
    _guard: None = Depends(require_local_host),
    factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, Any]:
    return _call(lambda: _service(factory).sources())


@router.get("/change-feed")
def change_feed(
    limit: int = Query(default=50, ge=1, le=100),
    _guard: None = Depends(require_local_host),
    factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, Any]:
    return _call(lambda: _service(factory).change_feed(limit=limit))


@router.get("/search")
def search(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=50, ge=1, le=100),
    _guard: None = Depends(require_local_host),
    factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, Any]:
    return _call(lambda: _service(factory).search(q, limit=limit))


@router.get("/research-cases/{case_id}/reports/{format}")
def export_report(
    case_id: UUID,
    format: str,
    _guard: None = Depends(require_local_host),
    factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> Response:
    content, media_type = _call(lambda: _service(factory).report(case_id, format=format))
    suffix = "md" if format == "markdown" else "html"
    return Response(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="aquantai-research-{case_id}.{suffix}"'},
    )


@router.get("/research-cases/{case_id}/ai-preview")
def ai_preview(
    case_id: UUID,
    _guard: None = Depends(require_local_host),
    factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, Any]:
    return _call(
        lambda: ProductWorkspaceAIService.from_environment().preview(
            _service(factory).get_case(case_id)
        )
    )


@router.post("/research-cases/{case_id}/ai-drafts")
def ai_draft(
    case_id: UUID,
    body: AIDraftBody,
    _guard: None = Depends(require_local_csrf),
    factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, Any]:
    return _call(
        lambda: ProductWorkspaceAIService.from_environment().generate(
            _service(factory).get_case(case_id),
            **body.model_dump(),
        )
    )
