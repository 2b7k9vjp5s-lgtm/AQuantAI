from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from market_cockpit.calculator import calculate_market_cockpit
from market_cockpit.liquidity_contracts import LIQUIDITY_IDENTIFIER_SAMPLE_LIMIT
from market_cockpit.repository import PersistedMarketDataSnapshot
from scripts.demo_liquidity_context import build_liquidity_context_demo


def _snapshot(
    *,
    stock_count: int = 3,
    session_count: int = 25,
) -> PersistedMarketDataSnapshot:
    dates = pd.bdate_range("2026-01-05", periods=session_count).strftime("%Y%m%d").tolist()
    codes = [f"{index:06d}" for index in range(1, stock_count + 1)]
    stock_basic = pd.DataFrame(
        [
            {
                "stock_code": code,
                "stock_name": f"Stock {code}",
                "exchange": "SZ",
                "industry": "Fixture",
                "listing_date": "20200101",
                "status": "active",
                "source": "fixture",
            }
            for code in codes
        ]
    )
    rows: list[dict] = []
    for code_index, code in enumerate(codes, start=1):
        for trade_date in dates:
            amount = float(code_index * 10)
            rows.append(
                {
                    "trade_date": trade_date,
                    "stock_code": code,
                    "open": 100.0,
                    "high": 100.0,
                    "low": 100.0,
                    "close": 100.0,
                    "volume": 100.0,
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
        ingestion_run_id=1,
        provider="fixture",
        contract_version="1.0",
        adapter_version="fixture-v1",
        information_cutoff_date=dates[-1],
        requested_start_date=dates[0],
        requested_end_date=dates[-1],
        adjust_type="qfq",
        ingestion_imported_at_utc="2026-07-18T00:00:00Z",
        ingestion_completed_at_utc="2026-07-18T00:00:01Z",
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


def _set_amount(
    snapshot: PersistedMarketDataSnapshot,
    *,
    stock_code: str,
    trade_date: str,
    amount: float,
) -> PersistedMarketDataSnapshot:
    prices = snapshot.daily_price.copy()
    mask = prices["stock_code"].eq(stock_code) & prices["trade_date"].eq(trade_date)
    prices.loc[mask, "amount"] = amount
    return replace(snapshot, daily_price=prices)


def test_latest_distribution_top5_and_top_decile_are_exact() -> None:
    snapshot = _snapshot(stock_count=12)
    result = calculate_market_cockpit(snapshot).liquidity_context

    assert result.latest_total_amount == 780.0
    assert result.latest_median_amount == 65.0
    assert result.top5_member_count == 5
    assert result.top5_stock_codes == ["000012", "000011", "000010", "000009", "000008"]
    assert result.top5_concentration_share == pytest.approx(500 / 780)
    assert result.top_decile_member_count == 2
    assert result.top_decile_stock_codes == ["000011", "000012"]
    assert result.top_decile_stock_codes_truncated is False
    assert result.top_decile_stock_codes_omitted_count == 0
    assert result.top_decile_concentration_share == pytest.approx(230 / 780)
    assert result.calculation_status == "complete"


def test_concentration_ties_use_stock_code_ascending() -> None:
    snapshot = _snapshot(stock_count=12)
    latest = snapshot.requested_end_date
    prices = snapshot.daily_price.copy()
    prices.loc[prices["trade_date"].eq(latest), "amount"] = 100.0

    result = calculate_market_cockpit(replace(snapshot, daily_price=prices)).liquidity_context

    assert result.top5_stock_codes == ["000001", "000002", "000003", "000004", "000005"]
    assert result.top_decile_stock_codes == ["000001", "000002"]


def test_small_universe_top_decile_uses_one_member() -> None:
    result = calculate_market_cockpit(_snapshot(stock_count=3)).liquidity_context

    assert result.top_decile_member_count == 1
    assert result.top_decile_stock_codes == ["000003"]
    assert result.top_decile_concentration_share == pytest.approx(30 / 60)


def test_exact_matched_cohort_activity_and_strict_above_baseline() -> None:
    snapshot = _snapshot(stock_count=2, session_count=21)
    latest = snapshot.requested_end_date
    snapshot = _set_amount(snapshot, stock_code="000001", trade_date=latest, amount=20.0)

    liquidity = calculate_market_cockpit(snapshot).liquidity_context

    for window in (liquidity.activity_5, liquidity.activity_20):
        assert window.matched_cohort_count == 2
        assert window.latest_matched_total_amount == 40.0
        assert window.baseline_total_amount == 30.0
        assert window.activity_ratio == pytest.approx(4 / 3)
        assert window.calculation_status == "complete"
    assert liquidity.latest_above_20_session_baseline_count == 1
    assert liquidity.latest_above_20_session_baseline_share == 0.5


@pytest.mark.parametrize("invalid_amount", [np.nan, np.inf, -1.0, 0.0])
def test_one_invalid_history_row_excludes_stock_from_entire_matched_cohort(
    invalid_amount: float,
) -> None:
    snapshot = _snapshot(stock_count=2, session_count=21)
    affected = snapshot.trade_calendar.iloc[-3]["trade_date"]
    snapshot = _set_amount(
        snapshot,
        stock_code="000002",
        trade_date=affected,
        amount=invalid_amount,
    )

    liquidity = calculate_market_cockpit(snapshot).liquidity_context

    for window in (liquidity.activity_5, liquidity.activity_20):
        assert window.matched_cohort_count == 1
        assert window.unavailable_stock_codes == ["000002"]
        assert window.calculation_status == "partial"
        assert window.activity_ratio == 1.0


def test_missing_history_row_excludes_stock_from_every_affected_window() -> None:
    snapshot = _snapshot(stock_count=2, session_count=21)
    affected = snapshot.trade_calendar.iloc[-3]["trade_date"]
    prices = snapshot.daily_price.loc[
        ~(
            snapshot.daily_price["stock_code"].eq("000002")
            & snapshot.daily_price["trade_date"].eq(affected)
        )
    ].copy()

    liquidity = calculate_market_cockpit(
        replace(snapshot, daily_price=prices)
    ).liquidity_context

    assert liquidity.activity_5.unavailable_stock_codes == ["000002"]
    assert liquidity.activity_20.unavailable_stock_codes == ["000002"]
    assert liquidity.latest_above_20_session_baseline_count == 0
    assert liquidity.latest_above_20_session_baseline_share == 0.0


@pytest.mark.parametrize(
    ("session_count", "window_name"),
    [(5, "activity_5"), (20, "activity_20")],
)
def test_insufficient_exact_history_returns_null_metrics(
    session_count: int,
    window_name: str,
) -> None:
    liquidity = calculate_market_cockpit(
        _snapshot(session_count=session_count)
    ).liquidity_context
    window = getattr(liquidity, window_name)

    assert window.matched_cohort_count == 0
    assert window.baseline_total_amount is None
    assert window.activity_ratio is None
    assert window.reason == "insufficient_open_session_history"
    assert window.calculation_status == "unavailable"


@pytest.mark.parametrize(
    ("mutation", "expected_reason"),
    [
        ("missing", "missing_latest_row"),
        ("no_trade", "no_trade_latest_row"),
        ("zero_amount", "zero_amount_latest_row"),
        ("negative", "invalid_amount_latest_row"),
        ("nan", "invalid_amount_latest_row"),
        ("infinite", "invalid_amount_latest_row"),
        ("invalid_close", "invalid_traded_record_latest_row"),
    ],
)
def test_latest_unavailable_reasons_are_explicit(
    mutation: str,
    expected_reason: str,
) -> None:
    snapshot = _snapshot(stock_count=1)
    latest = snapshot.requested_end_date
    prices = snapshot.daily_price.copy()
    mask = prices["trade_date"].eq(latest)
    if mutation == "missing":
        prices = prices.loc[~mask].copy()
    elif mutation == "no_trade":
        prices.loc[mask, ["volume", "amount"]] = 0.0
    elif mutation == "zero_amount":
        prices.loc[mask, "amount"] = 0.0
    elif mutation == "negative":
        prices.loc[mask, "amount"] = -1.0
    elif mutation == "nan":
        prices.loc[mask, "amount"] = np.nan
    elif mutation == "infinite":
        prices.loc[mask, "amount"] = np.inf
    else:
        prices.loc[mask, "close"] = np.inf

    liquidity = calculate_market_cockpit(
        replace(snapshot, daily_price=prices)
    ).liquidity_context

    assert liquidity.latest_eligible_count == 0
    assert liquidity.latest_total_amount is None
    assert liquidity.latest_median_amount is None
    assert liquidity.top5_concentration_share is None
    assert liquidity.top_decile_concentration_share is None
    assert liquidity.calculation_status == "unavailable"
    assert liquidity.diagnostics.latest_issues[0].reason == expected_reason


def test_partial_latest_coverage_uses_only_eligible_denominators() -> None:
    snapshot = _snapshot(stock_count=3)
    latest = snapshot.requested_end_date
    snapshot = _set_amount(snapshot, stock_code="000003", trade_date=latest, amount=0.0)

    liquidity = calculate_market_cockpit(snapshot).liquidity_context

    assert liquidity.latest_eligible_count == 2
    assert liquidity.latest_unavailable_count == 1
    assert liquidity.latest_total_amount == 30.0
    assert liquidity.latest_median_amount == 15.0
    assert liquidity.top5_member_count == 2
    assert liquidity.top5_concentration_share == 1.0
    assert liquidity.top_decile_member_count == 1
    assert liquidity.top_decile_concentration_share == pytest.approx(20 / 30)


def test_all_latest_unavailable_is_not_fabricated_zero() -> None:
    snapshot = _snapshot()
    prices = snapshot.daily_price.copy()
    prices.loc[prices["trade_date"].eq(snapshot.requested_end_date), ["volume", "amount"]] = 0.0

    liquidity = calculate_market_cockpit(
        replace(snapshot, daily_price=prices)
    ).liquidity_context

    assert liquidity.latest_eligible_count == 0
    assert liquidity.latest_unavailable_count == 3
    assert liquidity.latest_total_amount is None
    assert liquidity.latest_above_20_session_baseline_share is None
    assert [issue.stock_code for issue in liquidity.diagnostics.latest_issues] == [
        "000001",
        "000002",
        "000003",
    ]


def test_accepted_equity_filter_exclusions_are_structured_and_bounded() -> None:
    snapshot = _snapshot()
    latest = snapshot.requested_end_date
    original = snapshot.daily_price.loc[
        snapshot.daily_price["trade_date"].eq(latest)
        & snapshot.daily_price["stock_code"].eq("000001")
    ].iloc[0].to_dict()
    rows = [
        {**original, "trade_date": "20991231"},
        {**original, "trade_date": "20260110"},
        {**original, "stock_code": "999999"},
        {**original, "stock_code": "000002", "adjust_type": ""},
        dict(original),
    ]
    prices = pd.concat([snapshot.daily_price, pd.DataFrame(rows)], ignore_index=True)

    liquidity = calculate_market_cockpit(
        replace(snapshot, daily_price=prices)
    ).liquidity_context
    exclusions = liquidity.diagnostics.source_exclusions

    assert [item.reason for item in exclusions] == [
        "future_price_rows",
        "out_of_calendar_price_rows",
        "wrong_scope_price_rows",
        "wrong_adjustment_price_rows",
        "duplicate_stock_session_price_rows",
    ]
    assert all(item.excluded_row_count > 0 for item in exclusions)
    assert all(len(item.identifiers) <= LIQUIDITY_IDENTIFIER_SAMPLE_LIMIT for item in exclusions)
    assert all(item.identifier_count >= len(item.identifiers) for item in exclusions)
    assert all(
        item.identifiers_omitted_count == item.identifier_count - len(item.identifiers)
        for item in exclusions
    )
    assert liquidity.calculation_status == "partial"


def test_latest_and_concentration_aggregates_fail_closed_on_finite_overflow() -> None:
    snapshot = _snapshot(stock_count=20)
    prices = snapshot.daily_price.copy()
    large = float(np.finfo(float).max * 0.75)
    prices.loc[prices["trade_date"].eq(snapshot.requested_end_date), "amount"] = large

    liquidity = calculate_market_cockpit(
        replace(snapshot, daily_price=prices)
    ).liquidity_context

    assert liquidity.latest_eligible_count == 20
    assert liquidity.latest_unavailable_count == 0
    assert liquidity.latest_total_amount is None
    assert liquidity.latest_median_amount == large
    assert liquidity.latest_aggregate_reason == "non_finite_aggregate"
    assert liquidity.top5_member_count == 5
    assert liquidity.top_decile_member_count == 2
    assert liquidity.top5_concentration_share is None
    assert liquidity.top_decile_concentration_share is None
    assert liquidity.calculation_status == "partial"
    assert any("non-finite total" in warning for warning in liquidity.warnings)
    json.dumps(liquidity, default=lambda value: value.__dict__, allow_nan=False)


def test_exact_activity_windows_fail_closed_on_finite_session_total_overflow() -> None:
    snapshot = _snapshot(stock_count=2, session_count=21)
    prices = snapshot.daily_price.copy()
    overflow_session = snapshot.trade_calendar.iloc[-3]["trade_date"]
    prices.loc[
        prices["trade_date"].eq(overflow_session), "amount"
    ] = float(np.finfo(float).max * 0.75)

    liquidity = calculate_market_cockpit(
        replace(snapshot, daily_price=prices)
    ).liquidity_context

    for window in (liquidity.activity_5, liquidity.activity_20):
        assert window.matched_cohort_count == 2
        assert window.unavailable_stock_count == 0
        assert window.latest_matched_total_amount is None
        assert window.baseline_total_amount is None
        assert window.activity_ratio is None
        assert window.calculation_status == "unavailable"
        assert window.reason == "non_finite_aggregate"
    payload = json.dumps(
        liquidity,
        default=lambda value: value.__dict__,
        allow_nan=False,
    )
    assert "NaN" not in payload
    assert "Infinity" not in payload


def test_large_latest_issue_diagnostics_are_exact_bounded_and_deterministic() -> None:
    snapshot = _snapshot(stock_count=25)
    prices = snapshot.daily_price.copy()
    prices.loc[
        prices["trade_date"].eq(snapshot.requested_end_date), "amount"
    ] = 0.0
    bounded = replace(snapshot, daily_price=prices)

    first = calculate_market_cockpit(bounded).liquidity_context
    second = calculate_market_cockpit(bounded).liquidity_context
    diagnostics = first.diagnostics

    assert first == second
    assert first.latest_unavailable_count == 25
    assert diagnostics.latest_issue_count == 25
    assert len(diagnostics.latest_issues) == LIQUIDITY_IDENTIFIER_SAMPLE_LIMIT
    assert [issue.stock_code for issue in diagnostics.latest_issues] == [
        f"{index:06d}" for index in range(1, 11)
    ]
    assert diagnostics.latest_issues_truncated is True
    assert diagnostics.latest_issues_omitted_count == 15
    assert first.activity_5.unavailable_stock_count == 25
    assert first.activity_20.unavailable_stock_count == 25
    assert first.activity_5.unavailable_stock_codes_truncated is True
    assert first.activity_20.unavailable_stock_codes_omitted_count == 15
    assert all("(+15 more)" in warning for warning in first.warnings[:3])
    assert all(len(warning) < 500 for warning in first.warnings)
    assert "000025" not in " ".join(first.warnings)


def test_large_window_diagnostics_do_not_change_full_matched_cohort_math() -> None:
    snapshot = _snapshot(stock_count=30, session_count=21)
    prices = snapshot.daily_price.copy()
    affected_session = snapshot.trade_calendar.iloc[-3]["trade_date"]
    unavailable_codes = [f"{index:06d}" for index in range(1, 16)]
    prices.loc[
        prices["trade_date"].eq(affected_session)
        & prices["stock_code"].isin(unavailable_codes),
        "amount",
    ] = 0.0

    liquidity = calculate_market_cockpit(
        replace(snapshot, daily_price=prices)
    ).liquidity_context

    for window in (liquidity.activity_5, liquidity.activity_20):
        assert window.matched_cohort_count == 15
        assert window.unavailable_stock_count == 15
        assert window.unavailable_stock_codes == unavailable_codes[:10]
        assert window.unavailable_stock_codes_truncated is True
        assert window.unavailable_stock_codes_omitted_count == 5
        assert window.activity_ratio == 1.0
        assert window.calculation_status == "partial"
    assert liquidity.latest_above_20_session_baseline_count == 0
    assert liquidity.latest_above_20_session_baseline_share == 0.0
    assert any("(+5 more)" in warning for warning in liquidity.warnings)


def test_large_top_decile_sample_is_bounded_without_changing_denominator() -> None:
    snapshot = _snapshot(stock_count=120)

    liquidity = calculate_market_cockpit(snapshot).liquidity_context

    expected_total = float(sum(index * 10 for index in range(1, 121)))
    expected_numerator = float(sum(index * 10 for index in range(109, 121)))
    assert liquidity.latest_total_amount == expected_total
    assert liquidity.top_decile_member_count == 12
    assert liquidity.top_decile_stock_codes == [
        f"{index:06d}" for index in range(109, 119)
    ]
    assert liquidity.top_decile_stock_codes_truncated is True
    assert liquidity.top_decile_stock_codes_omitted_count == 2
    assert liquidity.top_decile_concentration_share == pytest.approx(
        expected_numerator / expected_total
    )
    assert liquidity.activity_5.matched_cohort_count == 120
    assert liquidity.activity_20.matched_cohort_count == 120
    assert liquidity.activity_5.activity_ratio == 1.0
    assert liquidity.activity_20.activity_ratio == 1.0


def test_output_is_deterministic_and_strict_json_safe() -> None:
    snapshot = _snapshot(stock_count=12)
    first = calculate_market_cockpit(snapshot).liquidity_context
    second = calculate_market_cockpit(snapshot).liquidity_context

    assert first == second
    serialized = json.dumps(first, default=lambda value: value.__dict__, allow_nan=False)
    assert "NaN" not in serialized
    assert "Infinity" not in serialized
    assert "crowding conclusion" in serialized


def test_persisted_liquidity_fixture_demo_is_offline_and_deterministic() -> None:
    payload = build_liquidity_context_demo()

    assert payload["current"]["effective_session"] == payload["historical"][
        "effective_session"
    ]
    assert payload["current"]["latest_total_amount"] == 12000.0
    assert payload["current"]["activity_5"]["activity_ratio"] == 2.0
    assert payload["current"]["activity_20"]["matched_cohort_count"] == 3
    assert payload["current"]["calculation_status"] == "complete"
    assert payload["read_only"] is True
    assert payload["network_access"] is False
    assert payload["temporary_database_removed"] is True
