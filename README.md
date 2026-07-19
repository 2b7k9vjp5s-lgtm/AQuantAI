# AQuantAI

AQuantAI is a local-first personal A-share research workbench built around attributable market data, deterministic quantitative research, evidence-backed industry/company research, backtesting foundations and future guarded AI assistance.

It is for research and learning only. It does not provide investment advice, recommendations, broker connectivity, real orders or automated trading, and it is not production-ready.

## Current state

AQuantAI uses three independent status axes:

| Axis | Current state |
| --- | --- |
| Released software version | `0.2.0` |
| Merged capability stage on `main` | v0.6D |
| Runtime surfaces | Local fixture-backed read-only Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured |

Merged capability stages do not automatically publish a new release. The application version remains `0.2.0` until a separate release decision.

The authoritative state, dependency direction, ownership rules, invariants, architecture debt and development gates are defined in [the architecture baseline](docs/architecture_baseline.md).

## Implemented capability summary

### Quant Core and Dashboard

- FastAPI application and health endpoint;
- normalized provider contracts and guarded AKShare boundary;
- deterministic factor values, percentile scores and composite utilities;
- weekly equal-weight backtest foundations;
- ML feature/label/prediction contracts and deterministic baseline path;
- deterministic research-report contracts and lazy adapter boundaries;
- fixture-backed read-only `/dashboard` page and JSON endpoints;
- local fixture demo and no-network test discipline.

### Market-data persistence and Market Cockpit

- PostgreSQL market-data migrations and explicit session boundary;
- immutable ingestion attempts and complete-snapshot reconciliation;
- canonical snapshot-series identities isolating scopes, dates, adjustment and contract parameters;
- controlled manual AKShare ingestion with explicit network opt-in and offline fixture mode;
- cutoff-aware deterministic reads;
- selected-universe breadth/risk, optional benchmark and sector context, liquidity distribution and descriptive price-behavior proxies;
- read-only database-backed Market Cockpit API/page when configured.

### Industry Alpha and Stage 2 research

Merged reviewed foundations through v0.6D include:

- v0.5A research cases, evidence, claims, conflicts and immutable revisions;
- v0.5B industry maps, nodes, relationships, drivers, bottlenecks and value-pool observations;
- v0.5C beneficiary classifications and exact candidate-pool handoff;
- v0.6A company research and financial-transmission hypotheses;
- v0.6B market expectations and valuation observations;
- v0.6C catalyst and risk assessments;
- v0.6D independent industry/company quality judgments.

These records are append-only, cutoff-aware, evidence-bound and read-only. They do not produce target prices, fair values, expected returns, rankings, recommendations, Watchlist state, portfolio actions or trading behavior.

## Architecture freeze

The attempted v0.6E price-observation judgment path in Issue #70 and PR #71 is superseded and closed without merge.

Before any new domain is authorized, the project must complete the architecture-baseline review and a separately authorized Stage 2 consolidation characterization. No v0.6E, v0.7 or new migration is currently authorized.

A local `daily_price` row linked to a v0.6B valuation remains provenance/context. Generic valuation `observed_value` is not automatically eligible for price comparison. Canonical market-price measurement, unit and currency semantics require a separately reviewed upstream contract.

## Technology stack

- Python 3.12
- FastAPI
- SQLAlchemy and Alembic
- PostgreSQL
- Pydantic
- pandas and NumPy
- pytest and httpx
- Docker and Docker Compose for local use

## Quick start

Install runtime and development dependencies:

```bash
pip install -e ".[dev]"
```

Run the API:

```bash
uvicorn backend.main:app --reload
```

Available baseline endpoints include:

- `GET /`
- `GET /health`
- `GET /dashboard`
- `GET /dashboard/overview`
- `GET /dashboard/report`

The fixture Dashboard remains local, read-only and sample-data-only.

Run the local research flow demo:

```bash
python -m scripts.demo_research_flow
```

Run tests:

```bash
python -m pytest
```

## Local Docker launch

With Docker Desktop available:

- Windows: `start-aquantai.bat`
- macOS/Linux: `./start-aquantai.sh`

The launcher checks Docker and Compose, preserves an existing `.env`, starts the local stack, waits for health and opens the local Dashboard. It does not install dependencies or enable production deployment.

## Database-backed local use

Migrations are explicit and never run during FastAPI import or startup.

```bash
python -m alembic upgrade head
python -m scripts.persist_fixture_market_data
```

Set `DATABASE_URL` to a host-reachable PostgreSQL URL when running outside Docker. See [database documentation](docs/database.md).

### Controlled AKShare ingestion

Live collection is manual, bounded and requires explicit stock codes, dates, adjustment, cutoff and `--allow-network`.

```bash
python -m scripts.ingest_akshare_market_data \
  --stock-code 000001 \
  --start-date 20260708 \
  --end-date 20260709 \
  --adjust qfq \
  --cutoff 20260718 \
  --allow-network
```

Use `--dry-run` to inspect normalization and series identity without persistence. Use `--offline-fixture` for deterministic no-network verification. No AKShare call occurs during imports, startup, tests, CI, fixture demos or ordinary read use.

### Market Cockpit

After persisting a compatible explicit snapshot series:

```text
/market-cockpit/snapshot?series_key=<series-key>&as_of_cutoff=YYYYMMDD
/market-cockpit?series_key=<series-key>&as_of_cutoff=YYYYMMDD
```

Equity, benchmark and sector series remain explicit and independent. The API never selects by provider alone and never stitches incompatible runs.

## Development workflow

GitHub is the source of truth for authorization and review. Every task must follow `.codex/WORKFLOW.md` and the active linked Issue.

The required sequence is:

```text
Architecture Preflight
  -> Definition of Ready
  -> concise authoritative Issue
  -> task synchronization/planning review
  -> implementation review
  -> explicit merge authorization
  -> architecture/status synchronization
```

Green CI is necessary but not sufficient. New work must also prove field ownership, production reachability, fixture/provider parity, explicit semantics and bounded scope.