# Local Usage Guide

This guide describes the v0.2 local, read-only research Dashboard baseline. It is fixture/sample-data-only, not production-ready, does not provide investment advice, and does not support live trading, broker connections, or order placement.

## Prerequisites

- Python 3.12.
- Docker Desktop is optional, only for the Docker and Docker Compose steps.

Run all commands from the repository root.

## One-Click Local Dashboard

Prerequisites: a repository checkout and Docker Desktop. The launchers do not install Docker, Python, packages, or other software.

### Windows

Double-click `start-aquantai.bat`. It finds the repository root, checks Docker, Docker Compose, and the Docker daemon, then starts the existing Compose stack in the background. It creates `.env` from `.env.example` only if `.env` is missing and never overwrites an existing `.env`. After a bounded health-check wait, it opens:

```text
http://127.0.0.1:8000/dashboard
```

Double-click `stop-aquantai.bat` to stop the stack. It uses `docker compose down` and keeps volumes, images, `.env`, and local files.

The Dashboard always uses port `8000`. If startup reports a conflict, run `netstat -ano | findstr :8000`, identify the local process, close it safely, and rerun the launcher. The launcher returns a non-zero status when Docker cannot bind port 8000.

When started by double-click, the Windows scripts keep the result visible for 10 seconds before closing. For terminal or automated use, run `start-aquantai.bat --no-wait` or `stop-aquantai.bat --no-wait`; success still returns 0 and failure returns non-zero.

### macOS

Make the scripts executable once:

```bash
chmod +x start-aquantai.sh stop-aquantai.sh
```

Start and stop the local stack:

```bash
./start-aquantai.sh
./stop-aquantai.sh
```

The script uses the same Docker checks, `.env` preservation, bounded local health check, and safe `docker compose down` behavior. After the Dashboard is ready, macOS uses the standard `open` command.

### Linux

Make the scripts executable once, then start or stop the stack:

```bash
chmod +x start-aquantai.sh stop-aquantai.sh
./start-aquantai.sh
./stop-aquantai.sh
```

Linux uses `xdg-open` when available. macOS alone uses `open`. If the platform-specific opener is missing or fails, the script prints the exact Dashboard URL.

Common fixes:

- Docker command unavailable: install Docker Desktop and open a new terminal.
- Docker daemon unavailable: start Docker Desktop and wait until it finishes starting.
- Compose configuration invalid: compare `.env` with `.env.example`; the launcher does not overwrite the existing file.
- First-build package failure: check the internet or proxy used by Docker, then retry. The launcher does not download or execute remote scripts itself.
- Port 8000 unavailable: close the program using port 8000, then rerun the launcher. The launcher does not change ports or terminate processes automatically.
- Health-check timeout: review the printed Compose status and app logs, then use the matching stop script if partial services should be stopped.

These launchers only start the existing local Compose stack. They do not provide production deployment, live data, persistence, accounts, brokers, orders, or trading.

## Python Setup

Install the runtime and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the local checks:

```bash
python -m pytest
python -m scripts.demo_research_flow
```

The demo uses local fixtures. It does not require live market data, an LLM credential, broker access, or a production service.

## Local API

Start FastAPI:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open these local URLs in a browser or HTTP client:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/dashboard
- http://127.0.0.1:8000/dashboard/overview
- http://127.0.0.1:8000/dashboard/report

Expected results:

- `/` reports version `0.2.0` and the research-only local Dashboard baseline status.
- `/health` reports `{"status": "ok"}`.
- `/dashboard` is a local graphical page. It renders the existing fixture/sample Dashboard JSON payloads only.
- Both dashboard endpoints return JSON with `read_only: true` and the research disclaimer.

The Dashboard is a local, read-only research surface. The browser page is not a live-data product or a persistence layer: it displays local fixture/sample data, retains the raw JSON endpoints, and exposes no trading, order, broker, account, or editable strategy controls.

## Docker Image

Build the image:

```bash
docker build -t aquantai:v0.2 .
```

Start it on port 8000:

```bash
docker run --rm -p 8000:8000 aquantai:v0.2
```

Use the listed local URLs above to verify the API. Stop the foreground container with `Ctrl+C`.

## Docker Compose

Create local configuration from the public template:

```bash
cp .env.example .env
```

Start the app and PostgreSQL services:

```bash
docker compose up --build
```

The app is available on host port 8000 and PostgreSQL is exposed on port 5432. The released v0.2 API and Dashboard remain fixture-oriented and do not read from the database. The v0.3 data work remains an isolated persistence and manually controlled ingestion foundation.

Migrations are explicit and do not run during API startup. From inside the running app container:

