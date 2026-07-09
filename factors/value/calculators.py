"""Value factor calculators."""

from __future__ import annotations

import numpy as np
import pandas as pd

from factors.base import FactorCalculator, FactorDefinition, FactorResult, build_factor_frame, require_columns


class PeInverseCalculator(FactorCalculator):
    definition = FactorDefinition(name="pe_inverse", group="value", direction="descending")
    required_columns = ("factor_date", "stock_code", "pe")

    def calculate(self, data: pd.DataFrame) -> FactorResult:
        require_columns(data, self.required_columns)
        values = _safe_inverse(data["pe"])
        return FactorResult(self.definition, build_factor_frame(data, self.definition, values))


class PbInverseCalculator(FactorCalculator):
    definition = FactorDefinition(name="pb_inverse", group="value", direction="descending")
    required_columns = ("factor_date", "stock_code", "pb")

    def calculate(self, data: pd.DataFrame) -> FactorResult:
        require_columns(data, self.required_columns)
        values = _safe_inverse(data["pb"])
        return FactorResult(self.definition, build_factor_frame(data, self.definition, values))


def _safe_inverse(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return 1 / numeric.where(numeric > 0, np.nan)
