"""Read-only provider-attributed benchmark context contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

BenchmarkAlignmentStatus = Literal["aligned", "different_session", "partial"]


@dataclass(frozen=True)
class BenchmarkCodeMetrics:
    index_code: str
    latest_close: float | None
    latest_session: str | None
    latest_return: float | None
    sma20: float | None
    above_sma20: bool | None
    sma60: float | None
    above_sma60: bool | None
    realized_volatility_20: float | None
    max_drawdown_20: float | None
    available_session_count: int
    latest_return_required_sessions: int = 2
    sma20_required_sessions: int = 20
    sma60_required_sessions: int = 60
    risk_required_sessions: int = 21
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class BenchmarkProvenance:
    series_key: str
    ingestion_run_id: int
    provider: str
    source: str
    contract_version: str
    adapter_version: str
    endpoint: str
    frequency: str
    adapter_compatibility_version: str
    index_codes: list[str]
    requested_start_date: str
    requested_end_date: str
    information_cutoff_date: str
    requested_as_of_cutoff: str | None
    effective_benchmark_session: str
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
class BenchmarkContext:
    provenance: BenchmarkProvenance
    metrics: list[BenchmarkCodeMetrics]
    alignment_status: BenchmarkAlignmentStatus
    warnings: list[str]
    label: str = "provider-attributed benchmark index context"
    formula_reference: str = "docs/benchmark_context.md"
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
