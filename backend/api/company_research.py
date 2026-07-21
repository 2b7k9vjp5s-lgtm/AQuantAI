"""Lazy, read-only FastAPI boundary for the Company Research Workspace."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
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

router = APIRouter(prefix="/company-research", tags=["company-research"])


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
