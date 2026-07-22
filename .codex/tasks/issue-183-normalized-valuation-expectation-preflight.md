# Issue #183 — Normalized Valuation and Expectation Metrics v1 Architecture Preflight

## Authority

- GitHub Issue: #183
- Product Roadmap: #137, Slice 5
- Required base: `9ac65e1677d6377958e3c3b6ee71f0178bfb9eda`
- Risk tier: **Strict**
- Owner authorization: `合并 PR #182，并进行下一步开发` on 2026-07-22
- Architecture only; no production schema, migration, runtime, Provider, release or version change

## Objective

Define one implementable, local-first and non-advisory architecture for structured financial observations, deterministic normalized valuation metrics, historical/peer comparison context and numeric expectation gaps.

The architecture must answer:

> Given one exact accepted price and explicit financial observations, what valuation metric is reproducibly calculable, is it comparable across time or peers, what did actual results differ from explicit expectations by, and why is any result missing or non-meaningful?

No output may become fair value, target price, expected return or trade advice.

## Accepted upstream boundaries

Reuse without mutation or backfill:

- v0.6B market-expectation and valuation-observation identities/revisions;
- v0.6A Company Research and financial hypotheses;
- Evidence Ledger claims and evidence;
- Listed Instrument, Canonical Price and Comparison Eligibility;
- Investment Candidate v1 component and snapshot revisions.

Existing v0.6B free-text `metric_context`, `observed_value`, expectation `basis` and direction cannot be parsed or silently promoted into structured numeric inputs.

## Required architecture decisions

### Structured financial observations

Close ownership, revision, provenance, period, horizon, currency, unit, scale and state for at least:

1. `diluted_shares_outstanding`
2. `revenue`
3. `net_profit_attributable`
4. `ebitda`
5. `free_cash_flow`
6. `net_debt`

Supported source kinds must distinguish actual, guidance, consensus and explicit research assumption. No Provider, name, stock-code, free-text or AI inference is permitted.

### Normalized valuation formulas

Close exact formula/input contracts for:

- `pe`
- `ps`
- `ev_ebitda`
- `fcf_yield`

Candidate rule version: `aquantai.normalized-valuation.v1`.

```text
equity_value = price_per_share * diluted_shares_outstanding
enterprise_value = equity_value + net_debt
pe = equity_value / net_profit_attributable
ps = equity_value / revenue
ev_ebitda = enterprise_value / ebitda
fcf_yield_pct = free_cash_flow / equity_value * 100
```

All arithmetic uses Decimal and `ROUND_HALF_EVEN`; exact intermediate/final scale must be decided.

### Non-meaningful states

- nonpositive net profit blocks PE;
- nonpositive EBITDA blocks EV/EBITDA;
- nonpositive revenue blocks PS;
- negative FCF yield remains numeric but explicitly negative;
- no absolute-value denominator, epsilon, clipping, imputation or period substitution.

### Price, currency and unit compatibility

- exact accepted Canonical Price revision;
- exact eligible Comparison Eligibility revision under a reviewed purpose;
- explicit instrument, currency, price kind, adjustment basis and share unit;
- no FX or corporate-action engine in v1;
- incompatible share-count/price chronology fails closed.

### Historical comparison

Define append-only frozen historical sets, exact member revisions, minimum sample/time-span rules, deterministic percentile/tie formula, insufficient-history state and no newest-row selection.

### Peer comparison

Define analyst-owned peer-set identity/revisions, exact membership, complete membership preservation, per-member eligibility, same metric/formula/period/horizon/currency/unit/accounting scope and deterministic comparison outputs. Peer selection is D3; comparison arithmetic is D1/D2.

### Structured expectation gap

Candidate rule version: `aquantai.normalized-expectation-gap.v1`.

```text
absolute_gap = actual_value - expected_value
percentage_gap = (actual_value - expected_value) / abs(expected_value) * 100
```

Close zero-expected behavior, directionality, source kind, same metric/period/unit/currency/accounting scope and missing/disputed/stale behavior.

### Investment Candidate integration

Normalized metrics may be exact supporting inputs for newly recorded analyst-owned `valuation_context` and `expectation_gap` component revisions. They must not mutate or automatically rescore existing components or snapshots.

Prefer additive bridge records over existing-table mutation or generic UUID/type links.

### Persistence candidate

Decide the minimum additive append-only schema for:

- financial observation identities/revisions/input links;
- normalized valuation identities/revisions/formula links;
- historical and peer comparison set identities/revisions/members;
- expectation-gap identities/revisions/input links;
- optional additive Investment Candidate bridge links.

No existing table mutation/backfill. Populated downgrade must refuse before any destructive drop.

### Commands and reads

Define bounded local UTF-8 JSON commands with strict fields, dry-run, expected-latest protection, exact IDs, one transaction, zero partial writes, strict JSON and no network/AI.

Define exact-ID read-only APIs and a Chinese-first read surface requiring both as-of boundaries.

## Golden path

One production-reachable offline fixture must create:

1. four explicit peer companies;
2. exact accepted canonical prices;
3. explicit TTM/forward financial observations;
4. deterministic PE, PS, EV/EBITDA and FCF yield;
5. one loss-making PE marked non-meaningful;
6. one sufficient frozen historical set;
7. one explicit peer set preserving one ineligible member;
8. one expected and one actual net-profit observation;
9. deterministic absolute and percentage expectation gap;
10. exact-ID readback with provenance and zero hidden network.

## Primary failure path

Fail before any write for:

- identity, currency, unit, period, horizon or accounting-scope conflict;
- missing/ineligible price contract;
- free-text parsing or unowned inference;
- omitted/duplicated/substituted comparison members;
- input outside either as-of boundary;
- incomparable expected/actual records;
- expected-latest conflict.

## Stop conditions

Return to architecture if:

- a required financial value lacks an authoritative owner;
- success requires Provider/network, FX, corporate-action logic or a free-text parser;
- a generic abstraction hides different domain semantics;
- integration would silently alter existing Investment Candidate accepted state.

## Deliverables

- this task snapshot;
- `docs/normalized_valuation_expectation_preflight.md`;
- bounded `docs/architecture_baseline.md` current-state correction;
- Draft architecture PR based exactly on the required base;
- repository checks and author fixed-head handoff;
- independent fixed-head architecture review.

## Required approval

`NORMALIZED VALUATION AND EXPECTATION METRICS PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`

## Locked exclusions

No production code, schema, migration, external network, Provider, ingestion, crawling, browsing, hidden consensus feed, FX acquisition, corporate-action engine, automatic peer discovery, free-text parsing, target price, fair value, expected return, performance promise, buy/sell/hold output, portfolio, position sizing, broker/trading, AI-owned accepted state, automatic Investment Candidate score change, existing-row mutation/backfill, release, tag or version change.