"""Typed contracts for selected-universe liquidity distribution context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LiquidityCalculationStatus = Literal["complete", "partial", "unavailable"]
LiquidityLatestIssueReason = Literal[
    "missing_latest_row",
    "no_trade_latest_row",
    "zero_amount_latest_row",
    "invalid_amount_latest_row",
    "invalid_traded_record_latest_row",
]
LiquidityWindowReason = Literal[
    "complete",
    "partial_matched_cohort",
    "insufficient_open_session_history",
    "empty_matched_cohort",
    "invalid_baseline",
]
LiquiditySourceExclusionReason = Literal[
    "future_price_rows",
    "out_of_calendar_price_rows",
    "wrong_scope_price_rows",
    "wrong_adjustment_price_rows",
    "duplicate_stock_session_price_rows",
]


@dataclass(frozen=True)
class LiquidityLatestIssue:
    stock_code: str
    session: str
    reason: LiquidityLatestIssueReason


@dataclass(frozen=True)
class LiquiditySourceExclusion:
    reason: LiquiditySourceExclusionReason
    excluded_row_count: int
    identifiers: list[str]
    identifiers_truncated: bool


@dataclass(frozen=True)
class LiquidityActivityWindow:
    prior_session_count: int
    required_session_count: int
    observed_session_count: int
    window_start_session: str | None
    window_end_session: str | None
    matched_cohort_count: int
    unavailable_stock_codes: list[str]
    latest_matched_total_amount: float | None
    baseline_total_amount: float | None
    activity_ratio: float | None
    calculation_status: LiquidityCalculationStatus
    reason: LiquidityWindowReason


@dataclass(frozen=True)
class LiquidityDiagnostics:
    latest_issues: list[LiquidityLatestIssue]
    source_exclusions: list[LiquiditySourceExclusion]


@dataclass(frozen=True)
class LiquidityContext:
    effective_session: str
    expected_session_source: str
    requested_stock_count: int
    latest_eligible_count: int
    latest_unavailable_count: int
    latest_total_amount: float | None
    latest_median_amount: float | None
    top5_concentration_share: float | None
    top5_member_count: int
    top5_stock_codes: list[str]
    top_decile_concentration_share: float | None
    top_decile_member_count: int
    top_decile_stock_codes: list[str]
    activity_5: LiquidityActivityWindow
    activity_20: LiquidityActivityWindow
    latest_above_20_session_baseline_count: int
    latest_above_20_session_baseline_share: float | None
    calculation_status: LiquidityCalculationStatus
    diagnostics: LiquidityDiagnostics
    warnings: list[str]
    amount_unit: str = "provider-attributed raw amount"
    scope_label: str = "selected universe"
    scope_label_zh: str = "选定股票范围"
    interpretation: str = (
        "Trading concentration is a descriptive distribution statistic only; it is not "
        "a crowding conclusion, regime, signal, recommendation, or attractiveness score."
    )
    formula_reference: str = "docs/market_cockpit.md#v04d-liquidity-distribution-context"
    read_only: bool = True
