# Review Log

GitHub Issues and pull-request reviews are authoritative. `docs/architecture_baseline.md` owns the current architecture interpretation.

## Current status

- Review date: 2026-07-20
- Released software version: `0.2.0`
- Merged capability stage: v0.6D
- Provider-status synchronization base: `ca2a9fa0ca4daea6b7318a50851272b74c4dc115`
- Accepted application/consolidation implementation baseline: `7705b7caf210d606473db6f24c5fadfad4918646`
- Runtime surfaces: local fixture-backed read-only Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured
- Most recent accepted architecture characterization: Issue #124 / PR #125
- Active application or consolidation implementation authorization: none
- New migration authorization: none

Docs-only commits may advance `main` without changing release, capability or runtime state.

## Accepted architecture decisions

- Issue #70 / PR #71 for v0.6E price judgment were closed without merge.
- Issue #72 / PR #73 established the unified baseline and delivery gates.
- Issue #74 / PR #75 characterized Stage 2 infrastructure.
- Issue #76 / PR #77 extracted the neutral frozen boundary.
- Issues #80/#82 and PRs #81/#83 characterized and implemented ordered scalar row loading.
- Issues #86/#88 and PRs #87/#89 characterized and implemented v0.6A-v0.6C pure query values.
- Issue #92 / PR #93 kept evidence read serializers domain-local because no neutral claim projection reached Definition of Ready.
- Issues #96/#98 and PRs #97/#99 characterized and implemented neutral command integrity translation.
- Issues #102/#104 and PRs #103/#105 characterized and implemented the neutral process-local revision-lock registry.
- Issue #108 / PR #109 characterized Hithink as the preferred future A-share provider candidate while retaining AKShare as an explicit separate alternative.
- Issue #116 / PR #117 characterized Stage 2 ORM lifecycle behavior.
- Issue #118 / PR #119 committed and accepted the ORM lifecycle compatibility matrix.
- Issue #120 / PR #121 implemented the one accepted neutral append-only mutation-scan helper.
- Issue #124 / PR #125 characterized canonical market-price evidence, accepted its independent value and preferred future ownership, and found no production implementation ready.

## Canonical market-price characterization acceptance

PR #125 was accepted at fixed head `969815964fc150c224cf862ad47556569606332c` and merged as `8955e419c79f592ee9edcccdb446ebbe249de1dd`.

Independent review confirmed:

- the base-to-head diff contained exactly the two Issue #124 documentation files;
- provider-normalized rows, persisted `DailyPriceRecord` rows, latest-series reads, canonical evidence, v0.6B valuation observations, comparison eligibility and later judgment state remain distinct boundaries;
- a standalone canonical market-price evidence contract has independent value for point-in-time inspection, audit and downstream provenance;
- a separately reviewed market-data/evidence layer is the preferred future owner, not Stage 2 valuation or a future price-judgment domain;
- a linked daily-price row, generic `observed_value` or optional `daily_price_id` is context only and is not automatically canonical or comparison eligible;
- comparison eligibility remains a later separate deterministic contract;
- provider price semantics, unit/currency source, historical freezing, price-specific decimal limits, exact selector, information/UTC visibility, missing-state vocabulary, migration and rollback remain unresolved;
- no module, table, migration, API or production implementation reaches Definition of Ready;
- Actions `29728198982`, job `88306125767`, completed PostgreSQL setup, the full test step, fixture demo and cleanup successfully. Exact counts were not exposed and are not guessed.

No code, test, fixture, dependency, provider behavior, schema/migration, API/runtime, release/version, v0.6E, v0.7 or PR #38 change occurred.

## ORM lifecycle compatibility acceptance

PR #119 was accepted at fixed head `905fce200a6d3d47519a0512ef52fb59b6de813b` and merged as `e0644de3ea7c3afaeba8da483fef800c2c90f197`.

Independent review confirmed:

