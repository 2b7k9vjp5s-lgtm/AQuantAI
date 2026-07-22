# THS Structured Provider v1 — Closure Decisions and Open Gates

## 1. Authority

- Governing Issue: #190.
- Architecture document: `docs/ths_structured_provider_preflight.md`.
- Required base: `2247499f698f1fbdea5fc33503678c682662c166`.
- Risk tier: **Strict**.
- Architecture only.

This document records the decisions that must remain stable during fixed-head review. It also separates architecture closure from account-specific contract facts that still block production implementation.

## 2. Source status

### Decision

The selected source is the official account-authorized 同花顺 / HiThink Financial Data API for personal, local and non-commercial research.

The project records the source as:

- `source_key`: `ths-account-structured-provider-v1`;
- acquisition mode: `account_authorized_api`;
- adapter family: `ths_structured_provider`;
- production transport candidate: documented REST API.

### Current state

The user reports that the 同花顺 API has been applied for. The repository does not yet possess the non-secret account capability manifest needed to mark the source authorization `active`.

The initial source authorization state is therefore:

`pending_review`

This is not a rejection of the Provider. It is a hard boundary preventing the architecture from guessing account entitlements, rate limits, hosts, endpoint contracts or retention rights.

## 3. Contract evidence decision

### Decision

Implementation requires a secret-free account capability package containing:

1. exact enabled capability/product names;
2. credential mechanism label;
3. exact approved HTTPS hosts;
4. accepted endpoint contract keys;
5. request/response schema versions or reviewed dates;
6. pagination/order semantics;
7. rate limits, quotas and concurrency;
8. historical coverage;
9. local-retention/personal-use restrictions;
10. correction/restatement behavior.

The package may be represented by screenshots, downloaded documentation or local notes, but the public repository records only non-secret summaries and fingerprints.

### Rejected

- posting an API key in chat, Issue or PR;
- copying a full credential-bearing request;
- storing an account ID;
- treating public documentation visibility as proof that every endpoint is enabled;
- inferring limits by repeatedly calling until blocked.

## 4. Transport decision

### Decision

Documented REST is the only production transport candidate for v1.

### Auxiliary tools

- Python SDK may be used to compare documented behavior or construct fixtures only after its exact version and transport are reviewed.
- CLI may be used for a user-invoked bootstrap only if it produces a complete, fingerprinted and reproducible artifact under the same source authorization.
- MCP may assist interactive exploration but cannot own accepted ingestion state.
- Bulk dumps may be a separate explicit bootstrap capability, not a hidden REST fallback.
- DuckDB may be a cache or projection, not the default authoritative system of record.

### Rejected

- browser-session replay;
- Cookie or CAS ticket;
- reverse-engineered signatures;
- undocumented endpoints;
- proxy rotation;
- automatic provider fallback.

## 5. Network execution decision

### Decision

All remote operations are explicit local commands. Network is disabled by default.

A live command requires:

- exact active source authorization revision;
- exact active capability revision;
- credential profile key;
- validated bounded selector;
- explicit remote-access confirmation.

No import, startup, ordinary read, test, CI or fixture demo performs network access.

### Retry decision

- no retry for authentication, permission, validation or schema errors;
- no same-command retry for quota or rate limit;
- at most one documented transient retry;
- no alternate host or source fallback.

## 6. Raw capture decision

### Decision

Raw Provider responses are immutable L0 objects stored as database-owned binary bytes:

- SQLAlchemy `LargeBinary`;
- PostgreSQL `BYTEA`;
- SQLite `BLOB`.

V1 does not introduce filesystem or object-store raw persistence.

### Ceilings

- 10 MiB per raw response object;
- 50 MiB aggregate raw bytes per command;
- oversized responses fail without truncation.

### Required provenance

Every raw object binds:

- source and capability revisions;
- acquisition attempt revision;
- request fingerprint;
- data family and page/cursor identity;
- media type and byte length;
- SHA-256;
- fetched-at and recorded-at UTC;
- adapter/schema contract versions.

Secrets and private headers are excluded.

## 7. Source-specific persistence decision

### Decision

