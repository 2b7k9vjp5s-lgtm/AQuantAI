# Controlled THS Data Refresh MVP — Account Capability Closure

## 1. Decision status

- Governing Issue: #219.
- Product Roadmap: #137.
- Accepted Provider architecture: Issue #190 / PR #191.
- Exact required base: `2e1f8000fe1e431142d07be718729962f65bb2cd`.
- Risk tier: **Strict Architecture Preflight**.
- Release remains `0.2.0`.
- Architecture/task documentation only.

### Current implementation-gate result

`blocked_pending_account_facts`

The generic THS Provider architecture is accepted, but the repository still has no reviewed secret-free account capability manifest for the user's actual account. This preflight does not guess entitlements, hostnames, endpoints, rate limits, retention rights, source identities, chronology or revision behavior.

Architecture completion may fix the contract and later implementation boundary while the production gate remains blocked.

## 2. Why this is the next roadmap step

Personal Research Workbench UI Phase 2B is merged. The next planned product capability is controlled Provider refresh, before:

1. Daily Research Radar;
2. Follow/Track and reminders;
3. Research Portfolio;
4. broader settings or automation.

Controlled refresh must establish trustworthy source acquisition before later monitoring can claim that a company, price, financial statement, taxonomy or market-attention observation changed.

This phase is therefore source-contract closure, not a radar, alert or recommendation feature.

## 3. Product question

The preflight answers:

> Which exact non-secret capabilities are enabled for the user's THS account, and what is the smallest Provider-foundation implementation that can preserve one bounded response with exact authorization, immutable raw bytes, deterministic identity candidates and no automatic downstream promotion?

It does not answer:

- what the latest market data is;
- which stock is attractive;
- whether a hot-list entry is an investment opportunity;
- whether Provider data is official disclosure evidence;
- whether Provider prices should replace Canonical Price;
- whether a Daily Radar or alert should be created.

## 4. Existing decisions retained without change

The following accepted PR #191 decisions remain authoritative:

- source: official account-authorized 同花顺 / HiThink Financial Data API;
- source key: `ths-account-structured-provider-v1`;
- use: personal, local, non-commercial research;
- production transport candidate: documented REST only;
- adapter family: `ths_structured_provider`;
- explicit user-initiated bounded operations;
- network disabled by default;
- immutable database-owned L0 raw bytes;
- source-specific persistence rather than a generic multi-provider framework;
- Provider symbol mapping is a candidate workflow, not accepted identity;
- THS observations do not automatically replace Canonical Price, official evidence, normalized financial inputs, beneficiary state or Investment Candidate state;
- no browser replay, Cookie/CAS ticket, reverse-engineered signature, undocumented endpoint or automatic fallback.

This preflight narrows the first implementation boundary. It does not reopen the accepted source portfolio or domain ownership.

## 5. Account capability manifest contract

The owner-completable template is:

`docs/ths_account_capability_manifest_template.md`

### 5.1 Manifest identity

A completed manifest must freeze:

- manifest contract key: `aquantai.ths-account-capability-manifest.v1`;
- Provider/source key;
- evidence review date;
- exact enabled product and capability labels;
- contract/evidence package fingerprint;
- credential profile key label, never credential material;
- one record per exact capability;
- deterministic readiness result;
- owner review state and date.

### 5.2 Allowed fact states

Every required fact uses exactly one of:

- `confirmed`;
- `unsupported`;
- `not_entitled`;
- `unknown`;
- `pending_owner_evidence`;
- `not_applicable` with rationale.

Blank, unknown and pending facts cannot satisfy a production gate.

### 5.3 Evidence treatment

The public repository may preserve only:

- evidence kind;
- non-secret title/capability label;
- review date;
- non-secret summary;
- SHA-256 of a locally retained artifact when permitted;
- evidence package fingerprint.

It must not preserve:

- API keys or tokens;
- account IDs;
- credential-bearing request examples;
- private headers;
- Cookie or CAS material;
- downloaded Provider datasets;
- restricted contract text that cannot be redistributed.

Screenshots or local documents may be reviewed outside the repository. The repository records only the permitted summary and fingerprint.

## 6. Deterministic capability readiness

### 6.1 Readiness states

Each capability receives exactly one:

- `implementation_ready`;
- `deferred_not_entitled`;
- `deferred_contract_incomplete`;
- `rejected_undocumented`;
- `blocked_retention_or_use`.

### 6.2 Readiness predicate

