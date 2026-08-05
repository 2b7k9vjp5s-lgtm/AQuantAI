"""Local-only HTTP adapter for explicit PDF import and reviewed acceptance."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from backend.api.industry_alpha import get_industry_alpha_session_factory
from industry_alpha.commands import EvidenceLedgerCommandService
from industry_alpha.document_import_commands import DocumentImportCommandService
from industry_alpha.document_import_contracts import (
    AcceptanceInput,
    CandidateInput,
    DecisionInput,
    DocumentImportError,
    ReviewRevisionInput,
)
from industry_alpha.document_import_query import DocumentImportQueryService
from industry_alpha.document_import_rules import MAX_INPUT_BYTES
from industry_alpha.errors import (
    EvidenceLedgerConflictError,
    EvidenceLedgerNotFound,
    EvidenceLedgerValidationError,
)


api_router = APIRouter(tags=["document-import"])
page_router = APIRouter(tags=["document-import-page"])
_CSRF_COOKIE = "aquantai_document_csrf"
_CSRF_TOKEN = secrets.token_urlsafe(32)
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "testserver"}
_STATIC_DIR = Path(__file__).resolve().parents[2] / "document_import" / "static"


class ReviewCreateBody(BaseModel):
    import_attempt_id: UUID
    target_research_case_id: UUID
    created_at_utc: datetime | None = None


class CandidateBody(BaseModel):
    candidate_kind: str
    payload: dict[str, object] = Field(default_factory=dict)
    page_number: int | None = None
    start_utf8_byte: int | None = None
    end_utf8_byte: int | None = None
    quote_text: str | None = None
    quote_sha256: str | None = None
    statement: str | None = None
    recorded_at_utc: datetime | None = None


class DecisionBody(BaseModel):
    candidate_id: UUID
    decision: str
    claim_status: str | None = None
    evidence_relation: str | None = None


class ReviewRevisionBody(BaseModel):
    expected_previous_revision_number: int
    review_state: str
    source_kind: str
    evidence_grade: str
    document_identity_candidate_id: UUID
    subject_candidate_id: UUID
    information_date: date
    decisions: list[DecisionBody]
    reviewer_note: str | None = None
    recorded_at_utc: datetime | None = None


class AcceptanceBody(BaseModel):
    source_review_revision_id: UUID
    expected_source_review_revision_number: int
    expected_source_review_fingerprint_sha256: str
    expected_session_latest_revision_number: int
    target_research_case_id: UUID
    selected_candidate_ids: list[UUID]
    selected_decision_fingerprints: list[str]
    recorded_at_utc: datetime
    acceptance_plan_fingerprint_sha256: str
    acceptance_contract_version: str = "aquantai.local-document-acceptance.v1"


def _origin(request: Request) -> str:
    host = request.headers.get("host", "")
    hostname = request.url.hostname or ""
    if hostname not in _LOCAL_HOSTS:
        raise HTTPException(403, "Document Import is restricted to the local application origin.")
    return f"{request.url.scheme}://{host}"


def require_local_csrf(request: Request) -> None:
    expected_origin = _origin(request)
    if request.headers.get("origin") != expected_origin:
        raise HTTPException(403, "Origin does not match the local application origin.")
    if (
        request.cookies.get(_CSRF_COOKIE) != _CSRF_TOKEN
        or request.headers.get("x-aquantai-csrf") != _CSRF_TOKEN
    ):
        raise HTTPException(403, "CSRF confirmation is missing or expired.")


def require_local_host(request: Request) -> None:
    """Keep every document page and read API inside the loopback boundary."""

    _origin(request)


def is_document_import_mutation(request: Request) -> bool:
    return request.method == "POST" and (
        request.url.path == "/api/document-imports"
        or request.url.path.startswith("/api/document-reviews")
    )


def _commands(factory: sessionmaker[Session]) -> DocumentImportCommandService:
    return DocumentImportCommandService(factory)


def _acceptance(body: AcceptanceBody) -> AcceptanceInput:
    return AcceptanceInput(
        source_review_revision_id=body.source_review_revision_id,
        expected_source_review_revision_number=body.expected_source_review_revision_number,
        expected_source_review_fingerprint_sha256=body.expected_source_review_fingerprint_sha256,
        expected_session_latest_revision_number=body.expected_session_latest_revision_number,
        target_research_case_id=body.target_research_case_id,
        selected_candidate_ids=tuple(body.selected_candidate_ids),
        selected_decision_fingerprints=tuple(body.selected_decision_fingerprints),
        recorded_at_utc=body.recorded_at_utc,
        acceptance_plan_fingerprint_sha256=body.acceptance_plan_fingerprint_sha256,
        acceptance_contract_version=body.acceptance_contract_version,
    )


def _domain_call(callable_):
    try:
        return callable_()
    except DocumentImportError as exc:
        status = 404 if exc.code.endswith("not_found") else 409 if "conflict" in exc.code or "mismatch" in exc.code else 422
        raise HTTPException(status, exc.code) from exc
    except EvidenceLedgerNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except EvidenceLedgerConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except EvidenceLedgerValidationError as exc:
        raise HTTPException(422, str(exc)) from exc


def _bind_review_path(
    session_factory: sessionmaker[Session], review_id: UUID, revision_id: UUID
) -> None:
    exact = DocumentImportQueryService(session_factory).source_review_session_id(
        revision_id
    )
    if exact != review_id:
        raise DocumentImportError("review_session_path_mismatch")


@page_router.get("/document-import", include_in_schema=False)
def document_import_page(
    _guard: None = Depends(require_local_host),
) -> FileResponse:
    return FileResponse(_STATIC_DIR / "document_import.html", media_type="text/html")


@api_router.get("/api/document-import/csrf")
def csrf_token(request: Request, response: Response) -> dict[str, str]:
    _origin(request)
    response.set_cookie(
        _CSRF_COOKIE,
        _CSRF_TOKEN,
        httponly=False,
        secure=False,
        samesite="strict",
        path="/",
    )
    return {"csrf_token": _CSRF_TOKEN}


@api_router.post("/api/document-imports")
async def import_document(
    request: Request,
    original_filename: str = Query(...),
    display_name: str | None = Query(default=None),
    _guard: None = Depends(require_local_csrf),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, object]:
    length = request.headers.get("content-length")
    if length is not None and int(length) > MAX_INPUT_BYTES:
        raise HTTPException(413, "file_too_large")
    payload = await request.body()
    if len(payload) > MAX_INPUT_BYTES:
        raise HTTPException(413, "file_too_large")
    result = _domain_call(
        lambda: _commands(session_factory).import_pdf(
            pdf_bytes=payload,
            original_filename=original_filename,
            display_name=display_name,
            observed_media_type=request.headers.get("content-type", ""),
        )
    )
    return result.to_dict()


@api_router.get("/api/document-imports/{attempt_id}")
def import_detail(
    attempt_id: UUID,
    _guard: None = Depends(require_local_host),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, object]:
    return _domain_call(lambda: DocumentImportQueryService(session_factory).import_detail(attempt_id))


@api_router.get("/api/document-contents/{content_id}/pages")
def document_pages(
    content_id: UUID,
    after_page: int = Query(default=0, ge=0),
    limit: int = Query(default=30, ge=1, le=30),
    _guard: None = Depends(require_local_host),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, object]:
    return _domain_call(
        lambda: DocumentImportQueryService(session_factory).page_batch(
            content_id, after_page=after_page, limit=limit
        )
    )


@api_router.get("/api/document-contents/{content_id}/pdf")
def document_pdf(
    content_id: UUID,
    _guard: None = Depends(require_local_host),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> Response:
    value = _domain_call(lambda: DocumentImportQueryService(session_factory).attachment(content_id))
    return Response(
        value,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="document.pdf"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@api_router.post("/api/document-reviews")
def create_review(
    body: ReviewCreateBody,
    _guard: None = Depends(require_local_csrf),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, str]:
    row = _domain_call(
        lambda: _commands(session_factory).create_review_session(**body.model_dump())
    )
    return {"review_session_id": str(row.id)}


@api_router.post("/api/document-reviews/{review_id}/candidates")
def create_candidate(
    review_id: UUID,
    body: CandidateBody,
    _guard: None = Depends(require_local_csrf),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, str]:
    row = _domain_call(
        lambda: _commands(session_factory).add_candidate(
            review_id, CandidateInput(**body.model_dump())
        )
    )
    return {
        "candidate_id": str(row.id),
        "candidate_fingerprint_sha256": row.candidate_fingerprint_sha256,
    }


@api_router.post("/api/document-reviews/{review_id}/revisions")
def create_review_revision(
    review_id: UUID,
    body: ReviewRevisionBody,
    _guard: None = Depends(require_local_csrf),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, object]:
    data = body.model_dump(exclude={"decisions"})
    data["decisions"] = tuple(DecisionInput(**item.model_dump()) for item in body.decisions)
    row = _domain_call(
        lambda: _commands(session_factory).append_review_revision(
            review_id, ReviewRevisionInput(**data)
        )
    )
    return {
        "review_revision_id": str(row.id),
        "revision_number": row.revision_number,
        "review_fingerprint_sha256": row.review_fingerprint_sha256,
    }


@api_router.get("/api/document-reviews/{review_id}")
def review_detail(
    review_id: UUID,
    after_candidate_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=50),
    review_revision_id: UUID | None = Query(default=None),
    _guard: None = Depends(require_local_host),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, object]:
    return _domain_call(
        lambda: DocumentImportQueryService(session_factory).review_detail(
            review_id,
            after_candidate_id=after_candidate_id,
            limit=limit,
            review_revision_id=review_revision_id,
        )
    )


@api_router.post("/api/document-reviews/{review_id}/acceptance-preview")
def acceptance_preview(
    review_id: UUID,
    body: AcceptanceBody,
    _guard: None = Depends(require_local_csrf),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, object]:
    result = _domain_call(
        lambda: (
            _bind_review_path(
                session_factory, review_id, body.source_review_revision_id
            ),
            EvidenceLedgerCommandService(
                session_factory
            ).preview_reviewed_local_document(_acceptance(body)),
        )[1]
    )
    return result.to_dict()


@api_router.post("/api/document-reviews/{review_id}/acceptance-commit")
def acceptance_commit(
    review_id: UUID,
    body: AcceptanceBody,
    _guard: None = Depends(require_local_csrf),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, object]:
    result = _domain_call(
        lambda: (
            _bind_review_path(
                session_factory, review_id, body.source_review_revision_id
            ),
            EvidenceLedgerCommandService(
                session_factory
            ).accept_reviewed_local_document(_acceptance(body)),
        )[1]
    )
    return result.to_dict()


@api_router.get("/api/document-acceptances/{receipt_id}")
def acceptance_detail(
    receipt_id: UUID,
    information_cutoff_date: date = Query(...),
    recorded_at_utc: datetime = Query(...),
    _guard: None = Depends(require_local_host),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict[str, object]:
    return _domain_call(
        lambda: DocumentImportQueryService(session_factory).acceptance_detail(
            receipt_id,
            information_cutoff_date=information_cutoff_date,
            recorded_at_utc=recorded_at_utc,
        )
    )
