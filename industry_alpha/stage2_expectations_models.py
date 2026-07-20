"""Append-only v0.6B expectation and valuation snapshot models."""

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
    String,
    UniqueConstraint,
    Uuid,
    event,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.database.models import Base, IDENTITY_TYPE
from industry_alpha.orm_append_only import reject_append_only_mutation


class Stage2MarketExpectation(Base):
    __tablename__ = "stage2_market_expectations"
    __table_args__ = (
        UniqueConstraint(
            "company_research_id",
            "expectation_key",
            name="uq_stage2_expectation_key",
        ),
        Index("ix_stage2_expectation_research", "company_research_id", "expectation_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_research_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research.id", ondelete="RESTRICT"),
        nullable=False,
    )
    expectation_key: Mapped[str] = mapped_column(String(96), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2MarketExpectationRevision(Base):
    __tablename__ = "stage2_market_expectation_revisions"
    __table_args__ = (
        UniqueConstraint(
            "expectation_id",
            "revision_no",
            name="uq_stage2_expectation_revision_no",
        ),
        CheckConstraint("revision_no > 0", name="ck_stage2_expectation_revision_positive"),
        CheckConstraint(
            "expectation_kind IN ('consensus','guidance','market_implied','research_assumption','unknown')",
            name="ck_stage2_expectation_kind",
        ),
        CheckConstraint(
            "direction IN ('positive','negative','mixed','uncertain')",
            name="ck_stage2_expectation_direction",
        ),
        CheckConstraint(
            "status IN ('draft','supported','disputed','rejected')",
            name="ck_stage2_expectation_status",
        ),
        CheckConstraint(
            "confidence IN ('low','medium','high')",
            name="ck_stage2_expectation_confidence",
        ),
        Index("ix_stage2_expectation_revision", "expectation_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    expectation_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_market_expectations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    company_research_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    period_horizon: Mapped[str] = mapped_column(String(300), nullable=False)
    expectation_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    basis: Mapped[str] = mapped_column(String(4000), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage2_market_expectation_revisions.id", ondelete="RESTRICT")
    )


class Stage2ExpectationHypothesisLink(Base):
    __tablename__ = "stage2_expectation_hypothesis_links"
    __table_args__ = (
        UniqueConstraint(
            "expectation_revision_id",
            "hypothesis_revision_id",
            name="uq_stage2_expectation_hypothesis_link",
        ),
        Index(
            "ix_stage2_expectation_hypothesis",
            "expectation_revision_id",
            "hypothesis_revision_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    expectation_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_market_expectation_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    hypothesis_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_financial_hypothesis_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2ExpectationClaimLink(Base):
    __tablename__ = "stage2_expectation_claim_links"
    __table_args__ = (
        UniqueConstraint(
            "expectation_revision_id",
            "claim_revision_id",
            name="uq_stage2_expectation_claim_link",
        ),
        Index("ix_stage2_expectation_claim", "expectation_revision_id", "claim_revision_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    expectation_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_market_expectation_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    claim_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2ExpectationEvidenceLink(Base):
    __tablename__ = "stage2_expectation_evidence_links"
    __table_args__ = (
        UniqueConstraint(
            "expectation_revision_id",
            "claim_evidence_link_id",
            name="uq_stage2_expectation_evidence_link",
        ),
        Index("ix_stage2_expectation_evidence", "expectation_revision_id", "claim_revision_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    expectation_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_market_expectation_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    claim_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    claim_evidence_link_id: Mapped[UUID] = mapped_column(
        ForeignKey("claim_evidence_links.id", ondelete="RESTRICT"), nullable=False
    )
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="RESTRICT"), nullable=False
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2ValuationSnapshot(Base):
    __tablename__ = "stage2_valuation_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "company_research_id",
            "valuation_key",
            name="uq_stage2_valuation_key",
        ),
        Index("ix_stage2_valuation_research", "company_research_id", "valuation_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_research_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research.id", ondelete="RESTRICT"),
        nullable=False,
    )
    valuation_key: Mapped[str] = mapped_column(String(96), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2ValuationSnapshotRevision(Base):
    __tablename__ = "stage2_valuation_snapshot_revisions"
    __table_args__ = (
        UniqueConstraint(
            "valuation_id",
            "revision_no",
            name="uq_stage2_valuation_revision_no",
        ),
        CheckConstraint("revision_no > 0", name="ck_stage2_valuation_revision_positive"),
        CheckConstraint(
            "valuation_method IN ('multiple_observation','asset_reference','historical_range','market_price_context','missing_data')",
            name="ck_stage2_valuation_method",
        ),
        CheckConstraint(
            "status IN ('draft','supported','disputed','rejected')",
            name="ck_stage2_valuation_status",
        ),
        CheckConstraint(
            "confidence IN ('low','medium','high')",
            name="ck_stage2_valuation_confidence",
        ),
        Index("ix_stage2_valuation_revision", "valuation_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    valuation_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_valuation_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    company_research_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    valuation_method: Mapped[str] = mapped_column(String(32), nullable=False)
    metric_context: Mapped[str] = mapped_column(String(1000), nullable=False)
    observed_value: Mapped[str | None] = mapped_column(String(64))
    missing_data_reason: Mapped[str | None] = mapped_column(String(500))
    unit: Mapped[str | None] = mapped_column(String(64))
    currency: Mapped[str | None] = mapped_column(String(16))
    comparison_basis: Mapped[str] = mapped_column(String(1000), nullable=False)
    assumptions: Mapped[str] = mapped_column(String(4000), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    daily_price_id: Mapped[int | None] = mapped_column(
        IDENTITY_TYPE,
        ForeignKey("daily_price.id", ondelete="RESTRICT"),
    )
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage2_valuation_snapshot_revisions.id", ondelete="RESTRICT")
    )


class Stage2ValuationHypothesisLink(Base):
    __tablename__ = "stage2_valuation_hypothesis_links"
    __table_args__ = (
        UniqueConstraint(
            "valuation_revision_id",
            "hypothesis_revision_id",
            name="uq_stage2_valuation_hypothesis_link",
        ),
        Index("ix_stage2_valuation_hypothesis", "valuation_revision_id", "hypothesis_revision_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    valuation_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_valuation_snapshot_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    hypothesis_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_financial_hypothesis_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2ValuationClaimLink(Base):
    __tablename__ = "stage2_valuation_claim_links"
    __table_args__ = (
        UniqueConstraint(
            "valuation_revision_id",
            "claim_revision_id",
            name="uq_stage2_valuation_claim_link",
        ),
        Index("ix_stage2_valuation_claim", "valuation_revision_id", "claim_revision_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    valuation_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_valuation_snapshot_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    claim_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2ValuationEvidenceLink(Base):
    __tablename__ = "stage2_valuation_evidence_links"
    __table_args__ = (
        UniqueConstraint(
            "valuation_revision_id",
            "claim_evidence_link_id",
            name="uq_stage2_valuation_evidence_link",
        ),
        Index("ix_stage2_valuation_evidence", "valuation_revision_id", "claim_revision_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    valuation_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_valuation_snapshot_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    claim_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    claim_evidence_link_id: Mapped[UUID] = mapped_column(
        ForeignKey("claim_evidence_links.id", ondelete="RESTRICT"), nullable=False
    )
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="RESTRICT"), nullable=False
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


STAGE2_EXPECTATION_MODELS = (
    Stage2MarketExpectation,
    Stage2MarketExpectationRevision,
    Stage2ExpectationHypothesisLink,
    Stage2ExpectationClaimLink,
    Stage2ExpectationEvidenceLink,
    Stage2ValuationSnapshot,
    Stage2ValuationSnapshotRevision,
    Stage2ValuationHypothesisLink,
    Stage2ValuationClaimLink,
    Stage2ValuationEvidenceLink,
)


@event.listens_for(Session, "before_flush")
def reject_stage2_expectation_mutation(
    session: Session, _flush_context: object, _instances: object
) -> None:
    reject_append_only_mutation(session, STAGE2_EXPECTATION_MODELS)
