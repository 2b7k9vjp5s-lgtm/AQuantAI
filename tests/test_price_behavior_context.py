from __future__ import annotations

import json
from dataclasses import replace
from math import sqrt

import numpy as np
import pandas as pd
import pytest

from market_cockpit.calculator import calculate_market_cockpit
from market_cockpit.price_behavior_contracts import (
    PRICE_BEHAVIOR_IDENTIFIER_SAMPLE_LIMIT,
)
from market_cockpit.repository import PersistedMarketDataSnapshot
from tests.test_liquidity_context import _snapshot as build_snapshot


def _with_closes(
    snapshot: PersistedMarketDataSnapshot,
    stock_code: str,
    closes: list[float],
) -> PersistedMarketDataSnapshot:
    dates = snapshot.trade_calendar["trade_date"].astype(str).tolist()
    assert len(closes) == len(dates)
    prices = snapshot.daily_price.copy()
    for trade_date, close in zip(dates, closes):
        mask = prices["stock_code"].eq(stock_code) & prices["trade_date"].eq(trade_date)
        prices.loc[mask, "close"] = close
    return replace(snapshot, daily_price=prices)


def _geometric_closes(returns: list[float], *, initial: float = 100.0) -> list[float]:
    closes = [initial]
    for value in returns:
        closes.append(closes[-1] * (1.0 + value))
    return closes


def _context(snapshot: PersistedMarketDataSnapshot):
    return calculate_market_cockpit(snapshot).price_behavior_context


def test_exact_20_and_60_momentum_and_ddof1_volatility() -> None:
    snapshot = build_snapshot(stock_count=1, session_count=61)
    returns = [0.005, -0.003, 0.012, -0.004, 0.007] * 12
    snapshot = _with_closes(snapshot, "000001", _geometric_closes(returns))

    context = _context(snapshot)
    closes = _geometric_closes(returns)
    expected_20 = closes[-1] / closes[-21] - 1.0
    expected_60 = closes[-1] / closes[0] - 1.0
    expected_volatility = float(np.std(returns[-20:], ddof=1) * sqrt(252.0))

    assert context.return_20.median_return == pytest.approx(expected_20)
    assert context.return_20.positive_count == 1
    assert context.return_20.non_positive_count == 0
    assert context.return_20.positive_share == 1.0
    assert context.return_60.median_return == pytest.approx(expected_60)
    assert context.volatility_20.median_annualized_volatility == pytest.approx(
        expected_volatility
    )
    assert context.return_20.window.required_close_count == 21
    assert context.return_60.window.required_close_count == 61
    assert context.volatility_20.window.required_return_count == 20
    assert context.volatility_20.ddof == 1
    assert context.volatility_20.annualization_factor == 252
    assert context.calculation_status == "complete"


def test_zero_momentum_is_non_positive_and_volatility_ties_use_lower_or_equal() -> None:
    snapshot = build_snapshot(stock_count=2, session_count=61)
    snapshot = _with_closes(snapshot, "000001", [100.0] * 61)
    snapshot = _with_closes(snapshot, "000002", [100.0] * 61)

    context = _context(snapshot)
    quadrants = context.matched_cohort.quadrants

    assert context.return_20.positive_count == 0
    assert context.return_20.non_positive_count == 2
    assert context.return_20.positive_share == 0.0
    assert context.return_60.positive_count == 0
    assert context.matched_cohort.matched_median_annualized_volatility == 0.0
    assert quadrants.non_positive_momentum_lower_or_equal_volatility.count == 2
    assert quadrants.non_positive_momentum_higher_volatility.count == 0


def test_four_quadrants_are_exhaustive_and_shares_sum_to_one() -> None:
    snapshot = build_snapshot(stock_count=4, session_count=61)
    paths = {
        "000001": _geometric_closes([0.01] * 60),
        "000002": _geometric_closes([0.05, -0.03] * 30),
        "000003": _geometric_closes([0.0] * 60),
        "000004": _geometric_closes([0.03, -0.05] * 30),
    }
    for code, closes in paths.items():
        snapshot = _with_closes(snapshot, code, closes)

    matched = _context(snapshot).matched_cohort
    buckets = list(matched.quadrants.__dict__.values())

    assert matched.matched_cohort_count == 4
    assert [bucket.count for bucket in buckets] == [1, 1, 1, 1]
    assert sum(bucket.count for bucket in buckets) == matched.matched_cohort_count
    assert sum(bucket.share for bucket in buckets if bucket.share is not None) == pytest.approx(
        1.0
    )
    assert all(bucket.share == pytest.approx(0.25) for bucket in buckets)


