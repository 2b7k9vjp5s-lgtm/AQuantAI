from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import datetime, timezone
from importlib.metadata import version

import pandas as pd
import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database.engine import build_session_factory
from backend.database.models import Base, BenchmarkIndexDailyRecord, IngestionRun
from datasource.akshare import AkshareDataProvider, AkshareProviderError, AkshareProviderTimeout
from datasource.akshare.provider import (
    BENCHMARK_INDEX_ENDPOINT,
    RAW_AMOUNT,
    RAW_CLOSE,
    RAW_DATE,
    RAW_HIGH,
    RAW_LOW,
    RAW_OPEN,
    RAW_VOLUME,
)
from datasource.base import BENCHMARK_INDEX_DAILY_COLUMNS
from scripts.ingest_akshare_benchmark_data import (
    BenchmarkIngestionRequest,
    run_controlled_benchmark_ingestion,
)


@pytest.fixture
def database() -> Iterator[sessionmaker[Session]]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _foreign_keys(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield build_session_factory(engine)
    engine.dispose()


class FrozenBenchmarkClient:
    def __init__(self, *, malformed: bool = False) -> None:
        self.calls = 0
        self.args: list[dict] = []
        self.malformed = malformed

    def index_zh_a_hist(self, **kwargs) -> pd.DataFrame:
        self.calls += 1
        self.args.append(kwargs)
        if self.malformed:
            return pd.DataFrame([{"unexpected": 1}])
        return pd.DataFrame(
            [
                _raw_row("2026-01-05", 1000.0),
                _raw_row("2026-01-06", 1010.0),
            ]
        )


def _raw_row(trade_date: str, close: float) -> dict:
    return {
        RAW_DATE: trade_date,
        RAW_OPEN: close - 1,
        RAW_HIGH: close + 2,
        RAW_LOW: close - 2,
        RAW_CLOSE: close,
        RAW_VOLUME: 1000.0,
        RAW_AMOUNT: 100000.0,
    }


def _request(*, dry_run: bool = False) -> BenchmarkIngestionRequest:
    return BenchmarkIngestionRequest(
        index_codes=("000001", "000300"),
        start_date="20260105",
        end_date="20260106",
        information_cutoff_date="20260106",
        dry_run=dry_run,
        timeout_seconds=1,
        max_retries=0,
    )


def test_provider_maps_only_reviewed_endpoint_and_normalized_columns() -> None:
    client = FrozenBenchmarkClient()
    provider = AkshareDataProvider(client, max_retries=0)
    bundle = provider.get_benchmark_index_daily(["000300", "000001"], "20260105", "20260106")
    frame = bundle.benchmark_index_daily
    assert list(frame.columns) == BENCHMARK_INDEX_DAILY_COLUMNS
    assert frame["index_code"].tolist() == ["000001", "000001", "000300", "000300"]
    assert frame["source"].unique().tolist() == ["akshare"]
    assert client.calls == 2
    assert all(item["period"] == "daily" for item in client.args)


def test_provider_rejects_more_than_twenty_codes() -> None:
    provider = AkshareDataProvider(FrozenBenchmarkClient())
    with pytest.raises(AkshareProviderError, match="At most 20 benchmark"):
        provider.get_benchmark_index_daily(
            [f"{value:06d}" for value in range(21)], "20260105", "20260106"
        )


def test_dry_run_never_creates_engine_or_ingestion_run(database) -> None:
    provider = AkshareDataProvider(FrozenBenchmarkClient(), max_retries=0)

    def reject_engine(_url) -> Engine:
        raise AssertionError("dry-run must not create a database engine")

    payload = run_controlled_benchmark_ingestion(
        _request(dry_run=True),
        provider=provider,
        engine_factory=reject_engine,
    )
    assert payload["mode"] == "dry-run"
    assert payload["dataset_counts"] == {"benchmark_index_daily": 4}
    assert payload["canonical_scope"]["endpoint"] == BENCHMARK_INDEX_ENDPOINT
    with database() as session:
        assert session.scalar(select(func.count()).select_from(IngestionRun)) == 0


def test_repeated_mocked_ingestion_is_idempotent_and_auditable(database) -> None:
    provider = AkshareDataProvider(FrozenBenchmarkClient(), max_retries=0)
    first = run_controlled_benchmark_ingestion(
        _request(), provider=provider, session_factory=database
    )
    second = run_controlled_benchmark_ingestion(
        _request(), provider=provider, session_factory=database
    )
    assert first["rows_written"] == 4
    assert second["rows_written"] == 0
    assert second["ingestion_run_id"] == first["ingestion_run_id"]
    with database() as session:
        run = session.get(IngestionRun, first["ingestion_run_id"])
        assert run is not None
        assert run.provider_request_metadata["collection_endpoint"] == BENCHMARK_INDEX_ENDPOINT
        assert run.provider_request_metadata["akshare_package_version"] == version("akshare")
        assert run.provider_request_metadata["network_mode"] == "injected-mock"
        assert session.scalar(select(func.count()).select_from(BenchmarkIndexDailyRecord)) == 4


def test_malformed_provider_response_leaves_failed_attempt_and_zero_rows(database) -> None:
    provider = AkshareDataProvider(FrozenBenchmarkClient(malformed=True), max_retries=0)
    with pytest.raises(AkshareProviderError, match="missing columns"):
        run_controlled_benchmark_ingestion(
            _request(), provider=provider, session_factory=database
        )
    with database() as session:
        run = session.scalar(select(IngestionRun))
        assert run is not None and run.status == "failed"
        assert session.scalar(select(func.count()).select_from(BenchmarkIndexDailyRecord)) == 0


def test_network_requires_explicit_authorization() -> None:
    with pytest.raises(ValueError, match="requires --allow-network"):
        run_controlled_benchmark_ingestion(_request())


@pytest.mark.parametrize("cutoff", ["20260717", "20260719"])
def test_live_invalid_cutoff_fails_before_provider_and_engine(cutoff: str) -> None:
    client = FrozenBenchmarkClient()
    provider = AkshareDataProvider(client, max_retries=0)
    engine_calls: list[str | None] = []

    def reject_engine(url: str | None) -> Engine:
        engine_calls.append(url)
        raise AssertionError("engine must not be created")

    request = replace(
        _request(),
        information_cutoff_date=cutoff,
        allow_network=True,
    )
    with pytest.raises(ValueError, match="UTC collection date 20260718"):
        run_controlled_benchmark_ingestion(
            request,
            provider=provider,
            clock=lambda: datetime(2026, 7, 18, tzinfo=timezone.utc),
            engine_factory=reject_engine,
        )
    assert client.calls == 0
    assert engine_calls == []


def test_live_collection_date_cutoff_is_accepted(database) -> None:
    client = FrozenBenchmarkClient()
    payload = run_controlled_benchmark_ingestion(
        replace(
            _request(),
            information_cutoff_date="20260718",
            allow_network=True,
        ),
        provider=AkshareDataProvider(client, max_retries=0),
        session_factory=database,
        clock=lambda: datetime(2026, 7, 18, 8, 9, 10, tzinfo=timezone.utc),
    )
    assert payload["rows_written"] == 4
    assert client.calls == 2
    with database() as session:
        run = session.get(IngestionRun, payload["ingestion_run_id"])
        assert run is not None
        assert run.provider_request_metadata["collection_timestamp_utc"] == "2026-07-18T08:09:10Z"


def test_timeout_retry_and_network_mode_do_not_change_series_key() -> None:
    first = run_controlled_benchmark_ingestion(
        replace(_request(dry_run=True), timeout_seconds=1, max_retries=0),
        provider=AkshareDataProvider(
            FrozenBenchmarkClient(), request_timeout_seconds=1, max_retries=0
        ),
    )
    second = run_controlled_benchmark_ingestion(
        replace(_request(dry_run=True), timeout_seconds=5, max_retries=2),
        provider=AkshareDataProvider(
            FrozenBenchmarkClient(), request_timeout_seconds=5, max_retries=2
        ),
    )
    assert first["series_key"] == second["series_key"]


class RaisingRunner:
    def __init__(self) -> None:
        self.calls = 0

    def call(self, endpoint, _kwargs, _timeout):
        assert endpoint == BENCHMARK_INDEX_ENDPOINT
        self.calls += 1
        raise AkshareProviderTimeout("bounded benchmark timeout")


def test_benchmark_timeout_retries_are_finite() -> None:
    runner = RaisingRunner()
    provider = AkshareDataProvider(
        runner=runner,
        max_retries=1,
        sleep=lambda _seconds: None,
    )
    with pytest.raises(AkshareProviderTimeout, match="bounded benchmark timeout"):
        provider.get_benchmark_index_daily(["000001"], "20260105", "20260106")
    assert runner.calls == 2
