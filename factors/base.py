"""Factor calculation contracts for AQuantAI."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

import pandas as pd

FactorDirection = Literal["ascending", "descending"]

FACTOR_VALUE_COLUMNS = [
    "factor_date",
    "stock_code",
    "factor_name",
    "factor_value",
    "factor_group",
    "factor_version",
]

FACTOR_SCORE_COLUMNS = [
    "score_date",
    "stock_code",
    "factor_name",
    "factor_group",
    "score",
    "rank",
    "universe",
]


@dataclass(frozen=True)
class FactorDefinition:
    """Metadata and scoring direction for one factor."""

    name: str
    group: str
    direction: FactorDirection
    version: str = "1.0.0"


@dataclass(frozen=True)
class FactorResult:
    """Normalized factor values plus their definition."""

    definition: FactorDefinition
    values: pd.DataFrame


class FactorCalculator(ABC):
    """Base class for deterministic pandas factor calculators."""

    definition: FactorDefinition
    required_columns: tuple[str, ...]

    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> FactorResult:
        """Calculate normalized factor values from an input DataFrame."""


def build_factor_frame(
    data: pd.DataFrame,
    definition: FactorDefinition,
    values: pd.Series,
    date_column: str = "factor_date",
) -> pd.DataFrame:
    """Build the normalized factor output frame."""
    frame = pd.DataFrame(
        {
            "factor_date": data[date_column].astype(str),
            "stock_code": data["stock_code"].astype(str),
            "factor_name": definition.name,
            "factor_value": values,
            "factor_group": definition.group,
            "factor_version": definition.version,
        }
    )
    return frame[FACTOR_VALUE_COLUMNS]


def require_columns(data: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"Missing required factor input columns: {missing}")
