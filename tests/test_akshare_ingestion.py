from __future__ import annotations

from collections.abc import Iterator

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database.engine import build_session_factory
from backend.main import app
from backend.database.models import Base, DailyPriceRecord, IngestionRun, StockBasicRecord, TradeCalendarRecord
from datasource.akshare import AkshareDataProvider, AkshareProviderError
from datasource.akshare.provider import (
    RAW_AMOUNT,
    RAW_CLOSE,
    RAW_DATE,
    RAW_HIGH,
    RAW_LOW,
    RAW_OPEN,
    RAW_STOCK_CODE,
    RAW_VOLUME,
)
from scripts.ingest_akshare_market_data import AkshareIngestionRequest, run_controlled_akshare_ingestion
from scripts.demo_research_flow import build_demo_payload


@pytest.fixture
def database() -> Iterator[tuple[Engine, sessionmaker[Session]]]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine, build_session_factory(engine)
    engine.dispose()


class FrozenAkshare:
    def __init__(self, *, bad_date: bool = False, missing_calendar: bool = False) -> None:
        self.bad_date = bad_date
        self.missing_calendar = missing_calendar

    def stock_info_a_code_name(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"code": "000001", "name": "Ping An Bank"},
                {"code": "600000", "name": "SPDB"},
            ]
        )

    def stock_zh_a_hist(self, symbol, period, start_date, end_date, adjust) -> pd.DataFrame:
        del period, start_date, end_date, adjust
        dates = ["2026-07-08", "2026-07-10" if self.bad_date else "2026-07-09"]
        return pd.DataFrame([_daily_row(value, symbol) for value in dates])

    def tool_trade_date_hist_sina(self) -> pd.DataFrame:
        dates = ["2026-07-08"] if self.missing_calendar else ["2026-07-08", "2026-07-09"]
        return pd.DataFrame([{"trade_date": value} for value in dates])


class FailingAkshare(FrozenAkshare):
    def stock_info_a_code_name(self) -> pd.DataFrame:
        raise RuntimeError("mocked provider outage")


def _daily_row(trade_date: str, symbol: str) -> dict:
    return {
        RAW_DATE: trade_date,
        RAW_STOCK_CODE: symbol,
        RAW_OPEN: 10.0,
        RAW_HIGH: 10.8,
        RAW_LOW: 9.9,
        RAW_CLOSE: 10.5,
        RAW_VOLUME: 1000.0,
        RAW_AMOUNT: 10500.0,
    }


def _request(*, dry_run: bool = False) -> AkshareIngestionRequest:
    return AkshareIngestionRequest(
        stock_codes=("000001", "600000"),
        start_date="20260708",
        end_date="20260709",
        adjust_type="qfq",
        information_cutoff_date="20260709",
        dry_run=dry_run,
        timeout_seconds=1,
        max_retries=0,
    )


def test_dry_run_normalizes_without_database_writes(database) -> None:
    _, session_factory = database
    payload = run_controlled_akshare_ingestion(
        _request(dry_run=True),
        provider=AkshareDataProvider(FrozenAkshare(), max_retries=0),
        session_factory=session_factory,
    )

    assert payload["mode"] == "dry-run"
    assert payload["valid"] is True
    assert payload["dataset_counts"] == {"stock_basic": 2, "daily_price": 4, "trade_calendar": 2}
    assert payload["canonical_scope"]["adjust_type"] == "qfq"
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(IngestionRun)) == 0


def test_repeated_mocked_ingestion_is_idempotent_and_records_request_metadata(database) -> None:
    _, session_factory = database
    provider = AkshareDataProvider(FrozenAkshare(), max_retries=0)

    first = run_controlled_akshare_ingestion(_request(), provider=provider, session_factory=session_factory)
    second = run_controlled_akshare_ingestion(_request(), provider=provider, session_factory=session_factory)

    assert first["rows_written"] == 8
    assert second["rows_written"] == 0
    assert second["idempotent"] is True
    assert first["ingestion_run_id"] == second["ingestion_run_id"]
    assert first["series_key"] == second["series_key"]
    with session_factory() as session:
        run = session.get(IngestionRun, first["ingestion_run_id"])
        assert run is not None
        assert run.adapter_version == "akshare-normalizer-v1"
        assert run.provider_request_metadata["network_mode"] == "injected-mock"
        assert run.provider_request_metadata["stock_codes"] == ["000001", "600000"]


@pytest.mark.parametrize(
    ("client", "message"),
    [
        (FailingAkshare(), "mocked provider outage"),
        (FrozenAkshare(bad_date=True), "outside the requested date range"),
        (FrozenAkshare(missing_calendar=True), "missing from trade_calendar"),
    ],
)
def test_provider_and_validation_failures_leave_zero_rows_and_auditable_attempt(
    database, client, message
) -> None:
    _, session_factory = database
    provider = AkshareDataProvider(client, max_retries=0)

    with pytest.raises((AkshareProviderError, ValueError), match=message):
        run_controlled_akshare_ingestion(_request(), provider=provider, session_factory=session_factory)

    with session_factory() as session:
        runs = session.scalars(select(IngestionRun)).all()
        assert len(runs) == 1
        assert runs[0].status == "failed"
        assert runs[0].error_summary
        assert session.scalar(select(func.count()).select_from(StockBasicRecord)) == 0
        assert session.scalar(select(func.count()).select_from(DailyPriceRecord)) == 0
        assert session.scalar(select(func.count()).select_from(TradeCalendarRecord)) == 0


def test_network_access_is_rejected_without_explicit_opt_in() -> None:
    with pytest.raises(ValueError, match="requires --allow-network"):
        run_controlled_akshare_ingestion(_request())


def test_api_dashboard_and_fixture_demo_remain_offline_and_unchanged(monkeypatch) -> None:
    def reject_collection(*_args, **_kwargs):
        raise AssertionError("an ordinary application path attempted AKShare collection")

    monkeypatch.setattr(AkshareDataProvider, "get_market_data_bundle", reject_collection)
    client = TestClient(app)

    assert client.get("/").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/dashboard").status_code == 200
    overview = client.get("/dashboard/overview").json()
    report = client.get("/dashboard/report").json()
    demo = build_demo_payload()

    assert overview["read_only"] is True
    assert report["read_only"] is True
    assert demo["dashboard"]["read_only"] is True
    assert "trade" not in overview["allowed_actions"]
