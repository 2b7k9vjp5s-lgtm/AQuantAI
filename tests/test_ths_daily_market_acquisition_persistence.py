from __future__ import annotations

from copy import deepcopy
from datetime import date
import inspect
import json
from pathlib import Path
from typing import Iterator

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database.benchmark_data import BenchmarkPersistenceService
from backend.database.engine import build_session_factory
from backend.database.market_data import MarketDataPersistenceService
from backend.database.models import (
    Base,
    BenchmarkIndexDailyRecord,
    DailyPriceRecord,
    IngestionRun,
    StockBasicRecord,
    TradeCalendarRecord,
)
from datasource import ths_structured_provider as ths
from datasource.ths_structured_provider import acquisition


FIXTURES = Path(__file__).parent / "fixtures" / "ths_daily_market_acquisition"


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


def _sessions() -> tuple[date, ...]:
    return (date(2026, 7, 27), date(2026, 7, 28))


def _equities() -> tuple[ths.EquityIdentity, ...]:
    return (
        ths.EquityIdentity("SYNTH.SSE.EQ001", "990001", ths.Exchange.SSE),
        ths.EquityIdentity("SYNTH.SZSE.EQ002", "990002", ths.Exchange.SZSE),
    )


def _benchmark_identity() -> ths.BenchmarkIdentity:
    return ths.BenchmarkIdentity("SYNTH.SSE.IDX50", "999950", ths.Exchange.SSE)


def _observations(identities, sessions: tuple[date, ...]) -> tuple[ths.ExpectedObservation, ...]:
    return tuple(
        ths.ExpectedObservation(identity.identity_key, session)
        for session in sessions
        for identity in identities
    )


def _budget() -> ths.AcquisitionQuotaBudget:
    return ths.AcquisitionQuotaBudget(
        budget_revision_id="synthetic-persistence-budget-v1",
        remaining_calls=100,
        remaining_cells=1_000_000,
        per_function_qps=10,
        account_total_qps=20,
    )


def _component(selector, fixture_name: str, *, fixture_value: dict | None = None):
    value = fixture_value or ths.load_synthetic_live_fixture(FIXTURES / fixture_name)
    return ths.ValidatedAcquisitionComponent(
        selector=selector,
        plan=ths.build_live_request_plan(selector, _budget()),
        response=ths.validate_live_response(selector, value),
    )


def _foundation_input(
    *,
    calendar_value: dict | None = None,
    daily_value: dict | None = None,
    benchmark_value: dict | None = None,
) -> ths.DailyMarketFoundationInput:
    sessions = _sessions()
    equities = _equities()
    benchmark = _benchmark_identity()
    listed_selector = ths.ListedInstrumentSelector(
        identities=equities,
        as_of_date=sessions[-1],
        provider_horizon_reference_date=sessions[-1],
    )
    calendar_selector = ths.TradingCalendarSelector(
        exchange=ths.Exchange.SSE,
        requested_dates=sessions,
        provider_horizon_reference_date=sessions[-1],
    )
    daily_selector = ths.AShareDailySelector(
        identities=equities,
        requested_sessions=sessions,
        expected_observations=_observations(equities, sessions),
        adjustment=ths.DailyAdjustment.RAW,
        provider_horizon_reference_date=sessions[-1],
    )
    benchmark_selector = ths.BenchmarkDailySelector(
        identities=(benchmark,),
        requested_sessions=sessions,
        expected_observations=_observations((benchmark,), sessions),
        provider_horizon_reference_date=sessions[-1],
    )
    return ths.DailyMarketFoundationInput(
        listed_instruments=_component(
            listed_selector,
            "stock_basic_success.synthetic.json",
        ),
        trading_calendar=_component(
            calendar_selector,
            "trade_calendar_success.synthetic.json",
            fixture_value=calendar_value,
        ),
        a_share_daily_raw=_component(
            daily_selector,
            "a_share_daily_success.synthetic.json",
            fixture_value=daily_value,
        ),
        benchmark_daily=_component(
            benchmark_selector,
            "benchmark_daily_success.synthetic.json",
            fixture_value=benchmark_value,
        ),
        information_cutoff_date=sessions[-1],
    )


