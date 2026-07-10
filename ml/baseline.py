"""Deterministic baseline model path for Phase 4."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml.base import MLExperimentConfig, PREDICTION_COLUMNS, FeatureDataset, PredictionResult, validate_feature_frame


class FactorAverageBaselineModel:
    """Average selected feature columns to validate prediction contracts."""

    def __init__(self, config: MLExperimentConfig) -> None:
        if not config.feature_columns:
            raise ValueError("config.feature_columns must not be empty")
        self.config = config

    def predict(self, features: FeatureDataset) -> PredictionResult:
        missing = [column for column in self.config.feature_columns if column not in features.frame.columns]
        if missing:
            raise ValueError(f"features is missing configured feature columns: {missing}")

        frame = validate_feature_frame(features.frame, self.config.feature_columns)
        if not frame["universe"].eq(self.config.universe).all():
            raise ValueError("features universe must match the experiment universe")
        numeric_features = frame.loc[:, self.config.feature_columns].apply(pd.to_numeric, errors="coerce")
        if numeric_features.isna().any().any() or not np.isfinite(numeric_features.to_numpy()).all():
            raise ValueError("configured features must contain finite numeric values")
        frame["prediction_score"] = numeric_features.mean(axis=1)
        frame["prediction_date"] = frame["feature_date"].astype(str)
        frame["model_name"] = self.config.model_name
        frame = frame.sort_values(
            ["prediction_date", "universe", "prediction_score", "stock_code"],
            ascending=[True, True, False, True],
            kind="stable",
        )
        frame["prediction_rank"] = frame.groupby(["prediction_date", "universe"], sort=False).cumcount() + 1
        predictions = frame[PREDICTION_COLUMNS].reset_index(drop=True)
        return PredictionResult(predictions)
