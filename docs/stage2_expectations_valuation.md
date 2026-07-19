# Stage 2 Expectations And Valuation Snapshots

v0.6B adds local, append-only records for market expectations and valuation-context observations. The module is research-only and read-only through HTTP.

## Boundaries

- Every expectation or valuation revision freezes one exact v0.6A company-research revision.
- Every revision freezes exact supported or disputed financial-transmission hypothesis revisions.
- Every revision freezes exact claim revisions and visible evidence links from those hypothesis boundaries.
- Valuation snapshots may optionally bind one exact local `daily_price` row from a successful ingestion run.
- Historical views require both `information_cutoff_date <= as_of_cutoff` and `recorded_at_utc` date `<= as_of_cutoff`.
- Later evidence, links, price rows, or revisions do not leak into earlier views.

## Unsupported

The module does not compute target price, fair value, expected return, upside/downside, score, rank, recommendation, good-price/good-timing, catalyst/risk judgment, DCF, comparable-company automation, provider collection, LLM output, watchlist action, portfolio action, broker action, order, or trade.

## Read-Only API

- `GET /industry-alpha/market-expectations`
- `GET /industry-alpha/market-expectations/{expectation_id}`
- `GET /industry-alpha/valuation-snapshots`
- `GET /industry-alpha/valuation-snapshots/{valuation_id}`

All endpoints accept optional `as_of_cutoff=YYYY-MM-DD`. List endpoints also accept optional `company_research_id`.

## Offline Demo

```bash
python -m scripts.demo_stage2_expectations_valuation
```

The demo uses an in-memory SQLite database, deterministic fixtures, and no network access.
