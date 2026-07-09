# Dashboard

Phase 6 creates a read-only dashboard foundation for presenting research outputs. The goal is safe presentation contracts, not trading, production deployment, or account workflows.

## Dashboard Boundary

The dashboard consumes outputs from previous phases:

- factor summaries;
- backtest metrics;
- ML prediction summaries;
- research report summaries;
- source references.

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
