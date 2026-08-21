"""Additive product-workspace metadata over the immutable evidence ledger."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid, event
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.database.models import Base
from industry_alpha.errors import EvidenceLedgerImmutableError


class ProductResearchCaseProfile(Base):
    __tablename__ = "product_research_case_profiles"
    __table_args__ = (
        CheckConstraint("case_type IN ('industry','company')", name="ck_product_case_type"),
        CheckConstraint(
            "(case_type = 'industry' AND company_name IS NULL AND stock_code IS NULL) OR "
            "(case_type = 'company' AND industry_theme IS NULL)",
            name="ck_product_case_scope",
        ),
        Index("ix_product_case_type_title", "case_type", "display_title"),
    )

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_cases.id", ondelete="RESTRICT"), primary_key=True
    )
    case_type: Mapped[str] = mapped_column(String(16), nullable=False)
    display_title: Mapped[str] = mapped_column(String(300), nullable=False)
    industry_theme: Mapped[str | None] = mapped_column(String(300))
    company_name: Mapped[str | None] = mapped_column(String(300))
    stock_code: Mapped[str | None] = mapped_column(String(32))
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProductResearchRevisionContent(Base):
    __tablename__ = "product_research_revision_contents"
    __table_args__ = (
        CheckConstraint("length(content_sha256) = 64", name="ck_product_revision_content_sha"),
        Index("ix_product_revision_recorded", "recorded_at_utc", "revision_id"),
    )

    revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_case_revisions.id", ondelete="RESTRICT"), primary_key=True
    )
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    change_summary: Mapped[str | None] = mapped_column(String(2000))
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProductResearchRevisionEvidenceReference(Base):
    __tablename__ = "product_research_revision_evidence_references"
    __table_args__ = (
        UniqueConstraint("revision_id", "evidence_id", name="uq_product_revision_evidence"),
        UniqueConstraint("revision_id", "citation_order", name="uq_product_revision_citation_order"),
        CheckConstraint("citation_order > 0", name="ck_product_citation_order_positive"),
        Index("ix_product_evidence_reference", "evidence_id", "revision_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_case_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="RESTRICT"), nullable=False
    )
    citation_order: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(String(1000))
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


PRODUCT_WORKSPACE_MODELS = (
    ProductResearchCaseProfile,
    ProductResearchRevisionContent,
    ProductResearchRevisionEvidenceReference,
)


@event.listens_for(Session, "before_flush")
def reject_product_workspace_history_mutation(
    session: Session, _flush_context: object, _instances: object
) -> None:
    for row in session.deleted:
        if isinstance(row, PRODUCT_WORKSPACE_MODELS):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows are append-only and cannot be deleted."
            )
    for row in session.dirty:
        if isinstance(row, PRODUCT_WORKSPACE_MODELS) and session.is_modified(
            row, include_collections=False
        ):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows are append-only and cannot be updated."
            )
