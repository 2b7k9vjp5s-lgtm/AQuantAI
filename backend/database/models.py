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
    benchmark_index_daily_rows: Mapped[list[BenchmarkIndexDailyRecord]] = relationship(
        back_populates="ingestion_run"
    )
    sector_definition_rows: Mapped[list[SectorDefinitionRecord]] = relationship(
        back_populates="ingestion_run"
    )
    sector_daily_rows: Mapped[list[SectorDailyRecord]] = relationship(
        back_populates="ingestion_run"
    )


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


class BenchmarkIndexDailyRecord(Base):
    __tablename__ = "benchmark_index_daily"
    __table_args__ = (
        UniqueConstraint(
            "ingestion_run_id",
            "source",
            "index_code",
            "trade_date",
            name="uq_benchmark_index_daily_run_natural_key",
        ),
        CheckConstraint("close > 0", name="ck_benchmark_index_daily_close_positive"),
        CheckConstraint("open IS NULL OR open > 0", name="ck_benchmark_index_daily_open_positive"),
        CheckConstraint("high IS NULL OR high > 0", name="ck_benchmark_index_daily_high_positive"),
        CheckConstraint("low IS NULL OR low > 0", name="ck_benchmark_index_daily_low_positive"),
        CheckConstraint("volume IS NULL OR volume >= 0", name="ck_benchmark_index_daily_volume_nonnegative"),
        CheckConstraint("amount IS NULL OR amount >= 0", name="ck_benchmark_index_daily_amount_nonnegative"),
        CheckConstraint(
            "open IS NULL OR high IS NULL OR low IS NULL OR (low <= open AND open <= high)",
            name="ck_benchmark_index_daily_open_range",
        ),
        CheckConstraint(
            "high IS NULL OR low IS NULL OR (low <= close AND close <= high)",
            name="ck_benchmark_index_daily_close_range",
        ),
        Index(
            "ix_benchmark_index_daily_run_code_date",
            "ingestion_run_id",
            "index_code",
            "trade_date",
        ),
        Index(
            "ix_benchmark_index_daily_source_code_date",
            "source",
            "index_code",
            "trade_date",
        ),
    )

    id: Mapped[int] = mapped_column(IDENTITY_TYPE, primary_key=True, autoincrement=True)
    ingestion_run_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="RESTRICT"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    index_code: Mapped[str] = mapped_column(String(32), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float | None] = mapped_column(Float)
    amount: Mapped[float | None] = mapped_column(Float)

    ingestion_run: Mapped[IngestionRun] = relationship(
        back_populates="benchmark_index_daily_rows"
    )


class SectorDefinitionRecord(Base):
    __tablename__ = "sector_definition"
    __table_args__ = (
        UniqueConstraint(
            "ingestion_run_id",
            "source",
            "classification_system",
            "sector_code",
            name="uq_sector_definition_run_natural_key",
        ),
        Index(
            "ix_sector_definition_run_class_code",
            "ingestion_run_id",
            "classification_system",
            "classification_level",
            "sector_code",
        ),
        Index(
            "ix_sector_definition_source_class_code",
            "source",
            "classification_system",
            "sector_code",
        ),
    )

    id: Mapped[int] = mapped_column(IDENTITY_TYPE, primary_key=True, autoincrement=True)
    ingestion_run_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="RESTRICT"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    sector_code: Mapped[str] = mapped_column(String(32), nullable=False)
    sector_name: Mapped[str] = mapped_column(String(200), nullable=False)
    classification_system: Mapped[str] = mapped_column(String(128), nullable=False)
    classification_level: Mapped[str | None] = mapped_column(String(64))
    parent_sector_code: Mapped[str | None] = mapped_column(String(32))
    parent_sector_name: Mapped[str | None] = mapped_column(String(200))

    ingestion_run: Mapped[IngestionRun] = relationship(
        back_populates="sector_definition_rows"
    )


class SectorDailyRecord(Base):
    __tablename__ = "sector_daily"
    __table_args__ = (
        UniqueConstraint(
            "ingestion_run_id",
            "source",
            "sector_code",
            "trade_date",
            name="uq_sector_daily_run_natural_key",
        ),
        CheckConstraint("close > 0", name="ck_sector_daily_close_positive"),
        CheckConstraint("open IS NULL OR open > 0", name="ck_sector_daily_open_positive"),
        CheckConstraint("high IS NULL OR high > 0", name="ck_sector_daily_high_positive"),
        CheckConstraint("low IS NULL OR low > 0", name="ck_sector_daily_low_positive"),
        CheckConstraint("volume IS NULL OR volume >= 0", name="ck_sector_daily_volume_nonnegative"),
        CheckConstraint("amount IS NULL OR amount >= 0", name="ck_sector_daily_amount_nonnegative"),
        CheckConstraint(
            "turnover_rate IS NULL OR turnover_rate >= 0",
            name="ck_sector_daily_turnover_nonnegative",
        ),
        CheckConstraint(
            "open IS NULL OR high IS NULL OR low IS NULL OR (low <= open AND open <= high)",
            name="ck_sector_daily_open_range",
        ),
        CheckConstraint(
            "high IS NULL OR low IS NULL OR (low <= close AND close <= high)",
            name="ck_sector_daily_close_range",
        ),
        Index(
            "ix_sector_daily_run_code_date",
            "ingestion_run_id",
            "sector_code",
            "trade_date",
        ),
        Index(
            "ix_sector_daily_source_code_date",
            "source",
            "sector_code",
            "trade_date",
        ),
    )

    id: Mapped[int] = mapped_column(IDENTITY_TYPE, primary_key=True, autoincrement=True)
    ingestion_run_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="RESTRICT"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    sector_code: Mapped[str] = mapped_column(String(32), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float | None] = mapped_column(Float)
    amount: Mapped[float | None] = mapped_column(Float)
    turnover_rate: Mapped[float | None] = mapped_column(Float)

    ingestion_run: Mapped[IngestionRun] = relationship(back_populates="sector_daily_rows")
