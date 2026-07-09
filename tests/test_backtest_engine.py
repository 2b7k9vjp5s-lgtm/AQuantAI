import math

import pandas as pd
import pytest

from backtest import BacktestConfig, HOLDING_COLUMNS, RebalanceConfig
from backtest.vectorbt import WeeklyRebalanceBacktestEngine


def _price_fixture() -> pd.DataFrame:
    rows = []
    prices = {
        "000001": [10, 11, 12, 13, 14, 15],
        "000002": [20, 19, 20, 21, 22, 23],
        "000003": [30, 31, 30, 29, 28, 27],
    }
    dates = ["20260101", "20260102", "20260105", "20260106", "20260107", "20260108"]
    for stock_code, closes in prices.items():
        for trade_date, close in zip(dates, closes):
            rows.append({"trade_date": trade_date, "stock_code": stock_code, "close": close})
    return pd.DataFrame(rows)


def _score_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"score_date": "20260101", "stock_code": "000001", "score": 90.0, "rank": 1, "universe": "test"},
            {"score_date": "20260101", "stock_code": "000002", "score": 80.0, "rank": 2, "universe": "test"},
            {"score_date": "20260101", "stock_code": "000003", "score": 70.0, "rank": 3, "universe": "test"},
            {"score_date": "20260105", "stock_code": "000003", "score": 95.0, "rank": 1, "universe": "test"},
            {"score_date": "20260105", "stock_code": "000002", "score": 85.0, "rank": 2, "universe": "test"},
            {"score_date": "20260105", "stock_code": "000001", "score": 75.0, "rank": 3, "universe": "test"},
        ]
    )


def test_top_n_selection_and_equal_weights() -> None:
    engine = WeeklyRebalanceBacktestEngine(BacktestConfig(rebalance=RebalanceConfig(top_n=2)))

    selection = engine.select_portfolio(_score_fixture()).holdings

    assert list(selection.columns) == HOLDING_COLUMNS
    assert set(selection[selection["rebalance_date"] == "20260101"]["stock_code"]) == {"000001", "000002"}
    assert set(selection[selection["rebalance_date"] == "20260105"]["stock_code"]) == {"000003", "000002"}
    weight_sums = selection.groupby("rebalance_date")["weight"].sum()
    assert all(math.isclose(value, 1.0) for value in weight_sums)


def test_weekly_backtest_returns_metrics_and_equity_curve() -> None:
    engine = WeeklyRebalanceBacktestEngine(BacktestConfig(rebalance=RebalanceConfig(top_n=2)))

    result = engine.run(_price_fixture(), _score_fixture())

    assert result.start_date == "20260101"
    assert result.end_date == "20260108"
    assert result.rebalance_count == 2
    assert result.equity_curve["equity"].iloc[0] == pytest.approx(1.0)
    assert result.equity_curve["equity"].iloc[-1] > 0
    assert math.isfinite(result.total_return)
    assert math.isfinite(result.annual_return)
    assert math.isfinite(result.max_drawdown)
    assert math.isfinite(result.volatility)
    assert math.isfinite(result.sharpe_ratio)
    assert result.turnover >= 0


def test_rebalance_dates_align_to_available_trade_dates() -> None:
    scores = _score_fixture().copy()
    scores.loc[scores["score_date"] == "20260105", "score_date"] = "20260104"
    engine = WeeklyRebalanceBacktestEngine(BacktestConfig(rebalance=RebalanceConfig(top_n=1)))

    result = engine.run(_price_fixture(), scores)

    assert set(result.holdings["rebalance_date"]) == {"20260101", "20260105"}
    assert result.rebalance_count == 2


def test_invalid_inputs_fail_with_clear_errors() -> None:
    engine = WeeklyRebalanceBacktestEngine()

    with pytest.raises(ValueError, match="prices must not be empty"):
        engine.run(pd.DataFrame(), _score_fixture())

    with pytest.raises(ValueError, match="scores is missing required columns"):
        engine.select_portfolio(pd.DataFrame([{"stock_code": "000001"}]))

    with pytest.raises(ValueError, match="top_n must be positive"):
        WeeklyRebalanceBacktestEngine(BacktestConfig(rebalance=RebalanceConfig(top_n=0)))
