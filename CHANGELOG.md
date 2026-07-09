# Changelog

All notable baseline changes for AQuantAI are summarized here.

## 0.1.0 - v0.1 Baseline Freeze

Status: release readiness review.

This release freezes the local, research-only baseline after Phase 0 through Phase 6 and post-Phase-6 stabilization. It is not production-ready and does not include live trading, broker integration, order placement, production deployment, or investment advice.

### Phase 0: Project Initialization

- Created the Python/FastAPI project skeleton, documentation set, pytest setup, and Docker compose placeholders.
- Added root and health endpoints for local application smoke checks.

### Phase 1: A-share Data Center

- Added the data provider interface and AKShare provider boundary.
- Defined normalized stock basic, daily price, and trade calendar contracts with mocked tests.

### Phase 2: Multi-factor Scoring

- Added deterministic value, growth, quality, momentum, and risk factor calculators.
- Added percentile scoring and weighted composite score utilities.

### Phase 3: Backtesting Foundation

- Added deterministic weekly Top-N equal-weight portfolio selection.
- Added backtest contracts, equity curve output, and core performance metrics.

### Phase 4: Qlib/ML Foundation

- Added ML experiment, feature, label, and prediction contracts.
- Added deterministic baseline predictions and a lazy Qlib adapter boundary.

### Phase 5: AI Research Agent Foundation

- Added deterministic research-only report generation.
- Added source references, safety disclaimers, and a lazy LLM adapter boundary.

### Phase 6: Dashboard Foundation

- Added read-only dashboard contracts and payload builders.
- Added FastAPI JSON endpoints for overview and report inspection.

### Post-Phase-6 Stabilization

- Added an end-to-end local fixture demo.
- Added cross-module integration tests.
- Centralized research-only safety wording checks across reports and dashboard payloads.

### Release Readiness

- Aligned version and status metadata on `0.1.0`.
- Added release checklist and future work documentation.
- Added a local-only CI workflow for pytest and the fixture demo.
