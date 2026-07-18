# Issue #49 — v0.4C Metadata And Sector Compatibility Audit Fix

## Task identity

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#49 [v0.4C] Sector market data foundation and descriptive rotation context`
- Pull request: `#50 [v0.4C] Add sector market context`
- Branch: `feat/v04c-sector-market-context`
- Required product ancestor: v0.4B squash merge `50147ecd7b796167d52a04e2ecc774010b8956b8`
- Task-sync start: `9eb00d830737f7c4f622b3d9bf295a4ab8de89eb`
- Reviewed implementation head: `6c9969a8d5570f67dbcef660747d9417bf672c79`
- Passing implementation CI: `29643708843`
- Blocking COMMENT review: `4728479274`
- Project version remains `0.2.0`

Read `.codex/WORKFLOW.md`, this task, Issue #49, PR #50, review `4728479274`, `docs/sector_context.md`, the sector provider/persistence/repository/service implementation, and the sector tests before editing.

Keep PR #50 Draft. Do not merge, close Issue #49, release, tag, change version, begin v0.5, or modify PR #38.

## Accepted implementation

Do not redesign or regress the accepted v0.4C foundation:

- separate sector definition and daily persistence in migration `20260718_0004`;
- stable Eastmoney `BK` identifiers and exact selected scope;
- exactly one taxonomy endpoint and one bounded daily-history endpoint with no fallback;
- separate canonical sector series identity and one physical successful snapshot;
- no taxonomy/history stitching across runs or series;
- selected equity snapshot's persisted open-session sequence as the only expected-session source;
- exact latest/5-session/20-session return, SMA20, realized-volatility and drawdown windows;
- bounded missing/invalid/duplicate diagnostics and no filling or shortening;
- deterministic selected-scope cross-section denominators and rankings;
- explicit coverage, session, cutoff and overall alignment;
- nullable effective sector session when no requested code is eligible;
- optional read-only Market Cockpit API/page integration;
- all v0.4A/v0.4B compatibility and no-network behavior.

Only the two audit blockers below are authorized for correction.

## Blocker 1 — fixed provider metadata allowlist

`backend/database/sector_data.py::_request_metadata()` currently accepts any canonical JSON object and rejects only keys matching a sensitive-term blacklist. This permits unknown debug fields, nested raw provider payloads, host/path fields that avoid the blacklist, and future accidental data to be persisted in `IngestionRun.provider_request_metadata`.

Replace blacklist-only acceptance with a fixed, explicit sector metadata contract.

### Allowed top-level fields

Use one named constant for the exact allowed keys required by the reviewed sector provenance contract:

- `taxonomy_endpoint`
- `history_endpoint`
- `classification_system`
- `classification_level`
- `frequency`
- `adjust_type`
- `sector_codes`
- `start_date`
- `end_date`
- `network_mode`
- `timeout_seconds`
- `max_retries`
- `akshare_package_version`
- `definition_contract_version`
- `daily_contract_version`
- `adapter_version`
- `adapter_compatibility_version`
- `collection_timestamp_utc`
- `effective_information_cutoff_date`

Do not add fields merely because a provider could return them. A new public metadata field requires a future reviewed change.

### Validation rules

1. Reject every unknown top-level key with a stable actionable error.
2. Reject dictionaries and lists except the exact flat `sector_codes` list. Do not persist raw responses, debug dumps, request headers, environment data, filesystem paths, or arbitrary nested payloads.
3. Keep the existing sensitive-term rejection as defense in depth, but it is not a substitute for the allowlist.
4. Normalize and validate every allowed value:
   - endpoints, classification, frequency, adjustment, versions and network mode are bounded public identifiers or exact reviewed values;
   - `sector_codes` is the exact sorted unique stable `BK` scope;
   - start/end/effective-cutoff values use `YYYYMMDD`;
   - collection timestamp is timezone-aware UTC and serialized deterministically;
   - timeout is finite and positive;
   - retries is a bounded nonnegative integer;
   - nullable classification level remains explicitly `null`.
5. Cross-check identity-bearing metadata against the canonical request and series:
   - taxonomy/history endpoints;
   - classification system and level;
   - exact sector codes;
   - requested start/end dates;
   - definition/daily contract versions;
   - adapter compatibility version;
   - frequency and unadjusted policy.
6. Contradictory metadata must fail before a succeeded snapshot is committed. Failed provider attempts must also pass the same metadata validation before their audit row is stored.
7. Repository/public provenance must continue exposing only the already reviewed bounded fields.

### Metadata regression tests

Add deterministic tests proving:

