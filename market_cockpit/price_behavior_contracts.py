"""Typed contracts for selected-universe price-behavior proxies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PRICE_BEHAVIOR_IDENTIFIER_SAMPLE_LIMIT = 10

PriceBehaviorCalculationStatus = Literal["complete", "partial", "unavailable"]
PriceBehaviorMetricReason = Literal[
    "complete",
    "partial_eligible_cohort",
    "insufficient_open_session_history",
    "empty_eligible_cohort",
    "non_finite_aggregate",
]
PriceBehaviorMatchedReason = Literal[
    "complete",
    "partial_matched_cohort",
    "empty_matched_cohort",
    "non_finite_aggregate",
]
PriceBehaviorIssueReason = Literal[
    "insufficient_open_session_history",
    "missing_required_row",
    "no_trade_required_row",
    "invalid_close_required_row",
    "non_positive_close_required_row",
    "non_finite_close_required_row",
    "invalid_traded_record_required_row",
    "non_finite_calculation",
]
PriceBehaviorSourceExclusionReason = Literal[
    "future_price_rows",
    "out_of_calendar_price_rows",
    "wrong_scope_price_rows",
    "wrong_adjustment_price_rows",
    "duplicate_stock_session_price_rows",
]


@dataclass(frozen=True)
class PriceBehaviorWindow:
    prior_session_count: int
    required_close_count: int
    required_return_count: int
    observed_open_session_count: int
    window_start_session: str | None
    window_end_session: str | None


@dataclass(frozen=True)
class PriceBehaviorIssue:
    stock_code: str
    reason: PriceBehaviorIssueReason
    blocking_session: str | None


@dataclass(frozen=True)
class PriceBehaviorMetricDiagnostics:
    issue_count: int
    issues: list[PriceBehaviorIssue]
    issues_truncated: bool
    issues_omitted_count: int


@dataclass(frozen=True)
class PriceBehaviorSourceExclusion:
    reason: PriceBehaviorSourceExclusionReason
    excluded_row_count: int
    stock_code_count: int
    stock_codes: list[str]
    stock_codes_truncated: bool
    stock_codes_omitted_count: int


@dataclass(frozen=True)
class MomentumSummary:
    metric: Literal["return_20", "return_60"]
    window: PriceBehaviorWindow
    requested_stock_count: int
    eligible_stock_count: int
    unavailable_stock_count: int
    median_return: float | None
    positive_count: int
    non_positive_count: int
    positive_share: float | None
    calculation_status: PriceBehaviorCalculationStatus
    reason: PriceBehaviorMetricReason
    diagnostics: PriceBehaviorMetricDiagnostics


@dataclass(frozen=True)
class VolatilitySummary:
    metric: Literal["volatility_20"]
    window: PriceBehaviorWindow
    requested_stock_count: int
    eligible_stock_count: int
    unavailable_stock_count: int
    median_annualized_volatility: float | None
    ddof: int
    annualization_factor: int
    calculation_status: PriceBehaviorCalculationStatus
    reason: PriceBehaviorMetricReason
    diagnostics: PriceBehaviorMetricDiagnostics


@dataclass(frozen=True)
class PriceBehaviorBucket:
    count: int
    share: float | None
    stock_codes: list[str]
    stock_codes_truncated: bool
    stock_codes_omitted_count: int


@dataclass(frozen=True)
class PriceBehaviorQuadrants:
    positive_momentum_lower_or_equal_volatility: PriceBehaviorBucket
    positive_momentum_higher_volatility: PriceBehaviorBucket
    non_positive_momentum_lower_or_equal_volatility: PriceBehaviorBucket
    non_positive_momentum_higher_volatility: PriceBehaviorBucket


@dataclass(frozen=True)
class PriceBehaviorMatchedCohort:
    requested_stock_count: int
    matched_cohort_count: int
    unavailable_stock_count: int
    unavailable_stock_codes: list[str]
    unavailable_stock_codes_truncated: bool
    unavailable_stock_codes_omitted_count: int
    matched_median_annualized_volatility: float | None
    calculation_status: PriceBehaviorCalculationStatus
    reason: PriceBehaviorMatchedReason
    quadrants: PriceBehaviorQuadrants


@dataclass(frozen=True)
class PriceBehaviorDiagnostics:
    source_exclusions: list[PriceBehaviorSourceExclusion]


@dataclass(frozen=True)
class PriceBehaviorContext:
    effective_session: str
    expected_session_source: str
    return_20: MomentumSummary
    return_60: MomentumSummary
    volatility_20: VolatilitySummary
    matched_cohort: PriceBehaviorMatchedCohort
    calculation_status: PriceBehaviorCalculationStatus
    diagnostics: PriceBehaviorDiagnostics
    warnings: list[str]
    scope_label: str = "selected universe"
    scope_label_zh: str = "选定股票范围"
    interpretation: str = (
        "These are descriptive selected-universe price-behavior proxies only. They are "
        "not canonical style factors, factor exposures, a market regime, a score, a "
        "signal, a recommendation, or an investment-attractiveness ranking."
    )
    formula_reference: str = "docs/market_cockpit.md#v04e-price-behavior-proxy-context"
    read_only: bool = True
