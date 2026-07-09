"""Quality factor calculators."""

from __future__ import annotations

import numpy as np
import pandas as pd

from factors.base import FactorCalculator, FactorDefinition, FactorResult, build_factor_frame, require_columns


class RoeCalculator(FactorCalculator):
    definition = FactorDefinition(name="roe", group="quality", direction="descending")
    required_columns = ("factor_date", "stock_code", "net_profit", "equity")

    def calculate(self, data: pd.DataFrame) -> FactorResult:
        require_columns(data, self.required_columns)
        values = _ratio(data["net_profit"], data["equity"])
        return FactorResult(self.definition, build_factor_frame(data, self.definition, values))


class GrossMarginCalculator(FactorCalculator):
    definition = FactorDefinition(name="gross_margin", group="quality", direction="descending")
    required_columns = ("factor_date", "stock_code", "gross_profit", "revenue")

    def calculate(self, data: pd.DataFrame) -> FactorResult:
        require_columns(data, self.required_columns)
        values = _ratio(data["gross_profit"], data["revenue"])
        return FactorResult(self.definition, build_factor_frame(data, self.definition, values))


def _ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    numerator_numeric = pd.to_numeric(numerator, errors="coerce")
    denominator_numeric = pd.to_numeric(denominator, errors="coerce")
    return numerator_numeric / denominator_numeric.where(denominator_numeric != 0, np.nan)
