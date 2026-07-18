from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from market_cockpit.fixtures import (
    COCKPIT_FIXTURE_ADJUST_TYPE,
    COCKPIT_FIXTURE_CURRENT_CUTOFF,
    COCKPIT_FIXTURE_DATES,
    COCKPIT_FIXTURE_END_DATE,
    COCKPIT_FIXTURE_PROVIDER,
    COCKPIT_FIXTURE_START_DATE,
    build_market_cockpit_fixture,
)
from market_cockpit.repository import PersistedMarketDataSnapshot
from market_cockpit.sector_calculator import (
    SectorCalculationError,
    calculate_sector_metrics,
)
from market_cockpit.sector_fixtures import (
    SECTOR_FIXTURE_CODES,
    SECTOR_FIXTURE_CURRENT_CUTOFF,
    SECTOR_FIXTURE_DATES,
    SECTOR_FIXTURE_END_DATE,
    SECTOR_FIXTURE_START_DATE,
    build_sector_fixture,
)
from market_cockpit.sector_repository import PersistedSectorSnapshot
from market_cockpit.service import MarketCockpitService


def _sector_snapshot(**changes) -> PersistedSectorSnapshot:
    fixture = build_sector_fixture()
    values = dict(
        series_key="b" * 64,
        ingestion_run_id=20,
        provider="fixture",
        definition_contract_version="1.0",
        daily_contract_version="1.0",
        adapter_version="sector-fixture-v1",
        adapter_compatibility_version="sector-fixture-v1",
        information_cutoff_date=SECTOR_FIXTURE_CURRENT_CUTOFF,
        requested_start_date=SECTOR_FIXTURE_START_DATE,
        requested_end_date=SECTOR_FIXTURE_END_DATE,
        sector_codes=SECTOR_FIXTURE_CODES,
        taxonomy_endpoint="fixture_sector_taxonomy",
        history_endpoint="fixture_sector_history",
        classification_system="eastmoney_industry_board",
        classification_level=None,
        frequency="daily",
        adjust_type="",
        ingestion_imported_at_utc="2026-04-05T12:00:00Z",
        ingestion_completed_at_utc="2026-04-05T12:00:01Z",
        collection_timestamp_utc="2026-04-05T11:59:00Z",
        effective_information_cutoff_date=SECTOR_FIXTURE_CURRENT_CUTOFF,
        akshare_package_version="1.18.64",
        network_mode="offline-fixture",
        timeout_seconds=20.0,
        max_retries=2,
        series_identity={},
        sector_definition=fixture.sector_definition,
        sector_daily=fixture.sector_daily,
    )
    values.update(changes)
    return PersistedSectorSnapshot(**values)


def _equity_snapshot() -> PersistedMarketDataSnapshot:
    fixture = build_market_cockpit_fixture()
    return PersistedMarketDataSnapshot(
        series_key="a" * 64,
        ingestion_run_id=10,
        provider=COCKPIT_FIXTURE_PROVIDER,
        contract_version="1.0",
        adapter_version="fixture-v1",
        information_cutoff_date=COCKPIT_FIXTURE_CURRENT_CUTOFF,
        requested_start_date=COCKPIT_FIXTURE_START_DATE,
        requested_end_date=COCKPIT_FIXTURE_END_DATE,
        adjust_type=COCKPIT_FIXTURE_ADJUST_TYPE,
        ingestion_imported_at_utc="2026-04-05T12:00:00Z",
        ingestion_completed_at_utc="2026-04-05T12:00:01Z",
        collection_timestamp_utc=None,
        effective_information_cutoff_date=COCKPIT_FIXTURE_CURRENT_CUTOFF,
        akshare_package_version=None,
        stock_basic_endpoint="fixture_stock_basic",
        daily_price_endpoint="fixture_daily_price",
        trade_calendar_endpoint="fixture_trade_calendar",
        frequency="daily",
        adapter_compatibility_version="fixture-v1",
        stock_codes=sorted(fixture.stock_basic["stock_code"].tolist()),
        series_identity={},
        stock_basic=fixture.stock_basic,
        daily_price=fixture.daily_price,
        trade_calendar=fixture.trade_calendar,
    )


class _EquityRepository:
    def __init__(self, snapshot: PersistedMarketDataSnapshot) -> None:
        self.snapshot = snapshot

    def load_snapshot(self, **_kwargs) -> PersistedMarketDataSnapshot:
        return self.snapshot


class _SectorRepository:
    def __init__(self, snapshot: PersistedSectorSnapshot) -> None:
        self.snapshot = snapshot

    def load_snapshot(self, **_kwargs) -> PersistedSectorSnapshot:
        return self.snapshot


def _service_snapshot(sector: PersistedSectorSnapshot | None = None):
    return MarketCockpitService(
        _EquityRepository(_equity_snapshot()),
        sector_repository=_SectorRepository(sector or _sector_snapshot()),
        clock=lambda: datetime(2026, 4, 5, 13, tzinfo=timezone.utc),
    ).build_snapshot(
        series_key="a" * 64,
        sector_series_key="b" * 64,
    )


