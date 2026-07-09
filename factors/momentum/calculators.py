"""Momentum factor calculators."""

from __future__ import annotations

import pandas as pd

from factors.base import FactorCalculator, FactorDefinition, FactorResult, FACTOR_VALUE_COLUMNS, require_columns


class Return20DCalculator(FactorCalculator):
    definition = FactorDefinition(name="return_20d", group="momentum", direction="descending")
    required_columns = ("trade_date", "stock_code", "close")
    window = 20

    def calculate(self, data: pd.DataFrame) -> FactorResult:
        return _calculate_window_return(data, self.definition, self.required_columns, self.window)


class Return60DCalculator(FactorCalculator):
    definition = FactorDefinition(name="return_60d", group="momentum", direction="descending")
    required_columns = ("trade_date", "stock_code", "close")
    window = 60

    def calculate(self, data: pd.DataFrame) -> FactorResult:
        return _calculate_window_return(data, self.definition, self.required_columns, self.window)


def _calculate_window_return(
    data: pd.DataFrame,
    definition: FactorDefinition,
    required_columns: tuple[str, ...],
    window: int,
) -> FactorResult:
    require_columns(data, required_columns)
    frame = data.copy()
    frame["trade_date"] = frame["trade_date"].astype(str)
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.sort_values(["stock_code", "trade_date"])
    frame["factor_value"] = frame.groupby("stock_code")["close"].pct_change(periods=window)
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
    return FactorResult(definition, values[FACTOR_VALUE_COLUMNS])