def _service(session_factory: sessionmaker[Session]) -> ths.DailyMarketAcquisitionPersistenceService:
    return ths.DailyMarketAcquisitionPersistenceService(
        MarketDataPersistenceService(session_factory),
        BenchmarkPersistenceService(session_factory),
    )


def test_complete_foundation_persists_both_existing_owners_and_returns_one_receipt(database) -> None:
    _, session_factory = database
    value = _foundation_input()

    receipt = _service(session_factory).persist_foundation(value)

    assert receipt.source_key == "ths-account-structured-provider-v1"
    assert receipt.acquisition_fingerprint == value.acquisition_fingerprint
    assert receipt.covered_sessions == ("2026-07-27", "2026-07-28")
    assert receipt.stock_codes == ("990001", "990002")
    assert receipt.index_codes == ("999950",)
    assert receipt.market.owner == "MarketDataPersistenceService"
    assert receipt.benchmark.owner == "BenchmarkPersistenceService"
    assert receipt.market.idempotent is False
    assert receipt.benchmark.idempotent is False
    assert len(receipt.receipt_fingerprint) == 64

    with session_factory() as session:
        runs = session.scalars(select(IngestionRun).order_by(IngestionRun.id)).all()
        assert len(runs) == 2
        assert {run.dataset for run in runs} == {"market_data_bundle", "benchmark_index_daily"}
        assert all(run.status == "succeeded" for run in runs)
        assert session.scalar(select(func.count()).select_from(StockBasicRecord)) == 2
        assert session.scalar(select(func.count()).select_from(DailyPriceRecord)) == 4
        assert session.scalar(select(func.count()).select_from(TradeCalendarRecord)) == 2
        assert session.scalar(select(func.count()).select_from(BenchmarkIndexDailyRecord)) == 2
        serialized = json.dumps(
            [run.provider_request_metadata for run in runs],
            sort_keys=True,
        ).lower()
        for forbidden in ("token", "secret", "password", "api_key", "credential"):
            assert forbidden not in serialized
        assert all(run.provider == "ths-account-structured-provider-v1" for run in runs)


def test_identical_foundation_replay_is_idempotent_with_stable_receipt_identity(database) -> None:
    _, session_factory = database
    service = _service(session_factory)
    value = _foundation_input()

    first = service.persist_foundation(value)
    second = service.persist_foundation(value)

    assert second.market.ingestion_run_id == first.market.ingestion_run_id
    assert second.benchmark.ingestion_run_id == first.benchmark.ingestion_run_id
    assert second.market.idempotent is True
    assert second.benchmark.idempotent is True
    assert second.market.rows_written == 0
    assert second.benchmark.rows_written == 0
    assert second.receipt_fingerprint == first.receipt_fingerprint
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(IngestionRun)) == 2


def test_changed_source_fact_appends_new_market_run_without_rewriting_prior_history(database) -> None:
    _, session_factory = database
    service = _service(session_factory)
    first_input = _foundation_input()
    first = service.persist_foundation(first_input)

    changed = ths.load_synthetic_live_fixture(
        FIXTURES / "a_share_daily_success.synthetic.json"
    )
    changed["data"]["items"][-1]["close"] = 22.5
    second_input = _foundation_input(daily_value=changed)
    second = service.persist_foundation(second_input)

    assert second.market.ingestion_run_id != first.market.ingestion_run_id
    assert second.market.batch_identifier != first.market.batch_identifier
    assert second.market.idempotent is False
    assert second.benchmark.ingestion_run_id == first.benchmark.ingestion_run_id
    assert second.benchmark.idempotent is True
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(IngestionRun)) == 3
        assert session.scalar(select(func.count()).select_from(DailyPriceRecord)) == 8
        assert session.scalar(select(func.count()).select_from(BenchmarkIndexDailyRecord)) == 2


