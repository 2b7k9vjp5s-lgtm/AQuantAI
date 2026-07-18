"""Create ingestion provenance and versioned market-data tables.

Revision ID: 20260718_0001
Revises:
Create Date: 2026-07-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260718_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("batch_identifier", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("dataset", sa.String(length=64), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_start_date", sa.Date(), nullable=False),
        sa.Column("requested_end_date", sa.Date(), nullable=False),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("requested_scope", sa.JSON(), nullable=False),
        sa.Column("snapshot_mode", sa.String(length=16), nullable=False),
        sa.Column("contract_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("row_count_received", sa.Integer(), nullable=False),
        sa.Column("row_count_written", sa.Integer(), nullable=False),
        sa.Column("dataset_counts", sa.JSON(), nullable=False),
        sa.Column("error_summary", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "row_count_received >= 0", name="ck_ingestion_runs_received_nonnegative"
        ),
        sa.CheckConstraint("row_count_written >= 0", name="ck_ingestion_runs_written_nonnegative"),
        sa.CheckConstraint("snapshot_mode = 'complete'", name="ck_ingestion_runs_snapshot_mode"),
        sa.CheckConstraint("status IN ('pending', 'succeeded', 'failed')", name="ck_ingestion_runs_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_runs_batch_identifier", "ingestion_runs", ["batch_identifier"])
    op.create_index(
        "ix_ingestion_runs_provider_dataset_cutoff",
        "ingestion_runs",
        ["provider", "dataset", "information_cutoff_date"],
    )
    op.create_index(
        "uq_ingestion_runs_successful_batch",
        "ingestion_runs",
        ["batch_identifier"],
        unique=True,
        postgresql_where=sa.text("status = 'succeeded'"),
        sqlite_where=sa.text("status = 'succeeded'"),
    )

    op.create_table(
        "stock_basic",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("ingestion_run_id", sa.BigInteger(), nullable=False),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("stock_name", sa.String(length=200), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("industry", sa.String(length=200), nullable=False),
        sa.Column("listing_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ingestion_run_id", "source", "stock_code", name="uq_stock_basic_run_natural_key"
        ),
    )
    op.create_index(
        "ix_stock_basic_natural_key", "stock_basic", ["source", "stock_code", "ingestion_run_id"]
    )

    op.create_table(
        "daily_price",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("ingestion_run_id", sa.BigInteger(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("adjust_type", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_daily_price_amount_nonnegative"),
        sa.CheckConstraint("volume >= 0", name="ck_daily_price_volume_nonnegative"),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ingestion_run_id",
            "source",
            "stock_code",
            "trade_date",
            "adjust_type",
            name="uq_daily_price_run_natural_key",
        ),
    )
    op.create_index(
        "ix_daily_price_natural_key",
        "daily_price",
        ["source", "stock_code", "trade_date", "adjust_type", "ingestion_run_id"],
    )
    op.create_index("ix_daily_price_trade_date", "daily_price", ["trade_date", "stock_code"])

    op.create_table(
        "trade_calendar",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("ingestion_run_id", sa.BigInteger(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("is_open", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ingestion_run_id", "source", "trade_date", name="uq_trade_calendar_run_natural_key"
        ),
    )
    op.create_index(
        "ix_trade_calendar_natural_key",
        "trade_calendar",
        ["source", "trade_date", "ingestion_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_trade_calendar_natural_key", table_name="trade_calendar")
    op.drop_table("trade_calendar")
    op.drop_index("ix_daily_price_trade_date", table_name="daily_price")
    op.drop_index("ix_daily_price_natural_key", table_name="daily_price")
    op.drop_table("daily_price")
    op.drop_index("ix_stock_basic_natural_key", table_name="stock_basic")
    op.drop_table("stock_basic")
    op.drop_index("uq_ingestion_runs_successful_batch", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_provider_dataset_cutoff", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_batch_identifier", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")