def test_exact_sector_formulas_and_window_diagnostics() -> None:
    snapshot = _sector_snapshot()
    metrics, warnings = calculate_sector_metrics(
        snapshot, expected_sessions=SECTOR_FIXTURE_DATES
    )
    first = metrics[0]
    frame = snapshot.sector_daily.loc[
        snapshot.sector_daily["sector_code"].eq(first.sector_code)
    ].sort_values("trade_date")
    closes = frame["close"].astype(float).to_numpy()
    returns = closes[-21:][1:] / closes[-21:][:-1] - 1.0
    wealth = np.concatenate(([1.0], np.cumprod(1.0 + returns)))
    assert first.latest_return == pytest.approx(closes[-1] / closes[-2] - 1)
    assert first.return_5 == pytest.approx(closes[-1] / closes[-6] - 1)
    assert first.return_20 == pytest.approx(closes[-1] / closes[-21] - 1)
    assert first.sma20 == pytest.approx(closes[-20:].mean())
    assert first.sma20_distance == pytest.approx(closes[-1] / closes[-20:].mean() - 1)
    assert first.realized_volatility_20 == pytest.approx(returns.std(ddof=1) * np.sqrt(252))
    assert first.max_drawdown_20 == pytest.approx(
        np.min(wealth / np.maximum.accumulate(wealth) - 1)
    )
    assert first.latest_return_window.reason == "available"
    assert first.return_5_window.required_session_count == 6
    assert first.return_20_window.required_session_count == 21
    assert warnings == []


def test_middle_gap_invalidates_only_affected_exact_windows() -> None:
    snapshot = _sector_snapshot()
    daily = snapshot.sector_daily.copy()
    mask = daily["sector_code"].eq("BK0001") & daily["trade_date"].eq(SECTOR_FIXTURE_DATES[-10])
    daily = daily.loc[~mask].copy()
    metrics, _ = calculate_sector_metrics(
        replace(snapshot, sector_daily=daily), expected_sessions=SECTOR_FIXTURE_DATES
    )
    first = metrics[0]
    assert first.latest_return is not None
    assert first.return_5 is not None
    assert first.return_20 is None
    assert first.sma20 is None
    assert first.realized_volatility_20 is None
    assert first.return_20_window.reason == "missing_expected_session"
    assert first.return_20_window.missing_sessions == (SECTOR_FIXTURE_DATES[-10],)


@pytest.mark.parametrize("mutation", ["invalid", "duplicate"])
def test_invalid_or_duplicate_session_returns_null_with_diagnostic(mutation: str) -> None:
    snapshot = _sector_snapshot()
    daily = snapshot.sector_daily.copy()
    mask = daily["sector_code"].eq("BK0001") & daily["trade_date"].eq(SECTOR_FIXTURE_DATES[-2])
    if mutation == "invalid":
        daily.loc[mask, "close"] = float("nan")
    else:
        daily = pd.concat([daily, daily.loc[mask]], ignore_index=True)
    metrics, _ = calculate_sector_metrics(
        replace(snapshot, sector_daily=daily), expected_sessions=SECTOR_FIXTURE_DATES
    )
    first = metrics[0]
    assert first.latest_return is None
    assert first.latest_return_window.reason == "invalid_close"
    assert first.latest_return_window.invalid_sessions == (SECTOR_FIXTURE_DATES[-2],)


def test_insufficient_history_never_shortens_long_windows() -> None:
    metrics, _ = calculate_sector_metrics(
        _sector_snapshot(), expected_sessions=SECTOR_FIXTURE_DATES[:10]
    )
    first = metrics[0]
    assert first.latest_return is not None
    assert first.return_5 is not None
    assert first.return_20 is None
    assert first.sma20 is None
    assert first.realized_volatility_20 is None
    assert first.return_20_window.reason == "insufficient_history"


def test_future_price_trap_is_excluded_and_never_becomes_effective_session() -> None:
    snapshot = _sector_snapshot()
    future = snapshot.sector_daily.iloc[[0]].copy()
    future["trade_date"] = "20990101"
    future["close"] = 999999.0
    daily = pd.concat([snapshot.sector_daily, future], ignore_index=True)
    metrics, warnings = calculate_sector_metrics(
        replace(snapshot, sector_daily=daily), expected_sessions=SECTOR_FIXTURE_DATES
    )
    assert metrics[0].latest_session == SECTOR_FIXTURE_END_DATE
    assert metrics[0].latest_close != 999999.0
    assert any("outside the selected equity open-session" in warning for warning in warnings)


