# AQuantAI Authoritative Architecture Baseline

## Status and authority

This document is the authoritative architecture and current-state baseline. `.codex/WORKFLOW.md` controls execution gates, and an accepted linked GitHub Issue controls a specific task.

- Released software version: `0.2.0`.
- Merged capability stage: v0.6D.
- Accepted application/consolidation implementation baseline: `e424fa3a95e35b20f5fe8d8ada211821d9661efd`.
- Runtime surfaces: local fixture-backed read-only Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured.
- Active application, consolidation implementation or migration authorization: none.

Docs-only commits may advance `main` without changing the released version, capability stage or runtime behavior. PR #73 established the unified baseline; PR #75 characterized Stage 2 consolidation; PR #77 extracted the neutral frozen boundary; PR #81 characterized ordered repository row loading; PR #83 implemented the neutral ordered row loader. Issue #84 and its linked synchronization PR record the resulting state.

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

Two neutral Stage 2 infrastructure boundaries are now accepted:

- `industry_alpha.stage2_boundary` owns exact shared v0.6A/v0.6B frozen-boundary mechanics used by v0.6C and v0.6D;
- `industry_alpha.stage2_repository_rows` owns one stateless ordered scalar row-loading primitive used through repository-local private wrappers.

Catalyst/risk and quality-judgment semantics remain in their domain modules. Repository graph assembly, v0.6B `None` normalization, link-field selection, missing-parent policy and session/transaction ownership remain local.

The current implementable path does not include v0.6E price judgment, timing judgment, Watchlist tasks, Paper Portfolio, simulated trades, portfolio analysis or Quant Core workflow state. Issue #70 and PR #71 remain superseded and closed without merge.

## Capability matrix

| Capability | Merged boundary | Explicit boundary and remaining debt |
| --- | --- | --- |
| v0.3 market-data persistence | Complete-snapshot PostgreSQL persistence, ingestion attempts, canonical series and cutoff-aware reads | Manual bounded ingestion; canonical market-price measurement kind/unit/currency is not a standalone evidence contract |
| v0.4A-v0.4E Market Cockpit | Selected-scope breadth/risk, benchmark/sector context, liquidity and descriptive price behavior | Read-only and non-advisory; no official full-market, valuation, regime, signal or recommendation claims |
| v0.5A-v0.5C | Evidence ledger, industry-chain maps, beneficiary classifications and candidate-pool handoff | Evidence qualification and exact frozen-link patterns remain repeated downstream |
| v0.6A | Company research and financial-transmission hypotheses | Revision allocation, append-only and evidence checks remain repeated |
| v0.6B | Expectations and valuation observations with optional local-price provenance | Generic `observed_value` is not automatically comparison eligible; no target/fair value or timing output |
| v0.6C | Catalyst and risk assessments over exact frozen boundaries | Base-boundary and ordered-row mechanics are consolidated; query/concurrency/ORM repetition remains |
| v0.6D | Independent industry/company quality judgments | Incorrect private dependency and repeated ordered-row mechanics are removed; remaining query and lifecycle infrastructure needs separate review |
| v0.6E | Superseded planning only | Not implemented or authorized |
| v0.7+ | Prospective only | Not authorized; requires Architecture Preflight and Definition of Ready |

## Field and infrastructure ownership

| Information or mechanism | Authoritative owner | Rule |
| --- | --- | --- |
| Provider rows, series identity, ingestion status and cutoff | Market-data persistence | Explicit series/run selection; no provider-only fallback or cross-run stitching |
| Canonical market-price value, measurement kind, unit, currency and decimal normalization | Future separately reviewed market-data/evidence contract | Downstream judgment code must not invent it |
| Evidence grades, claims, links and conflicts | v0.5 evidence ledger | Downstream slices freeze exact revisions and links |
| Company-research workflow and hypotheses | v0.6A | Downstream records bind exact revisions |
| Expectations and valuation observations | v0.6B | Recorded context remains generic unless a later contract grants comparison eligibility |
| Catalyst and risk state | v0.6C | Not monitors, alerts or task lifecycles |
| Industry/company quality outcome and evidence state | v0.6D | Does not automatically generate price, timing or recommendation state |
| Shared v0.6A/v0.6B frozen-boundary mechanics | Neutral Stage 2 infrastructure | `stage2_boundary.py` owns exact base-boundary loading and visibility; domain semantics remain local |
| Ordered scalar repository row loading | Neutral Stage 2 infrastructure | `stage2_repository_rows.py` executes explicit `IN` filtering and caller-owned ordering; all normalization and graph semantics remain local |
| “Good price” and “good timing” | Conceptual future workflow | Not current runtime entities |

A linked local `daily_price` row remains provenance/context. It is not a canonical comparison value merely because a valuation record also stores a numeric string and currency.

## Shared architecture invariants

