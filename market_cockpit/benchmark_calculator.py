"""Deterministic close-only benchmark context calculations."""

from __future__ import annotations

from math import isfinite, sqrt

import numpy as np
import pandas as pd

from market_cockpit.benchmark_contracts import BenchmarkCodeMetrics
from market_cockpit.benchmark_repository import PersistedBenchmarkSnapshot


class BenchmarkCalculationError(ValueError):
    """Raised when persisted benchmark data violates the reviewed contract."""


def calculate_benchmark_metrics(
    snapshot: PersistedBenchmarkSnapshot,
) -> tuple[list[BenchmarkCodeMetrics], list[str]]:
    frame = snapshot.benchmark_index_daily.copy()
    if frame.duplicated(["source", "index_code", "trade_date"]).any():
        raise BenchmarkCalculationError("Benchmark snapshot contains duplicate natural keys.")
    frame["trade_date"] = frame["trade_date"].astype(str)
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    if frame["close"].isna().any() or not all(
        isfinite(float(value)) and float(value) > 0 for value in frame["close"]
    ):
        raise BenchmarkCalculationError("Benchmark snapshot contains invalid close values.")
    unexpected = sorted(set(frame["index_code"].astype(str)) - set(snapshot.index_codes))
    if unexpected:
        raise BenchmarkCalculationError(f"Benchmark snapshot contains unexpected codes: {unexpected}.")
    warnings: list[str] = []
    date_sets: dict[str, set[str]] = {}
    metrics: list[BenchmarkCodeMetrics] = []
    for code in snapshot.index_codes:
        code_frame = frame.loc[frame["index_code"].astype(str).eq(code)].sort_values("trade_date")
        dates = code_frame["trade_date"].astype(str).tolist()
        closes = code_frame["close"].astype(float).tolist()
        date_sets[code] = set(dates)
        code_warnings: list[str] = []
        if not closes:
            code_warnings.append(f"Benchmark {code} has no row in the permitted window.")
            metrics.append(BenchmarkCodeMetrics(code, None, None, None, None, None, None, None, None, None, 0, warnings=tuple(code_warnings)))
            warnings.extend(code_warnings)
            continue
        latest_return = closes[-1] / closes[-2] - 1.0 if len(closes) >= 2 else None
        if latest_return is None:
            code_warnings.append(f"Benchmark {code} latest return requires 2 sessions; available={len(closes)}.")
        sma20 = float(np.mean(closes[-20:])) if len(closes) >= 20 else None
        if sma20 is None:
            code_warnings.append(f"Benchmark {code} SMA20 requires 20 sessions; available={len(closes)}.")
        sma60 = float(np.mean(closes[-60:])) if len(closes) >= 60 else None
        if sma60 is None:
            code_warnings.append(f"Benchmark {code} SMA60 requires 60 sessions; available={len(closes)}.")
        volatility = None
        drawdown = None
        if len(closes) >= 21:
            window = np.asarray(closes[-21:], dtype=float)
            returns = window[1:] / window[:-1] - 1.0
            volatility = float(returns.std(ddof=1) * sqrt(252))
            wealth = np.concatenate(([1.0], np.cumprod(1.0 + returns)))
            drawdown = float(np.min(wealth / np.maximum.accumulate(wealth) - 1.0))
        else:
            code_warnings.append(
                f"Benchmark {code} volatility/drawdown requires 21 sessions; available={len(closes)}."
            )
        metrics.append(
            BenchmarkCodeMetrics(
                index_code=code,
                latest_close=float(closes[-1]),
                latest_session=dates[-1],
                latest_return=latest_return,
                sma20=sma20,
                above_sma20=(float(closes[-1]) > sma20) if sma20 is not None else None,
                sma60=sma60,
                above_sma60=(float(closes[-1]) > sma60) if sma60 is not None else None,
                realized_volatility_20=volatility,
                max_drawdown_20=drawdown,
                available_session_count=len(closes),
                warnings=tuple(code_warnings),
            )
        )
        warnings.extend(code_warnings)
    if len({frozenset(values) for values in date_sets.values()}) > 1:
        warnings.append(
            "Benchmark codes have mismatched persisted sessions; each code was calculated only from its own ordered rows."
        )
    return metrics, warnings
