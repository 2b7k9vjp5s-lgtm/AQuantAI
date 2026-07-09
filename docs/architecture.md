# Architecture

AQuantAI follows a layered architecture designed for long-term iteration and clear module boundaries.

```text
AKShare Provider
          |
          v
Normalized Data Contracts
          |
          v
PostgreSQL
          |
          v
Factor Engine
          |
          v
Ranking Engine
          |
          v
Backtest Engine
          |
          v
AI Research Agent
          |
          v
Dashboard
```

## Layer Responsibilities

- Data sources: Fetch and normalize external data behind provider interfaces. Phase 1 includes only the AKShare boundary.
- Normalized data contracts: Stable DataFrame columns for stock basic data, daily prices, and trade calendars before database persistence.
- PostgreSQL: Store market data, financial data, factor values, portfolios, backtest results, and reports.
- Factor Engine: Calculate factor values from prepared data.
- Ranking Engine: Combine factor scores into stock rankings and stock pools.
- Backtest Engine: Evaluate portfolio rules and rebalancing strategies.
- AI Research Agent: Explain results, coordinate research workflows, and generate reports.
- Dashboard: Present research data and outputs to users.

## Dependency Rules

- The data layer must not be tightly coupled to the factor layer.
- The factor layer must not be tightly coupled to the backtest layer.
- The AI Agent only explains, summarizes, and orchestrates workflows. It must not directly own core factor calculations, ranking logic, or backtest calculations.
- Business modules should communicate through explicit interfaces and documented data contracts.

## Phase 0 Boundary

Phase 0 only creates the project skeleton. No market data fetching, factor calculation, backtesting, AI workflow, or dashboard implementation is included.

## Phase 1 Boundary

Phase 1 adds the data-provider interface, AKShare provider skeleton, normalized data contracts, mocked provider tests, and a lightweight update script placeholder. It does not add factor calculation, ranking, backtesting, Qlib, AI Agent logic, dashboard UI, automatic trading, or full historical ingestion.
