"""Production-boundary offline demo for the local-only Today Market slice."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.today_market import (
    TodayMarketBoundaries,
    TodayMarketSnapshotRequest,
    _build_catalog,
    today_market_snapshot,
)
from backend.database.benchmark_data import BenchmarkPersistenceService
from backend.database.engine import build_session_factory
from backend.database.market_data import MarketDataPersistenceService
from backend.database.models import Base, IngestionRun
from backend.database.sector_data import (
    DEFAULT_SECTOR_REVIEWED_AKSHARE_VERSION,
    SECTOR_DAILY_CONTRACT_VERSION,
    SECTOR_DEFINITION_CONTRACT_VERSION,
    SectorPersistenceService,
)
from market_cockpit.benchmark_fixtures import (
    BENCHMARK_FIXTURE_CURRENT_CUTOFF,
    BENCHMARK_FIXTURE_END_DATE,
    BENCHMARK_FIXTURE_PROVIDER,
    BENCHMARK_FIXTURE_SCOPE,
    BENCHMARK_FIXTURE_START_DATE,
    build_benchmark_fixture,
)
from market_cockpit.fixtures import (
    COCKPIT_FIXTURE_ADJUST_TYPE,
    COCKPIT_FIXTURE_CURRENT_CUTOFF,
    COCKPIT_FIXTURE_END_DATE,
    COCKPIT_FIXTURE_PROVIDER,
    COCKPIT_FIXTURE_SCOPE,
    COCKPIT_FIXTURE_START_DATE,
    build_market_cockpit_fixture,
)
from market_cockpit.sector_fixtures import (
    SECTOR_FIXTURE_CURRENT_CUTOFF,
    SECTOR_FIXTURE_END_DATE,
    SECTOR_FIXTURE_PROVIDER,
    SECTOR_FIXTURE_SCOPE,
    SECTOR_FIXTURE_START_DATE,
    build_sector_fixture,
)


VISIBLE_AT = datetime(2026, 4, 6, 12, 0, tzinfo=timezone.utc)
EARLY_BOUNDARY = datetime(2026, 4, 6, 11, 59, 59, tzinfo=timezone.utc)


def build_today_market_demo() -> dict[str, Any]:
    """Persist deterministic fixtures, then prove normal and not-visible reads."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)
    try:
        equity = _ingest_equity(session_factory)
        benchmark = _ingest_benchmark(session_factory)
        sector = _ingest_sector(session_factory)
        _fix_recorded_times(
            session_factory,
            equity.ingestion_run_id,
            benchmark.ingestion_run_id,
            sector.ingestion_run_id,
        )
        boundaries = _boundaries(VISIBLE_AT)
        with session_factory() as session:
            catalog = _build_catalog(session, boundaries)
        request = TodayMarketSnapshotRequest(
            equity_series_key=equity.series_key,
            benchmark_series_key=benchmark.series_key,
            sector_series_key=sector.series_key,
            boundaries=boundaries,
        )
        snapshot = today_market_snapshot(
            request=request,
            session_factory=session_factory,
        )
        early_failure = _early_failure(
            session_factory,
            equity.series_key,
            benchmark.series_key,
            sector.series_key,
        )
        return {
            "catalog_counts": {
                family: len(values)
                for family, values in catalog["families"].items()
            },
            "catalog_auto_selected": catalog["auto_selected"],
            "snapshot_status": snapshot["status"],
            "coverage_notice": snapshot["scope_and_freshness"]["coverage_notice"],
            "effective_equity_session": snapshot["scope_and_freshness"][
                "effective_equity_session"
            ],
            "benchmark_selected": snapshot["scope_and_freshness"][
                "benchmark_selected"
            ],
            "sector_selected": snapshot["scope_and_freshness"]["sector_selected"],
            "unavailable_sections": [
                item["key"] for item in snapshot["unavailable_sections"]
            ],
            "early_boundary_failure": early_failure,
            "read_only": snapshot["read_only"],
            "network_access": False,
            "ai_calls": False,
        }
    finally:
        engine.dispose()


def _boundaries(recorded_at: datetime) -> TodayMarketBoundaries:
    return TodayMarketBoundaries(
        cutoff=date(2026, 4, 5),
        cutoff_compact="20260405",
        recorded_at=recorded_at,
        recorded_at_iso=recorded_at.isoformat().replace("+00:00", "Z"),
    )


def _early_failure(
    session_factory: sessionmaker[Session],
    equity_key: str,
    benchmark_key: str,
    sector_key: str,
) -> dict[str, Any]:
    try:
        today_market_snapshot(
            request=TodayMarketSnapshotRequest(
                equity_series_key=equity_key,
                benchmark_series_key=benchmark_key,
                sector_series_key=sector_key,
                boundaries=_boundaries(EARLY_BOUNDARY),
            ),
            session_factory=session_factory,
        )
    except HTTPException as exc:
        return {
            "status_code": exc.status_code,
            "code": exc.detail["code"],
            "fallback_used": False,
        }
    raise AssertionError("early recorded boundary must fail closed")


