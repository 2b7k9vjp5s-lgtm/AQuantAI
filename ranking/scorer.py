"""Factor scoring and composite score utilities."""

from __future__ import annotations

import pandas as pd

from factors.base import FACTOR_SCORE_COLUMNS, FactorDefinition

DEFAULT_GROUP_WEIGHTS = {
    "value": 0.25,
    "growth": 0.25,
    "quality": 0.20,
    "momentum": 0.20,
    "risk": 0.10,
}


def score_factor_values(
    factor_values: pd.DataFrame,
    definitions: dict[str, FactorDefinition],
    universe: str = "default",
) -> pd.DataFrame:
    """Convert factor values to 0-100 percentile scores."""
    required = {"factor_date", "stock_code", "factor_name", "factor_value", "factor_group"}
    missing = required - set(factor_values.columns)
    if missing:
        raise ValueError(f"Missing required score input columns: {sorted(missing)}")

    scored_frames = []
    for factor_name, frame in factor_values.groupby("factor_name", sort=False):
        definition = definitions[factor_name]
        scored = frame.copy()
        scored["score"] = _percentile_score(scored["factor_value"], definition.direction)
        scored["rank"] = scored["score"].rank(method="min", ascending=False).astype(int)
        scored["score_date"] = scored["factor_date"].astype(str)
        scored["universe"] = universe
        scored_frames.append(scored[FACTOR_SCORE_COLUMNS])

    if not scored_frames:
        return pd.DataFrame(columns=FACTOR_SCORE_COLUMNS)
    return pd.concat(scored_frames, ignore_index=True)


def build_group_composite_scores(factor_scores: pd.DataFrame, universe: str = "default") -> pd.DataFrame:
    """Average factor scores within each group for each stock."""
    if factor_scores.empty:
        return pd.DataFrame(columns=FACTOR_SCORE_COLUMNS)

    grouped = (
        factor_scores.groupby(["score_date", "stock_code", "factor_group"], as_index=False)["score"]
        .mean()
        .rename(columns={"score": "score"})
    )
    grouped["factor_name"] = "composite:" + grouped["factor_group"]
    grouped["rank"] = grouped.groupby(["score_date", "factor_group"])["score"].rank(method="min", ascending=False).astype(int)
    grouped["universe"] = universe
    return grouped[FACTOR_SCORE_COLUMNS]


def build_total_composite_scores(
    group_scores: pd.DataFrame,
    weights: dict[str, float] | None = None,
    universe: str = "default",
) -> pd.DataFrame:
    """Build a weighted total score from group composite scores."""
    if group_scores.empty:
        return pd.DataFrame(columns=FACTOR_SCORE_COLUMNS)

    active_weights = weights or DEFAULT_GROUP_WEIGHTS
    _validate_weights(active_weights)
    frame = group_scores.copy()
    frame["weight"] = frame["factor_group"].map(active_weights).fillna(0.0)
    frame["weighted_score"] = frame["score"] * frame["weight"]
    total = frame.groupby(["score_date", "stock_code"], as_index=False)["weighted_score"].sum()
    total = total.rename(columns={"weighted_score": "score"})
    total["factor_name"] = "composite:total"
    total["factor_group"] = "total"
    total["rank"] = total.groupby("score_date")["score"].rank(method="min", ascending=False).astype(int)
    total["universe"] = universe
    return total[FACTOR_SCORE_COLUMNS]


def _percentile_score(values: pd.Series, direction: str) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.notna().sum() == 0:
        return pd.Series(50.0, index=values.index)

    ascending = direction == "descending"
    scores = numeric.rank(method="average", pct=True, ascending=ascending) * 100
    return scores.fillna(50.0).clip(lower=0, upper=100)


def _validate_weights(weights: dict[str, float]) -> None:
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"Composite weights must sum to 1.0, got {total}")
