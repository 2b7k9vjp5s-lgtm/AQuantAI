from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.market_cockpit import get_market_cockpit_session_factory
from backend.database.benchmark_data import BenchmarkPersistenceService
from backend.database.engine import build_session_factory
from backend.database.market_data import MarketDataPersistenceService
from backend.database.models import Base
from backend.main import app
from market_cockpit.benchmark_calculator import (
    BenchmarkCalculationError,
    calculate_benchmark_metrics,
)
from market_cockpit.benchmark_fixtures import (
    BENCHMARK_FIXTURE_CURRENT_CUTOFF,
    BENCHMARK_FIXTURE_DATES,
    BENCHMARK_FIXTURE_END_DATE,
    BENCHMARK_FIXTURE_HISTORICAL_CUTOFF,
    BENCHMARK_FIXTURE_PROVIDER,
    BENCHMARK_FIXTURE_SCOPE,
    BENCHMARK_FIXTURE_START_DATE,
    build_benchmark_fixture,
)
from market_cockpit.benchmark_repository import BenchmarkRepository
from market_cockpit.fixtures import (
    COCKPIT_FIXTURE_ADJUST_TYPE,
    COCKPIT_FIXTURE_CURRENT_CUTOFF,
    COCKPIT_FIXTURE_END_DATE,
    COCKPIT_FIXTURE_PROVIDER,
    COCKPIT_FIXTURE_SCOPE,
    COCKPIT_FIXTURE_START_DATE,
    build_market_cockpit_fixture,
)
from scripts.demo_benchmark_context import build_persisted_benchmark_demo


