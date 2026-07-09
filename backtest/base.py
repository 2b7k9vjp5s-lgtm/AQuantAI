"""Backtesting contracts for AQuantAI."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

PRICE_COLUMNS = ["trade_date", "stock_code", "close"]
SCORE_COLUMNS = ["score_date", "stock_code", "score", "rank", "universe"]
HOLDING_COLUMNS = ["rebalance_date", "stock_code", "weight", "rank", "score", "universe"]
EQUITY_COLUMNS = ["trade_date", "portfolio_return", "equity"]


@dataclass(frozen=True)
class RebalanceConfig:
    """Portfolio rebalance settings."""

    frequency: str = "W"
    top_n: int = 20


@dataclass(frozen=True)
class BacktestConfig:
    """Backtest runtime configuration."""

    initial_cash: float = 1.0
    trading_days_per_year: int = 252
    risk_free_rate: float = 0.0
    rebalance: RebalanceConfig = RebalanceConfig()


@dataclass(frozen=True)
class PortfolioSelection:
    """Selected holdings at each rebalance date."""

    holdings: pd.DataFrame


@dataclass(frozen=True)
class BacktestResult:
    """Backtest metrics and deterministic output series."""

    start_date: str
    end_date: str
    total_return: float
    annual_return: float
    max_drawdown: float
    volatility: float
    sharpe_ratio: float
    turnover: float
    rebalance_count: int
    equity_curve: pd.DataFrame
    holdings: pd.DataFrame


def require_columns(data: pd.DataFrame, columns: list[str], frame_name: str) -> None:
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"{frame_name} is missing required columns: {missing}")


def require_non_empty(data: pd.DataFrame, frame_name: str) -> None:
    if data.empty:
        raise ValueError(f"{frame_name} must not be empty")
