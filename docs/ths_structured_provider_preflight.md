# Account-Authorized THS Structured Financial Data v1 Architecture Preflight

## 1. Decision status

This document defines the Strict Definition of Ready for the first account-authorized structured financial-data Provider slice.

- Governing Issue: #190.
- Product Roadmap: #137, Slice 6.
- Required base: `2247499f698f1fbdea5fc33503678c682662c166`.
- Release remains `0.2.0`.
- Architecture only; no production schema, migration, dependency, credential, live request or runtime adapter is authorized by this document alone.

### 1.1 Architecture decision

The accepted source candidate is the official 同花顺 / HiThink Financial Data API under one user-owned account for personal, local and non-commercial research.

The accepted future acquisition mode is named:

`account_authorized_api`

The production transport candidate is the documented REST API. A local SDK, CLI, MCP tool or bulk data dump may be used only where the reviewed contract explicitly permits it and the implementation Issue identifies its exact role. They may not become silent alternate runtime transports.

The architecture accepts one source-specific adapter family:

`ths_structured_provider`

It rejects:

- browser-session replay;
- Cookie or CAS-ticket capture;
- reverse-engineered request signing;
- undocumented or private endpoints;
- multiple runtime providers or automatic fallback;
- direct promotion of Provider observations into official disclosure evidence;
- direct promotion of Provider popularity into investment quality;
- a generic Provider framework introduced before one concrete source path works.

### 1.2 Source portfolio boundary

The source portfolio is intentionally split:

- 同花顺 supplies structured Provider observations for accepted market, financial, taxonomy and attention families.
- CNINFO automated acquisition remains blocked until official Token/entitlement, retention, limits and document rights are confirmed.
- Official CNINFO announcement/PDF manual import remains a separate future offline workflow.

No source may silently substitute for another. A failed 同花顺 request does not trigger CNINFO, AKShare, Tushare, public-page scraping or cached third-party fallback.

## 2. Product boundary

The capability answers:

> What exact structured Provider response was acquired under which account-authorized contract, how was it normalized, what internal identity was selected, and which downstream read or deterministic calculation used the exact observation?

It does not answer:

- whether a security should be bought, sold or held;
- whether a popular security is a good investment;
- whether a Provider field is equivalent to an official filing fact without separate evidence;
- whether a current concept membership existed historically;
- whether an adjusted price is canonical for every purpose;
- whether an unreviewed derived financial metric is meaningful;
- whether another source should be tried after failure.

This is structured Provider acquisition and provenance, not an autonomous investment agent.

## 3. Source-contract gate

### 3.1 Required non-secret contract package

Before an implementation Issue may authorize a live request, the repository record must identify a reviewed contract package containing all of:

1. provider/operator and exact product names;
2. official documentation version or review date;
3. enabled account capabilities;
4. permitted personal non-commercial use;
5. permitted automated access and local retention;
6. credential mechanism and renewal/revocation behavior;
7. exact approved HTTPS hosts;
8. endpoint paths and HTTP methods;
9. request fields, pagination and ordering semantics;
10. response fields, types, nullability and identifiers;
11. time-zone and timestamp semantics;
12. rate limits, quotas, concurrency and retry guidance;
13. historical coverage and entitlement limits;
14. correction, restatement and late-arrival behavior;
15. suspension, expiry and contract-change behavior.

The repository records only non-secret labels, approved capabilities, dates and fingerprints. API keys, secrets, account IDs and confidential contract contents remain outside repository state.

### 3.2 Authorization state

A source authorization revision has one of:

- `pending_review`;
- `active`;
- `suspended`;
- `retired`.

Only an exact `active` revision may be used for a remote request.

Missing capability details, uncertain retention rights, unknown rate limits, unreviewed hosts or expired credentials keep the revision at `pending_review` or `suspended`.

### 3.3 Source identity

The proposed first source identity is:

- `source_key`: `ths-account-structured-provider-v1`;
- operator: `同花顺 / HiThink`;
- source class: `account_authorized_financial_data_service`;
- acquisition mode: `account_authorized_api`;
- adapter family: `ths_structured_provider`;
- permitted use: `personal_local_noncommercial_research`.

The source identity does not imply every documented endpoint is authorized. Exact capability revisions own the allowed data families.

## 4. Data-family decision

The architecture accepts a phased Provider contract. The source authorization revision may activate only reviewed families.

### 4.1 Accepted architecture families

The following families are eligible for later implementation after their exact endpoint contracts are confirmed:

