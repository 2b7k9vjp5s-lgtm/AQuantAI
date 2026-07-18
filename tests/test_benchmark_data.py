from __future__ import annotations

from collections.abc import Iterator

import pandas as pd
import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.database.benchmark_data import (
    BenchmarkDataValidationError,
    BenchmarkPersistenceService,
    validate_benchmark_bundle,
)
from backend.database.engine import build_session_factory
from backend.database.models import Base, BenchmarkIndexDailyRecord, IngestionRun
from backend.database.series import (
    build_benchmark_series_identity,
    build_snapshot_series_identity,
)
from datasource.base import BenchmarkIndexBundle
from market_cockpit.benchmark_fixtures import (
    BENCHMARK_FIXTURE_CURRENT_CUTOFF,
    BENCHMARK_FIXTURE_END_DATE,
    BENCHMARK_FIXTURE_HISTORICAL_CUTOFF,
    BENCHMARK_FIXTURE_PROVIDER,
    BENCHMARK_FIXTURE_SCOPE,
    BENCHMARK_FIXTURE_START_DATE,
    build_benchmark_fixture,
)
from market_cockpit.benchmark_repository import (
    BenchmarkRepository,
    BenchmarkSelectionError,
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


def _ingest(service: BenchmarkPersistenceService, *, revision: str, cutoff: str, **kwargs):
    return service.ingest_bundle(
        build_benchmark_fixture(revision=revision),
        provider=BENCHMARK_FIXTURE_PROVIDER,
        requested_start_date=BENCHMARK_FIXTURE_START_DATE,
        requested_end_date=BENCHMARK_FIXTURE_END_DATE,
        information_cutoff_date=cutoff,
        requested_scope=BENCHMARK_FIXTURE_SCOPE,
        endpoint="fixture_index_history",
        adapter_compatibility_version="benchmark-fixture-v1",
        adapter_version="benchmark-fixture-v1",
        **kwargs,
    )


def test_contract_accepts_null_optional_fields_and_builds_benchmark_only_series(database) -> None:
    frame = build_benchmark_fixture().benchmark_index_daily.loc[
        lambda value: value["index_code"].eq("000001")
    ].copy()
    frame = frame[["source", "index_code", "trade_date", "close"]]
    bundle = BenchmarkIndexBundle(frame)
    scope = {
        "datasets": ["benchmark_index_daily"],
        "index_codes": ["000001"],
        "index_code_semantics": "exact",
    }
    summary = validate_benchmark_bundle(
        bundle,
        provider="fixture",
        requested_start_date=BENCHMARK_FIXTURE_START_DATE,
        requested_end_date=BENCHMARK_FIXTURE_END_DATE,
        information_cutoff_date=BENCHMARK_FIXTURE_CURRENT_CUTOFF,
        requested_scope=scope,
        endpoint="fixture_index_history",
        adapter_compatibility_version="benchmark-fixture-v1",
    )
    equity = build_snapshot_series_identity(
        provider="fixture",
        dataset="market_data_bundle",
        contract_version="1.0",
        datasets=["stock_basic", "daily_price", "trade_calendar"],
        stock_codes=["000001"],
        requested_start_date=BENCHMARK_FIXTURE_START_DATE,
        requested_end_date=BENCHMARK_FIXTURE_END_DATE,
        adjust_type="qfq",
    )
    assert summary.valid is True
    assert summary.dataset_counts == {"benchmark_index_daily": 65}
    assert summary.canonical_scope["series_schema"] == "aquantai.benchmark-snapshot-series.v1"
    assert summary.series_key != equity.series_key
    result = BenchmarkPersistenceService(database).ingest_bundle(
        bundle,
        provider="fixture",
        requested_start_date=BENCHMARK_FIXTURE_START_DATE,
        requested_end_date=BENCHMARK_FIXTURE_END_DATE,
        information_cutoff_date=BENCHMARK_FIXTURE_CURRENT_CUTOFF,
        requested_scope=scope,
        endpoint="fixture_index_history",
        adapter_compatibility_version="benchmark-fixture-v1",
    )
    with database() as session:
        row = session.scalar(
            select(BenchmarkIndexDailyRecord).where(
                BenchmarkIndexDailyRecord.ingestion_run_id == result.ingestion_run_id
            )
        )
        assert row is not None
        assert row.open is None and row.high is None and row.low is None
        assert row.volume is None and row.amount is None


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda frame: frame.assign(close=float("nan")), "close must be finite"),
        (lambda frame: frame.assign(close=0), "close must be positive"),
        (lambda frame: frame.assign(low=frame["high"] + 1), "OHLC values violate"),
        (lambda frame: frame.assign(volume=-1), "volume must be nonnegative"),
        (lambda frame: pd.concat([frame, frame.iloc[[0]]], ignore_index=True), "Duplicate benchmark"),
    ],
)
def test_invalid_benchmark_rows_fail_transactionally(database, mutation, message: str) -> None:
    service = BenchmarkPersistenceService(database)
    bundle = build_benchmark_fixture()
    malformed = BenchmarkIndexBundle(mutation(bundle.benchmark_index_daily.copy()))
    with pytest.raises(BenchmarkDataValidationError, match=message):
        service.ingest_bundle(
            malformed,
            provider=BENCHMARK_FIXTURE_PROVIDER,
            requested_start_date=BENCHMARK_FIXTURE_START_DATE,
            requested_end_date=BENCHMARK_FIXTURE_END_DATE,
            information_cutoff_date=BENCHMARK_FIXTURE_CURRENT_CUTOFF,
            requested_scope=BENCHMARK_FIXTURE_SCOPE,
            endpoint="fixture_index_history",
            adapter_compatibility_version="benchmark-fixture-v1",
        )
    with database() as session:
        run = session.scalar(select(IngestionRun))
        assert run is not None and run.status == "failed"
        assert session.scalar(select(func.count()).select_from(BenchmarkIndexDailyRecord)) == 0


