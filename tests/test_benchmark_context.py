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
from market_cockpit.benchmark_calculator import calculate_benchmark_metrics
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
from market_cockpit.repository import MarketCockpitRepository
from market_cockpit.service import _expected_benchmark_sessions
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


def _benchmark_frame(
    session_factory: sessionmaker[Session],
    frame: pd.DataFrame,
    *,
    cutoff: str = BENCHMARK_FIXTURE_CURRENT_CUTOFF,
    requested_end_date: str = BENCHMARK_FIXTURE_END_DATE,
):
    return BenchmarkPersistenceService(session_factory).ingest_bundle(
        replace(build_benchmark_fixture(), benchmark_index_daily=frame.copy()),
        provider=BENCHMARK_FIXTURE_PROVIDER,
        requested_start_date=BENCHMARK_FIXTURE_START_DATE,
        requested_end_date=requested_end_date,
        information_cutoff_date=cutoff,
        requested_scope=BENCHMARK_FIXTURE_SCOPE,
        endpoint="fixture_index_history",
        adapter_compatibility_version="benchmark-fixture-v1",
        adapter_version="benchmark-fixture-v1",
    )


def test_exact_close_formulas_and_minimum_windows(database) -> None:
    _, session_factory = database
    result = _benchmark(session_factory)
    with session_factory() as session:
        snapshot = BenchmarkRepository(session).load_snapshot(series_key=result.series_key)
    metrics, warnings = calculate_benchmark_metrics(
        snapshot,
        expected_sessions=BENCHMARK_FIXTURE_DATES,
    )
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
    assert first.latest_return_window.reason == "available"
    assert first.sma20_window.present_valid_session_count == 20
    assert first.sma60_window.present_valid_session_count == 60
    assert first.risk_window.present_valid_session_count == 21
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
        replace(snapshot, benchmark_index_daily=frame),
        expected_sessions=BENCHMARK_FIXTURE_DATES,
    )
    first = next(item for item in metrics if item.index_code == "000001")
    assert first.latest_return is not None
    assert first.sma20 is None
    assert first.sma60 is None
    assert first.realized_volatility_20 is None
    assert first.sma20_window.reason == "missing_expected_session"
    assert any("reason=missing_expected_session" in warning for warning in warnings)


def test_gap_before_all_required_ending_windows_does_not_invalidate_metrics(database) -> None:
    _, session_factory = database
    result = _benchmark(session_factory)
    with session_factory() as session:
        snapshot = BenchmarkRepository(session).load_snapshot(series_key=result.series_key)
    frame = snapshot.benchmark_index_daily.copy()
    frame = frame.loc[frame["trade_date"].ne(BENCHMARK_FIXTURE_DATES[0])]
    metrics, warnings = calculate_benchmark_metrics(
        replace(snapshot, benchmark_index_daily=frame),
        expected_sessions=BENCHMARK_FIXTURE_DATES,
    )
    assert all(metric.latest_return is not None for metric in metrics)
    assert all(metric.sma20 is not None for metric in metrics)
    assert all(metric.sma60 is not None for metric in metrics)
    assert all(metric.realized_volatility_20 is not None for metric in metrics)
    assert warnings == []


