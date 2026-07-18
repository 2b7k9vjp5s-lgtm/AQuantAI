"""Add benchmark-index daily snapshot persistence.

Revision ID: 20260718_0003
Revises: 20260718_0002
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260718_0003"
down_revision: str | None = "20260718_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "benchmark_index_daily",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("ingestion_run_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("index_code", sa.String(length=32), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=True),
        sa.Column("high", sa.Float(), nullable=True),
        sa.Column("low", sa.Float(), nullable=True),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.CheckConstraint("close > 0", name="ck_benchmark_index_daily_close_positive"),
        sa.CheckConstraint("open IS NULL OR open > 0", name="ck_benchmark_index_daily_open_positive"),
        sa.CheckConstraint("high IS NULL OR high > 0", name="ck_benchmark_index_daily_high_positive"),
        sa.CheckConstraint("low IS NULL OR low > 0", name="ck_benchmark_index_daily_low_positive"),
        sa.CheckConstraint("volume IS NULL OR volume >= 0", name="ck_benchmark_index_daily_volume_nonnegative"),
        sa.CheckConstraint("amount IS NULL OR amount >= 0", name="ck_benchmark_index_daily_amount_nonnegative"),
        sa.CheckConstraint(
            "open IS NULL OR high IS NULL OR low IS NULL OR (low <= open AND open <= high)",
            name="ck_benchmark_index_daily_open_range",
        ),
        sa.CheckConstraint(
            "high IS NULL OR low IS NULL OR (low <= close AND close <= high)",
            name="ck_benchmark_index_daily_close_range",
        ),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ingestion_run_id",
            "source",
            "index_code",
            "trade_date",
            name="uq_benchmark_index_daily_run_natural_key",
        ),
    )
    op.create_index(
        "ix_benchmark_index_daily_run_code_date",
        "benchmark_index_daily",
        ["ingestion_run_id", "index_code", "trade_date"],
    )
    op.create_index(
        "ix_benchmark_index_daily_source_code_date",
        "benchmark_index_daily",
        ["source", "index_code", "trade_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_benchmark_index_daily_source_code_date",
        table_name="benchmark_index_daily",
    )
    op.drop_index(
        "ix_benchmark_index_daily_run_code_date",
        table_name="benchmark_index_daily",
    )
    op.drop_table("benchmark_index_daily")
