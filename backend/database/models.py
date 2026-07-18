"""ORM models for versioned normalized market data and ingestion provenance."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


IDENTITY_TYPE = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    """Declarative metadata used only by explicit migrations and tests."""


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'succeeded', 'failed')", name="ck_ingestion_runs_status"),
        CheckConstraint("snapshot_mode = 'complete'", name="ck_ingestion_runs_snapshot_mode"),
        CheckConstraint("length(series_key) = 64", name="ck_ingestion_runs_series_key_length"),
        CheckConstraint("row_count_received >= 0", name="ck_ingestion_runs_received_nonnegative"),
        CheckConstraint("row_count_written >= 0", name="ck_ingestion_runs_written_nonnegative"),
        Index("ix_ingestion_runs_batch_identifier", "batch_identifier"),
        Index("ix_ingestion_runs_provider_dataset_cutoff", "provider", "dataset", "information_cutoff_date"),
        Index(
            "ix_ingestion_runs_series_cutoff",
            "series_key",
            "information_cutoff_date",
            "completed_at",
            "id",
        ),
        Index(
            "uq_ingestion_runs_successful_batch",
            "batch_identifier",
            "series_key",
            unique=True,
            postgresql_where=text("status = 'succeeded'"),
            sqlite_where=text("status = 'succeeded'"),
        ),
    )

    id: Mapped[int] = mapped_column(IDENTITY_TYPE, primary_key=True, autoincrement=True)
    batch_identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    series_key: Mapped[str] = mapped_column(String(64), nullable=False)
    series_identity: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset: Mapped[str] = mapped_column(String(64), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    requested_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    requested_scope: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    provider_request_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    row_count_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    row_count_written: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dataset_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(String(500))

    stock_basic_rows: Mapped[list[StockBasicRecord]] = relationship(back_populates="ingestion_run")
    daily_price_rows: Mapped[list[DailyPriceRecord]] = relationship(back_populates="ingestion_run")
    trade_calendar_rows: Mapped[list[TradeCalendarRecord]] = relationship(back_populates="ingestion_run")


class StockBasicRecord(Base):
    __tablename__ = "stock_basic"
    __table_args__ = (
        UniqueConstraint("ingestion_run_id", "source", "stock_code", name="uq_stock_basic_run_natural_key"),
        Index("ix_stock_basic_natural_key", "source", "stock_code", "ingestion_run_id"),
    )

    id: Mapped[int] = mapped_column(IDENTITY_TYPE, primary_key=True, autoincrement=True)
    ingestion_run_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="RESTRICT"), nullable=False
    )
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    stock_name: Mapped[str] = mapped_column(String(200), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    industry: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    listing_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)

    ingestion_run: Mapped[IngestionRun] = relationship(back_populates="stock_basic_rows")


class DailyPriceRecord(Base):
    __tablename__ = "daily_price"
    __table_args__ = (
        UniqueConstraint(
            "ingestion_run_id",
            "source",
            "stock_code",
            "trade_date",
            "adjust_type",
            name="uq_daily_price_run_natural_key",
        ),
        CheckConstraint("volume >= 0", name="ck_daily_price_volume_nonnegative"),
        CheckConstraint("amount >= 0", name="ck_daily_price_amount_nonnegative"),
        Index("ix_daily_price_natural_key", "source", "stock_code", "trade_date", "adjust_type", "ingestion_run_id"),
        Index("ix_daily_price_trade_date", "trade_date", "stock_code"),
    )

    id: Mapped[int] = mapped_column(IDENTITY_TYPE, primary_key=True, autoincrement=True)
    ingestion_run_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="RESTRICT"), nullable=False
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    adjust_type: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(64), nullable=False)

    ingestion_run: Mapped[IngestionRun] = relationship(back_populates="daily_price_rows")


class TradeCalendarRecord(Base):
    __tablename__ = "trade_calendar"
    __table_args__ = (
        UniqueConstraint("ingestion_run_id", "source", "trade_date", name="uq_trade_calendar_run_natural_key"),
        Index("ix_trade_calendar_natural_key", "source", "trade_date", "ingestion_run_id"),
    )

    id: Mapped[int] = mapped_column(IDENTITY_TYPE, primary_key=True, autoincrement=True)
    ingestion_run_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="RESTRICT"), nullable=False
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)

    ingestion_run: Mapped[IngestionRun] = relationship(back_populates="trade_calendar_rows")
