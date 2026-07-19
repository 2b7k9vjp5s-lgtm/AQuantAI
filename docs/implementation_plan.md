# Personal Investment Research Implementation Plan

This plan is prospective. It summarizes merged capability stages and the required gates for future work. It does not authorize implementation by itself.

`docs/architecture_baseline.md` is authoritative for current state, ownership, invariants, architecture debt and delivery gates.

## Current state

- Released software version: `0.2.0`
- Merged capability stage: v0.6D
- Runtime surfaces: fixture-backed read-only Dashboard plus database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured
- Current authorized work: docs-only architecture baseline reset in Issue #72
- Current application implementation authorization: none

Merged capability stages do not automatically publish a new release.

## Completed capability stages

### v0.2 local read-only baseline

Implemented released baseline:

- deterministic Quant Core contracts;
- local fixture-backed Dashboard and JSON APIs;
- local demo, tests and safety wording;
- no production data or execution claims.

### v0.3 market-data persistence

Implemented:

- reviewed provider interfaces and normalized contracts;
- PostgreSQL migrations and explicit session boundary;
- immutable ingestion attempts and complete-snapshot reconciliation;
- canonical snapshot-series identities;
- controlled manual AKShare ingestion and offline fixtures;
- provenance, validation and cutoff-aware reads.

### v0.4A-v0.4E Market Cockpit

Implemented selected-scope descriptive contexts:

- breadth, participation, volatility and drawdown;
- optional separate benchmark context;
- provider-attributed sector context;
- liquidity distribution and concentration;
- descriptive price-behavior proxies.

Excluded: full-market claims, canonical style/valuation/regime/crowding, signals, recommendations, automatic collection and trading.

### v0.5A-v0.5C Industry Alpha Stage 1

Implemented:

- research cases, evidence, claims, conflicts and immutable revisions;
- evidence-backed chain maps and assertions;
- beneficiary classifications and exact candidate-pool handoff.

Excluded: scoring, company deep-dive conclusions, recommendations, portfolio and trading behavior.

### v0.6A-v0.6D Stage 2

Implemented:

- v0.6A company-research revisions and financial-transmission hypotheses;
- v0.6B expectation and valuation-observation revisions;
- v0.6C catalyst and risk assessments;
- v0.6D industry/company quality judgments.

These stages bind exact accepted upstream revisions and evidence, preserve cutoff plus UTC chronology and expose read-only deterministic APIs/demos.

Excluded: target/fair value, expected return, automatic conclusions, ranking, recommendations, price/timing judgment, Watchlist state, portfolio action and trading.

## Superseded v0.6E plan

Issue #70 and PR #71 are closed without merge. No v0.6E application code or migration was implemented.

The plan was superseded because the repository must first settle:

- canonical market-price measurement, unit and currency ownership;
- structured comparison eligibility for valuation observations;
- production-realistic fixture/provider parity;
- Stage 2 repeated-boundary and test-matrix consolidation.

A v0.6B `daily_price` link remains provenance/context. Generic `observed_value` is not automatically a price-comparison reference.

## Architecture reset — active Issue #72

The active docs-only stage must:

- establish the three-axis state model;
- align README, roadmap, review and architecture documents;
- record the capability matrix through v0.6D;
- define dependency and field/domain ownership;
- centralize architecture invariants;
- record architecture debt;
- introduce Architecture Preflight, Definition of Ready, golden-path-first, reset and consolidation gates.

It must not change application behavior, migrations, tests, fixtures, provider behavior, version or release metadata.

## Required future process

Every future capability follows:

```text
Architecture Preflight
  -> Definition of Ready
  -> authoritative GitHub Issue
  -> task synchronization and planning review
  -> explicit implementation authorization
  -> implementation review
  -> explicit merge authorization
  -> architecture/status synchronization
```

### Architecture Preflight

Before a feature Issue exists, establish:

- user problem and missing capability;
- field/domain ownership;
- real provider or accepted upstream source for each input;
- one production-realistic offline golden path;
- important failure path;
- migration/runtime impact;
- conflicts with current architecture;
- smallest viable slice and exclusions.

### Definition of Ready

Implementation requires:

- accepted input/output contracts;
- explicit ownership table;
- production-reachable golden path;
- fixture/provider parity evidence;
- exact selectors and chronology;
- explicit migration decision;
- one main domain capability and at most one infrastructure change;
- acceptance tests and stop conditions.

### Reset rule

Stop and create a new architecture decision rather than extending the task file when:

- two rounds of foundational blockers occur;
- production reachability fails;
- a material field has no single owner;
- semantics rely on free text, names, identifier patterns or defaults;
- one slice requires multiple infrastructure foundations;
- project documents materially disagree.

### Consolidation cadence

After every two domain slices, pause new features and review:

- duplicated models, repositories, validators and serializers;
- schema and frozen-link growth;
- test count and cross-product growth;
- API consistency;
- next-stage input reachability;
- status-document consistency.

Green CI is necessary regression evidence but not architecture acceptance.

## Candidate next stages — not authorized

### Stage 2 consolidation characterization

Potential objective: measure repeated v0.6A-v0.6D revision allocation, append-only enforcement, evidence qualification, cutoff validation, repository/query, fixture and database-test patterns.

Default constraint: no migration and no schema rewrite. A later proposal may extract only justified shared Python-layer utilities.

### Canonical market-price evidence

Potential objective: define a standalone market-data/evidence object with canonical decimal text, measurement kind, unit, currency, trade date, adjustment, provider, series/run identity and chronology.

This stage must have independent user value and a production-realistic offline AKShare path. It must not create below/at/above, good-price, recommendation or timing state.

### Structured valuation comparison eligibility

Potential objective: explicitly state whether a valuation observation is a compatible price-per-share reference and what role it serves.

Generic `observed_value` remains ineligible by default. This stage must not create target price, fair value or expected return.

### Re-evaluate price interpretation

Only after accepted upstream contracts exist, decide whether a separate persisted price-judgment aggregate is necessary. Prefer a deterministic read model when the relationship can be reproduced without duplicating state.

### v0.7 Watchlist and verification workflow

Not authorized. It may be reconsidered only after the architecture baseline and required consolidation review are accepted. Follow-up verification text in current records is not yet a task lifecycle.

### v0.8 Paper Portfolio

Not authorized. Future records must be explicitly simulated and have no broker or real-order meaning.

### v0.9 portfolio analysis and Quant Core integration

Not authorized. Future analysis must remain traceable and must not create autonomous allocation or execution.

## Locked exclusions

Without a separate accepted Issue, do not add:

- application behavior from this plan;
- migrations;
- v0.6E price or timing judgment;
- v0.7+ workflow entities;
- new mutation UI/API;
- automatic provider collection;
- production LLM execution;
- recommendations, broker actions, orders or automated trading;
- release/tag or version change;
- modification of PR #38.