- the matrix fixes four global `Session.before_flush` listeners, tuple sizes 11/10/14/18 and exactly 53 Stage 2 tables;
- ordinary imports preserve listener, tuple, mapped-class, table and shared metadata identity;
- one dirty-but-unmodified flush invokes each Stage 2 listener exactly once after repeated ordinary imports;
- SQLite and custom-`Session` tests preserve pending/no-op, exact update/delete errors and rollback behavior;
- PostgreSQL 16 verifies representative v0.6A-v0.6D update/delete rollback behavior;
- dynamic v0.6C/v0.6D factories and generated globals remain domain-local;
- Actions `29715627495` completed the full test step, PostgreSQL service, fixture demo and cleanup successfully. Exact counts are not guessed.

## Append-only helper implementation acceptance

PR #121 was accepted at fixed head `3d41a3f238a994aba172bd824d704d0fc11091cc` and merged as `7705b7caf210d606473db6f24c5fadfad4918646`.

Independent review confirmed:

- `industry_alpha.orm_append_only.reject_append_only_mutation(session, model_types)` owns only delete-before-dirty scanning, `isinstance`, material-dirty detection with `include_collections=False` and the exact existing immutable error messages;
- all four event decorators, listener names/signatures and identities, registration modules and model tuples remain domain-local;
- all mapped classes, dynamic factories and generated globals remain unchanged and domain-local;
- explicit reload support, listener or tuple relocation, database triggers and Core-DML interception were not added;
- Actions `29716094740`, job `88269576578`, completed PostgreSQL 16, the full test step, fixture demo and cleanup successfully. Exact counts are not guessed;
- no migration, schema, dependency, API/runtime, provider, release/version, v0.6E, v0.7 or PR #38 change occurred.

## Command integrity implementation acceptance

PR #99 was accepted at fixed head `b0dc58b2adb27e9a6ec6f1a2dce3699bd2bab9ff` and squash-merged as `a2688b6e244743ef5e3bdcaedfc6c6717d7a7d8c`.

Independent review confirmed:

- the base-to-head diff contained exactly the seven Issue #98 files;
- `stage2_integrity.translate_integrity(message)` catches only SQLAlchemy `IntegrityError`;
- it raises `EvidenceLedgerConflictError` with the exact caller message and chains from the original exception;
- non-integrity exceptions propagate as the same object;
- all four command modules preserve outer-translator/inner-`session_factory.begin()` nesting;
- conflict messages, transaction-owned rollback, process-local locks, database row locks, revision allocation and supersession are unchanged;
- Actions `29687524781`, full tests and the fixture demo succeeded;
- PostgreSQL-focused tests were honestly reported as skipped where the required database URL was unavailable.

No migration, API, schema, fixture, dependency, release, version, v0.6E, v0.7 or PR #38 change occurred.

## Revision-lock implementation acceptance

PR #105 was accepted at fixed head `d1266de8369906af90f481d3727f08fb5552e8fa` and merged as `cf3ad09c9f9fb39dbaada7342435a8c7b2853b1a`.

Independent review confirmed:

- `industry_alpha.stage2_revision_locks` owns only one guarded process-local `(kind, UUID) -> RLock` registry;
- all eight labels (`research`, `hypothesis`, `expectation`, `valuation`, `catalyst`, `risk`, `industry`, `company`) are unchanged;
- lock -> integrity translator -> transaction nesting is unchanged;
- same-key identity, different-key isolation, reentrancy and same-key thread exclusion are covered directly;
- row locks, latest-revision reads, revision-number allocation, supersession, cleanup/eviction and retry remain command-local;
- no cross-process or cross-host guarantee was added, and SQLite/PostgreSQL concurrency limitations remain unchanged;
- Actions `29688711474`, full tests and the fixture demo succeeded.

No migration, runtime-surface, API, schema, release, version, v0.6E, v0.7 or PR #38 change occurred.

## Hithink provider characterization acceptance

PR #109 merged as `375a8d15b8a4f7ca80fe843fcfd93bccdeaa2d9a` and changed documentation only.

The accepted direction is:

