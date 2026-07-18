"""Persist and inspect deterministic current/historical Market Cockpit snapshots."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from backend.database import build_engine, build_session_factory
from backend.database.market_data import MarketDataPersistenceService
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


def build_persisted_market_cockpit_demo(database_url: str | None = None) -> dict[str, Any]:
    """Persist two fixture revisions and calculate current and historical cutoff views."""
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    persistence = MarketDataPersistenceService(session_factory)
    try:
        historical = _ingest_revision(
            persistence,
            revision="historical",
            cutoff=COCKPIT_FIXTURE_HISTORICAL_CUTOFF,
        )
        current = _ingest_revision(
            persistence,
            revision="current",
            cutoff=COCKPIT_FIXTURE_CURRENT_CUTOFF,
        )
        fixed_clock = lambda: datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
        with session_factory() as session:
            service = MarketCockpitService(
                MarketCockpitRepository(session),
                clock=fixed_clock,
            )
            current_view = service.build_snapshot(series_key=current.series_key)
            historical_view = service.build_snapshot(
                series_key=current.series_key,
                as_of_cutoff=COCKPIT_FIXTURE_HISTORICAL_CUTOFF,
            )
        return {
            "series_key": current.series_key,
            "current": _summary(current_view.to_dict()),
            "historical": _summary(historical_view.to_dict()),
            "read_only": True,
            "network_access": False,
        }
    finally:
        engine.dispose()


def _ingest_revision(
    service: MarketDataPersistenceService,
    *,
    revision: str,
    cutoff: str,
):
    collection_timestamp = (
        "2026-04-04T12:00:00Z" if revision == "historical" else "2026-04-05T12:00:00Z"
    )
    return service.ingest_bundle(
        build_market_cockpit_fixture(revision=revision),
        provider=COCKPIT_FIXTURE_PROVIDER,
        requested_start_date=COCKPIT_FIXTURE_START_DATE,
        requested_end_date=COCKPIT_FIXTURE_END_DATE,
        information_cutoff_date=cutoff,
        requested_scope=COCKPIT_FIXTURE_SCOPE,
        adjust_type=COCKPIT_FIXTURE_ADJUST_TYPE,
        compatibility_parameters={
            "stock_basic_endpoint": "fixture_stock_basic",
            "daily_price_endpoint": "fixture_daily_price",
            "trade_calendar_endpoint": "fixture_trade_calendar",
            "frequency": "daily",
            "adapter_compatibility_version": "market-cockpit-fixture-v1",
        },
        provider_request_metadata={
            "fixture_revision": revision,
            "network_access": False,
            "collection_timestamp_utc": collection_timestamp,
            "effective_information_cutoff_date": cutoff,
        },
        adapter_version="market-cockpit-fixture-v1",
    )


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    provenance = payload["provenance"]
    latest = payload["metrics"]["latest_session"]
    return {
        "ingestion_run_id": provenance["ingestion_run_id"],
        "information_cutoff_date": provenance["information_cutoff_date"],
        "effective_as_of_session": provenance["effective_as_of_session"],
        "requested_as_of_cutoff": provenance["requested_as_of_cutoff"],
        "collection_timestamp_utc": provenance["collection_timestamp_utc"],
        "ingestion_imported_at_utc": provenance["ingestion_imported_at_utc"],
        "ingestion_completed_at_utc": provenance["ingestion_completed_at_utc"],
        "generated_at_utc": provenance["generated_at_utc"],
        "calculation_status": payload["calculation_status"],
        "scope_coverage_status": payload["scope_coverage_status"],
        "completeness_status": payload["completeness_status"],
        "universe_stock_count": payload["universe_stock_count"],
        "available_stock_count": payload["available_stock_count"],
        "equal_weight_mean_return": latest["equal_weight_mean_return"],
        "advancing_count": latest["advancing_count"],
        "declining_count": latest["declining_count"],
        "unchanged_count": latest["unchanged_count"],
        "stale_or_missing_latest_count": payload["latest_data_diagnostics"][
            "stale_or_missing_latest_count"
        ],
        "no_trade_latest_count": payload["latest_data_diagnostics"][
            "no_trade_latest_count"
        ],
    }


def main() -> None:
    print(json.dumps(build_persisted_market_cockpit_demo(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
