"""Deterministic weekly backtest foundation.

The module lives under the VectorBT adapter namespace for Phase 3, but the
initial implementation uses pandas to keep tests lightweight and deterministic.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from backtest.base import (
    EQUITY_COLUMNS,
    HOLDING_COLUMNS,
    PRICE_COLUMNS,
    SCORE_COLUMNS,
    BacktestConfig,
    BacktestResult,
    PortfolioSelection,
    require_columns,
    require_non_empty,
)


class WeeklyRebalanceBacktestEngine:
    """Top-N equal-weight weekly rebalance backtest engine."""

    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config or BacktestConfig()
        if self.config.rebalance.top_n <= 0:
            raise ValueError("top_n must be positive")
        if self.config.initial_cash <= 0:
            raise ValueError("initial_cash must be positive")

    def select_portfolio(self, scores: pd.DataFrame) -> PortfolioSelection:
        """Select top-N equal-weight holdings for each score date."""
        _validate_scores(scores)
        frame = scores.copy()
        frame["score_date"] = frame["score_date"].astype(str)
        frame["stock_code"] = frame["stock_code"].astype(str)
        frame["score"] = pd.to_numeric(frame["score"], errors="coerce")
        frame["rank"] = pd.to_numeric(frame["rank"], errors="coerce")
        frame = frame.dropna(subset=["score", "rank"])
        if frame.empty:
            raise ValueError("scores must contain finite score and rank values")

        selected = (
            frame.sort_values(["score_date", "rank", "score"], ascending=[True, True, False])
            .groupby("score_date", as_index=False)
            .head(self.config.rebalance.top_n)
            .copy()
        )
        selected["selection_count"] = selected.groupby("score_date")["stock_code"].transform("count")
        selected["weight"] = 1.0 / selected["selection_count"]
        selected = selected.rename(columns={"score_date": "rebalance_date"})
        return PortfolioSelection(selected[HOLDING_COLUMNS])

    def run(self, prices: pd.DataFrame, scores: pd.DataFrame) -> BacktestResult:
        """Run a deterministic long-only equal-weight backtest."""
        _validate_prices(prices)
        selection = self.select_portfolio(scores)
        price_frame = _prepare_prices(prices)
        holdings = selection.holdings.copy()
        holdings["rebalance_date"] = holdings["rebalance_date"].astype(str)

        pivot_returns = price_frame.pivot(index="trade_date", columns="stock_code", values="daily_return").sort_index()
        trade_dates = list(pivot_returns.index)
        rebalance_date_map = _build_rebalance_date_map(list(holdings["rebalance_date"].unique()), trade_dates)
        if not rebalance_date_map:
            raise ValueError("No score dates align with available price dates")
        holdings["rebalance_date"] = holdings["rebalance_date"].map(rebalance_date_map)
        rebalance_dates = set(rebalance_date_map.values())

        current_weights = pd.Series(dtype=float)
        previous_weights = pd.Series(dtype=float)
        turnover_values: list[float] = []
        returns: list[dict[str, float | str]] = []
        equity = self.config.initial_cash

        for trade_date in trade_dates:
            if trade_date in rebalance_dates:
                current_weights = _weights_for_date(holdings, trade_date)
                turnover_values.append(_turnover(previous_weights, current_weights))
                previous_weights = current_weights

            if current_weights.empty:
                portfolio_return = 0.0
            else:
                day_returns = pivot_returns.loc[trade_date, current_weights.index].fillna(0.0)
                portfolio_return = float((day_returns * current_weights).sum())
            equity *= 1.0 + portfolio_return
            returns.append({"trade_date": trade_date, "portfolio_return": portfolio_return, "equity": equity})

        equity_curve = pd.DataFrame(returns)[EQUITY_COLUMNS]
        metrics = _compute_metrics(equity_curve, self.config.trading_days_per_year, self.config.risk_free_rate)
        metrics["turnover"] = float(np.mean(turnover_values)) if turnover_values else 0.0
        metrics["rebalance_count"] = len(rebalance_dates)

        return BacktestResult(
            start_date=str(equity_curve.iloc[0]["trade_date"]),
            end_date=str(equity_curve.iloc[-1]["trade_date"]),
            total_return=metrics["total_return"],
            annual_return=metrics["annual_return"],
            max_drawdown=metrics["max_drawdown"],
            volatility=metrics["volatility"],
            sharpe_ratio=metrics["sharpe_ratio"],
            turnover=metrics["turnover"],
            rebalance_count=metrics["rebalance_count"],
            equity_curve=equity_curve,
            holdings=holdings,
        )


def _validate_prices(prices: pd.DataFrame) -> None:
    require_non_empty(prices, "prices")
    require_columns(prices, PRICE_COLUMNS, "prices")


def _validate_scores(scores: pd.DataFrame) -> None:
    require_non_empty(scores, "scores")
    require_columns(scores, SCORE_COLUMNS, "scores")


def _prepare_prices(prices: pd.DataFrame) -> pd.DataFrame:
    frame = prices.copy()
    frame["trade_date"] = frame["trade_date"].astype(str)
    frame["stock_code"] = frame["stock_code"].astype(str)
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["close"]).sort_values(["stock_code", "trade_date"])
    if frame.empty:
        raise ValueError("prices must contain finite close values")
    frame["daily_return"] = frame.groupby("stock_code")["close"].pct_change().fillna(0.0)
    return frame


def _build_rebalance_date_map(score_dates: list[str], trade_dates: list[str]) -> dict[str, str]:
    aligned = {}
    for score_date in sorted(score_dates):
        candidates = [trade_date for trade_date in trade_dates if trade_date >= score_date]
        if candidates:
            aligned[score_date] = candidates[0]
    return aligned


def _weights_for_date(holdings: pd.DataFrame, trade_date: str) -> pd.Series:
    frame = holdings[holdings["rebalance_date"] == trade_date]
    if frame.empty:
        return pd.Series(dtype=float)
    return frame.set_index("stock_code")["weight"].astype(float)


def _turnover(previous: pd.Series, current: pd.Series) -> float:
    codes = previous.index.union(current.index)
    previous_aligned = previous.reindex(codes, fill_value=0.0)
    current_aligned = current.reindex(codes, fill_value=0.0)
    return float((current_aligned - previous_aligned).abs().sum() / 2.0)


def _compute_metrics(equity_curve: pd.DataFrame, trading_days_per_year: int, risk_free_rate: float) -> dict[str, float]:
    returns = pd.to_numeric(equity_curve["portfolio_return"], errors="coerce").fillna(0.0)
    equity = pd.to_numeric(equity_curve["equity"], errors="coerce")
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0) if len(equity) > 1 else 0.0
    years = max(len(equity_curve) / trading_days_per_year, 1 / trading_days_per_year)
    annual_return = float((1.0 + total_return) ** (1.0 / years) - 1.0) if total_return > -1 else -1.0
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    max_drawdown = float(drawdown.min())
    volatility = float(returns.std(ddof=0) * math.sqrt(trading_days_per_year))
    excess_daily = returns - risk_free_rate / trading_days_per_year
    sharpe_ratio = 0.0
    if excess_daily.std(ddof=0) > 0:
        sharpe_ratio = float(excess_daily.mean() / excess_daily.std(ddof=0) * math.sqrt(trading_days_per_year))
    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "max_drawdown": max_drawdown,
        "volatility": volatility,
        "sharpe_ratio": sharpe_ratio,
    }
