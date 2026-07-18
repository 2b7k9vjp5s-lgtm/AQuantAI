"""Deterministic liquidity calculations over one accepted equity snapshot."""

from __future__ import annotations

from collections.abc import Callable
from math import ceil, isfinite

import numpy as np

from market_cockpit.liquidity_contracts import (
    LiquidityActivityWindow,
    LiquidityContext,
    LiquidityDiagnostics,
    LiquidityLatestIssue,
    LiquidityLatestIssueReason,
    LiquiditySourceExclusion,
)

Record = dict[str, float]
RecordPredicate = Callable[[Record], bool]


def calculate_liquidity_context(
    *,
    stock_codes: list[str],
    expected_sessions: list[str],
    effective_session: str,
    price_lookup: dict[tuple[str, str], Record],
    source_exclusions: list[LiquiditySourceExclusion],
    is_no_trade: RecordPredicate,
    is_valid_traded_record: RecordPredicate,
) -> LiquidityContext:
    """Calculate exact-session amount distribution without selecting data again."""
    codes = sorted(stock_codes)
    if not expected_sessions or expected_sessions[-1] != effective_session:
        raise ValueError(
            "Liquidity context requires the accepted effective session to end the expected-session sequence."
        )

    latest_values: list[tuple[str, float]] = []
    latest_issues: list[LiquidityLatestIssue] = []
    for code in codes:
        record = price_lookup.get((effective_session, code))
        reason = _amount_issue(record, is_no_trade, is_valid_traded_record)
        if reason is not None:
            latest_issues.append(LiquidityLatestIssue(code, effective_session, reason))
            continue
        assert record is not None
        latest_values.append((code, float(record["amount"])))

    ranked = sorted(latest_values, key=lambda item: (-item[1], item[0]))
    latest_total = float(sum(value for _, value in latest_values)) if latest_values else None
    latest_median = (
        float(np.median(np.asarray([value for _, value in latest_values], dtype=float)))
        if latest_values
        else None
    )
    top5_count = min(5, len(ranked))
    top_decile_count = max(1, ceil(0.10 * len(ranked))) if ranked else 0
    top5_codes = [code for code, _ in ranked[:top5_count]]
    top_decile_codes = [code for code, _ in ranked[:top_decile_count]]
    top5_share = _concentration_share(ranked, top5_count, latest_total)
    top_decile_share = _concentration_share(ranked, top_decile_count, latest_total)

    activity_5, _ = _activity_window(
        prior_session_count=5,
        codes=codes,
        sessions=expected_sessions,
        lookup=price_lookup,
        is_no_trade=is_no_trade,
        is_valid_traded_record=is_valid_traded_record,
    )
    activity_20, matched_20 = _activity_window(
        prior_session_count=20,
        codes=codes,
        sessions=expected_sessions,
        lookup=price_lookup,
        is_no_trade=is_no_trade,
        is_valid_traded_record=is_valid_traded_record,
    )
    above_count, above_share = _above_20_baseline(
        matched_codes=matched_20,
        sessions=expected_sessions,
        lookup=price_lookup,
    )

    warnings = _warnings(
        latest_issues=latest_issues,
        activity_5=activity_5,
        activity_20=activity_20,
        source_exclusions=source_exclusions,
    )
    if not latest_values:
        status = "unavailable"
    elif (
        len(latest_values) == len(codes)
        and activity_5.calculation_status == "complete"
        and activity_20.calculation_status == "complete"
        and not source_exclusions
    ):
        status = "complete"
    else:
        status = "partial"

    return LiquidityContext(
        effective_session=effective_session,
        expected_session_source="selected_equity_snapshot.persisted_trade_calendar",
        requested_stock_count=len(codes),
        latest_eligible_count=len(latest_values),
        latest_unavailable_count=len(codes) - len(latest_values),
        latest_total_amount=latest_total,
        latest_median_amount=latest_median,
        top5_concentration_share=top5_share,
        top5_member_count=top5_count,
        top5_stock_codes=top5_codes,
        top_decile_concentration_share=top_decile_share,
        top_decile_member_count=top_decile_count,
        top_decile_stock_codes=top_decile_codes,
        activity_5=activity_5,
        activity_20=activity_20,
        latest_above_20_session_baseline_count=above_count,
        latest_above_20_session_baseline_share=above_share,
        calculation_status=status,
        diagnostics=LiquidityDiagnostics(
            latest_issues=latest_issues,
            source_exclusions=source_exclusions,
        ),
        warnings=warnings,
    )


