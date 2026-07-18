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
        ingestion_imported_at_utc="2026-07-18T04:00:00Z",
        ingestion_completed_at_utc="2026-07-18T04:00:01Z",
        collection_timestamp_utc=None,
        effective_information_cutoff_date=None,
        akshare_package_version=None,
        stock_basic_endpoint=None,
        daily_price_endpoint=None,
        trade_calendar_endpoint=None,
        frequency=None,
        adapter_compatibility_version=None,
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
    assert result.calculation_status == "ready"
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
    assert result.calculation_status == "partial"
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
    assert result.calculation_status == "partial"
    assert result.latest_data_diagnostics.stale_or_missing_latest_count == 1
    assert result.latest_data_diagnostics.no_trade_latest_count == 0
    issue = result.latest_data_diagnostics.latest_return_issues[0]
    assert issue.stock_code == "000003"
    assert issue.reason == "missing_effective_session_row"
    assert issue.blocking_session == latest_date
    assert issue.last_valid_traded_session == (
        snapshot.trade_calendar.iloc[-2]["trade_date"]
    )
    assert issue.open_session_gap == 1
    _assert_latest_return_diagnostic_invariant(result)
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

    assert result.calculation_status == "partial"
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
    assert first["calculation_status"] == "ready"
    assert first["scope_coverage_status"] == "unverified_selected_scope"
    assert first["completeness_status"] == "partial"
    assert "do not imply representative" in first["warnings"][-1]
    assert first["read_only"] is True
    assert len(first["unsupported_sections"]) == 5


def test_no_trade_latest_is_not_counted_as_unchanged_or_participating() -> None:
    snapshot = _snapshot()
    latest_date = snapshot.requested_end_date
    prices = snapshot.daily_price.copy()
    mask = prices["trade_date"].eq(latest_date) & prices["stock_code"].eq("000003")
    prices.loc[mask, ["volume", "amount"]] = 0.0

    result = calculate_market_cockpit(replace(snapshot, daily_price=prices))
    diagnostics = result.latest_data_diagnostics

    assert result.available_stock_count == 2
    assert result.metrics.latest_session.unchanged_count == 0
    assert result.metrics.latest_session.unavailable_count == 1
    assert result.metrics.volume_participation.eligible_stock_count == 2
    assert result.metrics.amount_participation.eligible_stock_count == 2
    assert result.metrics.breadth_20.eligible_stock_count == 2
    assert result.metrics.breadth_60.eligible_stock_count == 2
    assert result.metrics.equal_weight_risk.eligible_return_sessions == 19
    assert diagnostics.stale_or_missing_latest_count == 0
    assert diagnostics.no_trade_latest_count == 1
    assert diagnostics.latest_return_issues[0].reason == "no_trade_effective_session_row"
    assert diagnostics.latest_return_issues[0].blocking_session == latest_date
    assert diagnostics.latest_return_issues[0].open_session_gap == 1
    _assert_latest_return_diagnostic_invariant(result)
    assert any("potentially suspended or no-trade" in warning for warning in result.warnings)


def test_genuinely_unchanged_close_with_activity_remains_available() -> None:
    result = calculate_market_cockpit(_snapshot())

    assert result.metrics.latest_session.unchanged_count == 1
    assert result.metrics.latest_session.unavailable_count == 0
    assert result.latest_data_diagnostics.no_trade_latest_count == 0
    assert result.latest_data_diagnostics.latest_return_unavailable_count == 0
    assert result.latest_data_diagnostics.latest_return_issues == []
    _assert_latest_return_diagnostic_invariant(result)


def test_no_trade_inside_rolling_window_excludes_stock_consistently() -> None:
    snapshot = _snapshot()
    affected_date = snapshot.trade_calendar.iloc[-10]["trade_date"]
    prices = snapshot.daily_price.copy()
    mask = prices["trade_date"].eq(affected_date) & prices["stock_code"].eq("000002")
    prices.loc[mask, ["volume", "amount"]] = 0.0

    result = calculate_market_cockpit(replace(snapshot, daily_price=prices))

    assert result.metrics.breadth_20.eligible_stock_count == 2
    assert result.metrics.breadth_60.eligible_stock_count == 2
    assert result.metrics.volume_participation.eligible_stock_count == 2
    assert result.metrics.amount_participation.eligible_stock_count == 2
    assert result.metrics.equal_weight_risk.eligible_return_sessions == 18
    assert result.calculation_status == "partial"


def test_no_core_latest_returns_is_insufficient_and_details_are_sorted() -> None:
    snapshot = _snapshot()
    latest_date = snapshot.requested_end_date
    prices = snapshot.daily_price.copy()
    prices.loc[prices["trade_date"].eq(latest_date), ["volume", "amount"]] = 0.0

    result = calculate_market_cockpit(replace(snapshot, daily_price=prices))

    assert result.available_stock_count == 0
    assert result.calculation_status == "insufficient_data"
    assert result.latest_data_diagnostics.no_trade_latest_count == 3
    assert [item.stock_code for item in result.latest_data_diagnostics.latest_return_issues] == [
        "000001",
        "000002",
        "000003",
    ]
    _assert_latest_return_diagnostic_invariant(result)


