# Hithink Primary A-Share Provider Characterization

## Status

Issue #108 characterizes the official Hithink/Fuyao financial-data service as AQuantAI's preferred future A-share provider candidate from `main` commit `586fd3e82460aead32537916394c9624b4e6eedd`.

This is Architecture Preflight and documentation only. It performs no live request, requires no API key, changes no provider or runtime behavior, adds no dependency and authorizes no migration. Released version remains `0.2.0`; merged capability stage remains v0.6D.

## Decision summary

The accepted direction is:

- Hithink is the preferred future provider candidate for reviewed A-share market-data collection;
- AKShare remains an explicit alternative during migration, validation and coverage gaps;
- existing AKShare ingestion runs and canonical series remain immutable and readable;
- one ingestion run and one canonical series contain data from exactly one provider;
- fallback is an explicit orchestration decision that creates a separate provider-specific series;
- row-level provider mixing, silent fallback and provider-name rewriting are prohibited;
- canonical ingestion may use reviewed REST endpoints or reviewed market-dump files, never MCP or LLM-mediated tool calls;
- no implementation reaches Definition of Ready until account capabilities, exact response contracts and data-use rights are confirmed.

This characterization supersedes immediate sequencing into ORM lifecycle review. ORM lifecycle remains deferred and unchanged; the provider decision is a more fundamental upstream data-contract gate.

## Existing AQuantAI provider boundary

`datasource.base.DataProvider` defines stable normalized DataFrame contracts for:

### Stock identity

- `stock_code`
- `stock_name`
- `exchange`
- `industry`
- `listing_date`
- `status`
- `source`

### Daily price

