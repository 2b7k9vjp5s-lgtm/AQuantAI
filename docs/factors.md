# Factor Engine

Phase 2 creates the multi-factor scoring foundation. The goal is deterministic contracts and tests, not strategy performance.

## Factor Groups

- Value: `pe_inverse`, `pb_inverse`
- Growth: `revenue_growth`, `net_profit_growth`
- Quality: `roe`, `gross_margin`
- Momentum: `return_20d`, `return_60d`
- Risk: `volatility_20d`, `max_drawdown_60d`

## Input Contracts

Financial statement and valuation factors expect local DataFrames with:

- `factor_date`
- `stock_code`
- required numeric columns such as `pe`, `pb`, `revenue`, `revenue_prev`, `net_profit`, `net_profit_prev`, `equity`, and `gross_profit`

Price-based factors expect normalized daily price DataFrames with:

- `trade_date`
- `stock_code`
- `close`

## Factor Output Contract

All factor calculators return:

- `factor_date`
- `stock_code`
- `factor_name`
- `factor_value`
- `factor_group`
- `factor_version`

## Score Output Contract

Scoring utilities return:

- `score_date`
- `stock_code`
- `factor_name`
- `factor_group`
- `score`
- `rank`
- `universe`

## Scoring Method

Factor values are converted into percentile scores from 0 to 100. Descending factors reward larger values. Ascending factors reward smaller values. Missing factor values receive a neutral score of 50.

Scores are isolated by `factor_date`, `factor_name`, and `universe`. Group and total composites remain isolated by `score_date` and `universe`, so stocks from separate dates or universes are never ranked together. Equal scores use `stock_code` as the final deterministic tie-break. Duplicate factor or composite inputs that would make a score ambiguous are rejected, and composite score inputs must be finite.

Default group weights:

- Value: 25%
- Growth: 25%
- Quality: 20%
- Momentum: 20%
- Risk: 10%

Group composites average factor scores within each group. Total composite scores apply the default group weights.

## Phase 2 Boundary

Phase 2 does not implement portfolio construction, weekly rebalance logic, VectorBT backtesting, Qlib integration, AI Research Agent workflows, dashboard UI, automatic trading, full historical ingestion, or live market data calls in tests.
