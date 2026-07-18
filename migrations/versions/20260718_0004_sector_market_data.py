"""Add sector definition and daily snapshot persistence.

Revision ID: 20260718_0004
Revises: 20260718_0003
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260718_0004"
down_revision: str | None = "20260718_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    identity_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "sector_definition",
        sa.Column("id", identity_type, autoincrement=True, nullable=False),
        sa.Column("ingestion_run_id", identity_type, nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("sector_code", sa.String(length=32), nullable=False),
        sa.Column("sector_name", sa.String(length=200), nullable=False),
        sa.Column("classification_system", sa.String(length=128), nullable=False),
        sa.Column("classification_level", sa.String(length=64), nullable=True),
        sa.Column("parent_sector_code", sa.String(length=32), nullable=True),
        sa.Column("parent_sector_name", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ingestion_run_id",
            "source",
            "classification_system",
            "sector_code",
            name="uq_sector_definition_run_natural_key",
        ),
    )
    op.create_index(
        "ix_sector_definition_run_class_code",
        "sector_definition",
        ["ingestion_run_id", "classification_system", "classification_level", "sector_code"],
    )
    op.create_index(
        "ix_sector_definition_source_class_code",
        "sector_definition",
        ["source", "classification_system", "sector_code"],
    )
    op.create_table(
        "sector_daily",
        sa.Column("id", identity_type, autoincrement=True, nullable=False),
        sa.Column("ingestion_run_id", identity_type, nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("sector_code", sa.String(length=32), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=True),
        sa.Column("high", sa.Float(), nullable=True),
        sa.Column("low", sa.Float(), nullable=True),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("turnover_rate", sa.Float(), nullable=True),
        sa.CheckConstraint("close > 0", name="ck_sector_daily_close_positive"),
        sa.CheckConstraint("open IS NULL OR open > 0", name="ck_sector_daily_open_positive"),
        sa.CheckConstraint("high IS NULL OR high > 0", name="ck_sector_daily_high_positive"),
        sa.CheckConstraint("low IS NULL OR low > 0", name="ck_sector_daily_low_positive"),
        sa.CheckConstraint("volume IS NULL OR volume >= 0", name="ck_sector_daily_volume_nonnegative"),
        sa.CheckConstraint("amount IS NULL OR amount >= 0", name="ck_sector_daily_amount_nonnegative"),
        sa.CheckConstraint("turnover_rate IS NULL OR turnover_rate >= 0", name="ck_sector_daily_turnover_nonnegative"),
        sa.CheckConstraint(
            "open IS NULL OR high IS NULL OR low IS NULL OR (low <= open AND open <= high)",
            name="ck_sector_daily_open_range",
        ),
        sa.CheckConstraint(
            "high IS NULL OR low IS NULL OR (low <= close AND close <= high)",
            name="ck_sector_daily_close_range",
        ),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ingestion_run_id", "source", "sector_code", "trade_date",
            name="uq_sector_daily_run_natural_key",
        ),
    )
    op.create_index(
        "ix_sector_daily_run_code_date",
        "sector_daily",
        ["ingestion_run_id", "sector_code", "trade_date"],
    )
    op.create_index(
        "ix_sector_daily_source_code_date",
        "sector_daily",
        ["source", "sector_code", "trade_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_sector_daily_source_code_date", table_name="sector_daily")
    op.drop_index("ix_sector_daily_run_code_date", table_name="sector_daily")
    op.drop_table("sector_daily")
    op.drop_index("ix_sector_definition_source_class_code", table_name="sector_definition")
    op.drop_index("ix_sector_definition_run_class_code", table_name="sector_definition")
    op.drop_table("sector_definition")
