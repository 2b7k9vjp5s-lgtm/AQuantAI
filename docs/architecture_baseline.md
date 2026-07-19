# AQuantAI Authoritative Architecture Baseline

## Status and authority

This document is the authoritative architecture and current-state baseline. `.codex/WORKFLOW.md` controls execution gates, and an accepted linked GitHub Issue controls a specific task.

- Released software version: `0.2.0`.
- Merged capability stage: v0.6D.
- Accepted application/consolidation implementation baseline: `782b2362e1252aa87b21f7aa58f764837f5adb71`.
- Runtime surfaces: local fixture-backed read-only Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured.
- Active application, consolidation implementation or migration authorization: none.

Docs-only commits may advance `main` without changing release, capability or runtime behavior. PR #73 established the unified baseline; PR #75 characterized Stage 2 consolidation; PR #77 extracted the neutral frozen boundary; PR #81 characterized ordered repository row loading; PR #83 implemented the neutral row loader; PR #87 characterized query-value mechanics; PR #89 implemented the accepted v0.6A-v0.6C query-value boundary.

## Product boundary

AQuantAI is a local-first, personal-use, research-only and non-advisory workbench. It is not a broker, order-management system, automated-trading system, investment-advice service, multi-user SaaS product or production deployment platform.

Deterministic calculations, canonicalization, selectors and state transitions belong to reviewed application code. An LLM may assist only behind an explicit adapter and may not own evidence qualification, deterministic state, execution or trading behavior.

## Implemented dependency direction

```text
market-data evidence
  -> v0.5 evidence ledger
  -> Stage 1 industry map and beneficiary boundary
  -> v0.6A company research and financial-transmission hypotheses
  -> v0.6B expectations and valuation observations
  -> v0.6C catalyst and risk assessments
  -> v0.6D industry and company quality judgments
```

Downstream records freeze exact accepted upstream revisions and links. They do not silently select newer records, infer missing state or rewrite historical meaning.

Three neutral Stage 2 infrastructure boundaries are accepted:

- `industry_alpha.stage2_boundary` owns exact shared v0.6A/v0.6B frozen-boundary mechanics used by v0.6C and v0.6D;
- `industry_alpha.stage2_repository_rows` owns stateless ordered scalar row loading used through repository-local wrappers;
- `industry_alpha.stage2_query_values` owns required UTC normalization, date-granular visibility and timestamp/date/UUID formatting used by v0.6A-v0.6C query modules.

Domain semantics remain local. Repository graph assembly, optional-ID normalization, link-field selection, missing-parent policy, sessions and transactions remain repository-local. Evidence serialization, link selection, payload sorting, notices, aggregate errors and v0.6D timestamp-null policy remain query-module-local.

The current implementable path does not include v0.6E price judgment, timing judgment, Watchlist tasks, Paper Portfolio, simulated trades, portfolio analysis or Quant Core workflow state. Issue #70 and PR #71 remain superseded and closed without merge.

## Capability matrix

| Capability | Merged boundary | Remaining boundary |
| --- | --- | --- |
| v0.3 market-data persistence | Complete-snapshot PostgreSQL persistence, ingestion attempts, canonical series and cutoff-aware reads | Canonical arbitrary market-price measurement semantics are not a standalone evidence contract |
| v0.4A-v0.4E Market Cockpit | Read-only selected-scope breadth/risk, context, liquidity and descriptive price behavior | No official full-market, valuation, regime, signal or recommendation claims |
| v0.5A-v0.5C | Evidence ledger, industry maps, beneficiary classifications and candidate-pool handoff | Evidence qualification and frozen-link patterns remain repeated downstream |
| v0.6A | Company research and hypotheses | Command lifecycle and revision allocation remain local |
| v0.6B | Expectations and valuation observations with optional price provenance | `observed_value` is not automatically comparison eligible |
| v0.6C | Catalyst and risk assessments | Frozen-boundary, ordered-row and query-value mechanics are consolidated; domain read serialization remains local |
| v0.6D | Industry/company quality judgments | Query-value helpers remain local because malformed-null semantics differ; lifecycle repetition needs separate review |
| v0.6E | Superseded planning only | Not implemented or authorized |
| v0.7+ | Prospective only | Requires Architecture Preflight and Definition of Ready |

## Field and infrastructure ownership