def test_exact_scope_and_sensitive_metadata_fail_closed(database) -> None:
    service = BenchmarkPersistenceService(database)
    with pytest.raises(BenchmarkDataValidationError, match="exact requested"):
        service.ingest_bundle(
            build_benchmark_fixture(),
            provider=BENCHMARK_FIXTURE_PROVIDER,
            requested_start_date=BENCHMARK_FIXTURE_START_DATE,
            requested_end_date=BENCHMARK_FIXTURE_END_DATE,
            information_cutoff_date=BENCHMARK_FIXTURE_CURRENT_CUTOFF,
            requested_scope={
                "datasets": ["benchmark_index_daily"],
                "index_codes": ["000001"],
            },
            endpoint="fixture_index_history",
            adapter_compatibility_version="benchmark-fixture-v1",
        )
    with pytest.raises(BenchmarkDataValidationError, match="Sensitive metadata"):
        _ingest(
            service,
            revision="current",
            cutoff=BENCHMARK_FIXTURE_CURRENT_CUTOFF,
            provider_request_metadata={"api_token": "not-allowed"},
        )


def test_repeated_import_is_idempotent_and_natural_key_is_enforced(database) -> None:
    service = BenchmarkPersistenceService(database)
    first = _ingest(service, revision="current", cutoff=BENCHMARK_FIXTURE_CURRENT_CUTOFF)
    second = _ingest(service, revision="current", cutoff=BENCHMARK_FIXTURE_CURRENT_CUTOFF)
    assert first.rows_written == 130
    assert second.rows_written == 0
    assert second.idempotent is True
    assert second.ingestion_run_id == first.ingestion_run_id
    with database() as session:
        row = session.scalar(select(BenchmarkIndexDailyRecord).limit(1))
        assert row is not None
        session.add(
            BenchmarkIndexDailyRecord(
                ingestion_run_id=row.ingestion_run_id,
                source=row.source,
                index_code=row.index_code,
                trade_date=row.trade_date,
                close=row.close,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_current_and_as_of_select_one_physical_run_without_stitching(database) -> None:
    service = BenchmarkPersistenceService(database)
    historical = _ingest(
        service, revision="historical", cutoff=BENCHMARK_FIXTURE_HISTORICAL_CUTOFF
    )
    current = _ingest(
        service, revision="current", cutoff=BENCHMARK_FIXTURE_CURRENT_CUTOFF
    )
    assert historical.series_key == current.series_key
    with database() as session:
        repository = BenchmarkRepository(session)
        current_snapshot = repository.load_snapshot(series_key=current.series_key)
        historical_snapshot = repository.load_snapshot(
            series_key=current.series_key,
            as_of_cutoff=BENCHMARK_FIXTURE_HISTORICAL_CUTOFF,
        )
    assert current_snapshot.ingestion_run_id == current.ingestion_run_id
    assert historical_snapshot.ingestion_run_id == historical.ingestion_run_id
    current_close = current_snapshot.benchmark_index_daily.loc[
        current_snapshot.benchmark_index_daily["index_code"].eq("000001"), "close"
    ].iloc[-1]
    historical_close = historical_snapshot.benchmark_index_daily.loc[
        historical_snapshot.benchmark_index_daily["index_code"].eq("000001"), "close"
    ].iloc[-1]
    assert current_close != historical_close


def test_repository_requires_complete_benchmark_selector(database) -> None:
    with database() as session:
        repository = BenchmarkRepository(session)
        with pytest.raises(BenchmarkSelectionError, match="explicit benchmark"):
            repository.load_snapshot()


def test_series_identity_changes_for_every_compatibility_boundary() -> None:
    base = dict(
        provider="akshare",
        contract_version="1.0",
        index_codes=["000001"],
        requested_start_date="20260101",
        requested_end_date="20260401",
        endpoint="index_zh_a_hist",
        adapter_compatibility_version="v1",
    )
    original = build_benchmark_series_identity(**base).series_key
    variants = [
        {**base, "provider": "fixture"},
        {**base, "contract_version": "2.0"},
        {**base, "index_codes": ["000001", "000300"]},
        {**base, "requested_end_date": "20260402"},
        {**base, "endpoint": "different_endpoint"},
        {**base, "adapter_compatibility_version": "v2"},
    ]
    assert all(build_benchmark_series_identity(**variant).series_key != original for variant in variants)


def test_benchmark_identity_rejects_non_public_endpoint_and_sensitive_compatibility(database) -> None:
    with pytest.raises(ValueError, match="public identifier"):
        build_benchmark_series_identity(
            provider="akshare",
            contract_version="1.0",
            index_codes=["000001"],
            requested_start_date="20260101",
            requested_end_date="20260401",
            endpoint="https://user:password@example.invalid",
            adapter_compatibility_version="v1",
        )
    with pytest.raises(BenchmarkDataValidationError, match="Sensitive metadata"):
        _ingest(
            BenchmarkPersistenceService(database),
            revision="current",
            cutoff=BENCHMARK_FIXTURE_CURRENT_CUTOFF,
            compatibility_parameters={"database_url": "not-allowed"},
        )