def test_equivalent_date_formats_cannot_bypass_duplicate_detection(database) -> None:
    _, session_factory = database
    result = _benchmark(session_factory)
    with session_factory() as session:
        snapshot = BenchmarkRepository(session).load_snapshot(series_key=result.series_key)
    duplicate = snapshot.benchmark_index_daily.iloc[[0]].copy()
    duplicate["trade_date"] = pd.to_datetime(duplicate["trade_date"]).dt.strftime(
        "%Y-%m-%d"
    )
    frame = pd.concat([snapshot.benchmark_index_daily, duplicate], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate natural keys"):
        calculate_benchmark_metrics(
            replace(snapshot, benchmark_index_daily=frame),
            expected_sessions=BENCHMARK_FIXTURE_DATES,
        )


def test_missing_immediately_previous_expected_session_breaks_latest_return(database) -> None:
    _, session_factory = database
    result = _benchmark(session_factory)
    with session_factory() as session:
        snapshot = BenchmarkRepository(session).load_snapshot(series_key=result.series_key)
    missing = BENCHMARK_FIXTURE_DATES[-2]
    frame = snapshot.benchmark_index_daily
    frame = frame.loc[
        ~(frame["index_code"].eq("000001") & frame["trade_date"].eq(missing))
    ]
    metrics, warnings = calculate_benchmark_metrics(
        replace(snapshot, benchmark_index_daily=frame),
        expected_sessions=BENCHMARK_FIXTURE_DATES,
    )
    first = next(metric for metric in metrics if metric.index_code == "000001")
    second = next(metric for metric in metrics if metric.index_code == "000300")
    assert first.latest_return is None
    assert first.latest_return_window.reason == "missing_expected_session"
    assert first.latest_return_window.missing_sessions == (missing,)
    assert second.latest_return is not None
    assert any("latest_return unavailable" in warning for warning in warnings)


def test_middle_gap_breaks_exact_sma20_and_risk_windows(database) -> None:
    _, session_factory = database
    result = _benchmark(session_factory)
    with session_factory() as session:
        snapshot = BenchmarkRepository(session).load_snapshot(series_key=result.series_key)
    missing = BENCHMARK_FIXTURE_DATES[-10]
    frame = snapshot.benchmark_index_daily
    frame = frame.loc[
        ~(frame["index_code"].eq("000001") & frame["trade_date"].eq(missing))
    ]
    metrics, _ = calculate_benchmark_metrics(
        replace(snapshot, benchmark_index_daily=frame),
        expected_sessions=BENCHMARK_FIXTURE_DATES,
    )
    first = next(metric for metric in metrics if metric.index_code == "000001")
    assert first.latest_return is not None
    assert first.sma20 is None
    assert first.realized_volatility_20 is None
    assert first.max_drawdown_20 is None
    assert first.sma20_window.missing_sessions == (missing,)
    assert first.risk_window.reason == "missing_expected_session"


def test_same_middle_gap_for_every_code_is_still_detected(database) -> None:
    _, session_factory = database
    result = _benchmark(session_factory)
    with session_factory() as session:
        snapshot = BenchmarkRepository(session).load_snapshot(series_key=result.series_key)
    missing = BENCHMARK_FIXTURE_DATES[-10]
    frame = snapshot.benchmark_index_daily.loc[
        snapshot.benchmark_index_daily["trade_date"].ne(missing)
    ]
    metrics, warnings = calculate_benchmark_metrics(
        replace(snapshot, benchmark_index_daily=frame),
        expected_sessions=BENCHMARK_FIXTURE_DATES,
    )
    assert all(metric.sma20 is None for metric in metrics)
    assert all(metric.risk_window.missing_sessions == (missing,) for metric in metrics)
    assert sum("sma20 unavailable" in warning for warning in warnings) == 2


def test_gap_only_inside_sma60_window_keeps_shorter_metrics(database) -> None:
    _, session_factory = database
    result = _benchmark(session_factory)
    with session_factory() as session:
        snapshot = BenchmarkRepository(session).load_snapshot(series_key=result.series_key)
    missing = BENCHMARK_FIXTURE_DATES[-30]
    frame = snapshot.benchmark_index_daily
    frame = frame.loc[
        ~(frame["index_code"].eq("000001") & frame["trade_date"].eq(missing))
    ]
    metrics, _ = calculate_benchmark_metrics(
        replace(snapshot, benchmark_index_daily=frame),
        expected_sessions=BENCHMARK_FIXTURE_DATES,
    )
    first = next(metric for metric in metrics if metric.index_code == "000001")
    assert first.latest_return is not None
    assert first.sma20 is not None
    assert first.realized_volatility_20 is not None
    assert first.max_drawdown_20 is not None
    assert first.sma60 is None
    assert first.sma60_window.missing_sessions == (missing,)


def test_invalid_close_inside_exact_window_has_stable_reason(database) -> None:
    _, session_factory = database
    result = _benchmark(session_factory)
    with session_factory() as session:
        snapshot = BenchmarkRepository(session).load_snapshot(series_key=result.series_key)
    invalid = BENCHMARK_FIXTURE_DATES[-10]
    frame = snapshot.benchmark_index_daily.copy()
    frame.loc[
        frame["index_code"].eq("000001") & frame["trade_date"].eq(invalid),
        "close",
    ] = np.inf
    metrics, warnings = calculate_benchmark_metrics(
        replace(snapshot, benchmark_index_daily=frame),
        expected_sessions=BENCHMARK_FIXTURE_DATES,
    )
    first = next(metric for metric in metrics if metric.index_code == "000001")
    assert first.sma20 is None
    assert first.realized_volatility_20 is None
    assert first.sma20_window.reason == "invalid_close"
    assert first.sma20_window.invalid_sessions == (invalid,)
    assert any("reason=invalid_close" in warning for warning in warnings)


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


@pytest.mark.parametrize("calendar_state", ["empty", "duplicate", "invalid_flag"])
def test_required_equity_calendar_fails_closed_when_unavailable_or_contradictory(
    database,
    calendar_state: str,
) -> None:
    _, session_factory = database
    equity_result = _equity(session_factory)
    benchmark_result = _benchmark(session_factory)
    with session_factory() as session:
        equity = MarketCockpitRepository(session).load_snapshot(
            series_key=equity_result.series_key
        )
        benchmark = BenchmarkRepository(session).load_snapshot(
            series_key=benchmark_result.series_key
        )
    if calendar_state == "empty":
        calendar = equity.trade_calendar.iloc[0:0].copy()
    elif calendar_state == "invalid_flag":
        calendar = equity.trade_calendar.copy()
        calendar["is_open"] = "true"
    else:
        calendar = pd.concat(
            [equity.trade_calendar, equity.trade_calendar.iloc[[0]]],
            ignore_index=True,
        )
    with pytest.raises(
        ValueError,
        match="no persisted open session|contradictory|invalid open flags",
    ):
        _expected_benchmark_sessions(
            equity_snapshot=replace(equity, trade_calendar=calendar),
            benchmark_information_cutoff=benchmark.information_cutoff_date,
            benchmark_requested_end=benchmark.requested_end_date,
            equity_effective_session=BENCHMARK_FIXTURE_DATES[-1],
            as_of_cutoff=None,
        )


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
    assert context["session_alignment_status"] == "aligned"
    assert context["cutoff_alignment_status"] == "aligned"
    assert context["requested_code_count"] == 2
    assert context["available_code_count"] == 2
    assert context["aligned_code_count"] == 2
    assert context["missing_codes"] == []
    assert context["expected_session_source"] == (
        "selected_equity_snapshot.persisted_trade_calendar"
    )
    assert context["expected_session_count"] == 65
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


def test_mixed_per_code_latest_sessions_are_partial(client) -> None:
    test_client, session_factory = client
    equity = _equity(session_factory)
    rows = build_benchmark_fixture().benchmark_index_daily
    rows = rows.loc[
        ~(rows["index_code"].eq("000300") & rows["trade_date"].eq(BENCHMARK_FIXTURE_DATES[-1]))
    ]
    benchmark = _benchmark_frame(session_factory, rows)
    response = test_client.get(
        "/market-cockpit/snapshot?series_key="
        + equity.series_key
        + "&benchmark_series_key="
        + benchmark.series_key
    )
    context = response.json()["benchmark_context"]
    assert response.status_code == 200
    assert context["alignment_status"] == "partial"
    assert context["session_alignment_status"] == "partial"
    assert context["available_code_count"] == 2
    assert context["aligned_code_count"] == 1
    assert context["missing_codes"] == []
    assert any("mixed latest eligible sessions" in warning for warning in context["warnings"])


def test_all_codes_on_one_earlier_session_are_different_session(client) -> None:
    test_client, session_factory = client
    equity = _equity(session_factory)
    rows = build_benchmark_fixture().benchmark_index_daily
    rows = rows.loc[rows["trade_date"].ne(BENCHMARK_FIXTURE_DATES[-1])]
    benchmark = _benchmark_frame(session_factory, rows)
    response = test_client.get(
        "/market-cockpit/snapshot?series_key="
        + equity.series_key
        + "&benchmark_series_key="
        + benchmark.series_key
    )
    assert response.status_code == 200
    context = response.json()["benchmark_context"]
    assert context["alignment_status"] == "different_session"
    assert context["session_alignment_status"] == "different_session"
    assert context["cutoff_alignment_status"] == "aligned"
    assert context["available_code_count"] == 2
    assert context["aligned_code_count"] == 0
    assert any("effective sessions differ" in warning for warning in context["warnings"])


def test_equal_sessions_with_different_cutoffs_are_not_aligned(client) -> None:
    test_client, session_factory = client
    equity = _equity(session_factory)
    benchmark = _benchmark(
        session_factory,
        revision="historical",
        cutoff=BENCHMARK_FIXTURE_HISTORICAL_CUTOFF,
    )
    response = test_client.get(
        "/market-cockpit/snapshot?series_key="
        + equity.series_key
        + "&benchmark_series_key="
        + benchmark.series_key
    )
    context = response.json()["benchmark_context"]
    assert response.status_code == 200
    assert context["session_alignment_status"] == "aligned"
    assert context["cutoff_alignment_status"] == "different_cutoff"
    assert context["alignment_status"] == "different_cutoff"
    assert context["aligned_code_count"] == 2
    assert any("information cutoffs differ" in warning for warning in context["warnings"])


def test_one_requested_code_without_eligible_row_is_partial(client) -> None:
    test_client, session_factory = client
    equity = _equity(
        session_factory,
        revision="historical",
        cutoff=BENCHMARK_FIXTURE_HISTORICAL_CUTOFF,
    )
    rows = build_benchmark_fixture(revision="historical").benchmark_index_daily
    code_one = rows.loc[rows["index_code"].eq("000001")].copy()
    code_two = rows.loc[
        rows["index_code"].eq("000300") & rows["trade_date"].eq(BENCHMARK_FIXTURE_DATES[-1])
    ].copy()
    code_two["trade_date"] = BENCHMARK_FIXTURE_HISTORICAL_CUTOFF
    rows = pd.concat([code_one, code_two], ignore_index=True)
    benchmark = _benchmark_frame(
        session_factory,
        rows,
        cutoff=BENCHMARK_FIXTURE_HISTORICAL_CUTOFF,
        requested_end_date=BENCHMARK_FIXTURE_HISTORICAL_CUTOFF,
    )
    response = test_client.get(
        "/market-cockpit/snapshot?series_key="
        + equity.series_key
        + "&benchmark_series_key="
        + benchmark.series_key
        + "&as_of_cutoff="
        + BENCHMARK_FIXTURE_HISTORICAL_CUTOFF
    )
    context = response.json()["benchmark_context"]
    assert response.status_code == 200
    assert context["alignment_status"] == "partial"
    assert context["available_code_count"] == 1
    assert context["aligned_code_count"] == 1
    assert context["missing_codes"] == ["000300"]
    assert any("no eligible row" in warning for warning in context["warnings"])


def test_all_requested_codes_outside_open_calendar_have_no_effective_session(
    client,
) -> None:
    test_client, session_factory = client
    equity = _equity(session_factory)
    rows = build_benchmark_fixture().benchmark_index_daily
    rows = rows.groupby("index_code", sort=True).head(1).copy()
    excluded_date = "20260110"
    rows["trade_date"] = excluded_date
    benchmark = _benchmark_frame(session_factory, rows)

    response = test_client.get(
        "/market-cockpit/snapshot?series_key="
        + equity.series_key
        + "&benchmark_series_key="
        + benchmark.series_key
    )
    assert response.status_code == 200
    context = response.json()["benchmark_context"]
    assert context["requested_code_count"] == 2
    assert context["available_code_count"] == 0
    assert context["aligned_code_count"] == 0
    assert context["missing_codes"] == ["000001", "000300"]
    assert context["session_alignment_status"] == "partial"
    assert context["alignment_status"] == "partial"
    assert context["cutoff_alignment_status"] == "aligned"
    assert context["effective_benchmark_session"] is None
    assert context["provenance"]["effective_benchmark_session"] is None
    for metric in context["metrics"]:
        assert metric["latest_close"] is None
        assert metric["latest_session"] is None
        assert metric["latest_return"] is None
        assert metric["sma20"] is None
        assert metric["sma60"] is None
        assert metric["realized_volatility_20"] is None
        assert metric["max_drawdown_20"] is None
        assert metric["available_session_count"] == 0
        assert metric["latest_return_window"]["reason"] == "insufficient_history"
        assert metric["risk_window"]["reason"] == "insufficient_history"
    assert any(
        "outside the selected equity open-session sequence" in warning
        and excluded_date in warning
        for warning in context["warnings"]
    )
    assert any(
        "No requested benchmark code has an eligible row" in warning
        for warning in context["warnings"]
    )
    assert excluded_date not in str(context["effective_benchmark_session"])

    script = (
        Path(__file__).resolve().parents[1]
        / "market_cockpit"
        / "static"
        / "market_cockpit.js"
    ).read_text(encoding="utf-8")
    assert 'return "Unavailable";' in script
    assert '["Effective benchmark session", provenance.effective_benchmark_session]' in script


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
    assert "exact consecutive 2/20/60/21-session windows" in page
    assert "Requested benchmark codes" in script
    assert "Cutoff alignment" in script
    assert "Missing exact codes" in script
    assert "formatBenchmarkWindow" in script
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
    assert payload["current"]["session_alignment_status"] == "aligned"
    assert payload["current"]["cutoff_alignment_status"] == "aligned"
    assert payload["current"]["requested_code_count"] == 2
    assert payload["current"]["available_code_count"] == 2
    assert payload["current"]["aligned_code_count"] == 2
    assert payload["current"]["missing_codes"] == []
    assert payload["current"]["expected_session_count"] == 65
    assert payload["read_only"] is True
    assert payload["network_access"] is False
