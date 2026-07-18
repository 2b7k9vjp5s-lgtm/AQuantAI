from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import datetime, timezone
from importlib.metadata import version

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database.engine import build_session_factory
from backend.main import app
from backend.database.models import Base, DailyPriceRecord, IngestionRun, StockBasicRecord, TradeCalendarRecord
from backend.database.series import build_snapshot_series_identity
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
from scripts.ingest_akshare_market_data import (
    AKSHARE_COMPATIBILITY_PARAMETERS,
    AkshareIngestionRequest,
    akshare_compatibility_parameters,
    run_controlled_akshare_ingestion,
)
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
        self.calls = 0

    def stock_info_a_code_name(self) -> pd.DataFrame:
        self.calls += 1
        return pd.DataFrame(
            [
                {"code": "000001", "name": "Ping An Bank"},
                {"code": "600000", "name": "SPDB"},
            ]
        )

    def stock_zh_a_hist(self, symbol, period, start_date, end_date, adjust) -> pd.DataFrame:
        self.calls += 1
        del period, start_date, end_date, adjust
        dates = ["2026-07-08", "2026-07-10" if self.bad_date else "2026-07-09"]
        return pd.DataFrame([_daily_row(value, symbol) for value in dates])

    def tool_trade_date_hist_sina(self) -> pd.DataFrame:
        self.calls += 1
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
        assert run.provider_request_metadata["akshare_package_version"] == version("akshare")
        assert run.provider_request_metadata["collection_timestamp_utc"].endswith("Z")


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


@pytest.mark.parametrize("cutoff", ["20260717", "20260719"])
def test_live_past_and_future_cutoffs_fail_before_provider_or_database_activity(
    database, cutoff: str
) -> None:
    _, session_factory = database
    client = FrozenAkshare()
    provider = AkshareDataProvider(client, max_retries=0)
    engine_calls: list[str | None] = []

    def reject_engine(database_url: str | None) -> Engine:
        engine_calls.append(database_url)
        raise AssertionError("database engine must not be created")

    request = replace(_request(), information_cutoff_date=cutoff, allow_network=True)
    with pytest.raises(ValueError, match="UTC collection date 20260718"):
        run_controlled_akshare_ingestion(
            request,
            provider=provider,
            clock=lambda: datetime(2026, 7, 18, 1, 2, 3, tzinfo=timezone.utc),
            engine_factory=reject_engine,
        )

    assert client.calls == 0
    assert engine_calls == []
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(IngestionRun)) == 0
        assert session.scalar(select(func.count()).select_from(StockBasicRecord)) == 0
        assert session.scalar(select(func.count()).select_from(DailyPriceRecord)) == 0
        assert session.scalar(select(func.count()).select_from(TradeCalendarRecord)) == 0


def test_live_collection_date_cutoff_is_accepted_and_records_utc_timestamp(database) -> None:
    _, session_factory = database
    client = FrozenAkshare()
    request = replace(_request(), information_cutoff_date="20260718", allow_network=True)

    payload = run_controlled_akshare_ingestion(
        request,
        provider=AkshareDataProvider(client, max_retries=0),
        session_factory=session_factory,
        clock=lambda: datetime(2026, 7, 18, 9, 10, 11, 123456, tzinfo=timezone.utc),
    )

    assert payload["rows_written"] == 8
    assert client.calls == 4
    with session_factory() as session:
        run = session.get(IngestionRun, payload["ingestion_run_id"])
        assert run is not None
        assert run.information_cutoff_date.isoformat() == "2026-07-18"
        assert run.provider_request_metadata["collection_timestamp_utc"] == (
            "2026-07-18T09:10:11.123456Z"
        )
        assert run.provider_request_metadata["effective_information_cutoff_date"] == "20260718"


def _series_key(compatibility_parameters: dict[str, str]) -> str:
    return build_snapshot_series_identity(
        provider="akshare",
        dataset="market_data_bundle",
        contract_version="1.0",
        datasets=["daily_price", "stock_basic", "trade_calendar"],
        stock_codes=["000001", "600000"],
        requested_start_date="20260708",
        requested_end_date="20260709",
        adjust_type="qfq",
        compatibility_parameters=compatibility_parameters,
    ).series_key


def test_adapter_compatibility_version_changes_series_key() -> None:
    changed = akshare_compatibility_parameters(
        adapter_compatibility_version="aquantai.akshare-adapter.v2"
    )

    assert _series_key(changed) != _series_key(AKSHARE_COMPATIBILITY_PARAMETERS)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("stock_basic_endpoint", "stock_basic_v2"),
        ("daily_price_endpoint", "daily_price_v2"),
        ("trade_calendar_endpoint", "trade_calendar_v2"),
    ],
)
def test_any_endpoint_mapping_change_creates_a_distinct_series(field: str, value: str) -> None:
    parameters = dict(AKSHARE_COMPATIBILITY_PARAMETERS)
    parameters[field] = value

    assert _series_key(parameters) != _series_key(AKSHARE_COMPATIBILITY_PARAMETERS)


def test_timeout_retry_and_network_mode_do_not_change_series_key() -> None:
    fixed_clock = lambda: datetime(2026, 7, 18, tzinfo=timezone.utc)
    base_request = replace(
        _request(dry_run=True),
        information_cutoff_date="20260718",
        timeout_seconds=1,
        max_retries=0,
    )
    injected = run_controlled_akshare_ingestion(
        base_request,
        provider=AkshareDataProvider(FrozenAkshare(), request_timeout_seconds=1, max_retries=0),
        clock=fixed_clock,
    )
    live = run_controlled_akshare_ingestion(
        replace(base_request, allow_network=True, timeout_seconds=5, max_retries=2),
        provider=AkshareDataProvider(FrozenAkshare(), request_timeout_seconds=5, max_retries=2),
        clock=fixed_clock,
    )

    assert injected["series_key"] == live["series_key"]


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
