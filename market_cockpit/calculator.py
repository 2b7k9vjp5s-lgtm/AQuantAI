"""Deterministic point-in-time Market Cockpit calculations."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Literal

import numpy as np
import pandas as pd

from market_cockpit.contracts import (
    CalculationStatus,
    LatestDataDiagnostics,
    LatestReturnIssue,
    LatestReturnIssueReason,
    LatestSessionMetrics,
    MarketCockpitMetrics,
    ParticipationMetric,
    RiskMetrics,
    WindowBreadthMetrics,
)
from market_cockpit.liquidity_calculator import calculate_liquidity_context
from market_cockpit.liquidity_contracts import (
    LiquidityContext,
    LiquiditySourceExclusion,
    LiquiditySourceExclusionReason,
)
from market_cockpit.repository import PersistedMarketDataSnapshot

RETURN_EPSILON = 1e-12


class MarketCockpitCalculationError(ValueError):
    """Raised when a selected snapshot has no usable point-in-time session."""


@dataclass(frozen=True)
class MarketCockpitCalculation:
    effective_as_of_session: str
    metrics: MarketCockpitMetrics
    available_stock_count: int
    calculation_status: CalculationStatus
    latest_data_diagnostics: LatestDataDiagnostics
    liquidity_context: LiquidityContext
    warnings: list[str]


@dataclass(frozen=True)
class LatestReturnClassification:
    stock_code: str
    return_value: float | None
    issue: LatestReturnIssue | None


def calculate_market_cockpit(
    snapshot: PersistedMarketDataSnapshot,
    *,
    as_of_cutoff: str | None = None,
) -> MarketCockpitCalculation:
    """Calculate selected-universe metrics from one physical snapshot only."""
    expected_codes = sorted(snapshot.stock_codes)
    warnings: list[str] = []
    liquidity_exclusions: list[LiquiditySourceExclusion] = []
    bound = min(
        value
        for value in (
            snapshot.information_cutoff_date,
            snapshot.requested_end_date,
            _compact_optional_date(as_of_cutoff),
        )
        if value is not None
    )

    calendar = snapshot.trade_calendar.copy()
    calendar["trade_date"] = calendar["trade_date"].map(_compact_date)
    duplicate_calendar_dates = sorted(
        calendar.loc[calendar.duplicated(["trade_date"], keep=False), "trade_date"].unique()
    )
    if duplicate_calendar_dates:
        warnings.append(
            f"Duplicate trade-calendar sessions were excluded: {duplicate_calendar_dates}."
        )
        calendar = calendar.loc[~calendar["trade_date"].isin(duplicate_calendar_dates)]
    sessions = sorted(
        calendar.loc[
            calendar["is_open"].eq(True) & calendar["trade_date"].le(bound),
            "trade_date",
        ].unique()
    )
    if not sessions:
        raise MarketCockpitCalculationError(
            "The selected snapshot has no open trade-calendar session at or before the effective cutoff."
        )
    effective_session = sessions[-1]

    prices = snapshot.daily_price.copy()
    prices["trade_date"] = prices["trade_date"].map(_compact_date)
    future_rows = prices["trade_date"].gt(effective_session)
    if future_rows.any():
        liquidity_exclusions.append(
            _liquidity_source_exclusion("future_price_rows", prices.loc[future_rows])
        )
        warnings.append(
            f"Excluded {int(future_rows.sum())} price rows after effective session {effective_session}."
        )
    prices = prices.loc[~future_rows]
    out_of_calendar = ~prices["trade_date"].isin(sessions)
    if out_of_calendar.any():
        liquidity_exclusions.append(
            _liquidity_source_exclusion(
                "out_of_calendar_price_rows", prices.loc[out_of_calendar]
            )
        )
        warnings.append(
            f"Excluded {int(out_of_calendar.sum())} price rows outside persisted open sessions."
        )
    prices = prices.loc[~out_of_calendar]
    wrong_scope = ~prices["stock_code"].isin(expected_codes)
    if wrong_scope.any():
        liquidity_exclusions.append(
            _liquidity_source_exclusion("wrong_scope_price_rows", prices.loc[wrong_scope])
        )
        warnings.append(
            f"Excluded price rows outside the exact selected scope: "
            f"{sorted(prices.loc[wrong_scope, 'stock_code'].astype(str).unique())}."
        )
    prices = prices.loc[~wrong_scope]
    wrong_adjust = ~prices["adjust_type"].fillna("").eq(snapshot.adjust_type)
    if wrong_adjust.any():
        liquidity_exclusions.append(
            _liquidity_source_exclusion(
                "wrong_adjustment_price_rows", prices.loc[wrong_adjust]
            )
        )
        warnings.append(
            f"Excluded {int(wrong_adjust.sum())} rows with an incompatible adjustment policy."
        )
    prices = prices.loc[~wrong_adjust]
    duplicate_keys = prices.duplicated(["trade_date", "stock_code"], keep=False)
    if duplicate_keys.any():
        liquidity_exclusions.append(
            _liquidity_source_exclusion(
                "duplicate_stock_session_price_rows", prices.loc[duplicate_keys]
            )
        )
        duplicate_labels = sorted(
            prices.loc[duplicate_keys, ["trade_date", "stock_code"]]
            .astype(str)
            .agg(":".join, axis=1)
            .unique()
        )
        warnings.append(f"Duplicate stock-session prices were excluded: {duplicate_labels}.")
        prices = prices.loc[~duplicate_keys]

    stock_basic_codes = sorted(snapshot.stock_basic["stock_code"].astype(str).unique())
    if stock_basic_codes != expected_codes:
        warnings.append(
            "Stock-basic rows do not exactly match the canonical selected scope; "
            f"expected={expected_codes}, observed={stock_basic_codes}."
        )
    inactive = sorted(
        snapshot.stock_basic.loc[
            ~snapshot.stock_basic["status"].astype(str).str.lower().eq("active"),
            "stock_code",
        ].astype(str).unique()
    )
    if inactive:
        warnings.append(f"Selected scope contains non-active stock records: {inactive}.")

    price_lookup = _price_lookup(prices)
    latest_classifications = _classify_latest_returns(
        expected_codes,
        sessions,
        price_lookup,
    )
    if len(sessions) < 2:
        warnings.append("Latest-session returns require at least two persisted open sessions.")
    latest_diagnostics = _latest_data_diagnostics(latest_classifications, warnings)
    latest = _latest_metrics(latest_classifications, len(expected_codes), warnings)
    if (
        latest_diagnostics.latest_return_unavailable_count != latest.unavailable_count
        or len(latest_diagnostics.latest_return_issues) != latest.unavailable_count
    ):
        raise MarketCockpitCalculationError(
            "Latest-return diagnostics must contain exactly one issue per unavailable return."
        )
    breadth_20 = _window_breadth(20, expected_codes, sessions, price_lookup, warnings)
    breadth_60 = _window_breadth(60, expected_codes, sessions, price_lookup, warnings)
    volume_participation = _participation(
        "volume", expected_codes, sessions, price_lookup, warnings
    )
    amount_participation = _participation(
        "amount", expected_codes, sessions, price_lookup, warnings
    )
    risk = _risk_metrics(expected_codes, sessions, price_lookup, warnings)
    liquidity_context = calculate_liquidity_context(
        stock_codes=expected_codes,
        expected_sessions=sessions,
        effective_session=effective_session,
        price_lookup=price_lookup,
        source_exclusions=liquidity_exclusions,
        is_no_trade=_is_no_trade,
        is_valid_traded_record=_is_valid_traded_record,
    )
    available_count = (
        latest.advancing_count + latest.declining_count + latest.unchanged_count
    )
    calculation_status = _calculation_status(
        expected_codes,
        available_count,
        breadth_20,
        breadth_60,
        volume_participation,
        amount_participation,
        risk,
        warnings,
    )
    return MarketCockpitCalculation(
        effective_as_of_session=effective_session,
        metrics=MarketCockpitMetrics(
            latest_session=latest,
            breadth_20=breadth_20,
            breadth_60=breadth_60,
            volume_participation=volume_participation,
            amount_participation=amount_participation,
            equal_weight_risk=risk,
        ),
        available_stock_count=available_count,
        calculation_status=calculation_status,
        latest_data_diagnostics=latest_diagnostics,
        liquidity_context=liquidity_context,
        warnings=warnings,
    )


def _price_lookup(prices: pd.DataFrame) -> dict[tuple[str, str], dict[str, float]]:
    lookup: dict[tuple[str, str], dict[str, float]] = {}
    for row in prices.to_dict(orient="records"):
        lookup[(str(row["trade_date"]), str(row["stock_code"]))] = {
            "close": float(row["close"]),
            "volume": float(row["volume"]),
            "amount": float(row["amount"]),
        }
    return lookup


def _latest_metrics(
    classifications: list[LatestReturnClassification],
    stock_count: int,
    warnings: list[str],
) -> LatestSessionMetrics:
    returns = [
        item.return_value
        for item in classifications
        if item.return_value is not None
    ]
    advancing = sum(value > RETURN_EPSILON for value in returns)
    declining = sum(value < -RETURN_EPSILON for value in returns)
    unchanged = len(returns) - advancing - declining
    if not returns:
        warnings.append("No selected stock has an available latest-session return.")
        return LatestSessionMetrics(None, None, 0, 0, 0, stock_count, None, None, None)
    values = np.asarray(returns, dtype=float)
    return LatestSessionMetrics(
        equal_weight_mean_return=float(values.mean()),
        median_return=float(np.median(values)),
        advancing_count=advancing,
        declining_count=declining,
        unchanged_count=unchanged,
        unavailable_count=stock_count - len(returns),
        advance_ratio=float(advancing / len(returns)),
        breadth_balance=float((advancing - declining) / len(returns)),
        return_dispersion=float(values.std(ddof=0)),
    )


def _window_breadth(
    window: int,
    codes: list[str],
    sessions: list[str],
    lookup: dict[tuple[str, str], dict[str, float]],
    warnings: list[str],
) -> WindowBreadthMetrics:
    if len(sessions) < window:
        warnings.append(
            f"{window}-session moving-average and new-high/new-low metrics require "
            f"{window} persisted open sessions; observed {len(sessions)}."
        )
        return WindowBreadthMetrics(window, None, None, None, None, 0)
    selected_sessions = sessions[-window:]
    above = 0
    highs = 0
    lows = 0
    eligible = 0
    unavailable: list[str] = []
    for code in codes:
        closes = [
            _value(
                lookup,
                session,
                code,
                "close",
                positive=True,
                require_trade=True,
            )
            for session in selected_sessions
        ]
        if any(value is None for value in closes):
            unavailable.append(code)
            continue
        values = np.asarray(closes, dtype=float)
        current = float(values[-1])
        eligible += 1
        above += int(current > float(values.mean()))
        highs += int(current >= float(values.max()) - RETURN_EPSILON)
        lows += int(current <= float(values.min()) + RETURN_EPSILON)
    if unavailable:
        warnings.append(f"{window}-session history is incomplete for stocks: {unavailable}.")
    if eligible == 0:
        return WindowBreadthMetrics(window, None, None, None, None, 0)
    return WindowBreadthMetrics(
        window_sessions=window,
        above_sma_ratio=float(above / eligible),
        above_sma_count=above,
        new_high_count=highs,
        new_low_count=lows,
        eligible_stock_count=eligible,
    )


def _participation(
    field: str,
    codes: list[str],
    sessions: list[str],
    lookup: dict[tuple[str, str], dict[str, float]],
    warnings: list[str],
) -> ParticipationMetric:
    if len(sessions) < 21:
        warnings.append(
            f"{field.capitalize()} participation requires 21 persisted open sessions; "
            f"observed {len(sessions)}."
        )
        return ParticipationMetric(None, 0)
    prior_sessions = sessions[-21:-1]
    current_session = sessions[-1]
    ratios: list[float] = []
    unavailable: list[str] = []
    for code in codes:
        history = [
            _value(
                lookup,
                session,
                code,
                field,
                nonnegative=True,
                require_trade=True,
            )
            for session in prior_sessions
        ]
        current = _value(
            lookup,
            current_session,
            code,
            field,
            nonnegative=True,
            require_trade=True,
        )
        if current is None or any(value is None for value in history):
            unavailable.append(code)
            continue
        baseline = float(np.median(np.asarray(history, dtype=float)))
        if baseline <= 0:
            unavailable.append(code)
            continue
        ratios.append(current / baseline)
    if unavailable:
        warnings.append(
            f"{field.capitalize()} participation is unavailable for stocks: {unavailable}."
        )
    return ParticipationMetric(
        ratio_to_prior_20_session_median=(float(np.mean(ratios)) if ratios else None),
        eligible_stock_count=len(ratios),
    )


def _risk_metrics(
    codes: list[str],
    sessions: list[str],
    lookup: dict[tuple[str, str], dict[str, float]],
    warnings: list[str],
) -> RiskMetrics:
    if len(sessions) < 21:
        warnings.append(
            f"Equal-weight risk requires 21 persisted open sessions for 20 returns; "
            f"observed {len(sessions)}."
        )
        return RiskMetrics(None, None, max(len(sessions) - 1, 0))
    selected_sessions = sessions[-21:]
    universe_returns: list[float] = []
    for previous_session, current_session in zip(selected_sessions, selected_sessions[1:]):
        stock_returns: list[float] = []
        for code in codes:
            previous = _value(
                lookup,
                previous_session,
                code,
                "close",
                positive=True,
                require_trade=True,
            )
            current = _value(
                lookup,
                current_session,
                code,
                "close",
                positive=True,
                require_trade=True,
            )
            if previous is None or current is None:
                stock_returns = []
                break
            stock_returns.append(current / previous - 1.0)
        if len(stock_returns) == len(codes):
            universe_returns.append(float(np.mean(stock_returns)))
    if len(universe_returns) != 20:
        warnings.append(
            "Equal-weight risk is unavailable because the trailing 20 return sessions do not "
            "have complete selected-universe closes."
        )
        return RiskMetrics(None, None, len(universe_returns))
    values = np.asarray(universe_returns, dtype=float)
    volatility = float(values.std(ddof=1) * sqrt(252.0))
    wealth = np.concatenate(([1.0], np.cumprod(1.0 + values)))
    drawdowns = wealth / np.maximum.accumulate(wealth) - 1.0
    return RiskMetrics(
        realized_volatility_20=volatility,
        max_drawdown_20=float(drawdowns.min()),
        eligible_return_sessions=20,
    )


def _value(
    lookup: dict[tuple[str, str], dict[str, float]],
    session: str,
    code: str,
    field: str,
    *,
    positive: bool = False,
    nonnegative: bool = False,
    require_trade: bool = False,
) -> float | None:
    record = lookup.get((session, code))
    if record is None:
        return None
    if require_trade and not _is_valid_traded_record(record):
        return None
    value = record.get(field)
    if value is None or not isfinite(value):
        return None
    if positive and value <= 0:
        return None
    if nonnegative and value < 0:
        return None
    return value


def _classify_latest_returns(
    codes: list[str],
    sessions: list[str],
    lookup: dict[tuple[str, str], dict[str, float]],
) -> list[LatestReturnClassification]:
    classifications: list[LatestReturnClassification] = []
    if len(sessions) < 2:
        for code in codes:
            classifications.append(
                LatestReturnClassification(
                    stock_code=code,
                    return_value=None,
                    issue=LatestReturnIssue(
                        stock_code=code,
                        reason="missing_previous_session_row",
                        blocking_session=None,
                        last_valid_traded_session=None,
                        open_session_gap=None,
                    ),
                )
            )
        return classifications

    previous_index = len(sessions) - 2
    effective_index = len(sessions) - 1
    for code in codes:
        effective_record = lookup.get((sessions[effective_index], code))
        previous_record = lookup.get((sessions[previous_index], code))
        effective_reason = _record_issue_reason(effective_record, "effective")
        previous_reason = _record_issue_reason(previous_record, "previous")
        if effective_reason is not None:
            issue = _build_latest_return_issue(
                code,
                effective_reason,
                effective_index,
                sessions,
                lookup,
            )
            classifications.append(LatestReturnClassification(code, None, issue))
        elif previous_reason is not None:
            issue = _build_latest_return_issue(
                code,
                previous_reason,
                previous_index,
                sessions,
                lookup,
            )
            classifications.append(LatestReturnClassification(code, None, issue))
        else:
            assert effective_record is not None and previous_record is not None
            classifications.append(
                LatestReturnClassification(
                    stock_code=code,
                    return_value=(
                        float(effective_record["close"]) / float(previous_record["close"]) - 1.0
                    ),
                    issue=None,
                )
            )
    return classifications


def _latest_data_diagnostics(
    classifications: list[LatestReturnClassification],
    warnings: list[str],
) -> LatestDataDiagnostics:
    issues = [item.issue for item in classifications if item.issue is not None]
    effective_stale = [
        issue.stock_code
        for issue in issues
        if issue.reason in {
            "missing_effective_session_row",
            "invalid_effective_session_row",
        }
    ]
    effective_no_trade = [
        issue.stock_code
        for issue in issues
        if issue.reason == "no_trade_effective_session_row"
    ]
    previous_stale = [
        issue.stock_code
        for issue in issues
        if issue.reason in {
            "missing_previous_session_row",
            "invalid_previous_session_row",
        }
    ]
    previous_no_trade = [
        issue.stock_code
        for issue in issues
        if issue.reason == "no_trade_previous_session_row"
    ]
    if effective_stale:
        warnings.append(
            "Effective-session rows are missing or invalid for latest returns; structured "
            f"blocking-session diagnostics are provided: {effective_stale}."
        )
    if effective_no_trade:
        warnings.append(
            "Effective-session zero-volume and zero-amount rows were excluded as potentially "
            f"suspended or no-trade observations: {effective_no_trade}."
        )
    if previous_stale:
        warnings.append(
            "Previous-session rows are missing or invalid for latest returns; structured "
            f"blocking-session diagnostics are provided: {previous_stale}."
        )
    if previous_no_trade:
        warnings.append(
            "Previous-session zero-volume and zero-amount rows were excluded from latest returns "
            f"as potentially suspended or no-trade observations: {previous_no_trade}."
        )
    return LatestDataDiagnostics(
        stale_or_missing_latest_count=len(effective_stale),
        no_trade_latest_count=len(effective_no_trade),
        latest_return_unavailable_count=len(issues),
        latest_return_issues=issues,
    )


def _record_issue_reason(
    record: dict[str, float] | None,
    session_role: Literal["effective", "previous"],
) -> LatestReturnIssueReason | None:
    if record is None:
        return (
            "missing_effective_session_row"
            if session_role == "effective"
            else "missing_previous_session_row"
        )
    if _is_no_trade(record):
        return (
            "no_trade_effective_session_row"
            if session_role == "effective"
            else "no_trade_previous_session_row"
        )
    if not _is_valid_traded_record(record):
        return (
            "invalid_effective_session_row"
            if session_role == "effective"
            else "invalid_previous_session_row"
        )
    return None


def _build_latest_return_issue(
    code: str,
    reason: LatestReturnIssueReason,
    blocking_index: int,
    sessions: list[str],
    lookup: dict[tuple[str, str], dict[str, float]],
) -> LatestReturnIssue:
    last_valid_index: int | None = None
    for index in range(blocking_index - 1, -1, -1):
        session = sessions[index]
        record = lookup.get((session, code))
        if record is not None and _is_valid_traded_record(record):
            last_valid_index = index
            break
    return LatestReturnIssue(
        stock_code=code,
        reason=reason,
        blocking_session=sessions[blocking_index],
        last_valid_traded_session=(
            sessions[last_valid_index] if last_valid_index is not None else None
        ),
        open_session_gap=(
            blocking_index - last_valid_index if last_valid_index is not None else None
        ),
    )


def _is_no_trade(record: dict[str, float]) -> bool:
    volume = record.get("volume")
    amount = record.get("amount")
    return (
        volume is not None
        and amount is not None
        and isfinite(volume)
        and isfinite(amount)
        and volume == 0
        and amount == 0
    )


def _is_valid_traded_record(record: dict[str, float]) -> bool:
    close = record.get("close")
    volume = record.get("volume")
    amount = record.get("amount")
    return (
        close is not None
        and volume is not None
        and amount is not None
        and isfinite(close)
        and isfinite(volume)
        and isfinite(amount)
        and close > 0
        and volume >= 0
        and amount >= 0
        and not _is_no_trade(record)
    )


def _calculation_status(
    codes: list[str],
    available_count: int,
    breadth_20: WindowBreadthMetrics,
    breadth_60: WindowBreadthMetrics,
    volume: ParticipationMetric,
    amount: ParticipationMetric,
    risk: RiskMetrics,
    warnings: list[str],
) -> CalculationStatus:
    if available_count == 0:
        return "insufficient_data"
    full_count = len(codes)
    fully_ready = (
        available_count == full_count
        and breadth_20.eligible_stock_count == full_count
        and breadth_60.eligible_stock_count == full_count
        and volume.eligible_stock_count == full_count
        and amount.eligible_stock_count == full_count
        and risk.eligible_return_sessions == 20
        and not warnings
    )
    return "ready" if fully_ready else "partial"


def _compact_date(value: object) -> str:
    return str(value).strip().replace("-", "")


def _compact_optional_date(value: str | None) -> str | None:
    return _compact_date(value) if value is not None else None


def _liquidity_source_exclusion(
    reason: LiquiditySourceExclusionReason,
    rows: pd.DataFrame,
) -> LiquiditySourceExclusion:
    identifiers = sorted(
        rows.loc[:, ["trade_date", "stock_code"]]
        .astype(str)
        .agg(":".join, axis=1)
        .unique()
    )
    bounded = identifiers[:20]
    return LiquiditySourceExclusion(
        reason=reason,
        excluded_row_count=len(rows),
        identifiers=bounded,
        identifiers_truncated=len(identifiers) > len(bounded),
    )