1. `instrument_identity`;
2. `daily_market`;
3. `company_action`;
4. `financial_statement`;
5. `industry_taxonomy`;
6. `concept_taxonomy`;
7. `market_attention`.

### 4.2 Conditional families

The following require extra semantic closure before implementation:

- `financial_indicator`: accepted only where exact formula, numerator, denominator, period, currency, unit and restatement behavior are documented;
- `bulk_market_dump`: accepted only as an explicit bootstrap path with file identity, checksums, coverage and replay rules;
- `duckdb_interop`: accepted only as a local cache or research projection unless a later decision makes it authoritative;
- `adjusted_price`: accepted only with exact adjustment-factor and corporate-action semantics;
- `historical_taxonomy_membership`: accepted only if the Provider supplies effective-date history rather than a current snapshot.

### 4.3 Deferred families

The following are outside v1:

- minute bars, tick data and order-book data;
- macroeconomic data;
- news and research-report full text;
- consensus estimates unless exact entitlement and contract are separately reviewed;
- overseas markets;
- sentiment inference;
- automatic announcement or filing extraction;
- autonomous screening, recommendation or trade execution.

## 5. Domain ownership

| State | Authoritative owner | Meaning |
| --- | --- | --- |
| Source authorization | THS acquisition domain | Whether one exact account capability may be used |
| Credential material | local environment/secret store | Runtime-only secret; never repository/database content |
| Capability manifest | THS acquisition domain | Reviewed non-secret list of enabled Provider families |
| Acquisition attempt | THS acquisition domain | One explicit bounded remote operation |
| Raw Provider response | THS acquisition domain, L0 | Immutable bytes/payload and request provenance |
| Provider instrument candidate | THS acquisition domain, D2 candidate | Candidate mapping, not accepted identity |
| Accepted Listed Instrument identity | existing Listed Instrument domain | Exact internal security identity |
| Normalized market observation | THS acquisition domain, L1 | Source-specific price/volume observation |
| Canonical Price | existing Canonical Price domain, L3 | Purpose-specific accepted price owner |
| Company action observation | THS acquisition domain, L1 | Source-specific action event |
| Financial statement observation | THS acquisition domain, L1/L2 contract-specific | Structured Provider value with exact period/scope/unit |
| Normalized financial observation | existing normalized-financial domain | Accepted standardized input under existing rules |
| Taxonomy and membership observation | THS acquisition domain, L1 | Source-specific current or effective membership |
| Market-attention observation | THS acquisition domain, L1 | Provider market-state observation |
| Evidence grade and EvidenceItem | Evidence Ledger | Accepted evidence only after separate human-owned workflow |
| Investment Candidate state | existing Investment Candidate domain | Deterministic research-priority state; never directly owned by Provider attention |

## 6. Network and credential boundary

### 6.1 Disabled by default

A remote operation is disabled unless one explicit local command supplies:

- exact active source authorization revision ID;
- exact capability revision ID;
- credential profile key;
- bounded selector;
- information cutoff;
- remote-access confirmation;
- dry-run choice.

Imports, FastAPI startup, ordinary reads, tests, CI and fixture demos never trigger network access.

### 6.2 Credential rules

Credential material may be loaded only from an implementation-approved environment variable or local secret-store adapter.

Persistence may record only:

- credential profile key;
- credential mechanism code;
- non-secret entitlement label;
- verification state and time;
- expiry date where non-secret and relevant.

Secrets must not appear in:

- source code;
- database rows;
- request fingerprints;
- fixtures;
- logs;
- errors;
- Issues or PRs;
- screenshots or copied examples.

### 6.3 Host allowlist

The active capability revision freezes the exact approved HTTPS host set. Redirects are allowed only when the final host is in the same reviewed set and the contract requires the redirect.

Unexpected host, HTTP downgrade, certificate failure or login/interstitial response fails closed before body acceptance.

### 6.4 Request bounds

The architecture ceiling for one command is:

- one source authorization revision;
- one capability revision;
- one data family;
- at most 20 exact instruments for market or statement requests;
- at most 366 calendar days for daily market data;
- at most 20 report periods for financial statements;
- at most 10 pages;
- at most 2,000 normalized records;
- at most 50 MiB raw aggregate bytes;
- one concurrent request;
- no automatic continuation after a bound is reached.

A later implementation Issue may choose stricter limits but may not widen them without architecture review.

### 6.5 Timeout and retry candidate

Until the official contract specifies otherwise:

