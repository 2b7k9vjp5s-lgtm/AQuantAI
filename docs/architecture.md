# Architecture

AQuantAI follows a layered architecture designed for long-term iteration and clear module boundaries.

## Current Baseline And Planned Product Architecture

The implemented v0.2 baseline is a local, fixture-backed, read-only research Dashboard. Its provider, factor, ranking, backtest, ML-boundary, report, and Dashboard layers are preserved as **Quant Core**.

Issue #39 defines a future local-first personal research product around Market Cockpit, Industry Alpha, Stock Research, Watchlist, Paper Portfolio, and Settings. It is documentation and implementation planning only; it does not add a new runtime architecture in v0.2. Future product modules will own personal research workflow state and depend on stable provider interfaces. Quant Core provides validation inputs and must not independently produce final research conclusions.

See [product architecture](product_architecture.md), [research workflow](research_workflow.md), [conceptual data model](data_model.md), and [implementation plan](implementation_plan.md).

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
ML Research Layer
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
- PostgreSQL: v0.3A persists normalized stock-basic, daily-price, and trade-calendar versions. v0.3B adds canonical snapshot-series identity so only compatible complete snapshots compete for current/as-of selection. Explicit migrations, provenance, series selectors, and repository interfaces remain isolated from Quant Core calculations. Research workflow, portfolio, backtest, report, and Dashboard persistence remain future work.
- Factor Engine: Calculate normalized factor values from prepared data.
- Ranking Engine: Convert factor values into scores and composites. Portfolio construction is reserved for later phases.
- Backtest Engine: Evaluate deterministic Top-N equal-weight portfolio rules and weekly rebalancing strategies.
- ML Research Layer: Define feature, label, prediction, evaluation, and Qlib adapter boundaries without production training.
- AI Research Agent: Assemble research-only structured reports from prior-layer outputs without owning calculations or trading decisions.
- Dashboard: Present research data and outputs through read-only contracts, JSON endpoints, and a local fixture-backed browser page.

## Dependency Rules

- The data layer must not be tightly coupled to the factor layer.
- The factor layer must not be tightly coupled to the backtest layer.
- The ML layer must keep Qlib-specific imports inside adapter modules.
- The AI Agent only explains, summarizes, and orchestrates workflows. It must not directly own core factor calculations, ranking logic, or backtest calculations.
- Optional LLM adapters must be lazy, mockable, and outside deterministic report assembly.
- Business modules should communicate through explicit interfaces and documented data contracts.

## Phase 0 Boundary

Phase 0 only creates the project skeleton. No market data fetching, factor calculation, backtesting, AI workflow, or dashboard implementation is included.

## Phase 1 Boundary

Phase 1 adds the data-provider interface, AKShare provider skeleton, normalized data contracts, mocked provider tests, and a lightweight update script placeholder. It does not add factor calculation, ranking, backtesting, Qlib, AI Agent logic, dashboard UI, automatic trading, or full historical ingestion.

## Phase 2 Boundary

Phase 2 adds factor contracts, deterministic factor calculators, percentile scoring, group composites, and total composite scores. It does not add portfolio construction, weekly rebalancing, VectorBT backtesting, Qlib, AI Agent logic, dashboard UI, automatic trading, full historical ingestion, or live market data calls in tests.

## Phase 3 Boundary

Phase 3 adds backtest contracts, Top-N equal-weight portfolio selection, weekly rebalance mechanics, equity curves, and core metrics. The current VectorBT namespace acts as an adapter boundary with deterministic pandas logic. Phase 3 does not add Qlib, ML model training, AI Agent logic, dashboard UI, broker APIs, order placement, automatic trading, strategy optimization, parameter grid search, full historical ingestion, or live market data calls in tests.

## Phase 4 Boundary

Phase 4 adds ML experiment contracts, feature and label contracts, prediction outputs, a deterministic baseline model path, and a lazy Qlib adapter boundary. It does not add production model training, hyperparameter search, model registry, scheduled retraining, AI Agent logic, dashboard UI, broker APIs, order placement, automatic trading, live market data calls in tests, or claims about investment profitability.

## Phase 5 Boundary

Phase 5 adds research context contracts, structured research report contracts, deterministic report generation, automatic disclaimers, source-reference preservation, and a lazy LLM adapter boundary. It does not add dashboard UI, broker APIs, order placement, automatic trading, live data fetching in tests, autonomous investment decisions, buy/sell/hold recommendations, guaranteed performance claims, or required OpenAI/LangGraph dependencies.

## Phase 6 Boundary

Phase 6 adds dashboard contracts, read-only overview/report payload builders, research-only disclaimers, source-reference preservation, and read-only FastAPI JSON endpoints. It does not add broker APIs, order placement, automatic trading, live market data fetching in tests, production user authentication, account management, payment/subscription features, production deployment pipelines, trading buttons, buy/sell/hold recommendation UI, or guaranteed-performance claims.

## Post-Phase-6 Boundary

Post-Phase-6 stabilization adds documentation consistency, a local end-to-end fixture demo, integration tests, and shared safety validation. It does not add new product phases, full data ingestion, database persistence, production model training, real Qlib experiments, real LLM calls, frontend framework UI, deployment pipelines, login/auth/account systems, broker APIs, order placement, or automatic trading.

## v0.1 Baseline Boundary

The v0.1 baseline freezes the completed local research-only scope and adds release-readiness documentation, version/status alignment, a changelog, a release checklist, future work boundaries, and local-only CI checks. It does not add runtime behavior, live data ingestion, external service integration, trading features, production deployment, or production-readiness claims.

## v0.2 Local Dashboard Baseline Boundary

The v0.2 baseline records the accepted correctness hardening and the local read-only Dashboard delivery. The browser page renders only existing fixture JSON payloads; Dashboard contracts, research calculations, and allowed actions remain unchanged. It does not add live ingestion, database persistence, production Qlib/VectorBT/LLM execution, authentication, deployment automation, broker APIs, order placement, or automated trading.

## v0.3 Data Foundation Boundary

v0.3A adds explicit PostgreSQL persistence, immutable attempts, complete snapshots, cutoff-aware reads, reconciliation, and fixture-only idempotency. v0.3B adds canonical snapshot-series identity plus one manually invoked AKShare adapter and CLI. Live collection requires explicit bounded scope, `--allow-network`, and a cutoff equal to the UTC collection date; the exact UTC collection time and installed AKShare version are retained as provenance. Endpoint mappings, frequency, and adapter compatibility version define series compatibility, while timeout/retry/network mode do not. The stock-basic endpoint cannot reconstruct a historical universe. Automated tests remain offline. Neither slice connects the Dashboard to PostgreSQL or adds scheduling, background refresh, Market Cockpit, Industry Alpha, LLM execution, broker integration, orders, or trading.
