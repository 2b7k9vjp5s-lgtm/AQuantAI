"""Deterministic weekly backtest foundation using explicit next-day execution."""

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
    """Top-N equal-weight weekly backtest with next-trading-date execution."""

    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config or BacktestConfig()
        if self.config.rebalance.top_n <= 0:
            raise ValueError("top_n must be positive")
        if self.config.initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        if self.config.rebalance.frequency != "W":
            raise ValueError("Only weekly rebalance frequency 'W' is supported")

    def select_portfolio(self, scores: pd.DataFrame) -> PortfolioSelection:
        """Select top-N holdings per score date and universe deterministically."""
        frame = _normalize_scores(scores)
        selected = (
            frame.sort_values(
                ["score_date", "universe", "rank", "score", "stock_code"],
                ascending=[True, True, True, False, True],
                kind="stable",
            )
            .groupby(["score_date", "universe"], as_index=False, sort=False)
            .head(self.config.rebalance.top_n)
            .copy()
        )
        selected["selection_count"] = selected.groupby(["score_date", "universe"])["stock_code"].transform("count")
        selected["weight"] = 1.0 / selected["selection_count"]
        selected = selected.rename(columns={"score_date": "signal_date"})
        selected["rebalance_date"] = selected["signal_date"]
        return PortfolioSelection(selected[HOLDING_COLUMNS].reset_index(drop=True))

    def run(self, prices: pd.DataFrame, scores: pd.DataFrame) -> BacktestResult:
        """Run a deterministic long-only equal-weight backtest."""
        price_frame = _prepare_prices(prices)
        selection = self.select_portfolio(scores)
        holdings = selection.holdings.copy()
        if holdings["universe"].nunique() != 1:
            raise ValueError("Backtest run supports exactly one universe per score input")

        pivot_returns = price_frame.pivot(index="trade_date", columns="stock_code", values="daily_return").sort_index()
        trade_dates = list(pivot_returns.index)
        execution_map = _build_execution_date_map(list(holdings["signal_date"].unique()), trade_dates)
        if not execution_map:
            raise ValueError("No score dates have a later available trading date")
        holdings = holdings[holdings["signal_date"].isin(execution_map)].copy()
        holdings["rebalance_date"] = holdings["signal_date"].map(execution_map)
        rebalance_dates = set(execution_map.values())

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
        metrics = _compute_metrics(
            equity_curve,
            self.config.initial_cash,
            self.config.trading_days_per_year,
            self.config.risk_free_rate,
        )
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
            holdings=holdings[HOLDING_COLUMNS].sort_values(["rebalance_date", "stock_code"]).reset_index(drop=True),
        )


def _validate_prices(prices: pd.DataFrame) -> None:
    require_non_empty(prices, "prices")
    require_columns(prices, PRICE_COLUMNS, "prices")


def _prepare_prices(prices: pd.DataFrame) -> pd.DataFrame:
    _validate_prices(prices)
    frame = prices.copy()
    frame["trade_date"] = frame["trade_date"].astype(str)
    frame["stock_code"] = frame["stock_code"].astype(str)
    if frame.duplicated(["trade_date", "stock_code"]).any():
        raise ValueError("prices contains duplicate (trade_date, stock_code) rows")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    if frame["close"].isna().any() or not np.isfinite(frame["close"]).all():
        raise ValueError("prices must contain finite close values")
    if (frame["close"] <= 0).any():
        raise ValueError("prices must contain positive close values")
    frame = frame.sort_values(["stock_code", "trade_date"], kind="stable")
    frame["daily_return"] = frame.groupby("stock_code", sort=False)["close"].pct_change().fillna(0.0)
    return frame


def _validate_scores(scores: pd.DataFrame) -> None:
    require_non_empty(scores, "scores")
    require_columns(scores, SCORE_COLUMNS, "scores")


def _normalize_scores(scores: pd.DataFrame) -> pd.DataFrame:
    _validate_scores(scores)
    frame = scores.copy()
    frame["score_date"] = frame["score_date"].astype(str)
    frame["stock_code"] = frame["stock_code"].astype(str)
    frame["universe"] = frame["universe"].astype(str)
    if frame.duplicated(["score_date", "stock_code", "universe"]).any():
        raise ValueError("scores contains duplicate (score_date, stock_code, universe) rows")
    for column in ("score", "rank"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        if frame[column].isna().any() or not np.isfinite(frame[column]).all():
            raise ValueError(f"scores must contain finite {column} values")
    if (frame["rank"] < 1).any():
        raise ValueError("scores must contain positive rank values")
    if frame["universe"].eq("").any():
        raise ValueError("scores must contain a non-empty universe")
    return frame


def _build_execution_date_map(signal_dates: list[str], trade_dates: list[str]) -> dict[str, str]:
    aligned: dict[str, str] = {}
    for signal_date in sorted(signal_dates):
        candidates = [trade_date for trade_date in trade_dates if trade_date > signal_date]
        if candidates:
            aligned[signal_date] = candidates[0]
    execution_dates = list(aligned.values())
    if len(execution_dates) != len(set(execution_dates)):
        raise ValueError("Multiple signal dates map to the same execution date")
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


def _compute_metrics(
    equity_curve: pd.DataFrame,
    initial_cash: float,
    trading_days_per_year: int,
    risk_free_rate: float,
) -> dict[str, float]:
    returns = pd.to_numeric(equity_curve["portfolio_return"], errors="coerce").fillna(0.0)
    equity = pd.to_numeric(equity_curve["equity"], errors="coerce")
    total_return = float(equity.iloc[-1] / initial_cash - 1.0)
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
