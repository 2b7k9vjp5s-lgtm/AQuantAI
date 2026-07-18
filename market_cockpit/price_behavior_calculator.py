"""Deterministic price-behavior proxies over one accepted equity snapshot."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import fsum, isfinite, sqrt
from typing import Literal

from market_cockpit.price_behavior_contracts import (
    PRICE_BEHAVIOR_IDENTIFIER_SAMPLE_LIMIT,
    MomentumSummary,
    PriceBehaviorBucket,
    PriceBehaviorCalculationStatus,
    PriceBehaviorContext,
    PriceBehaviorDiagnostics,
    PriceBehaviorIssue,
    PriceBehaviorIssueReason,
    PriceBehaviorMatchedCohort,
    PriceBehaviorMetricDiagnostics,
    PriceBehaviorMetricReason,
    PriceBehaviorQuadrants,
    PriceBehaviorSourceExclusion,
    PriceBehaviorWindow,
    VolatilitySummary,
)

Record = dict[str, float]
RecordPredicate = Callable[[Record], bool]


@dataclass(frozen=True)
class _IdentifierSample:
    values: list[str]
    exact_count: int
    truncated: bool
    omitted_count: int


@dataclass(frozen=True)
class _MetricValues:
    values: dict[str, float]
    issues: list[PriceBehaviorIssue]
    window: PriceBehaviorWindow
    reason: PriceBehaviorMetricReason
    status: PriceBehaviorCalculationStatus


def calculate_price_behavior_context(
    *,
    stock_codes: list[str],
    expected_sessions: list[str],
    effective_session: str,
    price_lookup: dict[tuple[str, str], Record],
    source_exclusions: list[PriceBehaviorSourceExclusion],
    is_no_trade: RecordPredicate,
    is_valid_traded_record: RecordPredicate,
) -> PriceBehaviorContext:
    """Calculate complete-window proxies without selecting or stitching data."""
    codes = sorted(stock_codes)
    if not expected_sessions or expected_sessions[-1] != effective_session:
        raise ValueError(
            "Price behavior requires the accepted effective session to end the open-session sequence."
        )

    return_20_values = _momentum_values(
        prior_session_count=20,
        codes=codes,
        sessions=expected_sessions,
        lookup=price_lookup,
        is_no_trade=is_no_trade,
        is_valid_traded_record=is_valid_traded_record,
    )
    return_60_values = _momentum_values(
        prior_session_count=60,
        codes=codes,
        sessions=expected_sessions,
        lookup=price_lookup,
        is_no_trade=is_no_trade,
        is_valid_traded_record=is_valid_traded_record,
    )
    volatility_values = _volatility_values(
        codes=codes,
        sessions=expected_sessions,
        lookup=price_lookup,
        is_no_trade=is_no_trade,
        is_valid_traded_record=is_valid_traded_record,
    )

    return_20 = _momentum_summary("return_20", codes, return_20_values)
    return_60 = _momentum_summary("return_60", codes, return_60_values)
    volatility_20 = _volatility_summary(codes, volatility_values)
    matched = _matched_cohort(
        codes=codes,
        return_20=return_20_values.values,
        return_60=return_60_values.values,
        volatility_20=volatility_values.values,
    )
    summaries = (return_20, return_60, volatility_20)
    if all(summary.calculation_status == "complete" for summary in summaries) and (
        matched.calculation_status == "complete"
    ):
        status: PriceBehaviorCalculationStatus = "complete"
    elif any(summary.eligible_stock_count > 0 for summary in summaries):
        status = "partial"
    else:
        status = "unavailable"

    warnings = _warnings(
        return_20=return_20,
        return_60=return_60,
        volatility_20=volatility_20,
        matched=matched,
        source_exclusions=source_exclusions,
    )
    return PriceBehaviorContext(
        effective_session=effective_session,
        expected_session_source="selected_equity_snapshot.persisted_trade_calendar",
        return_20=return_20,
        return_60=return_60,
        volatility_20=volatility_20,
        matched_cohort=matched,
        calculation_status=status,
        diagnostics=PriceBehaviorDiagnostics(source_exclusions=source_exclusions),
        warnings=warnings,
    )


def _momentum_values(
    *,
    prior_session_count: int,
    codes: list[str],
    sessions: list[str],
    lookup: dict[tuple[str, str], Record],
    is_no_trade: RecordPredicate,
    is_valid_traded_record: RecordPredicate,
) -> _MetricValues:
    required = prior_session_count + 1
    window = _window(prior_session_count, sessions)
    if len(sessions) < required:
        return _insufficient_values(codes, window)
    selected_sessions = sessions[-required:]
    values: dict[str, float] = {}
    issues: list[PriceBehaviorIssue] = []
    for code in codes:
        closes, issue = _complete_closes(
            code,
            selected_sessions,
            lookup,
            is_no_trade,
            is_valid_traded_record,
        )
        if issue is not None:
            issues.append(issue)
            continue
        assert closes is not None
        result = float(closes[-1] / closes[0] - 1.0)
        if not isfinite(result):
            issues.append(
                PriceBehaviorIssue(code, "non_finite_calculation", selected_sessions[-1])
            )
            continue
        values[code] = result
    reason, status = _metric_state(len(values), len(codes))
    return _MetricValues(values, issues, window, reason, status)


def _volatility_values(
    *,
    codes: list[str],
    sessions: list[str],
    lookup: dict[tuple[str, str], Record],
    is_no_trade: RecordPredicate,
    is_valid_traded_record: RecordPredicate,
) -> _MetricValues:
    window = _window(20, sessions)
    if len(sessions) < 21:
        return _insufficient_values(codes, window)
    selected_sessions = sessions[-21:]
    values: dict[str, float] = {}
    issues: list[PriceBehaviorIssue] = []
    for code in codes:
        closes, issue = _complete_closes(
            code,
            selected_sessions,
            lookup,
            is_no_trade,
            is_valid_traded_record,
        )
        if issue is not None:
            issues.append(issue)
            continue
        assert closes is not None
        returns: list[float] = []
        for previous, current in zip(closes, closes[1:]):
            value = float(current / previous - 1.0)
            if not isfinite(value):
                issue = PriceBehaviorIssue(
                    code, "non_finite_calculation", selected_sessions[len(returns) + 1]
                )
                break
            returns.append(value)
        if issue is not None:
            issues.append(issue)
            continue
        volatility = _safe_annualized_sample_volatility(returns)
        if volatility is None:
            issues.append(
                PriceBehaviorIssue(code, "non_finite_calculation", selected_sessions[-1])
            )
            continue
        values[code] = volatility
    reason, status = _metric_state(len(values), len(codes))
    return _MetricValues(values, issues, window, reason, status)


def _complete_closes(
    code: str,
    sessions: list[str],
    lookup: dict[tuple[str, str], Record],
    is_no_trade: RecordPredicate,
    is_valid_traded_record: RecordPredicate,
) -> tuple[list[float] | None, PriceBehaviorIssue | None]:
    closes: list[float] = []
    for session in sessions:
        record = lookup.get((session, code))
        reason = _close_issue(record, is_no_trade, is_valid_traded_record)
        if reason is not None:
            return None, PriceBehaviorIssue(code, reason, session)
        assert record is not None
        closes.append(float(record["close"]))
    return closes, None


def _close_issue(
    record: Record | None,
    is_no_trade: RecordPredicate,
    is_valid_traded_record: RecordPredicate,
) -> PriceBehaviorIssueReason | None:
    if record is None:
        return "missing_required_row"
    if is_no_trade(record):
        return "no_trade_required_row"
    close = record.get("close")
    if close is None:
        return "invalid_close_required_row"
    if not isfinite(close):
        return "non_finite_close_required_row"
    if close <= 0:
        return "non_positive_close_required_row"
    if not is_valid_traded_record(record):
        return "invalid_traded_record_required_row"
    return None


def _momentum_summary(
    metric: Literal["return_20", "return_60"],
    codes: list[str],
    result: _MetricValues,
) -> MomentumSummary:
    values = list(result.values.values())
    median = _safe_median(values)
    reason = result.reason
    status = result.status
    if values and median is None:
        median = None
        reason = "non_finite_aggregate"
        status = "unavailable"
    positive_count = sum(value > 0 for value in values)
    non_positive_count = len(values) - positive_count
    positive_share = _safe_share(positive_count, len(values))
    return MomentumSummary(
        metric=metric,
        window=result.window,
        requested_stock_count=len(codes),
        eligible_stock_count=len(values),
        unavailable_stock_count=len(codes) - len(values),
        median_return=median,
        positive_count=positive_count,
        non_positive_count=non_positive_count,
        positive_share=positive_share,
        calculation_status=status,
        reason=reason,
        diagnostics=_metric_diagnostics(result.issues),
    )


def _volatility_summary(
    codes: list[str],
    result: _MetricValues,
) -> VolatilitySummary:
    values = list(result.values.values())
    median = _safe_median(values)
    reason = result.reason
    status = result.status
    if values and median is None:
        reason = "non_finite_aggregate"
        status = "unavailable"
    return VolatilitySummary(
        metric="volatility_20",
        window=result.window,
        requested_stock_count=len(codes),
        eligible_stock_count=len(values),
        unavailable_stock_count=len(codes) - len(values),
        median_annualized_volatility=median,
        ddof=1,
        annualization_factor=252,
        calculation_status=status,
        reason=reason,
        diagnostics=_metric_diagnostics(result.issues),
    )


def _matched_cohort(
    *,
    codes: list[str],
    return_20: dict[str, float],
    return_60: dict[str, float],
    volatility_20: dict[str, float],
) -> PriceBehaviorMatchedCohort:
    matched_codes = sorted(set(return_20) & set(return_60) & set(volatility_20))
    unavailable = _identifier_sample(sorted(set(codes) - set(matched_codes)))
    empty_quadrants = _quadrants({}, len(matched_codes))
    if not matched_codes:
        return PriceBehaviorMatchedCohort(
            requested_stock_count=len(codes),
            matched_cohort_count=0,
            unavailable_stock_count=unavailable.exact_count,
            unavailable_stock_codes=unavailable.values,
            unavailable_stock_codes_truncated=unavailable.truncated,
            unavailable_stock_codes_omitted_count=unavailable.omitted_count,
            matched_median_annualized_volatility=None,
            calculation_status="unavailable",
            reason="empty_matched_cohort",
            quadrants=empty_quadrants,
        )
    median = _safe_median([volatility_20[code] for code in matched_codes])
    if median is None:
        return PriceBehaviorMatchedCohort(
            requested_stock_count=len(codes),
            matched_cohort_count=len(matched_codes),
            unavailable_stock_count=unavailable.exact_count,
            unavailable_stock_codes=unavailable.values,
            unavailable_stock_codes_truncated=unavailable.truncated,
            unavailable_stock_codes_omitted_count=unavailable.omitted_count,
            matched_median_annualized_volatility=None,
            calculation_status="unavailable",
            reason="non_finite_aggregate",
            quadrants=empty_quadrants,
        )
    members: dict[str, list[str]] = {
        "positive_momentum_lower_or_equal_volatility": [],
        "positive_momentum_higher_volatility": [],
        "non_positive_momentum_lower_or_equal_volatility": [],
        "non_positive_momentum_higher_volatility": [],
    }
    for code in matched_codes:
        momentum_label = (
            "positive_momentum" if return_60[code] > 0 else "non_positive_momentum"
        )
        volatility_label = (
            "lower_or_equal_volatility"
            if volatility_20[code] <= median
            else "higher_volatility"
        )
        members[f"{momentum_label}_{volatility_label}"].append(code)
    status: PriceBehaviorCalculationStatus = (
        "complete" if len(matched_codes) == len(codes) else "partial"
    )
    reason = "complete" if status == "complete" else "partial_matched_cohort"
    return PriceBehaviorMatchedCohort(
        requested_stock_count=len(codes),
        matched_cohort_count=len(matched_codes),
        unavailable_stock_count=unavailable.exact_count,
        unavailable_stock_codes=unavailable.values,
        unavailable_stock_codes_truncated=unavailable.truncated,
        unavailable_stock_codes_omitted_count=unavailable.omitted_count,
        matched_median_annualized_volatility=median,
        calculation_status=status,
        reason=reason,
        quadrants=_quadrants(members, len(matched_codes)),
    )


def _quadrants(
    members: dict[str, list[str]],
    denominator: int,
) -> PriceBehaviorQuadrants:
    def bucket(key: str) -> PriceBehaviorBucket:
        sample = _identifier_sample(members.get(key, []))
        return PriceBehaviorBucket(
            count=sample.exact_count,
            share=_safe_share(sample.exact_count, denominator),
            stock_codes=sample.values,
            stock_codes_truncated=sample.truncated,
            stock_codes_omitted_count=sample.omitted_count,
        )

    return PriceBehaviorQuadrants(
        positive_momentum_lower_or_equal_volatility=bucket(
            "positive_momentum_lower_or_equal_volatility"
        ),
        positive_momentum_higher_volatility=bucket(
            "positive_momentum_higher_volatility"
        ),
        non_positive_momentum_lower_or_equal_volatility=bucket(
            "non_positive_momentum_lower_or_equal_volatility"
        ),
        non_positive_momentum_higher_volatility=bucket(
            "non_positive_momentum_higher_volatility"
        ),
    )


def _window(prior_session_count: int, sessions: list[str]) -> PriceBehaviorWindow:
    required = prior_session_count + 1
    observed = min(len(sessions), required)
    return PriceBehaviorWindow(
        prior_session_count=prior_session_count,
        required_close_count=required,
        required_return_count=prior_session_count,
        observed_open_session_count=observed,
        window_start_session=(
            sessions[-required] if len(sessions) >= required else sessions[0]
        ),
        window_end_session=sessions[-1],
    )


def _insufficient_values(
    codes: list[str],
    window: PriceBehaviorWindow,
) -> _MetricValues:
    issues = [
        PriceBehaviorIssue(code, "insufficient_open_session_history", None)
        for code in codes
    ]
    return _MetricValues(
        values={},
        issues=issues,
        window=window,
        reason="insufficient_open_session_history",
        status="unavailable",
    )


def _metric_state(
    eligible_count: int,
    requested_count: int,
) -> tuple[PriceBehaviorMetricReason, PriceBehaviorCalculationStatus]:
    if requested_count == 0:
        return "empty_eligible_cohort", "unavailable"
    if eligible_count == requested_count:
        return "complete", "complete"
    if eligible_count > 0:
        return "partial_eligible_cohort", "partial"
    return "empty_eligible_cohort", "unavailable"


def _safe_annualized_sample_volatility(returns: list[float]) -> float | None:
    if len(returns) != 20 or any(not isfinite(value) for value in returns):
        return None
    scale = max(abs(value) for value in returns)
    if scale == 0:
        return 0.0
    scaled = [value / scale for value in returns]
    try:
        mean = fsum(scaled) / len(scaled)
        variance = fsum((value - mean) ** 2 for value in scaled) / (
            len(scaled) - 1
        )
        result = float(sqrt(variance) * scale * sqrt(252.0))
    except (OverflowError, ValueError):
        return None
    return result if isfinite(result) else None


def _safe_median(values: list[float]) -> float | None:
    if not values or any(not isfinite(value) for value in values):
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    lower = ordered[middle - 1]
    upper = ordered[middle]
    result = float(lower + (upper - lower) / 2.0)
    return result if isfinite(result) else None


def _safe_share(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    value = float(numerator / denominator)
    return value if isfinite(value) else None


def _metric_diagnostics(
    issues: list[PriceBehaviorIssue],
) -> PriceBehaviorMetricDiagnostics:
    ordered = sorted(issues, key=lambda item: item.stock_code)
    bounded = ordered[:PRICE_BEHAVIOR_IDENTIFIER_SAMPLE_LIMIT]
    return PriceBehaviorMetricDiagnostics(
        issue_count=len(ordered),
        issues=bounded,
        issues_truncated=len(ordered) > len(bounded),
        issues_omitted_count=len(ordered) - len(bounded),
    )


def _identifier_sample(values: list[str]) -> _IdentifierSample:
    ordered = sorted(set(values))
    bounded = ordered[:PRICE_BEHAVIOR_IDENTIFIER_SAMPLE_LIMIT]
    return _IdentifierSample(
        values=bounded,
        exact_count=len(ordered),
        truncated=len(ordered) > len(bounded),
        omitted_count=len(ordered) - len(bounded),
    )


def _warnings(
    *,
    return_20: MomentumSummary,
    return_60: MomentumSummary,
    volatility_20: VolatilitySummary,
    matched: PriceBehaviorMatchedCohort,
    source_exclusions: list[PriceBehaviorSourceExclusion],
) -> list[str]:
    warnings: list[str] = []
    for summary in (return_20, return_60, volatility_20):
        if summary.reason == "complete":
            continue
        diagnostics = summary.diagnostics
        sample = [issue.stock_code for issue in diagnostics.issues]
        suffix = (
            f" (+{diagnostics.issues_omitted_count} more)"
            if diagnostics.issues_truncated
            else ""
        )
        warnings.append(
            f"{summary.metric} status is {summary.reason}; unavailable count="
            f"{summary.unavailable_stock_count}, sample={sample}{suffix}."
        )
    if matched.reason != "complete":
        suffix = (
            f" (+{matched.unavailable_stock_codes_omitted_count} more)"
            if matched.unavailable_stock_codes_truncated
            else ""
        )
        warnings.append(
            f"Price-behavior matched cohort status is {matched.reason}; matched="
            f"{matched.matched_cohort_count}/{matched.requested_stock_count}, unavailable "
            f"count={matched.unavailable_stock_count}, sample="
            f"{matched.unavailable_stock_codes}{suffix}."
        )
    for exclusion in source_exclusions:
        suffix = (
            f" (+{exclusion.stock_codes_omitted_count} more)"
            if exclusion.stock_codes_truncated
            else ""
        )
        warnings.append(
            f"Accepted equity filtering excluded {exclusion.excluded_row_count} rows for "
            f"{exclusion.reason}; stock count={exclusion.stock_code_count}, sample="
            f"{exclusion.stock_codes}{suffix}."
        )
    return warnings