def test_closed_calendar_session_fails_preflight_before_any_database_run(database) -> None:
    _, session_factory = database
    calendar = ths.load_synthetic_live_fixture(
        FIXTURES / "trade_calendar_success.synthetic.json"
    )
    calendar["data"]["items"][-1]["is_open"] = False

    with pytest.raises(ths.DailyMarketAcquisitionError) as error:
        _service(session_factory).persist_foundation(
            _foundation_input(calendar_value=calendar)
        )

    assert error.value.reason_code is ths.AcquisitionFailureCode.CLOSED_SESSION
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(IngestionRun)) == 0
        assert session.scalar(select(func.count()).select_from(DailyPriceRecord)) == 0


def test_non_owner_benchmark_identity_fails_closed_before_persistence(database) -> None:
    _, session_factory = database
    sessions = _sessions()
    identity = ths.BenchmarkIdentity("SYNTH.SSE.BADIDX", "SYNTH50", ths.Exchange.SSE)
    selector = ths.BenchmarkDailySelector(
        identities=(identity,),
        requested_sessions=sessions,
        expected_observations=_observations((identity,), sessions),
        provider_horizon_reference_date=sessions[-1],
    )
    fixture = ths.load_synthetic_live_fixture(
        FIXTURES / "benchmark_daily_success.synthetic.json"
    )
    fixture["data"]["items"][0]["provider_symbol"] = "SYNTH.SSE.BADIDX"
    fixture["data"]["items"][0]["index_code"] = "SYNTH50"
    fixture["data"]["items"][1]["provider_symbol"] = "SYNTH.SSE.BADIDX"
    fixture["data"]["items"][1]["index_code"] = "SYNTH50"
    original = _foundation_input()
    value = ths.DailyMarketFoundationInput(
        listed_instruments=original.listed_instruments,
        trading_calendar=original.trading_calendar,
        a_share_daily_raw=original.a_share_daily_raw,
        benchmark_daily=_component(
            selector,
            "benchmark_daily_success.synthetic.json",
            fixture_value=fixture,
        ),
        information_cutoff_date=sessions[-1],
    )

    with pytest.raises(ths.DailyMarketAcquisitionError) as error:
        _service(session_factory).persist_foundation(value)
    assert error.value.reason_code is ths.AcquisitionFailureCode.OWNER_IDENTITY_UNSUPPORTED
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(IngestionRun)) == 0


def test_benchmark_database_failure_preserves_market_history_but_emits_no_complete_receipt(database) -> None:
    _, session_factory = database

    def fail_benchmark_insert(_mapper, _connection, _target) -> None:
        raise RuntimeError("synthetic benchmark insert failure")

    event.listen(BenchmarkIndexDailyRecord, "before_insert", fail_benchmark_insert)
    try:
        with pytest.raises(ths.DailyMarketAcquisitionError) as error:
            _service(session_factory).persist_foundation(_foundation_input())
    finally:
        event.remove(BenchmarkIndexDailyRecord, "before_insert", fail_benchmark_insert)

    assert error.value.reason_code is ths.AcquisitionFailureCode.BENCHMARK_PERSISTENCE_FAILED
    assert error.value.persisted_market is not None
    assert error.value.persisted_market.owner == "MarketDataPersistenceService"
    with session_factory() as session:
        runs = session.scalars(select(IngestionRun).order_by(IngestionRun.id)).all()
        assert len(runs) == 2
        assert [run.status for run in runs] == ["succeeded", "failed"]
        assert session.scalar(select(func.count()).select_from(DailyPriceRecord)) == 4
        assert session.scalar(select(func.count()).select_from(BenchmarkIndexDailyRecord)) == 0


def test_acquisition_module_has_no_network_credential_or_schema_mutation_path() -> None:
    source = inspect.getsource(acquisition)
    for forbidden in (
        "import requests",
        "import httpx",
        "urllib.request",
        "os.environ",
        "getenv(",
        "credential_value",
        "Base.metadata",
        "ALTER TABLE",
        "CREATE TABLE",
    ):
        assert forbidden not in source