def _fix_recorded_times(
    session_factory: sessionmaker[Session],
    *run_ids: int,
) -> None:
    with session_factory.begin() as session:
        for run_id in run_ids:
            run = session.get(IngestionRun, run_id)
            if run is None:
                raise RuntimeError(f"fixture run {run_id} disappeared")
            run.imported_at = datetime(2026, 4, 6, 10, 0, tzinfo=timezone.utc)
            run.completed_at = VISIBLE_AT


def _ingest_equity(session_factory: sessionmaker[Session]):
    return MarketDataPersistenceService(session_factory).ingest_bundle(
        build_market_cockpit_fixture(),
        provider=COCKPIT_FIXTURE_PROVIDER,
        requested_start_date=COCKPIT_FIXTURE_START_DATE,
        requested_end_date=COCKPIT_FIXTURE_END_DATE,
        information_cutoff_date=COCKPIT_FIXTURE_CURRENT_CUTOFF,
        requested_scope=COCKPIT_FIXTURE_SCOPE,
        adjust_type=COCKPIT_FIXTURE_ADJUST_TYPE,
        compatibility_parameters={
            "stock_basic_endpoint": "fixture_stock_basic",
            "daily_price_endpoint": "fixture_daily_price",
            "trade_calendar_endpoint": "fixture_trade_calendar",
            "frequency": "daily",
            "adapter_compatibility_version": "today-market-demo-v1",
        },
        provider_request_metadata={
            "collection_timestamp_utc": "2026-04-05T12:00:00Z",
            "effective_information_cutoff_date": COCKPIT_FIXTURE_CURRENT_CUTOFF,
        },
        adapter_version="today-market-demo-v1",
    )


def _ingest_benchmark(session_factory: sessionmaker[Session]):
    return BenchmarkPersistenceService(session_factory).ingest_bundle(
        build_benchmark_fixture(),
        provider=BENCHMARK_FIXTURE_PROVIDER,
        requested_start_date=BENCHMARK_FIXTURE_START_DATE,
        requested_end_date=BENCHMARK_FIXTURE_END_DATE,
        information_cutoff_date=BENCHMARK_FIXTURE_CURRENT_CUTOFF,
        requested_scope=BENCHMARK_FIXTURE_SCOPE,
        endpoint="fixture_benchmark_history",
        adapter_compatibility_version="today-market-demo-v1",
        provider_request_metadata={"network_mode": "offline-fixture"},
        adapter_version="today-market-demo-v1",
    )


def _ingest_sector(session_factory: sessionmaker[Session]):
    return SectorPersistenceService(session_factory).ingest_bundle(
        build_sector_fixture(),
        provider=SECTOR_FIXTURE_PROVIDER,
        requested_start_date=SECTOR_FIXTURE_START_DATE,
        requested_end_date=SECTOR_FIXTURE_END_DATE,
        information_cutoff_date=SECTOR_FIXTURE_CURRENT_CUTOFF,
        requested_scope=SECTOR_FIXTURE_SCOPE,
        taxonomy_endpoint="fixture_sector_taxonomy",
        history_endpoint="fixture_sector_history",
        adapter_compatibility_version="today-market-demo-v1",
        provider_request_metadata={
            "taxonomy_endpoint": "fixture_sector_taxonomy",
            "history_endpoint": "fixture_sector_history",
            "classification_system": "eastmoney_industry_board",
            "classification_level": None,
            "frequency": "daily",
            "adjust_type": "",
            "sector_codes": list(SECTOR_FIXTURE_SCOPE["sector_codes"]),
            "start_date": SECTOR_FIXTURE_START_DATE,
            "end_date": SECTOR_FIXTURE_END_DATE,
            "network_mode": "offline-fixture",
            "timeout_seconds": 1.0,
            "max_retries": 0,
            "akshare_package_version": DEFAULT_SECTOR_REVIEWED_AKSHARE_VERSION,
            "definition_contract_version": SECTOR_DEFINITION_CONTRACT_VERSION,
            "daily_contract_version": SECTOR_DAILY_CONTRACT_VERSION,
            "adapter_version": "today-market-demo-v1",
            "adapter_compatibility_version": "today-market-demo-v1",
            "collection_timestamp_utc": "2026-04-05T12:00:00Z",
            "effective_information_cutoff_date": SECTOR_FIXTURE_CURRENT_CUTOFF,
        },
        adapter_version="today-market-demo-v1",
    )


def main() -> None:
    print(json.dumps(build_today_market_demo(), indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