- `trade_date`
- `stock_code`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount`
- `adjust_type`
- `source`

### Trade calendar

- `trade_date`
- `is_open`
- `source`

The current AKShare adapter sits behind this boundary. Unit tests use injected clients or fixtures; imports, startup, tests, CI and the fixture demo do not perform hidden provider network access.

## Existing ingestion protocol that must remain authoritative

The controlled v0.3 market-data path already provides the correct provider-neutral persistence foundation:

1. the caller selects one provider and an exact requested scope;
2. provider rows are normalized into the three reviewed contracts;
3. a canonical `series_key` includes provider identity, contract/bundle identity, exact stock scope, requested date range, adjustment policy, complete/exact semantics and compatibility parameters;
4. ingestion attempts are immutable physical audit records;
5. successful complete snapshots reconcile the exact requested scope and trade calendar;
6. identity, rows, provenance and completion state commit or roll back together;
7. reads require an explicit compatible series or validated selector and fail closed on provider-only ambiguity;
8. ordinary imports, application startup, CI and local fixture demos remain offline.

Hithink must adapt to these rules. The rules must not be weakened to resemble a provider's convenience API.

## Official Hithink surfaces reviewed

The official service exposes several access styles with different architectural uses:

| Surface | Intended AQuantAI use | Decision |
| --- | --- | --- |
| REST API | bounded metadata, calendar or symbol/date queries | eligible after exact contract acceptance |
| Market dumps | bulk historical and rolling incremental ingestion | promising but requires a separate reviewed importer |
| Python SDK / CLI | developer convenience around the same external service | not a canonical persistence boundary by itself |
| MCP / Agent Skill | interactive research and exploratory queries | prohibited for canonical ingestion |
| Local DuckDB tooling | optional inspection of downloaded files | not automatically an AQuantAI storage contract |

The service requires an account API key for data access. A future implementation must read it only from a secure environment or credential store, preferably `HITHINK_FINANCE_API_KEY`. Secrets must never appear in source, fixtures, Issues, PRs, logs, error messages or committed environment files.

## Contract mapping

### Unadjusted daily OHLCV

The public market-dump contract is the strongest fit for the current `daily_price` table. It exposes unadjusted A-share daily bars with a natural key equivalent to `(thscode, date_ms)` and fields for OHLC, volume, turnover, currency, interval and adjustment state.

Proposed deterministic mapping:

| Hithink field | AQuantAI field | Rule |
| --- | --- | --- |
| `thscode` | `stock_code`, `exchange` | parse exact suffix; never infer from name |
| `date_ms` | `trade_date` | interpret under the documented Asia/Shanghai date convention and store the exact local trading date |
| `open` | `open` | decimal-preserving normalization |
| `high` | `high` | decimal-preserving normalization |
| `low` | `low` | decimal-preserving normalization |
| `close` | `close` | decimal-preserving normalization |
| `volume` | `volume` | preserve documented share unit |
| `turnover` | `amount` | preserve documented currency amount |
| `adjusted = none` | `adjust_type = ""` | first slice accepts unadjusted data only |
| provider identity | `source` | fixed reviewed provider identifier; not caller free text |

The first implementation must not derive qfq/hfq values from corporate actions or silently treat adjusted values as unadjusted. Adjusted-price policy requires a separate contract decision.

### Symbol identity

The public service exposes symbol metadata/catalog capabilities, but the exact ability to populate every existing `stock_basic` field and to reconstruct historical universes has not yet been accepted.

Minimum deterministic symbol rule:

- `<six digits>.SH` maps to the exact six-digit code and exchange `SH`;
- `<six digits>.SZ` maps to the exact six-digit code and exchange `SZ`;
- `<six digits>.BJ` maps to the exact six-digit code and exchange `BJ`;
- unknown, missing or malformed suffixes fail validation;
- no company-name, code-prefix, free-text or current-database inference is allowed;
- provider-specific symbol text remains request provenance even after normalization.

No claim is made that a current symbol catalog reconstructs historical listing membership, status, name or industry as of an arbitrary cutoff. A future adapter must not fill missing `industry`, `listing_date` or `status` with invented semantics merely to satisfy columns.

### Trade calendar

The official service exposes an A-share trading-calendar capability. It appears suitable for bounded calendar collection, but the exact available history window, exchange distinctions, update policy and revision behavior must be confirmed before implementation.

The adapter may map an explicitly returned open trading date to `is_open = True`. It must not infer closed dates from missing response rows unless the accepted endpoint contract explicitly defines a complete date interval.

### Corporate actions

Market dumps expose raw dividend, bonus-share and rights-issue fields with an event key equivalent to `(thscode, ex_date_ms)`. These records are useful for future adjustment and evidence work but do not fit the current three normalized contracts without losing event semantics.

Therefore raw corporate actions are not part of the first implementation slice and must not be collapsed into `daily_price.adjust_type` or one opaque adjustment factor. They require a separate schema and point-in-time characterization.

### Financials, indices and Hithink specialty data

Financial statements, current index constituents, Hithink concept/industry indices, limit-up lists, hot lists, anomalies and similar datasets are outside the first provider slice.

They raise independent concerns about:

- announcement and availability timestamps;
- provider-side revisions and restatements;
- historical constituent membership;
- classification effective dates;
- evidence ownership and cutoff semantics;
- whether the data is descriptive context or persisted domain state.

They must not be added opportunistically while implementing the core market-data provider.

## REST response and error policy

The official API uses an application envelope containing fields such as `code`, `message`, `request_id` and `data`. Business errors may still arrive with HTTP status 200.

A future adapter must therefore:

1. validate transport success;
2. decode the response envelope;
3. require the documented success business code before reading `data`;
4. preserve `request_id` and non-secret endpoint/contract provenance in the ingestion attempt;
5. emit sanitized errors without the API key or raw connection details.

Initial retry classification for later implementation review:

| Error family | Default handling |
| --- | --- |
| malformed request / validation (`100x`) | fail without retry |
| authentication / permission (`200x`) | fail without automatic retry |
| symbol or data-state errors (`300x`) | fail or record explicit provider-data absence; no blind retry |
| rate limit (`4001`) | bounded backoff only |
| upstream timeout/unavailable (`5002`, `5003`) | bounded finite retry only |
| unknown business code | fail closed |

Exact limits, jitter, total elapsed time and retry metadata require a separate implementation contract. Existing no-infinite-retry and hard-timeout principles remain mandatory.

## Market-dump ingestion requirements

The public dump model offers approximately ten years of unadjusted A-share daily history, a rolling recent-period increment and corporate-action files through short-lived download URLs. The dump path is operationally different from the existing per-symbol AKShare CLI and should be reviewed separately.

A later dump importer must:

- request or refresh a short-lived URL when needed;
- never persist the presigned URL;
- persist stable manifest identifiers and non-secret provenance;
- validate manifest version, mode, coverage, start/end dates and adjustment state;
- verify SHA-256 before parsing;
- verify expected row count and ticker count;
- reject unexpected schemas or types;
- enforce uniqueness of `(thscode, date_ms)` for daily bars;
- record and reject or explicitly quarantine non-empty `failed_tickers` according to complete-snapshot policy;
- map all rows through the same normalized validation used by bounded collection;
- avoid cross-file or cross-provider stitching that would make one run appear complete when it is not;
- keep download, validation and database commit boundaries auditable.

Parquet ingestion may require a new parsing dependency such as PyArrow. Dependency selection, file-size limits, streaming behavior and temporary-file security make the dump importer a separate implementation Issue from a small REST adapter.

## Provider coexistence options

### Option A: replace AKShare immediately

Rejected.

Immediate replacement would discard a reviewed fallback, complicate verification of provider differences and risk making existing tooling unreadable or misleading. Existing AKShare series are immutable evidence and must remain selectable by their original identity.

### Option B: silently fall back or mix rows

Rejected.

Examples of prohibited behavior:

- use Hithink for most symbols and AKShare for missing symbols inside one run;
- fill missing Hithink dates with AKShare rows while retaining one series key;
- relabel AKShare rows as Hithink after normalization;
- choose a fallback merely because one provider returned an empty frame;
- stitch separate provider snapshots into one apparent complete snapshot.

Such behavior destroys provenance and invalidates exact series identity.

### Option C: preferred provider plus explicit provider-specific alternatives

Accepted.

A future orchestration layer may choose Hithink first and may allow a caller to explicitly run AKShare separately. Each choice creates a distinct provider-specific request, ingestion attempt and series key. Comparison or promotion between series is a later reviewed decision; persistence never hides the distinction.

## Point-in-time limitations

Public API documentation alone does not establish every historical availability guarantee AQuantAI requires.

The following remain unresolved:

- whether symbol metadata can reconstruct the exact historical universe at an arbitrary cutoff;
- whether delisting, name, board and status changes have effective-from/effective-to history;
- whether trade-calendar corrections can occur and how they are versioned;
- whether index constituent APIs expose historical effective periods rather than current membership only;
- which timestamp on financial data represents public availability rather than report period or provider update time;
- how restatements and corrections are exposed;
- whether a market dump is reproducible by stable version after its short-lived URL expires.

Until resolved, the provider must not be used to make historical-universe, historical-index-membership or financial-availability claims.

## Authorization, rights and operating gates

The official repository's software license does not by itself establish the rights for all API-returned data. Before production implementation reaches Definition of Ready, the account owner must confirm:

- enabled API capabilities and dataset permissions;
- request and download quotas;
- QPS and burst policy;
- expected availability or SLA, if any;
- permission for local long-term storage;
- permission to cache and transform data;
- permission to display derived or raw values through AQuantAI's local APIs and Dashboard;
- redistribution or deployment limits;
- retention and deletion requirements;
- whether dump versions remain reproducible and auditable.

No key should be pasted into chat or repository artifacts. A later approved contract probe should read a user-configured local secret and return only sanitized schema, capability and validation evidence.

## Implementation slicing assessment

### Candidate 1: bounded REST adapter

Potential scope:

- a new provider module behind the existing `DataProvider` interface;
- exact symbol normalization;
- unadjusted daily OHLCV;
- bounded trade calendar;
- mocked/offline contract fixtures;
- no provider fallback inside the adapter;
- no database migration and no automatic network path.

This candidate may remain source-only, but it does **not** yet reach Definition of Ready. It is blocked by exact endpoint/field acceptance, symbol metadata completeness, account capability confirmation and data-use rights.

### Candidate 2: market-dump importer

Potential scope:

- manifest client;
- secure short-lived download handling;
- checksum/schema/count/uniqueness validation;
- Parquet parsing;
- complete-snapshot integration;
- rolling increment strategy.

This candidate is separate from Candidate 1. It may add a dependency and substantially different ingestion mechanics, so it requires its own Architecture Preflight and Issue after the dump contract is validated.

### Candidate 3: corporate actions and adjusted prices

Not ready. Raw event ownership, schema, correction policy, effective dates and deterministic adjustment rules require a separate design.

## Definition of Ready conclusion

The strategic provider choice is accepted: Hithink is the preferred future A-share provider candidate, with AKShare retained as an explicit provider-specific alternative.

No production implementation Issue is authorized yet.

The next permissible gate is a narrowly scoped **Hithink contract acceptance probe** that:

1. uses a user-configured local `HITHINK_FINANCE_API_KEY` without exposing it;
2. performs no database writes and changes no default provider;
3. verifies enabled capabilities, representative response envelopes and exact field types;
4. validates `.SH`, `.SZ` and `.BJ` symbol handling;
5. verifies daily-bar, symbol-catalog and trade-calendar coverage;
6. verifies one representative market-dump manifest, checksum and schema without committing market data;
7. records sanitized QPS/permission/data-use evidence supplied by the account owner;
8. produces deterministic offline fixtures only if provider terms permit their storage in the repository.

Only after that evidence is independently reviewed may a separate implementation Issue decide whether Candidate 1, Candidate 2 or neither reaches Definition of Ready.

## Locked exclusions

This characterization authorizes no provider code, API key, live request, dependency, environment-template change, database/schema/migration change, ingestion script, fixture, test, CI, runtime, release/version, v0.6E, v0.7 or PR #38 change.