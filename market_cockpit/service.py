"""Application service for database-backed Market Cockpit snapshots."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from pandas.api.types import is_bool_dtype

from backend.database.series import SnapshotSeriesIdentity
from market_cockpit.benchmark_calculator import calculate_benchmark_metrics
from market_cockpit.benchmark_contracts import BenchmarkContext, BenchmarkProvenance
from market_cockpit.benchmark_repository import BenchmarkRepository
from market_cockpit.calculator import calculate_market_cockpit
from market_cockpit.contracts import (
    MarketCockpitProvenance,
    MarketCockpitSnapshot,
    UnsupportedSection,
)
from market_cockpit.repository import MarketCockpitRepository
from market_cockpit.repository import PersistedMarketDataSnapshot


class MarketCockpitService:
    """Load one persisted series snapshot and build a read-only result."""

    def __init__(
        self,
        repository: MarketCockpitRepository,
        *,
        benchmark_repository: BenchmarkRepository | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._benchmark_repository = benchmark_repository
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def build_snapshot(
        self,
        *,
        series_key: str | None = None,
        selector: SnapshotSeriesIdentity | None = None,
        as_of_cutoff: str | None = None,
        benchmark_series_key: str | None = None,
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
        scope_warning = (
            "Scope coverage is unverified: internally ready calculations describe only the "
            "exact selected universe and do not imply representative A-share or full-market coverage."
        )
        warnings = [*calculation.warnings, scope_warning]
        overall_status = (
            "insufficient_data"
            if calculation.calculation_status == "insufficient_data"
            else "partial"
        )
        benchmark_context = self._build_benchmark_context(
            benchmark_series_key=benchmark_series_key,
            as_of_cutoff=as_of_cutoff,
            equity_snapshot=persisted,
            equity_effective_session=calculation.effective_as_of_session,
            generated_at=generated_at,
        )
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
                ingestion_imported_at_utc=persisted.ingestion_imported_at_utc,
                ingestion_completed_at_utc=persisted.ingestion_completed_at_utc,
                collection_timestamp_utc=persisted.collection_timestamp_utc,
                effective_information_cutoff_date=(
                    persisted.effective_information_cutoff_date
                ),
                akshare_package_version=persisted.akshare_package_version,
                stock_basic_endpoint=persisted.stock_basic_endpoint,
                daily_price_endpoint=persisted.daily_price_endpoint,
                trade_calendar_endpoint=persisted.trade_calendar_endpoint,
                frequency=persisted.frequency,
                adapter_compatibility_version=(
                    persisted.adapter_compatibility_version
                ),
                requested_as_of_cutoff=(
                    str(as_of_cutoff).strip().replace("-", "")
                    if as_of_cutoff is not None
                    else None
                ),
                effective_as_of_session=calculation.effective_as_of_session,
                generated_at_utc=generated_at.astimezone(timezone.utc).isoformat().replace(
                    "+00:00", "Z"
                ),
            ),
            metrics=calculation.metrics,
            stock_codes=persisted.stock_codes,
            universe_stock_count=len(persisted.stock_codes),
            available_stock_count=calculation.available_stock_count,
            calculation_status=calculation.calculation_status,
            scope_coverage_status="unverified_selected_scope",
            completeness_status=overall_status,
            latest_data_diagnostics=calculation.latest_data_diagnostics,
            warnings=warnings,
            unsupported_sections=_unsupported_sections(),
            benchmark_context=benchmark_context,
        )

    def _build_benchmark_context(
        self,
        *,
        benchmark_series_key: str | None,
        as_of_cutoff: str | None,
        equity_snapshot: PersistedMarketDataSnapshot,
        equity_effective_session: str,
        generated_at: datetime,
    ) -> BenchmarkContext | None:
        if benchmark_series_key is None:
            return None
        if self._benchmark_repository is None:
            raise ValueError("Benchmark repository is required when benchmark_series_key is provided.")
        persisted = self._benchmark_repository.load_snapshot(
            series_key=benchmark_series_key,
            as_of_cutoff=as_of_cutoff,
            permitted_end_session=equity_effective_session,
        )
        expected_sessions = _expected_benchmark_sessions(
            equity_snapshot=equity_snapshot,
            benchmark_information_cutoff=persisted.information_cutoff_date,
            benchmark_requested_end=persisted.requested_end_date,
            equity_effective_session=equity_effective_session,
            as_of_cutoff=as_of_cutoff,
        )
        metrics, warnings = calculate_benchmark_metrics(
            persisted,
            expected_sessions=expected_sessions,
        )
        available_metrics = [metric for metric in metrics if metric.latest_session is not None]
        latest_sessions = {metric.latest_session for metric in available_metrics}
        missing_codes = sorted(
            metric.index_code for metric in metrics if metric.latest_session is None
        )
        aligned_code_count = sum(
            metric.latest_session == equity_effective_session for metric in metrics
        )
        cutoff_alignment_status = (
            "aligned"
            if persisted.information_cutoff_date
            == equity_snapshot.information_cutoff_date
            else "different_cutoff"
        )
        if missing_codes or len(latest_sessions) > 1:
            session_alignment_status = "partial"
        elif latest_sessions != {equity_effective_session}:
            session_alignment_status = "different_session"
        else:
            session_alignment_status = "aligned"
        if session_alignment_status == "partial":
            alignment_status = "partial"
        elif session_alignment_status == "different_session":
            alignment_status = "different_session"
        elif cutoff_alignment_status == "different_cutoff":
            alignment_status = "different_cutoff"
        else:
            alignment_status = "aligned"

        effective_benchmark_session = (
            max(session for session in latest_sessions if session is not None)
            if latest_sessions
            else persisted.effective_benchmark_session
        )
        if cutoff_alignment_status == "different_cutoff":
            warnings.append(
                "Equity and benchmark information cutoffs differ: "
                f"equity={equity_snapshot.information_cutoff_date}, "
                f"benchmark={persisted.information_cutoff_date}."
            )
        if missing_codes:
            warnings.append(
                f"Benchmark exact scope has no eligible row for codes: {missing_codes}."
            )
        if len(latest_sessions) > 1:
            warnings.append(
                "Benchmark codes have mixed latest eligible sessions: "
                f"{sorted(session for session in latest_sessions if session is not None)}."
            )
        if effective_benchmark_session != equity_effective_session:
            warnings.append(
                "Equity and benchmark effective sessions differ: "
                f"equity={equity_effective_session}, benchmark={effective_benchmark_session}."
            )
        requested_cutoff = (
            str(as_of_cutoff).strip().replace("-", "") if as_of_cutoff is not None else None
        )
        return BenchmarkContext(
            provenance=BenchmarkProvenance(
                series_key=persisted.series_key,
                ingestion_run_id=persisted.ingestion_run_id,
                provider=persisted.provider,
                source=persisted.provider,
                contract_version=persisted.contract_version,
                adapter_version=persisted.adapter_version,
                endpoint=persisted.endpoint,
                frequency=persisted.frequency,
                adapter_compatibility_version=persisted.adapter_compatibility_version,
                index_codes=persisted.index_codes,
                requested_start_date=persisted.requested_start_date,
                requested_end_date=persisted.requested_end_date,
                information_cutoff_date=persisted.information_cutoff_date,
                requested_as_of_cutoff=requested_cutoff,
                effective_benchmark_session=effective_benchmark_session,
                ingestion_imported_at_utc=persisted.ingestion_imported_at_utc,
                ingestion_completed_at_utc=persisted.ingestion_completed_at_utc,
                collection_timestamp_utc=persisted.collection_timestamp_utc,
                effective_information_cutoff_date=(
                    persisted.effective_information_cutoff_date
                ),
                akshare_package_version=persisted.akshare_package_version,
                network_mode=persisted.network_mode,
                timeout_seconds=persisted.timeout_seconds,
                max_retries=persisted.max_retries,
                generated_at_utc=generated_at.astimezone(timezone.utc).isoformat().replace(
                    "+00:00", "Z"
                ),
            ),
            metrics=metrics,
            alignment_status=alignment_status,
            session_alignment_status=session_alignment_status,
            cutoff_alignment_status=cutoff_alignment_status,
            requested_code_count=len(metrics),
            available_code_count=len(available_metrics),
            aligned_code_count=aligned_code_count,
            missing_codes=missing_codes,
            equity_information_cutoff_date=equity_snapshot.information_cutoff_date,
            benchmark_information_cutoff_date=persisted.information_cutoff_date,
            equity_effective_session=equity_effective_session,
            effective_benchmark_session=effective_benchmark_session,
            expected_session_source="selected_equity_snapshot.persisted_trade_calendar",
            expected_session_count=len(expected_sessions),
            expected_session_start=expected_sessions[0],
            expected_session_end=expected_sessions[-1],
            warnings=warnings,
        )


def _expected_benchmark_sessions(
    *,
    equity_snapshot: PersistedMarketDataSnapshot,
    benchmark_information_cutoff: str,
    benchmark_requested_end: str,
    equity_effective_session: str,
    as_of_cutoff: str | None,
) -> list[str]:
    calendar = equity_snapshot.trade_calendar.copy()
    required = {"trade_date", "is_open"}
    missing = sorted(required - set(calendar.columns))
    if missing:
        raise ValueError(
            f"Selected equity snapshot trade calendar is incomplete; missing={missing}."
        )
    calendar["trade_date"] = calendar["trade_date"].map(_compact_date)
    duplicates = sorted(
        calendar.loc[
            calendar.duplicated(["trade_date"], keep=False), "trade_date"
        ].unique()
    )
    if duplicates:
        raise ValueError(
            "Selected equity snapshot trade calendar is contradictory; duplicate sessions="
            f"{duplicates}."
        )
    if calendar["is_open"].isna().any() or not is_bool_dtype(calendar["is_open"]):
        raise ValueError(
            "Selected equity snapshot trade calendar contains invalid open flags."
        )
    bound = min(
        value
        for value in (
            equity_snapshot.information_cutoff_date,
            equity_snapshot.requested_end_date,
            benchmark_information_cutoff,
            benchmark_requested_end,
            equity_effective_session,
            _compact_optional_date(as_of_cutoff),
        )
        if value is not None
    )
    sessions = sorted(
        calendar.loc[
            calendar["is_open"].eq(True) & calendar["trade_date"].le(bound),
            "trade_date",
        ].unique()
    )
    if not sessions:
        raise ValueError(
            "Selected equity snapshot has no persisted open session eligible for benchmark context."
        )
    return sessions


def _compact_optional_date(value: str | None) -> str | None:
    if value is None:
        return None
    return _compact_date(value)


def _compact_date(value: object) -> str:
    normalized = str(value).strip().replace("-", "")
    try:
        return datetime.strptime(normalized, "%Y%m%d").strftime("%Y%m%d")
    except ValueError as exc:
        raise ValueError("Persisted trade-calendar dates must use YYYYMMDD format.") from exc


def _unsupported_sections() -> list[UnsupportedSection]:
    reason = "The required reviewed data source and coverage policy are not available in this slice."
    return [
        UnsupportedSection("official_indices", "Official index levels and returns", reason),
        UnsupportedSection("sector_rotation", "Sector or industry rotation", reason),
        UnsupportedSection("style_analysis", "Size, value, and growth style analysis", reason),
        UnsupportedSection("valuation_breadth", "Valuation and market-cap breadth", reason),
        UnsupportedSection("crowding", "Crowding and positioning indicators", reason),
    ]
