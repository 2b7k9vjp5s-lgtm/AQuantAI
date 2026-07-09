"""Growth factor calculators."""

from __future__ import annotations

import numpy as np
import pandas as pd

from factors.base import FactorCalculator, FactorDefinition, FactorResult, build_factor_frame, require_columns


class RevenueGrowthCalculator(FactorCalculator):
    definition = FactorDefinition(name="revenue_growth", group="growth", direction="descending")
    required_columns = ("factor_date", "stock_code", "revenue", "revenue_prev")

    def calculate(self, data: pd.DataFrame) -> FactorResult:
        require_columns(data, self.required_columns)
        values = _growth_rate(data["revenue"], data["revenue_prev"])
        return FactorResult(self.definition, build_factor_frame(data, self.definition, values))


class NetProfitGrowthCalculator(FactorCalculator):
    definition = FactorDefinition(name="net_profit_growth", group="growth", direction="descending")
    required_columns = ("factor_date", "stock_code", "net_profit", "net_profit_prev")

    def calculate(self, data: pd.DataFrame) -> FactorResult:
        require_columns(data, self.required_columns)
        values = _growth_rate(data["net_profit"], data["net_profit_prev"])
        return FactorResult(self.definition, build_factor_frame(data, self.definition, values))


def _growth_rate(current: pd.Series, previous: pd.Series) -> pd.Series:
    current_numeric = pd.to_numeric(current, errors="coerce")
    previous_numeric = pd.to_numeric(previous, errors="coerce")
    return (current_numeric - previous_numeric) / previous_numeric.where(previous_numeric != 0, np.nan)