- Hithink is the preferred future A-share provider candidate, not an active default or implemented provider;
- AKShare remains an explicit provider-specific alternative, with existing runs and series preserved;
- one ingestion run and canonical series contain exactly one provider;
- silent fallback, provider relabeling, row-level provider mixing and hidden cross-provider stitching are prohibited;
- canonical ingestion may use reviewed REST or a separately reviewed market-dump importer;
- MCP and LLM-mediated calls are not canonical ingestion;
- no production provider implementation has reached Definition of Ready.

PR #109 remains the accepted future characterization; it is not rolled back. Hithink is deferred and is neither implemented nor the active default.

## Hithink probe review and deferral

Issue #112 and Draft PR #113 produced a seven-file credential-safe contract probe at reviewed fixed head `b09fcd8e68f4d280407b483a7d114aa0b0e8a015`.

Independent technical review confirmed:

- the base-to-head diff contained exactly the seven authorized files;
- explicit offline/live gating, delayed local-environment key access, injected transport and sanitized deterministic JSON were implemented;
- the probe performed no database writes or dump download and changed no provider default;
- focused and full tests, the fixture demo and Actions `29691380530` succeeded;
- no live probe ran, no API key was requested or used, and no live contract, permission or data-use acceptance exists.

The account owner then deferred Hithink integration. Issue #112 closed as `not planned` and PR #113 closed without merge. Consequently no Hithink code, dependency, runtime/default-provider change, database/schema change or migration reached `main`.

Hithink remains a future candidate only and requires new Architecture Preflight plus explicit authorization before reconsideration. AKShare remains the implemented controlled provider path, and provider-specific history remains immutable and readable.

## Current review conclusion

Neutral ownership exists for:

- shared Stage 2 frozen-boundary mechanics;
- ordered scalar repository row loading;
- v0.6A-v0.6C pure query-value mechanics;
- SQLAlchemy integrity-error translation;
- the process-local keyed revision-lock registry;
- the Stage 2 append-only ORM mutation scan.

Evidence read serialization intentionally remains domain-local. Command modules continue to own exact conflict text, transaction boundaries, row locks, latest-revision reads, revision-number allocation, supersession, cleanup/eviction and retry. ORM event decorators, listener identities, model tuples, dynamic factories and generated globals remain domain-local.

Canonical market-price evidence now has an accepted independent-value and preferred-ownership direction, but no implementation DoR. Existing provider rows, persisted daily-price rows, selected DataFrame reads and v0.6B valuation observations remain source/context boundaries. The next independent gate is credential-free provider measurement-semantics and deterministic-fixture characterization.

## Locked exclusions

- no evidence serializer extraction or projection DTOs without a re-evaluation trigger and new preflight;
- no row-lock, latest-revision, revision-allocation, supersession, cleanup/eviction or retry refactor without accepted characterization;
- no listener/decorator/tuple relocation, dynamic model-factory consolidation, explicit reload support, database trigger or Core-DML interception;
- no canonical market-price record, resolver, repository, API or comparison implementation without a later accepted DoR;
- no application/provider behavior change or migration;
- no provider implementation, live request, secret, dependency, ingestion script, fixture or default-provider change;
- no reopening of Hithink integration without new Architecture Preflight and explicit authorization;
- no v0.6E price or timing judgment;
- no v0.7 Watchlist or verification-task behavior;
- no portfolio, broker, order, recommendation or automated trading behavior;
- no release/tag/version change;
- no modification of PR #38.

## Next development gate

The next gate is a separately authorized credential-free characterization of provider price semantics and a deterministic offline fixture matrix. It may determine whether implemented provider contracts can prove exact instrument market identity, `daily_close` meaning, unit/currency, unadjusted-versus-adjusted eligibility, exact provider/series/run/row selection, information-cutoff plus imported/completed UTC visibility, price-specific decimal limits and the minimum provenance required for historical stability.

That characterization must not change provider code, make a live request, create a schema or migration, implement canonical evidence or comparison eligibility, or start v0.6E or v0.7. No application implementation command is active after this synchronization.
