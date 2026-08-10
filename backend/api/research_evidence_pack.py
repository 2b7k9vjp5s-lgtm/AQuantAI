"""Local-only HTTP adapter for Research Evidence Pack v1."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.api.document_import import require_local_host
from backend.api.industry_alpha import get_industry_alpha_session_factory
from industry_alpha.research_evidence_pack_contracts import (
    EvidencePackRequest,
    ResearchEvidencePackError,
)
from industry_alpha.research_evidence_pack_query import ResearchEvidencePackQueryService


router = APIRouter(prefix="/research-evidence-pack/api", tags=["research-evidence-pack"])


@router.get("/cases/{research_case_id}/revisions/{research_case_revision_id}")
def get_research_evidence_pack(
    research_case_id: UUID,
    research_case_revision_id: UUID,
    information_cutoff_date: date = Query(...),
    recorded_at_utc: datetime = Query(...),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(default=None),
    _guard: None = Depends(require_local_host),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, object]:
    try:
        return ResearchEvidencePackQueryService(session_factory).get_pack(
            EvidencePackRequest(
                research_case_id=research_case_id,
                research_case_revision_id=research_case_revision_id,
                information_cutoff_date=information_cutoff_date,
                recorded_at_utc=recorded_at_utc,
                limit=limit,
                cursor=cursor,
            )
        ).to_dict()
    except ResearchEvidencePackError as exc:
        if exc.code in {
            "research_case_not_found",
            "research_case_revision_not_found",
            "research_case_revision_not_visible_as_of",
        }:
            status = 404
        elif exc.code in {
            "research_case_revision_mismatch",
            "evidence_pack_integrity_error",
        }:
            status = 409
        elif exc.code == "database_unavailable":
            status = 503
        else:
            status = 422
        raise HTTPException(status_code=status, detail=exc.code) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database_unavailable") from exc
