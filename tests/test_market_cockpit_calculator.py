from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from datasource.base import MarketDataBundle
from market_cockpit.calculator import calculate_market_cockpit
from market_cockpit.repository import PersistedMarketDataSnapshot
from market_cockpit.service import MarketCockpitService


def _snapshot(*, sessions: int = 65) -> PersistedMarketDataSnapshot:
    dates = pd.bdate_range("2026-01-05", periods=sessions).strftime("%Y%m%d").tolist()
    codes = ["000001", "000002", "000003"]
    stock_basic = pd.DataFrame(
        [
            {
                "stock_code": code,
                "stock_name": f"Stock {code}",
                "exchange": "SZ",
                "industry": "Test",
                "listing_date": "20200101",
                "status": "active",
                "source": "fixture",
            }
            for code in codes
        ]
    )
    close_series = {
        "000001": [100.0 + index for index in range(sessions)],
        "000002": [200.0 - index * 0.5 for index in range(sessions)],
        "000003": [50.0 for _ in range(sessions)],
    }
    if sessions >= 2:
        close_series["000001"][-1] = close_series["000001"][-2] * 1.10
        close_series["000002"][-1] = close_series["000002"][-2] * 0.90
    rows = []
    for code_index, code in enumerate(codes, start=1):
        for index, trade_date in enumerate(dates):
            close = close_series[code][index]
            volume = float(100 * code_index)
            amount = float(1000 * code_index)
            if index == sessions - 1:
                volume *= 2
                amount *= 2
            rows.append(
                {
                    "trade_date": trade_date,
                    "stock_code": code,
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                    "volume": volume,
                    "amount": amount,
                    "adjust_type": "qfq",
                    "source": "fixture",
                }
            )
    identity = {
        "series_schema": "aquantai.snapshot-series.v1",
        "provider": "fixture",
        "dataset": "market_data_bundle",
        "contract_version": "1.0",
        "datasets": ["daily_price", "stock_basic", "trade_calendar"],
        "stock_codes": codes,
        "requested_start_date": dates[0],
        "requested_end_date": dates[-1],
        "adjust_type": "qfq",
        "snapshot_mode": "complete",
        "stock_code_semantics": "exact",
        "compatibility_parameters": {},
    }
    return PersistedMarketDataSnapshot(
        series_key="a" * 64,
        ingestion_run_id=7,
        provider="fixture",
        contract_version="1.0",
        adapter_version="test-adapter",
        information_cutoff_date=dates[-1],
        requested_start_date=dates[0],
        requested_end_date=dates[-1],
        adjust_type="qfq",
        stock_codes=codes,
        series_identity=identity,
        stock_basic=stock_basic,
        daily_price=pd.DataFrame(rows),
        trade_calendar=pd.DataFrame(
            [
                {"trade_date": trade_date, "is_open": True, "source": "fixture"}
                for trade_date in dates
            ]
        ),
    )


def test_exact_latest_breadth_statistics_and_window_metrics() -> None:
    result = calculate_market_cockpit(_snapshot())
    latest = result.metrics.latest_session

    assert latest.advancing_count == 1
    assert latest.declining_count == 1
    assert latest.unchanged_count == 1
    assert latest.unavailable_count == 0
    assert latest.equal_weight_mean_return == pytest.approx(0.0, abs=1e-15)
    assert latest.median_return == 0.0
    assert latest.advance_ratio == 1 / 3
    assert latest.breadth_balance == 0.0
    assert latest.return_dispersion == pytest.approx(np.std([0.1, -0.1, 0.0], ddof=0))

    for window in (result.metrics.breadth_20, result.metrics.breadth_60):
        assert window.eligible_stock_count == 3
        assert window.above_sma_count == 1
        assert window.above_sma_ratio == 1 / 3
        assert window.new_high_count == 2
        assert window.new_low_count == 2


def test_participation_and_equal_weight_risk_use_documented_windows() -> None:
    snapshot = _snapshot()
    result = calculate_market_cockpit(snapshot)

    assert result.metrics.volume_participation.ratio_to_prior_20_session_median == 2.0
    assert result.metrics.volume_participation.eligible_stock_count == 3
    assert result.metrics.amount_participation.ratio_to_prior_20_session_median == 2.0
    assert result.metrics.amount_participation.eligible_stock_count == 3
    assert result.metrics.equal_weight_risk.eligible_return_sessions == 20
    pivot = snapshot.daily_price.pivot(
        index="trade_date", columns="stock_code", values="close"
    ).sort_index()
    expected_returns = pivot.pct_change(fill_method=None).mean(axis=1).tail(20).to_numpy()
    expected_volatility = np.std(expected_returns, ddof=1) * np.sqrt(252.0)
    wealth = np.concatenate(([1.0], np.cumprod(1.0 + expected_returns)))
    expected_drawdown = np.min(wealth / np.maximum.accumulate(wealth) - 1.0)
    assert result.metrics.equal_weight_risk.realized_volatility_20 == pytest.approx(
        expected_volatility
    )
    assert result.metrics.equal_weight_risk.max_drawdown_20 == pytest.approx(expected_drawdown)
    assert result.completeness_status == "ready"
    assert result.warnings == []


