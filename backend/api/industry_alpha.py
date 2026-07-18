"""Lazy, read-only FastAPI boundary for the Industry Alpha ledger."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from industry_alpha.chain_map_query import IndustryChainMapQueryService
from industry_alpha.chain_map_repository import IndustryChainMapRepository
from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerNotVisible
from industry_alpha.query import EvidenceLedgerQueryService
from industry_alpha.repository import EvidenceLedgerRepository

router = APIRouter(prefix="/industry-alpha", tags=["industry-alpha"])


def get_industry_alpha_session_factory() -> Iterator[sessionmaker[Session]]:
    """Create database resources only when a ledger route is requested."""
    try:
        engine = build_engine()
    except (RuntimeError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Industry Alpha database configuration is unavailable. "
                "Verify local database settings and try again."
            ),
        ) from exc
    try:
        yield build_session_factory(engine)
    finally:
        engine.dispose()


@router.get("/maps")
def list_industry_maps(
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return IndustryChainMapQueryService(
                IndustryChainMapRepository(session)
            ).list_maps(as_of_cutoff=as_of_cutoff).to_dict()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/maps/{map_id}")
def get_industry_map(
    map_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return IndustryChainMapQueryService(
                IndustryChainMapRepository(session)
            ).get_map(map_id, as_of_cutoff=as_of_cutoff).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/cases")
def list_industry_alpha_cases(
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return EvidenceLedgerQueryService(
                EvidenceLedgerRepository(session)
            ).list_cases(as_of_cutoff=as_of_cutoff).to_dict()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/cases/{case_id}")
def get_industry_alpha_case(
    case_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return EvidenceLedgerQueryService(
                EvidenceLedgerRepository(session)
            ).get_case(case_id, as_of_cutoff=as_of_cutoff).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc
