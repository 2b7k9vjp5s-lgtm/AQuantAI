"""Exact-ID, read-only Canonical Price API."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from backend.database.canonical_price import (
    CanonicalPriceError,
    CanonicalPriceNotFound,
    CanonicalPriceQueryService,
)

router = APIRouter(prefix="/market-data", tags=["market-data"])


def get_canonical_price_session_factory() -> Iterator[sessionmaker[Session]]:
    try:
        engine = build_engine()
    except (RuntimeError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Market-data database configuration is unavailable. Verify local database settings and try again.",
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
    except CanonicalPriceNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code, "message": str(exc)}) from exc
    except CanonicalPriceError as exc:
        raise HTTPException(status_code=409, detail={"code": exc.code, "message": str(exc)}) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Market-data database query failed. Verify local database settings and migrations.") from exc


@router.get("/listed-instruments/{instrument_id}")
def get_listed_instrument(
    instrument_id: UUID,
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(get_canonical_price_session_factory),
) -> dict:
    boundary = _boundary(as_of_cutoff, as_of_recorded_at_utc)
    with session_factory() as session:
        return _read(lambda: CanonicalPriceQueryService(session).get_instrument(instrument_id, as_of_cutoff=as_of_cutoff, as_of_recorded_at_utc=boundary))


@router.get("/canonical-prices/{canonical_price_id}")
def get_canonical_price(
    canonical_price_id: UUID,
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(get_canonical_price_session_factory),
) -> dict:
    boundary = _boundary(as_of_cutoff, as_of_recorded_at_utc)
    with session_factory() as session:
        return _read(lambda: CanonicalPriceQueryService(session).get_price(canonical_price_id, as_of_cutoff=as_of_cutoff, as_of_recorded_at_utc=boundary))


@router.get("/comparison-eligibility/{assessment_id}")
def get_comparison_eligibility(
    assessment_id: UUID,
    as_of_cutoff: date = Query(),
    as_of_recorded_at_utc: datetime = Query(),
    session_factory: sessionmaker[Session] = Depends(get_canonical_price_session_factory),
) -> dict:
    boundary = _boundary(as_of_cutoff, as_of_recorded_at_utc)
    with session_factory() as session:
        return _read(lambda: CanonicalPriceQueryService(session).get_eligibility(assessment_id, as_of_cutoff=as_of_cutoff, as_of_recorded_at_utc=boundary))
