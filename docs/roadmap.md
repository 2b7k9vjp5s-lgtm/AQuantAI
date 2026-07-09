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
- Current status: Completed.

## Phase 5: AI Research Agent

- Goal: Add research-only agent and report-generation contracts.
- Input: Data contracts, factor scores, backtest metrics, ML predictions, and source references.
- Output: Deterministic research reports, safety disclaimers, source refs, and lazy LLM adapter boundary.
- Completion standard: Reports are structured, auditable, deterministic from local fixtures, and avoid investment-advice wording.
- Current status: Completed.

## Phase 6: Dashboard

- Goal: Provide a read-only dashboard foundation for research workflows and results.
- Input: Data, scores, backtests, and reports from previous phases.
- Output: Dashboard data contracts, read-only payload builders, and sample FastAPI JSON endpoints.
- Completion standard: Users can inspect project, factor, backtest, ML, and report summaries through read-only payloads.
- Current status: Completed.

## Post-Phase-6 Stabilization

- Goal: Consolidate Phase 0-6 into a clean, testable local research baseline.
- Input: Existing contracts, local fixtures, report outputs, and dashboard payloads.
- Output: Documentation consistency, end-to-end fixture demo, cross-module integration tests, and shared safety validation.
- Completion standard: Local demo and tests pass without network, trading, broker, or production deployment behavior.
- Current status: Completed.

## v0.1 Baseline Freeze & Release Readiness

- Goal: Freeze the local research-only v0.1 baseline and prepare release documentation.
- Input: Completed Phase 0-6 work, post-Phase-6 stabilization, local tests, and fixture demo.
- Output: Version/status consistency, changelog, release checklist, local-only CI workflow, and future work boundary documentation.
- Completion standard: Version `0.1.0` is consistent, local tests and demo pass, documentation avoids production-readiness claims, and future work remains outside the v0.1 baseline.
- Current status: Ready for review.
