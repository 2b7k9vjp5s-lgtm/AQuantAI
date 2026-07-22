"""Add canonical price and comparison eligibility histories.

Revision ID: 20260722_0013
Revises: 20260721_0012
Create Date: 2026-07-22
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260722_0013"
down_revision: str | None = "20260721_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "listed_instruments", "listed_instrument_revisions", "canonical_price_series",
    "canonical_price_series_revisions", "canonical_prices", "canonical_price_revisions",
    "comparison_eligibility_assessments", "comparison_eligibility_revisions",
    "comparison_eligibility_members",
)


def upgrade() -> None:
    uuid = sa.Uuid()
    op.create_table(
        "listed_instruments",
        sa.Column("id", uuid, nullable=False), sa.Column("instrument_key", sa.String(160), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("instrument_key"),
    )
    op.create_table(
        "listed_instrument_revisions",
        sa.Column("id", uuid, nullable=False), sa.Column("instrument_id", uuid, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False), sa.Column("canonical_symbol", sa.String(64), nullable=False),
        sa.Column("security_type", sa.String(32), nullable=False), sa.Column("market_code", sa.String(32), nullable=False),
        sa.Column("exchange_code_namespace", sa.String(32), nullable=False), sa.Column("exchange_code", sa.String(32), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False), sa.Column("listing_date", sa.Date(), nullable=False),
        sa.Column("delisting_date", sa.Date(), nullable=True), sa.Column("listing_status", sa.String(16), nullable=False),
        sa.Column("recorded_by", sa.String(100), nullable=False), sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False), sa.Column("supersedes_revision_id", uuid, nullable=True),
        sa.CheckConstraint("revision_no > 0", name="ck_listed_instrument_revision_positive"),
        sa.CheckConstraint("security_type = 'common_equity'", name="ck_listed_instrument_security_type"),
        sa.CheckConstraint("listing_status IN ('active','suspended','delisted')", name="ck_listed_instrument_status"),
        sa.CheckConstraint("delisting_date IS NULL OR delisting_date >= listing_date", name="ck_listed_instrument_dates"),
        sa.ForeignKeyConstraint(["instrument_id"], ["listed_instruments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], ["listed_instrument_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("instrument_id", "revision_no", name="uq_listed_instrument_revision_no"),
    )
    op.create_index("ix_listed_instrument_revision", "listed_instrument_revisions", ["instrument_id", "revision_no"])

    op.create_table(
        "canonical_price_series",
        sa.Column("id", uuid, nullable=False), sa.Column("series_contract_key", sa.String(160), nullable=False),
        sa.Column("instrument_id", uuid, nullable=False), sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["instrument_id"], ["listed_instruments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("series_contract_key"),
    )
    op.create_index("ix_canonical_price_series_instrument", "canonical_price_series", ["instrument_id"])
    op.create_table(
        "canonical_price_series_revisions",
        sa.Column("id", uuid, nullable=False), sa.Column("series_id", uuid, nullable=False), sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("instrument_revision_id", uuid, nullable=False), sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("dataset", sa.String(64), nullable=False), sa.Column("series_key", sa.String(64), nullable=False),
        sa.Column("source_stock_code", sa.String(64), nullable=False), sa.Column("source_adjust_type", sa.String(32), nullable=False),
        sa.Column("price_kind", sa.String(32), nullable=False), sa.Column("adjustment_basis", sa.String(32), nullable=False),
        sa.Column("unit_code", sa.String(32), nullable=False), sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("decimal_scale", sa.Integer(), nullable=False), sa.Column("decimal_rule_code", sa.String(32), nullable=False),
        sa.Column("rounding_mode", sa.String(32), nullable=False), sa.Column("status", sa.String(16), nullable=False),
        sa.Column("recorded_by", sa.String(100), nullable=False), sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False), sa.Column("supersedes_revision_id", uuid, nullable=True),
        sa.CheckConstraint("revision_no > 0", name="ck_canonical_price_series_revision_positive"),
        sa.CheckConstraint("price_kind = 'official_close'", name="ck_canonical_price_series_kind"),
        sa.CheckConstraint("unit_code = 'currency_per_share'", name="ck_canonical_price_series_unit"),
        sa.CheckConstraint("adjustment_basis IN ('unadjusted','forward_adjusted','backward_adjusted')", name="ck_canonical_price_series_adjustment"),
        sa.CheckConstraint("decimal_scale >= 0 AND decimal_scale <= 10", name="ck_canonical_price_series_scale"),
        sa.CheckConstraint("decimal_rule_code = 'float_repr_decimal_v1'", name="ck_canonical_price_series_decimal_rule"),
        sa.CheckConstraint("rounding_mode = 'ROUND_HALF_EVEN'", name="ck_canonical_price_series_rounding"),
        sa.CheckConstraint("status IN ('draft','accepted','retired')", name="ck_canonical_price_series_status"),
        sa.ForeignKeyConstraint(["series_id"], ["canonical_price_series.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["instrument_revision_id"], ["listed_instrument_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], ["canonical_price_series_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("series_id", "revision_no", name="uq_canonical_price_series_revision_no"),
    )
    op.create_index("ix_canonical_price_series_revision", "canonical_price_series_revisions", ["series_id", "revision_no"])

    op.create_table(
        "canonical_prices",
        sa.Column("id", uuid, nullable=False), sa.Column("series_id", uuid, nullable=False), sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("price_kind", sa.String(32), nullable=False), sa.Column("adjustment_basis", sa.String(32), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["series_id"], ["canonical_price_series.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series_id", "trade_date", "price_kind", "adjustment_basis", name="uq_canonical_price_identity"),
    )
    op.create_index("ix_canonical_price_series_date", "canonical_prices", ["series_id", "trade_date"])
    op.create_table(
        "canonical_price_revisions",
        sa.Column("id", uuid, nullable=False), sa.Column("canonical_price_id", uuid, nullable=False), sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("series_revision_id", uuid, nullable=False), sa.Column("instrument_revision_id", uuid, nullable=False),
        sa.Column("source_daily_price_id", sa.BigInteger(), nullable=False), sa.Column("source_ingestion_run_id", sa.BigInteger(), nullable=False),
        sa.Column("source_value_text", sa.String(64), nullable=False), sa.Column("standardized_value_text", sa.String(64), nullable=False),
        sa.Column("value_decimal", sa.Numeric(28, 10), nullable=False), sa.Column("numeric_fidelity", sa.String(32), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False), sa.Column("unit_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False), sa.Column("canonical_status", sa.String(16), nullable=False),
        sa.Column("conflict_summary", sa.String(2000), nullable=True), sa.Column("recorded_by", sa.String(100), nullable=False),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False), sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", uuid, nullable=True),
        sa.CheckConstraint("revision_no > 0", name="ck_canonical_price_revision_positive"),
        sa.CheckConstraint("numeric_fidelity = 'binary_float_normalized'", name="ck_canonical_price_fidelity"),
        sa.CheckConstraint("unit_code = 'currency_per_share'", name="ck_canonical_price_unit"),
        sa.CheckConstraint("canonical_status IN ('accepted','conflicting','rejected')", name="ck_canonical_price_status"),
        sa.CheckConstraint("(canonical_status = 'conflicting' AND conflict_summary IS NOT NULL) OR (canonical_status <> 'conflicting' AND conflict_summary IS NULL)", name="ck_canonical_price_conflict_summary"),
        sa.CheckConstraint("value_decimal > 0", name="ck_canonical_price_value_positive"),
        sa.ForeignKeyConstraint(["canonical_price_id"], ["canonical_prices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["series_revision_id"], ["canonical_price_series_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["instrument_revision_id"], ["listed_instrument_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_daily_price_id"], ["daily_price.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_ingestion_run_id"], ["ingestion_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], ["canonical_price_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("canonical_price_id", "revision_no", name="uq_canonical_price_revision_no"),
    )
    op.create_index("ix_canonical_price_revision", "canonical_price_revisions", ["canonical_price_id", "revision_no"])

    op.create_table(
        "comparison_eligibility_assessments",
        sa.Column("id", uuid, nullable=False), sa.Column("assessment_key", sa.String(160), nullable=False),
        sa.Column("purpose_code", sa.String(64), nullable=False), sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("assessment_key", "purpose_code", name="uq_comparison_eligibility_assessment"),
    )
    op.create_table(
        "comparison_eligibility_revisions",
        sa.Column("id", uuid, nullable=False), sa.Column("assessment_id", uuid, nullable=False), sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("rule_version", sa.String(96), nullable=False), sa.Column("state", sa.String(24), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False), sa.Column("requested_trade_date", sa.Date(), nullable=False),
        sa.Column("recorded_by", sa.String(100), nullable=False), sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False), sa.Column("supersedes_revision_id", uuid, nullable=True),
        sa.CheckConstraint("revision_no > 0", name="ck_comparison_eligibility_revision_positive"),
        sa.CheckConstraint("state IN ('eligible','ineligible','missing','stale','conflicting','not_applicable')", name="ck_comparison_eligibility_state"),
        sa.ForeignKeyConstraint(["assessment_id"], ["comparison_eligibility_assessments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], ["comparison_eligibility_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("assessment_id", "revision_no", name="uq_comparison_eligibility_revision_no"),
    )
    op.create_index("ix_comparison_eligibility_revision", "comparison_eligibility_revisions", ["assessment_id", "revision_no"])
    op.create_table(
        "comparison_eligibility_members",
        sa.Column("id", uuid, nullable=False), sa.Column("eligibility_revision_id", uuid, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False), sa.Column("canonical_price_revision_id", uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_comparison_eligibility_member_position"),
        sa.ForeignKeyConstraint(["eligibility_revision_id"], ["comparison_eligibility_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["canonical_price_revision_id"], ["canonical_price_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("eligibility_revision_id", "position", name="uq_comparison_eligibility_member_position"),
        sa.UniqueConstraint("eligibility_revision_id", "canonical_price_revision_id", name="uq_comparison_eligibility_member_price"),
    )
    op.create_index("ix_comparison_eligibility_member", "comparison_eligibility_members", ["eligibility_revision_id", "position"])


def downgrade() -> None:
    bind = op.get_bind()
    populated = [table for table in _TABLES if bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first() is not None]
    if populated:
        raise RuntimeError("Cannot downgrade canonical price and comparison eligibility while append-only history exists. Preserve or explicitly migrate the records first.")
    indexes = (
        ("ix_comparison_eligibility_member", "comparison_eligibility_members"),
        ("ix_comparison_eligibility_revision", "comparison_eligibility_revisions"),
        ("ix_canonical_price_revision", "canonical_price_revisions"),
        ("ix_canonical_price_series_date", "canonical_prices"),
        ("ix_canonical_price_series_revision", "canonical_price_series_revisions"),
        ("ix_canonical_price_series_instrument", "canonical_price_series"),
        ("ix_listed_instrument_revision", "listed_instrument_revisions"),
    )
    for name, table in indexes: op.drop_index(name, table_name=table)
    for table in reversed(_TABLES): op.drop_table(table)
