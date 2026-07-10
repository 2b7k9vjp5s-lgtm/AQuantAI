"""Factor scoring and composite score utilities."""

from __future__ import annotations

import numpy as np
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
    """Convert factor values to deterministic 0-100 percentile scores."""
    required = {"factor_date", "stock_code", "factor_name", "factor_value", "factor_group"}
    missing = required - set(factor_values.columns)
    if missing:
        raise ValueError(f"Missing required score input columns: {sorted(missing)}")

    frame = _with_universe(factor_values, universe)
    frame["factor_date"] = frame["factor_date"].astype(str)
    frame["stock_code"] = frame["stock_code"].astype(str)
    _reject_duplicates(frame, ["factor_date", "stock_code", "factor_name", "universe"], "factor values")
    _validate_factor_values(frame["factor_value"])

    scored_frames = []
    for (factor_date, factor_name, factor_universe), group in frame.groupby(
        ["factor_date", "factor_name", "universe"], sort=True
    ):
        if factor_name not in definitions:
            raise ValueError(f"Missing definition for factor: {factor_name}")
        definition = definitions[factor_name]
        if not (group["factor_group"] == definition.group).all():
            raise ValueError(f"factor_group does not match definition for factor: {factor_name}")
        scored = group.copy()
        scored["score"] = _percentile_score(scored["factor_value"], definition.direction)
        scored["score_date"] = factor_date
        scored["universe"] = factor_universe
        scored = _assign_deterministic_rank(scored, ["score_date", "factor_name", "universe"])
        scored_frames.append(scored[FACTOR_SCORE_COLUMNS])

    if not scored_frames:
        return pd.DataFrame(columns=FACTOR_SCORE_COLUMNS)
    return pd.concat(scored_frames, ignore_index=True).sort_values(
        ["score_date", "universe", "factor_name", "rank", "stock_code"]
    ).reset_index(drop=True)


def build_group_composite_scores(factor_scores: pd.DataFrame, universe: str = "default") -> pd.DataFrame:
    """Average factor scores within each date, universe, group, and stock."""
    if factor_scores.empty:
        return pd.DataFrame(columns=FACTOR_SCORE_COLUMNS)

    required = {"score_date", "stock_code", "factor_name", "factor_group", "score"}
    missing = required - set(factor_scores.columns)
    if missing:
        raise ValueError(f"Missing required factor score columns: {sorted(missing)}")
    frame = _with_universe(factor_scores, universe)
    frame["score_date"] = frame["score_date"].astype(str)
    frame["stock_code"] = frame["stock_code"].astype(str)
    _reject_duplicates(frame, ["score_date", "stock_code", "factor_name", "universe"], "factor scores")
    _validate_finite(frame["score"], "factor scores")

    grouped = (
        frame.groupby(["score_date", "stock_code", "factor_group", "universe"], as_index=False)["score"]
        .mean()
    )
    grouped["factor_name"] = "composite:" + grouped["factor_group"]
    grouped = _assign_deterministic_rank(grouped, ["score_date", "factor_group", "universe"])
    return grouped[FACTOR_SCORE_COLUMNS].sort_values(
        ["score_date", "universe", "factor_group", "rank", "stock_code"]
    ).reset_index(drop=True)


def build_total_composite_scores(
    group_scores: pd.DataFrame,
    weights: dict[str, float] | None = None,
    universe: str = "default",
) -> pd.DataFrame:
    """Build a weighted total score isolated by score date and universe."""
    if group_scores.empty:
        return pd.DataFrame(columns=FACTOR_SCORE_COLUMNS)

    required = {"score_date", "stock_code", "factor_group", "score"}
    missing = required - set(group_scores.columns)
    if missing:
        raise ValueError(f"Missing required group score columns: {sorted(missing)}")
    active_weights = weights or DEFAULT_GROUP_WEIGHTS
    _validate_weights(active_weights)

    frame = _with_universe(group_scores, universe)
    frame["score_date"] = frame["score_date"].astype(str)
    frame["stock_code"] = frame["stock_code"].astype(str)
    _reject_duplicates(frame, ["score_date", "stock_code", "factor_group", "universe"], "group scores")
    _validate_finite(frame["score"], "group scores")
    frame["weight"] = frame["factor_group"].map(active_weights).fillna(0.0)
    frame["weighted_score"] = frame["score"] * frame["weight"]
    total = frame.groupby(["score_date", "stock_code", "universe"], as_index=False)["weighted_score"].sum()
    total = total.rename(columns={"weighted_score": "score"})
    total["factor_name"] = "composite:total"
    total["factor_group"] = "total"
    total = _assign_deterministic_rank(total, ["score_date", "universe"])
    return total[FACTOR_SCORE_COLUMNS].sort_values(
        ["score_date", "universe", "rank", "stock_code"]
    ).reset_index(drop=True)


def _with_universe(frame: pd.DataFrame, default_universe: str) -> pd.DataFrame:
    normalized = frame.copy()
    if "universe" not in normalized.columns:
        normalized["universe"] = default_universe
    if normalized["universe"].isna().any():
        raise ValueError("universe must not be missing")
    normalized["universe"] = normalized["universe"].astype(str)
    if normalized["universe"].eq("").any():
        raise ValueError("universe must not be empty")
    return normalized


def _assign_deterministic_rank(frame: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    ordered = frame.sort_values(
        [*group_columns, "score", "stock_code"],
        ascending=[*[True] * len(group_columns), False, True],
        kind="stable",
    ).copy()
    ordered["rank"] = ordered.groupby(group_columns, sort=False).cumcount() + 1
    return ordered


def _percentile_score(values: pd.Series, direction: str) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.notna().sum() == 0:
        return pd.Series(50.0, index=values.index)

    ascending = direction == "descending"
    scores = numeric.rank(method="average", pct=True, ascending=ascending) * 100
    return scores.fillna(50.0).clip(lower=0, upper=100)


def _validate_factor_values(values: pd.Series) -> None:
    numeric = pd.to_numeric(values, errors="coerce")
    if values.notna().any() and numeric[values.notna()].isna().any():
        raise ValueError("factor values must be numeric or missing")
    if np.isinf(numeric.dropna()).any():
        raise ValueError("factor values must be finite")


def _validate_finite(values: pd.Series, frame_name: str) -> None:
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.isna().any() or not np.isfinite(numeric).all():
        raise ValueError(f"{frame_name} must contain finite numeric scores")


def _reject_duplicates(frame: pd.DataFrame, columns: list[str], frame_name: str) -> None:
    if frame.duplicated(columns).any():
        raise ValueError(f"{frame_name} contains duplicate rows for {columns}")


def _validate_weights(weights: dict[str, float]) -> None:
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"Composite weights must sum to 1.0, got {total}")
