"""Append-only normalized valuation and expectation persistence models."""

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
    JSON,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    event,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.database.models import Base
from industry_alpha.orm_append_only import reject_append_only_mutation


FINANCIAL_METRIC_CODES = (
    "diluted_shares_outstanding",
    "revenue",
    "net_profit_attributable",
    "ebitda",
    "free_cash_flow",
    "net_debt",
)
SOURCE_KINDS = ("actual", "guidance", "consensus", "research_assumption")
OBSERVATION_STATES = ("supported", "missing", "disputed", "rejected", "not_applicable")
PERIOD_BASES = ("instant", "ttm", "fy_actual", "forward_fy1", "forward_fy2")
ACCOUNTING_SCOPES = ("consolidated", "consolidated_attributable")
VALUATION_METRIC_CODES = ("pe", "ps", "ev_ebitda", "fcf_yield")
CALCULATION_STATES = (
    "calculated",
    "calculated_negative",
    "non_meaningful_nonpositive_denominator",
    "non_meaningful_nonpositive_enterprise_value",
    "missing_input",
    "disputed_input",
    "rejected_input",
    "stale_input",
    "ineligible_price",
    "incompatible_input",
)
COMPARISON_KINDS = ("historical", "peer")
COMPARISON_STATES = ("calculated", "insufficient_history", "insufficient_peer_members")
MEMBER_ELIGIBILITY_STATES = ("eligible", "excluded")
EXPECTATION_METRIC_CODES = ("revenue", "net_profit_attributable", "ebitda", "free_cash_flow")
GAP_STATES = (
    "calculated",
    "percentage_not_meaningful_zero_expected",
    "missing_input",
    "disputed_input",
    "rejected_input",
    "stale_input",
    "incompatible_input",
)
GAP_DIRECTIONS = ("above_expected", "below_expected", "equal_expected")
VALUATION_INPUT_ROLES = (
    "canonical_price",
    "price_eligibility",
    "diluted_shares",
    "financial_denominator",
    "net_debt",
)
NORMALIZED_LINK_ROLES = (
    "valuation_metric",
    "historical_context",
    "peer_context",
    "expectation_gap",
)


def _sql_values(values: tuple[str, ...]) -> str:
    return ",".join(f"'{item}'" for item in values)