@pytest.fixture
def database() -> Iterator[tuple[Engine, sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine, build_session_factory(engine)
    engine.dispose()


@pytest.fixture
def client(database) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    _, session_factory = database
    app.dependency_overrides[get_market_cockpit_session_factory] = lambda: session_factory
    try:
        yield TestClient(app), session_factory
    finally:
        app.dependency_overrides.clear()


def _equity(
    session_factory: sessionmaker[Session],
    *,
    revision: str = "current",
    cutoff: str = COCKPIT_FIXTURE_CURRENT_CUTOFF,
):
    return MarketDataPersistenceService(session_factory).ingest_bundle(
        build_market_cockpit_fixture(revision=revision),
        provider=COCKPIT_FIXTURE_PROVIDER,
        requested_start_date=COCKPIT_FIXTURE_START_DATE,
        requested_end_date=COCKPIT_FIXTURE_END_DATE,
        information_cutoff_date=cutoff,
        requested_scope=COCKPIT_FIXTURE_SCOPE,
        adjust_type=COCKPIT_FIXTURE_ADJUST_TYPE,
    )


def _benchmark(
    session_factory: sessionmaker[Session],
    *,
    revision: str = "current",
    cutoff: str = BENCHMARK_FIXTURE_CURRENT_CUTOFF,
):
    return BenchmarkPersistenceService(session_factory).ingest_bundle(
        build_benchmark_fixture(revision=revision),
        provider=BENCHMARK_FIXTURE_PROVIDER,
        requested_start_date=BENCHMARK_FIXTURE_START_DATE,
        requested_end_date=BENCHMARK_FIXTURE_END_DATE,
        information_cutoff_date=cutoff,
        requested_scope=BENCHMARK_FIXTURE_SCOPE,
        endpoint="fixture_index_history",
        adapter_compatibility_version="benchmark-fixture-v1",
        adapter_version="benchmark-fixture-v1",
        provider_request_metadata={
            "collection_timestamp_utc": "2026-04-05T12:00:00Z",
            "effective_information_cutoff_date": cutoff,
            "network_mode": "offline-fixture",
            "timeout_seconds": 1,
            "max_retries": 0,
            "unknown_metadata": "must-not-be-exposed",
        },
    )


def test_exact_close_formulas_and_minimum_windows(database) -> None:
    _, session_factory = database
    result = _benchmark(session_factory)
    with session_factory() as session:
        snapshot = BenchmarkRepository(session).load_snapshot(series_key=result.series_key)
    metrics, warnings = calculate_benchmark_metrics(snapshot)
    first = metrics[0]
    frame = snapshot.benchmark_index_daily.loc[
        snapshot.benchmark_index_daily["index_code"].eq(first.index_code)
    ].sort_values("trade_date")
    closes = frame["close"].to_numpy(dtype=float)
    returns = closes[-20:] / closes[-21:-1] - 1.0
    wealth = np.concatenate(([1.0], np.cumprod(1.0 + returns)))
    assert first.latest_close == pytest.approx(closes[-1])
    assert first.latest_session == BENCHMARK_FIXTURE_DATES[-1]
    assert first.latest_return == pytest.approx(closes[-1] / closes[-2] - 1)
    assert first.sma20 == pytest.approx(closes[-20:].mean())
    assert first.sma60 == pytest.approx(closes[-60:].mean())
    assert first.realized_volatility_20 == pytest.approx(returns.std(ddof=1) * np.sqrt(252))
    assert first.max_drawdown_20 == pytest.approx(
        np.min(wealth / np.maximum.accumulate(wealth) - 1.0)
    )
    assert warnings == []


def test_insufficient_and_mismatched_sessions_return_null_with_warnings(database) -> None:
    _, session_factory = database
    result = _benchmark(session_factory)
    with session_factory() as session:
        snapshot = BenchmarkRepository(session).load_snapshot(series_key=result.series_key)
    frame = snapshot.benchmark_index_daily.copy()
    frame = frame.loc[
        ~(
            frame["index_code"].eq("000001")
            & ~frame["trade_date"].isin(BENCHMARK_FIXTURE_DATES[-10:])
        )
    ]
    metrics, warnings = calculate_benchmark_metrics(
        replace(snapshot, benchmark_index_daily=frame)
    )
    first = next(item for item in metrics if item.index_code == "000001")
    assert first.latest_return is not None
    assert first.sma20 is None
    assert first.sma60 is None
    assert first.realized_volatility_20 is None
    assert any("mismatched persisted sessions" in warning for warning in warnings)


def test_invalid_injected_close_fails_instead_of_fabricating_values(database) -> None:
    _, session_factory = database
    result = _benchmark(session_factory)
    with session_factory() as session:
        snapshot = BenchmarkRepository(session).load_snapshot(series_key=result.series_key)
    frame = snapshot.benchmark_index_daily.copy()
    frame.loc[frame.index[0], "close"] = np.inf
    with pytest.raises(BenchmarkCalculationError, match="invalid close"):
        calculate_benchmark_metrics(replace(snapshot, benchmark_index_daily=frame))


def test_repository_permitted_session_excludes_future_rows(database) -> None:
    _, session_factory = database
    result = _benchmark(session_factory)
    permitted = BENCHMARK_FIXTURE_DATES[-5]
    with session_factory() as session:
        snapshot = BenchmarkRepository(session).load_snapshot(
            series_key=result.series_key,
            permitted_end_session=permitted,
        )
    assert snapshot.effective_benchmark_session == permitted
    assert snapshot.benchmark_index_daily["trade_date"].max() == permitted


def test_api_equity_only_is_compatible_and_benchmark_is_optional(client) -> None:
    test_client, session_factory = client
    equity = _equity(session_factory)
    response = test_client.get("/market-cockpit/snapshot?series_key=" + equity.series_key)
    assert response.status_code == 200
    payload = response.json()
    assert payload["benchmark_context"] is None
    assert payload["metrics"]["latest_session"]["unavailable_count"] == 0


def test_api_returns_separate_benchmark_provenance_and_alignment(client) -> None:
    test_client, session_factory = client
    equity = _equity(session_factory)
    benchmark = _benchmark(session_factory)
    response = test_client.get(
        "/market-cockpit/snapshot?series_key="
        + equity.series_key
        + "&benchmark_series_key="
        + benchmark.series_key
    )
    assert response.status_code == 200
    payload = response.json()
    context = payload["benchmark_context"]
    assert context["label"] == "provider-attributed benchmark index context"
    assert context["alignment_status"] == "aligned"
    assert context["provenance"]["series_key"] == benchmark.series_key
    assert context["provenance"]["series_key"] != payload["provenance"]["series_key"]
    assert context["provenance"]["endpoint"] == "fixture_index_history"
    assert context["provenance"]["index_codes"] == ["000001", "000300"]
    assert len(context["metrics"]) == 2
    assert "unknown_metadata" not in str(context)
    assert "must-not-be-exposed" not in str(context)


def test_invalid_or_missing_benchmark_selector_has_422_or_404(client) -> None:
    test_client, session_factory = client
    equity = _equity(session_factory)
    invalid = test_client.get(
        "/market-cockpit/snapshot?series_key="
        + equity.series_key
        + "&benchmark_series_key=bad"
    )
    missing = test_client.get(
        "/market-cockpit/snapshot?series_key="
        + equity.series_key
        + "&benchmark_series_key="
        + "a" * 64
    )
    equity_as_benchmark = test_client.get(
        "/market-cockpit/snapshot?series_key="
        + equity.series_key
        + "&benchmark_series_key="
        + equity.series_key
    )
    assert invalid.status_code == 422
    assert missing.status_code == 404
    assert equity_as_benchmark.status_code == 404
    assert "benchmark snapshot" in missing.json()["detail"]


def test_historical_cutoff_selects_historical_benchmark_run(client) -> None:
    test_client, session_factory = client
    _equity(
        session_factory,
        revision="historical",
        cutoff=BENCHMARK_FIXTURE_HISTORICAL_CUTOFF,
    )
    equity = _equity(session_factory)
    historical = _benchmark(
        session_factory,
        revision="historical",
        cutoff=BENCHMARK_FIXTURE_HISTORICAL_CUTOFF,
    )
    current = _benchmark(session_factory)
    assert historical.series_key == current.series_key
    response = test_client.get(
        "/market-cockpit/snapshot?series_key="
        + equity.series_key
        + "&benchmark_series_key="
        + current.series_key
        + "&as_of_cutoff="
        + BENCHMARK_FIXTURE_HISTORICAL_CUTOFF
    )
    assert response.status_code == 200
    provenance = response.json()["benchmark_context"]["provenance"]
    assert provenance["ingestion_run_id"] == historical.ingestion_run_id
    assert provenance["requested_as_of_cutoff"] == BENCHMARK_FIXTURE_HISTORICAL_CUTOFF


def test_different_benchmark_cutoff_and_session_are_explicit(client) -> None:
    test_client, session_factory = client
    equity = _equity(session_factory)
    bundle = build_benchmark_fixture(revision="historical")
    rows = bundle.benchmark_index_daily
    bundle = replace(
        bundle,
        benchmark_index_daily=rows.loc[
            rows["trade_date"].ne(BENCHMARK_FIXTURE_DATES[-1])
        ].copy(),
    )
    benchmark = BenchmarkPersistenceService(session_factory).ingest_bundle(
        bundle,
        provider=BENCHMARK_FIXTURE_PROVIDER,
        requested_start_date=BENCHMARK_FIXTURE_START_DATE,
        requested_end_date=BENCHMARK_FIXTURE_END_DATE,
        information_cutoff_date=BENCHMARK_FIXTURE_HISTORICAL_CUTOFF,
        requested_scope=BENCHMARK_FIXTURE_SCOPE,
        endpoint="fixture_index_history",
        adapter_compatibility_version="benchmark-fixture-v1",
    )
    response = test_client.get(
        "/market-cockpit/snapshot?series_key="
        + equity.series_key
        + "&benchmark_series_key="
        + benchmark.series_key
    )
    assert response.status_code == 200
    context = response.json()["benchmark_context"]
    assert context["alignment_status"] == "different_session"
    assert any("information cutoffs differ" in warning for warning in context["warnings"])
    assert any("effective sessions differ" in warning for warning in context["warnings"])


def test_page_uses_safe_dom_and_neutral_read_only_benchmark_wording() -> None:
    page = TestClient(app).get("/market-cockpit").text
    script = (
        Path(__file__).resolve().parents[1]
        / "market_cockpit"
        / "static"
        / "market_cockpit.js"
    ).read_text(encoding="utf-8")
    assert "provider-attributed benchmark index context" in script
    assert "Benchmark index context" in page
    assert "benchmark_series_key" in page
    assert "Required sessions (return / SMA20 / SMA60 / risk)" in script
    assert "innerHTML" not in script
    assert "eval(" not in script
    assert "textContent" in script
    assert "<form" not in page.lower()
    assert "<button" not in page.lower()
    assert "automatic refresh" in page.lower()


def test_persisted_benchmark_demo_reports_current_and_historical(tmp_path) -> None:
    path = tmp_path / "benchmark-demo.sqlite3"
    engine = create_engine(f"sqlite+pysqlite:///{path.as_posix()}")
    Base.metadata.create_all(engine)
    engine.dispose()
    payload = build_persisted_benchmark_demo(f"sqlite+pysqlite:///{path.as_posix()}")
    assert payload["current"]["benchmark_information_cutoff"] == BENCHMARK_FIXTURE_CURRENT_CUTOFF
    assert payload["historical"]["benchmark_information_cutoff"] == BENCHMARK_FIXTURE_HISTORICAL_CUTOFF
    assert payload["current"]["alignment_status"] == "aligned"
    assert payload["read_only"] is True
    assert payload["network_access"] is False
