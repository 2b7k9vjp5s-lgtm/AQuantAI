"""Deterministic long-history Market Cockpit fixtures with no network access."""

from __future__ import annotations

import pandas as pd

from datasource.base import MarketDataBundle

COCKPIT_FIXTURE_PROVIDER = "fixture"
COCKPIT_FIXTURE_ADJUST_TYPE = "qfq"
COCKPIT_FIXTURE_DATES = pd.bdate_range("2026-01-05", periods=65).strftime("%Y%m%d").tolist()
COCKPIT_FIXTURE_START_DATE = COCKPIT_FIXTURE_DATES[0]
COCKPIT_FIXTURE_END_DATE = COCKPIT_FIXTURE_DATES[-1]
COCKPIT_FIXTURE_HISTORICAL_CUTOFF = "20260404"
COCKPIT_FIXTURE_CURRENT_CUTOFF = "20260405"
COCKPIT_FIXTURE_CODES = ["000001", "000002", "000003"]
COCKPIT_FIXTURE_SCOPE = {
    "datasets": ["stock_basic", "daily_price", "trade_calendar"],
    "stock_codes": COCKPIT_FIXTURE_CODES,
}


def build_market_cockpit_fixture(*, revision: str = "current") -> MarketDataBundle:
    """Build 65 open sessions for all authorized v0.4A calculations."""
    if revision not in {"historical", "current"}:
        raise ValueError("revision must be 'historical' or 'current'.")
    stock_basic = pd.DataFrame(
        [
            {
                "stock_code": code,
                "stock_name": f"Fixture Stock {code}",
                "exchange": "SZ" if code.startswith("0") else "SH",
                "industry": "Fixture",
                "listing_date": "20200101",
                "status": "active",
                "source": COCKPIT_FIXTURE_PROVIDER,
            }
            for code in COCKPIT_FIXTURE_CODES
        ]
    )
    session_count = len(COCKPIT_FIXTURE_DATES)
    closes = {
        "000001": [100.0 + index for index in range(session_count)],
        "000002": [200.0 - index * 0.5 for index in range(session_count)],
        "000003": [50.0 for _ in range(session_count)],
    }
    up_move, down_move = ((1.05, 0.95) if revision == "historical" else (1.10, 0.90))
    closes["000001"][-1] = closes["000001"][-2] * up_move
    closes["000002"][-1] = closes["000002"][-2] * down_move
    price_rows: list[dict] = []
    for code_index, code in enumerate(COCKPIT_FIXTURE_CODES, start=1):
        for date_index, trade_date in enumerate(COCKPIT_FIXTURE_DATES):
            close = closes[code][date_index]
            volume = float(100 * code_index)
            amount = float(1000 * code_index)
            if date_index == session_count - 1:
                volume *= 2
                amount *= 2
            price_rows.append(
                {
                    "trade_date": trade_date,
                    "stock_code": code,
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                    "volume": volume,
                    "amount": amount,
                    "adjust_type": COCKPIT_FIXTURE_ADJUST_TYPE,
                    "source": COCKPIT_FIXTURE_PROVIDER,
                }
            )
    trade_calendar = pd.DataFrame(
        [
            {
                "trade_date": trade_date,
                "is_open": True,
                "source": COCKPIT_FIXTURE_PROVIDER,
            }
            for trade_date in COCKPIT_FIXTURE_DATES
        ]
    )
    return MarketDataBundle(
        stock_basic=stock_basic,
        daily_price=pd.DataFrame(price_rows),
        trade_calendar=trade_calendar,
    )