A capability is `implementation_ready` only when all material facts are `confirmed` or validly `not_applicable`:

1. exact account entitlement;
2. permitted automated personal use;
3. permitted local retention and limits;
4. credential mechanism label and lifecycle;
5. exact approved HTTPS host;
6. method and endpoint contract;
7. request fields and selector semantics;
8. response fields, types and nullability;
9. schema version or reviewed documentation date;
10. pagination, ordering and terminal behavior;
11. rate limit, quota, concurrency and retry guidance;
12. stable source record and symbol identities;
13. timezone and chronology semantics;
14. correction, restatement and late-arrival behavior;
15. sanitized fixture reachable through the same reviewed production contract.

No configuration flag may bypass this predicate.

### 6.3 Current readiness

No capability is currently `implementation_ready` because the owner-provided manifest has not been completed.

Current family decisions:

| Family | Current state | Reason |
|---|---|---|
| `instrument_identity` | `deferred_contract_incomplete` | Exact entitlement, endpoint, limits, identity and sanitized fixture are not repository-confirmed. |
| `daily_market` | `deferred_contract_incomplete` | Same blockers; also adjustment/unit contract must be exact. |
| `company_action` | `deferred_contract_incomplete` | Action identity and chronology remain account-contract facts. |
| `financial_statement` | `deferred_contract_incomplete` | Period, scope, currency, unit, disclosure and restatement contracts remain unconfirmed. |
| `industry_taxonomy` | `deferred_contract_incomplete` | Current/effective membership contract is unconfirmed. |
| `concept_taxonomy` | `deferred_contract_incomplete` | Current/effective membership contract is unconfirmed. |
| `market_attention` | `deferred_contract_incomplete` | Exact list/window/identity/entitlement contract is unconfirmed. |
| `bulk_market_dump` | `deferred_contract_incomplete` | Separate file/coverage/retention/replay contract is absent. |

This table is not a rejection of the Provider. It is a fail-closed readiness record.

## 7. First implementation candidate: 190-A only

When the required account facts are confirmed and a separate Strict implementation Issue is authorized, the first candidate slice is:

**THS Provider Foundation and Instrument Identity (190-A)**

### 7.1 Authorized future behavior candidate

- append-only source authorization identity and revisions;
- append-only capability revisions bound to one reviewed manifest fingerprint;
- credential profile key boundary with secret material loaded only at runtime;
- dry-run request planning with zero network;
- explicit `remote_access_confirmed=true` requirement for any later live operation;
- acquisition attempt identity and append-only revisions;
- immutable L0 raw response bytes;
- deterministic request fingerprint;
- safe status/diagnostic recording with credential redaction;
- Provider instrument candidates from exact documented fields;
- explicit mapping review to an existing Listed Instrument identity;
- exact-ID provenance reads;
- ordinary tests and CI with network blocked;
- one separately marked smoke test disabled by default.

### 7.2 Explicitly deferred behavior

190-A does not normalize or promote:

- daily prices;
- company actions;
- financial statements;
- financial indicators;
- industry/concept membership;
- hot lists or market attention;
- Canonical Price;
- Evidence Ledger items;
- normalized financial observations;
- beneficiary or Investment Candidate state.

Those remain 190-B/190-C or later separately authorized work.

## 8. Ownership boundaries

| State | Owner | First-slice rule |
|---|---|---|
| Source authorization | THS acquisition domain | Exact append-only revision; only `active` may later access network. |
| Capability readiness | THS acquisition domain | Frozen manifest facts and deterministic predicate. |
| Credential secret | Local environment/approved secret store | Never repository or database content. |
| Credential profile key | THS acquisition domain | Non-secret lookup label only. |
| Acquisition attempt | THS acquisition domain | One explicit bounded operation. |
| Raw response | THS acquisition domain, L0 | Immutable bytes and provenance, no accepted meaning. |
| Provider instrument candidate | THS acquisition domain, D2 candidate | Candidate only; no fuzzy or inferred identity. |
| Listed Instrument | Existing Listed Instrument domain | Remains accepted identity owner. |
| Canonical Price | Existing Canonical Price domain | Unchanged and not written in 190-A. |
| Evidence | Existing Evidence Ledger | Unchanged and not written in 190-A. |
| Financial normalization | Existing normalized-financial domain | Unchanged and not written in 190-A. |
| Investment Candidate | Existing candidate domain | Unchanged and not written in 190-A. |

## 9. Authorization lifecycle

### 9.1 Source authorization states

Retain the accepted closed states:

- `pending_review`;
- `active`;
- `suspended`;
- `retired`.

Only one exact `active` source authorization revision may be used by a future live command.

### 9.2 Capability readiness and runtime state are separate

A capability may be contract-ready while its source authorization is suspended. A source may be active while a specific capability is deferred or not entitled.

A live request requires both:

- exact active source authorization revision;
- exact capability revision with readiness `implementation_ready`.

### 9.3 Mandatory suspension

A later implementation must append a suspended revision before the next remote request when:

- entitlement expires or is revoked;
- contract fingerprint changes;
- host or endpoint contract changes;
- credential mechanism changes materially;
- retention/use rights become unclear;
- schema drift invalidates the reviewed fixture;
- quota/rate behavior conflicts with the reviewed contract;
- Provider indicates service suspension.

No existing raw object or historical revision is deleted.

## 10. Network and credential boundary

### 10.1 Default state

Network is disabled during:

- module import;
- FastAPI startup;
- ordinary read APIs;
- tests;
- CI;
- migrations;
- fixture demos;
- dry-run commands.

### 10.2 Live-request preconditions

A future live command must require:

- exact source authorization revision ID;
- exact capability revision ID;
- credential profile key;
- one family-specific validated selector;
- explicit request bounds;
- information cutoff where material;
- `remote_access_confirmed=true`;
- `dry_run=false`.

Missing or stale state fails before network access.

### 10.3 Host and redirect rules

- HTTPS only;
- exact allowlisted host from the capability revision;
- no wildcard host unless the reviewed contract explicitly requires and bounds it;
- no HTTP downgrade;
- redirects only to another exact reviewed host and only when contractually expected;
- login page, CAPTCHA, interstitial or HTML response for a structured endpoint fails closed;
- no alternate endpoint or Provider fallback.

### 10.4 Credential redaction

Credentials are excluded from:

- request fingerprints;
- raw URL storage;
- request/response headers persisted as provenance;
- logs and errors;
- diagnostics;
- fixtures;
- database rows;
- Issues, PRs and task files.

Tests must include unique sentinel secrets and prove they never appear in user-visible or persisted output.

## 11. Request planning and fingerprint

### 11.1 Candidate commands

A future 190-A Issue may implement these local JSON-only commands:

1. `register-ths-source-authorization` — append secret-free source authorization state;
2. `register-ths-capability-manifest` — validate and append reviewed capability revisions;
3. `plan-ths-structured-request` — emit a redacted deterministic plan without network;
4. `acquire-ths-structured-data` — optional live path only after all gates and explicit confirmation;
5. `review-ths-instrument-candidate` — explicitly bind or reject one candidate;
6. `inspect-ths-provider-provenance` — exact-ID/cutoff-aware readback.

Names are candidates for the later implementation Issue. Production behavior is not authorized here.

### 11.2 Request plan

A plan freezes:

- source authorization revision ID;
- capability revision ID;
- adapter contract version;
- data family;
- endpoint contract key, not a credential-bearing URL;
- method;
- validated canonical selector;
- pagination/order contract;
- bounds;
- transport-policy version;
- dry-run/live mode.

### 11.3 Fingerprint

SHA-256 uses canonical UTF-8 JSON of the plan fields above. It excludes:

- credentials;
- runtime timestamps;
- non-deterministic request IDs;
- local file paths;
- free-text diagnostics.

Equal reviewed plans produce equal fingerprints.

## 12. Attempt and raw-capture contract

### 12.1 Attempt states

Retain:

- `planned`;
- `running`;
- `succeeded`;
- `partial`;
- `unauthorized`;
- `forbidden`;
- `rate_limited`;
- `quota_exhausted`;
- `blocked`;
- `contract_changed`;
- `failed`.

No state triggers fallback or automatic retry outside the reviewed policy.

### 12.2 Retry

Until exact account guidance is confirmed, retry behavior is not implementation-ready. A later capability revision must freeze the account-specific policy.

The maximum architecture ceiling remains:

- no retry for authentication, permission, validation or schema failures;
- no same-command retry for quota/rate limit;
- at most one documented transient retry;
- no host or Provider fallback.

### 12.3 Raw object

One accepted structured response body is stored immutably with:

- raw response UUID;
- exact attempt revision;
- request fingerprint;
- exact capability revision;
- family and page/cursor identity;
- method and endpoint contract key;
- response status;
- allowlisted non-secret headers only;
- media type;
- byte length and SHA-256;
- fetched-at UTC;
- recorded-at UTC;
- adapter and schema versions;
- database-owned raw bytes.

