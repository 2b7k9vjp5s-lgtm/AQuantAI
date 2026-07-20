"""Append-only v0.6D industry and company quality judgment models."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, event
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.database.models import Base
from industry_alpha.orm_append_only import reject_append_only_mutation


OUTCOME_CHECK = "outcome IN ('affirmed','not_affirmed','uncertain','not_assessed')"
EVIDENCE_STATE_CHECK = "evidence_state IN ('supported','disputed','insufficient_evidence')"
CONFIDENCE_CHECK = "confidence IN ('low','medium','high')"


class Stage2IndustryJudgment(Base):
    __tablename__ = "stage2_industry_judgments"
    __table_args__ = (
        UniqueConstraint("company_research_id", "judgment_key", name="uq_stage2_industry_judgment_key"),
        Index("ix_stage2_industry_judgment_research", "company_research_id", "judgment_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_research_id: Mapped[UUID] = mapped_column(ForeignKey("stage2_company_research.id", ondelete="RESTRICT"), nullable=False)
    judgment_key: Mapped[str] = mapped_column(String(96), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2CompanyJudgment(Base):
    __tablename__ = "stage2_company_judgments"
    __table_args__ = (
        UniqueConstraint("company_research_id", "judgment_key", name="uq_stage2_company_judgment_key"),
        Index("ix_stage2_company_judgment_research", "company_research_id", "judgment_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_research_id: Mapped[UUID] = mapped_column(ForeignKey("stage2_company_research.id", ondelete="RESTRICT"), nullable=False)
    judgment_key: Mapped[str] = mapped_column(String(96), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class _JudgmentRevisionMixin:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_research_revision_id: Mapped[UUID] = mapped_column(ForeignKey("stage2_company_research_revisions.id", ondelete="RESTRICT"), nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    evidence_state: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    decision_criteria: Mapped[str] = mapped_column(String(2000), nullable=False)
    rationale: Mapped[str] = mapped_column(String(4000), nullable=False)
    uncertainty: Mapped[str] = mapped_column(String(2000), nullable=False)
    follow_up_verification: Mapped[str] = mapped_column(String(3000), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2IndustryJudgmentRevision(_JudgmentRevisionMixin, Base):
    __tablename__ = "stage2_industry_judgment_revisions"
    __table_args__ = (
        UniqueConstraint("judgment_id", "revision_no", name="uq_stage2_industry_judgment_revision_no"),
        CheckConstraint("revision_no > 0", name="ck_stage2_industry_judgment_revision_positive"),
        CheckConstraint(OUTCOME_CHECK, name="ck_stage2_industry_judgment_outcome"),
        CheckConstraint(EVIDENCE_STATE_CHECK, name="ck_stage2_industry_judgment_evidence_state"),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_stage2_industry_judgment_confidence"),
        Index("ix_stage2_industry_judgment_revision", "judgment_id", "revision_no"),
    )

    judgment_id: Mapped[UUID] = mapped_column(ForeignKey("stage2_industry_judgments.id", ondelete="RESTRICT"), nullable=False)
    driver_durability: Mapped[str] = mapped_column(String(2000), nullable=False)
    value_pool_direction: Mapped[str] = mapped_column(String(2000), nullable=False)
    chain_bottleneck_support: Mapped[str] = mapped_column(String(2000), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("stage2_industry_judgment_revisions.id", ondelete="RESTRICT"))


class Stage2CompanyJudgmentRevision(_JudgmentRevisionMixin, Base):
    __tablename__ = "stage2_company_judgment_revisions"
    __table_args__ = (
        UniqueConstraint("judgment_id", "revision_no", name="uq_stage2_company_judgment_revision_no"),
        CheckConstraint("revision_no > 0", name="ck_stage2_company_judgment_revision_positive"),
        CheckConstraint(OUTCOME_CHECK, name="ck_stage2_company_judgment_outcome"),
        CheckConstraint(EVIDENCE_STATE_CHECK, name="ck_stage2_company_judgment_evidence_state"),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_stage2_company_judgment_confidence"),
        Index("ix_stage2_company_judgment_revision", "judgment_id", "revision_no"),
    )

    judgment_id: Mapped[UUID] = mapped_column(ForeignKey("stage2_company_judgments.id", ondelete="RESTRICT"), nullable=False)
    beneficiary_credibility: Mapped[str] = mapped_column(String(2000), nullable=False)
    financial_transmission_credibility: Mapped[str] = mapped_column(String(2000), nullable=False)
    execution_risks: Mapped[str] = mapped_column(String(2000), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("stage2_company_judgment_revisions.id", ondelete="RESTRICT"))


def _link_model(name: str, table: str, kind: str, upstream: str, upstream_table: str):
    revision_field = "judgment_revision_id"
    upstream_field = f"{upstream}_revision_id"
    return type(name, (Base,), {
        "__tablename__": table,
        "__table_args__": (
            UniqueConstraint(revision_field, upstream_field, name=f"uq_{table}"),
            Index(f"ix_stage2_{kind}_judgment_{upstream}", revision_field, upstream_field),
        ),
        "__annotations__": {
            "id": Mapped[UUID], revision_field: Mapped[UUID], upstream_field: Mapped[UUID],
            "recorded_at_utc": Mapped[datetime],
        },
        "id": mapped_column(Uuid, primary_key=True, default=uuid4),
        revision_field: mapped_column(ForeignKey(f"stage2_{kind}_judgment_revisions.id", ondelete="RESTRICT"), nullable=False),
        upstream_field: mapped_column(ForeignKey(f"{upstream_table}.id", ondelete="RESTRICT"), nullable=False),
        "recorded_at_utc": mapped_column(DateTime(timezone=True), nullable=False),
    })


_UPSTREAM_TABLES = {
    "hypothesis": "stage2_financial_hypothesis_revisions",
    "expectation": "stage2_market_expectation_revisions",
    "valuation": "stage2_valuation_snapshot_revisions",
    "catalyst": "stage2_catalyst_assessment_revisions",
    "risk": "stage2_risk_assessment_revisions",
    "claim": "claim_revisions",
}

for _kind, _prefix in (("industry", "Stage2IndustryJudgment"), ("company", "Stage2CompanyJudgment")):
    for _upstream, _table in _UPSTREAM_TABLES.items():
        globals()[f"{_prefix}{_upstream.title()}Link"] = _link_model(
            f"{_prefix}{_upstream.title()}Link",
            f"stage2_{_kind}_judgment_{_upstream}_links",
            _kind, _upstream, _table,
        )


class _EvidenceLinkMixin:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    claim_revision_id: Mapped[UUID] = mapped_column(ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False)
    claim_evidence_link_id: Mapped[UUID] = mapped_column(ForeignKey("claim_evidence_links.id", ondelete="RESTRICT"), nullable=False)
    evidence_id: Mapped[UUID] = mapped_column(ForeignKey("evidence_items.id", ondelete="RESTRICT"), nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage2IndustryJudgmentEvidenceLink(_EvidenceLinkMixin, Base):
    __tablename__ = "stage2_industry_judgment_evidence_links"
    __table_args__ = (
        UniqueConstraint("judgment_revision_id", "claim_evidence_link_id", name="uq_stage2_industry_judgment_evidence_link"),
        Index("ix_stage2_industry_judgment_evidence", "judgment_revision_id", "claim_revision_id"),
    )
    judgment_revision_id: Mapped[UUID] = mapped_column(ForeignKey("stage2_industry_judgment_revisions.id", ondelete="RESTRICT"), nullable=False)


class Stage2CompanyJudgmentEvidenceLink(_EvidenceLinkMixin, Base):
    __tablename__ = "stage2_company_judgment_evidence_links"
    __table_args__ = (
        UniqueConstraint("judgment_revision_id", "claim_evidence_link_id", name="uq_stage2_company_judgment_evidence_link"),
        Index("ix_stage2_company_judgment_evidence", "judgment_revision_id", "claim_revision_id"),
    )
    judgment_revision_id: Mapped[UUID] = mapped_column(ForeignKey("stage2_company_judgment_revisions.id", ondelete="RESTRICT"), nullable=False)


STAGE2_JUDGMENT_MODELS = tuple(
    [Stage2IndustryJudgment, Stage2IndustryJudgmentRevision, Stage2CompanyJudgment, Stage2CompanyJudgmentRevision]
    + [globals()[f"Stage2{kind}Judgment{upstream.title()}Link"] for kind in ("Industry", "Company") for upstream in _UPSTREAM_TABLES]
    + [Stage2IndustryJudgmentEvidenceLink, Stage2CompanyJudgmentEvidenceLink]
)


@event.listens_for(Session, "before_flush")
def reject_stage2_judgment_mutation(session: Session, _flush_context: object, _instances: object) -> None:
    reject_append_only_mutation(session, STAGE2_JUDGMENT_MODELS)
