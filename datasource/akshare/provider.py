"""AKShare-backed data provider with normalized AQuantAI contracts."""

from __future__ import annotations

from typing import Any

import pandas as pd

from datasource.base import (
    DAILY_PRICE_COLUMNS,
    STOCK_BASIC_COLUMNS,
    TRADE_CALENDAR_COLUMNS,
    AdjustType,
    DataProvider,
)

RAW_CODE = "\u4ee3\u7801"
RAW_NAME = "\u540d\u79f0"
RAW_DATE = "\u65e5\u671f"
RAW_STOCK_CODE = "\u80a1\u7968\u4ee3\u7801"
RAW_OPEN = "\u5f00\u76d8"
RAW_HIGH = "\u6700\u9ad8"
RAW_LOW = "\u6700\u4f4e"
RAW_CLOSE = "\u6536\u76d8"
RAW_VOLUME = "\u6210\u4ea4\u91cf"
RAW_AMOUNT = "\u6210\u4ea4\u989d"


class AkshareDataProvider(DataProvider):
    """Wrap AKShare calls and return stable internal column names."""

    source_name = "akshare"

    def __init__(self, akshare_client: Any | None = None) -> None:
        self._akshare = akshare_client

    @property
    def akshare(self) -> Any:
        if self._akshare is None:
            import akshare as akshare_client

            self._akshare = akshare_client
        return self._akshare

    def get_stock_basic(self) -> pd.DataFrame:
        """Return normalized A-share stock identity data."""
        raw = self.akshare.stock_info_a_code_name()
        if raw.empty:
            return _empty_frame(STOCK_BASIC_COLUMNS)

        frame = raw.rename(
            columns={
                "code": "stock_code",
                "name": "stock_name",
                RAW_CODE: "stock_code",
                RAW_NAME: "stock_name",
            }
        )
        frame = _ensure_columns(
            frame,
            STOCK_BASIC_COLUMNS,
            defaults={
                "exchange": "",
                "industry": "",
                "listing_date": pd.NA,
                "status": "active",
                "source": self.source_name,
            },
        )
        frame["stock_code"] = frame["stock_code"].astype(str)
        return frame[STOCK_BASIC_COLUMNS]

    def get_daily_price(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: AdjustType = "",
    ) -> pd.DataFrame:
        """Return normalized daily prices for one A-share symbol."""
        raw = self.akshare.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        if raw.empty:
            return _empty_frame(DAILY_PRICE_COLUMNS)

        frame = raw.rename(
            columns={
                RAW_DATE: "trade_date",
                RAW_STOCK_CODE: "stock_code",
                RAW_CODE: "stock_code",
                RAW_OPEN: "open",
                RAW_HIGH: "high",
                RAW_LOW: "low",
                RAW_CLOSE: "close",
                RAW_VOLUME: "volume",
                RAW_AMOUNT: "amount",
            }
        )
        frame = _ensure_columns(
            frame,
            DAILY_PRICE_COLUMNS,
            defaults={
                "stock_code": symbol,
                "adjust_type": adjust,
                "source": self.source_name,
            },
        )
        frame["stock_code"] = frame["stock_code"].astype(str)
        frame["trade_date"] = _normalize_date(frame["trade_date"])
        return frame[DAILY_PRICE_COLUMNS]

    def get_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Return normalized open trading dates within the requested range."""
        raw = self.akshare.tool_trade_date_hist_sina()
        if raw.empty:
            return _empty_frame(TRADE_CALENDAR_COLUMNS)

        frame = raw.rename(columns={"trade_date": "trade_date", RAW_DATE: "trade_date"})
        frame = _ensure_columns(
            frame,
            TRADE_CALENDAR_COLUMNS,
            defaults={"is_open": True, "source": self.source_name},
        )
        frame["trade_date"] = _normalize_date(frame["trade_date"])
        frame = frame[
            (frame["trade_date"] >= _compact_date(start_date))
            & (frame["trade_date"] <= _compact_date(end_date))
        ]
        return frame[TRADE_CALENDAR_COLUMNS]


def _empty_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _ensure_columns(
    frame: pd.DataFrame,
    columns: list[str],
    defaults: dict[str, Any],
) -> pd.DataFrame:
    normalized = frame.copy()
    for column in columns:
        if column not in normalized.columns:
            normalized[column] = defaults.get(column, pd.NA)
    return normalized


def _normalize_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.strftime("%Y%m%d")


def _compact_date(value: str) -> str:
    return value.replace("-", "")
