# AQuantAI Authoritative Architecture Baseline

## Status and authority

This document is the authoritative architecture and current-state baseline for future reviewed work.

It does not publish a new release and does not authorize a feature. The released software version remains `0.2.0`. The merged capability stage on `main` remains v0.6D. The accepted `main` commit after the first Stage 2 consolidation implementation is `4b6377169fabb8eef5f1b421e8f008a11582f8a9`.

The unified baseline was accepted in PR #73. Stage 2 consolidation was characterized in PR #75, and the first behavior-preserving extraction was accepted in PR #77.

When this document, a roadmap summary, a README sentence, an old review log, or a prospective plan disagree, this baseline and the active linked GitHub Issue control the architecture interpretation. `.codex/WORKFLOW.md` controls execution gates.

## Three independent current-state axes

AQuantAI must not use one phrase such as “current phase” to represent three different facts.

| Axis | Current state | Meaning |
| --- | --- | --- |
| Released software version | `0.2.0` | Published package/application metadata remains unchanged. Merged capability and consolidation slices do not automatically create a new release. |
| Merged capability stage | v0.6D | `main` contains reviewed persistence, Market Cockpit, Industry Alpha Stage 1, and Stage 2 foundations through independent industry/company quality judgments. |
| Runtime and user-visible surfaces | Mixed | The local fixture-backed read-only Dashboard remains available. Database-backed read-only Market Cockpit and Industry Alpha APIs and offline demos are also implemented when PostgreSQL and explicit local data are configured. No single unified end-user workbench UI exists. |

A document may summarize one axis, but it must name the axis explicitly.

## Product boundary

AQuantAI is a local-first, personal-use, research-only and non-advisory workbench. It is not a broker, order-management system, automated-trading system, investment-advice service, multi-user SaaS product, or production deployment platform.

Deterministic calculations and state transitions belong to reviewed application code. An LLM may assist future research workflows only behind an explicit adapter and may not own deterministic calculations, evidence qualification, workflow state, execution, or trading behavior.

## Implemented dependency direction

The accepted domain direction is:

```text
market-data evidence
  -> v0.5 evidence ledger
  -> Stage 1 industry map and beneficiary boundary
  -> v0.6A company research and financial-transmission hypotheses
  -> v0.6B expectations and valuation observations
  -> v0.6C catalyst and risk assessments
  -> v0.6D industry and company quality judgments
```

A downstream record may freeze exact accepted upstream revisions. It may not silently select newer compatible-looking records, infer missing upstream state, or rewrite historical upstream meaning.

The shared v0.6A/v0.6B frozen-boundary mechanics used by v0.6C and v0.6D now belong to the neutral `industry_alpha.stage2_boundary` module. v0.6D no longer imports those private mechanics from the v0.6C command module. Catalyst/risk and quality-judgment semantics remain in their owning domain modules.

The following are not part of the current implementable path:

- v0.6E price judgment;
- timing judgment;
- Watchlist and verification-task runtime behavior;
- Paper Portfolio and simulated trades;
- portfolio analysis or Quant Core integration into product workflow state.

Issue #70 and PR #71 are superseded and closed without merge. No price-judgment implementation exists.

## Capability matrix

| Capability | Merged boundary | Runtime surface | Explicit boundary | Architecture debt |
| --- | --- | --- | --- | --- |
| v0.3 market-data persistence | Complete-snapshot PostgreSQL persistence, ingestion attempts, cutoff-aware reads, canonical series identities, controlled AKShare command | CLI, persistence services, read paths | Manual bounded ingestion; no automatic collection; no production operations | Market-price measurement kind/unit/currency is not yet a standalone canonical evidence contract |
| v0.4A-v0.4E Market Cockpit | Selected-equity breadth/risk, optional benchmark and sector context, liquidity distribution and price-behavior proxies | Read-only API and local page when configured | Descriptive selected-scope context; no official full-market, valuation, regime, signal or recommendation claims | Some historical documents still emphasize only the original Dashboard surface |
| v0.5A evidence ledger | Research cases, evidence, claims, conflicts, immutable revisions and cutoff-aware reads | Read-only Industry Alpha APIs and offline fixture/demo | No scoring, beneficiary mapping, LLM execution or recommendations | Shared evidence qualification and chronology rules remain repeated downstream |
| v0.5B-v0.5C Stage 1 | Industry chain maps, assertions, beneficiary classifications and candidate-pool handoff | Read-only APIs and offline fixture/demo | No company deep dive, valuation, ranking or recommendation | Exact frozen-link patterns expand with each slice |
| v0.6A company research | Company-research identities/revisions and financial-transmission hypotheses | Read-only APIs and offline fixture/demo | No valuation, score, recommendation or trading | Revision allocation, append-only and evidence checks are implemented repeatedly |
| v0.6B expectations/valuation | Expectation and valuation-observation snapshots with optional local-price provenance | Read-only APIs and offline fixture/demo | `observed_value` is generic valuation context; no target/fair value, expected return, good-price or good-timing output | Comparison eligibility and canonical market-price measurement semantics are not defined |
| v0.6C catalyst/risk | Append-only catalyst and risk assessments over exact v0.6A/v0.6B/evidence boundaries | Read-only APIs and offline fixture/demo | Not monitoring, alerts, tasks, signals or recommendations | Base frozen-boundary ownership is consolidated; repository/query/concurrency/ORM repetition remains |
| v0.6D quality judgments | Manual industry/company quality judgments with separate outcome and evidence state | Read-only APIs and offline fixture/demo | Not a formal conclusion, price/timing judgment, score, Watchlist state or recommendation | Private dependency on v0.6C was removed; remaining read and lifecycle infrastructure still needs separate review |
| v0.6E | Superseded planning only | None | Not implemented and not authorized | Requires upstream ownership and further consolidation decisions before reconsideration |
| v0.7+ | Prospective only | None | Not authorized | Must pass Architecture Preflight and Definition of Ready |

