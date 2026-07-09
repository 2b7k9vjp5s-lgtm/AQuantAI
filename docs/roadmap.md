# Roadmap

Development must proceed phase by phase. Do not start a later phase until the current sprint is completed and reviewed.

## Phase 0: Project Initialization

- Goal: Create the repository, project structure, documentation, basic FastAPI app, tests, and Docker skeleton.
- Input: Project requirements and fixed technology stack.
- Output: Initialized repository with Phase 0 files.
- Completion standard: FastAPI app responds on `/` and `/health`, tests pass, documentation exists, and Git repository is initialized.
- Current status: Completed.

## Phase 1: A-share Data Center

- Goal: Build the A-share data source boundary and normalized data contracts.
- Input: AKShare as the first provider and PostgreSQL planning from Phase 0.
- Output: Data provider interface, AKShare provider skeleton, normalized data contracts, mocked tests, and a lightweight script placeholder.
- Completion standard: Provider methods return stable DataFrame schemas with mocked tests and no later-phase business logic.
- Current status: Completed.

## Phase 2: Multi-factor Scoring System

- Goal: Implement factor calculation contracts and scoring utilities.
- Input: Normalized data contracts from Phase 1 and local DataFrame fixtures.
- Output: Value, growth, quality, momentum, and risk calculators plus percentile and composite scoring.
- Completion standard: Factor values and factor scores can be generated deterministically from local DataFrames with tests.
- Current status: Completed.

## Phase 3: VectorBT Backtesting System

- Goal: Add deterministic weekly rebalancing backtest foundations for factor-ranked portfolios.
- Input: Factor scores and price data.
- Output: Backtest contracts, Top-N equal-weight selection, equity curves, and core performance metrics.
- Completion standard: A weekly rebalanced portfolio can be backtested from local fixtures with repeatable results.
- Current status: Completed.

## Phase 4: Qlib Machine Learning Models

- Goal: Create guarded Qlib/ML research contracts and adapter boundaries.
- Input: Normalized market data, factor outputs, score outputs, and local fixture datasets.
- Output: ML experiment configuration, feature/label/prediction contracts, lazy Qlib adapter boundary, and deterministic baseline predictions.
- Completion standard: ML contracts and baseline predictions are testable from local fixtures without production training or live data calls.
- Current status: Ready for review.

## Phase 5: AI Research Agent

- Goal: Add AI-assisted interpretation and report generation.
- Input: Stock pools, factor scores, backtest results, and research context.
- Output: Research Agent workflows and generated research reports.
- Completion standard: AI Agent can generate explainable research summaries without owning core calculations.
- Current status: Not started.

## Phase 6: Dashboard

- Goal: Provide an interactive dashboard for research workflows and results.
- Input: Data, scores, backtests, and reports from previous phases.
- Output: Dashboard UI and deployment workflow.
- Completion standard: Users can inspect stock pools, factor results, backtests, and reports through the dashboard.
- Current status: Not started.
