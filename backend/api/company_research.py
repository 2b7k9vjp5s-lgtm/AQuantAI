"""Lazy, read-only FastAPI boundary for the Company Research Workspace."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from industry_alpha.company_research_workspace_query import (
    CompanyResearchWorkspaceQueryService,
)
from industry_alpha.company_research_workspace_repository import (
    CompanyResearchWorkspaceDataError,
    CompanyResearchWorkspaceRepository,
)
from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerNotVisible
from industry_alpha.guarded_ai_contracts import GuardedAIError
from industry_alpha.guarded_ai_manifest import GuardedAIManifestError
from industry_alpha.guarded_ai_service import GuardedAIService

router = APIRouter(prefix="/company-research", tags=["company-research"])


class GuardedAIGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    expected_manifest_fingerprint: str = Field(
        pattern=r"^sha256:[0-9a-f]{64}$",
        min_length=71,
        max_length=71,
    )
    confirm_remote_transmission: StrictBool


def get_company_research_session_factory() -> Iterator[sessionmaker[Session]]:
    """Create database resources only when a workspace API is requested."""

    try:
        engine = build_engine()
    except (RuntimeError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Company Research database configuration is unavailable. "
                "Verify local database settings and try again."
            ),
        ) from exc
    try:
        yield build_session_factory(engine)
    finally:
        engine.dispose()


def _service(session: Session) -> CompanyResearchWorkspaceQueryService:
    return CompanyResearchWorkspaceQueryService(
        CompanyResearchWorkspaceRepository(session)
    )


def _guarded_ai_service() -> GuardedAIService:
    """Build configuration lazily; imports and startup never call a model."""

    return GuardedAIService.from_environment()


@router.get("/research")
def list_company_research_workspace_options(
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(
        get_company_research_session_factory
    ),
) -> dict:
    try:
        with session_factory() as session:
            return _service(session).list_research(
                as_of_cutoff=as_of_cutoff
            ).to_dict()
    except (SQLAlchemyError, CompanyResearchWorkspaceDataError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Company Research database query failed. "
                "Verify DATABASE_URL and run Alembic migrations."
            ),
        ) from exc


@router.get("/research/{company_research_id}/workspace")
def get_company_research_workspace(
    company_research_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(
        get_company_research_session_factory
    ),
) -> dict:
    try:
        with session_factory() as session:
            return _service(session).get_workspace(
                company_research_id, as_of_cutoff=as_of_cutoff
            ).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (SQLAlchemyError, CompanyResearchWorkspaceDataError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Company Research database query failed. "
                "Verify DATABASE_URL and run Alembic migrations."
            ),
        ) from exc


@router.get("/research/{company_research_id}/ai-draft-input")
def preview_guarded_ai_input(
    company_research_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(
        get_company_research_session_factory
    ),
) -> dict:
    try:
        with session_factory() as session:
            workspace = _service(session).get_workspace(
                company_research_id, as_of_cutoff=as_of_cutoff
            ).to_dict()
        return _guarded_ai_service().preview(
            workspace,
            company_research_id=str(company_research_id),
            as_of_cutoff=None if as_of_cutoff is None else as_of_cutoff.isoformat(),
        ).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GuardedAIError as exc:
        raise _guarded_ai_http_error(exc) from exc
    except GuardedAIManifestError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "guarded_ai_manifest_unavailable",
                "message": "The accepted research record could not be projected safely.",
            },
        ) from exc
    except (SQLAlchemyError, CompanyResearchWorkspaceDataError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Company Research database query failed. "
                "Verify DATABASE_URL and run Alembic migrations."
            ),
        ) from exc


@router.post("/research/{company_research_id}/ai-drafts")
def generate_guarded_ai_draft(
    company_research_id: UUID,
    payload: GuardedAIGenerationRequest,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(
        get_company_research_session_factory
    ),
) -> dict:
    if payload.confirm_remote_transmission is not True:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "remote_transmission_not_confirmed",
                "message": "Explicit remote transmission confirmation is required.",
            },
        )
    try:
        with session_factory() as session:
            workspace = _service(session).get_workspace(
                company_research_id, as_of_cutoff=as_of_cutoff
            ).to_dict()
        return _guarded_ai_service().generate(
            workspace,
            company_research_id=str(company_research_id),
            as_of_cutoff=None if as_of_cutoff is None else as_of_cutoff.isoformat(),
            expected_manifest_fingerprint=payload.expected_manifest_fingerprint,
            confirm_remote_transmission=payload.confirm_remote_transmission,
        ).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GuardedAIError as exc:
        raise _guarded_ai_http_error(exc) from exc
    except GuardedAIManifestError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "guarded_ai_manifest_unavailable",
                "message": "The accepted research record could not be projected safely.",
            },
        ) from exc
    except (SQLAlchemyError, CompanyResearchWorkspaceDataError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Company Research database query failed. "
                "Verify DATABASE_URL and run Alembic migrations."
            ),
        ) from exc


def _guarded_ai_http_error(exc: GuardedAIError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.failure_code, "message": exc.public_message},
    )