## Field and domain ownership

| Information | Authoritative owner | Current rule |
| --- | --- | --- |
| Provider rows, series identity, ingestion status and cutoff | Market-data persistence | Explicit series/run selection; no provider-only fallback or cross-run stitching |
| Canonical market-price value, measurement kind, unit, currency and decimal normalization | Future separately reviewed market-data/evidence contract | Not yet implemented as a complete standalone contract; downstream judgment code must not invent it |
| Evidence grades, claims, support/contradiction/context links and conflicts | v0.5 evidence ledger | Downstream slices freeze exact revisions and links rather than recreate evidence meaning |
| Company-research workflow/conclusion and hypotheses | v0.6A | Downstream records bind exact revisions and expose frozen state |
| Market expectations and valuation observations | v0.6B | `observed_value`, unit and currency retain their recorded context; generic values are not automatically price-comparison eligible |
| Catalyst and risk assessment state | v0.6C | Assessment records are not monitors, alerts or task lifecycles |
| Industry/company quality outcome and evidence state | v0.6D | Separate manual fields; neither automatically generates later price, timing or recommendation state |
| Shared v0.6A/v0.6B frozen-boundary mechanics | Neutral Stage 2 infrastructure | `stage2_boundary.py` owns exact base-boundary loading and visibility mechanics; domain semantics remain local |
| “Good price” and “good timing” | Conceptual future workflow | Not current runtime entities and not authorized for implementation |

A local `daily_price` row linked by v0.6B remains provenance/context. It does not become a canonical price-comparison value merely because a valuation record also stores a numeric string and currency.

## Shared architecture invariants

Future tasks must reference these invariants and add only slice-specific rules.

1. **Local and non-advisory:** personal-use, local-first, research-only; no advice, performance promise, broker, real order or automated trading.
2. **Deterministic ownership:** deterministic calculations, canonicalization, selectors and state transitions stay outside LLM ownership.
3. **No hidden network:** imports, FastAPI startup, tests, CI, fixture demos and ordinary read use perform no external network access.
4. **Explicit selection:** provider names, “latest”, names, free text and popularity are not substitutes for exact IDs, series keys, scopes, dates or revisions.
5. **Exact revision boundaries:** downstream accepted records freeze exact upstream revisions and links, not only stable identities.
6. **Append-only history:** accepted research identities, revisions and frozen links are not updated or deleted through ordinary application paths; corrections append revisions.
7. **Dual visibility:** both information cutoff and actual UTC recorded/imported/completed chronology prevent later information leakage.
8. **Visible uncertainty:** facts, inferences, conflicts, contradictions, missing evidence and uncertainty remain explicit; missing evidence is never silently upgraded.
9. **Atomicity:** identity creation, revision append and frozen links commit in one transaction; any validation or concurrency failure rolls back all rows.
10. **Determinism:** ordering, revision allocation, canonical decimal text and strict JSON are deterministic across supported databases.
11. **Fixture/provider parity:** a fixture success path must use fields and contracts reachable through the reviewed production adapter boundary. Fixture-only enrichment cannot prove production reachability.
12. **Read-only by default:** new mutation APIs, browser editing, notifications, tasks, portfolio state, broker or trading behavior require separate explicit authorization.
13. **Secrets and diagnostics:** credentials and raw connection details never appear in source, fixtures, Issues, PRs, logs or user-facing errors.
14. **Release independence:** merging a capability or consolidation slice does not change the released version without a separate release decision.

## Architecture debt register