### 12.4 Ceilings

The first implementation may choose stricter values but may not exceed the accepted architecture:

- 10 MiB per raw object;
- 50 MiB aggregate raw bytes per command;
- 10 pages;
- one concurrent request;
- no truncation presented as success.

Oversized or bound-exhausted operations fail or become explicit `partial` state without automatic continuation.

### 12.5 Duplicate and changed content

- exact request/page identity plus equal raw SHA-256 is idempotent;
- equal source identity with changed bytes creates a new raw object and append-only attempt revision;
- schema contract change records `contract_changed` and blocks normalization/candidate generation;
- prior bytes and revisions are never overwritten.

## 13. Instrument candidate contract

A Provider instrument candidate may use only:

- exact Provider symbol/code;
- exact documented exchange/market field;
- exact documented security type;
- reviewed deterministic aliases.

It may not use:

- code-prefix guessing;
- fuzzy company-name matching;
- concept membership;
- hot-list reason text;
- LLM inference.

Closed candidate states remain:

- `exact_candidate`;
- `no_candidate`;
- `ambiguous`;
- `market_conflict`;
- `security_type_conflict`;
- `retired_symbol`;
- `blocked`.

An explicit review freezes either:

- one exact existing Listed Instrument identity/revision; or
- one rejection/block reason.

No candidate automatically creates a Listed Instrument or changes existing identity history.

## 14. Persistence candidate for 190-A

The first implementation candidate uses only this subset of the accepted seventeen-table architecture:

1. `ths_source_authorization_identity`;
2. `ths_source_authorization_revision`;
3. `ths_capability_revision`;
4. `ths_acquisition_attempt_identity`;
5. `ths_acquisition_attempt_revision`;
6. `ths_raw_response_object`;
7. `ths_instrument_candidate`.

No existing table is modified and no existing data is backfilled.

### Required constraints

- application-generated UUID primary keys;
- append-only revisions with unique revision number per identity;
- expected-latest protection for reviewed state changes;
- exact foreign keys from attempt/raw/candidate records;
- unique request/page/raw-hash identity where appropriate;
- UTC timezone-aware timestamps;
- raw bytes stored as `LargeBinary` / PostgreSQL `BYTEA` / SQLite `BLOB`;
- no credential material;
- no cascade that destroys provenance;
- PostgreSQL concurrency tests;
- documented SQLite serialized-write behavior.

### Rollback and downgrade

- rollback before migration: no data effect;
- rollback after implementation: disable the source authorization and revert runtime commands while preserving captured history;
- populated downgrade refuses before dropping any THS table;
- empty downgrade may proceed only in exact reverse dependency order;
- no history rewrite or destructive backfill.

The migration remains a candidate only. This PR creates no schema.

## 15. Exact read candidates

A later implementation may expose local exact-ID reads for:

- source authorization revision;
- capability revision and manifest fingerprint;
- acquisition attempt revision;
- immutable raw response metadata, with bytes separately permissioned/local;
- instrument candidate and mapping review state.

Historical reads accept both:

- `information_cutoff_date` when the record has information-date meaning;
- `recorded_at_utc`.

No read triggers network access, selects a newer compatible record or reveals credential material.

## 16. Offline golden path

The production-realistic architecture path is:

1. owner completes a secret-free capability manifest;
2. one `instrument_identity` capability satisfies every readiness predicate;
3. a reviewed manifest fingerprint is frozen;
4. one source authorization revision becomes `active` and one capability revision becomes `implementation_ready`;
5. `plan-ths-structured-request` validates an exact selector and emits a redacted request plan with no network;
6. one sanitized response fixture reachable from the reviewed endpoint contract is replayed offline;
7. one immutable raw object preserves exact bytes, SHA-256, request fingerprint and chronology;
8. documented symbol, market and security-type fields create one exact instrument candidate;
9. explicit review binds the candidate to one existing Listed Instrument revision;
10. exact provenance is read back under the recorded-UTC boundary;
11. no Canonical Price, Evidence Ledger, normalized financial, taxonomy, beneficiary, Investment Candidate, recommendation or trading state changes;
12. the test proves zero external network.

### Current golden-path status

The specification is complete enough to test once evidence exists, but it is not currently executable with production-reachable fixtures because the account capability manifest and sanitized examples are absent.

Therefore the gate remains `blocked_pending_account_facts`.

## 17. Primary failure path

