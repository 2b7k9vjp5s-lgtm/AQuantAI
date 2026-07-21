"""Lazy, read-only FastAPI boundary for the Industry Beneficiary Workspace."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from industry_alpha.beneficiary_workspace_query import (
    IndustryBeneficiaryWorkspaceQueryService,
)
from industry_alpha.beneficiary_workspace_repository import (
    IndustryBeneficiaryWorkspaceDataError,
    IndustryBeneficiaryWorkspaceRepository,
)
from industry_alpha.chain_map_query import IndustryChainMapQueryService
from industry_alpha.chain_map_repository import IndustryChainMapRepository
from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerNotVisible

router = APIRouter(prefix="/industry-research", tags=["industry-research"])


def get_industry_research_session_factory() -> Iterator[sessionmaker[Session]]:
    """Create database resources only when a workspace API is requested."""

    try:
        engine = build_engine()
    except (RuntimeError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Industry Research database configuration is unavailable. "
                "Verify local database settings and try again."
            ),
        ) from exc
    try:
        yield build_session_factory(engine)
    finally:
        engine.dispose()


def _service(session: Session) -> IndustryBeneficiaryWorkspaceQueryService:
    return IndustryBeneficiaryWorkspaceQueryService(
        IndustryBeneficiaryWorkspaceRepository(session),
        IndustryChainMapQueryService(IndustryChainMapRepository(session)),
    )


@router.get("/maps")
def list_industry_research_maps(
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(
        get_industry_research_session_factory
    ),
) -> dict:
    try:
        with session_factory() as session:
            return _service(session).list_maps(
                as_of_cutoff=as_of_cutoff
            ).to_dict()
    except (SQLAlchemyError, IndustryBeneficiaryWorkspaceDataError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Industry Research database query failed. "
                "Verify DATABASE_URL and run Alembic migrations."
            ),
        ) from exc


@router.get("/maps/{map_id}/workspace")
def get_industry_beneficiary_workspace(
    map_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(
        get_industry_research_session_factory
    ),
) -> dict:
    try:
        with session_factory() as session:
            return _service(session).get_workspace(
                map_id, as_of_cutoff=as_of_cutoff
            ).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (SQLAlchemyError, IndustryBeneficiaryWorkspaceDataError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Industry Research database query failed. "
                "Verify DATABASE_URL and run Alembic migrations."
            ),
        ) from exc
