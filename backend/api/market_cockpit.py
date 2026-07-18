"""Lazy, read-only FastAPI boundary for Market Cockpit."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from backend.database.series import SnapshotSeriesError, validate_series_key
from market_cockpit.calculator import MarketCockpitCalculationError
from market_cockpit.repository import (
    MarketCockpitRepository,
    MarketCockpitSelectionError,
    MarketCockpitSnapshotNotFound,
)
from market_cockpit.service import MarketCockpitService

router = APIRouter(prefix="/market-cockpit", tags=["market-cockpit"])


@dataclass(frozen=True)
class MarketCockpitRequest:
    series_key: str
    as_of_cutoff: str | None


def require_market_cockpit_request(
    series_key: str | None = Query(default=None),
    as_of_cutoff: str | None = Query(default=None),
) -> MarketCockpitRequest:
    """Validate selection before any database engine can be constructed."""
    if series_key is None:
        raise HTTPException(
            status_code=422,
            detail="series_key is required; provider-only Market Cockpit selection is not allowed.",
        )
    try:
        validated_key = validate_series_key(series_key)
        validated_cutoff = _optional_compact_date(as_of_cutoff)
    except (SnapshotSeriesError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return MarketCockpitRequest(validated_key, validated_cutoff)


def get_market_cockpit_session_factory(
    _request: MarketCockpitRequest = Depends(require_market_cockpit_request),
) -> Iterator[sessionmaker[Session]]:
    """Create and dispose database resources only for an authorized request."""
    try:
        engine = build_engine()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Market Cockpit database configuration is unavailable: {exc}",
        ) from exc
    try:
        yield build_session_factory(engine)
    finally:
        engine.dispose()


@router.get("/snapshot")
def market_cockpit_snapshot(
    request: MarketCockpitRequest = Depends(require_market_cockpit_request),
    session_factory: sessionmaker[Session] = Depends(get_market_cockpit_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            snapshot = MarketCockpitService(MarketCockpitRepository(session)).build_snapshot(
                series_key=request.series_key,
                as_of_cutoff=request.as_of_cutoff,
            )
        return snapshot.to_dict()
    except MarketCockpitSnapshotNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (MarketCockpitSelectionError, MarketCockpitCalculationError, SnapshotSeriesError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Market Cockpit database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


def _optional_compact_date(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().replace("-", "")
    try:
        return datetime.strptime(normalized, "%Y%m%d").strftime("%Y%m%d")
    except ValueError as exc:
        raise ValueError("as_of_cutoff must use YYYYMMDD format.") from exc