def test_future_price_trap_is_excluded_from_every_metric() -> None:
    baseline = _snapshot()
    baseline_result = calculate_market_cockpit(baseline)
    future_date = "20991231"
    future_rows = baseline.daily_price.tail(3).copy()
    future_rows.loc[:, "trade_date"] = future_date
    future_rows.loc[:, ["close", "open", "high", "low", "volume", "amount"]] = 999999.0
    trapped = replace(
        baseline,
        daily_price=pd.concat([baseline.daily_price, future_rows], ignore_index=True),
        trade_calendar=pd.concat(
            [
                baseline.trade_calendar,
                pd.DataFrame(
                    [{"trade_date": future_date, "is_open": True, "source": "fixture"}]
                ),
            ],
            ignore_index=True,
        ),
    )

    trapped_result = calculate_market_cockpit(trapped)

    assert trapped_result.metrics == baseline_result.metrics
    assert trapped_result.effective_as_of_session == baseline_result.effective_as_of_session
    assert any("after effective session" in warning for warning in trapped_result.warnings)


def test_insufficient_windows_return_null_not_fabricated_zero() -> None:
    result = calculate_market_cockpit(_snapshot(sessions=10))

    assert result.metrics.breadth_20.above_sma_ratio is None
    assert result.metrics.breadth_20.new_high_count is None
    assert result.metrics.breadth_60.new_low_count is None
    assert result.metrics.volume_participation.ratio_to_prior_20_session_median is None
    assert result.metrics.equal_weight_risk.realized_volatility_20 is None
    assert result.metrics.equal_weight_risk.max_drawdown_20 is None
    assert result.completeness_status == "partial"
    assert any("require 20 persisted" in warning for warning in result.warnings)


@pytest.mark.parametrize(
    ("sessions", "eligible_20", "eligible_60"),
    [(19, 0, 0), (20, 3, 0), (59, 3, 0), (60, 3, 3)],
)
def test_20_and_60_session_boundaries_are_exact(
    sessions: int, eligible_20: int, eligible_60: int
) -> None:
    result = calculate_market_cockpit(_snapshot(sessions=sessions))

    assert result.metrics.breadth_20.eligible_stock_count == eligible_20
    assert result.metrics.breadth_60.eligible_stock_count == eligible_60
    assert (result.metrics.breadth_20.above_sma_ratio is None) == (eligible_20 == 0)
    assert (result.metrics.breadth_60.above_sma_ratio is None) == (eligible_60 == 0)


def test_missing_latest_price_is_unavailable_and_partial() -> None:
    snapshot = _snapshot()
    latest_date = snapshot.requested_end_date
    prices = snapshot.daily_price.loc[
        ~(
            snapshot.daily_price["trade_date"].eq(latest_date)
            & snapshot.daily_price["stock_code"].eq("000003")
        )
    ].copy()

    result = calculate_market_cockpit(replace(snapshot, daily_price=prices))

    assert result.available_stock_count == 2
    assert result.metrics.latest_session.unavailable_count == 1
    assert result.completeness_status == "partial"
    assert any("000003" in warning for warning in result.warnings)


def test_duplicate_stock_session_is_excluded_without_arbitrary_selection() -> None:
    snapshot = _snapshot()
    duplicate = snapshot.daily_price.loc[
        snapshot.daily_price["trade_date"].eq(snapshot.requested_end_date)
        & snapshot.daily_price["stock_code"].eq("000001")
    ].copy()
    duplicate.loc[:, "close"] = 999999.0

    result = calculate_market_cockpit(
        replace(
            snapshot,
            daily_price=pd.concat([snapshot.daily_price, duplicate], ignore_index=True),
        )
    )

    assert result.available_stock_count == 2
    assert result.metrics.latest_session.unavailable_count == 1
    assert any("Duplicate stock-session prices were excluded" in warning for warning in result.warnings)


def test_incomplete_scope_and_non_active_stock_are_visible_warnings() -> None:
    snapshot = _snapshot()
    stock_basic = snapshot.stock_basic.loc[
        snapshot.stock_basic["stock_code"].ne("000003")
    ].copy()
    stock_basic.loc[stock_basic["stock_code"].eq("000002"), "status"] = "suspended"

    result = calculate_market_cockpit(replace(snapshot, stock_basic=stock_basic))

    assert result.completeness_status == "partial"
    assert any("do not exactly match" in warning for warning in result.warnings)
    assert any("non-active stock records" in warning for warning in result.warnings)


class _StaticRepository:
    def __init__(self, snapshot: PersistedMarketDataSnapshot) -> None:
        self.snapshot = snapshot

    def load_snapshot(self, **_kwargs) -> PersistedMarketDataSnapshot:
        return self.snapshot


def test_same_input_and_clock_produce_identical_service_output() -> None:
    clock = lambda: datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
    service = MarketCockpitService(_StaticRepository(_snapshot()), clock=clock)

    first = service.build_snapshot(series_key="a" * 64).to_dict()
    second = service.build_snapshot(series_key="a" * 64).to_dict()

    assert first == second
    assert first["scope_label"] == "selected universe"
    assert first["scope_label_zh"] == "选定股票范围"
    assert first["read_only"] is True
    assert len(first["unsupported_sections"]) == 5