- connect timeout ceiling: 10 seconds;
- read timeout ceiling: 60 seconds;
- no retry for `400`, `401`, `403`, `404`, `409`, `422` or schema errors;
- `429` and quota exhaustion record explicit states and do not retry in the same command;
- at most one retry for documented transient `502`, `503`, `504` or connection reset;
- retry must honor `Retry-After` when present;
- no exponential loop, proxy rotation or source fallback.

The exact policy is versioned and cannot be widened by configuration alone.

## 7. Capability manifest

The account capability manifest is a non-secret reviewed object. It contains:

- source authorization revision ID;
- capability key;
- product label;
- endpoint contract key;
- method;
- approved host key;
- schema contract version;
- entitlement start/end where known;
- quota/rate-limit label;
- retention label;
- active/suspended state;
- reviewed-at UTC;
- manifest SHA-256.

The manifest contains no credential values. A capability absent from the manifest is unavailable even when the Provider documentation lists it publicly.

## 8. Explicit acquisition commands

The architecture defines one generic command envelope with one source-specific implementation rather than a generic multi-provider framework.

Candidate command:

`acquire-ths-structured-data`

Required strict-JSON fields:

- `source_authorization_revision_id`;
- `capability_revision_id`;
- `credential_profile_key`;
- `data_family`;
- `selector`;
- `max_pages`;
- `max_records`;
- `max_raw_bytes`;
- `information_cutoff_date`;
- `remote_access_confirmed`;
- `dry_run`;
- optional `expected_latest_attempt_revision_id`.

`selector` is validated by the selected family and cannot contain arbitrary endpoint parameters.

`dry_run=true` performs no network request. It validates authorization, capability, selector, bounds and emits a redacted deterministic request plan.

`dry_run=false` requires `remote_access_confirmed=true`.

No read API may invoke this command.

## 9. Request fingerprint and attempt lifecycle

### 9.1 Request fingerprint

SHA-256 is computed over canonical UTF-8 JSON containing only:

- source authorization revision ID;
- capability revision ID;
- adapter contract version;
- data family;
- validated selector;
- pagination/order contract;
- bounds;
- endpoint contract key;
- transport policy version.

Credentials and runtime timestamps are excluded.

### 9.2 Attempt states

Closed attempt states are:

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

`partial` means raw objects may exist, but no automatic normalized or downstream accepted state is implied.

A later command may explicitly replay the same request fingerprint. The system does not silently infer a resume cursor.

## 10. Immutable L0 capture

Every accepted response body is stored as one immutable raw object with:

- raw response UUID;
- exact attempt revision ID;
- request fingerprint;
- capability revision ID;
- data family;
- page/cursor identity;
- HTTP method and redacted endpoint contract key;
- response status and allowlisted non-secret headers;
- media type;
- byte length;
- SHA-256;
- fetched-at UTC;
- recorded-at UTC;
- adapter version;
- schema contract version.

Authentication headers, cookies, private signatures and raw URLs containing secrets are never stored.

### 10.1 Storage candidate

v1 uses database-owned binary storage for raw response bytes:

- SQLAlchemy `LargeBinary`;
- PostgreSQL `BYTEA`;
- SQLite `BLOB`.

No filesystem/object-store path is introduced in v1.

Per-object ceiling: 10 MiB.

Per-command aggregate ceiling: 50 MiB.

Oversized responses fail without truncation or best-effort parsing.

## 11. Instrument identity

### 11.1 Candidate generation

Candidate mapping may use only:

- exact Provider symbol/code;
- exact documented market/exchange field;
- exact security type where supplied;
- reviewed deterministic alias table.

It may not use:

- code-prefix guessing;
- fuzzy company-name matching;
- concept membership;
- free-text reason fields;
- LLM inference.

### 11.2 Candidate states

- `exact_candidate`;
- `no_candidate`;
- `ambiguous`;
- `market_conflict`;
- `security_type_conflict`;
- `retired_symbol`;
- `blocked`.

Candidate mapping is not accepted identity. A separate explicit review freezes the exact Listed Instrument identity/revision before downstream canonicalization.

## 12. Daily market observations

### 12.1 Source-specific fields

The exact contract must own:

- Provider symbol and market;
- trading date;
- open, high, low and close;
- volume;
- amount/turnover value;
- turnover ratio where documented;
- currency;
- adjustment state;
- source record ID where supplied;
- provider update time where supplied.

### 12.2 Numeric rules

