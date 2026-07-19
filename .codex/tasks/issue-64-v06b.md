# Issue #64 — v0.6B Focused Revision

## State

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#64`
- Branch: `feat/v06b-expectations-valuation`
- Draft PR: `#65`
- Required base: `c94c5ecbac66e43c2c369f36ba64c9b7a13655b6`
- Reviewed implementation Head: `0dea8098dedc718d55969fab956d804c5287f0f8`
- Blocking COMMENT review: `4729846016`
- Implementation CI: `29671888552` — success
- Version remains `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #64, PR #65 and review `4729846016` before editing.

Keep PR #65 Draft/Open/unmerged and Issue #64 Open. Do not merge, release/tag, change version, begin v0.6C or modify PR #38.

## Objective

Revise only the three blockers identified in review `4729846016`. Preserve the accepted v0.6B domain, migration `20260719_0009`, routes and exclusions. Do not add a migration or broaden functionality.

## Blocker 1 — Exact price provenance chronology and payload

Fix the exact local `daily_price` provenance boundary:

- reject a successful ingestion run when `completed_at` is missing or earlier than `imported_at`;
- keep valuation `recorded_at_utc` no earlier than both valid ingestion timestamps;
- correct the offline fixture so import precedes completion;
- expose deterministic `imported_at_utc` and `completed_at_utc` in `price_reference` together with the existing row/run/source/code/date/adjust/close/series/cutoff fields;
- keep exact-ID selection; do not add implicit latest/provider-only lookup;
- validation failure must rollback the valuation identity, revision and all link rows.

Add regressions for:

- impossible `completed_at < imported_at` rejected with a reviewed domain error and unchanged row counts;
- valid provenance visible in both detail and list latest-revision payloads;
- earlier cutoff continues to hide later valuation revisions/references.

## Blocker 2 — Complete deterministic fixture and non-leakage matrix

Extend the existing no-network fixture without adding a new domain:

- retain the supported expectation with A/B/C evidence;
- add one draft or disputed expectation with explicit missing evidence or visible contradiction;
- retain the observed-value valuation with exact local price provenance;
- add one valuation snapshot with `valuation_method="missing_data"`, no observed value and explicit `尚未获得可靠公开证据`-style reason;
- append later Stage 2 research/hypothesis, claim-evidence and price/run records after an earlier v0.6B snapshot boundary;
- prove current views can expose only newly created later revisions when explicitly bound, while the earlier accepted expectation/valuation snapshot remains frozen and earlier `as_of_cutoff` views do not leak later research, evidence or price provenance.

Return stable fixture IDs needed by tests. Keep all data deterministic and offline.

Add focused query/API tests for:

- supported, draft/disputed and missing-data records;
- conflicts and missing-evidence payloads;
- current versus earlier-cutoff behavior;
- later research/evidence/price additions not rewriting existing frozen snapshots;
- deterministic ordering and strict JSON.

## Blocker 3 — Bounded decimal and coherent missing-data state

Harden valuation input validation before any database write:

- accept only `str`, `Decimal` or `None` as already designed;
- reject NaN, positive/negative Infinity and invalid decimal text;
- canonicalize deterministically without binary-float input;
- reject a canonical observed value that cannot fit the reviewed `String(64)` persistence boundary; raise `EvidenceLedgerValidationError`, not a dialect-specific database exception;
- `valuation_method="missing_data"` must require `observed_value is None` and a nonblank explicit `missing_data_reason`;
- every other valuation method must require an observed value and must reject `missing_data_reason`;
- preserve optional unit/currency and existing no-target-price boundary;
- all failures must leave all v0.6B table counts unchanged.

Add SQLite and PostgreSQL regressions for:

- huge exponent / over-64-character canonical value;
- NaN and both infinities;
- `missing_data` plus observed value;
- `missing_data` without a reason;
- non-missing method without observed value;
- non-missing method with a missing-data reason;
- valid bounded decimal canonicalization.

## Allowed changes

Limit implementation changes to the existing v0.6B command, query, fixture, contracts/docs and focused tests as needed. Migration `20260719_0009` should remain unchanged unless a discovered schema defect makes that impossible; do not create `0010`.

Do not change API route paths, dependencies, Docker/Compose, CI, launchers, version, release metadata or unrelated stages.

## Validation

Run and report exact results for:

- focused SQLite/domain/API tests;
- focused PostgreSQL v0.6B tests;
- full offline suite;
- full PostgreSQL suite when available;
- clean Alembic `base -> head`;
- `20260719_0009 -> 20260719_0008 -> 20260719_0009`;
- `python -m alembic check`;
- all offline demos including `python -m scripts.demo_stage2_expectations_valuation`;
- explicit no-network coverage;
- `python -m compileall -q backend industry_alpha scripts tests`;
- `git diff --check`.

## Delivery

1. Implement only these focused fixes.
2. Update PR #65 and Issue #64 with the new Head, exact changed files and exact validation results.
3. Keep PR #65 Draft and Issue #64 Open.
4. Stop for ChatGPT re-review. Do not merge, begin v0.6C, release/tag, change version or modify PR #38.
