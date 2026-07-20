"""Append-only Stage 2 company-research persistence models."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
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


class Stage2CompanyResearch(Base):
    __tablename__ = "stage2_company_research"
    __table_args__ = (
        UniqueConstraint(
            "candidate_pool_revision_id",
            "candidate_pool_membership_id",
            name="uq_stage2_research_exact_membership",
        ),
        UniqueConstraint(
            "case_id", "map_id", "source", "stock_code", name="uq_stage2_research_company"
        ),
        Index("ix_stage2_research_pool", "candidate_pool_revision_id", "stock_code"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_cases.id", ondelete="RESTRICT"), nullable=False
    )
    map_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_maps.id", ondelete="RESTRICT"), nullable=False
    )
    candidate_pool_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_candidate_pools.id", ondelete="RESTRICT"), nullable=False
    )
    candidate_pool_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_candidate_pool_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    candidate_pool_membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_candidate_pool_memberships.id", ondelete="RESTRICT"),
        nullable=False,
    )
    beneficiary_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiaries.id", ondelete="RESTRICT"), nullable=False
    )
    beneficiary_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiary_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    selected_map_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_map_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    stock_basic_record_id: Mapped[int] = mapped_column(
        IDENTITY_TYPE,
        ForeignKey("stock_basic.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2HandoffAssertionLink(Base):
    __tablename__ = "stage2_handoff_assertion_links"
    __table_args__ = (
        UniqueConstraint(
            "company_research_id",
            "stage1_beneficiary_assertion_link_id",
            name="uq_stage2_handoff_assertion_link",
        ),
        Index(
            "ix_stage2_handoff_assertion",
            "company_research_id",
            "stage1_beneficiary_assertion_link_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_research_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research.id", ondelete="RESTRICT"), nullable=False
    )
    stage1_beneficiary_assertion_link_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiary_assertion_links.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2HandoffEvidenceLink(Base):
    __tablename__ = "stage2_handoff_evidence_links"
    __table_args__ = (
        UniqueConstraint(
            "company_research_id",
            "claim_evidence_link_id",
            name="uq_stage2_handoff_evidence_link",
        ),
        Index("ix_stage2_handoff_evidence", "company_research_id", "claim_revision_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_research_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research.id", ondelete="RESTRICT"), nullable=False
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


class Stage2HandoffClaimLink(Base):
    __tablename__ = "stage2_handoff_claim_links"
    __table_args__ = (
        UniqueConstraint(
            "company_research_id",
            "stage1_beneficiary_claim_link_id",
            name="uq_stage2_handoff_claim_link",
        ),
        Index("ix_stage2_handoff_claim", "company_research_id", "claim_revision_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_research_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research.id", ondelete="RESTRICT"), nullable=False
    )
    stage1_beneficiary_claim_link_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiary_claim_links.id", ondelete="RESTRICT"),
        nullable=False,
    )
    claim_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2CompanyResearchRevision(Base):
    __tablename__ = "stage2_company_research_revisions"
    __table_args__ = (
        UniqueConstraint(
            "company_research_id", "revision_no", name="uq_stage2_research_revision_no"
        ),
        CheckConstraint("revision_no > 0", name="ck_stage2_research_revision_positive"),
        CheckConstraint(
            "workflow_state IN ('open','paused','completed','archived')",
            name="ck_stage2_research_workflow",
        ),
        CheckConstraint(
            "conclusion_status IN ('unassessed','insufficient_evidence','supported','disputed','rejected')",
            name="ck_stage2_research_conclusion",
        ),
        Index("ix_stage2_research_revision", "company_research_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_research_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research.id", ondelete="RESTRICT"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    workflow_state: Mapped[str] = mapped_column(String(16), nullable=False)
    conclusion_status: Mapped[str] = mapped_column(String(32), nullable=False)
    research_question: Mapped[str] = mapped_column(String(2000), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(4000))
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage2_company_research_revisions.id", ondelete="RESTRICT")
    )


class Stage2FinancialHypothesis(Base):
    __tablename__ = "stage2_financial_hypotheses"
    __table_args__ = (
        UniqueConstraint(
            "company_research_id", "hypothesis_key", name="uq_stage2_hypothesis_key"
        ),
        Index("ix_stage2_hypothesis_research", "company_research_id", "hypothesis_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_research_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research.id", ondelete="RESTRICT"), nullable=False
    )
    hypothesis_key: Mapped[str] = mapped_column(String(96), nullable=False)
    stage1_assertion_link_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiary_assertion_links.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2FinancialHypothesisRevision(Base):
    __tablename__ = "stage2_financial_hypothesis_revisions"
    __table_args__ = (
        UniqueConstraint(
            "hypothesis_id", "revision_no", name="uq_stage2_hypothesis_revision_no"
        ),
        UniqueConstraint(
            "id", "hypothesis_id", name="uq_stage2_hypothesis_revision_identity"
        ),
        CheckConstraint("revision_no > 0", name="ck_stage2_hypothesis_revision_positive"),
        CheckConstraint(
            "hypothesis_status IN ('draft','supported','disputed','rejected')",
            name="ck_stage2_hypothesis_status",
        ),
        CheckConstraint(
            "direction IN ('positive','negative','mixed','uncertain')",
            name="ck_stage2_hypothesis_direction",
        ),
        CheckConstraint(
            "confidence IN ('low','medium','high')", name="ck_stage2_hypothesis_confidence"
        ),
        Index("ix_stage2_hypothesis_revision", "hypothesis_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    hypothesis_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_financial_hypotheses.id", ondelete="RESTRICT"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    hypothesis_status: Mapped[str] = mapped_column(String(16), nullable=False)
    mechanism: Mapped[str] = mapped_column(String(4000), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    operating_metric: Mapped[str] = mapped_column(String(300), nullable=False)
    financial_statement_line: Mapped[str] = mapped_column(String(300), nullable=False)
    expected_lag_horizon: Mapped[str] = mapped_column(String(300), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    basis: Mapped[str] = mapped_column(String(4000), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage2_financial_hypothesis_revisions.id", ondelete="RESTRICT")
    )


class Stage2HypothesisClaimLink(Base):
    __tablename__ = "stage2_hypothesis_claim_links"
    __table_args__ = (
        UniqueConstraint(
            "hypothesis_revision_id",
            "claim_revision_id",
            name="uq_stage2_hypothesis_claim_link",
        ),
        Index("ix_stage2_hypothesis_claim", "hypothesis_revision_id", "claim_revision_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    hypothesis_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_financial_hypothesis_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    claim_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2HypothesisEvidenceLink(Base):
    __tablename__ = "stage2_hypothesis_evidence_links"
    __table_args__ = (
        UniqueConstraint(
            "hypothesis_revision_id",
            "claim_evidence_link_id",
            name="uq_stage2_hypothesis_evidence_link",
        ),
        Index(
            "ix_stage2_hypothesis_evidence", "hypothesis_revision_id", "claim_revision_id"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    hypothesis_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_financial_hypothesis_revisions.id", ondelete="RESTRICT"),
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


class Stage2ResearchHypothesisLink(Base):
    __tablename__ = "stage2_research_hypothesis_links"
    __table_args__ = (
        UniqueConstraint(
            "company_research_revision_id",
            "hypothesis_id",
            name="uq_stage2_research_hypothesis_identity",
        ),
        UniqueConstraint(
            "company_research_revision_id",
            "hypothesis_revision_id",
            name="uq_stage2_research_hypothesis_revision",
        ),
        ForeignKeyConstraint(
            ["hypothesis_revision_id", "hypothesis_id"],
            [
                "stage2_financial_hypothesis_revisions.id",
                "stage2_financial_hypothesis_revisions.hypothesis_id",
            ],
            name="fk_stage2_research_exact_hypothesis_revision",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_stage2_research_hypothesis",
            "company_research_revision_id",
            "hypothesis_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_research_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    hypothesis_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_financial_hypotheses.id", ondelete="RESTRICT"), nullable=False
    )
    hypothesis_revision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2VerificationItem(Base):
    __tablename__ = "stage2_verification_items"
    __table_args__ = (
        UniqueConstraint(
            "company_research_revision_id",
            "item_no",
            name="uq_stage2_verification_item_no",
        ),
        CheckConstraint("item_no > 0", name="ck_stage2_verification_item_positive"),
        CheckConstraint(
            "status IN ('open','completed','deferred')",
            name="ck_stage2_verification_status",
        ),
        Index(
            "ix_stage2_verification_item", "company_research_revision_id", "item_no"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_research_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    item_no: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


STAGE2_MODELS = (
    Stage2CompanyResearch,
    Stage2HandoffAssertionLink,
    Stage2HandoffClaimLink,
    Stage2HandoffEvidenceLink,
    Stage2CompanyResearchRevision,
    Stage2FinancialHypothesis,
    Stage2FinancialHypothesisRevision,
    Stage2HypothesisClaimLink,
    Stage2HypothesisEvidenceLink,
    Stage2ResearchHypothesisLink,
    Stage2VerificationItem,
)


@event.listens_for(Session, "before_flush")
def reject_stage2_mutation(
    session: Session, _flush_context: object, _instances: object
) -> None:
    """Reject ordinary ORM updates and deletes for accepted Stage 2 rows."""
    reject_append_only_mutation(session, STAGE2_MODELS)
