"""Read-only provider-attributed benchmark context contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

BenchmarkAlignmentStatus = Literal[
    "aligned", "different_session", "different_cutoff", "partial"
]
BenchmarkSessionAlignmentStatus = Literal["aligned", "different_session", "partial"]
BenchmarkCutoffAlignmentStatus = Literal["aligned", "different_cutoff"]
BenchmarkWindowReason = Literal[
    "available",
    "insufficient_history",
    "missing_expected_session",
    "invalid_close",
]


@dataclass(frozen=True)
class BenchmarkWindowDiagnostic:
    required_session_count: int
    present_valid_session_count: int
    window_start_session: str | None
    window_end_session: str | None
    missing_session_count: int
    missing_sessions: tuple[str, ...]
    invalid_session_count: int
    invalid_sessions: tuple[str, ...]
    reason: BenchmarkWindowReason


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
    latest_return_window: BenchmarkWindowDiagnostic | None = None
    sma20_window: BenchmarkWindowDiagnostic | None = None
    sma60_window: BenchmarkWindowDiagnostic | None = None
    risk_window: BenchmarkWindowDiagnostic | None = None
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
    effective_benchmark_session: str | None
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
    session_alignment_status: BenchmarkSessionAlignmentStatus
    cutoff_alignment_status: BenchmarkCutoffAlignmentStatus
    requested_code_count: int
    available_code_count: int
    aligned_code_count: int
    missing_codes: list[str]
    equity_information_cutoff_date: str
    benchmark_information_cutoff_date: str
    equity_effective_session: str
    effective_benchmark_session: str | None
    expected_session_source: str
    expected_session_count: int
    expected_session_start: str
    expected_session_end: str
    warnings: list[str]
    label: str = "provider-attributed benchmark index context"
    formula_reference: str = "docs/benchmark_context.md"
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
