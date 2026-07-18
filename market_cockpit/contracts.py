"""Read-only Market Cockpit contracts for one selected persisted universe."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from backend.safety import RESEARCH_DISCLAIMER, validate_allowed_actions, validate_research_text

CompletenessStatus = Literal["ready", "partial", "insufficient_data"]


@dataclass(frozen=True)
class LatestSessionMetrics:
    equal_weight_mean_return: float | None
    median_return: float | None
    advancing_count: int
    declining_count: int
    unchanged_count: int
    unavailable_count: int
    advance_ratio: float | None
    breadth_balance: float | None
    return_dispersion: float | None


@dataclass(frozen=True)
class WindowBreadthMetrics:
    window_sessions: int
    above_sma_ratio: float | None
    above_sma_count: int | None
    new_high_count: int | None
    new_low_count: int | None
    eligible_stock_count: int


@dataclass(frozen=True)
class ParticipationMetric:
    ratio_to_prior_20_session_median: float | None
    eligible_stock_count: int
    required_sessions: int = 21


@dataclass(frozen=True)
class RiskMetrics:
    realized_volatility_20: float | None
    max_drawdown_20: float | None
    eligible_return_sessions: int
    required_return_sessions: int = 20


@dataclass(frozen=True)
class MarketCockpitMetrics:
    latest_session: LatestSessionMetrics
    breadth_20: WindowBreadthMetrics
    breadth_60: WindowBreadthMetrics
    volume_participation: ParticipationMetric
    amount_participation: ParticipationMetric
    equal_weight_risk: RiskMetrics


@dataclass(frozen=True)
class MarketCockpitProvenance:
    series_key: str
    ingestion_run_id: int
    provider: str
    contract_version: str
    adapter_version: str
    information_cutoff_date: str
    requested_start_date: str
    requested_end_date: str
    adjust_type: str
    generated_at_utc: str
    effective_as_of_session: str


@dataclass(frozen=True)
class UnsupportedSection:
    key: str
    label: str
    reason: str


@dataclass(frozen=True)
class MarketCockpitSnapshot:
    provenance: MarketCockpitProvenance
    metrics: MarketCockpitMetrics
    stock_codes: list[str]
    universe_stock_count: int
    available_stock_count: int
    completeness_status: CompletenessStatus
    warnings: list[str]
    unsupported_sections: list[UnsupportedSection]
    scope_label: str = "selected universe"
    scope_label_zh: str = "选定股票范围"
    formula_reference: str = "docs/market_cockpit.md"
    allowed_actions: list[str] = field(default_factory=lambda: ["view", "inspect"])
    disclaimer: str = RESEARCH_DISCLAIMER
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        validate_allowed_actions(self.allowed_actions)
        validate_research_text(payload)
        return payload
