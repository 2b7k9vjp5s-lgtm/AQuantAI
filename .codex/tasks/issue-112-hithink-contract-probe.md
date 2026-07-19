# Issue #112 - Credential-Safe Hithink Contract Acceptance Probe

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: #112
- Base and required ancestor: `ca2a9fa0ca4daea6b7318a50851272b74c4dc115`
- Branch: `feat/hithink-contract-probe`
- Work type: bounded contract-acceptance probe only
- Released version remains `0.2.0`; merged capability remains v0.6D.
- Migration decision: no migration.

## Objective

Add a secret-safe, no-database-write probe that gathers only sanitized evidence needed to decide whether a future Hithink REST adapter, a separately reviewed market-dump importer, or neither reaches Definition of Ready.

This is not a `DataProvider`, ingestion implementation, persistence path, fallback orchestrator or default-provider change.

## Exact authorized files

1. `.codex/tasks/issue-112-hithink-contract-probe.md`
2. `datasource/hithink/__init__.py`
3. `datasource/hithink/probe.py`
4. `scripts/probe_hithink_contracts.py`
5. `tests/test_hithink_contract_probe.py`
6. `docs/hithink_contract_probe.md`
7. `scripts/README.md`

Do not modify any other path.

## Required implementation

### Safety boundary

- No network access on import, startup, tests, CI or fixture demos.
- Live execution requires `--allow-network`.
- Offline execution requires `--offline-contract`; the modes are mutually exclusive.
- Read `HITHINK_FINANCE_API_KEY` only after live mode is explicitly selected.
- Do not accept a key through CLI arguments.
- Missing key must fail before transport construction or request execution.
- Add no dependency; use the standard library and existing packages only.
- Use a fixed HTTPS Fuyao base URL, a hard timeout and one bounded attempt per capability.
- Inject transport and environment lookup for tests.
- Import no database, persistence, SQLAlchemy or provider-default modules.

### Reviewed live calls

Permit only:

1. `GET /api/meta/tickers/list` with `asset_type=a-share`, bounded `limit`, `offset=0`;
2. `GET /api/a-share/calendar/trading-days`;
3. `GET /api/a-share/prices/historical` for exactly one caller-supplied `.SH`, `.SZ` and `.BJ` representative, a bounded date range, `interval=1d`, `adjust=none`;
4. `GET /dump/market-dumps/daily-k-10d/download-url` to inspect the response contract only.

Do not download the dump file.

Validate transport status and the application envelope separately. HTTP 200 is not sufficient. Require the reviewed success business code before reading `data`; classify known validation, authentication, permission, absence/data-state, rate-limit, timeout and upstream-unavailable codes; fail closed for unknown codes.

### Symbol and field contracts

- Require exactly three unique representatives with exact six-digit `.SH`, `.SZ`, `.BJ` suffixes.
- Reject malformed, duplicate, inferred or missing suffixes before network access.
- Validate exact required fields and primitive types for ticker items, calendar items and unadjusted historical bars.
- Do not normalize into DataFrames or existing persistence contracts in this Issue.

### Sanitized evidence

Output deterministic, sorted JSON containing only:

- endpoint identifier;
- acceptance/block status;
- business code/category;
- sanitized request ID;
- item count;
- required-field/type fingerprint;
- suffix coverage;
- dump HTTPS-link-present boolean;
- local manifest-evidence completeness;
- local account-rights-evidence completeness.

Never output or retain API keys, headers, full URLs, presigned query strings, raw response bodies, stock names, prices, volume/turnover values, account identifiers or free-text rights notes.

Errors must remain safe even when an injected exception or payload contains the API key. Do not include raw exception text from live transports in user-visible output.

### Dump evidence

- Validate that the download response contains an HTTPS URL, then discard it.
- Never print, return, cache or persist the URL.
- Do not fetch or parse Parquet.
- Accept an optional local untracked manifest JSON and validate declared dump ID, version, mode, coverage dates, row/ticker counts, `failed_tickers`, file name and lowercase SHA-256 shape.
- If checksum or schema evidence is absent, report the dump contract as `blocked`; do not invent acceptance.

### Account-rights evidence

Accept an optional local untracked JSON supplied by the account owner. Summarize only presence/completeness for:

- enabled capabilities;
- quotas and QPS;
- local long-term storage;
- caching and transformation;
- local display;
- redistribution/deployment;
- retention/deletion;
- dump reproducibility.

Do not echo free text, account names, IDs or credentials.

### Offline mode

- Use small synthetic contract envelopes authored for this repository, not copied provider datasets.
- Do not read `HITHINK_FINANCE_API_KEY`.
- Do not construct a live transport.
- Do not import or construct database objects.
- Produce the same sanitized report shape as live mode.

## Required tests

Cover at minimum:

1. explicit live/offline mode gating;
2. offline mode performs no network and does not read the key;
3. missing live key fails before transport;
4. key redaction from results, exceptions, CLI-facing errors and reprs;
5. HTTP 200 plus non-success business code is rejected/classified;
6. field/type contract validation for ticker, calendar and historical bars;
7. exact `.SH`, `.SZ`, `.BJ` representatives and pre-network rejection of malformed/duplicate input;
8. dump URL redaction and proof that no download occurs;
9. missing manifest checksum/schema reports `blocked`;
10. rights evidence is summarized without copying free text or identifiers;
11. deterministic sorted output with no raw market rows;
12. no database/persistence path is imported or exercised.

## Validation

Run and report:

- focused probe tests;
- full `python -m pytest -q`;
- `python -m scripts.demo_research_flow`;
- `git diff --check`;
- GitHub Actions on the fixed head.

A live probe is optional and may be run only by the account owner with a locally configured secret. Codex and CI must not request, create, print or use a real key. If no live probe is run, state that explicitly and do not claim live acceptance.

## Locked exclusions

No `DataProvider` implementation, DataFrame normalization, production ingestion, persistence, database engine/session, schema/migration, default-provider change, fallback orchestration, AKShare change, dump download/Parquet parsing, new dependency, environment-template edit, CI secret, provider-derived committed fixture, API key, release/version, v0.6E, v0.7 or PR #38 work.

## Stop gate

Push exactly the seven authorized files to a linked Draft PR. Keep it Draft/Open/unmerged for independent fixed-head review. Return the fixed head SHA, exact file list, validation results and an honest statement about whether a live probe was run.