# Database Planning

This document records the planned PostgreSQL schema. Phase 0 does not implement database models or migrations.

## stock_basic

- Purpose: Store basic stock identity and listing information.
- Core fields: stock_code, stock_name, exchange, industry, listing_date, delisting_date, status.
- Future extensions: Index membership, concept tags, trading board, data source lineage.

## daily_price

- Purpose: Store daily OHLCV and market data.
- Core fields: trade_date, stock_code, open, high, low, close, volume, amount, adjustment_type.
- Future extensions: Adjusted prices, turnover metrics, limit-up and limit-down flags, suspension status.

## financial_data

- Purpose: Store financial statements and derived financial indicators.
- Core fields: report_date, announce_date, stock_code, revenue, net_profit, total_assets, total_liabilities, equity.
- Future extensions: Statement type, restatement handling, trailing twelve month metrics, data quality flags.

## factor_values

- Purpose: Store raw factor calculation outputs.
- Core fields: factor_date, stock_code, factor_name, factor_value, factor_version.
- Future extensions: Factor metadata, calculation windows, source data snapshots, neutralization flags.

## factor_scores

- Purpose: Store normalized and comparable factor scores.
- Core fields: score_date, stock_code, factor_name, score, rank, universe.
- Future extensions: Industry-neutral scores, z-scores, percentile ranks, composite score components.

## portfolio

- Purpose: Store generated stock pools and portfolio holdings.
- Core fields: portfolio_date, portfolio_name, stock_code, weight, rank, rebalance_frequency.
- Future extensions: Constraints, turnover, sector exposure, risk budgets.

## backtest_result

- Purpose: Store backtest summaries and key performance metrics.
- Core fields: backtest_id, strategy_name, start_date, end_date, total_return, annual_return, max_drawdown, sharpe_ratio.
- Future extensions: Equity curves, trade logs, benchmark comparison, parameter snapshots.

## research_report

- Purpose: Store AI-assisted research reports and human review notes.
- Core fields: report_id, report_date, title, scope, content, model_name, source_refs.
- Future extensions: Report versioning, reviewer comments, generated charts, confidence and risk annotations.
