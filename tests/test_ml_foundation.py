import pandas as pd
import pytest

from ml import PREDICTION_COLUMNS, MLExperimentConfig
from ml.base import FeatureDataset, build_feature_dataset, build_label_dataset
from ml.baseline import FactorAverageBaselineModel
from ml.qlib import QlibAdapter


def _feature_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"feature_date": "20260630", "stock_code": "000001", "value_score": 80.0, "quality_score": 70.0, "universe": "test"},
            {"feature_date": "20260630", "stock_code": "000002", "value_score": 60.0, "quality_score": 95.0, "universe": "test"},
            {"feature_date": "20260630", "stock_code": "000003", "value_score": 30.0, "quality_score": 40.0, "universe": "test"},
        ]
    )


def _label_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"label_date": "20260731", "stock_code": "000001", "future_return": 0.05, "label_window": "20d", "universe": "test"},
            {"label_date": "20260731", "stock_code": "000002", "future_return": -0.01, "label_window": "20d", "universe": "test"},
        ]
    )


def test_feature_and_label_contract_validation() -> None:
    features = build_feature_dataset(_feature_fixture(), ("value_score", "quality_score"))
    labels = build_label_dataset(_label_fixture())

    assert features.feature_columns == ("value_score", "quality_score")
    assert features.frame["feature_date"].tolist() == ["20260630", "20260630", "20260630"]
    assert labels.frame["future_return"].tolist() == [0.05, -0.01]


def test_baseline_predictions_are_deterministic_and_normalized() -> None:
    config = MLExperimentConfig(
        experiment_name="phase4-test",
        model_name="baseline_factor_average",
        universe="test",
        feature_columns=("value_score", "quality_score"),
    )
    features = build_feature_dataset(_feature_fixture(), config.feature_columns)
    model = FactorAverageBaselineModel(config)

    predictions = model.predict(features).predictions

    assert list(predictions.columns) == PREDICTION_COLUMNS
    assert predictions["stock_code"].tolist() == ["000002", "000001", "000003"]
    assert predictions["prediction_rank"].tolist() == [1, 2, 3]
    assert predictions["prediction_score"].tolist() == [77.5, 75.0, 35.0]
    assert set(predictions["model_name"]) == {"baseline_factor_average"}


def test_missing_required_columns_fail_clearly() -> None:
    with pytest.raises(ValueError, match="features is missing required columns"):
        build_feature_dataset(pd.DataFrame([{"stock_code": "000001"}]), ("value_score",))

    with pytest.raises(ValueError, match="labels is missing required columns"):
        build_label_dataset(pd.DataFrame([{"stock_code": "000001"}]))

    config = MLExperimentConfig(experiment_name="phase4-test", feature_columns=("missing_feature",))
    features = build_feature_dataset(_feature_fixture(), ("value_score", "quality_score"))
    with pytest.raises(ValueError, match="features is missing configured feature columns"):
        FactorAverageBaselineModel(config).predict(features)


def test_qlib_adapter_is_lazy_and_mockable() -> None:
    config = MLExperimentConfig(experiment_name="phase4-test", model_name="mock_model", universe="test")
    adapter = QlibAdapter(qlib_module=object())

    assert adapter.is_available()
    assert adapter.build_experiment_payload(config) == {
        "experiment_name": "phase4-test",
        "model_name": "mock_model",
        "universe": "test",
        "label_window": "20d",
        "adapter": "qlib",
    }


def test_qlib_adapter_reports_missing_optional_dependency() -> None:
    adapter = QlibAdapter()

    if adapter.is_available():
        pytest.skip("Qlib is installed in this environment")

    with pytest.raises(RuntimeError, match="Qlib is not installed"):
        _ = adapter.qlib


def test_ml_feature_validation_and_tie_breaking_are_deterministic() -> None:
    config = MLExperimentConfig(experiment_name="phase4-test", universe="test", feature_columns=("value_score",))
    tied_features = pd.DataFrame(
        [
            {"feature_date": "20260630", "stock_code": "000002", "value_score": 80.0, "universe": "test"},
            {"feature_date": "20260630", "stock_code": "000001", "value_score": 80.0, "universe": "test"},
            {"feature_date": "20260701", "stock_code": "000001", "value_score": 70.0, "universe": "test"},
        ]
    )

    predictions = FactorAverageBaselineModel(config).predict(
        build_feature_dataset(tied_features, config.feature_columns)
    ).predictions

    first_date = predictions[predictions["prediction_date"] == "20260630"]
    assert first_date["stock_code"].tolist() == ["000001", "000002"]
    assert first_date["prediction_rank"].tolist() == [1, 2]
    assert predictions[predictions["prediction_date"] == "20260701"]["prediction_rank"].tolist() == [1]

    with pytest.raises(ValueError, match=r"duplicate \(feature_date, stock_code, universe\)"):
        build_feature_dataset(pd.concat([tied_features, tied_features.iloc[[0]]], ignore_index=True), config.feature_columns)

    non_finite = tied_features.copy()
    non_finite.loc[0, "value_score"] = float("inf")
    with pytest.raises(ValueError, match="finite numeric"):
        build_feature_dataset(non_finite, config.feature_columns)

    mismatched_universe = tied_features.copy()
    mismatched_universe.loc[0, "universe"] = "other"
    with pytest.raises(ValueError, match="experiment universe"):
        FactorAverageBaselineModel(config).predict(build_feature_dataset(mismatched_universe, config.feature_columns))

    unchecked = FeatureDataset(
        tied_features.assign(value_score=float("inf")),
        config.feature_columns,
    )
    with pytest.raises(ValueError, match="configured features must contain finite"):
        FactorAverageBaselineModel(config).predict(unchecked)
