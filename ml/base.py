"""ML experiment contracts for AQuantAI."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

FEATURE_REQUIRED_COLUMNS = ["feature_date", "stock_code", "universe"]
LABEL_REQUIRED_COLUMNS = ["label_date", "stock_code", "future_return", "label_window", "universe"]
PREDICTION_COLUMNS = [
    "prediction_date",
    "stock_code",
    "model_name",
    "prediction_score",
    "prediction_rank",
    "universe",
]


@dataclass(frozen=True)
class MLExperimentConfig:
    """Configuration for a guarded ML research experiment."""

    experiment_name: str
    model_name: str = "baseline_factor_average"
    universe: str = "default"
    feature_columns: tuple[str, ...] = ()
    label_window: str = "20d"


@dataclass(frozen=True)
class FeatureDataset:
    """Validated feature dataset wrapper."""

    frame: pd.DataFrame
    feature_columns: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "frame", validate_feature_frame(self.frame, self.feature_columns))


@dataclass(frozen=True)
class LabelDataset:
    """Validated label dataset wrapper."""

    frame: pd.DataFrame


@dataclass(frozen=True)
class PredictionResult:
    """Normalized prediction output."""

    predictions: pd.DataFrame


@dataclass(frozen=True)
class ModelEvaluationResult:
    """Deterministic evaluation summary for research experiments."""

    model_name: str
    metrics: dict[str, float]


def build_feature_dataset(frame: pd.DataFrame, feature_columns: tuple[str, ...]) -> FeatureDataset:
    return FeatureDataset(frame, feature_columns)


def validate_feature_frame(frame: pd.DataFrame, feature_columns: tuple[str, ...]) -> pd.DataFrame:
    require_non_empty(frame, "features")
    require_columns(frame, FEATURE_REQUIRED_COLUMNS, "features")
    if not feature_columns:
        raise ValueError("feature_columns must not be empty")
    require_columns(frame, list(feature_columns), "features")
    if frame[FEATURE_REQUIRED_COLUMNS].isna().any().any():
        raise ValueError(f"features must not contain missing identifiers: {FEATURE_REQUIRED_COLUMNS}")
    normalized = frame.copy()
    for column in FEATURE_REQUIRED_COLUMNS:
        normalized[column] = normalized[column].astype(str).str.strip()
    if (normalized[FEATURE_REQUIRED_COLUMNS] == "").any().any():
        raise ValueError(f"features must not contain blank identifiers: {FEATURE_REQUIRED_COLUMNS}")
    if normalized.duplicated(["feature_date", "stock_code", "universe"]).any():
        raise ValueError("features contains duplicate (feature_date, stock_code, universe) rows")
    for column in feature_columns:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        if normalized[column].isna().any() or not np.isfinite(normalized[column]).all():
            raise ValueError(f"features column {column} must contain finite numeric values")
    return normalized


def build_label_dataset(frame: pd.DataFrame) -> LabelDataset:
    require_non_empty(frame, "labels")
    require_columns(frame, LABEL_REQUIRED_COLUMNS, "labels")
    normalized = frame.copy()
    normalized["label_date"] = normalized["label_date"].astype(str)
    normalized["stock_code"] = normalized["stock_code"].astype(str)
    normalized["label_window"] = normalized["label_window"].astype(str)
    normalized["universe"] = normalized["universe"].astype(str)
    normalized["future_return"] = pd.to_numeric(normalized["future_return"], errors="coerce")
    if normalized["future_return"].isna().all():
        raise ValueError("labels must contain at least one finite future_return")
    return LabelDataset(normalized)


def require_columns(data: pd.DataFrame, columns: list[str], frame_name: str) -> None:
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"{frame_name} is missing required columns: {missing}")


def require_non_empty(data: pd.DataFrame, frame_name: str) -> None:
    if data.empty:
        raise ValueError(f"{frame_name} must not be empty")
