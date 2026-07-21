"""Read-only FastAPI boundary for typed beneficiary evidence semantics."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.api.industry_alpha import get_industry_alpha_session_factory
from industry_alpha.beneficiary_semantics_query import BeneficiarySemanticQueryService
from industry_alpha.beneficiary_semantics_repository import BeneficiarySemanticRepository
from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerNotVisible

router = APIRouter(prefix="/industry-alpha", tags=["industry-alpha"])


@router.get("/beneficiary-semantics/{beneficiary_id}")
def get_beneficiary_semantics(
    beneficiary_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(
        get_industry_alpha_session_factory
    ),
) -> dict:
    """Read one explicit beneficiary's cutoff-visible semantic history."""
    try:
        with session_factory() as session:
            return BeneficiarySemanticQueryService(
                BeneficiarySemanticRepository(session)
            ).get_profile(
                beneficiary_id, as_of_cutoff=as_of_cutoff
            ).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Industry Alpha database query failed. "
                "Verify DATABASE_URL and run Alembic migrations."
            ),
        ) from exc