```bash
docker compose exec app python -m alembic upgrade head
docker compose exec app python -m alembic current
docker compose exec app python -m scripts.persist_fixture_market_data
docker compose exec app python -m scripts.persist_fixture_market_data
```

The first import writes the local deterministic fixture. The second is idempotent and reports the same ingestion ID with zero rows written. No command in this flow calls AKShare or another external data service.

### Manual AKShare Collection

Real collection is never automatic. The CLI requires explicit codes, date bounds, adjustment policy, cutoff, and network consent. In live mode, the cutoff must equal the UTC collection date; past or future values fail before any provider or database activity:

```bash
python -m scripts.ingest_akshare_market_data \
  --stock-code 000001 \
  --start-date 20260708 \
  --end-date 20260709 \
  --adjust qfq \
  --cutoff 20260718 \
  --allow-network
```

The default request timeout is 20 seconds per endpoint call with at most two retries. Both limits are finite and can be reduced with `--timeout-seconds` and `--max-retries`. One request accepts at most 50 explicit stock codes and never defaults to all stocks or an unbounded date range. The `stock_info_a_code_name` endpoint has no historical date selector, so this command cannot reconstruct a historical stock universe; live stock-basic rows describe only information available at collection time.

Normalization-only mode prints the canonical scope, series key, cutoff, validation status, and row counts without writing the database:

```bash
python -m scripts.ingest_akshare_market_data \
  --stock-code 000001 \
  --stock-code 600000 \
  --start-date 20260708 \
  --end-date 20260709 \
  --adjust qfq \
  --cutoff 20260709 \
  --offline-fixture \
  --dry-run
```

`--offline-fixture` is a deterministic local response set for validation and makes no network request. It is mutually exclusive with `--allow-network`. See [akshare_ingestion.md](akshare_ingestion.md) for endpoint mappings, selector semantics, failure behavior, and boundaries.

For direct host-Python use, set `DATABASE_URL` to the exposed host address before running the same commands. The `.env.example` value uses hostname `postgres` inside Compose; use `127.0.0.1` only in the host process environment. See [database.md](database.md) for natural keys, provenance, cutoff behavior, and recovery.

### Market Cockpit

The v0.4A Market Cockpit is separate from the fixture Dashboard and reads one explicit successful complete snapshot from PostgreSQL. Run migrations and persist data first, then use:

```text
http://127.0.0.1:8000/market-cockpit/snapshot?series_key=<series-key>&as_of_cutoff=YYYYMMDD
http://127.0.0.1:8000/market-cockpit?series_key=<series-key>&as_of_cutoff=YYYYMMDD
```

`as_of_cutoff` is optional, but `series_key` is mandatory. Missing selection returns 422, no eligible snapshot returns 404, and unavailable database configuration/query state returns 503. No error path falls back to sample data.

The page displays selected-universe scope, stock codes/counts, ingestion run, provider, contract/adapter provenance, cutoff, effective trading session, requested dates, adjustment policy, completeness, warnings, formulas, and unsupported sections. It is read-only and does not automatically refresh or collect data.

Run the deterministic persisted current/historical demonstration after migration:

```bash
python -m scripts.demo_market_cockpit
```

See [market_cockpit.md](market_cockpit.md) for exact formulas, minimum history, missing-data rules, and the official-index/sector/style/valuation/crowding exclusions.

For ordinary local use, stop the stack without deleting volumes or `.env`:

```bash
docker compose down
```

The one-click stop scripts use the same safe command. Do not delete `.env` unless you intentionally want to recreate local configuration.

## Windows Docker Desktop Note

If PowerShell cannot find `docker` immediately after installing Docker Desktop, open a new terminal so its PATH is refreshed. Confirm the engine is ready with:

```bash
docker version
```

If Windows reserves port 8000, `netsh interface ipv4 show excludedportrange protocol=tcp` displays the excluded ranges. Do not remove system reservations automatically. Stop the launcher, resolve the Windows or Docker port reservation outside AQuantAI, and retry only after port 8000 is available.

## Current Boundaries

- Research and learning use only; not investment advice or a trading recommendation.
- The released v0.2 application remains fixture-backed. v0.3B permits only explicit manual, bounded AKShare collection; there is no scheduler or background refresh.
- The v0.4A Market Cockpit monitors only one explicitly selected persisted universe. It is not full-market or official-index breadth.
- No real LLM calls, broker APIs, order placement, automatic trading, or production deployment.
- No live-data Dashboard, authentication, account system, or payment system. PostgreSQL and AKShare ingestion are not connected to `/dashboard`.