- Persist source numeric text or exact documented representation before Decimal normalization.
- Decimal precision/scale is field-specific and versioned.
- Binary float is never treated as exact without disclosed fidelity.
- Null is unknown, never zero.
- High/low/open/close validation is deterministic and does not repair bad values.
- Negative volume or amount fails normalization.

### 12.3 Raw and adjusted prices

Closed adjustment states are:

- `raw_unadjusted`;
- `forward_adjusted`;
- `backward_adjusted`;
- `provider_adjusted_unspecified`;
- `unknown`.

Only exact documented adjustment semantics are eligible for normalization. `provider_adjusted_unspecified` and `unknown` cannot enter Canonical Price.

### 12.4 Canonical Price boundary

THS market observations are L1 Provider state. They do not become Canonical Price automatically.

Any later canonical promotion must:

- use one exact accepted Listed Instrument;
- bind one succeeded acquisition attempt and one raw response;
- bind one exact normalized market observation;
- satisfy Canonical Price source-series, adjustment, currency, unit and chronology contracts;
- use a separately reviewed deterministic command;
- preserve existing purpose-specific Comparison Eligibility.

The preflight does not change current Canonical Price ownership.

## 13. Company actions

The accepted candidate action types are limited to documented Provider values for:

- cash dividend;
- stock dividend/bonus shares;
- split or consolidation;
- rights/allotment;
- other action only after a separately mapped closed code.

Each observation preserves:

- Provider action ID where supplied;
- instrument candidate/accepted identity;
- announcement date where supplied;
- record date;
- ex-date;
- payment/effective date;
- action type code;
- exact ratio/amount/unit/currency fields;
- source update time;
- raw response link;
- normalizer version.

No price adjustment factor is inferred unless the contract supplies the complete deterministic formula inputs and a separately accepted rule version owns the calculation.

## 14. Financial statements

### 14.1 Statement identity

One financial statement observation identity is keyed by:

- accepted Listed Instrument/Company Research identity;
- statement family: `balance_sheet`, `income_statement`, `cash_flow_statement`;
- report period end;
- report type;
- accounting scope;
- currency;
- unit scale;
- Provider record identity where supplied.

### 14.2 Required chronology

Keep separate:

- report period end;
- source disclosure/publication date/time;
- provider update time;
- fetched-at UTC;
- recorded-at UTC.

A value may be visible under information cutoff only when its disclosure/publication time is on or before that cutoff and its local recorded time is on or before the recorded-UTC boundary.

If the Provider does not supply a disclosure/publication time, the observation cannot be represented as an official as-of fact without another exact source.

### 14.3 Scope and audit state

Closed scope values must be mapped from documented fields:

- `consolidated`;
- `parent_only`;
- `unknown`.

Closed audit states:

- `audited`;
- `reviewed`;
- `unaudited`;
- `unknown`.

Unknown scope or audit state remains explicit and may restrict downstream eligibility.

### 14.4 Restatement and revisions

The system never overwrites a prior financial value.

A repeated Provider record is classified as:

- `exact_duplicate`;
- `same_identity_same_value`;
- `same_identity_changed_value`;
- `provider_declared_restatement`;
- `late_arrival`;
- `identity_conflict`.

Changed values create append-only revisions with exact prior links and source timestamps.

### 14.5 Field observations

Statement fields are stored as source-specific line observations with:

- documented source field code;
- documented label;
- value text;
- normalized Decimal where valid;
- currency;
- unit scale;
- null/missing state;
- normalizer version;
- raw response link.

Labels alone never define internal meaning. A reviewed mapping table owns any promotion to existing normalized-financial field kinds.

### 14.6 Derived values

FCF, net debt, EBITDA, diluted shares and valuation metrics are not accepted merely because a Provider exposes a similarly named field.

They require one of:

- exact direct field mapping with documented definition accepted by the existing normalized-financial contract; or
- a separately versioned deterministic formula over exact accepted observations.

No LLM or free-text inference may derive them.

## 15. Industry and concept taxonomies

### 15.1 Taxonomy identity

Taxonomy identity freezes:

- Provider taxonomy key;
- taxonomy kind: `industry` or `concept`;
- Provider version/effective date where supplied;
- source language;
- hierarchy contract;
- raw response and normalizer version.

### 15.2 Membership observations

Each membership observation records:

- taxonomy revision;
- Provider symbol;
- candidate or accepted Listed Instrument identity;
- node code and label;
- observation time;
- effective-from/effective-to only when supplied;
- current-snapshot flag;
- raw response link.

