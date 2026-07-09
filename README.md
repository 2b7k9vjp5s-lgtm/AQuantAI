# AQuantAI

AQuantAI is a personal A-share AI quantitative research platform built around market data, multi-factor research, backtesting, OpenBB-style research workflows, and future AI Agent orchestration.

Current phase: Phase 0 - project initialization.

This project is for quantitative research and learning only. It does not provide investment advice, does not make trading recommendations, and is not intended for automated trading.

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
- Data sources planned for later phases: AKShare, Tushare, OpenBB
- Quant modules planned for later phases: VectorBT, Qlib
- AI modules planned for later phases: LangGraph, OpenAI API
- Deployment: Docker, docker-compose
- Testing: pytest, httpx

## Current Scope

Phase 0 includes:

- Project structure
- Documentation
- Basic FastAPI app
- Health check endpoint
- Basic tests
- Docker skeleton with FastAPI and PostgreSQL services

## Not Supported Yet

The current phase does not implement:

- AKShare data fetching
- Tushare data fetching
- OpenBB integration
- Factor calculation
- Ranking models
- Backtesting
- AI Research Agent
- Dashboard
- Automated trading

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

Run tests:

```bash
pytest
```

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
- `docs/development.md`
- `docs/review.md`

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