The mandatory failure path is an incomplete or mismatched source contract:

1. at least one required entitlement, host, endpoint, limit, retention, identity, chronology or fixture fact is not confirmed;
2. readiness resolves to `deferred_contract_incomplete`, `deferred_not_entitled`, `rejected_undocumented` or `blocked_retention_or_use`;
3. source authorization remains `pending_review` or becomes `suspended`;
4. request planning returns a structured blocked result;
5. no credential is loaded and no network is attempted;
6. no raw object, instrument candidate or downstream state is created;
7. no browser replay, limit probing, alternate endpoint, public scraper or Provider fallback occurs.

Other fail-closed paths include:

- unexpected host or redirect;
- HTML/login/CAPTCHA response;
- unauthorized, forbidden, quota or rate-limit response;
- schema drift;
- oversized response;
- ambiguous or conflicting identity;
- secret sentinel appearing in output;
- contract fingerprint changed since capability review.

## 18. Testing contract for later implementation

190-A must prove:

1. zero-network imports, startup, reads, ordinary tests, CI and fixture demos;
2. capability readiness truth table;
3. manifest canonicalization and SHA-256 determinism;
4. no secret material in persisted rows, fingerprints, logs, errors or fixtures;
5. exact host allowlist and redirect rejection;
6. dry-run performs no network;
7. live mode requires explicit confirmation and an exact active authorization/capability;
8. request fingerprint determinism;
9. attempt-state transitions and expected-latest conflict behavior;
10. per-object and aggregate byte ceilings;
11. raw idempotency and append-only changed-content behavior;
12. 401/403/429/quota/schema-drift fail-closed handling using sanitized fixtures;
13. exact instrument candidate inputs and ambiguity handling;
14. explicit mapping review to existing Listed Instrument identity;
15. exact-ID/cutoff-aware provenance reads;
16. PostgreSQL concurrency and SQLite behavior;
17. migration upgrade and populated downgrade refusal;
18. no downstream automatic promotion;
19. one separately marked opt-in smoke test disabled by default.

No live smoke test runs in normal CI.

## 19. Deferred phases

### 190-B

Deferred until separate authorization and exact capability facts:

- daily market normalization;
- company actions;
- financial statements;
- no automatic Canonical Price or normalized-financial promotion.

### 190-C

Deferred until separate authorization and exact capability facts:

- industry and concept taxonomies;
- current-versus-historical membership protection;
- market-attention observations;
- no Daily Radar, alerts or candidate-status mutation.

### Later product phases

Also excluded:

- scheduled refresh;
- Daily Research Radar;
- Follow/Track and reminders;
- Research Portfolio;
- recommendations or trading.

## 20. Architecture stop conditions

Return to project-owner/source review if:

- the owner cannot establish exact enabled account capabilities;
- automated personal access or local retention is not permitted;
- only browser session, Cookie/CAS ticket, private endpoint or reverse-engineered signature works;
- exact approved hosts, identities, limits or revision behavior cannot be established;
- sanitized fixtures cannot represent production responses without secrets;
- implementation requires multiple Providers or fallback;
- Provider rows would silently replace existing accepted domain owners;
- the first slice requires daily market, financial, taxonomy or attention semantics to function;
- the migration requires backfill, destructive history changes or existing-table ownership changes;
- normal tests or reads require network;
- secret material must enter repository or database state.

## 21. Definition of Ready for a later implementation Issue

A separate Strict 190-A implementation Issue may be created only when:

- the manifest template is completed for the first-slice capabilities;
- the project owner explicitly confirms the non-secret facts and evidence fingerprint;
- at least one required capability is `implementation_ready`;
- sanitized production-reachable fixtures exist;
- exact host, endpoint, limits, identity and chronology contracts are frozen;
- migration subset, commands, reads, golden path and failure path remain accepted at one fixed architecture HEAD;
- architecture CI and process-independent fixed-head review succeed;
- all review threads are resolved;
- the project owner separately authorizes architecture merge and later implementation start.

Architecture merge alone does not authorize production code or live access.

## 22. Current conclusion

The next roadmap phase has entered Strict architecture work, but production implementation is not yet ready.

Current result:

`blocked_pending_account_facts`

The exact missing inputs are the owner-completed non-secret account capability manifest and sanitized production-reachable fixtures. No secrets are needed or permitted.

Required fixed-head review phrase:

`AUTHORIZED CONTROLLED THS DATA REFRESH MVP PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`

Any new commit invalidates fixed-head validation and review.