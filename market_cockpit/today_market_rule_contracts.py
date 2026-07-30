"""Pure contracts for deterministic Today Market Slice B rules.

These contracts are source-neutral and persistence-neutral. They carry only explicit
calculation inputs, deterministic rule outputs, rule-version identity, and stable
fingerprints. They perform no database, network, runtime, Provider, UI, AI, research,
or recommendation work.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from hashlib import sha256
import json
from math import isfinite
from typing import Any, Literal

MARKET_RULE_VERSION = "aquantai.today-market-market-overview.v1"
SECTOR_RULE_VERSION = "aquantai.today-market-sector-hotspot.v1"
ANOMALY_RULE_VERSION = "aquantai.today-market-stock-anomaly.v1"
RETURN_EPSILON = 1e-12
MINIMUM_RANKED_SECTOR_COUNT = 10
CONSTITUENT_RETURN_COVERAGE_MIN = 0.90
CONSTITUENT_MA20_COVERAGE_MIN = 0.80

MarketState = Literal["strong", "weak", "mixed", "insufficient_coverage"]
HotspotState = Literal[
    "new",
    "strengthening",
    "spreading",
    "persistent_strong",
    "high_level_divergence",
    "cooling",
    "neutral",
    "insufficient_coverage",
]
AnomalyType = Literal[
    "large_move",
    "unusual_volume",
    "new_high",
    "new_low",
    "gap",
    "persistent_relative_strength",
    "sector_relative_outlier",
]

STRONG_PRIOR_STATES: frozenset[str] = frozenset(
    {"new", "strengthening", "spreading", "persistent_strong"}
)
ANOMALY_RULE_ORDER: tuple[AnomalyType, ...] = (
    "large_move",
    "unusual_volume",
    "new_high",
    "new_low",
    "gap",
    "persistent_relative_strength",
    "sector_relative_outlier",
)


class TodayMarketRuleInputError(ValueError):
    """Raised when explicit deterministic rule input violates the frozen contract."""


def _canonical(value: Any) -> Any:
    if is_dataclass(value):
        return _canonical(asdict(value))
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_canonical(item) for item in value)
    if isinstance(value, float):
        if not isfinite(value):
            raise TodayMarketRuleInputError("rule fingerprints reject non-finite numeric values")
        return value
    return value


def canonical_fingerprint(value: Any) -> str:
    payload = json.dumps(
        _canonical(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class MarketOverviewInput:
    expected_active_count: int
    accounted_count: int
    identity_conflict_count: int
    calendar_conflict: bool
    valid_returns: tuple[float, ...]
    above_ma20_flags: tuple[bool, ...]
    new_high_20_flags: tuple[bool, ...] = ()
    new_low_20_flags: tuple[bool, ...] = ()
    market_amount_current: float | None = None
    market_amount_previous_20: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class MarketOverviewResult:
    rule_version: str
    market_state: MarketState
    expected_active_count: int
    accounted_count: int
    missing_source_count: int
    identity_conflict_count: int
    valid_return_count: int
    return_coverage_ratio: float
    advancing_count: int
    declining_count: int
    unchanged_count: int
    advance_ratio: float | None
    breadth_balance: float | None
    median_return: float | None
    eligible_20_count: int
    above_ma20_ratio: float | None
    new_high_20_ratio: float | None
    new_low_20_ratio: float | None
    market_amount_current: float | None
    market_amount_ratio_20: float | None
    missing_inputs: tuple[str, ...]

    @property
    def fingerprint(self) -> str:
        return canonical_fingerprint(self)


@dataclass(frozen=True, slots=True)
class SectorRuleInput:
    sector_code: str
    sector_name: str
    taxonomy: str
    classification_level: str | None
    sector_r1: float | None
    sector_r5: float | None
    sector_r20: float | None
    broad_market_benchmark_r5: float | None
    dated_membership_revision_id: str | None
    constituent_return_coverage: float | None
    constituent_ma20_coverage: float | None
    breadth_up_1: float | None
    breadth_above_ma20: float | None
    activity_ratio_20: float | None
    new_high_20_share: float | None
    strong_rank_sessions_5: int | None
    prior_state: HotspotState | None
    representative_positive_share_5: float | None = None
    identity_ambiguous: bool = False


@dataclass(frozen=True, slots=True)
class SectorHotspotResult:
    rule_version: str
    sector_code: str
    sector_name: str
    taxonomy: str
    classification_level: str | None
    sector_r1: float | None
    sector_r5: float | None
    sector_r20: float | None
    sector_relative_5: float | None
    r1_pct: float | None
    r5_pct: float | None
    r20_pct: float | None
    breadth_up_1: float | None
    breadth_above_ma20: float | None
    activity_ratio_20: float | None
    new_high_20_share: float | None
    representative_positive_share_5: float | None
    constituent_return_coverage: float | None
    constituent_ma20_coverage: float | None
    strong_rank_sessions_5: int | None
    prior_state: HotspotState | None
    state: HotspotState
    matched_rule: str
    dated_membership_revision_id: str | None
    missing_inputs: tuple[str, ...]
    component_thresholds: tuple[tuple[str, float | int | str], ...]

    def __post_init__(self) -> None:
        missing = set(self.missing_inputs)
        state_specific_inputs = (
            ("breadth_up_1", self.breadth_up_1),
            ("activity_ratio_20", self.activity_ratio_20),
            ("new_high_20_share", self.new_high_20_share),
            ("strong_rank_sessions_5", self.strong_rank_sessions_5),
        )
        for field_name, value in state_specific_inputs:
            if value is None:
                missing.add(f"{field_name}_unavailable")
        object.__setattr__(self, "missing_inputs", tuple(sorted(missing)))

    @property
    def fingerprint(self) -> str:
        return canonical_fingerprint(self)


@dataclass(frozen=True, slots=True)
class StockRuleInput:
    stock_code: str
    r1: float | None
    r5: float | None
    broad_market_benchmark_r5: float | None
    volume_current: float | None
    volume_previous_20: tuple[float, ...]
    analysis_closes_60: tuple[float, ...]
    open_current: float | None
    reference_close_previous: float | None
    return_semantics_valid: bool
    reference_close_semantics_valid: bool
    sector_code: str | None = None
    dated_membership_revision_id: str | None = None
    sector_identity_ambiguous: bool = False


@dataclass(frozen=True, slots=True)
class StockAnomaly:
    stock_code: str
    anomaly_type: AnomalyType
    primary_metric: float
    rule_version: str
    details: tuple[tuple[str, float | int | str], ...] = ()

    @property
    def fingerprint(self) -> str:
        return canonical_fingerprint(self)


@dataclass(frozen=True, slots=True)
class StockRuleDiagnostics:
    stock_code: str
    unavailable_rules: tuple[tuple[AnomalyType, str], ...]


@dataclass(frozen=True, slots=True)
class StockAnomalyResult:
    rule_version: str
    anomalies: tuple[StockAnomaly, ...]
    diagnostics: tuple[StockRuleDiagnostics, ...]

    @property
    def fingerprint(self) -> str:
        return canonical_fingerprint(self)


@dataclass(frozen=True, slots=True)
class TodayMarketDeterministicReadModel:
    market: MarketOverviewResult
    sectors: tuple[SectorHotspotResult, ...]
    stock_anomalies: StockAnomalyResult

    @property
    def fingerprint(self) -> str:
        return canonical_fingerprint(self)
