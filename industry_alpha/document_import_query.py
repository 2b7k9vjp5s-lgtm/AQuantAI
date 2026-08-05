"""Read-only local document projections; raw bytes require an exact endpoint."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.document_import_contracts import DocumentImportError
from industry_alpha.document_import_repository import DocumentImportRepository
from industry_alpha.document_import_models import LocalDocumentReviewRevision
from industry_alpha.document_import_rules import MAX_QUEUE_PAGE_SIZE, utc_timestamp


def _utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class DocumentImportQueryService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def import_detail(self, attempt_id: UUID) -> dict[str, object]:
        with self._session_factory() as session:
            repo = DocumentImportRepository(session)
            attempt = repo.import_attempt(attempt_id)
            if attempt is None:
                raise DocumentImportError("import_not_found")
            content = (
                repo.content_metadata(attempt.content_id) if attempt.content_id else None
            )
            return {
                "import_attempt_id": str(attempt.id),
                "content_id": str(attempt.content_id) if attempt.content_id else None,
                "content_sha256": attempt.content_sha256,
                "original_filename": attempt.original_filename,
                "display_name": attempt.display_name,
                "observed_media_type": attempt.observed_media_type,
                "byte_size": attempt.byte_size,
                "admission_state": attempt.admission_state,
                "admission_reason": attempt.admission_reason,
                "imported_at_utc": _utc(attempt.imported_at_utc),
                "page_count": content.page_count if content else None,
                "embedded_text_page_count": (
                    content.embedded_text_page_count if content else None
                ),
                "extractor_contract_version": (
                    content.extractor_contract_version if content else None
                ),
            }

    def page_batch(
        self, content_id: UUID, *, after_page: int = 0, limit: int = 30
    ) -> dict[str, object]:
        with self._session_factory() as session:
            repo = DocumentImportRepository(session)
            content = repo.content_metadata(content_id)
            if content is None:
                raise DocumentImportError("content_not_found")
            if after_page < 0:
                raise DocumentImportError("invalid_page_cursor")
            effective_limit = min(max(limit, 1), 30)
            rows = repo.pages(
                content_id, after_page=after_page, limit=effective_limit
            )
            return {
                "content_id": str(content_id),
                "pages": [
                    {
                        "page_number": row.page_number,
                        "text_state": row.text_state,
                        "extracted_text": row.extracted_text,
                        "text_sha256": row.text_sha256,
                        "text_char_count": row.text_char_count,
                    }
                    for row in rows
                ],
                "next_after_page": (
                    rows[-1].page_number
                    if rows and rows[-1].page_number < content.page_count
                    else None
                ),
            }

    def attachment(self, content_id: UUID) -> bytes:
        with self._session_factory() as session:
            value = DocumentImportRepository(session).content_bytes(content_id)
            if value is None:
                raise DocumentImportError("content_not_found")
            return value

    def review_detail(
        self,
        review_id: UUID,
        *,
        after_candidate_id: UUID | None = None,
        limit: int = MAX_QUEUE_PAGE_SIZE,
        review_revision_id: UUID | None = None,
    ) -> dict[str, object]:
        with self._session_factory() as session:
            repo = DocumentImportRepository(session)
            review = repo.review_session(review_id)
            if review is None:
                raise DocumentImportError("review_session_not_found")
            effective_limit = min(max(limit, 1), MAX_QUEUE_PAGE_SIZE)
            revisions = repo.revisions(
                review_id, revision_id=review_revision_id
            )
            if review_revision_id is not None and not revisions:
                raise DocumentImportError("review_revision_not_found")
            candidate_page = repo.candidates(
                review_id,
                after_candidate_id=after_candidate_id,
                limit=effective_limit + 1,
                review_revision_id=review_revision_id,
            )
            has_more = len(candidate_page) > effective_limit
            candidates = candidate_page[:effective_limit]
            decisions = repo.revision_decisions(
                tuple(row.id for row in revisions),
                tuple(row.id for row in candidates),
            )
            decisions_by_revision: dict[UUID, list[object]] = {}
            for row in decisions:
                decisions_by_revision.setdefault(row.review_revision_id, []).append(
                    {
                        "candidate_id": str(row.candidate_id),
                        "decision": row.decision,
                        "claim_operation": row.claim_operation,
                        "claim_key": row.claim_key,
                        "claim_status": row.claim_status,
                        "evidence_relation": row.evidence_relation,
                        "decision_fingerprint_sha256": (
                            row.decision_fingerprint_sha256
                        ),
                    }
                )
            return {
                "review_session_id": str(review.id),
                "import_attempt_id": str(review.import_attempt_id),
                "target_research_case_id": str(review.target_research_case_id),
                "candidates": [
                    {
                        "candidate_id": str(row.id),
                        "candidate_kind": row.candidate_kind,
                        "page_number": row.page_number,
                        "start_utf8_byte": row.start_utf8_byte,
                        "end_utf8_byte": row.end_utf8_byte,
                        "quote_text": row.quote_text,
                        "statement": row.statement,
                        "candidate_payload_json": row.candidate_payload_json,
                        "candidate_fingerprint_sha256": row.candidate_fingerprint_sha256,
                    }
                    for row in candidates
                ],
                "next_after_candidate_id": (
                    str(candidates[-1].id) if has_more else None
                ),
                "revisions": [
                    {
                        "review_revision_id": str(row.id),
                        "revision_number": row.revision_number,
                        "review_state": row.review_state,
                        "review_fingerprint_sha256": row.review_fingerprint_sha256,
                        "source_kind": row.source_kind,
                        "evidence_grade": row.evidence_grade,
                        "document_identity_candidate_id": str(
                            row.document_identity_candidate_id
                        ),
                        "subject_candidate_id": str(row.subject_candidate_id),
                        "information_date": row.information_date.isoformat(),
                        "recorded_at_utc": _utc(row.recorded_at_utc),
                        "candidate_decisions": decisions_by_revision.get(row.id, []),
                    }
                    for row in revisions
                ],
            }

    def source_review_session_id(self, revision_id: UUID) -> UUID:
        with self._session_factory() as session:
            revision = session.get(LocalDocumentReviewRevision, revision_id)
            if revision is None:
                raise DocumentImportError("source_review_revision_not_found")
            return revision.review_session_id

    def acceptance_detail(
        self,
        receipt_id: UUID,
        *,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
    ) -> dict[str, object]:
        recorded = utc_timestamp(recorded_at_utc)
        if information_cutoff_date > recorded.date():
            raise DocumentImportError("invalid_acceptance_as_of")
        with self._session_factory() as session:
            repo = DocumentImportRepository(session)
            receipt = repo.receipt(receipt_id)
            if receipt is None:
                raise DocumentImportError("acceptance_receipt_not_found")
            accepted = session.get(
                LocalDocumentReviewRevision,
                receipt.accepted_review_revision_id,
            )
            if accepted is None:
                raise DocumentImportError("acceptance_graph_invalid")
            accepted_at = receipt.accepted_at_utc
            if accepted_at.tzinfo is None or accepted_at.utcoffset() is None:
                accepted_at = accepted_at.replace(tzinfo=timezone.utc)
            if (
                accepted_at.astimezone(timezone.utc) > recorded
                or accepted.information_date > information_cutoff_date
            ):
                raise DocumentImportError("acceptance_not_visible_as_of")
            links = repo.receipt_links(receipt_id)
            return {
                "receipt_id": str(receipt.id),
                "review_session_id": str(receipt.review_session_id),
                "source_review_revision_id": str(receipt.source_review_revision_id),
                "accepted_review_revision_id": str(receipt.accepted_review_revision_id),
                "target_research_case_id": str(receipt.target_research_case_id),
                "request_fingerprint_sha256": receipt.request_fingerprint_sha256,
                "accepted_at_utc": _utc(receipt.accepted_at_utc),
                "information_cutoff_date": information_cutoff_date.isoformat(),
                "recorded_at_boundary_utc": _utc(recorded),
                "links": [
                    {
                        "candidate_id": str(row.candidate_id),
                        "evidence_item_id": str(row.evidence_item_id),
                        "claim_id": str(row.claim_id),
                        "claim_revision_id": str(row.claim_revision_id),
                        "claim_evidence_link_id": str(row.claim_evidence_link_id),
                    }
                    for row in links
                ],
            }