### D1. Current-state documentation drift — controlled, monitored

PR #73 introduced the three-axis model and authoritative baseline. Issue #78 synchronizes the record after the first consolidation implementation. Future merges must update status before another development slice begins.

### D2. Repeated Stage 2 structural pattern — partially reduced

v0.6A-v0.6D repeatedly introduce identities, revisions, supersedes links, upstream membership links, claim/evidence links, repositories, query builders, contracts, fixtures and database-specific tests.

PR #77 removed the highest-priority incorrect dependency by extracting a neutral base boundary. It did not generalize schemas or domain semantics. Ordered repository row loading is the next characterization candidate; generic graph loading is not authorized.

### D3. Repeated cross-cutting validation — partially reduced

Exact v0.6A/v0.6B boundary loading, stored-UTC normalization, visibility checks and company-research locking used by v0.6C/v0.6D now have neutral ownership. Revision allocation, integrity translation, append-only mutation rejection, query serialization and fixture rules remain duplicated and require independent review.

### D4. Test-matrix growth

Each downstream frozen boundary multiplies state combinations and cross-database assertions. New slices must separate shared invariant tests from slice-specific semantic tests and avoid restating every historical matrix.

### D5. Fixture-versus-production reachability

Artificial fixture fields can make an otherwise unreachable production path appear valid. A production-realistic offline golden path is required before exhaustive negative tests.

### D6. Missing canonical market-price measurement semantics

`DailyPriceRecord` does not independently expose a reviewed measurement-kind/unit/currency evidence object suitable for arbitrary downstream price comparisons. This must be solved upstream, if needed, before reconsidering price judgment.

### D7. Consolidation cadence — active rule

Feature slices were merged faster than architecture integration. A consolidation review is mandatory after every two domain slices and may be required earlier when duplication or contract ambiguity appears.

## Development gates

### Gate 1: Architecture Preflight

Before creating a feature or consolidation implementation Issue, the architecture reviewer must document:

- user or maintenance problem and why current capability is insufficient;
- domain owner for each material field or mechanism;
- real provider/persistence source for each input where applicable;
- one production-realistic offline golden path;
- important failure path;
- dependency and migration impact;
- conflicts with existing architecture documents;
- smallest viable slice and explicit exclusions.

No implementation Issue is created when these questions remain open.

### Gate 2: Definition of Ready

Task synchronization or implementation requires:

- one unambiguous objective;
- accepted input/output contracts;
- an ownership table;
- a reachable golden path;
- fixture/provider parity evidence when applicable;
- explicit selectors and chronology;
- migration decision;
- bounded scope with no more than one main domain capability and one infrastructure change;
- acceptance tests and stop conditions.

### Gate 3: Planning and implementation separation

Architecture decisions precede a concise Issue. The task file is an executable snapshot, not a place to discover fundamental domain ownership. Application code begins only after a separate planning acceptance is synchronized to GitHub.

### Gate 4: Reset threshold

Reset the plan rather than adding another task-file patch when:

- two rounds of foundational blockers have occurred;
- a production adapter cannot reach the planned success path;
- a material field has no single authoritative owner;
- core semantics rely on free text, provider name, security-code inference or defaults;
- one slice introduces multiple new infrastructure boundaries;
- project-level documents materially disagree about the feature.

Provider reachability or ownership failure can trigger immediate reset without waiting for two rounds.

### Gate 5: Consolidation cadence

After every two domain slices, pause feature expansion and review:

- current-state documentation;
- duplicated models/services/validators;
- schema and frozen-link growth;
- test count, duration and matrix growth;
- API consistency;
- next-stage input reachability.

### Gate 6: Review evidence

Green CI is necessary regression evidence, but it is not architecture acceptance. Review must also establish domain ownership, production reachability, fixture parity, explicit semantics and scope coherence.

## Near-term sequence

Completed:

1. unified architecture baseline accepted in PR #73;
2. Stage 2 consolidation characterized in PR #75;
3. neutral Stage 2 frozen-boundary extraction accepted in PR #77.

Current synchronization:

4. Issue #78 records those merged outcomes and the remaining debt without changing application behavior.

Prospective and separately authorized:

5. characterize shared ordered repository row-loading primitives;
6. consider a minimal implementation only if characterization proves identical SQL, ordering and missing-row semantics;
7. characterize pure query visibility/date/UTC/UUID formatting;
8. decide whether a canonical market-price evidence contract has independent user value;
9. only then consider structured valuation comparison eligibility;
10. re-evaluate whether a separate price-judgment aggregate is necessary; a deterministic read model may be sufficient;
11. do not start v0.7 until required upstream contracts and consolidation reviews are accepted.

No prospective item is authorized by this document alone.
