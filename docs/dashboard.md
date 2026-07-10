# Dashboard

Phase 6 creates a read-only dashboard foundation for presenting research outputs. The goal is safe presentation contracts, not trading, production deployment, or account workflows.

## Dashboard Boundary

The dashboard consumes outputs from previous phases:

- factor summaries;
- backtest metrics;
- ML prediction summaries;
- research report summaries;
- source references.

Builder sample fixtures are used only when an input argument is `None`. Explicit empty lists or dictionaries are preserved as empty research inputs and are never silently replaced with sample data.

The dashboard does not fetch live market data, write to a database, place orders, connect to brokers, manage accounts, or perform trading actions.

## Data Contracts

Dashboard payloads include:

- `page_id`
- `title`
- `sections`
- `disclaimer`
- `allowed_actions`
- `source_refs`
- `read_only`

Supported section types include cards, metrics, tables, and report summaries.

## Minimum Sections

- project overview;
- factor summary;
- backtest summary;
- ML summary;
- research report summary;
- risk and disclaimer section.

## Allowed UI Behavior

The Phase 6 dashboard may expose read-only actions:

- view;
- inspect;
- export research.

## Disallowed UI Behavior

The dashboard must not expose:

- trading buttons;
- broker workflows;
- order placement;
- automatic trading;
- buy/sell/hold recommendation UI;
- guaranteed-performance claims;
- production authentication, account management, payment, subscription, or deployment workflows.

## Endpoints

Phase 6 adds deterministic sample JSON endpoints:

- `GET /dashboard/overview`
- `GET /dashboard/report`

These endpoints return local fixture/sample payloads only.

## Required Disclaimer

All dashboard payloads include the same research-only disclaimer used by reports:

```text
This report is for quantitative research and learning only. It is not investment advice, not a trading recommendation, and not an instruction to buy, sell, or hold any security.
```

## Phase 6 Limitations

Phase 6 does not implement broker APIs, order placement, automatic trading, live market data fetching inside tests, production user authentication, account management, payment/subscription features, production deployment pipelines, trading buttons, buy/sell/hold recommendation UI, or guaranteed-performance claims.

## Local Integration Demo

Run the post-Phase-6 local fixture demo with:

```bash
python -m scripts.demo_research_flow
```

The demo builds a deterministic research report and dashboard payload from local fixtures only. It does not call AKShare, Qlib, an LLM, a database, or any broker/trading service.
