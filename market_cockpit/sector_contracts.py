"""Read-only provider-attributed selected-sector context contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

SectorAlignmentStatus = Literal["aligned", "different_session", "different_cutoff", "partial"]
SectorSessionAlignmentStatus = Literal["aligned", "different_session", "partial"]
SectorCutoffAlignmentStatus = Literal["aligned", "different_cutoff"]
SectorCoverageStatus = Literal["complete", "partial"]
SectorWindowReason = Literal[
    "available", "insufficient_history", "missing_expected_session", "invalid_close"
]


@dataclass(frozen=True)
class SectorWindowDiagnostic:
    required_session_count: int
    present_valid_session_count: int
    window_start_session: str | None
    window_end_session: str | None
    missing_session_count: int
    missing_sessions: tuple[str, ...]
    invalid_session_count: int
    invalid_sessions: tuple[str, ...]
    reason: SectorWindowReason


@dataclass(frozen=True)
class SectorMetrics:
    sector_code: str
    sector_name: str
    latest_close: float | None
    latest_session: str | None
    latest_return: float | None
    return_5: float | None
    return_20: float | None
    sma20: float | None
    sma20_distance: float | None
    above_sma20: bool | None
    realized_volatility_20: float | None
    max_drawdown_20: float | None
    available_session_count: int
    latest_return_window: SectorWindowDiagnostic
    return_5_window: SectorWindowDiagnostic
    return_20_window: SectorWindowDiagnostic
    sma20_window: SectorWindowDiagnostic
    risk_window: SectorWindowDiagnostic
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SectorRankedMetric:
    sector_code: str
    sector_name: str
    value: float


@dataclass(frozen=True)
class SectorCrossSection:
    valid_latest_return_count: int
    positive_latest_return_count: int
    positive_latest_return_share: float | None
    valid_sma20_count: int
    above_sma20_count: int
    above_sma20_share: float | None
    top_latest_return: list[SectorRankedMetric]
    bottom_latest_return: list[SectorRankedMetric]
    top_return_20: list[SectorRankedMetric]
    bottom_return_20: list[SectorRankedMetric]


@dataclass(frozen=True)
class SectorProvenance:
    series_key: str
    ingestion_run_id: int
    provider: str
    source: str
    definition_contract_version: str
    daily_contract_version: str
    adapter_version: str
    adapter_compatibility_version: str
    taxonomy_endpoint: str
    history_endpoint: str
    taxonomy: str
    classification_level: str | None
    frequency: str
    adjust_type: str
    sector_codes: list[str]
    requested_start_date: str
    requested_end_date: str
    information_cutoff_date: str
    requested_as_of_cutoff: str | None
    effective_sector_session: str | None
    ingestion_imported_at_utc: str
    ingestion_completed_at_utc: str | None
    collection_timestamp_utc: str | None
    effective_information_cutoff_date: str | None
    akshare_package_version: str | None
    network_mode: str | None
    timeout_seconds: float | None
    max_retries: int | None
    generated_at_utc: str


@dataclass(frozen=True)
class SectorContext:
    provenance: SectorProvenance
    metrics: list[SectorMetrics]
    cross_section: SectorCrossSection
    coverage_status: SectorCoverageStatus
    alignment_status: SectorAlignmentStatus
    session_alignment_status: SectorSessionAlignmentStatus
    cutoff_alignment_status: SectorCutoffAlignmentStatus
    requested_sector_count: int
    available_sector_count: int
    aligned_sector_count: int
    missing_sector_codes: list[str]
    equity_information_cutoff_date: str
    sector_information_cutoff_date: str
    equity_effective_session: str
    effective_sector_session: str | None
    expected_session_source: str
    expected_session_count: int
    expected_session_start: str
    expected_session_end: str
    warnings: list[str]
    label: str = "provider-attributed selected-sector market context"
    formula_reference: str = "docs/sector_context.md"
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
