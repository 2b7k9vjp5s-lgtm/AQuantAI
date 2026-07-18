"""Deterministic local market-data fixtures with no provider or network calls."""

from __future__ import annotations

import pandas as pd

from datasource.base import MarketDataBundle

FIXTURE_PROVIDER = "fixture"
FIXTURE_START_DATE = "20260708"
FIXTURE_END_DATE = "20260709"
FIXTURE_CUTOFF_DATE = "20260709"
FIXTURE_SCOPE = {
    "datasets": ["stock_basic", "daily_price", "trade_calendar"],
    "stock_codes": ["000001", "600000"],
}


def build_market_data_fixture() -> MarketDataBundle:
    """Return local normalized frames used by persistence tests and the CLI."""
    stock_basic = pd.DataFrame(
        [
            {
                "stock_code": "000001",
                "stock_name": "Ping An Bank",
                "exchange": "SZ",
                "industry": "Banking",
                "listing_date": "19910403",
                "status": "active",
                "source": FIXTURE_PROVIDER,
            },
            {
                "stock_code": "600000",
                "stock_name": "SPDB",
                "exchange": "SH",
                "industry": "Banking",
                "listing_date": "19991110",
                "status": "active",
                "source": FIXTURE_PROVIDER,
            },
        ]
    )
    daily_price = pd.DataFrame(
        [
            {
                "trade_date": "20260708",
                "stock_code": "000001",
                "open": 10.0,
                "high": 10.8,
                "low": 9.9,
                "close": 10.5,
                "volume": 1000.0,
                "amount": 10450.0,
                "adjust_type": "",
                "source": FIXTURE_PROVIDER,
            },
            {
                "trade_date": "20260708",
                "stock_code": "600000",
                "open": 8.0,
                "high": 8.3,
                "low": 7.9,
                "close": 8.2,
                "volume": 2000.0,
                "amount": 16200.0,
                "adjust_type": "",
                "source": FIXTURE_PROVIDER,
            },
            {
                "trade_date": "20260709",
                "stock_code": "000001",
                "open": 10.5,
                "high": 11.0,
                "low": 10.3,
                "close": 10.9,
                "volume": 1200.0,
                "amount": 12840.0,
                "adjust_type": "",
                "source": FIXTURE_PROVIDER,
            },
            {
                "trade_date": "20260709",
                "stock_code": "600000",
                "open": 8.2,
                "high": 8.4,
                "low": 8.0,
                "close": 8.1,
                "volume": 1800.0,
                "amount": 14760.0,
                "adjust_type": "",
                "source": FIXTURE_PROVIDER,
            },
        ]
    )
    trade_calendar = pd.DataFrame(
        [
            {"trade_date": "20260708", "is_open": True, "source": FIXTURE_PROVIDER},
            {"trade_date": "20260709", "is_open": True, "source": FIXTURE_PROVIDER},
        ]
    )
    return MarketDataBundle(
        stock_basic=stock_basic,
        daily_price=daily_price,
        trade_calendar=trade_calendar,
    )