def test_missing_intermediate_session_invalidates_complete_windows() -> None:
    snapshot = build_snapshot(stock_count=2, session_count=61)
    dates = snapshot.trade_calendar["trade_date"].astype(str).tolist()
    prices = snapshot.daily_price.loc[
        ~(
            snapshot.daily_price["stock_code"].eq("000002")
            & snapshot.daily_price["trade_date"].eq(dates[-10])
        )
    ].copy()

    context = _context(replace(snapshot, daily_price=prices))

    for metric in (context.return_20, context.return_60, context.volatility_20):
        assert metric.eligible_stock_count == 1
        assert metric.unavailable_stock_count == 1
        assert metric.diagnostics.issues[0].stock_code == "000002"
        assert metric.diagnostics.issues[0].reason == "missing_required_row"
        assert metric.diagnostics.issues[0].blocking_session == dates[-10]
    assert context.matched_cohort.matched_cohort_count == 1


def test_metric_cohorts_are_independent_for_a_gap_outside_the_20_session_window() -> None:
    snapshot = build_snapshot(stock_count=2, session_count=61)
    dates = snapshot.trade_calendar["trade_date"].astype(str).tolist()
    prices = snapshot.daily_price.loc[
        ~(
            snapshot.daily_price["stock_code"].eq("000002")
            & snapshot.daily_price["trade_date"].eq(dates[-40])
        )
    ].copy()

    context = _context(replace(snapshot, daily_price=prices))

    assert context.return_20.eligible_stock_count == 2
    assert context.volatility_20.eligible_stock_count == 2
    assert context.return_60.eligible_stock_count == 1
    assert context.return_60.unavailable_stock_count == 1
    assert context.matched_cohort.matched_cohort_count == 1


@pytest.mark.parametrize(
    ("mutation", "expected_reason"),
    [
        ("no_trade", "no_trade_required_row"),
        ("non_finite", "non_finite_close_required_row"),
        ("non_positive", "non_positive_close_required_row"),
        ("invalid_trade", "invalid_traded_record_required_row"),
    ],
)
def test_no_trade_and_invalid_required_closes_fail_closed(
    mutation: str,
    expected_reason: str,
) -> None:
    snapshot = build_snapshot(stock_count=1, session_count=61)
    prices = snapshot.daily_price.copy()
    affected = snapshot.trade_calendar.iloc[-5]["trade_date"]
    mask = prices["trade_date"].eq(affected) & prices["stock_code"].eq("000001")
    if mutation == "no_trade":
        prices.loc[mask, ["volume", "amount"]] = 0.0
    elif mutation == "non_finite":
        prices.loc[mask, "close"] = np.inf
    elif mutation == "non_positive":
        prices.loc[mask, "close"] = 0.0
    else:
        prices.loc[mask, "volume"] = -1.0

    context = _context(replace(snapshot, daily_price=prices))

    assert context.return_20.eligible_stock_count == 0
    assert context.return_60.eligible_stock_count == 0
    assert context.volatility_20.eligible_stock_count == 0
    assert context.return_20.diagnostics.issues[0].reason == expected_reason
    assert context.matched_cohort.reason == "empty_matched_cohort"
    assert context.matched_cohort.matched_median_annualized_volatility is None
    for bucket in context.matched_cohort.quadrants.__dict__.values():
        assert bucket.count == 0
        assert bucket.share is None


def test_insufficient_history_preserves_typed_unavailable_context() -> None:
    twenty_sessions = _context(build_snapshot(stock_count=2, session_count=20))
    twenty_one_sessions = _context(build_snapshot(stock_count=2, session_count=21))

    for metric in (
        twenty_sessions.return_20,
        twenty_sessions.return_60,
        twenty_sessions.volatility_20,
    ):
        assert metric.reason == "insufficient_open_session_history"
        assert metric.eligible_stock_count == 0
        assert metric.unavailable_stock_count == 2
        assert metric.diagnostics.issue_count == 2
    assert twenty_sessions.calculation_status == "unavailable"
    assert twenty_one_sessions.return_20.calculation_status == "complete"
    assert twenty_one_sessions.volatility_20.calculation_status == "complete"
    assert twenty_one_sessions.return_60.reason == "insufficient_open_session_history"
    assert twenty_one_sessions.calculation_status == "partial"


