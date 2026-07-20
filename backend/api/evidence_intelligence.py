"""Lazy, read-only FastAPI boundary for Evidence Intelligence."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from industry_alpha.evidence_intelligence_query import (
    DEFAULT_LIMIT,
    EvidenceIntelligenceQueryService,
    EvidenceIntelligenceRequest,
    EvidenceIntelligenceValidationError,
    resolve_feed_request,
)
from industry_alpha.evidence_intelligence_repository import (
    EvidenceIntelligenceDataError,
    EvidenceIntelligenceRepository,
)

router = APIRouter(prefix="/evidence-intelligence", tags=["evidence-intelligence"])


def get_evaluated_at_utc() -> datetime:
    """Capture one request evaluation time through an overridable dependency."""

    return datetime.now(timezone.utc)


def require_evidence_intelligence_request(
    as_of_cutoff: date | None = Query(default=None),
    recorded_from: datetime | None = Query(default=None),
    recorded_to: datetime | None = Query(default=None),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=DEFAULT_LIMIT),
    cursor: str | None = Query(default=None),
    evaluated_at_utc: datetime = Depends(get_evaluated_at_utc),
) -> EvidenceIntelligenceRequest:
    """Validate the complete request before constructing database resources."""

    try:
        return resolve_feed_request(
            as_of_cutoff=as_of_cutoff,
            recorded_from=recorded_from,
            recorded_to=recorded_to,
            event_type=event_type,
            limit=limit,
            cursor=cursor,
            evaluated_at_utc=evaluated_at_utc,
        )
    except EvidenceIntelligenceValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def get_evidence_intelligence_session_factory(
    _request: EvidenceIntelligenceRequest = Depends(
        require_evidence_intelligence_request
    ),
) -> Iterator[sessionmaker[Session]]:
    """Create database resources only after request validation succeeds."""

    try:
        engine = build_engine()
    except (RuntimeError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Evidence Intelligence database configuration is unavailable. "
                "Verify local database settings and try again."
            ),
        ) from exc
    try:
        yield build_session_factory(engine)
    finally:
        engine.dispose()


@router.get("/feed")
def evidence_intelligence_feed(
    request: EvidenceIntelligenceRequest = Depends(
        require_evidence_intelligence_request
    ),
    session_factory: sessionmaker[Session] = Depends(
        get_evidence_intelligence_session_factory
    ),
) -> dict:
    try:
        with session_factory() as session:
            return EvidenceIntelligenceQueryService(
                EvidenceIntelligenceRepository(session)
            ).build_feed(request).to_dict()
    except (SQLAlchemyError, EvidenceIntelligenceDataError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Evidence Intelligence database query failed. "
                "Verify DATABASE_URL and run Alembic migrations."
            ),
        ) from exc
