"""Deterministic benchmark-index fixtures with no network access."""

from __future__ import annotations

import pandas as pd

from datasource.base import BenchmarkIndexBundle

BENCHMARK_FIXTURE_PROVIDER = "fixture"
BENCHMARK_FIXTURE_CODES = ["000001", "000300"]
BENCHMARK_FIXTURE_DATES = pd.bdate_range("2026-01-05", periods=65).strftime("%Y%m%d").tolist()
BENCHMARK_FIXTURE_START_DATE = BENCHMARK_FIXTURE_DATES[0]
BENCHMARK_FIXTURE_END_DATE = BENCHMARK_FIXTURE_DATES[-1]
BENCHMARK_FIXTURE_HISTORICAL_CUTOFF = "20260404"
BENCHMARK_FIXTURE_CURRENT_CUTOFF = "20260405"
BENCHMARK_FIXTURE_SCOPE = {
    "datasets": ["benchmark_index_daily"],
    "index_codes": BENCHMARK_FIXTURE_CODES,
    "index_code_semantics": "exact",
}


def build_benchmark_fixture(*, revision: str = "current") -> BenchmarkIndexBundle:
    if revision not in {"historical", "current"}:
        raise ValueError("revision must be 'historical' or 'current'.")
    rows: list[dict] = []
    for code_index, code in enumerate(BENCHMARK_FIXTURE_CODES, start=1):
        closes = [1000.0 * code_index + index * code_index for index in range(65)]
        multiplier = 1.02 if revision == "historical" else 1.03
        if code == "000300":
            multiplier = 0.99 if revision == "historical" else 0.98
        closes[-1] = closes[-2] * multiplier
        for index, trade_date in enumerate(BENCHMARK_FIXTURE_DATES):
            close = closes[index]
            rows.append(
                {
                    "source": BENCHMARK_FIXTURE_PROVIDER,
                    "index_code": code,
                    "trade_date": trade_date,
                    "open": close - 0.5,
                    "high": close + 1.0,
                    "low": close - 1.0,
                    "close": close,
                    "volume": 100000.0 * code_index + index,
                    "amount": 100000000.0 * code_index + index * 1000,
                }
            )
    return BenchmarkIndexBundle(benchmark_index_daily=pd.DataFrame(rows))