def test_service_alignment_provenance_cross_section_and_determinism() -> None:
    first = _service_snapshot().to_dict()
    second = _service_snapshot().to_dict()
    assert first == second
    context = first["sector_context"]
    assert context["alignment_status"] == "aligned"
    assert context["coverage_status"] == "complete"
    assert context["requested_sector_count"] == 2
    assert context["available_sector_count"] == 2
    assert context["aligned_sector_count"] == 2
    assert context["missing_sector_codes"] == []
    assert context["cross_section"]["valid_latest_return_count"] == 2
    assert context["cross_section"]["positive_latest_return_count"] == 1
    assert context["cross_section"]["positive_latest_return_share"] == pytest.approx(0.5)
    assert context["provenance"]["taxonomy_endpoint"] == "fixture_sector_taxonomy"
    assert context["provenance"]["effective_sector_session"] == SECTOR_FIXTURE_END_DATE
    assert context["label"] == "provider-attributed selected-sector market context"
    assert context["read_only"] is True


def test_top_bottom_lists_are_bounded_and_tie_break_by_stable_code() -> None:
    snapshot = _sector_snapshot()
    daily = snapshot.sector_daily.copy()
    for code in SECTOR_FIXTURE_CODES:
        code_rows = daily["sector_code"].eq(code)
        previous_index = daily.loc[code_rows].sort_values("trade_date").index[-2]
        latest_index = daily.loc[code_rows].sort_values("trade_date").index[-1]
        daily.loc[latest_index, "close"] = daily.loc[previous_index, "close"] * 1.01
        daily.loc[latest_index, "high"] = daily.loc[latest_index, "close"] + 1
        daily.loc[latest_index, "open"] = daily.loc[latest_index, "close"]
        daily.loc[latest_index, "low"] = daily.loc[latest_index, "close"] - 1
    context = _service_snapshot(replace(snapshot, sector_daily=daily)).sector_context
    assert context is not None
    assert [item.sector_code for item in context.cross_section.top_latest_return] == [
        "BK0001", "BK0002"
    ]
    assert [item.sector_code for item in context.cross_section.bottom_latest_return] == [
        "BK0001", "BK0002"
    ]


def test_all_ineligible_sectors_have_null_effective_session_and_partial_status() -> None:
    snapshot = _sector_snapshot()
    daily = snapshot.sector_daily.copy()
    daily["trade_date"] = pd.date_range("2099-01-01", periods=len(daily)).strftime("%Y%m%d")
    context = _service_snapshot(replace(snapshot, sector_daily=daily)).sector_context
    assert context is not None
    assert context.effective_sector_session is None
    assert context.provenance.effective_sector_session is None
    assert context.alignment_status == "partial"
    assert context.coverage_status == "partial"
    assert context.session_alignment_status == "partial"
    assert context.available_sector_count == 0
    assert context.aligned_sector_count == 0
    assert context.missing_sector_codes == SECTOR_FIXTURE_CODES
    assert all(metric.latest_close is None for metric in context.metrics)


def test_missing_mixed_and_shared_earlier_sessions_have_distinct_alignment() -> None:
    snapshot = _sector_snapshot()
    latest = SECTOR_FIXTURE_DATES[-1]

    mixed_daily = snapshot.sector_daily.loc[
        ~(snapshot.sector_daily["sector_code"].eq("BK0002") & snapshot.sector_daily["trade_date"].eq(latest))
    ].copy()
    mixed = _service_snapshot(replace(snapshot, sector_daily=mixed_daily)).sector_context
    assert mixed is not None
    assert mixed.coverage_status == "complete"
    assert mixed.session_alignment_status == "partial"
    assert mixed.alignment_status == "partial"

    earlier_daily = snapshot.sector_daily.loc[
        ~snapshot.sector_daily["trade_date"].eq(latest)
    ].copy()
    earlier = _service_snapshot(replace(snapshot, sector_daily=earlier_daily)).sector_context
    assert earlier is not None
    assert earlier.coverage_status == "complete"
    assert earlier.session_alignment_status == "different_session"
    assert earlier.alignment_status == "different_session"
    assert earlier.effective_sector_session == SECTOR_FIXTURE_DATES[-2]

    missing_daily = snapshot.sector_daily.loc[
        ~snapshot.sector_daily["sector_code"].eq("BK0002")
    ].copy()
    missing = _service_snapshot(replace(snapshot, sector_daily=missing_daily)).sector_context
    assert missing is not None
    assert missing.coverage_status == "partial"
    assert missing.missing_sector_codes == ["BK0002"]
    assert missing.alignment_status == "partial"


def test_same_session_different_cutoff_is_not_reported_aligned() -> None:
    context = _service_snapshot(
        replace(_sector_snapshot(), information_cutoff_date="20260404")
    ).sector_context
    assert context is not None
    assert context.effective_sector_session == COCKPIT_FIXTURE_END_DATE
    assert context.session_alignment_status == "aligned"
    assert context.cutoff_alignment_status == "different_cutoff"
    assert context.alignment_status == "different_cutoff"


def test_expected_session_sequence_must_be_unique_and_ordered() -> None:
    with pytest.raises(SectorCalculationError, match="unique and strictly ordered"):
        calculate_sector_metrics(
            _sector_snapshot(), expected_sessions=["20260402", "20260401"]
        )
    with pytest.raises(SectorCalculationError, match="unique and strictly ordered"):
        calculate_sector_metrics(
            _sector_snapshot(), expected_sessions=["20260401", "20260401"]
        )
