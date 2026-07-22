"""Exact-ID, read-only Investment Candidate Intelligence v1 API."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from industry_alpha.investment_candidate_service import (
    InvestmentCandidateError,
    InvestmentCandidateNotFound,
    InvestmentCandidateQueryService,
)

router = APIRouter(prefix="/investment-candidates", tags=["investment-candidates"])


def get_investment_candidate_session_factory() -> Iterator[sessionmaker[Session]]:
    try:
        engine = build_engine()
    except (RuntimeError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Investment-candidate database configuration is unavailable. Verify local database settings and try again.",
        ) from exc
    try:
        yield build_session_factory(engine)
    finally:
        engine.dispose()


def _boundary(cutoff: date, value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise HTTPException(status_code=422, detail="as_of_recorded_at_utc must be an explicit UTC timestamp")
    result = value.astimezone(timezone.utc)
    if cutoff > result.date():
        raise HTTPException(status_code=422, detail="as_of_cutoff cannot be later than as_of_recorded_at_utc")
    return result


def _read(action):
    try:
        return action()
    except InvestmentCandidateNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code, "message": str(exc)}) from exc
    except InvestmentCandidateError as exc:
        raise HTTPException(status_code=409, detail={"code": exc.code, "message": str(exc)}) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Investment-candidate database query failed. Verify local database settings and migrations.",
        ) from exc


@router.get("/component-revisions/{component_revision_id}")
def get_component_revision(
    component_revision_id: UUID,
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(get_investment_candidate_session_factory),
) -> dict:
    boundary = _boundary(as_of_cutoff, as_of_recorded_at_utc)
    with session_factory() as session:
        return _read(lambda: InvestmentCandidateQueryService(session).get_component_revision(
            component_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=boundary,
        ))


@router.get("/snapshot-revisions/{snapshot_revision_id}")
def get_snapshot_revision(
    snapshot_revision_id: UUID,
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(get_investment_candidate_session_factory),
) -> dict:
    boundary = _boundary(as_of_cutoff, as_of_recorded_at_utc)
    with session_factory() as session:
        return _read(lambda: InvestmentCandidateQueryService(session).get_snapshot_revision(
            snapshot_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=boundary,
        ))
