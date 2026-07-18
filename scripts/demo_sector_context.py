"""Persist deterministic sector revisions and render aligned Market Cockpit views."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from backend.database import build_engine, build_session_factory
from backend.database.market_data import MarketDataPersistenceService
from backend.database.sector_data import SectorPersistenceService
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
from market_cockpit.sector_fixtures import (
    SECTOR_FIXTURE_CODES,
    SECTOR_FIXTURE_CURRENT_CUTOFF,
    SECTOR_FIXTURE_END_DATE,
    SECTOR_FIXTURE_HISTORICAL_CUTOFF,
    SECTOR_FIXTURE_PROVIDER,
    SECTOR_FIXTURE_SCOPE,
    SECTOR_FIXTURE_START_DATE,
    build_sector_fixture,
)
from market_cockpit.sector_repository import SectorRepository
from market_cockpit.service import MarketCockpitService


def build_persisted_sector_demo(database_url: str | None = None) -> dict[str, Any]:
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    try:
        equity_service = MarketDataPersistenceService(session_factory)
        sector_service = SectorPersistenceService(session_factory)
        equity_historical = _ingest_equity(
            equity_service, "historical", COCKPIT_FIXTURE_HISTORICAL_CUTOFF
        )
        equity_current = _ingest_equity(
            equity_service, "current", COCKPIT_FIXTURE_CURRENT_CUTOFF
        )
        sector_historical = _ingest_sector(
            sector_service, "historical", SECTOR_FIXTURE_HISTORICAL_CUTOFF
        )
        sector_current = _ingest_sector(
            sector_service, "current", SECTOR_FIXTURE_CURRENT_CUTOFF
        )
        with session_factory() as session:
            service = MarketCockpitService(
                MarketCockpitRepository(session),
                sector_repository=SectorRepository(session),
                clock=lambda: datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc),
            )
            current = service.build_snapshot(
                series_key=equity_current.series_key,
                sector_series_key=sector_current.series_key,
            ).to_dict()
            historical = service.build_snapshot(
                series_key=equity_historical.series_key,
                sector_series_key=sector_historical.series_key,
                as_of_cutoff=SECTOR_FIXTURE_HISTORICAL_CUTOFF,
            ).to_dict()
        return {
            "equity_series_key": equity_current.series_key,
            "sector_series_key": sector_current.series_key,
            "sector_codes": SECTOR_FIXTURE_CODES,
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


def _ingest_sector(service: SectorPersistenceService, revision: str, cutoff: str):
    return service.ingest_bundle(
        build_sector_fixture(revision=revision),
        provider=SECTOR_FIXTURE_PROVIDER,
        requested_start_date=SECTOR_FIXTURE_START_DATE,
        requested_end_date=SECTOR_FIXTURE_END_DATE,
        information_cutoff_date=cutoff,
        requested_scope=SECTOR_FIXTURE_SCOPE,
        taxonomy_endpoint="fixture_sector_taxonomy",
        history_endpoint="fixture_sector_history",
        adapter_compatibility_version="sector-fixture-v1",
        adapter_version="sector-fixture-v1",
        provider_request_metadata={
            "taxonomy_endpoint": "fixture_sector_taxonomy",
            "history_endpoint": "fixture_sector_history",
            "classification_system": "eastmoney_industry_board",
            "classification_level": None,
            "frequency": "daily",
            "adjust_type": "",
            "sector_codes": list(SECTOR_FIXTURE_CODES),
            "start_date": SECTOR_FIXTURE_START_DATE,
            "end_date": SECTOR_FIXTURE_END_DATE,
            "collection_timestamp_utc": f"2026-04-{cutoff[-2:]}T12:00:00Z",
            "effective_information_cutoff_date": cutoff,
            "network_mode": "offline-fixture",
            "timeout_seconds": 1.0,
            "max_retries": 0,
            "akshare_package_version": "1.18.64",
            "definition_contract_version": "1.0",
            "daily_contract_version": "1.0",
            "adapter_version": "sector-fixture-v1",
            "adapter_compatibility_version": "sector-fixture-v1",
        },
    )


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    context = payload["sector_context"]
    return {
        "equity_ingestion_run_id": payload["provenance"]["ingestion_run_id"],
        "sector_ingestion_run_id": context["provenance"]["ingestion_run_id"],
        "sector_information_cutoff": context["provenance"]["information_cutoff_date"],
        "sector_effective_session": context["provenance"]["effective_sector_session"],
        "alignment_status": context["alignment_status"],
        "session_alignment_status": context["session_alignment_status"],
        "cutoff_alignment_status": context["cutoff_alignment_status"],
        "requested_sector_count": context["requested_sector_count"],
        "available_sector_count": context["available_sector_count"],
        "aligned_sector_count": context["aligned_sector_count"],
        "missing_sector_codes": context["missing_sector_codes"],
        "expected_session_source": context["expected_session_source"],
        "expected_session_count": context["expected_session_count"],
        "expected_session_range": [
            context["expected_session_start"], context["expected_session_end"]
        ],
        "cross_section": context["cross_section"],
        "metrics": context["metrics"],
    }


def main() -> None:
    print(json.dumps(build_persisted_sector_demo(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
