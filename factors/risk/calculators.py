"""Risk factor calculators."""

from __future__ import annotations

import pandas as pd

from factors.base import FactorCalculator, FactorDefinition, FactorResult, FACTOR_VALUE_COLUMNS, require_columns


class Volatility20DCalculator(FactorCalculator):
    definition = FactorDefinition(name="volatility_20d", group="risk", direction="ascending")
    required_columns = ("trade_date", "stock_code", "close")
    window = 20

    def calculate(self, data: pd.DataFrame) -> FactorResult:
        require_columns(data, self.required_columns)
        frame = _with_returns(data)
        frame["factor_value"] = frame.groupby("stock_code")["daily_return"].rolling(self.window).std().reset_index(level=0, drop=True)
        return FactorResult(self.definition, _latest_factor_frame(frame, self.definition))


class MaxDrawdown60DCalculator(FactorCalculator):
    definition = FactorDefinition(name="max_drawdown_60d", group="risk", direction="ascending")
    required_columns = ("trade_date", "stock_code", "close")
    window = 60

    def calculate(self, data: pd.DataFrame) -> FactorResult:
        require_columns(data, self.required_columns)
        frame = data.copy()
        frame["trade_date"] = frame["trade_date"].astype(str)
        frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
        frame = frame.sort_values(["stock_code", "trade_date"])
        rolling_max = frame.groupby("stock_code")["close"].rolling(self.window, min_periods=2).max().reset_index(level=0, drop=True)
        frame["drawdown"] = frame["close"] / rolling_max - 1
        frame["factor_value"] = frame.groupby("stock_code")["drawdown"].rolling(self.window, min_periods=2).min().reset_index(level=0, drop=True).abs()
        return FactorResult(self.definition, _latest_factor_frame(frame, self.definition))


def _with_returns(data: pd.DataFrame) -> pd.DataFrame:
    frame = data.copy()
    frame["trade_date"] = frame["trade_date"].astype(str)
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.sort_values(["stock_code", "trade_date"])
    frame["daily_return"] = frame.groupby("stock_code")["close"].pct_change()
    return frame


def _latest_factor_frame(frame: pd.DataFrame, definition: FactorDefinition) -> pd.DataFrame:
    latest = frame.groupby("stock_code", as_index=False).tail(1)
    values = pd.DataFrame(
        {
            "factor_date": latest["trade_date"],
            "stock_code": latest["stock_code"].astype(str),
            "factor_name": definition.name,
            "factor_value": latest["factor_value"],
            "factor_group": definition.group,
            "factor_version": definition.version,
        }
    )
    return values[FACTOR_VALUE_COLUMNS]
