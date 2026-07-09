"""Deterministic baseline model path for Phase 4."""

from __future__ import annotations

import pandas as pd

from ml.base import MLExperimentConfig, PREDICTION_COLUMNS, FeatureDataset, PredictionResult


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

        frame = features.frame.copy()
        numeric_features = frame.loc[:, self.config.feature_columns].apply(pd.to_numeric, errors="coerce")
        frame["prediction_score"] = numeric_features.mean(axis=1).fillna(0.0)
        frame["prediction_date"] = frame["feature_date"].astype(str)
        frame["model_name"] = self.config.model_name
        frame["prediction_rank"] = (
            frame.groupby(["prediction_date", "universe"])["prediction_score"]
            .rank(method="first", ascending=False)
            .astype(int)
        )
        predictions = frame[PREDICTION_COLUMNS].sort_values(["prediction_date", "prediction_rank"]).reset_index(drop=True)
        return PredictionResult(predictions)