The architecture uses THS-specific source tables rather than introducing a generic multi-provider acquisition framework.

Reason:

- data-family semantics differ materially;
- the first implementation must prove one complete source path;
- generic abstraction would hide endpoint, revision and ownership differences;
- CNINFO acquisition is not implemented and cannot act as a shared runtime base.

The proposed 17-table migration is a candidate only and is not authorized until a bounded implementation Issue is opened.

## 8. Existing market-data ownership decision

### Decision

THS daily-market rows remain source-normalized L1 observations.

They do not automatically replace:

- existing market-data persistence ownership;
- Canonical Price;
- purpose-specific Comparison Eligibility.

A later canonical-promotion command must bind exact source authorization, raw response, normalized observation, Listed Instrument identity and accepted price-series contract.

### Rejected

- selecting THS merely because it is newer;
- mixing rows from THS and another Provider in one series;
- changing canonical price when a new raw response arrives;
- inferring adjustment state from endpoint or field names.

## 9. Instrument identity decision

### Decision

Provider symbol mapping is a candidate workflow, not automatic identity acceptance.

Permitted candidate inputs:

- documented symbol/code;
- documented market/exchange field;
- documented security type;
- reviewed deterministic aliases.

Rejected inputs:

- code-prefix guessing;
- fuzzy company-name matching;
- concept membership;
- free-text abnormal-move reasons;
- LLM inference.

Downstream normalized observations require one explicitly accepted Listed Instrument mapping.

## 10. Daily market and company-action decision

### Daily market

The architecture preserves exact source representation before Decimal normalization and records explicit adjustment state.

Closed adjustment states:

- `raw_unadjusted`;
- `forward_adjusted`;
- `backward_adjusted`;
- `provider_adjusted_unspecified`;
- `unknown`.

Only documented states may be used downstream. Unknown or unspecified adjusted data is ineligible for Canonical Price.

### Company actions

Company actions remain source observations. No adjustment factor is derived unless all deterministic inputs and the exact formula contract are reviewed.

Action chronology remains explicit. Missing dates remain missing rather than inferred.

## 11. Financial-statement decision

### Decision

Provider financial values are contract-specific source observations. They do not become official filing evidence merely because the Provider is reputable.

Every observation separates:

- report period end;
- statement family;
- report type;
- consolidated/parent scope;
- audit state;
- currency and unit;
- disclosure/publication time;
- Provider update time;
- fetched/recorded time;
- source record identity;
- raw response.

### Visibility decision

A Provider value is eligible for an information-cutoff read only when a documented disclosure/publication time is available and on or before the cutoff.

When disclosure time is absent, the value may be stored and inspected but cannot be represented as an official as-of fact.

### Restatement decision

Changed values are append-only revisions. No last-write-wins overwrite.

### Derived-value decision

FCF, net debt, EBITDA, diluted shares and valuation metrics require:

- a reviewed exact direct mapping; or
- a versioned deterministic formula over exact observations.

Labels and free text do not own derivation meaning.

## 12. Taxonomy decision

### Decision

Industry and concept taxonomies are Provider source taxonomies. They do not create Stage 1 beneficiary status.

Current membership snapshots are not historical membership.

Historical as-of reads require source-supplied effective history. Otherwise they return:

`historical_membership_unavailable`

### Rejected

- carrying the current membership backward;
- treating concept membership as direct business exposure;
- creating a beneficiary from a taxonomy label.

## 13. Market-attention decision

### Decision

Hot lists, rank changes, abnormal-move reasons, limit-up pools, consecutive-limit-up state and dragon-tiger-list events are market-state observations only.

They preserve exact list/event type, observation time, ranking window, rank/value and source text.

They cannot in v1:

- create beneficiary status;
- alter evidence grade;
- create catalysts or risks automatically;
- alter accepted component assessments;
- directly change Investment Candidate status;
- create alerts, recommendations or trade actions.

A later Slice 7 rule may consume exact attention observations after separate authorization.

## 14. Duplicate and revision decision

### Decision

Exact raw duplicates are idempotent. Changed content is append-only.

The implementation must distinguish:

