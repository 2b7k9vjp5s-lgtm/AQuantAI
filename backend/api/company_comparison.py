"""Read-only FastAPI boundary for the Company Research Comparison Matrix."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from industry_alpha.company_comparison_query import (
    CompanyComparisonQueryService,
    CompanyComparisonSelectorError,
)
from industry_alpha.company_comparison_repository import (
    CompanyComparisonDataError,
    CompanyComparisonRepository,
)
from industry_alpha.errors import EvidenceLedgerNotFound

router = APIRouter(prefix="/company-comparison", tags=["company-comparison"])


def get_company_comparison_session_factory() -> Iterator[sessionmaker[Session]]:
    """Create database resources only when the comparison API is requested."""

    try:
        engine = build_engine()
    except (RuntimeError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Company Comparison database configuration is unavailable. "
                "Verify local database settings and try again."
            ),
        ) from exc
    try:
        yield build_session_factory(engine)
    finally:
        engine.dispose()


def _service(session: Session) -> CompanyComparisonQueryService:
    return CompanyComparisonQueryService(CompanyComparisonRepository(session))


@router.get("/candidate-pool-revisions/{candidate_pool_revision_id}")
def get_company_comparison(
    candidate_pool_revision_id: UUID,
    as_of_cutoff: date = Query(...),
    as_of_recorded_at_utc: datetime = Query(...),
    session_factory: sessionmaker[Session] = Depends(
        get_company_comparison_session_factory
    ),
) -> dict:
    """Read one explicit frozen candidate-pool universe without ranking it."""

    try:
        with session_factory() as session:
            return _service(session).get_comparison(
                candidate_pool_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            ).to_dict()
    except EvidenceLedgerNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CompanyComparisonSelectorError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_comparison_selector", "message": str(exc)},
        ) from exc
    except CompanyComparisonDataError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "company_comparison_integrity_failure",
                "message": "The frozen comparison boundary could not be projected safely.",
            },
        ) from exc
    except (SQLAlchemyError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Company Comparison database query failed. "
                "Verify DATABASE_URL and run Alembic migrations."
            ),
        ) from exc