1. **Local and non-advisory:** no advice, performance promise, broker, real order or automated trading.
2. **Deterministic ownership:** deterministic calculations and state stay outside LLM ownership.
3. **No hidden network:** imports, startup, tests, CI, fixture demos and ordinary reads perform no external network access.
4. **Explicit selection:** exact IDs, series keys, scopes, dates and revisions are required; names, free text and defaults are not substitutes.
5. **Exact revision boundaries:** downstream accepted records freeze exact revisions and links.
6. **Append-only history:** corrections append revisions; accepted history is not mutated through ordinary paths.
7. **Dual visibility:** information cutoff and actual UTC chronology both prevent later-information leakage.
8. **Visible uncertainty:** conflicts, contradictions, missing evidence and uncertainty remain explicit.
9. **Atomicity:** identity, revision and links commit together or roll back together.
10. **Determinism:** ordering, revision allocation, decimal text and strict JSON are deterministic across supported databases.
11. **Fixture/provider parity:** fixture success paths must use fields reachable through the reviewed adapter boundary.
12. **Read-only by default:** mutations, notifications, tasks and portfolio state need separate authorization.
13. **Secrets and diagnostics:** credentials and raw connection details never enter source, fixtures, Issues, PRs, logs or user errors.
14. **Release independence:** merging capability or consolidation work does not change the released version without a separate release decision.

## Architecture debt register

- **D1 Documentation drift — controlled:** architecture/status synchronization is required after accepted implementation changes.
- **D2 Repeated Stage 2 structure — partially reduced:** PR #77 consolidated the neutral frozen boundary and PR #83 consolidated ordered scalar row loading. Generic graph loading remains unjustified.
- **D3 Read and validation utilities — partially reduced:** pure query visibility/date/UTC/UUID formatting is the next characterization candidate; evidence serialization still requires a neutral contract.
- **D4 Command lifecycle and concurrency — deferred:** revision allocation, lock strategy and integrity translation affect rollback and error compatibility.
- **D5 ORM lifecycle — deferred:** dynamic link-model factories and append-only listeners are mapper/event sensitive and may remain duplicated.
- **D6 Test-matrix growth:** future slices must separate shared invariant tests from domain-specific semantic tests.
- **D7 Fixture-versus-production reachability:** every success path needs production-realistic offline adapter parity.
- **D8 Missing canonical market-price semantics:** `DailyPriceRecord` is not a complete arbitrary price-comparison evidence object.
- **D9 Consolidation cadence:** review is mandatory after every two domain slices and earlier when duplication or ownership ambiguity appears.

## Development gates

### Gate 1: Architecture Preflight

Before a feature or consolidation implementation Issue, document the user or maintenance problem, ownership, real inputs where applicable, one reachable golden path, a failure path, migration/dependency impact, document conflicts, smallest slice and exclusions.

### Gate 2: Definition of Ready

Require one objective, accepted contracts, ownership, a reachable golden path, applicable fixture/provider parity, explicit selectors and chronology, a migration decision, bounded scope, acceptance tests and stop conditions.

### Gate 3: Planning and implementation separation

Architecture decisions precede a concise Issue. A task file is an executable snapshot, not a place to discover fundamental ownership. Application code begins only after planning acceptance is synchronized to GitHub.

### Gate 4: Reset threshold

Reset rather than patch repeatedly when foundational blockers recur, a production adapter cannot reach the success path, ownership is ambiguous, core semantics depend on inference/defaults, one slice introduces multiple infrastructure boundaries, or project documents materially disagree.

### Gate 5: Consolidation cadence

After every two domain slices, review documentation, duplicated infrastructure, schema/link growth, test-matrix growth, API consistency and next-stage input reachability.

### Gate 6: Review evidence

Green CI is necessary but not sufficient. Review must also establish ownership, production reachability, fixture parity, explicit semantics and coherent scope.

## Near-term sequence

Completed:

1. unified architecture baseline accepted in PR #73;
2. Stage 2 consolidation characterized in PR #75;
3. neutral Stage 2 frozen-boundary extraction accepted in PR #77;
4. ordered repository row loading characterized in PR #81;
5. neutral ordered scalar row loader accepted in PR #83;
6. Issue #84 and its linked PR synchronize those outcomes without changing application behavior.

Current authorization state: no application feature, consolidation implementation or migration is authorized.

Prospective and separately authorized:

7. characterize pure query visibility/date/UTC/UUID formatting;
8. consider a minimal pure-helper implementation only if semantics and payload compatibility are proven identical;
9. characterize evidence read serialization only after defining a neutral contract;
10. decide whether canonical market-price evidence has independent user value;
11. only then consider structured valuation comparison eligibility;
12. re-evaluate whether price judgment needs persisted state or a deterministic read model;
13. do not start v0.7 until required upstream contracts and consolidation reviews are accepted.

No prospective item is authorized by this document alone.
