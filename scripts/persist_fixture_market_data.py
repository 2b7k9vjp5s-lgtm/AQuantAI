"""Persist deterministic local market-data fixtures without network access."""

from __future__ import annotations

import json
from typing import Any

from backend.database import build_engine, build_session_factory
from backend.database.market_data import MarketDataPersistenceService, MarketDataRepository
from datasource.fixtures import (
    FIXTURE_CUTOFF_DATE,
    FIXTURE_END_DATE,
    FIXTURE_PROVIDER,
    FIXTURE_SCOPE,
    FIXTURE_START_DATE,
    build_market_data_fixture,
)


def persist_fixture_market_data(database_url: str | None = None) -> dict[str, Any]:
    """Persist and read back the local fixture bundle using an existing schema."""
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    try:
        result = MarketDataPersistenceService(session_factory).ingest_bundle(
            build_market_data_fixture(),
            provider=FIXTURE_PROVIDER,
            requested_start_date=FIXTURE_START_DATE,
            requested_end_date=FIXTURE_END_DATE,
            information_cutoff_date=FIXTURE_CUTOFF_DATE,
            requested_scope=FIXTURE_SCOPE,
        )
        with session_factory() as session:
            repository = MarketDataRepository(session)
            readback_counts = {
                "stock_basic": len(repository.read_stock_basic(FIXTURE_PROVIDER)),
                "daily_price": len(repository.read_daily_price(FIXTURE_PROVIDER)),
                "trade_calendar": len(repository.read_trade_calendar(FIXTURE_PROVIDER)),
            }
        payload = result.to_dict()
        payload["provider"] = FIXTURE_PROVIDER
        payload["readback_counts"] = readback_counts
        return payload
    finally:
        engine.dispose()


def main() -> None:
    print(json.dumps(persist_fixture_market_data(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
