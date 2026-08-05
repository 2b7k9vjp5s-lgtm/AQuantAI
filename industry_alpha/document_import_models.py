"""Append-only persistence models for reviewed local PDF imports."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    event,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.database.models import Base
from industry_alpha.errors import EvidenceLedgerImmutableError


class LocalDocumentContent(Base):
    __tablename__ = "local_document_contents"
    __table_args__ = (
        CheckConstraint("length(content_sha256) = 64", name="ck_local_document_content_sha"),
        CheckConstraint("media_type = 'application/pdf'", name="ck_local_document_media_type"),
        CheckConstraint("byte_size > 0 AND byte_size <= 52428800", name="ck_local_document_byte_size"),
        CheckConstraint("page_count BETWEEN 1 AND 300", name="ck_local_document_page_count"),
        CheckConstraint(
            "embedded_text_page_count BETWEEN 1 AND page_count",
            name="ck_local_document_embedded_pages",
        ),
        CheckConstraint(
            "total_text_char_count BETWEEN 1 AND 5000000",
            name="ck_local_document_text_count",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_pdf_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, deferred=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedded_text_page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_text_char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    extractor_contract_version: Mapped[str] = mapped_column(String(128), nullable=False)
    extractor_package: Mapped[str] = mapped_column(String(64), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LocalDocumentImportAttempt(Base):
    __tablename__ = "local_document_import_attempts"
    __table_args__ = (
        CheckConstraint("length(content_sha256) = 64", name="ck_local_document_attempt_sha"),
        CheckConstraint("byte_size >= 0", name="ck_local_document_attempt_size"),
        CheckConstraint(
            "admission_state IN ('admitted','rejected','exact_content_duplicate','filename_content_conflict')",
            name="ck_local_document_admission_state",
        ),
        Index("ix_local_document_attempt_imported", "imported_at_utc", "id"),
        Index("ix_local_document_attempt_filename", "original_filename", "content_sha256"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("local_document_contents.id", ondelete="RESTRICT")
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(300), nullable=False)
    observed_media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    admission_state: Mapped[str] = mapped_column(String(32), nullable=False)
    admission_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    imported_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LocalDocumentPage(Base):
    __tablename__ = "local_document_pages"
    __table_args__ = (
        UniqueConstraint("content_id", "page_number", name="uq_local_document_page_number"),
        CheckConstraint("page_number BETWEEN 1 AND 300", name="ck_local_document_page_number"),
        CheckConstraint("text_state IN ('embedded_text_present','empty')", name="ck_local_document_page_state"),
        CheckConstraint("length(text_sha256) = 64", name="ck_local_document_page_sha"),
        CheckConstraint("text_char_count BETWEEN 0 AND 100000", name="ck_local_document_page_chars"),
        Index("ix_local_document_page_content", "content_id", "page_number"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    content_id: Mapped[UUID] = mapped_column(
        ForeignKey("local_document_contents.id", ondelete="RESTRICT"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_state: Mapped[str] = mapped_column(String(32), nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    text_char_count: Mapped[int] = mapped_column(Integer, nullable=False)


class LocalDocumentReviewSession(Base):
    __tablename__ = "local_document_review_sessions"
    __table_args__ = (
        UniqueConstraint("import_attempt_id", "target_research_case_id", name="uq_local_document_review_target"),
        Index("ix_local_document_review_case", "target_research_case_id", "created_at_utc"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    import_attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey("local_document_import_attempts.id", ondelete="RESTRICT"), nullable=False
    )
    target_research_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_cases.id", ondelete="RESTRICT"), nullable=False
    )
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LocalDocumentCandidate(Base):
    __tablename__ = "local_document_candidates"
    __table_args__ = (
        CheckConstraint(
            "candidate_kind IN ('document_identity','company_identity','fact','event')",
            name="ck_local_document_candidate_kind",
        ),
        CheckConstraint("length(candidate_fingerprint_sha256) = 64", name="ck_local_document_candidate_sha"),
        CheckConstraint(
            "(candidate_kind IN ('fact','event') AND page_number IS NOT NULL "
            "AND start_utf8_byte IS NOT NULL AND end_utf8_byte IS NOT NULL "
            "AND quote_text IS NOT NULL AND quote_sha256 IS NOT NULL "
            "AND statement IS NOT NULL AND start_utf8_byte >= 0 "
            "AND end_utf8_byte > start_utf8_byte) OR "
            "(candidate_kind IN ('document_identity','company_identity') "
            "AND page_number IS NULL AND start_utf8_byte IS NULL "
            "AND end_utf8_byte IS NULL AND quote_text IS NULL "
            "AND quote_sha256 IS NULL AND statement IS NULL)",
            name="ck_local_document_candidate_shape",
        ),
        UniqueConstraint("review_session_id", "candidate_fingerprint_sha256", name="uq_local_document_candidate_fingerprint"),
        Index("ix_local_document_candidate_session", "review_session_id", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    review_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("local_document_review_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    candidate_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    start_utf8_byte: Mapped[int | None] = mapped_column(Integer)
    end_utf8_byte: Mapped[int | None] = mapped_column(Integer)
    quote_text: Mapped[str | None] = mapped_column(Text)
    quote_sha256: Mapped[str | None] = mapped_column(String(64))
    statement: Mapped[str | None] = mapped_column(String(4000))
    candidate_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LocalDocumentReviewRevision(Base):
    __tablename__ = "local_document_review_revisions"
    __table_args__ = (
        UniqueConstraint("review_session_id", "revision_number", name="uq_local_document_review_revision_number"),
        UniqueConstraint("supersedes_review_revision_id", name="uq_local_document_review_successor"),
        CheckConstraint("revision_number > 0", name="ck_local_document_review_revision_positive"),
        CheckConstraint(
            "review_state IN ('draft','deferred','rejected','accepted')",
            name="ck_local_document_review_state",
        ),
        CheckConstraint("length(review_fingerprint_sha256) = 64", name="ck_local_document_review_sha"),
        CheckConstraint("evidence_grade IN ('A','B','C','D')", name="ck_local_document_review_grade"),
        Index("ix_local_document_review_revision", "review_session_id", "revision_number"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    review_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("local_document_review_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    review_state: Mapped[str] = mapped_column(String(16), nullable=False)
    review_fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_previous_revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_grade: Mapped[str] = mapped_column(String(1), nullable=False)
    document_identity_candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("local_document_candidates.id", ondelete="RESTRICT"), nullable=False
    )
    subject_candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("local_document_candidates.id", ondelete="RESTRICT"), nullable=False
    )
    information_date: Mapped[date] = mapped_column(Date, nullable=False)
    reviewer_note: Mapped[str | None] = mapped_column(String(2000))
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_review_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("local_document_review_revisions.id", ondelete="RESTRICT")
    )


class LocalDocumentReviewCandidateDecision(Base):
    __tablename__ = "local_document_review_candidate_decisions"
    __table_args__ = (
        UniqueConstraint("review_revision_id", "candidate_id", name="uq_local_document_review_decision"),
        CheckConstraint(
            "decision IN ('selected','rejected','deferred')",
            name="ck_local_document_decision",
        ),
        CheckConstraint(
            "claim_operation IS NULL OR claim_operation = 'create_new_deterministic_claim'",
            name="ck_local_document_claim_operation",
        ),
        CheckConstraint("length(decision_fingerprint_sha256) = 64", name="ck_local_document_decision_sha"),
        Index("ix_local_document_decision_revision", "review_revision_id", "candidate_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    review_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("local_document_review_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("local_document_candidates.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    claim_operation: Mapped[str | None] = mapped_column(String(48))
    claim_key: Mapped[str | None] = mapped_column(String(96))
    claim_status: Mapped[str | None] = mapped_column(String(16))
    evidence_relation: Mapped[str | None] = mapped_column(String(16))
    decision_fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LocalDocumentAcceptanceReceipt(Base):
    __tablename__ = "local_document_acceptance_receipts"
    __table_args__ = (
        UniqueConstraint("source_review_revision_id", name="uq_local_document_receipt_source"),
        UniqueConstraint("accepted_review_revision_id", name="uq_local_document_receipt_accepted"),
        UniqueConstraint("request_fingerprint_sha256", name="uq_local_document_receipt_request"),
        CheckConstraint("length(source_review_fingerprint_sha256) = 64", name="ck_local_document_receipt_source_sha"),
        CheckConstraint("length(accepted_review_fingerprint_sha256) = 64", name="ck_local_document_receipt_accepted_sha"),
        CheckConstraint("length(request_fingerprint_sha256) = 64", name="ck_local_document_receipt_request_sha"),
        Index("ix_local_document_receipt_session", "review_session_id", "accepted_at_utc"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    review_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("local_document_review_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    source_review_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("local_document_review_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    accepted_review_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("local_document_review_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    target_research_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_cases.id", ondelete="RESTRICT"), nullable=False
    )
    source_review_fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    accepted_review_fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    request_fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    acceptance_contract_version: Mapped[str] = mapped_column(String(128), nullable=False)
    accepted_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LocalDocumentAcceptanceLink(Base):
    __tablename__ = "local_document_acceptance_links"
    __table_args__ = (
        UniqueConstraint("receipt_id", "candidate_id", name="uq_local_document_acceptance_candidate"),
        UniqueConstraint("evidence_item_id", name="uq_local_document_acceptance_evidence"),
        UniqueConstraint("claim_revision_id", name="uq_local_document_acceptance_claim_revision"),
        Index("ix_local_document_acceptance_link_receipt", "receipt_id", "candidate_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    receipt_id: Mapped[UUID] = mapped_column(
        ForeignKey("local_document_acceptance_receipts.id", ondelete="RESTRICT"), nullable=False
    )
    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("local_document_candidates.id", ondelete="RESTRICT"), nullable=False
    )
    evidence_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="RESTRICT"), nullable=False
    )
    claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="RESTRICT"), nullable=False
    )
    claim_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    claim_evidence_link_id: Mapped[UUID] = mapped_column(
        ForeignKey("claim_evidence_links.id", ondelete="RESTRICT"), nullable=False
    )


DOCUMENT_IMPORT_MODELS = (
    LocalDocumentContent,
    LocalDocumentImportAttempt,
    LocalDocumentPage,
    LocalDocumentReviewSession,
    LocalDocumentCandidate,
    LocalDocumentReviewRevision,
    LocalDocumentReviewCandidateDecision,
    LocalDocumentAcceptanceReceipt,
    LocalDocumentAcceptanceLink,
)


@event.listens_for(Session, "before_flush")
def reject_document_import_mutation(
    session: Session, _flush_context: object, _instances: object
) -> None:
    """Reject update/delete paths for local document history."""

    for row in session.deleted:
        if isinstance(row, DOCUMENT_IMPORT_MODELS):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows are append-only and cannot be deleted."
            )
    for row in session.dirty:
        if isinstance(row, DOCUMENT_IMPORT_MODELS) and session.is_modified(
            row, include_collections=False
        ):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows are append-only and cannot be updated."
            )
