"""Exact-ID, read-only normalized valuation and expectation API."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from industry_alpha.normalized_financial_rules import NormalizedMetricError
from industry_alpha.normalized_valuation_service import (
    NormalizedMetricNotFound,
    NormalizedValuationQueryService,
)

router = APIRouter(prefix="/normalized-valuation", tags=["normalized-valuation"])


def _boundary(cutoff: date, value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise HTTPException(
            status_code=422,
            detail="as_of_recorded_at_utc must be an explicit UTC timestamp",
        )
    result = value.astimezone(timezone.utc)
    if cutoff > result.date():
        raise HTTPException(
            status_code=422,
            detail="as_of_cutoff cannot be later than as_of_recorded_at_utc",
        )
    return result


def get_normalized_valuation_session_factory(
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
) -> Iterator[sessionmaker[Session]]:
    """Validate read boundaries before opening the local database."""

    _boundary(as_of_cutoff, as_of_recorded_at_utc)
    try:
        engine = build_engine()
    except (RuntimeError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Normalized-valuation database configuration is unavailable. "
                "Verify local database settings and try again."
            ),
        ) from exc
    try:
        yield build_session_factory(engine)
    finally:
        engine.dispose()


def _read(action):
    try:
        return action()
    except NormalizedMetricNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except NormalizedMetricError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Normalized-valuation database query failed. "
                "Verify local database settings and migrations."
            ),
        ) from exc


@router.get("/financial-observation-revisions/{revision_id}")
def get_financial_observation_revision(
    revision_id: UUID,
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(
        get_normalized_valuation_session_factory
    ),
) -> dict:
    boundary = _boundary(as_of_cutoff, as_of_recorded_at_utc)
    with session_factory() as session:
        return _read(
            lambda: NormalizedValuationQueryService(
                session
            ).get_financial_observation_revision(
                revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=boundary,
            )
        )


@router.get("/metric-revisions/{revision_id}")
def get_metric_revision(
    revision_id: UUID,
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(
        get_normalized_valuation_session_factory
    ),
) -> dict:
    boundary = _boundary(as_of_cutoff, as_of_recorded_at_utc)
    with session_factory() as session:
        return _read(
            lambda: NormalizedValuationQueryService(session).get_metric_revision(
                revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=boundary,
            )
        )


@router.get("/comparison-set-revisions/{revision_id}")
def get_comparison_set_revision(
    revision_id: UUID,
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(
        get_normalized_valuation_session_factory
    ),
) -> dict:
    boundary = _boundary(as_of_cutoff, as_of_recorded_at_utc)
    with session_factory() as session:
        return _read(
            lambda: NormalizedValuationQueryService(
                session
            ).get_comparison_set_revision(
                revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=boundary,
            )
        )


@router.get("/expectation-gap-revisions/{revision_id}")
def get_expectation_gap_revision(
    revision_id: UUID,
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(
        get_normalized_valuation_session_factory
    ),
) -> dict:
    boundary = _boundary(as_of_cutoff, as_of_recorded_at_utc)
    with session_factory() as session:
        return _read(
            lambda: NormalizedValuationQueryService(
                session
            ).get_expectation_gap_revision(
                revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=boundary,
            )
        )
