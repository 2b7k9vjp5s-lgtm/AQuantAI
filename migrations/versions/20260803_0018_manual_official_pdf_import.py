"""Add immutable local PDF import and reviewed Evidence Ledger bridge.

Revision ID: 20260803_0018
Revises: 20260725_0017
Create Date: 2026-08-03
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260803_0018"
down_revision: str | None = "20260725_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "local_document_acceptance_links",
    "local_document_acceptance_receipts",
    "local_document_review_candidate_decisions",
    "local_document_review_revisions",
    "local_document_candidates",
    "local_document_review_sessions",
    "local_document_pages",
    "local_document_import_attempts",
    "local_document_contents",
)


def upgrade() -> None:
    op.create_table(
        "local_document_contents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("content_sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("media_type", sa.String(32), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("raw_pdf_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("embedded_text_page_count", sa.Integer(), nullable=False),
        sa.Column("total_text_char_count", sa.Integer(), nullable=False),
        sa.Column("extractor_contract_version", sa.String(128), nullable=False),
        sa.Column("extractor_package", sa.String(64), nullable=False),
        sa.Column("extractor_version", sa.String(32), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(content_sha256) = 64", name="ck_local_document_content_sha"),
        sa.CheckConstraint("media_type = 'application/pdf'", name="ck_local_document_media_type"),
        sa.CheckConstraint("byte_size > 0 AND byte_size <= 52428800", name="ck_local_document_byte_size"),
        sa.CheckConstraint("page_count BETWEEN 1 AND 300", name="ck_local_document_page_count"),
        sa.CheckConstraint("embedded_text_page_count BETWEEN 1 AND page_count", name="ck_local_document_embedded_pages"),
        sa.CheckConstraint("total_text_char_count BETWEEN 1 AND 5000000", name="ck_local_document_text_count"),
    )
    op.create_table(
        "local_document_import_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("content_id", sa.Uuid(), sa.ForeignKey("local_document_contents.id", ondelete="RESTRICT")),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(300), nullable=False),
        sa.Column("observed_media_type", sa.String(128), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("admission_state", sa.String(32), nullable=False),
        sa.Column("admission_reason", sa.String(64), nullable=False),
        sa.Column("imported_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(content_sha256) = 64", name="ck_local_document_attempt_sha"),
        sa.CheckConstraint("byte_size >= 0", name="ck_local_document_attempt_size"),
        sa.CheckConstraint("admission_state IN ('admitted','rejected','exact_content_duplicate','filename_content_conflict')", name="ck_local_document_admission_state"),
    )
    op.create_index("ix_local_document_attempt_imported", "local_document_import_attempts", ["imported_at_utc", "id"])
    op.create_index("ix_local_document_attempt_filename", "local_document_import_attempts", ["original_filename", "content_sha256"])
    op.create_table(
        "local_document_pages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("content_id", sa.Uuid(), sa.ForeignKey("local_document_contents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text_state", sa.String(32), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("text_char_count", sa.Integer(), nullable=False),
        sa.UniqueConstraint("content_id", "page_number", name="uq_local_document_page_number"),
        sa.CheckConstraint("page_number BETWEEN 1 AND 300", name="ck_local_document_page_number"),
        sa.CheckConstraint("text_state IN ('embedded_text_present','empty')", name="ck_local_document_page_state"),
        sa.CheckConstraint("length(text_sha256) = 64", name="ck_local_document_page_sha"),
        sa.CheckConstraint("text_char_count BETWEEN 0 AND 100000", name="ck_local_document_page_chars"),
    )
    op.create_index("ix_local_document_page_content", "local_document_pages", ["content_id", "page_number"])
    op.create_table(
        "local_document_review_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("import_attempt_id", sa.Uuid(), sa.ForeignKey("local_document_import_attempts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("target_research_case_id", sa.Uuid(), sa.ForeignKey("research_cases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("import_attempt_id", "target_research_case_id", name="uq_local_document_review_target"),
    )
    op.create_index("ix_local_document_review_case", "local_document_review_sessions", ["target_research_case_id", "created_at_utc"])
    op.create_table(
        "local_document_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("review_session_id", sa.Uuid(), sa.ForeignKey("local_document_review_sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("candidate_kind", sa.String(32), nullable=False),
        sa.Column("page_number", sa.Integer()),
        sa.Column("start_utf8_byte", sa.Integer()),
        sa.Column("end_utf8_byte", sa.Integer()),
        sa.Column("quote_text", sa.Text()),
        sa.Column("quote_sha256", sa.String(64)),
        sa.Column("statement", sa.String(4000)),
        sa.Column("candidate_payload_json", sa.Text(), nullable=False),
        sa.Column("candidate_fingerprint_sha256", sa.String(64), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("review_session_id", "candidate_fingerprint_sha256", name="uq_local_document_candidate_fingerprint"),
        sa.CheckConstraint("candidate_kind IN ('document_identity','company_identity','fact','event')", name="ck_local_document_candidate_kind"),
        sa.CheckConstraint("length(candidate_fingerprint_sha256) = 64", name="ck_local_document_candidate_sha"),
        sa.CheckConstraint("(candidate_kind IN ('fact','event') AND page_number IS NOT NULL AND start_utf8_byte IS NOT NULL AND end_utf8_byte IS NOT NULL AND quote_text IS NOT NULL AND quote_sha256 IS NOT NULL AND statement IS NOT NULL AND start_utf8_byte >= 0 AND end_utf8_byte > start_utf8_byte) OR (candidate_kind IN ('document_identity','company_identity') AND page_number IS NULL AND start_utf8_byte IS NULL AND end_utf8_byte IS NULL AND quote_text IS NULL AND quote_sha256 IS NULL AND statement IS NULL)", name="ck_local_document_candidate_shape"),
    )
    op.create_index("ix_local_document_candidate_session", "local_document_candidates", ["review_session_id", "id"])
    op.create_table(
        "local_document_review_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("review_session_id", sa.Uuid(), sa.ForeignKey("local_document_review_sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("review_state", sa.String(16), nullable=False),
        sa.Column("review_fingerprint_sha256", sa.String(64), nullable=False),
        sa.Column("expected_previous_revision_number", sa.Integer(), nullable=False),
        sa.Column("source_kind", sa.String(32), nullable=False),
        sa.Column("evidence_grade", sa.String(1), nullable=False),
        sa.Column("document_identity_candidate_id", sa.Uuid(), sa.ForeignKey("local_document_candidates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("subject_candidate_id", sa.Uuid(), sa.ForeignKey("local_document_candidates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("information_date", sa.Date(), nullable=False),
        sa.Column("reviewer_note", sa.String(2000)),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_review_revision_id", sa.Uuid(), sa.ForeignKey("local_document_review_revisions.id", ondelete="RESTRICT")),
        sa.UniqueConstraint("review_session_id", "revision_number", name="uq_local_document_review_revision_number"),
        sa.UniqueConstraint("supersedes_review_revision_id", name="uq_local_document_review_successor"),
        sa.CheckConstraint("revision_number > 0", name="ck_local_document_review_revision_positive"),
        sa.CheckConstraint("review_state IN ('draft','deferred','rejected','accepted')", name="ck_local_document_review_state"),
        sa.CheckConstraint("length(review_fingerprint_sha256) = 64", name="ck_local_document_review_sha"),
        sa.CheckConstraint("evidence_grade IN ('A','B','C','D')", name="ck_local_document_review_grade"),
    )
    op.create_index("ix_local_document_review_revision", "local_document_review_revisions", ["review_session_id", "revision_number"])
    op.create_table(
        "local_document_review_candidate_decisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("review_revision_id", sa.Uuid(), sa.ForeignKey("local_document_review_revisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("local_document_candidates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("claim_operation", sa.String(48)),
        sa.Column("claim_key", sa.String(96)),
        sa.Column("claim_status", sa.String(16)),
        sa.Column("evidence_relation", sa.String(16)),
        sa.Column("decision_fingerprint_sha256", sa.String(64), nullable=False),
        sa.UniqueConstraint("review_revision_id", "candidate_id", name="uq_local_document_review_decision"),
        sa.CheckConstraint("decision IN ('selected','rejected','deferred')", name="ck_local_document_decision"),
        sa.CheckConstraint("claim_operation IS NULL OR claim_operation = 'create_new_deterministic_claim'", name="ck_local_document_claim_operation"),
        sa.CheckConstraint("length(decision_fingerprint_sha256) = 64", name="ck_local_document_decision_sha"),
    )
    op.create_index("ix_local_document_decision_revision", "local_document_review_candidate_decisions", ["review_revision_id", "candidate_id"])
    op.create_table(
        "local_document_acceptance_receipts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("review_session_id", sa.Uuid(), sa.ForeignKey("local_document_review_sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_review_revision_id", sa.Uuid(), sa.ForeignKey("local_document_review_revisions.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("accepted_review_revision_id", sa.Uuid(), sa.ForeignKey("local_document_review_revisions.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("target_research_case_id", sa.Uuid(), sa.ForeignKey("research_cases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_review_fingerprint_sha256", sa.String(64), nullable=False),
        sa.Column("accepted_review_fingerprint_sha256", sa.String(64), nullable=False),
        sa.Column("request_fingerprint_sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("acceptance_contract_version", sa.String(128), nullable=False),
        sa.Column("accepted_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(source_review_fingerprint_sha256) = 64", name="ck_local_document_receipt_source_sha"),
        sa.CheckConstraint("length(accepted_review_fingerprint_sha256) = 64", name="ck_local_document_receipt_accepted_sha"),
        sa.CheckConstraint("length(request_fingerprint_sha256) = 64", name="ck_local_document_receipt_request_sha"),
    )
    op.create_index("ix_local_document_receipt_session", "local_document_acceptance_receipts", ["review_session_id", "accepted_at_utc"])
    op.create_table(
        "local_document_acceptance_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("receipt_id", sa.Uuid(), sa.ForeignKey("local_document_acceptance_receipts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("local_document_candidates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evidence_item_id", sa.Uuid(), sa.ForeignKey("evidence_items.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("claim_id", sa.Uuid(), sa.ForeignKey("claims.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("claim_revision_id", sa.Uuid(), sa.ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("claim_evidence_link_id", sa.Uuid(), sa.ForeignKey("claim_evidence_links.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("receipt_id", "candidate_id", name="uq_local_document_acceptance_candidate"),
    )
    op.create_index("ix_local_document_acceptance_link_receipt", "local_document_acceptance_links", ["receipt_id", "candidate_id"])


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in _TABLES:
        table = sa.table(table_name, sa.column("id"))
        if bind.execute(sa.select(sa.literal(1)).select_from(table).limit(1)).first():
            raise RuntimeError(
                "Cannot downgrade local document import while immutable import, review, "
                "or acceptance history exists. Preserve the database."
            )
    for table_name in _TABLES:
        op.drop_table(table_name)
