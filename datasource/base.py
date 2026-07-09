"""Data provider contracts for AQuantAI."""

from abc import ABC, abstractmethod
from typing import Literal

import pandas as pd

AdjustType = Literal["", "qfq", "hfq"]

STOCK_BASIC_COLUMNS = [
    "stock_code",
    "stock_name",
    "exchange",
    "industry",
    "listing_date",
    "status",
    "source",
]

DAILY_PRICE_COLUMNS = [
    "trade_date",
    "stock_code",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "adjust_type",
    "source",
]

TRADE_CALENDAR_COLUMNS = [
    "trade_date",
    "is_open",
    "source",
]


class DataProvider(ABC):
    """Abstract boundary for market data providers."""

    @abstractmethod
    def get_stock_basic(self) -> pd.DataFrame:
        """Return stock identity data using STOCK_BASIC_COLUMNS."""

    @abstractmethod
    def get_daily_price(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: AdjustType = "",
    ) -> pd.DataFrame:
        """Return daily OHLCV data using DAILY_PRICE_COLUMNS."""

    @abstractmethod
    def get_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Return exchange calendar data using TRADE_CALENDAR_COLUMNS."""
