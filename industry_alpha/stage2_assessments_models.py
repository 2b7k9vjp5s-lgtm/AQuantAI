"""Append-only v0.6C catalyst and company-risk assessment models."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, event
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.database.models import Base
from industry_alpha.errors import EvidenceLedgerImmutableError


ASSESSMENT_STATUS_CHECK = "status IN ('draft','supported','disputed','rejected')"
CONFIDENCE_CHECK = "confidence IN ('low','medium','high')"


class Stage2CatalystAssessment(Base):
    __tablename__ = "stage2_catalyst_assessments"
    __table_args__ = (
        UniqueConstraint("company_research_id", "catalyst_key", name="uq_stage2_catalyst_key"),
        Index("ix_stage2_catalyst_research", "company_research_id", "catalyst_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_research_id: Mapped[UUID] = mapped_column(ForeignKey("stage2_company_research.id", ondelete="RESTRICT"), nullable=False)
    catalyst_key: Mapped[str] = mapped_column(String(96), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2CatalystAssessmentRevision(Base):
    __tablename__ = "stage2_catalyst_assessment_revisions"
    __table_args__ = (
        UniqueConstraint("catalyst_id", "revision_no", name="uq_stage2_catalyst_revision_no"),
        CheckConstraint("revision_no > 0", name="ck_stage2_catalyst_revision_positive"),
        CheckConstraint("catalyst_category IN ('demand','supply','product','customer','certification','capacity','policy','financial','operational','other')", name="ck_stage2_catalyst_category"),
        CheckConstraint(ASSESSMENT_STATUS_CHECK, name="ck_stage2_catalyst_status"),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_stage2_catalyst_confidence"),
        Index("ix_stage2_catalyst_revision", "catalyst_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    catalyst_id: Mapped[UUID] = mapped_column(ForeignKey("stage2_catalyst_assessments.id", ondelete="RESTRICT"), nullable=False)
    company_research_revision_id: Mapped[UUID] = mapped_column(ForeignKey("stage2_company_research_revisions.id", ondelete="RESTRICT"), nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    catalyst_category: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    expected_observation_window: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    trigger_observation_criteria: Mapped[str] = mapped_column(String(2000), nullable=False)
    basis: Mapped[str] = mapped_column(String(4000), nullable=False)
    uncertainty: Mapped[str] = mapped_column(String(2000), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("stage2_catalyst_assessment_revisions.id", ondelete="RESTRICT"))


class Stage2RiskAssessment(Base):
    __tablename__ = "stage2_risk_assessments"
    __table_args__ = (
        UniqueConstraint("company_research_id", "risk_key", name="uq_stage2_risk_key"),
        Index("ix_stage2_risk_research", "company_research_id", "risk_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_research_id: Mapped[UUID] = mapped_column(ForeignKey("stage2_company_research.id", ondelete="RESTRICT"), nullable=False)
    risk_key: Mapped[str] = mapped_column(String(96), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2RiskAssessmentRevision(Base):
    __tablename__ = "stage2_risk_assessment_revisions"
    __table_args__ = (
        UniqueConstraint("risk_id", "revision_no", name="uq_stage2_risk_revision_no"),
        CheckConstraint("revision_no > 0", name="ck_stage2_risk_revision_positive"),
        CheckConstraint("risk_category IN ('demand','supply','execution','competition','customer','policy','financial','governance','operational','other')", name="ck_stage2_risk_category"),
        CheckConstraint(ASSESSMENT_STATUS_CHECK, name="ck_stage2_risk_status"),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_stage2_risk_confidence"),
        Index("ix_stage2_risk_revision", "risk_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    risk_id: Mapped[UUID] = mapped_column(ForeignKey("stage2_risk_assessments.id", ondelete="RESTRICT"), nullable=False)
    company_research_revision_id: Mapped[UUID] = mapped_column(ForeignKey("stage2_company_research_revisions.id", ondelete="RESTRICT"), nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_category: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    downside_path: Mapped[str] = mapped_column(String(2000), nullable=False)
    thesis_invalidation_condition: Mapped[str] = mapped_column(String(2000), nullable=False)
    mitigants: Mapped[str] = mapped_column(String(2000), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    basis: Mapped[str] = mapped_column(String(4000), nullable=False)
    uncertainty: Mapped[str] = mapped_column(String(2000), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("stage2_risk_assessment_revisions.id", ondelete="RESTRICT"))


def _link_model(name: str, table: str, revision_table: str, revision_field: str, upstream_table: str, upstream_field: str, index_name: str):
    return type(
        name,
        (Base,),
        {
            "__tablename__": table,
            "__table_args__": (
                UniqueConstraint(revision_field, upstream_field, name=f"uq_{table}"),
                Index(index_name, revision_field, upstream_field),
            ),
            "__annotations__": {
                "id": Mapped[UUID],
                revision_field: Mapped[UUID],
                upstream_field: Mapped[UUID],
                "recorded_at_utc": Mapped[datetime],
            },
            "id": mapped_column(Uuid, primary_key=True, default=uuid4),
            revision_field: mapped_column(ForeignKey(f"{revision_table}.id", ondelete="RESTRICT"), nullable=False),
            upstream_field: mapped_column(ForeignKey(f"{upstream_table}.id", ondelete="RESTRICT"), nullable=False),
            "recorded_at_utc": mapped_column(DateTime(timezone=True), nullable=False),
        },
    )


Stage2CatalystHypothesisLink = _link_model("Stage2CatalystHypothesisLink", "stage2_catalyst_hypothesis_links", "stage2_catalyst_assessment_revisions", "catalyst_revision_id", "stage2_financial_hypothesis_revisions", "hypothesis_revision_id", "ix_stage2_catalyst_hypothesis")
Stage2CatalystExpectationLink = _link_model("Stage2CatalystExpectationLink", "stage2_catalyst_expectation_links", "stage2_catalyst_assessment_revisions", "catalyst_revision_id", "stage2_market_expectation_revisions", "expectation_revision_id", "ix_stage2_catalyst_expectation")
Stage2CatalystValuationLink = _link_model("Stage2CatalystValuationLink", "stage2_catalyst_valuation_links", "stage2_catalyst_assessment_revisions", "catalyst_revision_id", "stage2_valuation_snapshot_revisions", "valuation_revision_id", "ix_stage2_catalyst_valuation")
Stage2CatalystClaimLink = _link_model("Stage2CatalystClaimLink", "stage2_catalyst_claim_links", "stage2_catalyst_assessment_revisions", "catalyst_revision_id", "claim_revisions", "claim_revision_id", "ix_stage2_catalyst_claim")

Stage2RiskHypothesisLink = _link_model("Stage2RiskHypothesisLink", "stage2_risk_hypothesis_links", "stage2_risk_assessment_revisions", "risk_revision_id", "stage2_financial_hypothesis_revisions", "hypothesis_revision_id", "ix_stage2_risk_hypothesis")
Stage2RiskExpectationLink = _link_model("Stage2RiskExpectationLink", "stage2_risk_expectation_links", "stage2_risk_assessment_revisions", "risk_revision_id", "stage2_market_expectation_revisions", "expectation_revision_id", "ix_stage2_risk_expectation")
Stage2RiskValuationLink = _link_model("Stage2RiskValuationLink", "stage2_risk_valuation_links", "stage2_risk_assessment_revisions", "risk_revision_id", "stage2_valuation_snapshot_revisions", "valuation_revision_id", "ix_stage2_risk_valuation")
Stage2RiskClaimLink = _link_model("Stage2RiskClaimLink", "stage2_risk_claim_links", "stage2_risk_assessment_revisions", "risk_revision_id", "claim_revisions", "claim_revision_id", "ix_stage2_risk_claim")


class Stage2CatalystEvidenceLink(Base):
    __tablename__ = "stage2_catalyst_evidence_links"
    __table_args__ = (
        UniqueConstraint("catalyst_revision_id", "claim_evidence_link_id", name="uq_stage2_catalyst_evidence_link"),
        Index("ix_stage2_catalyst_evidence", "catalyst_revision_id", "claim_revision_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    catalyst_revision_id: Mapped[UUID] = mapped_column(ForeignKey("stage2_catalyst_assessment_revisions.id", ondelete="RESTRICT"), nullable=False)
    claim_revision_id: Mapped[UUID] = mapped_column(ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False)
    claim_evidence_link_id: Mapped[UUID] = mapped_column(ForeignKey("claim_evidence_links.id", ondelete="RESTRICT"), nullable=False)
    evidence_id: Mapped[UUID] = mapped_column(ForeignKey("evidence_items.id", ondelete="RESTRICT"), nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2RiskEvidenceLink(Base):
    __tablename__ = "stage2_risk_evidence_links"
    __table_args__ = (
        UniqueConstraint("risk_revision_id", "claim_evidence_link_id", name="uq_stage2_risk_evidence_link"),
        Index("ix_stage2_risk_evidence", "risk_revision_id", "claim_revision_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    risk_revision_id: Mapped[UUID] = mapped_column(ForeignKey("stage2_risk_assessment_revisions.id", ondelete="RESTRICT"), nullable=False)
    claim_revision_id: Mapped[UUID] = mapped_column(ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False)
    claim_evidence_link_id: Mapped[UUID] = mapped_column(ForeignKey("claim_evidence_links.id", ondelete="RESTRICT"), nullable=False)
    evidence_id: Mapped[UUID] = mapped_column(ForeignKey("evidence_items.id", ondelete="RESTRICT"), nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


STAGE2_ASSESSMENT_MODELS = (
    Stage2CatalystAssessment, Stage2CatalystAssessmentRevision,
    Stage2CatalystHypothesisLink, Stage2CatalystExpectationLink, Stage2CatalystValuationLink,
    Stage2CatalystClaimLink, Stage2CatalystEvidenceLink,
    Stage2RiskAssessment, Stage2RiskAssessmentRevision,
    Stage2RiskHypothesisLink, Stage2RiskExpectationLink, Stage2RiskValuationLink,
    Stage2RiskClaimLink, Stage2RiskEvidenceLink,
)


@event.listens_for(Session, "before_flush")
def reject_stage2_assessment_mutation(session: Session, _flush_context: object, _instances: object) -> None:
    for row in session.deleted:
        if isinstance(row, STAGE2_ASSESSMENT_MODELS):
            raise EvidenceLedgerImmutableError(f"{type(row).__name__} rows are append-only and cannot be deleted.")
    for row in session.dirty:
        if isinstance(row, STAGE2_ASSESSMENT_MODELS) and session.is_modified(row, include_collections=False):
            raise EvidenceLedgerImmutableError(f"{type(row).__name__} rows are append-only and cannot be updated.")