| Information or mechanism | Authoritative owner | Rule |
| --- | --- | --- |
| Provider rows, series identity, ingestion status and cutoff | Market-data persistence | Explicit series/run selection; no provider-only fallback or cross-run stitching |
| Canonical market-price value, measurement kind, unit, currency and decimal normalization | Future separately reviewed market-data/evidence contract | Downstream judgment code must not invent it |
| Evidence grades, claims, links and conflicts | v0.5 evidence ledger | Downstream slices freeze exact revisions and links |
| Company-research workflow and hypotheses | v0.6A | Downstream records bind exact revisions |
| Expectations and valuation observations | v0.6B | Recorded context remains generic without later comparison eligibility |
| Catalyst and risk state | v0.6C | Not monitors, alerts or task lifecycles |
| Industry/company quality outcome and evidence state | v0.6D | Does not generate price, timing or recommendation state |
| Shared frozen-boundary mechanics | `stage2_boundary.py` | Exact base-boundary loading and visibility; domain semantics remain local |
| Ordered scalar repository row loading | `stage2_repository_rows.py` | Explicit `IN` filtering and caller-owned ordering only |
| v0.6A-v0.6C pure query values | `stage2_query_values.py` | Required UTC, date-granular visibility and text formatting only |
| Evidence read serialization | Domain query modules pending a neutral contract | No shared serializer is authorized |
| “Good price” and “good timing” | Conceptual future workflow | Not current runtime entities |

A linked local `daily_price` row remains provenance/context. It is not a canonical comparison value merely because a valuation record also stores a numeric string and currency.

## Shared architecture invariants

1. Local and non-advisory: no advice, performance promise, broker, real order or automated trading.
2. Deterministic calculations and state stay outside LLM ownership.
3. Imports, startup, tests, CI, fixture demos and ordinary reads perform no hidden external network access.
4. Exact IDs, series keys, scopes, dates and revisions are explicit.
5. Downstream accepted records freeze exact revisions and links.
6. Corrections append revisions; accepted history is not mutated through ordinary paths.
7. Information cutoff and UTC chronology both prevent later-information leakage.
8. Conflicts, contradictions, missing evidence and uncertainty remain visible.
9. Identity, revision and links commit or roll back together.
10. Ordering, revision allocation, decimal text and strict JSON are deterministic across supported databases.
11. Fixture success paths must be reachable through reviewed production adapters.
12. Mutations, notifications, tasks and portfolio state require separate authorization.
13. Credentials and raw connection details never enter source, fixtures, Issues, PRs, logs or user errors.
14. Capability/consolidation merges do not change the released version without a separate release decision.

## Architecture debt register

- **D1 Documentation drift — controlled:** architecture/status synchronization follows accepted implementations.
- **D2 Repeated Stage 2 structure — partially reduced:** frozen-boundary and ordered-row mechanics are consolidated; generic graph loading remains unjustified.
- **D3 Read utilities — partially reduced:** v0.6A-v0.6C pure query values are consolidated. Evidence read serialization still requires a neutral contract; v0.6D query-value policy remains local.
- **D4 Command lifecycle and concurrency — deferred:** integrity translation, revision allocation and locks affect rollback and error compatibility.
- **D5 ORM lifecycle — deferred:** dynamic link-model factories and append-only listeners are mapper/event sensitive.
- **D6 Test-matrix growth:** shared invariant tests and domain-semantic tests must remain distinct.
- **D7 Fixture-versus-production reachability:** success paths need production-realistic offline adapter parity.
- **D8 Missing canonical market-price semantics:** `DailyPriceRecord` is not a complete arbitrary price-comparison evidence object.
- **D9 Consolidation cadence:** review after every two domain slices and earlier when ownership ambiguity appears.

## Development gates

1. **Architecture Preflight:** document the problem, ownership, inputs, golden/failure paths, migration/dependency impact, conflicts, smallest slice and exclusions.
2. **Definition of Ready:** require one objective, accepted contracts, ownership, reachable paths, explicit selectors/chronology, migration decision, bounded tests and stop conditions.
3. **Planning before implementation:** architecture decisions precede the Issue; task files execute accepted decisions.
4. **Reset threshold:** reset when ownership is ambiguous, semantics depend on inference/defaults, production cannot reach the path, or documents materially disagree.
5. **Consolidation cadence:** review documentation, duplicated infrastructure, schema/link growth, tests, APIs and next-stage reachability.
6. **Review evidence:** green CI is necessary but not sufficient; ownership, reachability, semantics and scope must also pass.

## Near-term sequence

Completed:

1. unified architecture baseline — PR #73;
2. Stage 2 consolidation characterization — PR #75;
3. neutral frozen-boundary extraction — PR #77;
4. ordered-row characterization and implementation — PRs #81 and #83;
5. query-value characterization and implementation — PRs #87 and #89;
6. Issue #90 and its linked PR synchronize the query-value outcome without changing runtime behavior.

Current authorization state: no application feature, consolidation implementation or migration is authorized.

Prospective and separately authorized:

7. characterize a neutral evidence read-serialization contract; characterization may conclude serializers should remain local;
8. only if accepted, consider the smallest behavior-preserving serializer implementation;
9. separately characterize command integrity/conflict handling, revision allocation/locks and ORM lifecycle concerns;
10. decide whether canonical market-price evidence has independent user value;
11. only then consider valuation comparison eligibility and whether price judgment needs persisted state or a deterministic read model;
12. do not start v0.7 until required upstream contracts and consolidation reviews are accepted.

No prospective item is authorized by this document alone.