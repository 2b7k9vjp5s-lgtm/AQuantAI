"""Persist deterministic benchmark revisions and render aligned Market Cockpit views."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from backend.database import build_engine, build_session_factory
from backend.database.benchmark_data import BenchmarkPersistenceService
from backend.database.market_data import MarketDataPersistenceService
from market_cockpit.benchmark_fixtures import (
    BENCHMARK_FIXTURE_CODES,
    BENCHMARK_FIXTURE_CURRENT_CUTOFF,
    BENCHMARK_FIXTURE_END_DATE,
    BENCHMARK_FIXTURE_HISTORICAL_CUTOFF,
    BENCHMARK_FIXTURE_PROVIDER,
    BENCHMARK_FIXTURE_SCOPE,
    BENCHMARK_FIXTURE_START_DATE,
    build_benchmark_fixture,
)
from market_cockpit.benchmark_repository import BenchmarkRepository
from market_cockpit.fixtures import (
    COCKPIT_FIXTURE_ADJUST_TYPE,
    COCKPIT_FIXTURE_CURRENT_CUTOFF,
    COCKPIT_FIXTURE_END_DATE,
    COCKPIT_FIXTURE_HISTORICAL_CUTOFF,
    COCKPIT_FIXTURE_PROVIDER,
    COCKPIT_FIXTURE_SCOPE,
    COCKPIT_FIXTURE_START_DATE,
    build_market_cockpit_fixture,
)
from market_cockpit.repository import MarketCockpitRepository
from market_cockpit.service import MarketCockpitService


def build_persisted_benchmark_demo(database_url: str | None = None) -> dict[str, Any]:
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    try:
        equity_service = MarketDataPersistenceService(session_factory)
        benchmark_service = BenchmarkPersistenceService(session_factory)
        equity_historical = _ingest_equity(equity_service, "historical", COCKPIT_FIXTURE_HISTORICAL_CUTOFF)
        equity_current = _ingest_equity(equity_service, "current", COCKPIT_FIXTURE_CURRENT_CUTOFF)
        benchmark_historical = _ingest_benchmark(
            benchmark_service, "historical", BENCHMARK_FIXTURE_HISTORICAL_CUTOFF
        )
        benchmark_current = _ingest_benchmark(
            benchmark_service, "current", BENCHMARK_FIXTURE_CURRENT_CUTOFF
        )
        with session_factory() as session:
            service = MarketCockpitService(
                MarketCockpitRepository(session),
                benchmark_repository=BenchmarkRepository(session),
                clock=lambda: datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc),
            )
            current = service.build_snapshot(
                series_key=equity_current.series_key,
                benchmark_series_key=benchmark_current.series_key,
            ).to_dict()
            historical = service.build_snapshot(
                series_key=equity_historical.series_key,
                benchmark_series_key=benchmark_historical.series_key,
                as_of_cutoff=BENCHMARK_FIXTURE_HISTORICAL_CUTOFF,
            ).to_dict()
        return {
            "equity_series_key": equity_current.series_key,
            "benchmark_series_key": benchmark_current.series_key,
            "benchmark_codes": BENCHMARK_FIXTURE_CODES,
            "current": _summary(current),
            "historical": _summary(historical),
            "read_only": True,
            "network_access": False,
        }
    finally:
        engine.dispose()


def _ingest_equity(service: MarketDataPersistenceService, revision: str, cutoff: str):
    return service.ingest_bundle(
        build_market_cockpit_fixture(revision=revision),
        provider=COCKPIT_FIXTURE_PROVIDER,
        requested_start_date=COCKPIT_FIXTURE_START_DATE,
        requested_end_date=COCKPIT_FIXTURE_END_DATE,
        information_cutoff_date=cutoff,
        requested_scope=COCKPIT_FIXTURE_SCOPE,
        adjust_type=COCKPIT_FIXTURE_ADJUST_TYPE,
        adapter_version="market-cockpit-fixture-v1",
    )


def _ingest_benchmark(service: BenchmarkPersistenceService, revision: str, cutoff: str):
    return service.ingest_bundle(
        build_benchmark_fixture(revision=revision),
        provider=BENCHMARK_FIXTURE_PROVIDER,
        requested_start_date=BENCHMARK_FIXTURE_START_DATE,
        requested_end_date=BENCHMARK_FIXTURE_END_DATE,
        information_cutoff_date=cutoff,
        requested_scope=BENCHMARK_FIXTURE_SCOPE,
        endpoint="fixture_index_history",
        adapter_compatibility_version="benchmark-fixture-v1",
        adapter_version="benchmark-fixture-v1",
        provider_request_metadata={
            "collection_timestamp_utc": f"2026-04-{cutoff[-2:]}T12:00:00Z",
            "effective_information_cutoff_date": cutoff,
            "network_mode": "offline-fixture",
            "timeout_seconds": 1.0,
            "max_retries": 0,
        },
    )


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    context = payload["benchmark_context"]
    return {
        "equity_ingestion_run_id": payload["provenance"]["ingestion_run_id"],
        "benchmark_ingestion_run_id": context["provenance"]["ingestion_run_id"],
        "benchmark_information_cutoff": context["provenance"]["information_cutoff_date"],
        "benchmark_effective_session": context["provenance"]["effective_benchmark_session"],
        "alignment_status": context["alignment_status"],
        "metrics": context["metrics"],
    }


def main() -> None:
    print(json.dumps(build_persisted_benchmark_demo(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