def test_valid_current_row_with_missing_previous_row_has_structured_issue() -> None:
    snapshot = _snapshot()
    previous_date = snapshot.trade_calendar.iloc[-2]["trade_date"]
    prices = snapshot.daily_price.loc[
        ~(
            snapshot.daily_price["trade_date"].eq(previous_date)
            & snapshot.daily_price["stock_code"].eq("000003")
        )
    ].copy()

    result = calculate_market_cockpit(replace(snapshot, daily_price=prices))
    diagnostics = result.latest_data_diagnostics
    issue = diagnostics.latest_return_issues[0]

    assert diagnostics.stale_or_missing_latest_count == 0
    assert diagnostics.no_trade_latest_count == 0
    assert issue.reason == "missing_previous_session_row"
    assert issue.blocking_session == previous_date
    assert issue.last_valid_traded_session == snapshot.trade_calendar.iloc[-3]["trade_date"]
    assert issue.open_session_gap == 1
    _assert_latest_return_diagnostic_invariant(result)


def test_valid_current_row_with_no_trade_previous_row_has_structured_issue() -> None:
    snapshot = _snapshot()
    previous_date = snapshot.trade_calendar.iloc[-2]["trade_date"]
    prices = snapshot.daily_price.copy()
    mask = prices["trade_date"].eq(previous_date) & prices["stock_code"].eq("000003")
    prices.loc[mask, ["volume", "amount"]] = 0.0

    result = calculate_market_cockpit(replace(snapshot, daily_price=prices))
    issue = result.latest_data_diagnostics.latest_return_issues[0]

    assert result.latest_data_diagnostics.stale_or_missing_latest_count == 0
    assert result.latest_data_diagnostics.no_trade_latest_count == 0
    assert issue.reason == "no_trade_previous_session_row"
    assert issue.blocking_session == previous_date
    assert issue.last_valid_traded_session == snapshot.trade_calendar.iloc[-3]["trade_date"]
    assert issue.open_session_gap == 1
    _assert_latest_return_diagnostic_invariant(result)


@pytest.mark.parametrize(("field", "value"), [("volume", np.nan), ("close", np.inf)])
def test_valid_current_row_with_invalid_previous_row_has_structured_issue(
    field: str,
    value: float,
) -> None:
    snapshot = _snapshot()
    previous_date = snapshot.trade_calendar.iloc[-2]["trade_date"]
    prices = snapshot.daily_price.copy()
    mask = prices["trade_date"].eq(previous_date) & prices["stock_code"].eq("000003")
    prices.loc[mask, field] = value

    result = calculate_market_cockpit(replace(snapshot, daily_price=prices))
    issue = result.latest_data_diagnostics.latest_return_issues[0]

    assert issue.reason == "invalid_previous_session_row"
    assert issue.blocking_session == previous_date
    assert issue.last_valid_traded_session == snapshot.trade_calendar.iloc[-3]["trade_date"]
    assert issue.open_session_gap == 1
    _assert_latest_return_diagnostic_invariant(result)


def test_effective_session_issue_precedes_previous_session_issue() -> None:
    snapshot = _snapshot()
    effective_date = snapshot.trade_calendar.iloc[-1]["trade_date"]
    previous_date = snapshot.trade_calendar.iloc[-2]["trade_date"]
    prices = snapshot.daily_price.copy()
    previous_mask = prices["trade_date"].eq(previous_date) & prices["stock_code"].eq("000003")
    prices.loc[previous_mask, ["volume", "amount"]] = 0.0
    prices = prices.loc[
        ~(
            prices["trade_date"].eq(effective_date)
            & prices["stock_code"].eq("000003")
        )
    ].copy()

    result = calculate_market_cockpit(replace(snapshot, daily_price=prices))
    issue = result.latest_data_diagnostics.latest_return_issues[0]

    assert issue.reason == "missing_effective_session_row"
    assert issue.blocking_session == effective_date
    assert issue.last_valid_traded_session == snapshot.trade_calendar.iloc[-3]["trade_date"]
    assert issue.open_session_gap == 2
    _assert_latest_return_diagnostic_invariant(result)


def test_latest_return_issues_are_unique_and_stock_code_sorted() -> None:
    snapshot = _snapshot()
    effective_date = snapshot.trade_calendar.iloc[-1]["trade_date"]
    previous_date = snapshot.trade_calendar.iloc[-2]["trade_date"]
    prices = snapshot.daily_price.copy()
    prices.loc[
        prices["trade_date"].eq(effective_date)
        & prices["stock_code"].eq("000001"),
        ["volume", "amount"],
    ] = 0.0
    prices = prices.loc[
        ~(
            prices["trade_date"].eq(previous_date)
            & prices["stock_code"].eq("000002")
        )
    ].copy()
    prices.loc[
        prices["trade_date"].eq(effective_date)
        & prices["stock_code"].eq("000003"),
        "close",
    ] = np.nan

    result = calculate_market_cockpit(replace(snapshot, daily_price=prices))
    issues = result.latest_data_diagnostics.latest_return_issues

    assert [issue.stock_code for issue in issues] == ["000001", "000002", "000003"]
    assert [issue.reason for issue in issues] == [
        "no_trade_effective_session_row",
        "missing_previous_session_row",
        "invalid_effective_session_row",
    ]
    _assert_latest_return_diagnostic_invariant(result)


def _assert_latest_return_diagnostic_invariant(result) -> None:
    diagnostics = result.latest_data_diagnostics
    unavailable = result.metrics.latest_session.unavailable_count
    assert diagnostics.latest_return_unavailable_count == unavailable
    assert len(diagnostics.latest_return_issues) == unavailable
    codes = [issue.stock_code for issue in diagnostics.latest_return_issues]
    assert codes == sorted(set(codes))