class StructuredFinancialObservation(Base):
    __tablename__ = "structured_financial_observations"
    __table_args__ = (
        UniqueConstraint("observation_key", name="uq_structured_financial_observation_key"),
        CheckConstraint(
            f"metric_code IN ({_sql_values(FINANCIAL_METRIC_CODES)})",
            name="ck_structured_financial_metric",
        ),
        CheckConstraint(
            f"source_kind IN ({_sql_values(SOURCE_KINDS)})",
            name="ck_structured_financial_source",
        ),
        CheckConstraint(
            f"accounting_scope IN ({_sql_values(ACCOUNTING_SCOPES)})",
            name="ck_structured_financial_scope",
        ),
        CheckConstraint(
            "(metric_code = 'diluted_shares_outstanding' AND currency_code IS NULL AND unit_code = 'shares') OR "
            "(metric_code <> 'diluted_shares_outstanding' AND currency_code IS NOT NULL AND unit_code = 'currency_amount')",
            name="ck_structured_financial_identity_unit",
        ),
        Index(
            "ix_structured_financial_company_metric",
            "company_research_id",
            "metric_code",
            "target_period_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    observation_key: Mapped[str] = mapped_column(String(200), nullable=False)
    company_research_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research.id", ondelete="RESTRICT"), nullable=False
    )
    instrument_id: Mapped[UUID] = mapped_column(
        ForeignKey("listed_instruments.id", ondelete="RESTRICT"), nullable=False
    )
    metric_code: Mapped[str] = mapped_column(String(40), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    target_period_key: Mapped[str] = mapped_column(String(128), nullable=False)
    accounting_scope: Mapped[str] = mapped_column(String(40), nullable=False)
    currency_code: Mapped[str | None] = mapped_column(String(3))
    unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StructuredFinancialObservationRevision(Base):
    __tablename__ = "structured_financial_observation_revisions"
    __table_args__ = (
        UniqueConstraint(
            "observation_id", "revision_no", name="uq_structured_financial_revision_no"
        ),
        CheckConstraint("revision_no > 0", name="ck_structured_financial_revision_positive"),
        CheckConstraint(
            f"observation_state IN ({_sql_values(OBSERVATION_STATES)})",
            name="ck_structured_financial_state",
        ),
        CheckConstraint(
            f"period_basis IN ({_sql_values(PERIOD_BASES)})",
            name="ck_structured_financial_period_basis",
        ),
        CheckConstraint(
            "(observation_state = 'supported' AND source_value_text IS NOT NULL "
            "AND standardized_value_text IS NOT NULL AND value_decimal IS NOT NULL) OR "
            "(observation_state <> 'supported' AND source_value_text IS NULL "
            "AND standardized_value_text IS NULL AND value_decimal IS NULL)",
            name="ck_structured_financial_value_state",
        ),
        CheckConstraint(
            "period_start_date IS NULL OR period_start_date <= period_end_date",
            name="ck_structured_financial_period_dates",
        ),
        CheckConstraint(
            "effective_end_date IS NULL OR "
            "(effective_start_date IS NOT NULL AND effective_end_date >= effective_start_date)",
            name="ck_structured_financial_effective_dates",
        ),
        Index(
            "ix_structured_financial_revision",
            "observation_id",
            "revision_no",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("structured_financial_observations.id", ondelete="RESTRICT"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    company_research_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    instrument_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("listed_instrument_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    observation_state: Mapped[str] = mapped_column(String(24), nullable=False)
    source_value_text: Mapped[str | None] = mapped_column(String(128))
    standardized_value_text: Mapped[str | None] = mapped_column(String(128))
    value_decimal: Mapped[Decimal | None] = mapped_column(Numeric(38, 6))
    period_basis: Mapped[str] = mapped_column(String(24), nullable=False)
    period_start_date: Mapped[date | None] = mapped_column(Date)
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer)
    observation_as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_start_date: Mapped[date | None] = mapped_column(Date)
    effective_end_date: Mapped[date | None] = mapped_column(Date)
    rationale: Mapped[str | None] = mapped_column(String(4000))
    falsification_condition: Mapped[str | None] = mapped_column(String(2000))
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("structured_financial_observation_revisions.id", ondelete="RESTRICT")
    )


class StructuredFinancialObservationClaimLink(Base):
    __tablename__ = "structured_financial_observation_claim_links"
    __table_args__ = (
        UniqueConstraint(
            "observation_revision_id", "position", name="uq_structured_financial_claim_position"
        ),
        UniqueConstraint(
            "observation_revision_id",
            "claim_revision_id",
            name="uq_structured_financial_claim_revision",
        ),
        CheckConstraint("position >= 0", name="ck_structured_financial_claim_position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    observation_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("structured_financial_observation_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    claim_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StructuredFinancialObservationEvidenceLink(Base):
    __tablename__ = "structured_financial_observation_evidence_links"
    __table_args__ = (
        UniqueConstraint(
            "observation_revision_id",
            "position",
            name="uq_structured_financial_evidence_position",
        ),
        UniqueConstraint(
            "observation_revision_id",
            "claim_evidence_link_id",
            name="uq_structured_financial_evidence_link",
        ),
        CheckConstraint("position >= 0", name="ck_structured_financial_evidence_position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    observation_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("structured_financial_observation_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
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


class NormalizedValuationMetric(Base):
    __tablename__ = "normalized_valuation_metrics"
    __table_args__ = (
        UniqueConstraint("metric_key", name="uq_normalized_valuation_metric_key"),
        CheckConstraint(
            f"metric_code IN ({_sql_values(VALUATION_METRIC_CODES)})",
            name="ck_normalized_valuation_metric",
        ),
        CheckConstraint(
            f"period_basis IN ({_sql_values(PERIOD_BASES)})",
            name="ck_normalized_valuation_period_basis",
        ),
        CheckConstraint(
            f"accounting_scope IN ({_sql_values(ACCOUNTING_SCOPES)})",
            name="ck_normalized_valuation_scope",
        ),
        CheckConstraint(
            "formula_version = 'aquantai.normalized-valuation.v1'",
            name="ck_normalized_valuation_formula",
        ),
        Index(
            "ix_normalized_valuation_instrument_date",
            "instrument_id",
            "valuation_as_of_date",
            "metric_code",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    metric_key: Mapped[str] = mapped_column(String(220), nullable=False)
    instrument_id: Mapped[UUID] = mapped_column(
        ForeignKey("listed_instruments.id", ondelete="RESTRICT"), nullable=False
    )
    metric_code: Mapped[str] = mapped_column(String(24), nullable=False)
    valuation_as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_period_key: Mapped[str] = mapped_column(String(128), nullable=False)
    period_basis: Mapped[str] = mapped_column(String(24), nullable=False)
    accounting_scope: Mapped[str] = mapped_column(String(40), nullable=False)
    formula_version: Mapped[str] = mapped_column(String(96), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NormalizedValuationMetricRevision(Base):
    __tablename__ = "normalized_valuation_metric_revisions"
    __table_args__ = (
        UniqueConstraint(
            "metric_id", "revision_no", name="uq_normalized_valuation_revision_no"
        ),
        CheckConstraint("revision_no > 0", name="ck_normalized_valuation_revision_positive"),
        CheckConstraint(
            f"calculation_state IN ({_sql_values(CALCULATION_STATES)})",
            name="ck_normalized_valuation_state",
        ),
        CheckConstraint(
            "(calculation_state IN ('calculated','calculated_negative') "
            "AND normalized_value IS NOT NULL) OR "
            "(calculation_state NOT IN ('calculated','calculated_negative') "
            "AND normalized_value IS NULL)",
            name="ck_normalized_valuation_result_state",
        ),
        CheckConstraint("equity_value IS NULL OR equity_value > 0", name="ck_normalized_equity_positive"),
        Index("ix_normalized_valuation_revision", "metric_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    metric_id: Mapped[UUID] = mapped_column(
        ForeignKey("normalized_valuation_metrics.id", ondelete="RESTRICT"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    instrument_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("listed_instrument_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    calculation_state: Mapped[str] = mapped_column(String(56), nullable=False)
    normalized_value: Mapped[Decimal | None] = mapped_column(Numeric(38, 4))
    equity_value: Mapped[Decimal | None] = mapped_column(Numeric(38, 6))
    enterprise_value: Mapped[Decimal | None] = mapped_column(Numeric(38, 6))
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    output_unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    price_trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    financial_period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("normalized_valuation_metric_revisions.id", ondelete="RESTRICT")
    )


class NormalizedValuationMetricInputLink(Base):
    __tablename__ = "normalized_valuation_metric_input_links"
    __table_args__ = (
        UniqueConstraint(
            "metric_revision_id", "position", name="uq_normalized_valuation_input_position"
        ),
        UniqueConstraint(
            "metric_revision_id", "input_role", name="uq_normalized_valuation_input_role"
        ),
        CheckConstraint("position >= 0", name="ck_normalized_valuation_input_position"),
        CheckConstraint(
            f"input_role IN ({_sql_values(VALUATION_INPUT_ROLES)})",
            name="ck_normalized_valuation_input_role",
        ),
        CheckConstraint(
            "(CASE WHEN canonical_price_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN comparison_eligibility_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN financial_observation_revision_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_normalized_valuation_input_one_target",
        ),
        CheckConstraint(
            "(input_role = 'canonical_price' AND canonical_price_revision_id IS NOT NULL) OR "
            "(input_role = 'price_eligibility' AND comparison_eligibility_revision_id IS NOT NULL) OR "
            "(input_role IN ('diluted_shares','financial_denominator','net_debt') "
            "AND financial_observation_revision_id IS NOT NULL)",
            name="ck_normalized_valuation_input_target_role",
        ),
        Index("ix_normalized_valuation_input", "metric_revision_id", "position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    metric_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("normalized_valuation_metric_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    input_role: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_price_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("canonical_price_revisions.id", ondelete="RESTRICT")
    )
    comparison_eligibility_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("comparison_eligibility_revisions.id", ondelete="RESTRICT")
    )
    financial_observation_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("structured_financial_observation_revisions.id", ondelete="RESTRICT")
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ValuationComparisonSet(Base):
    __tablename__ = "valuation_comparison_sets"
    __table_args__ = (
        UniqueConstraint("comparison_key", name="uq_valuation_comparison_key"),
        CheckConstraint(
            f"comparison_kind IN ({_sql_values(COMPARISON_KINDS)})",
            name="ck_valuation_comparison_kind",
        ),
        CheckConstraint(
            f"metric_code IN ({_sql_values(VALUATION_METRIC_CODES)})",
            name="ck_valuation_comparison_metric",
        ),
        CheckConstraint(
            f"period_basis IN ({_sql_values(PERIOD_BASES)})",
            name="ck_valuation_comparison_period_basis",
        ),
        CheckConstraint(
            f"accounting_scope IN ({_sql_values(ACCOUNTING_SCOPES)})",
            name="ck_valuation_comparison_scope",
        ),
        CheckConstraint(
            "rule_version = 'aquantai.normalized-comparison-context.v1'",
            name="ck_valuation_comparison_rule",
        ),
        Index(
            "ix_valuation_comparison_subject",
            "subject_instrument_id",
            "comparison_kind",
            "metric_code",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    comparison_key: Mapped[str] = mapped_column(String(220), nullable=False)
    comparison_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    subject_company_research_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research.id", ondelete="RESTRICT"), nullable=False
    )
    subject_instrument_id: Mapped[UUID] = mapped_column(
        ForeignKey("listed_instruments.id", ondelete="RESTRICT"), nullable=False
    )
    metric_code: Mapped[str] = mapped_column(String(24), nullable=False)
    target_period_key: Mapped[str] = mapped_column(String(128), nullable=False)
    period_basis: Mapped[str] = mapped_column(String(24), nullable=False)
    accounting_scope: Mapped[str] = mapped_column(String(40), nullable=False)
    formula_version: Mapped[str] = mapped_column(String(96), nullable=False)
    purpose_code: Mapped[str] = mapped_column(String(80), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(96), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ValuationComparisonSetRevision(Base):
    __tablename__ = "valuation_comparison_set_revisions"
    __table_args__ = (
        UniqueConstraint(
            "comparison_set_id", "revision_no", name="uq_valuation_comparison_revision_no"
        ),
        CheckConstraint("revision_no > 0", name="ck_valuation_comparison_revision_positive"),
        CheckConstraint(
            f"comparison_state IN ({_sql_values(COMPARISON_STATES)})",
            name="ck_valuation_comparison_state",
        ),
        CheckConstraint(
            "total_member_count >= 1 AND eligible_member_count >= 0 "
            "AND excluded_member_count >= 0 "
            "AND total_member_count = eligible_member_count + excluded_member_count",
            name="ck_valuation_comparison_member_counts",
        ),
        CheckConstraint(
            "(comparison_state = 'calculated' AND minimum_value IS NOT NULL "
            "AND maximum_value IS NOT NULL AND median_value IS NOT NULL "
            "AND subject_percentile IS NOT NULL) OR "
            "(comparison_state <> 'calculated' AND minimum_value IS NULL "
            "AND maximum_value IS NULL AND median_value IS NULL "
            "AND subject_percentile IS NULL)",
            name="ck_valuation_comparison_result_state",
        ),
        CheckConstraint(
            "subject_percentile IS NULL OR (subject_percentile >= 0 AND subject_percentile <= 100)",
            name="ck_valuation_comparison_percentile",
        ),
        Index(
            "ix_valuation_comparison_revision", "comparison_set_id", "revision_no"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    comparison_set_id: Mapped[UUID] = mapped_column(
        ForeignKey("valuation_comparison_sets.id", ondelete="RESTRICT"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_metric_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("normalized_valuation_metric_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    comparison_state: Mapped[str] = mapped_column(String(40), nullable=False)
    rationale: Mapped[str] = mapped_column(String(4000), nullable=False)
    total_member_count: Mapped[int] = mapped_column(Integer, nullable=False)
    eligible_member_count: Mapped[int] = mapped_column(Integer, nullable=False)
    excluded_member_count: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_value: Mapped[Decimal | None] = mapped_column(Numeric(38, 4))
    maximum_value: Mapped[Decimal | None] = mapped_column(Numeric(38, 4))
    median_value: Mapped[Decimal | None] = mapped_column(Numeric(38, 4))
    subject_percentile: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("valuation_comparison_set_revisions.id", ondelete="RESTRICT")
    )


class ValuationComparisonMember(Base):
    __tablename__ = "valuation_comparison_members"
    __table_args__ = (
        UniqueConstraint(
            "comparison_revision_id", "position", name="uq_valuation_comparison_member_position"
        ),
        UniqueConstraint(
            "comparison_revision_id", "member_key", name="uq_valuation_comparison_member_key"
        ),
        CheckConstraint("position >= 0", name="ck_valuation_comparison_member_position"),
        CheckConstraint(
            f"eligibility_state IN ({_sql_values(MEMBER_ELIGIBILITY_STATES)})",
            name="ck_valuation_comparison_member_eligibility",
        ),
        CheckConstraint(
            "(eligibility_state = 'eligible' AND normalized_metric_revision_id IS NOT NULL "
            "AND normalized_value IS NOT NULL) OR "
            "(eligibility_state = 'excluded' AND normalized_value IS NULL)",
            name="ck_valuation_comparison_member_value",
        ),
        Index("ix_valuation_comparison_member", "comparison_revision_id", "position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    comparison_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("valuation_comparison_set_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    member_key: Mapped[str] = mapped_column(String(160), nullable=False)
    member_company_research_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage2_company_research_revisions.id", ondelete="RESTRICT")
    )
    member_instrument_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("listed_instrument_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    normalized_metric_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("normalized_valuation_metric_revisions.id", ondelete="RESTRICT")
    )
    eligibility_state: Mapped[str] = mapped_column(String(16), nullable=False)
    normalized_value: Mapped[Decimal | None] = mapped_column(Numeric(38, 4))
    valuation_date: Mapped[date | None] = mapped_column(Date)
    financial_period_end_date: Mapped[date | None] = mapped_column(Date)
    is_subject: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NormalizedExpectationGap(Base):
    __tablename__ = "normalized_expectation_gaps"
    __table_args__ = (
        UniqueConstraint("gap_key", name="uq_normalized_expectation_gap_key"),
        CheckConstraint(
            f"metric_code IN ({_sql_values(EXPECTATION_METRIC_CODES)})",
            name="ck_normalized_expectation_metric",
        ),
        CheckConstraint(
            "expected_source_kind IN ('guidance','consensus','research_assumption')",
            name="ck_normalized_expectation_source",
        ),
        CheckConstraint(
            "rule_version = 'aquantai.normalized-expectation-gap.v1'",
            name="ck_normalized_expectation_rule",
        ),
        Index(
            "ix_normalized_expectation_company_metric",
            "company_research_id",
            "metric_code",
            "target_period_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    gap_key: Mapped[str] = mapped_column(String(220), nullable=False)
    company_research_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research.id", ondelete="RESTRICT"), nullable=False
    )
    instrument_id: Mapped[UUID] = mapped_column(
        ForeignKey("listed_instruments.id", ondelete="RESTRICT"), nullable=False
    )
    metric_code: Mapped[str] = mapped_column(String(40), nullable=False)
    target_period_key: Mapped[str] = mapped_column(String(128), nullable=False)
    expected_source_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(96), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NormalizedExpectationGapRevision(Base):
    __tablename__ = "normalized_expectation_gap_revisions"
    __table_args__ = (
        UniqueConstraint("gap_id", "revision_no", name="uq_normalized_expectation_revision_no"),
        CheckConstraint("revision_no > 0", name="ck_normalized_expectation_revision_positive"),
        CheckConstraint(
            f"gap_state IN ({_sql_values(GAP_STATES)})",
            name="ck_normalized_expectation_state",
        ),
        CheckConstraint(
            "direction IS NULL OR direction IN ('above_expected','below_expected','equal_expected')",
            name="ck_normalized_expectation_direction",
        ),
        CheckConstraint(
            "(gap_state = 'calculated' AND absolute_gap IS NOT NULL "
            "AND percentage_gap IS NOT NULL AND direction IS NOT NULL) OR "
            "(gap_state = 'percentage_not_meaningful_zero_expected' "
            "AND absolute_gap IS NOT NULL AND percentage_gap IS NULL AND direction IS NOT NULL) OR "
            "(gap_state NOT IN ('calculated','percentage_not_meaningful_zero_expected') "
            "AND absolute_gap IS NULL AND percentage_gap IS NULL AND direction IS NULL)",
            name="ck_normalized_expectation_result_state",
        ),
        Index("ix_normalized_expectation_revision", "gap_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    gap_id: Mapped[UUID] = mapped_column(
        ForeignKey("normalized_expectation_gaps.id", ondelete="RESTRICT"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    company_research_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage2_company_research_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    instrument_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("listed_instrument_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    expected_observation_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("structured_financial_observation_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actual_observation_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("structured_financial_observation_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    gap_state: Mapped[str] = mapped_column(String(56), nullable=False)
    absolute_gap: Mapped[Decimal | None] = mapped_column(Numeric(38, 6))
    percentage_gap: Mapped[Decimal | None] = mapped_column(Numeric(38, 4))
    direction: Mapped[str | None] = mapped_column(String(24))
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    calculation_as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("normalized_expectation_gap_revisions.id", ondelete="RESTRICT")
    )


class InvestmentCandidateNormalizedMetricLink(Base):
    __tablename__ = "investment_candidate_normalized_metric_links"
    __table_args__ = (
        UniqueConstraint(
            "component_revision_id", "position", name="uq_investment_candidate_normalized_position"
        ),
        CheckConstraint("position >= 0", name="ck_investment_candidate_normalized_position"),
        CheckConstraint(
            f"link_role IN ({_sql_values(NORMALIZED_LINK_ROLES)})",
            name="ck_investment_candidate_normalized_role",
        ),
        CheckConstraint(
            "(CASE WHEN valuation_metric_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN comparison_set_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN expectation_gap_revision_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_investment_candidate_normalized_one_target",
        ),
        CheckConstraint(
            "(link_role = 'valuation_metric' AND valuation_metric_revision_id IS NOT NULL) OR "
            "(link_role IN ('historical_context','peer_context') "
            "AND comparison_set_revision_id IS NOT NULL) OR "
            "(link_role = 'expectation_gap' AND expectation_gap_revision_id IS NOT NULL)",
            name="ck_investment_candidate_normalized_target_role",
        ),
        Index(
            "ix_investment_candidate_normalized_link", "component_revision_id", "position"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    component_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("investment_candidate_component_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    link_role: Mapped[str] = mapped_column(String(32), nullable=False)
    valuation_metric_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("normalized_valuation_metric_revisions.id", ondelete="RESTRICT")
    )
    comparison_set_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("valuation_comparison_set_revisions.id", ondelete="RESTRICT")
    )
    expectation_gap_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("normalized_expectation_gap_revisions.id", ondelete="RESTRICT")
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


NORMALIZED_VALUATION_MODELS = (
    StructuredFinancialObservation,
    StructuredFinancialObservationRevision,
    StructuredFinancialObservationClaimLink,
    StructuredFinancialObservationEvidenceLink,
    NormalizedValuationMetric,
    NormalizedValuationMetricRevision,
    NormalizedValuationMetricInputLink,
    ValuationComparisonSet,
    ValuationComparisonSetRevision,
    ValuationComparisonMember,
    NormalizedExpectationGap,
    NormalizedExpectationGapRevision,
    InvestmentCandidateNormalizedMetricLink,
)


@event.listens_for(Session, "before_flush")
def reject_normalized_valuation_mutation(
    session: Session, _flush_context: object, _instances: object
) -> None:
    reject_append_only_mutation(session, NORMALIZED_VALUATION_MODELS)
