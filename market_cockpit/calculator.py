"""Deterministic point-in-time Market Cockpit calculations."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt

import numpy as np
import pandas as pd

from market_cockpit.contracts import (
    CompletenessStatus,
    LatestSessionMetrics,
    MarketCockpitMetrics,
    ParticipationMetric,
    RiskMetrics,
    WindowBreadthMetrics,
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
    completeness_status: CompletenessStatus
    warnings: list[str]


def calculate_market_cockpit(
    snapshot: PersistedMarketDataSnapshot,
    *,
    as_of_cutoff: str | None = None,
) -> MarketCockpitCalculation:
    """Calculate selected-universe metrics from one physical snapshot only."""
    expected_codes = sorted(snapshot.stock_codes)
    warnings: list[str] = []
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
        warnings.append(
            f"Excluded {int(future_rows.sum())} price rows after effective session {effective_session}."
        )
    prices = prices.loc[~future_rows]
    out_of_calendar = ~prices["trade_date"].isin(sessions)
    if out_of_calendar.any():
        warnings.append(
            f"Excluded {int(out_of_calendar.sum())} price rows outside persisted open sessions."
        )
    prices = prices.loc[~out_of_calendar]
    wrong_scope = ~prices["stock_code"].isin(expected_codes)
    if wrong_scope.any():
        warnings.append(
            f"Excluded price rows outside the exact selected scope: "
            f"{sorted(prices.loc[wrong_scope, 'stock_code'].astype(str).unique())}."
        )
    prices = prices.loc[~wrong_scope]
    wrong_adjust = ~prices["adjust_type"].fillna("").eq(snapshot.adjust_type)
    if wrong_adjust.any():
        warnings.append(
            f"Excluded {int(wrong_adjust.sum())} rows with an incompatible adjustment policy."
        )
    prices = prices.loc[~wrong_adjust]
    duplicate_keys = prices.duplicated(["trade_date", "stock_code"], keep=False)
    if duplicate_keys.any():
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
    latest = _latest_metrics(expected_codes, sessions, price_lookup, warnings)
    breadth_20 = _window_breadth(20, expected_codes, sessions, price_lookup, warnings)
    breadth_60 = _window_breadth(60, expected_codes, sessions, price_lookup, warnings)
    volume_participation = _participation(
        "volume", expected_codes, sessions, price_lookup, warnings
    )
    amount_participation = _participation(
        "amount", expected_codes, sessions, price_lookup, warnings
    )
    risk = _risk_metrics(expected_codes, sessions, price_lookup, warnings)
    available_count = (
        latest.advancing_count + latest.declining_count + latest.unchanged_count
    )
    status = _completeness_status(
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
        completeness_status=status,
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
    codes: list[str],
    sessions: list[str],
    lookup: dict[tuple[str, str], dict[str, float]],
    warnings: list[str],
) -> LatestSessionMetrics:
    if len(sessions) < 2:
        warnings.append("Latest-session returns require at least two persisted open sessions.")
        return LatestSessionMetrics(None, None, 0, 0, 0, len(codes), None, None, None)
    previous_session, latest_session = sessions[-2:]
    returns: list[float] = []
    unavailable: list[str] = []
    for code in codes:
        previous = _value(lookup, previous_session, code, "close", positive=True)
        current = _value(lookup, latest_session, code, "close", positive=True)
        if previous is None or current is None:
            unavailable.append(code)
            continue
        returns.append(current / previous - 1.0)
    if unavailable:
        warnings.append(
            "Latest-session return is unavailable for stocks missing a current or previous close: "
            f"{unavailable}."
        )
    advancing = sum(value > RETURN_EPSILON for value in returns)
    declining = sum(value < -RETURN_EPSILON for value in returns)
    unchanged = len(returns) - advancing - declining
    if not returns:
        warnings.append("No selected stock has an available latest-session return.")
        return LatestSessionMetrics(None, None, 0, 0, 0, len(codes), None, None, None)
    values = np.asarray(returns, dtype=float)
    return LatestSessionMetrics(
        equal_weight_mean_return=float(values.mean()),
        median_return=float(np.median(values)),
        advancing_count=advancing,
        declining_count=declining,
        unchanged_count=unchanged,
        unavailable_count=len(codes) - len(returns),
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
        closes = [_value(lookup, session, code, "close", positive=True) for session in selected_sessions]
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
        history = [_value(lookup, session, code, field, nonnegative=True) for session in prior_sessions]
        current = _value(lookup, current_session, code, field, nonnegative=True)
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
            previous = _value(lookup, previous_session, code, "close", positive=True)
            current = _value(lookup, current_session, code, "close", positive=True)
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
) -> float | None:
    record = lookup.get((session, code))
    if record is None:
        return None
    value = record.get(field)
    if value is None or not isfinite(value):
        return None
    if positive and value <= 0:
        return None
    if nonnegative and value < 0:
        return None
    return value


def _completeness_status(
    codes: list[str],
    available_count: int,
    breadth_20: WindowBreadthMetrics,
    breadth_60: WindowBreadthMetrics,
    volume: ParticipationMetric,
    amount: ParticipationMetric,
    risk: RiskMetrics,
    warnings: list[str],
) -> CompletenessStatus:
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