- the exact allowed metadata from `sector_request_metadata()` plus collection/effective-cutoff fields persists successfully;
- an unknown scalar field is rejected;
- `raw_response` or another nested dictionary/list payload is rejected;
- a local-path/debug-like field not caught by the old blacklist is still rejected by the allowlist;
- contradictory taxonomy endpoint is rejected;
- contradictory history endpoint is rejected;
- contradictory code scope or date scope is rejected;
- contradictory contract or adapter compatibility version is rejected;
- invalid timestamp/timeout/retry types are rejected;
- failed-attempt metadata follows the same contract;
- rejection writes no sector definition or daily rows and leaves only the established bounded failed-attempt audit behavior where applicable.

Update `docs/sector_context.md` with the exact metadata allowlist and state that unknown/nested provider payloads are never persisted.

## Blocker 2 — sector-specific AKShare compatibility gate

The implementation was inspected and tested against installed AKShare `1.18.64`, but it inherits the generic runtime range `>=1.16.0,<2.0.0` and documents the entire range as reviewed for the new sector endpoints. That broad claim is not supported by the current sector tests or recorded endpoint evidence.

Add a distinct sector endpoint compatibility contract.

### Required behavior

1. Define a sector-specific compatibility version/range for the exact pair:
   - `stock_board_industry_name_em`
   - `stock_board_industry_hist_em`
2. Establish the supported version boundary from official AKShare source/history and deterministic contract tests. Do not guess a historical lower bound.
3. If a broader version family cannot be demonstrated, fail closed to the exact reviewed `1.18.64` version or the narrowest officially justified family containing it.
4. The generic equity/benchmark AKShare runtime gate may remain unchanged; sector collection must additionally pass the sector-specific gate before provider access or engine creation.
5. Use a separately named sector compatibility constant/version. Include it in canonical sector series identity through `adapter_compatibility_version` or an explicit normalized compatibility parameter.
6. Changing the sector endpoint compatibility contract must change the sector series key.
7. Error text must identify that the installed AKShare version is unsupported for the reviewed sector endpoint contract and state the accepted version/range.
8. Offline injected frames/fixtures may continue without live network, but they must provide an explicitly accepted deterministic package version when exercising the AKShare adapter contract.

### Compatibility regression tests

Add tests proving:

- installed/reviewed `1.18.64` passes the sector gate;
- at least one version accepted by the generic `>=1.16.0,<2.0.0` gate but not proven for the sector contract is rejected before taxonomy/history calls and before engine creation;
- malformed, pre-range and `2.x` versions fail closed;
- the accepted provider still sends exact `BK` codes with the reviewed history arguments;
- changing the sector compatibility contract changes canonical series identity;
- equity and benchmark existing version behavior is unchanged.

Update `docs/sector_context.md`, `docs/akshare_ingestion.md`, local usage documentation and PR wording. Do not describe a version as reviewed or supported unless the sector-specific gate accepts it and the evidence is recorded.

## Expected files

Keep the revision bounded. Expected changes are limited to files such as:

- `backend/database/sector_data.py`
- `backend/database/series.py` only if required for the explicit compatibility identity
- `datasource/akshare/provider.py`
- `scripts/ingest_akshare_sector_data.py`
- `docs/sector_context.md`
- `docs/akshare_ingestion.md`
- `docs/local_usage.md`
- `tests/test_sector_data.py`
- `tests/test_sector_provider.py`
- narrowly related tests

Do not add a migration unless a genuine persistence-schema requirement is discovered and separately reported. Do not modify calculation formulas, alignment semantics, frontend behavior, dependencies, Docker/Compose, CI, version files, or unrelated modules.

## Required validation

Run and report exact results for:

1. `python -m pytest -q`
2. focused sector metadata, provider compatibility, persistence and repository tests
3. focused sector calculation/alignment/API/page regression tests
4. PostgreSQL sector migration/persistence focus
5. no-network import/startup/page/live-cutoff/dry-run focus
6. clean Alembic `base -> head`
7. `20260718_0004 -> 20260718_0003 -> 20260718_0004`
8. `python -m alembic check`
9. `python -m scripts.demo_research_flow`
10. persisted equity current/historical demo
11. benchmark current/historical demo
12. sector current/historical demo
13. offline sector dry-run and repeated idempotent persistence
14. `python -m compileall -q backend datasource market_cockpit scripts`
15. `git diff --check`
16. GitHub Actions for the final implementation Head

All automated validation must remain offline. Do not make a live AKShare call for this correction.

## GitHub handoff

After implementation:

1. Update PR #50 body with the new implementation Head, exact changed files, final sector compatibility contract, metadata allowlist, tests and validation results.
2. Add a concise PR #50 comment referencing review `4728479274` and explaining how each blocker was closed.
3. Add the same bounded record to Issue #49.
4. Keep PR #50 Draft.
5. Stop for ChatGPT re-review.

Do not mark Ready, merge, close Issue #49, release/tag, change version, start v0.5, or modify PR #38.