A current snapshot cannot answer a historical as-of query. When effective history is absent, historical reads fail with `historical_membership_unavailable` rather than carrying the current value backward.

### 15.3 No beneficiary inference

Industry or concept membership does not create Stage 1 beneficiary status. It is a source taxonomy observation only.

## 16. Market-attention observations

### 16.1 Accepted observation classes

Eligible classes after exact contract review include:

- hot-list rank;
- rank-change history;
- abnormal-move reason;
- limit-up pool;
- consecutive-limit-up state;
- dragon-tiger-list event.

### 16.2 Required semantics

Every observation must preserve:

- exact list/event type;
- Provider symbol and market;
- observation timestamp;
- ranking window or event date;
- rank where applicable;
- Provider score/value only when documented;
- reason code/text where supplied;
- source record ID where supplied;
- raw response link;
- normalizer version.

Reason text remains source text. It is not automatically parsed into catalyst, evidence, risk or beneficiary facts.

### 16.3 Downstream restrictions

Market attention may later contribute to a separately authorized market-state component under an explicit rule version.

It cannot:

- create or remove a beneficiary;
- determine company quality;
- upgrade evidence grade;
- overwrite an analyst component;
- trigger a recommendation;
- directly change an Investment Candidate status in this slice;
- create an alert or daily radar output in this slice.

## 17. Normalization, duplicate and correction semantics

Each family has one source-specific normalizer rule key. Initial candidates are:

- `aquantai.ths.instrument-normalization.v1`;
- `aquantai.ths.daily-market-normalization.v1`;
- `aquantai.ths.company-action-normalization.v1`;
- `aquantai.ths.financial-statement-normalization.v1`;
- `aquantai.ths.taxonomy-normalization.v1`;
- `aquantai.ths.market-attention-normalization.v1`.

Closed normalization states:

- `normalized`;
- `missing_required_field`;
- `unsupported_value`;
- `schema_mismatch`;
- `identity_ambiguous`;
- `invalid_numeric`;
- `invalid_chronology`;
- `unit_unknown`;
- `currency_unknown`;
- `contract_changed`;
- `blocked`.

Unknown fields remain only in immutable raw bytes until reviewed. No best-effort promotion.

Exact raw duplicates are idempotent. Changed source content creates a new raw object and append-only normalized revision. No ordinary path overwrites prior raw or normalized values.

## 18. Persistence candidate

The later implementation architecture candidate is an additive migration after `20260722_0015`.

Proposed THS-specific tables:

1. `ths_source_authorization_identity`;
2. `ths_source_authorization_revision`;
3. `ths_capability_revision`;
4. `ths_acquisition_attempt_identity`;
5. `ths_acquisition_attempt_revision`;
6. `ths_raw_response_object`;
7. `ths_instrument_candidate`;
8. `ths_market_observation`;
9. `ths_company_action_observation`;
10. `ths_financial_statement_identity`;
11. `ths_financial_statement_revision`;
12. `ths_financial_line_observation`;
13. `ths_taxonomy_identity`;
14. `ths_taxonomy_revision`;
15. `ths_membership_observation`;
16. `ths_attention_observation`;
17. `ths_downstream_provenance_link`.

This is a candidate, not an authorized migration.

### 18.1 Required constraints

- UUID primary keys generated by application code;
- append-only revision numbers unique per identity;
- expected-latest protection for accepted/reviewed state changes;
- exact foreign keys to raw response and source authorization revisions;
- unique raw SHA-256 plus request/page identity where appropriate;
- Decimal stored as exact text or reviewed numeric types consistent with existing patterns;
- timestamps stored in UTC and timezone-aware;
- closed enums validated in application and database-compatible constraints;
- no credential material;
- no existing-table backfill;
- no delete cascade that destroys provenance.

### 18.2 PostgreSQL and SQLite

Both supported databases must preserve:

- deterministic revision allocation;
- atomic identity/revision creation;
- duplicate protection;
- foreign-key integrity;
- raw-byte fidelity;
- populated downgrade refusal.

PostgreSQL implementation must include concurrency tests. SQLite remains supported for local development under documented serialized-write behavior.

### 18.3 Downgrade

A populated downgrade refuses before dropping THS tables or links. Empty-table downgrade may proceed only in exact reverse dependency order.

## 19. Reads and downstream use

Candidate exact-ID reads:

- source authorization revision;
- capability revision;
- acquisition attempt and raw response;
- instrument candidate;
- market observation;
- company action;
- financial statement revision and line observations;
- taxonomy revision and membership observation;
- attention observation;
- downstream provenance link.

