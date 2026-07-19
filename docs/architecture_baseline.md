# AQuantAI Authoritative Architecture Baseline

## Status and authority

This document is the authoritative architecture and current-state baseline. `.codex/WORKFLOW.md` controls execution gates, and an accepted linked GitHub Issue controls a specific task.

- Released software version: `0.2.0`.
- Merged capability stage: v0.6D.
- Provider-status synchronization base: `ca2a9fa0ca4daea6b7318a50851272b74c4dc115`.
- Accepted application/consolidation implementation baseline: `cf3ad09c9f9fb39dbaada7342435a8c7b2853b1a`.
- Runtime surfaces: local fixture-backed read-only Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured.
- Active application, consolidation implementation or migration authorization: none.

Docs-only commits may advance `main` without changing release, capability or runtime behavior. PR #73 established the unified baseline; PR #75 characterized Stage 2 consolidation; PR #77 extracted the neutral frozen boundary; PR #83 implemented the neutral ordered-row primitive; PR #89 implemented the accepted v0.6A-v0.6C query-value boundary; PR #93 kept evidence read serializers domain-local; PRs #97/#99 characterized and implemented command integrity translation; PRs #103/#105 characterized and implemented the neutral process-local revision-lock registry; PR #109 characterized Hithink as the preferred future A-share provider candidate.

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

## Accepted future provider direction

Issue #108 and PR #109 accept Hithink as the preferred future A-share provider candidate, not an active default or implemented provider. AKShare remains an explicit, separate provider-specific alternative, and all existing AKShare ingestion runs and canonical series remain immutable and readable.

One ingestion run and one canonical series contain exactly one provider. Silent fallback, provider relabeling and row-level provider mixing are prohibited. A caller may explicitly choose a separate provider run and series; persistence must not hide that distinction.

Canonical ingestion may use reviewed REST contracts or a separately reviewed market-dump importer. MCP or LLM-mediated calls are not canonical ingestion. Neither Hithink production path has reached Definition of Ready.

Issue #112 and Draft PR #113 explored only a credential-safe contract probe. The seven-file implementation passed fixed-head scope and safety review at `b09fcd8e68f4d280407b483a7d114aa0b0e8a015` and Actions `29691380530`, then Issue #112 closed as `not planned` and PR #113 closed without merge when the account owner deferred Hithink integration. No live probe ran, no API key was used, and no live contract, account permission or data-use acceptance was established.

No Hithink code, dependency, runtime/default-provider change, database/schema change or migration reached `main`. AKShare remains the implemented controlled provider path. Hithink is a deferred future candidate and may be reconsidered only through a new Architecture Preflight and explicit authorization.

Five neutral Stage 2 infrastructure boundaries are accepted:

- `industry_alpha.stage2_boundary` owns exact shared v0.6A/v0.6B frozen-boundary mechanics used by v0.6C and v0.6D;
- `industry_alpha.stage2_repository_rows` owns stateless ordered scalar row loading used through repository-local wrappers;
- `industry_alpha.stage2_query_values` owns required UTC normalization, date-granular visibility and timestamp/date/UUID formatting used by v0.6A-v0.6C query modules;
- `industry_alpha.stage2_integrity` owns stateless SQLAlchemy `IntegrityError` translation to `EvidenceLedgerConflictError` while preserving the caller-provided message and original cause.
- `industry_alpha.stage2_revision_locks` owns only the guarded process-local `(kind, UUID) -> RLock` registry shared by v0.6A-v0.6D commands.

Domain semantics remain local. Repository graph assembly, optional-ID normalization, link-field selection, missing-parent policy, sessions and transactions remain repository-local. Evidence read serialization, claim projection, missing-evidence wording, link selection, payload sorting, notices, aggregate errors and v0.6D timestamp-null policy remain query-module-local by the accepted PR #93 decision. Command modules retain the eight exact lock-kind strings and lock -> integrity translator -> transaction placement, conflict-message policy, transaction boundaries, rollback ownership, database row locks, latest-revision reads, revision-number allocation, supersession and retry policy. The shared registry has no cleanup or eviction and provides no cross-process or cross-host guarantee.

The current implementable path does not include v0.6E price judgment, timing judgment, Watchlist tasks, Paper Portfolio, simulated trades, portfolio analysis or Quant Core workflow state. Issue #70 and PR #71 remain superseded and closed without merge.

## Capability matrix

