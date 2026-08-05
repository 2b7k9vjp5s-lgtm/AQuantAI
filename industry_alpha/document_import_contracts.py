"""Closed contracts for local PDF import, review, and acceptance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID


EXTRACTION_CONTRACT_VERSION = "aquantai.local-pdf-embedded-text.v1"
ACCEPTANCE_CONTRACT_VERSION = "aquantai.local-document-acceptance.v1"
ACCEPTED_REVIEW_CONTRACT_VERSION = "aquantai.local-document-accepted-review.v1"
EVIDENCE_FINGERPRINT_CONTRACT = "aquantai.local-document-evidence-item.v1"


class DocumentImportError(RuntimeError):
    """Fail-closed domain error with a stable public code."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    text_sha256: str
    text_char_count: int


@dataclass(frozen=True)
class ExtractionResult:
    content_sha256: str
    byte_size: int
    pages: tuple[ExtractedPage, ...]
    embedded_text_page_count: int
    total_text_char_count: int
    extractor_package: str
    extractor_version: str
    extractor_contract_version: str = EXTRACTION_CONTRACT_VERSION


@dataclass(frozen=True)
class ImportResult:
    import_attempt_id: UUID
    content_id: UUID | None
    content_sha256: str
    admission_state: str
    admission_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "import_attempt_id": str(self.import_attempt_id),
            "content_id": str(self.content_id) if self.content_id else None,
            "content_sha256": self.content_sha256,
            "admission_state": self.admission_state,
            "admission_reason": self.admission_reason,
        }


@dataclass(frozen=True)
class CandidateInput:
    candidate_kind: str
    payload: dict[str, Any]
    page_number: int | None = None
    start_utf8_byte: int | None = None
    end_utf8_byte: int | None = None
    quote_text: str | None = None
    quote_sha256: str | None = None
    statement: str | None = None
    recorded_at_utc: datetime | None = None


@dataclass(frozen=True)
class DecisionInput:
    candidate_id: UUID
    decision: str
    claim_status: str | None = None
    evidence_relation: str | None = None


@dataclass(frozen=True)
class ReviewRevisionInput:
    expected_previous_revision_number: int
    review_state: str
    source_kind: str
    evidence_grade: str
    document_identity_candidate_id: UUID
    subject_candidate_id: UUID
    information_date: date
    decisions: tuple[DecisionInput, ...]
    reviewer_note: str | None = None
    recorded_at_utc: datetime | None = None


@dataclass(frozen=True)
class AcceptanceInput:
    source_review_revision_id: UUID
    expected_source_review_revision_number: int
    expected_source_review_fingerprint_sha256: str
    expected_session_latest_revision_number: int
    target_research_case_id: UUID
    selected_candidate_ids: tuple[UUID, ...]
    selected_decision_fingerprints: tuple[str, ...]
    recorded_at_utc: datetime
    acceptance_plan_fingerprint_sha256: str
    acceptance_contract_version: str = ACCEPTANCE_CONTRACT_VERSION


@dataclass(frozen=True)
class AcceptanceResult:
    receipt_id: UUID | None
    accepted_review_revision_id: UUID | None
    acceptance_plan_fingerprint_sha256: str
    request_fingerprint_sha256: str
    selected_candidate_ids: tuple[UUID, ...]
    commit_ready: bool
    replayed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": str(self.receipt_id) if self.receipt_id else None,
            "accepted_review_revision_id": (
                str(self.accepted_review_revision_id)
                if self.accepted_review_revision_id
                else None
            ),
            "acceptance_plan_fingerprint_sha256": (
                self.acceptance_plan_fingerprint_sha256
            ),
            "request_fingerprint_sha256": self.request_fingerprint_sha256,
            "selected_candidate_ids": [str(value) for value in self.selected_candidate_ids],
            "commit_ready": self.commit_ready,
            "replayed": self.replayed,
        }