Every read requiring historical meaning accepts:

- `information_cutoff_date`;
- `recorded_at_utc`.

No read endpoint performs network access or selects a newer compatible-looking revision when an exact ID is supplied.

## 20. Production-realistic offline golden path

The required fixture path is:

1. register one active source authorization revision with a secret-free capability manifest;
2. dry-run one bounded request plan;
3. replay one immutable instrument-identity response;
4. create one exact Listed Instrument candidate and explicitly accept its mapping;
5. replay one daily-market response for the accepted instrument;
6. replay one explicit no-company-action result or one documented action;
7. replay one financial-statement response with period, scope, currency, unit and disclosure time;
8. replay one taxonomy/membership response marked as current snapshot;
9. replay one hot-list or event observation with exact window/time semantics;
10. persist immutable raw objects and deterministic normalized observations;
11. read every object by exact ID under both as-of boundaries;
12. verify no Canonical Price, EvidenceItem, beneficiary, Investment Candidate status or recommendation is created automatically;
13. verify no hidden fallback or network request occurs.

## 21. Primary failure path

The primary failure fixture is an account capability mismatch:

1. a source authorization revision is active;
2. the requested family is not present in the exact capability manifest or the Provider returns unauthorized/quota denial;
3. the attempt records `unauthorized`, `forbidden`, `rate_limited` or `quota_exhausted` with redacted diagnostics;
4. no raw body is accepted when the response is a login/interstitial or unreviewed schema;
5. no normalized observation or downstream state is created;
6. no Cookie, browser replay, alternate endpoint, public scraper or fallback Provider is attempted.

Additional fail-closed cases include:

- unexpected host;
- schema drift;
- unknown currency/unit;
- ambiguous instrument identity;
- missing disclosure time for an as-of financial fact;
- changed financial value without append-only revision;
- current taxonomy membership requested as historical;
- attention observation attempting to mutate candidate status.

## 22. Testing contract

Architecture acceptance requires test design for:

1. zero-network import/startup/read/CI behavior;
2. secret-free offline fixtures;
3. credential redaction in logs/errors/fingerprints;
4. request plan/fingerprint determinism;
5. pagination and stable ordering;
6. object and aggregate byte ceilings;
7. `401`, `403`, `429`, quota and timeout behavior;
8. unexpected-host and redirect rejection;
9. schema drift and unknown-field blocking;
10. instrument ambiguity;
11. daily-market numeric/unit/adjustment validation;
12. company-action chronology;
13. financial period/scope/unit/null/restatement behavior;
14. taxonomy current-versus-historical protection;
15. attention window/time semantics and downstream isolation;
16. exact duplicate/idempotency and changed-content revisions;
17. cutoff and recorded-UTC leakage prevention;
18. PostgreSQL concurrency and supported SQLite behavior;
19. migration upgrade and populated downgrade refusal;
20. no automatic Canonical Price, Evidence Ledger, beneficiary, candidate or recommendation mutation.

A live smoke test is separately marked, disabled by default and requires an exact active local credential profile plus explicit operator confirmation.

## 23. Stop conditions

Return to source/architecture review rather than implementation if:

- exact account capabilities cannot be established;
- automated personal access or local retention is prohibited;
- only undocumented endpoints or browser state work;
- credential generation requires reverse engineering;
- hosts, pagination, identifiers, units or revision behavior are unstable;
- raw fixtures cannot represent the production response without secrets;
- the success path requires multiple Providers or fallback;
- market observations would silently replace Canonical Price;
- Provider financial values would silently become official disclosure evidence;
- current taxonomy state would be presented as historical;
- attention would become an unexplained investment score;
- the migration would require destructive backfill or history rewrite.

## 24. Locked exclusions

This preflight does not authorize:

- production adapter code;
- migration or dependency changes;
- live requests or credential setup;
- scheduler/background polling;
- CNINFO automated acquisition;
- public-page scraping or browser replay;
- reverse-engineered endpoints or signatures;
- generic multi-provider fallback;
- minute/tick/order-book ingestion;
- news or research-report ingestion;
- OCR or filing-body extraction;
- automatic EvidenceItem, claim or evidence grade;
- automatic accepted financial derivation;
- automatic Canonical Price promotion;
- automatic beneficiary or Investment Candidate mutation;
- unexplained score, recommendation, target price, portfolio or trading action;
- release, tag or version change.

## 25. Required approval

`AUTHORIZED THS STRUCTURED PROVIDER PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`
