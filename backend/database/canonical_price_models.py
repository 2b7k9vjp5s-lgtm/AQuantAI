"""Append-only listed identity, canonical price, and eligibility models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
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


class ListedInstrument(Base):
    __tablename__ = "listed_instruments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    instrument_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ListedInstrumentRevision(Base):
    __tablename__ = "listed_instrument_revisions"
    __table_args__ = (
        UniqueConstraint("instrument_id", "revision_no", name="uq_listed_instrument_revision_no"),
        CheckConstraint("revision_no > 0", name="ck_listed_instrument_revision_positive"),
        CheckConstraint("security_type = 'common_equity'", name="ck_listed_instrument_security_type"),
        CheckConstraint("listing_status IN ('active','suspended','delisted')", name="ck_listed_instrument_status"),
        CheckConstraint("delisting_date IS NULL OR delisting_date >= listing_date", name="ck_listed_instrument_dates"),
        Index("ix_listed_instrument_revision", "instrument_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("listed_instruments.id", ondelete="RESTRICT"), nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    canonical_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    security_type: Mapped[str] = mapped_column(String(32), nullable=False)
    market_code: Mapped[str] = mapped_column(String(32), nullable=False)
    exchange_code_namespace: Mapped[str] = mapped_column(String(32), nullable=False)
    exchange_code: Mapped[str] = mapped_column(String(32), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    listing_date: Mapped[date] = mapped_column(Date, nullable=False)
    delisting_date: Mapped[date | None] = mapped_column(Date)
    listing_status: Mapped[str] = mapped_column(String(16), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("listed_instrument_revisions.id", ondelete="RESTRICT"))


class CanonicalPriceSeries(Base):
    __tablename__ = "canonical_price_series"
    __table_args__ = (Index("ix_canonical_price_series_instrument", "instrument_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    series_contract_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("listed_instruments.id", ondelete="RESTRICT"), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CanonicalPriceSeriesRevision(Base):
    __tablename__ = "canonical_price_series_revisions"
    __table_args__ = (
        UniqueConstraint("series_id", "revision_no", name="uq_canonical_price_series_revision_no"),
        CheckConstraint("revision_no > 0", name="ck_canonical_price_series_revision_positive"),
        CheckConstraint("price_kind = 'official_close'", name="ck_canonical_price_series_kind"),
        CheckConstraint("unit_code = 'currency_per_share'", name="ck_canonical_price_series_unit"),
        CheckConstraint("adjustment_basis IN ('unadjusted','forward_adjusted','backward_adjusted')", name="ck_canonical_price_series_adjustment"),
        CheckConstraint("decimal_scale >= 0 AND decimal_scale <= 10", name="ck_canonical_price_series_scale"),
        CheckConstraint("decimal_rule_code = 'float_repr_decimal_v1'", name="ck_canonical_price_series_decimal_rule"),
        CheckConstraint("rounding_mode = 'ROUND_HALF_EVEN'", name="ck_canonical_price_series_rounding"),
        CheckConstraint("status IN ('draft','accepted','retired')", name="ck_canonical_price_series_status"),
        Index("ix_canonical_price_series_revision", "series_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    series_id: Mapped[UUID] = mapped_column(ForeignKey("canonical_price_series.id", ondelete="RESTRICT"), nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    instrument_revision_id: Mapped[UUID] = mapped_column(ForeignKey("listed_instrument_revisions.id", ondelete="RESTRICT"), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset: Mapped[str] = mapped_column(String(64), nullable=False)
    series_key: Mapped[str] = mapped_column(String(64), nullable=False)
    source_stock_code: Mapped[str] = mapped_column(String(64), nullable=False)
    source_adjust_type: Mapped[str] = mapped_column(String(32), nullable=False)
    price_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    adjustment_basis: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    decimal_scale: Mapped[int] = mapped_column(Integer, nullable=False)
    decimal_rule_code: Mapped[str] = mapped_column(String(32), nullable=False)
    rounding_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("canonical_price_series_revisions.id", ondelete="RESTRICT"))


class CanonicalPrice(Base):
    __tablename__ = "canonical_prices"
    __table_args__ = (
        UniqueConstraint("series_id", "trade_date", "price_kind", "adjustment_basis", name="uq_canonical_price_identity"),
        Index("ix_canonical_price_series_date", "series_id", "trade_date"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    series_id: Mapped[UUID] = mapped_column(ForeignKey("canonical_price_series.id", ondelete="RESTRICT"), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    price_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    adjustment_basis: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CanonicalPriceRevision(Base):
    __tablename__ = "canonical_price_revisions"
    __table_args__ = (
        UniqueConstraint("canonical_price_id", "revision_no", name="uq_canonical_price_revision_no"),
        CheckConstraint("revision_no > 0", name="ck_canonical_price_revision_positive"),
        CheckConstraint("numeric_fidelity = 'binary_float_normalized'", name="ck_canonical_price_fidelity"),
        CheckConstraint("unit_code = 'currency_per_share'", name="ck_canonical_price_unit"),
        CheckConstraint("canonical_status IN ('accepted','conflicting','rejected')", name="ck_canonical_price_status"),
        CheckConstraint("(canonical_status = 'conflicting' AND conflict_summary IS NOT NULL) OR (canonical_status <> 'conflicting' AND conflict_summary IS NULL)", name="ck_canonical_price_conflict_summary"),
        CheckConstraint("value_decimal > 0", name="ck_canonical_price_value_positive"),
        Index("ix_canonical_price_revision", "canonical_price_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    canonical_price_id: Mapped[UUID] = mapped_column(ForeignKey("canonical_prices.id", ondelete="RESTRICT"), nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    series_revision_id: Mapped[UUID] = mapped_column(ForeignKey("canonical_price_series_revisions.id", ondelete="RESTRICT"), nullable=False)
    instrument_revision_id: Mapped[UUID] = mapped_column(ForeignKey("listed_instrument_revisions.id", ondelete="RESTRICT"), nullable=False)
    source_daily_price_id: Mapped[int] = mapped_column(ForeignKey("daily_price.id", ondelete="RESTRICT"), nullable=False)
    source_ingestion_run_id: Mapped[int] = mapped_column(ForeignKey("ingestion_runs.id", ondelete="RESTRICT"), nullable=False)
    source_value_text: Mapped[str] = mapped_column(String(64), nullable=False)
    standardized_value_text: Mapped[str] = mapped_column(String(64), nullable=False)
    value_decimal: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    numeric_fidelity: Mapped[str] = mapped_column(String(32), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    canonical_status: Mapped[str] = mapped_column(String(16), nullable=False)
    conflict_summary: Mapped[str | None] = mapped_column(String(2000))
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("canonical_price_revisions.id", ondelete="RESTRICT"))


class ComparisonEligibilityAssessment(Base):
    __tablename__ = "comparison_eligibility_assessments"
    __table_args__ = (UniqueConstraint("assessment_key", "purpose_code", name="uq_comparison_eligibility_assessment"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    assessment_key: Mapped[str] = mapped_column(String(160), nullable=False)
    purpose_code: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ComparisonEligibilityRevision(Base):
    __tablename__ = "comparison_eligibility_revisions"
    __table_args__ = (
        UniqueConstraint("assessment_id", "revision_no", name="uq_comparison_eligibility_revision_no"),
        CheckConstraint("revision_no > 0", name="ck_comparison_eligibility_revision_positive"),
        CheckConstraint("state IN ('eligible','ineligible','missing','stale','conflicting','not_applicable')", name="ck_comparison_eligibility_state"),
        Index("ix_comparison_eligibility_revision", "assessment_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    assessment_id: Mapped[UUID] = mapped_column(ForeignKey("comparison_eligibility_assessments.id", ondelete="RESTRICT"), nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(96), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    requested_trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("comparison_eligibility_revisions.id", ondelete="RESTRICT"))


class ComparisonEligibilityMember(Base):
    __tablename__ = "comparison_eligibility_members"
    __table_args__ = (
        UniqueConstraint("eligibility_revision_id", "position", name="uq_comparison_eligibility_member_position"),
        UniqueConstraint("eligibility_revision_id", "canonical_price_revision_id", name="uq_comparison_eligibility_member_price"),
        CheckConstraint("position >= 0", name="ck_comparison_eligibility_member_position"),
        Index("ix_comparison_eligibility_member", "eligibility_revision_id", "position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    eligibility_revision_id: Mapped[UUID] = mapped_column(ForeignKey("comparison_eligibility_revisions.id", ondelete="RESTRICT"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    canonical_price_revision_id: Mapped[UUID] = mapped_column(ForeignKey("canonical_price_revisions.id", ondelete="RESTRICT"), nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


CANONICAL_PRICE_MODELS = (
    ListedInstrument,
    ListedInstrumentRevision,
    CanonicalPriceSeries,
    CanonicalPriceSeriesRevision,
    CanonicalPrice,
    CanonicalPriceRevision,
    ComparisonEligibilityAssessment,
    ComparisonEligibilityRevision,
    ComparisonEligibilityMember,
)


@event.listens_for(Session, "before_flush")
def reject_canonical_price_mutation(session: Session, _flush_context: object, _instances: object) -> None:
    reject_append_only_mutation(session, CANONICAL_PRICE_MODELS)
