# AQuantAI

AQuantAI is a local-first personal A-share research workbench built around attributable market data, deterministic quantitative research, evidence-backed industry/company research, backtesting foundations and guarded AI assistance.

It is for research and learning only. It does not provide investment advice, recommendations, broker connectivity, real orders or automated trading, and it is not production-ready.

## Current state

AQuantAI uses three independent status axes:

| Axis | Current state |
| --- | --- |
| Released software version | `0.2.0` |
| Phase 2A capability merge commit | `1f9edfc0719c9d512ed95c2330db78dadea17eea` |
| Latest merged product capability | Personal Research Workbench UI Phase 2A — local-only Today Market through PRs #209 and #212 |
| Runtime surfaces | Local Dashboard, technical Market Cockpit, Today Market, Industry Research, Company Research, Investment Candidates and related exact-ID APIs/commands when configured |

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

### Market-data persistence, Market Cockpit and Today Market

- PostgreSQL market-data migrations and explicit session boundary;
- immutable ingestion attempts and complete-snapshot reconciliation;
- canonical snapshot-series identities isolating scopes, dates, adjustment and contract parameters;
- controlled manual AKShare ingestion with explicit network opt-in and offline fixture mode;
- cutoff-aware deterministic reads;
- technical read-only `/market-cockpit` using exact selected series;
- Chinese-first `/today-market` with an explicit local equity selection, optional benchmark/sector selections, required information-cutoff and recorded-UTC boundaries;
- existing `MarketCockpitService` remains the sole deterministic price, liquidity, benchmark and sector calculation owner;
- no automatic series selection, remote refresh, full-market breadth claim, anomaly/cause inference or hidden network access.

### Industry and company research

Merged reviewed foundations include:

- v0.5A research cases, evidence, claims, conflicts and immutable revisions;
- v0.5B industry maps, nodes, relationships, drivers, bottlenecks and value-pool observations;
- v0.5C beneficiary classifications and exact candidate-pool handoff;
- typed beneficiary evidence semantics;
- v0.6A company research and financial-transmission hypotheses;
- v0.6B market expectations and valuation observations;
- v0.6C catalyst and risk assessments;
- v0.6D independent industry/company quality judgments;
- complete-universe company comparison;
- Canonical Price and purpose-specific Comparison Eligibility;
- transparent Investment Candidate components, statuses and bounded priority;
- normalized financial, valuation, comparison and expectation-gap contracts;
- Chinese-first Personal Research Workbench for scope confirmation, complete candidate construction, complete review and exact history reopening.

These records are append-only, cutoff-aware and evidence-bound. They do not produce target prices, fair values, expected returns, unexplained recommendations, Watchlist state, portfolio actions or trading behavior.

## Governed boundaries

The attempted v0.6E price-observation judgment path in Issue #70 and PR #71 is superseded and closed without merge.

Canonical Price and Comparison Eligibility now own accepted price identity and purpose-specific use. A generic valuation `observed_value` or Provider-normalized market row is not automatically canonical or eligible for comparison.

No next product phase is currently authorized. Roadmap Issue #210 describes a possible Personal Research Workbench UI Phase 2B, but it does not authorize architecture, implementation or production changes. Every future phase still requires its own linked Issue, bounded scope, validation and explicit merge authorization.

## Technology stack

- Python 3.12+
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

Available local surfaces include:

- `GET /`
- `GET /health`
- `GET /dashboard`
- `GET /workbench`
- `GET /industry-analysis`
- `GET /today-market`
- `GET /market-cockpit`
- `GET /investment-candidates`

The fixture Dashboard remains local, read-only and sample-data-only. Database-backed surfaces require an explicitly configured local database and exact persisted records.

Run the local research flow demo:

```bash
python -m scripts.demo_research_flow
```

Run the Today Market offline demo:

```bash
python -m scripts.demo_today_market
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

### Today Market

Open `/today-market`, choose an explicit local equity series, optionally choose exact benchmark and sector series, set both requested boundaries and select `查看本地市场快照`.

Today Market reads only already persisted local data. It never auto-selects a series, advances a requested boundary, performs remote refresh or represents an exact selected universe as complete A-share market coverage.

## Development workflow

GitHub is the source of truth for authorization and review. Every task must follow `.codex/WORKFLOW.md` and the active linked Issue.

The required sequence is:

```text
Architecture Preflight when required by risk
  -> Definition of Ready
  -> authoritative Issue and bounded branch/PR
  -> validation and applicable fixed-head review
  -> explicit merge authorization
  -> architecture/status synchronization
```

Green CI is necessary but not sufficient. New work must also prove field ownership, production reachability, fixture/provider parity, explicit semantics and bounded scope.
