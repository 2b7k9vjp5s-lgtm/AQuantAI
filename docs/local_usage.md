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

The app is available on host port 8000 and PostgreSQL is exposed on port 5432. PostgreSQL starts to validate the Compose environment, but database persistence is not implemented in the v0.2 baseline. The app remains a local, fixture-oriented research service and does not claim persisted research data.

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

## v0.2 Boundaries

- Research and learning use only; not investment advice or a trading recommendation.
- No live data ingestion, real LLM calls, broker APIs, order placement, automatic trading, or production deployment.
- No live-data dashboard, authentication, account system, payment system, or database persistence. The local `/dashboard` page is presentation-only and fixture-backed.
