"""SQLAlchemy models for immutable Industry Alpha ledger history."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, event
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.database.models import Base
from industry_alpha.errors import EvidenceLedgerImmutableError


class ResearchCase(Base):
    __tablename__ = "research_cases"
    __table_args__ = (
        CheckConstraint("origin IN ('manual', 'fixture')", name="ck_research_cases_origin"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_key: Mapped[str] = mapped_column(String(96), nullable=False, unique=True)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    origin: Mapped[str] = mapped_column(String(16), nullable=False)


class ResearchCaseRevision(Base):
    __tablename__ = "research_case_revisions"
    __table_args__ = (
        UniqueConstraint("case_id", "revision_no", name="uq_case_revision_number"),
        CheckConstraint("revision_no > 0", name="ck_case_revision_number_positive"),
        CheckConstraint("workflow_state IN ('open','paused','completed','archived')", name="ck_case_revision_workflow"),
        CheckConstraint("conclusion_status IN ('unassessed','insufficient_evidence','supported','disputed','rejected')", name="ck_case_revision_conclusion"),
        Index("ix_case_revision_case_number", "case_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("research_cases.id", ondelete="RESTRICT"), nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    research_question: Mapped[str] = mapped_column(String(2000), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(4000))
    workflow_state: Mapped[str] = mapped_column(String(16), nullable=False)
    conclusion_status: Mapped[str] = mapped_column(String(32), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("research_case_revisions.id", ondelete="RESTRICT"))


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    __table_args__ = (
        CheckConstraint("evidence_grade IN ('A','B','C','D')", name="ck_evidence_grade"),
        CheckConstraint("source_kind IN ('official','regulatory','filing','statistics','company','research','media','industry','community','other')", name="ck_evidence_source_kind"),
        UniqueConstraint("case_id", "content_fingerprint", name="uq_evidence_case_fingerprint"),
        Index("ix_evidence_case_information", "case_id", "information_date", "recorded_at_utc"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("research_cases.id", ondelete="RESTRICT"), nullable=False)
    evidence_grade: Mapped[str] = mapped_column(String(1), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_title: Mapped[str] = mapped_column(String(500), nullable=False)
    publisher_or_author: Mapped[str | None] = mapped_column(String(300))
    source_locator: Mapped[str | None] = mapped_column(String(1500))
    information_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary: Mapped[str] = mapped_column(String(4000), nullable=False)
    content_fingerprint: Mapped[str | None] = mapped_column(String(128))
    supersedes_evidence_id: Mapped[UUID | None] = mapped_column(ForeignKey("evidence_items.id", ondelete="RESTRICT"))


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (UniqueConstraint("case_id", "claim_key", name="uq_claim_case_key"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("research_cases.id", ondelete="RESTRICT"), nullable=False)
    claim_key: Mapped[str] = mapped_column(String(96), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ClaimRevision(Base):
    __tablename__ = "claim_revisions"
    __table_args__ = (
        UniqueConstraint("claim_id", "revision_no", name="uq_claim_revision_number"),
        CheckConstraint("revision_no > 0", name="ck_claim_revision_number_positive"),
        CheckConstraint("claim_kind IN ('fact','inference')", name="ck_claim_revision_kind"),
        CheckConstraint("claim_status IN ('draft','supported','disputed','rejected')", name="ck_claim_revision_status"),
        CheckConstraint("inference_confidence IS NULL OR inference_confidence IN ('low','medium','high')", name="ck_claim_revision_confidence"),
        CheckConstraint("(claim_kind = 'fact' AND inference_confidence IS NULL AND inference_basis IS NULL) OR (claim_kind = 'inference' AND inference_confidence IS NOT NULL AND length(trim(inference_basis)) > 0)", name="ck_claim_revision_inference_fields"),
        Index("ix_claim_revision_claim_number", "claim_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id", ondelete="RESTRICT"), nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    statement: Mapped[str] = mapped_column(String(4000), nullable=False)
    claim_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    claim_status: Mapped[str] = mapped_column(String(16), nullable=False)
    inference_confidence: Mapped[str | None] = mapped_column(String(16))
    inference_basis: Mapped[str | None] = mapped_column(String(4000))
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("claim_revisions.id", ondelete="RESTRICT"))


class ClaimEvidenceLink(Base):
    __tablename__ = "claim_evidence_links"
    __table_args__ = (
        UniqueConstraint("claim_revision_id", "evidence_id", "relation", name="uq_claim_evidence_relation"),
        CheckConstraint("relation IN ('supports','contradicts','context')", name="ck_claim_evidence_relation"),
        Index("ix_claim_evidence_revision", "claim_revision_id", "relation", "evidence_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    claim_revision_id: Mapped[UUID] = mapped_column(ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False)
    evidence_id: Mapped[UUID] = mapped_column(ForeignKey("evidence_items.id", ondelete="RESTRICT"), nullable=False)
    relation: Mapped[str] = mapped_column(String(16), nullable=False)
    link_note: Mapped[str | None] = mapped_column(String(1000))
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CaseRevisionClaimLink(Base):
    __tablename__ = "case_revision_claim_links"
    __table_args__ = (
        UniqueConstraint("case_revision_id", "claim_revision_id", "role", name="uq_case_revision_claim_role"),
        CheckConstraint("role IN ('conclusion','context','risk')", name="ck_case_revision_claim_role"),
        Index("ix_case_revision_claim", "case_revision_id", "role", "claim_revision_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_revision_id: Mapped[UUID] = mapped_column(ForeignKey("research_case_revisions.id", ondelete="RESTRICT"), nullable=False)
    claim_revision_id: Mapped[UUID] = mapped_column(ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VerificationItem(Base):
    __tablename__ = "verification_items"
    __table_args__ = (
        UniqueConstraint("case_revision_id", "item_no", name="uq_verification_item_number"),
        CheckConstraint("item_no > 0", name="ck_verification_item_number_positive"),
        CheckConstraint("status IN ('open','completed','deferred')", name="ck_verification_item_status"),
        Index("ix_verification_case_revision_number", "case_revision_id", "item_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_revision_id: Mapped[UUID] = mapped_column(ForeignKey("research_case_revisions.id", ondelete="RESTRICT"), nullable=False)
    item_no: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


LEDGER_MODELS = (
    ResearchCase, ResearchCaseRevision, EvidenceItem, Claim, ClaimRevision,
    ClaimEvidenceLink, CaseRevisionClaimLink, VerificationItem,
)


@event.listens_for(Session, "before_flush")
def reject_accepted_ledger_mutation(session: Session, _flush_context: object, _instances: object) -> None:
    """Reject ordinary ORM update/delete paths for accepted ledger rows."""
    for row in session.deleted:
        if isinstance(row, LEDGER_MODELS):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows are append-only and cannot be deleted."
            )
    for row in session.dirty:
        if isinstance(row, LEDGER_MODELS) and session.is_modified(row, include_collections=False):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows are append-only and cannot be updated."
            )