| Capability | Merged boundary | Remaining boundary |
| --- | --- | --- |
| v0.3 market-data persistence | Complete-snapshot PostgreSQL persistence, ingestion attempts, canonical series and cutoff-aware reads | Canonical arbitrary market-price measurement semantics are not a standalone evidence contract |
| v0.4A-v0.4E Market Cockpit | Read-only selected-scope breadth/risk, context, liquidity and descriptive price behavior | No official full-market, valuation, regime, signal or recommendation claims |
| v0.5A-v0.5C | Evidence ledger, industry maps, beneficiary classifications and candidate-pool handoff | Evidence qualification and frozen-link patterns remain repeated downstream |
| v0.6A | Company research and hypotheses | Integrity translation and the process-local lock registry are consolidated; row locks and revision allocation remain local |
| v0.6B | Expectations and valuation observations with optional price provenance | `observed_value` is not automatically comparison eligible; reduced evidence claim shape remains local |
| v0.6C | Catalyst and risk assessments | Frozen-boundary, ordered-row, query-value and integrity mechanics are consolidated; evidence serializer remains local |
| v0.6D | Industry/company quality judgments | Integrity translation and the process-local lock registry are consolidated; query-value/evidence serializer policies and revision allocation remain local |
| v0.6E | Superseded planning only | Not implemented or authorized |
| v0.7+ | Prospective only | Requires Architecture Preflight and Definition of Ready |

## Field and infrastructure ownership

| Information or mechanism | Authoritative owner | Rule |
| --- | --- | --- |
| Provider rows, series identity, ingestion status and cutoff | Market-data persistence | One explicit provider per run and series; no silent fallback, relabeling, row-level mixing or cross-run stitching |
| Canonical market-price value, measurement kind, unit, currency and decimal normalization | Future separately reviewed market-data/evidence contract | Downstream judgment code must not invent it |
| Evidence grades, claims, links and conflicts | v0.5 evidence ledger | Downstream slices freeze exact revisions and links |
| Company-research workflow and hypotheses | v0.6A | Downstream records bind exact revisions |
| Expectations and valuation observations | v0.6B | Recorded context remains generic without later comparison eligibility |
| Catalyst and risk state | v0.6C | Not monitors, alerts or task lifecycles |
| Industry/company quality outcome and evidence state | v0.6D | Does not generate price, timing or recommendation state |
| Shared frozen-boundary mechanics | `stage2_boundary.py` | Exact base-boundary loading and visibility; domain semantics remain local |
| Ordered scalar repository row loading | `stage2_repository_rows.py` | Explicit `IN` filtering and caller-owned ordering only |
| v0.6A-v0.6C pure query values | `stage2_query_values.py` | Required UTC, date-granular visibility and text formatting only |
| Evidence read serialization | v0.6B-v0.6D domain query modules | Reviewed in PR #93 and intentionally remains local |
| SQLAlchemy integrity translation | `stage2_integrity.py` | Translate only `IntegrityError`; exact messages and transaction ownership remain command-local |
| Process-local revision-lock registry | `stage2_revision_locks.py` | Guarded exact `(kind, UUID)` keys and reentrant lock identity only; eight kinds and call placement remain caller-owned |
| Revision allocation and database lock strategy | Stage 2 command modules | Row locks, latest-revision reads, revision-number allocation, supersession, cleanup/eviction and retry remain command-local |
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

- **D1 Documentation drift — controlled:** architecture/status synchronization follows accepted implementations and characterization decisions.
- **D2 Repeated Stage 2 structure — partially reduced:** frozen-boundary and ordered-row mechanics are consolidated; generic graph loading remains unjustified.
- **D3 Read utilities — reviewed:** v0.6A-v0.6C pure query values are consolidated. Evidence serializers remain local because no neutral claim contract reaches Definition of Ready; v0.6D query-value policy remains local.
- **D4 Command lifecycle and concurrency — partially reduced:** integrity translation and the process-local lock registry are consolidated; row locks, latest-revision reads, allocation, supersession, cleanup/eviction and retry remain command-local.
- **D5 ORM lifecycle — next characterization gate:** dynamic link-model factories and append-only listeners are mapper/event sensitive; no implementation is authorized before characterization.
- **D6 Test-matrix growth:** shared invariant tests and domain-semantic tests must remain distinct.
- **D7 Fixture-versus-production reachability — deferred:** the reviewed offline Hithink probe did not establish live contract, permission or data-use acceptance; a future provider attempt requires new preflight.
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
6. evidence read-serialization characterization — PR #93; decision: keep serializers local and open no implementation Issue;
7. command integrity characterization and implementation — PRs #97 and #99;
8. Issue #100 and its linked PR synchronize the completed integrity boundary without changing runtime behavior.
9. revision-lock characterization and implementation — Issues #102/#104 and PRs #103/#105.
10. Hithink provider characterization — Issue #108 and PR #109; preferred future candidate, no implementation authorization.
11. Hithink probe technical review — Issue #112 / PR #113; closed without merge after integration was deferred.

Current authorization state: no application feature, consolidation implementation or migration is authorized.

Prospective and separately authorized:

12. characterize ORM lifecycle concerns without implementing dynamic model factories or append-only listeners;
13. decide whether canonical market-price evidence has independent user value;
14. only then consider valuation comparison eligibility and whether price judgment needs persisted state or a deterministic read model;
15. do not start v0.7 until required upstream contracts and consolidation reviews are accepted;
16. reconsider Hithink only through a new Architecture Preflight and explicit authorization.

No prospective item is authorized by this document alone.