def test_empty_cohorts_emit_nulls_without_nan_or_infinity() -> None:
    snapshot = build_snapshot(stock_count=2, session_count=61)
    prices = snapshot.daily_price.copy()
    prices["close"] = np.nan

    context = _context(replace(snapshot, daily_price=prices))
    payload = json.dumps(context, default=lambda value: value.__dict__, allow_nan=False)

    assert context.return_20.median_return is None
    assert context.return_20.positive_share is None
    assert context.return_60.median_return is None
    assert context.volatility_20.median_annualized_volatility is None
    assert context.matched_cohort.matched_cohort_count == 0
    assert "NaN" not in payload
    assert "Infinity" not in payload


def test_non_finite_return_and_volatility_calculations_are_rejected() -> None:
    snapshot = build_snapshot(stock_count=1, session_count=61)
    closes = [float(np.nextafter(0.0, 1.0))] + [1.0] * 60
    snapshot = _with_closes(snapshot, "000001", closes)

    context = _context(snapshot)

    assert context.return_60.eligible_stock_count == 0
    assert context.return_60.diagnostics.issues[0].reason == "non_finite_calculation"
    assert context.return_60.median_return is None


def test_bounded_diagnostics_do_not_change_full_cohort_math() -> None:
    snapshot = build_snapshot(stock_count=25, session_count=61)
    dates = snapshot.trade_calendar["trade_date"].astype(str).tolist()
    unavailable_codes = [f"{index:06d}" for index in range(1, 16)]
    prices = snapshot.daily_price.loc[
        ~(
            snapshot.daily_price["stock_code"].isin(unavailable_codes)
            & snapshot.daily_price["trade_date"].eq(dates[-10])
        )
    ].copy()
    bounded = replace(snapshot, daily_price=prices)

    first = _context(bounded)
    second = _context(bounded)

    assert first == second
    for metric in (first.return_20, first.return_60, first.volatility_20):
        diagnostics = metric.diagnostics
        assert metric.eligible_stock_count == 10
        assert metric.unavailable_stock_count == 15
        assert diagnostics.issue_count == 15
        assert [issue.stock_code for issue in diagnostics.issues] == unavailable_codes[:10]
        assert diagnostics.issues_truncated is True
        assert diagnostics.issues_omitted_count == 5
    matched = first.matched_cohort
    assert matched.matched_cohort_count == 10
    assert matched.unavailable_stock_count == 15
    assert matched.unavailable_stock_codes == unavailable_codes[:10]
    assert matched.unavailable_stock_codes_truncated is True
    assert matched.unavailable_stock_codes_omitted_count == 5
    assert sum(
        bucket.count for bucket in matched.quadrants.__dict__.values()
    ) == matched.matched_cohort_count
    assert all(len(warning) < 600 for warning in first.warnings)
    assert "000015" not in " ".join(first.warnings)


def test_quadrant_member_samples_are_bounded_without_changing_counts() -> None:
    stock_count = 120
    snapshot = build_snapshot(stock_count=stock_count, session_count=61)
    context = _context(snapshot)
    bucket = (
        context.matched_cohort.quadrants.non_positive_momentum_lower_or_equal_volatility
    )

    assert context.matched_cohort.matched_cohort_count == stock_count
    assert bucket.count == stock_count
    assert bucket.share == 1.0
    assert len(bucket.stock_codes) == PRICE_BEHAVIOR_IDENTIFIER_SAMPLE_LIMIT
    assert bucket.stock_codes == [f"{index:06d}" for index in range(1, 11)]
    assert bucket.stock_codes_truncated is True
    assert bucket.stock_codes_omitted_count == 110


def test_source_exclusion_diagnostics_are_exact_bounded_and_sorted() -> None:
    snapshot = build_snapshot(stock_count=12, session_count=61)
    duplicate_rows = snapshot.daily_price.loc[
        snapshot.daily_price["trade_date"].eq(snapshot.requested_end_date)
    ].copy()
    malformed = replace(
        snapshot,
        daily_price=pd.concat([snapshot.daily_price, duplicate_rows], ignore_index=True),
    )

    context = _context(malformed)
    exclusion = context.diagnostics.source_exclusions[0]

    assert exclusion.reason == "duplicate_stock_session_price_rows"
    assert exclusion.excluded_row_count == 24
    assert exclusion.stock_code_count == 12
    assert exclusion.stock_codes == [f"{index:06d}" for index in range(1, 11)]
    assert exclusion.stock_codes_truncated is True
    assert exclusion.stock_codes_omitted_count == 2
    json.dumps(context, default=lambda value: value.__dict__, allow_nan=False)
