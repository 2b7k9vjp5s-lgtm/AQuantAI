# Local Usage Guide

This guide describes the v0.1 local, research-only baseline. It is not production-ready, does not provide investment advice, and does not support live trading, broker connections, or order placement.

## Prerequisites

- Python 3.12.
- Docker Desktop is optional, only for the Docker and Docker Compose steps.

Run all commands from the repository root.

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
- http://127.0.0.1:8000/dashboard/overview
- http://127.0.0.1:8000/dashboard/report

Expected results:

- `/` reports version `0.1.0`.
- `/health` reports `{"status": "ok"}`.
- Both dashboard endpoints return JSON with `read_only: true` and the research disclaimer.

The Dashboard is a JSON-only, read-only API surface in v0.1. It is not a graphical web frontend. Its allowed actions are limited to viewing, inspecting, and exporting research output; it exposes no trading, order, or broker actions.

## Docker Image

Build the image:

```bash
docker build -t aquantai:v0.1 .
```

Start it on port 8000:

```bash
docker run --rm -p 8000:8000 aquantai:v0.1
```

Use the same four local URLs above to verify the API. Stop the foreground container with `Ctrl+C`.

## Docker Compose

Create local configuration from the public template:

```bash
cp .env.example .env
```

Start the app and PostgreSQL services:

```bash
docker compose up --build
```

The app is available on port 8000 and PostgreSQL is exposed on port 5432. PostgreSQL starts to validate the Compose environment, but database persistence is not implemented in the v0.1 baseline. The app remains a local, fixture-oriented research service and does not claim persisted research data.

Stop and remove the test stack, including its volume:

```bash
docker compose down -v --remove-orphans
```

Remove the temporary `.env` only if it was created from `.env.example` for this local test.

## Windows Docker Desktop Note

If PowerShell cannot find `docker` immediately after installing Docker Desktop, open a new terminal so its PATH is refreshed. Confirm the engine is ready with:

```bash
docker version
```

## v0.1 Boundaries

- Research and learning use only; not investment advice or a trading recommendation.
- No live data ingestion, real LLM calls, broker APIs, order placement, automatic trading, or production deployment.
- No graphical dashboard, authentication, account system, payment system, or database persistence.
