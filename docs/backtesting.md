# Backtesting

Phase 3 creates the backtesting foundation. The goal is deterministic contracts and local-fixture tests, not strategy optimization.

## Input Contracts

Price data must contain:

- `trade_date`
- `stock_code`
- `close`

Score data must contain:

- `score_date`
- `stock_code`
- `score`
- `rank`
- `universe`

## Selection Rule

The initial portfolio construction rule is intentionally small:

- select top N stocks by rank;
- default `top_n = 20`;
- assign equal weights;
- no leverage;
- no shorting.

## Rebalance Frequency

Phase 3 implements a weekly rebalance foundation. A score date is a signal date, not an execution date: the trading calendar maps it to the first available trading date strictly after the signal date. With close-to-close returns, the engine first applies the return ending on each trade date to the holdings already active before that close, records equity, then applies any rebalance after that close. New holdings therefore become active for the next return interval and never receive a move ending on their execution date. Output holdings preserve both `signal_date` and `rebalance_date` (execution date), while standalone portfolio selection leaves the execution date unset until `run()` has a trading calendar.

Only weekly frequency (`W`) is supported in the deterministic foundation; unsupported frequencies are rejected clearly. Top-N selection is deterministic for ties using `stock_code` after rank and score ordering. The engine rejects duplicate price rows, duplicate score rows, non-finite prices, scores, or ranks, non-positive prices, and mixed-universe score inputs in a single backtest run.

## Result Fields

Backtest results include:

- `start_date`
- `end_date`
- `total_return`
- `annual_return`
- `max_drawdown`
- `volatility`
- `sharpe_ratio`
- `turnover`
- `rebalance_count`

The engine also returns a deterministic equity curve and selected holdings.

## Metric Definitions

- Total return: final equity divided by configured initial cash minus one.
- Annual return: total return annualized by configured trading days per year.
- Max drawdown: minimum equity drawdown from the running peak.
- Volatility: annualized standard deviation of daily portfolio returns.
- Sharpe ratio: annualized mean excess daily return divided by daily return volatility.
- Turnover: average one-way absolute weight change at rebalance dates.
- Rebalance count: number of rebalance dates applied to the backtest.

## VectorBT Boundary

The Phase 3 engine lives under `backtest/vectorbt` as an adapter boundary. The first implementation uses deterministic pandas logic to keep tests lightweight. Deeper VectorBT integration can be added after review if it improves reliability without hiding core contracts.

## Phase 3 Boundary

Phase 3 does not implement Qlib integration, ML model training, AI Research Agent workflows, dashboard UI, broker APIs, order placement, automatic trading, full historical ingestion, strategy optimization, parameter grid search, or live market data calls in tests.
