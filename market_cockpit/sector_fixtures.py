"""Deterministic sector fixtures with no network access."""

from __future__ import annotations

import pandas as pd

from datasource.base import SectorMarketBundle

SECTOR_FIXTURE_PROVIDER = "fixture"
SECTOR_FIXTURE_CODES = ["BK0001", "BK0002"]
SECTOR_FIXTURE_NAMES = {
    "BK0001": "Fixture Industry One",
    "BK0002": "Fixture Industry Two",
}
SECTOR_FIXTURE_DATES = pd.bdate_range("2026-01-05", periods=65).strftime("%Y%m%d").tolist()
SECTOR_FIXTURE_START_DATE = SECTOR_FIXTURE_DATES[0]
SECTOR_FIXTURE_END_DATE = SECTOR_FIXTURE_DATES[-1]
SECTOR_FIXTURE_HISTORICAL_CUTOFF = "20260404"
SECTOR_FIXTURE_CURRENT_CUTOFF = "20260405"
SECTOR_FIXTURE_SCOPE = {
    "datasets": ["sector_definition", "sector_daily"],
    "sector_codes": SECTOR_FIXTURE_CODES,
    "sector_code_semantics": "exact",
    "classification_system": "eastmoney_industry_board",
    "classification_level": None,
}


def build_sector_fixture(*, revision: str = "current") -> SectorMarketBundle:
    if revision not in {"historical", "current"}:
        raise ValueError("revision must be 'historical' or 'current'.")
    definitions = pd.DataFrame([
        {
            "source": SECTOR_FIXTURE_PROVIDER,
            "sector_code": code,
            "sector_name": SECTOR_FIXTURE_NAMES[code],
            "classification_system": "eastmoney_industry_board",
            "classification_level": None,
            "parent_sector_code": None,
            "parent_sector_name": None,
        }
        for code in SECTOR_FIXTURE_CODES
    ])
    rows: list[dict] = []
    for code_index, code in enumerate(SECTOR_FIXTURE_CODES, start=1):
        closes = [1000.0 * code_index + index * code_index for index in range(65)]
        if code == "BK0001":
            closes[-1] = closes[-2] * (1.03 if revision == "current" else 1.02)
        else:
            closes[-1] = closes[-2] * (0.97 if revision == "current" else 0.98)
        for index, trade_date in enumerate(SECTOR_FIXTURE_DATES):
            close = closes[index]
            rows.append({
                "source": SECTOR_FIXTURE_PROVIDER,
                "sector_code": code,
                "trade_date": trade_date,
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 100000.0 * code_index + index,
                "amount": 100000000.0 * code_index + index * 1000,
                "turnover_rate": 1.0 + index / 1000,
            })
    return SectorMarketBundle(
        sector_definition=definitions,
        sector_daily=pd.DataFrame(rows),
    )