- exact raw duplicate;
- same source identity and same normalized value;
- same source identity and changed value;
- Provider-declared correction/restatement;
- late arrival;
- identity conflict;
- schema contract change.

No ordinary path overwrites prior raw bytes or normalized revisions.

## 15. Time decision

Keep separate:

- market trading date;
- statement report period end;
- statement disclosure/publication time;
- taxonomy observation/effective time;
- attention observation/window time;
- Provider update time;
- request time;
- fetched-at UTC;
- recorded-at UTC;
- downstream information cutoff.

Live request, fetched and recorded timestamps are system-owned. Production JSON cannot override them.

Later acquisition cannot appear in an earlier recorded-UTC view. Later Provider revisions cannot rewrite earlier accepted history.

## 16. Command and API decision

### Commands

The source-specific command envelope is:

`acquire-ths-structured-data`

It validates one family-specific selector and supports dry-run planning.

Separate commands may later be introduced for normalization, identity review and provenance inspection, but they remain THS-specific.

### Reads

Reads are exact-ID and cutoff-aware. No read performs network access, fallback or implicit newest-record selection.

## 17. Implementation sequencing decision

The architecture covers one coherent Provider domain, but production work should be split into bounded implementation slices after architecture approval.

Recommended order:

### Slice 190-A — Provider foundation and identity

- source authorization/capability revisions;
- credential profile boundary;
- acquisition attempts;
- immutable raw response objects;
- instrument candidates and explicit acceptance;
- dry-run and opt-in smoke-test boundary.

### Slice 190-B — Daily market, company actions and financial statements

- exact accepted endpoint contracts;
- market/company-action normalization;
- financial statement identities, revisions and line observations;
- no automatic Canonical Price or normalized-financial promotion.

### Slice 190-C — Taxonomy and market attention

- industry/concept taxonomy and membership observations;
- current-versus-historical protection;
- hot-list/event observations;
- no candidate-status or recommendation mutation.

Each implementation slice requires its own linked Strict Issue, migration decision where applicable, fixed-head review and explicit owner merge authorization.

The owner may combine slices only if the final architecture review confirms the change remains bounded and testable.

## 18. Golden-path decision

The mandatory offline golden path must prove:

- active secret-free capability manifest;
- bounded request planning;
- immutable raw capture;
- exact identity candidate and explicit acceptance;
- market, financial, taxonomy and attention normalization;
- exact provenance readback;
- both as-of boundaries;
- no hidden network;
- no automatic Canonical Price, Evidence Ledger, beneficiary, candidate or recommendation state.

Fixture data may use only fields reachable through reviewed production contracts.

## 19. Primary failure decision

The primary fail-closed path is capability mismatch or source denial.

Expected result:

- attempt state records the denial safely;
- credentials remain redacted;
- no unreviewed body is normalized;
- no downstream state is created;
- no browser replay, alternate endpoint, public scraper or Provider fallback occurs.

## 20. Current implementation blockers

Architecture may proceed to fixed-head review, but production implementation remains blocked until all of the following are owner-confirmed:

1. exact enabled account capabilities;
2. credential mechanism label and local setup method;
3. approved HTTPS host set;
4. endpoint contracts for the first implementation slice;
5. rate limits, quotas and concurrency;
6. retention/personal-use restrictions;
7. historical coverage;
8. stable source identities;
9. correction/restatement behavior;
10. secret-free response fixtures or sanitized examples.

The blockers are source-contract facts, not reasons to inspect browser traffic or reverse engineer the service.

## 21. Fixed-head approval

Required phrase:

`AUTHORIZED THS STRUCTURED PROVIDER PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`

Any new commit invalidates approval.

## 22. Locked exclusions

No production adapter, migration, dependency, credential, live request, scheduler, background worker, CNINFO automated acquisition, public scraping, browser replay, reverse-engineered endpoint, generic fallback, minute/tick data, news/report text, OCR, automatic evidence acceptance, automatic financial derivation, automatic Canonical Price promotion, automatic candidate mutation, unexplained score, recommendation, target price, portfolio, execution, trading, release, tag or version change.
