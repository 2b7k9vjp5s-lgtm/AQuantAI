"""Append-only Investment Candidate Intelligence v1 persistence models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    event,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.database.models import Base
from industry_alpha.orm_append_only import reject_append_only_mutation


COMPONENT_CODES = (
    "industry_opportunity",
    "beneficiary_strength",
    "earnings_conversion",
    "expectation_gap",
    "valuation_context",
    "catalyst_readiness",
    "evidence_quality",
    "risk_penalty",
)
ASSESSMENT_STATES = ("supported", "missing", "disputed", "not_applicable")
VERIFICATION_STATES = ("verified", "pending", "failed", "not_applicable")
VERIFICATION_ITEM_CODES = (
    "certification",
    "order",
    "capacity",
    "production",
    "financial_confirmation",
    "customer_confirmation",
    "other_explicit",
)
FALSIFICATION_STATES = ("inactive", "active", "not_applicable")
CANDIDATE_STATUSES = (
    "priority_candidate",
    "watch_candidate",
    "awaiting_verification",
    "pricing_demanding",
    "evidence_insufficient",
    "not_current_candidate",
)


def _sql_values(values: tuple[str, ...]) -> str:
    return ",".join(f"'{item}'" for item in values)


class InvestmentCandidateComponentAssessment(Base):
    __tablename__ = "investment_candidate_component_assessments"
    __table_args__ = (
        UniqueConstraint(
            "beneficiary_id",
            "component_code",
            "assessment_key",
            name="uq_investment_candidate_component_assessment",
        ),
        CheckConstraint(
            f"component_code IN ({_sql_values(COMPONENT_CODES)})",
            name="ck_investment_candidate_component_code",
        ),
        Index(
            "ix_investment_candidate_component_beneficiary",
            "beneficiary_id",
            "component_code",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    beneficiary_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiaries.id", ondelete="RESTRICT"), nullable=False
    )
    component_code: Mapped[str] = mapped_column(String(32), nullable=False)
    assessment_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InvestmentCandidateComponentRevision(Base):
    __tablename__ = "investment_candidate_component_revisions"
    __table_args__ = (
        UniqueConstraint(
            "component_assessment_id",
            "revision_no",
            name="uq_investment_candidate_component_revision_no",
        ),
        CheckConstraint("revision_no > 0", name="ck_investment_candidate_component_revision_positive"),
        CheckConstraint(
            f"assessment_state IN ({_sql_values(ASSESSMENT_STATES)})",
            name="ck_investment_candidate_assessment_state",
        ),
        CheckConstraint(
            f"verification_state IN ({_sql_values(VERIFICATION_STATES)})",
            name="ck_investment_candidate_verification_state",
        ),
        CheckConstraint(
            f"verification_item_code IS NULL OR verification_item_code IN ({_sql_values(VERIFICATION_ITEM_CODES)})",
            name="ck_investment_candidate_verification_item_code",
        ),
        CheckConstraint(
            "(verification_state IN ('pending','failed') "
            "AND verification_material = true "
            "AND verification_item_code IS NOT NULL "
            "AND verification_question IS NOT NULL "
            "AND length(trim(verification_question)) > 0) OR "
            "(verification_state IN ('verified','not_applicable') "
            "AND verification_material = false "
            "AND verification_item_code IS NULL "
            "AND verification_question IS NULL)",
            name="ck_investment_candidate_verification_contract",
        ),
        CheckConstraint(
            f"falsification_state IN ({_sql_values(FALSIFICATION_STATES)})",
            name="ck_investment_candidate_falsification_state",
        ),
        CheckConstraint(
            "score_value IS NULL OR (score_value >= 0 AND score_value <= 100)",
            name="ck_investment_candidate_score_range",
        ),
        CheckConstraint(
            "(assessment_state = 'supported' AND score_value IS NOT NULL AND source_score_text IS NOT NULL AND missing_reason IS NULL) OR "
            "(assessment_state = 'disputed' AND missing_reason IS NULL) OR "
            "(assessment_state IN ('missing','not_applicable') AND score_value IS NULL AND source_score_text IS NULL)",
            name="ck_investment_candidate_score_state",
        ),
        CheckConstraint(
            "assessment_state <> 'missing' OR missing_reason IS NOT NULL",
            name="ck_investment_candidate_missing_reason",
        ),
        Index(
            "ix_investment_candidate_component_revision",
            "component_assessment_id",
            "revision_no",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    component_assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("investment_candidate_component_assessments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    beneficiary_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiary_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    company_research_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assessment_state: Mapped[str] = mapped_column(String(24), nullable=False)
    verification_state: Mapped[str] = mapped_column(String(24), nullable=False)
    verification_material: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_item_code: Mapped[str | None] = mapped_column(String(40))
    verification_question: Mapped[str | None] = mapped_column(String(2000))
    source_score_text: Mapped[str | None] = mapped_column(String(64))
    score_value: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    missing_reason: Mapped[str | None] = mapped_column(String(500))
    rationale: Mapped[str] = mapped_column(String(4000), nullable=False)
    falsification_condition: Mapped[str] = mapped_column(String(2000), nullable=False)
    falsification_state: Mapped[str] = mapped_column(String(24), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("investment_candidate_component_revisions.id", ondelete="RESTRICT")
    )


class InvestmentCandidateComponentInputLink(Base):
    __tablename__ = "investment_candidate_component_input_links"
    __table_args__ = (
        UniqueConstraint(
            "component_revision_id",
            "position",
            name="uq_investment_candidate_component_input_position",
        ),
        CheckConstraint("position >= 0", name="ck_investment_candidate_component_input_position"),
        CheckConstraint(
            "(CASE WHEN map_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN map_observation_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN beneficiary_semantic_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN financial_hypothesis_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN market_expectation_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN valuation_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN catalyst_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN risk_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN industry_judgment_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN company_judgment_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN canonical_price_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN comparison_eligibility_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN claim_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN evidence_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_investment_candidate_component_input_one_target",
        ),
        Index(
            "ix_investment_candidate_component_input",
            "component_revision_id",
            "position",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    component_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("investment_candidate_component_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    map_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_map_revisions.id", ondelete="RESTRICT")
    )
    map_observation_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_map_observation_revisions.id", ondelete="RESTRICT")
    )
    beneficiary_semantic_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage1_beneficiary_semantic_profile_revisions.id", ondelete="RESTRICT")
    )
    financial_hypothesis_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage2_financial_hypothesis_revisions.id", ondelete="RESTRICT")
    )
    market_expectation_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage2_market_expectation_revisions.id", ondelete="RESTRICT")
    )
    valuation_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage2_valuation_snapshot_revisions.id", ondelete="RESTRICT")
    )
    catalyst_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage2_catalyst_assessment_revisions.id", ondelete="RESTRICT")
    )
    risk_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage2_risk_assessment_revisions.id", ondelete="RESTRICT")
    )
    industry_judgment_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage2_industry_judgment_revisions.id", ondelete="RESTRICT")
    )
    company_judgment_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage2_company_judgment_revisions.id", ondelete="RESTRICT")
    )
    canonical_price_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("canonical_price_revisions.id", ondelete="RESTRICT")
    )
    comparison_eligibility_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("comparison_eligibility_revisions.id", ondelete="RESTRICT")
    )
    claim_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("claim_revisions.id", ondelete="RESTRICT")
    )
    evidence_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="RESTRICT")
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InvestmentCandidateSnapshot(Base):
    __tablename__ = "investment_candidate_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "candidate_pool_id",
            "purpose_code",
            "snapshot_key",
            name="uq_investment_candidate_snapshot",
        ),
        Index("ix_investment_candidate_snapshot_pool", "candidate_pool_id", "purpose_code"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    candidate_pool_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_candidate_pools.id", ondelete="RESTRICT"), nullable=False
    )
    purpose_code: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InvestmentCandidateSnapshotRevision(Base):
    __tablename__ = "investment_candidate_snapshot_revisions"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id", "revision_no", name="uq_investment_candidate_snapshot_revision_no"
        ),
        CheckConstraint("revision_no > 0", name="ck_investment_candidate_snapshot_revision_positive"),
        CheckConstraint(
            "purpose_code = 'industry_beneficiary_investment_candidate_v1'",
            name="ck_investment_candidate_snapshot_purpose",
        ),
        CheckConstraint(
            "rule_version = 'aquantai.investment-candidate-priority.v1'",
            name="ck_investment_candidate_snapshot_rule",
        ),
        Index("ix_investment_candidate_snapshot_revision", "snapshot_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("investment_candidate_snapshots.id", ondelete="RESTRICT"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_pool_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_candidate_pool_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    purpose_code: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(96), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("investment_candidate_snapshot_revisions.id", ondelete="RESTRICT")
    )


class InvestmentCandidateMember(Base):
    __tablename__ = "investment_candidate_members"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_revision_id",
            "candidate_pool_membership_id",
            name="uq_investment_candidate_member_membership",
        ),
        UniqueConstraint(
            "snapshot_revision_id",
            "beneficiary_id",
            name="uq_investment_candidate_member_beneficiary",
        ),
        CheckConstraint(
            f"candidate_status IN ({_sql_values(CANDIDATE_STATUSES)})",
            name="ck_investment_candidate_member_status",
        ),
        CheckConstraint(
            "priority_ordinal IS NULL OR priority_ordinal > 0",
            name="ck_investment_candidate_member_priority_positive",
        ),
        CheckConstraint(
            "(candidate_status IN ('priority_candidate','watch_candidate') AND priority_ordinal IS NOT NULL) OR "
            "(candidate_status NOT IN ('priority_candidate','watch_candidate') AND priority_ordinal IS NULL)",
            name="ck_investment_candidate_member_priority_status",
        ),
        CheckConstraint(
            "(base_score IS NULL AND business_quality_score IS NULL AND risk_penalty_points IS NULL AND final_score IS NULL) OR "
            "(base_score IS NOT NULL AND business_quality_score IS NOT NULL AND risk_penalty_points IS NOT NULL AND final_score IS NOT NULL)",
            name="ck_investment_candidate_member_aggregate_all_or_none",
        ),
        Index("ix_investment_candidate_member_snapshot", "snapshot_revision_id", "candidate_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    snapshot_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("investment_candidate_snapshot_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    candidate_pool_membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_candidate_pool_memberships.id", ondelete="RESTRICT"), nullable=False
    )
    beneficiary_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiaries.id", ondelete="RESTRICT"), nullable=False
    )
    beneficiary_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiary_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    company_research_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage2_company_research_revisions.id", ondelete="RESTRICT")
    )
    typed_beneficiary_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage1_beneficiary_semantic_profile_revisions.id", ondelete="RESTRICT")
    )
    canonical_price_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("canonical_price_revisions.id", ondelete="RESTRICT")
    )
    comparison_eligibility_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("comparison_eligibility_revisions.id", ondelete="RESTRICT")
    )
    base_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    business_quality_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    risk_penalty_points: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    final_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    candidate_status: Mapped[str] = mapped_column(String(32), nullable=False)
    priority_ordinal: Mapped[int | None] = mapped_column(Integer)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InvestmentCandidateMemberComponentLink(Base):
    __tablename__ = "investment_candidate_member_component_links"
    __table_args__ = (
        UniqueConstraint(
            "member_id", "component_code", name="uq_investment_candidate_member_component"
        ),
        CheckConstraint(
            f"component_code IN ({_sql_values(COMPONENT_CODES)})",
            name="ck_investment_candidate_member_component_code",
        ),
        CheckConstraint("rule_weight >= 0 AND rule_weight <= 1", name="ck_investment_candidate_rule_weight"),
        Index("ix_investment_candidate_member_component", "member_id", "component_code"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    member_id: Mapped[UUID] = mapped_column(
        ForeignKey("investment_candidate_members.id", ondelete="RESTRICT"), nullable=False
    )
    component_code: Mapped[str] = mapped_column(String(32), nullable=False)
    component_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("investment_candidate_component_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rule_weight: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    contribution_amount: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InvestmentCandidateMemberReasonCode(Base):
    __tablename__ = "investment_candidate_member_reason_codes"
    __table_args__ = (
        UniqueConstraint("member_id", "reason_code", name="uq_investment_candidate_member_reason"),
        UniqueConstraint("member_id", "ordinal", name="uq_investment_candidate_member_reason_ordinal"),
        CheckConstraint("ordinal >= 0", name="ck_investment_candidate_member_reason_ordinal"),
        Index("ix_investment_candidate_member_reason", "member_id", "ordinal"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    member_id: Mapped[UUID] = mapped_column(
        ForeignKey("investment_candidate_members.id", ondelete="RESTRICT"), nullable=False
    )
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


INVESTMENT_CANDIDATE_MODELS = (
    InvestmentCandidateComponentAssessment,
    InvestmentCandidateComponentRevision,
    InvestmentCandidateComponentInputLink,
    InvestmentCandidateSnapshot,
    InvestmentCandidateSnapshotRevision,
    InvestmentCandidateMember,
    InvestmentCandidateMemberComponentLink,
    InvestmentCandidateMemberReasonCode,
)


@event.listens_for(Session, "before_flush")
def reject_investment_candidate_mutation(
    session: Session, _flush_context: object, _instances: object
) -> None:
    reject_append_only_mutation(session, INVESTMENT_CANDIDATE_MODELS)