def _activity_window(
    *,
    prior_session_count: int,
    codes: list[str],
    sessions: list[str],
    lookup: dict[tuple[str, str], Record],
    is_no_trade: RecordPredicate,
    is_valid_traded_record: RecordPredicate,
) -> tuple[LiquidityActivityWindow, list[str]]:
    required = prior_session_count + 1
    if len(sessions) < required:
        return (
            LiquidityActivityWindow(
                prior_session_count=prior_session_count,
                required_session_count=required,
                observed_session_count=len(sessions),
                window_start_session=sessions[0] if sessions else None,
                window_end_session=sessions[-1] if sessions else None,
                matched_cohort_count=0,
                unavailable_stock_codes=list(codes),
                latest_matched_total_amount=None,
                baseline_total_amount=None,
                activity_ratio=None,
                calculation_status="unavailable",
                reason="insufficient_open_session_history",
            ),
            [],
        )

    selected_sessions = sessions[-required:]
    matched_codes = [
        code
        for code in codes
        if all(
            _eligible_amount(
                lookup.get((session, code)), is_no_trade, is_valid_traded_record
            )
            is not None
            for session in selected_sessions
        )
    ]
    unavailable = sorted(set(codes) - set(matched_codes))
    if not matched_codes:
        return (
            LiquidityActivityWindow(
                prior_session_count=prior_session_count,
                required_session_count=required,
                observed_session_count=required,
                window_start_session=selected_sessions[0],
                window_end_session=selected_sessions[-1],
                matched_cohort_count=0,
                unavailable_stock_codes=unavailable,
                latest_matched_total_amount=None,
                baseline_total_amount=None,
                activity_ratio=None,
                calculation_status="unavailable",
                reason="empty_matched_cohort",
            ),
            [],
        )

    session_totals = [
        float(sum(float(lookup[(session, code)]["amount"]) for code in matched_codes))
        for session in selected_sessions
    ]
    baseline = float(np.median(np.asarray(session_totals[:-1], dtype=float)))
    latest_total = float(session_totals[-1])
    if not isfinite(baseline) or baseline <= 0:
        reason = "invalid_baseline"
        ratio = None
        status = "unavailable"
        baseline_value = None
    else:
        reason = "complete" if not unavailable else "partial_matched_cohort"
        ratio = float(latest_total / baseline)
        status = "complete" if not unavailable else "partial"
        baseline_value = baseline
    return (
        LiquidityActivityWindow(
            prior_session_count=prior_session_count,
            required_session_count=required,
            observed_session_count=required,
            window_start_session=selected_sessions[0],
            window_end_session=selected_sessions[-1],
            matched_cohort_count=len(matched_codes),
            unavailable_stock_codes=unavailable,
            latest_matched_total_amount=latest_total,
            baseline_total_amount=baseline_value,
            activity_ratio=ratio,
            calculation_status=status,
            reason=reason,
        ),
        matched_codes,
    )


def _above_20_baseline(
    *,
    matched_codes: list[str],
    sessions: list[str],
    lookup: dict[tuple[str, str], Record],
) -> tuple[int, float | None]:
    if not matched_codes or len(sessions) < 21:
        return 0, None
    selected_sessions = sessions[-21:]
    count = 0
    for code in matched_codes:
        history = [float(lookup[(session, code)]["amount"]) for session in selected_sessions[:-1]]
        baseline = float(np.median(np.asarray(history, dtype=float)))
        count += int(float(lookup[(selected_sessions[-1], code)]["amount"]) > baseline)
    return count, float(count / len(matched_codes))


def _amount_issue(
    record: Record | None,
    is_no_trade: RecordPredicate,
    is_valid_traded_record: RecordPredicate,
) -> LiquidityLatestIssueReason | None:
    if record is None:
        return "missing_latest_row"
    if is_no_trade(record):
        return "no_trade_latest_row"
    amount = record.get("amount")
    if amount is None or not isfinite(amount) or amount < 0:
        return "invalid_amount_latest_row"
    if amount == 0:
        return "zero_amount_latest_row"
    if not is_valid_traded_record(record):
        return "invalid_traded_record_latest_row"
    return None


def _eligible_amount(
    record: Record | None,
    is_no_trade: RecordPredicate,
    is_valid_traded_record: RecordPredicate,
) -> float | None:
    if _amount_issue(record, is_no_trade, is_valid_traded_record) is not None:
        return None
    assert record is not None
    return float(record["amount"])


def _concentration_share(
    ranked: list[tuple[str, float]],
    member_count: int,
    total: float | None,
) -> float | None:
    if total is None or total <= 0 or member_count == 0:
        return None
    return float(sum(value for _, value in ranked[:member_count]) / total)


def _warnings(
    *,
    latest_issues: list[LiquidityLatestIssue],
    activity_5: LiquidityActivityWindow,
    activity_20: LiquidityActivityWindow,
    source_exclusions: list[LiquiditySourceExclusion],
) -> list[str]:
    warnings: list[str] = []
    if latest_issues:
        warnings.append(
            "Latest-session amount is unavailable for selected stocks: "
            f"{[issue.stock_code for issue in latest_issues]}."
        )
    for window in (activity_5, activity_20):
        if window.reason != "complete":
            warnings.append(
                f"Exact {window.prior_session_count}-prior-session liquidity activity "
                f"window status is {window.reason}; matched cohort="
                f"{window.matched_cohort_count}/{len(window.unavailable_stock_codes) + window.matched_cohort_count}."
            )
    for exclusion in source_exclusions:
        warnings.append(
            f"Accepted equity filtering excluded {exclusion.excluded_row_count} rows for "
            f"{exclusion.reason}."
        )
    return warnings
