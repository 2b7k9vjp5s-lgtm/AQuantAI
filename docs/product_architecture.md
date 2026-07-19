# Personal Investment Research Product Architecture

`docs/architecture_baseline.md` is the authoritative source for current state, dependency direction, field ownership and delivery gates. This document describes product intent without authorizing implementation.

## Positioning

AQuantAI is a local-first, personal-use research workbench for attributable market data, deterministic quantitative analysis and evidence-backed industry/company research.

It is not a multi-user service, broker, order-management system or automated execution system.

Current state has three independent axes:

- released version: `0.2.0`;
- merged capability stage: v0.6D;
- runtime surfaces: fixture-backed read-only Dashboard plus database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured.

## Product flow

Long-term conceptual flow:

```text
Market monitoring
  -> Industry Alpha research
  -> Company research
  -> future price/timing interpretation
  -> future Watchlist and verification workflow
  -> future Paper Portfolio
  -> Quant review
```

Only the path through v0.6D industry/company quality judgments is implemented. Price judgment, timing judgment, Watchlist, verification-task lifecycle, Paper Portfolio and portfolio analysis remain prospective and unauthorized.

Later evidence may create a new revision or review context. It must not overwrite historical facts, claims, judgments or cutoff-date meaning.

## Information architecture

| Area | Purpose | Current state |
| --- | --- | --- |
| Dashboard | Fixture-backed Quant Core overview | Implemented in released `0.2.0`; read-only and sample-data-only |
| Market Cockpit | Explicit selected-series market context | v0.4A-v0.4E merged; read-only; no canonical valuation, signal or recommendation claims |
| Industry Alpha | Evidence ledger, chain maps, beneficiaries and Stage 2 research | v0.5A-v0.6D merged; read-only APIs/demos |
| Stock Research | Company research, expectations/valuation observations, catalysts/risks and quality judgments | v0.6A-v0.6D merged; no price/timing judgment or formal recommendation |
| Watchlist | Future research-status and verification workflow | Not authorized |
| Paper Portfolio | Future simulated records | Not authorized |
| Settings | Future local configuration surface | Planned; not authorized |
| Quant Core | Provider, factor, ranking, backtest, ML, report and Dashboard foundations | Implemented supporting layer |

## Dependency direction

```text
Frontend/read-only presentation
  -> FastAPI application services
  -> product-domain modules and stable provider interfaces
  -> PostgreSQL persistence and provider adapters
```

Research direction:

```text
market-data evidence
  -> v0.5 evidence ledger
  -> Stage 1 beneficiary boundary
  -> v0.6A company research
  -> v0.6B expectations and valuation observations
  -> v0.6C catalysts and risks
  -> v0.6D quality judgments
```

Rules:

- Product workflow ownership stays in AQuantAI.
- Providers and external projects are adapters or infrastructure, not owners of research state.
- Business modules depend on stable interfaces rather than one vendor.
- Quant Core supplies deterministic validation artifacts; it does not silently create workflow conclusions.
- Stage 2 starts only from exact frozen Stage 1 membership.
- Downstream records bind exact accepted revisions and links rather than newer compatible-looking records.

## Market-price and valuation ownership

The superseded v0.6E review established:

- Canonical market-price value, measurement kind, unit, currency, decimal normalization and provider/series provenance belong to a separately reviewed market-data/evidence contract.
- v0.6B valuation `observed_value` is generic recorded context and is not automatically eligible for price comparison.
- An optional v0.6B `daily_price` link remains provenance/context unless a future upstream contract explicitly provides comparison semantics.
- Names, free text, identifier patterns, valuation currency or fallback defaults cannot create missing price meaning.
- “Good price” and “good timing” are conceptual goals, not current runtime entities.

Issue #70 and PR #71 are superseded and closed without merge. No price-judgment model, migration or API exists.

## Research discipline

- Facts require evidence, provenance and an information cutoff.
- Inferences state basis and confidence.
- Missing evidence and unresolved conflicts remain explicit.
- D-grade leads cannot independently support a conclusion.
- Completed research outputs retain a bounded `后续验证清单`.
- Accepted records are versioned rather than overwritten.
- Historical reads enforce both information cutoff and actual UTC chronology.
- Unsupported operating facts must not be invented.

## Delivery gates

A future feature starts only after Architecture Preflight and Definition of Ready establish:

- a real user problem;
- field/domain ownership;
- production-reachable inputs;
- a production-realistic offline golden path;
- fixture/provider parity;
- explicit selectors and chronology;
- bounded scope, migration decision and stop conditions.

After every two domain slices, feature expansion pauses for consolidation review. Green CI is necessary but does not prove architecture acceptance.

## Current boundary

The only active architecture work is the docs-only baseline reset in Issue #72. It does not authorize Stage 2 refactoring, canonical market-price evidence, structured valuation comparison, v0.6E, v0.7, a migration, release or version change.