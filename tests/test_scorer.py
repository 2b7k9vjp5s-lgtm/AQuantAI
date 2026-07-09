import pandas as pd
import pytest

from factors import FACTOR_SCORE_COLUMNS, FactorDefinition
from ranking.scorer import (
    DEFAULT_GROUP_WEIGHTS,
    build_group_composite_scores,
    build_total_composite_scores,
    score_factor_values,
)


def test_score_factor_values_handles_direction_and_missing_values() -> None:
    values = pd.DataFrame(
        [
            {"factor_date": "20260630", "stock_code": "000001", "factor_name": "pe_inverse", "factor_value": 0.10, "factor_group": "value"},
            {"factor_date": "20260630", "stock_code": "000002", "factor_name": "pe_inverse", "factor_value": 0.05, "factor_group": "value"},
            {"factor_date": "20260630", "stock_code": "000003", "factor_name": "pe_inverse", "factor_value": None, "factor_group": "value"},
            {"factor_date": "20260630", "stock_code": "000001", "factor_name": "volatility_20d", "factor_value": 0.30, "factor_group": "risk"},
            {"factor_date": "20260630", "stock_code": "000002", "factor_name": "volatility_20d", "factor_value": 0.10, "factor_group": "risk"},
        ]
    )
    definitions = {
        "pe_inverse": FactorDefinition("pe_inverse", "value", "descending"),
        "volatility_20d": FactorDefinition("volatility_20d", "risk", "ascending"),
    }

    result = score_factor_values(values, definitions, universe="test")

    assert list(result.columns) == FACTOR_SCORE_COLUMNS
    assert result["score"].between(0, 100).all()
    assert result.loc[(result["factor_name"] == "pe_inverse") & (result["stock_code"] == "000001"), "score"].iloc[0] == 100
    assert result.loc[(result["factor_name"] == "volatility_20d") & (result["stock_code"] == "000001"), "score"].iloc[0] == 50
    assert result.loc[(result["factor_name"] == "volatility_20d") & (result["stock_code"] == "000002"), "score"].iloc[0] == 100
    assert result.loc[(result["factor_name"] == "pe_inverse") & (result["stock_code"] == "000003"), "score"].iloc[0] == 50
    assert set(result["universe"]) == {"test"}


def test_group_and_total_composite_scores_use_configured_weights() -> None:
    factor_scores = pd.DataFrame(
        [
            {"score_date": "20260630", "stock_code": "000001", "factor_name": "pe_inverse", "factor_group": "value", "score": 80.0, "rank": 1, "universe": "test"},
            {"score_date": "20260630", "stock_code": "000001", "factor_name": "pb_inverse", "factor_group": "value", "score": 60.0, "rank": 2, "universe": "test"},
            {"score_date": "20260630", "stock_code": "000001", "factor_name": "revenue_growth", "factor_group": "growth", "score": 50.0, "rank": 1, "universe": "test"},
            {"score_date": "20260630", "stock_code": "000001", "factor_name": "roe", "factor_group": "quality", "score": 90.0, "rank": 1, "universe": "test"},
            {"score_date": "20260630", "stock_code": "000001", "factor_name": "return_20d", "factor_group": "momentum", "score": 40.0, "rank": 2, "universe": "test"},
            {"score_date": "20260630", "stock_code": "000001", "factor_name": "volatility_20d", "factor_group": "risk", "score": 30.0, "rank": 2, "universe": "test"},
        ]
    )

    group_scores = build_group_composite_scores(factor_scores, universe="test")
    total_scores = build_total_composite_scores(group_scores, universe="test")

    assert set(group_scores["factor_name"]) == {
        "composite:value",
        "composite:growth",
        "composite:quality",
        "composite:momentum",
        "composite:risk",
    }
    expected_total = 70 * 0.25 + 50 * 0.25 + 90 * 0.20 + 40 * 0.20 + 30 * 0.10
    assert total_scores.iloc[0]["score"] == pytest.approx(expected_total)
    assert sum(DEFAULT_GROUP_WEIGHTS.values()) == pytest.approx(1.0)


def test_total_composite_rejects_invalid_weights() -> None:
    group_scores = pd.DataFrame(
        [
            {"score_date": "20260630", "stock_code": "000001", "factor_name": "composite:value", "factor_group": "value", "score": 80.0, "rank": 1, "universe": "test"}
        ]
    )

    with pytest.raises(ValueError, match="Composite weights must sum"):
        build_total_composite_scores(group_scores, weights={"value": 0.5})
