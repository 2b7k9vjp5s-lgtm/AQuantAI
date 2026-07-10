# v0.2 Release Checklist

This checklist is for the v0.2 local read-only research Dashboard baseline. It validates documentation, local tests, Docker startup, and fixture-only demos. It does not validate production deployment, live market ingestion, broker connectivity, order placement, or investment advice.

## Required Local Checks

Run from the repository root:

```bash
python -m pytest
python -m scripts.demo_research_flow
```

Expected result:

- All tests pass.
- The demo emits a local fixture-based research payload.
- No live data source, LLM provider, broker API, trading credential, or production service is required.

## API Smoke Checks

When the API is running with:

```bash
uvicorn backend.main:app --reload
```

Verify these local read-only endpoints:

- `GET /`
- `GET /health`
- `GET /dashboard`
- `GET /dashboard/overview`
- `GET /dashboard/report`

Expected result:

- Root metadata and FastAPI metadata report version `0.2.0`.
- Health returns `{"status": "ok"}`.
- The local Dashboard page and JSON endpoints return fixture-backed, read-only research presentation data.

## Release Boundary

Before tagging or announcing v0.2, confirm:

- README, `pyproject.toml`, FastAPI metadata, and roadmap status all refer to version `0.2.0` or the v0.2 local Dashboard baseline consistently.
- Documentation does not claim production readiness.
- The project remains research-only and learning-only.
- There are no trading buttons, broker integrations, order placement flows, production deployment pipelines, or live credential requirements.
- Optional adapters remain lazy boundaries and are not required by tests or demos.

## GitHub Actions Scope

The v0.2 CI workflow may install package dependencies, run pytest, and run the local fixture demo only. It must not deploy, publish releases, call paid external services, fetch live market data, use secrets, or connect to broker/trading systems.
