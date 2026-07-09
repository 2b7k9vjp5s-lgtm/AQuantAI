# Database Planning

This document records the planned PostgreSQL schema and Phase 1 normalized data contracts. Phase 1 does not implement database models, migrations, or full ingestion.

## stock_basic

- Purpose: Store basic stock identity and listing information.
- Core fields: stock_code, stock_name, exchange, industry, listing_date, delisting_date, status.
- Future extensions: Index membership, concept tags, trading board, data source lineage.

Normalized provider columns:

- `stock_code`
- `stock_name`
- `exchange`
- `industry`
- `listing_date`
- `status`
- `source`

## daily_price

- Purpose: Store daily OHLCV and market data.
- Core fields: trade_date, stock_code, open, high, low, close, volume, amount, adjustment_type.
- Future extensions: Adjusted prices, turnover metrics, limit-up and limit-down flags, suspension status.

Normalized provider columns:

- `trade_date`
- `stock_code`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount`
- `adjust_type`
- `source`

## trade_calendar

- Purpose: Store open trading dates for the A-share market.
- Core fields: trade_date, is_open, source.
- Future extensions: Exchange-specific calendars, half-day flags, holiday metadata, data source lineage.

Normalized provider columns:

- `trade_date`
- `is_open`
- `source`

## financial_data

- Purpose: Store financial statements and derived financial indicators.
- Core fields: report_date, announce_date, stock_code, revenue, net_profit, total_assets, total_liabilities, equity.
- Future extensions: Statement type, restatement handling, trailing twelve month metrics, data quality flags.

## factor_values

- Purpose: Store raw factor calculation outputs.
- Core fields: factor_date, stock_code, factor_name, factor_value, factor_version.
- Future extensions: Factor metadata, calculation windows, source data snapshots, neutralization flags.

Normalized factor output columns:

- `factor_date`
- `stock_code`
- `factor_name`
- `factor_value`
- `factor_group`
- `factor_version`

## factor_scores

- Purpose: Store normalized and comparable factor scores.
- Core fields: score_date, stock_code, factor_name, score, rank, universe.
- Future extensions: Industry-neutral scores, z-scores, percentile ranks, composite score components.

Normalized score output columns:

- `score_date`
- `stock_code`
- `factor_name`
- `factor_group`
- `score`
- `rank`
- `universe`

## portfolio

- Purpose: Store generated stock pools and portfolio holdings.
- Core fields: portfolio_date, portfolio_name, stock_code, weight, rank, rebalance_frequency.
- Future extensions: Constraints, turnover, sector exposure, risk budgets.

Backtest holding output columns:

- `rebalance_date`
- `stock_code`
- `weight`
- `rank`
- `score`
- `universe`

## backtest_result

- Purpose: Store backtest summaries and key performance metrics.
- Core fields: backtest_id, strategy_name, start_date, end_date, total_return, annual_return, max_drawdown, sharpe_ratio.
- Future extensions: Equity curves, trade logs, benchmark comparison, parameter snapshots.

Phase 3 result fields:

- `start_date`
- `end_date`
- `total_return`
- `annual_return`
- `max_drawdown`
- `volatility`
- `sharpe_ratio`
- `turnover`
- `rebalance_count`

## research_report

- Purpose: Store AI-assisted research reports and human review notes.
- Core fields: report_id, report_date, title, scope, content, model_name, source_refs.
- Future extensions: Report versioning, reviewer comments, generated charts, confidence and risk annotations.

Phase 5 report fields:

- `report_date`
- `title`
- `scope`
- `summary`
- `factor_highlights`
- `backtest_highlights`
- `ml_highlights`
- `risks`
- `limitations`
- `disclaimer`
- `source_refs`

## ml_features

- Purpose: Store feature snapshots for guarded ML experiments.
- Core fields: feature_date, stock_code, universe, feature columns derived from factors or normalized market data.
- Future extensions: Feature versioning, lineage, preprocessing metadata, train/test split tags.

## ml_labels

- Purpose: Store supervised learning labels for research experiments.
- Core fields: label_date, stock_code, future_return, label_window, universe.
- Future extensions: Label definitions, benchmark-relative returns, outlier policy, leakage checks.

## ml_predictions

- Purpose: Store model prediction outputs in a backtest-compatible format.
- Core fields: prediction_date, stock_code, model_name, prediction_score, prediction_rank, universe.
- Future extensions: Experiment ID, model version, confidence bands, calibration metadata.
