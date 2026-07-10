# AQuantAI

AQuantAI is a personal A-share AI quantitative research platform built around market data, multi-factor research, backtesting, OpenBB-style research workflows, and future AI Agent orchestration.

Current phase: v0.1 baseline freeze and release readiness.

Current version: `0.1.0`.

This project is for quantitative research and learning only. It does not provide investment advice, does not make trading recommendations, is not production-ready, and is not intended for automated trading.

## Positioning

AQuantAI aims to become a sustainable research system for:

- A-share market data collection
- Multi-factor stock selection models
- Weekly rebalancing backtests
- Stock pool generation
- AI-assisted research reports
- Future integration with Qlib, VectorBT, OpenBB, LangGraph, and OpenAI APIs

## Technology Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy, Pydantic
- Database: PostgreSQL
- Data research: pandas, numpy
- Data source foundation: AKShare provider boundary
- Factor engine: deterministic pandas/numpy factor calculators and scoring utilities
- Backtest engine: deterministic weekly Top-N equal-weight portfolio backtests
- ML research layer: feature/label/prediction contracts and Qlib adapter boundary
- AI Research Agent: deterministic research-only report assembly and adapter boundaries
- Dashboard: read-only research presentation contracts and JSON endpoints
- Future data source integrations: Tushare, OpenBB
- Future full quant integrations beyond current adapter boundaries: VectorBT, Qlib
- Future AI integrations beyond current adapter boundaries: LangGraph, OpenAI API
- Deployment: Docker, docker-compose
- Testing: pytest, httpx

## Current Scope

Phase 0 through Phase 6 and the post-Phase-6 stabilization pass are implemented and review-accepted from an architecture perspective. The v0.1 baseline freezes the following local, deterministic research scope:

- Project structure
- Documentation
- Basic FastAPI app
- Health check endpoint
- Basic tests
- Docker skeleton with FastAPI and PostgreSQL services
- Data provider interface
- AKShare provider skeleton
- Normalized stock basic, daily price, and trade calendar contracts
- Mocked provider tests
- Factor contracts for values and scores
- Initial value, growth, quality, momentum, and risk factors
- Percentile scoring and weighted composite score utilities
- Backtest contracts and result metrics
- Top-N equal-weight portfolio selection from total scores
- Weekly rebalance foundation using local price and score DataFrames
- ML experiment contracts
- Feature, label, and prediction output contracts
- Deterministic baseline prediction path
- Lazy Qlib adapter boundary
- Research context and report contracts
- Deterministic local report generation
- Research-only disclaimer and safety wording checks
- Optional lazy LLM adapter boundary
- Dashboard data contracts
- Read-only overview and report payload builders
- Read-only dashboard FastAPI endpoints
- End-to-end local fixture demo
- Cross-module integration checks
- Shared research-only safety validation
- Release checklist and future work boundary documentation

## Not Supported Yet

The current phase does not implement:

- Full historical A-share data ingestion
- Tushare data fetching
- OpenBB integration
- Production stock-pool ranking
- Strategy optimization or parameter grid search
- Production model training
- Hyperparameter search
- Model registry
- Scheduled retraining
- Trading buttons
- Broker APIs
- Order placement
- Automated trading
- Production deployment pipeline
- Login/auth/account system

## Quick Start

Install dependencies:

```bash
pip install -e ".[dev]"
```

Run the API:

```bash
uvicorn backend.main:app --reload
```

Open:

- `GET /`
- `GET /health`
- `GET /dashboard/overview`
- `GET /dashboard/report`

Inspect the Phase 1 data provider placeholder:

```bash
python -m scripts.update_data
```

Run the local research flow demo:

```bash
python -m scripts.demo_research_flow
```

Run tests:

```bash
python -m pytest
```

Release readiness checklist:

- `CHANGELOG.md`
- `docs/release_checklist.md`
- `docs/future_work.md`

## Docker Start

Copy the environment template:

```bash
cp .env.example .env
```

Start services:

```bash
docker compose up --build
```

## Development Workflow

GitHub is the single source of truth for task synchronization and review follow-up.

Every development sprint must start by reading:

- Latest GitHub Review Issue
- `docs/roadmap.md`
- `docs/architecture.md`
- `docs/factors.md`
- `docs/backtesting.md`
- `docs/ml.md`
- `docs/agent.md`
- `docs/dashboard.md`
- `docs/development.md`
- `docs/review.md`
- `docs/release_checklist.md`
- `docs/future_work.md`

Every sprint should update:

- `docs/roadmap.md`
- `docs/review.md`
- `README.md` when necessary

Development must follow the planned phases and must not skip ahead.

## GitHub Collaboration

- `main`: stable branch
- `dev`: development branch
- `feature/*`: feature branches
- `fix/*`: bug fix branches

Codex implements changes, commits code, pushes branches, and opens pull requests when available. ChatGPT reviews the repository as an architecture and code reviewer. Review feedback is recorded in `docs/review.md` or GitHub Issues, then addressed in later sprints.

After each sprint, Codex must:

- Update relevant documentation
- Commit code
- Create a pull request
- Include completed work, test results, and unfinished items in the pull request description
- Wait for ChatGPT review before entering the next phase

ChatGPT review feedback should be synchronized to GitHub first, preferably as an Issue titled `Sprint N Review & Next Tasks`, then as pull request review comments, and finally in `docs/review.md` when needed.
