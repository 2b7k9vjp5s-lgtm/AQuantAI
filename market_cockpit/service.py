"""Application service for database-backed Market Cockpit snapshots."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from backend.database.series import SnapshotSeriesIdentity
from market_cockpit.calculator import calculate_market_cockpit
from market_cockpit.contracts import (
    MarketCockpitProvenance,
    MarketCockpitSnapshot,
    UnsupportedSection,
)
from market_cockpit.repository import MarketCockpitRepository


class MarketCockpitService:
    """Load one persisted series snapshot and build a read-only result."""

    def __init__(
        self,
        repository: MarketCockpitRepository,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def build_snapshot(
        self,
        *,
        series_key: str | None = None,
        selector: SnapshotSeriesIdentity | None = None,
        as_of_cutoff: str | None = None,
    ) -> MarketCockpitSnapshot:
        persisted = self._repository.load_snapshot(
            series_key=series_key,
            selector=selector,
            as_of_cutoff=as_of_cutoff,
        )
        calculation = calculate_market_cockpit(persisted, as_of_cutoff=as_of_cutoff)
        generated_at = self._clock()
        if generated_at.tzinfo is None or generated_at.utcoffset() is None:
            raise ValueError("Market Cockpit clock must return a timezone-aware datetime.")
        return MarketCockpitSnapshot(
            provenance=MarketCockpitProvenance(
                series_key=persisted.series_key,
                ingestion_run_id=persisted.ingestion_run_id,
                provider=persisted.provider,
                contract_version=persisted.contract_version,
                adapter_version=persisted.adapter_version,
                information_cutoff_date=persisted.information_cutoff_date,
                requested_start_date=persisted.requested_start_date,
                requested_end_date=persisted.requested_end_date,
                adjust_type=persisted.adjust_type,
                generated_at_utc=generated_at.astimezone(timezone.utc).isoformat().replace(
                    "+00:00", "Z"
                ),
                effective_as_of_session=calculation.effective_as_of_session,
            ),
            metrics=calculation.metrics,
            stock_codes=persisted.stock_codes,
            universe_stock_count=len(persisted.stock_codes),
            available_stock_count=calculation.available_stock_count,
            completeness_status=calculation.completeness_status,
            warnings=calculation.warnings,
            unsupported_sections=_unsupported_sections(),
        )


def _unsupported_sections() -> list[UnsupportedSection]:
    reason = "The required reviewed data source and coverage policy are not available in v0.4A."
    return [
        UnsupportedSection("official_indices", "Official index levels and returns", reason),
        UnsupportedSection("sector_rotation", "Sector or industry rotation", reason),
        UnsupportedSection("style_analysis", "Size, value, and growth style analysis", reason),
        UnsupportedSection("valuation_breadth", "Valuation and market-cap breadth", reason),
        UnsupportedSection("crowding", "Crowding and positioning indicators", reason),
    ]
