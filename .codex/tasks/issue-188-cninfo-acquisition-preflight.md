# Issue #188 — Authorized CNINFO Disclosure Acquisition v1 Architecture Preflight

## Authority

- GitHub Issue: #188
- Product Roadmap: #137, Slice 6
- Required base: `2cb894c1547380d2e350d4200150ad50a5461236`
- Branch: `docs/cninfo-authorized-acquisition-preflight`
- Risk tier: **Strict**
- Owner authorization: `进行下一轮开发` on 2026-07-22
- Architecture only; no production network adapter, schema, migration, dependency, credential, release or version change

## Objective

Define one implementable acquisition contract for public listed-company announcements through an explicitly licensed and documented CNINFO / 巨潮资讯 data service.

The architecture must make one narrow decision:

> AQuantAI may later acquire CNINFO announcement metadata and document objects only through a formally authorized data-service/API contract. Public-page scraping, browser request replay and undocumented endpoints are not accepted production contracts.

The output of this task is a Definition of Ready, not an implementation.

## Accepted source candidate

- Operator: 深圳证券信息有限公司 / CNINFO.
- Source class: official listed-company disclosure platform.
- Document class: public listed-company announcements and official document objects.
- Accepted future acquisition mode: `licensed_api` only.
- One source registration and one source-specific adapter.
- One explicit user-initiated bounded request in v1.
- No scheduler, background worker or automatic daily polling.

The implementation gate remains closed until the project owner provides or confirms all of:

1. official API/service documentation;
2. written entitlement or service agreement permitting automated access;
3. retention and local-storage rights for response/document objects;
4. credential mechanism and account scope;
5. rate limits, quotas and request constraints;
6. stable source identifiers, pagination and document-locator semantics.

## Existing accepted boundaries

Reuse without changing meaning:

- Evidence Ledger `ResearchCase`, `EvidenceItem`, `ClaimRevision` and `ClaimEvidenceLink`;
- Listed Instrument and Company Research identity/revision boundaries;
- information cutoff and recorded-UTC leakage prevention;
- append-only accepted history;
- local-only default startup, reads, tests, CI and fixture demos;
- deterministic state and accepted decisions outside LLM ownership.

Do not reuse market-data `IngestionRun` merely because both workflows involve acquisition. Document acquisition has different source authorization, immutable-object, duplicate, review and acceptance semantics.

## Required architecture decisions

### 1. Source authorization

Define append-only source authorization identity/revisions containing:

- stable source key;
- operator and service-product label;
- document class;
- permitted acquisition mode;
- authorization basis and review date;
- active/suspended/retired/pending state;
- credential profile key only, never credential material;
- contract fingerprint and schema-contract version;
- permitted retention and replay behavior.

### 2. Credential and network boundary

Define:

- environment/secret-store loading outside repository state;
- explicit disabled-by-default network profile;
- one allowlisted HTTPS host set from official documentation;
- connect/read timeout;
- bounded retry policy only for reviewed transient statuses;
- no redirect to unreviewed hosts;
- redacted diagnostics;
- no credentials in URLs, fixtures, logs, Issues or errors.

### 3. User-initiated acquisition

Define one bounded command that requires:

- exact source-authorization revision ID;
- explicit company/instrument selector or exact source code;
- start/end publication date;
- maximum page count and item count;
- information cutoff and recorded-at boundary;
- explicit confirmation that remote access will occur;
- dry-run request-plan mode without network.

No startup request, ordinary read request, scheduler, daemon, webhook or background execution.

### 4. Immutable capture

Separate:

- acquisition attempt identity/revision;
- immutable metadata response object;
- immutable document object;
- request fingerprint;
- response/document SHA-256;
- media type and byte length;
- source locator and source natural identity;
- requested/fetched/recorded timestamps;
- HTTP status and credential-safe diagnostics.

Raw objects remain L0 audit state and cannot directly become accepted Evidence Ledger records.

### 5. Source-specific normalization

Define one CNINFO-specific normalizer contract for:

- source announcement ID;
- security code and issuer text;
- title;
- publication timestamp/date;
- category/type values if contractually documented;
- official document locator and media type;
- response schema version;
- normalized metadata fingerprint;
- deterministic ordering and strict missing-field behavior.

No free-text entity inference, OCR or generic provider abstraction.

### 6. Duplicate, correction and replay

Distinguish:

- exact response duplicate;
- exact document-byte duplicate;
- same source natural ID with identical fingerprint;
- same source natural ID with changed fingerprint;
- source-declared correction/supersession;
- normalized duplicate under different natural ID;
- ambiguous collision requiring review.

A repeated fetch must be idempotent for exact duplicates and append-only for changed source objects. It must not silently overwrite prior raw objects.

### 7. Candidate identity

Candidate generation may use only:

- exact documented source security code;
- exact exchange/market field if supplied;
- exact issuer text;
- reviewed deterministic aliases.

Candidates record method, matched value, target identity/revision, ambiguity and reason codes. Candidate match is not accepted identity.

### 8. Human review and acceptance

Define explicit review outcomes:

- pending;
- accepted;
- rejected;
- duplicate;
- superseded;
- identity_ambiguous;
- unauthorized;
- blocked;
- failed.

Acceptance requires one explicit transaction that records:

- exact source authorization revision;
- acquisition attempt and raw object IDs;
- normalized document revision;
- selected target `ResearchCase`;
- accepted company/instrument identity where relevant;
- evidence grade and source kind;
- EvidenceItem fields;
- optional exact existing ClaimRevision link;
- reviewer label and decision rationale;
- expected-latest protection.

No automatic EvidenceItem, claim, grade or identity acceptance.

### 9. Time and cutoff semantics

Keep separate:

- source publication time;
- source update/correction time when documented;
- request time;
- fetched time;
- local recorded UTC;
- information cutoff used by downstream reads.

Later acquisition cannot appear in an earlier recorded-UTC view. Later correction cannot rewrite earlier accepted history.

### 10. Schema and migration candidate

Define minimum additive append-only tables for:

- source authorization identities/revisions;
- acquisition attempt identities/revisions;
- immutable raw metadata objects;
- immutable raw document objects;
- normalized announcement identities/revisions;
- entity candidates;
- review decisions;
- accepted-evidence provenance bridge.

Decide exact constraints, indexes, PostgreSQL/SQLite semantics, migration order, populated downgrade refusal and no existing-table backfill.

### 11. Commands and reads

Candidate future commands:

1. register/update source authorization;
2. plan acquisition without network;
3. acquire one bounded window;
4. normalize one captured object set;
5. list identity candidates;
6. accept/reject/mark duplicate;
7. inspect exact provenance.

Reads must be exact-ID and cutoff-aware. No endpoint may trigger acquisition.

### 12. Testing

Require:

- offline contract fixtures matching reviewed schemas;
- zero-network imports/startup/ordinary reads/tests/CI/demos;
- one separately marked opt-in contract smoke test disabled by default;
- request fingerprint and pagination determinism;
- rate-limit/timeout/401/403/429 handling;
- schema drift and unexpected-host rejection;
- credential redaction;
- immutable object and duplicate behavior;
- changed-natural-ID correction behavior;
- ambiguous identity review;
- atomic acceptance and rollback;
- cutoff/recorded-UTC leakage prevention;
- PostgreSQL concurrency and supported SQLite behavior;
- populated downgrade refusal.

## Production-realistic golden path

The architecture document must specify one offline-replayable golden path corresponding to a future licensed request:

1. active source authorization revision;
2. explicit bounded company/date request plan;
3. one immutable metadata response object;
4. one immutable official announcement document object;
5. deterministic normalized announcement revision;
6. exact listed-instrument/company candidate;
7. explicit human acceptance;
8. one accepted EvidenceItem and optional existing-claim link;
9. exact provenance readback under both as-of boundaries;
10. no hidden fallback or background request.

## Primary failure path

No accepted-state write when:

- entitlement or API documentation is missing/expired;
- authorization is not active;
- host, endpoint, response schema or natural identity differs from contract;
- source returns unauthorized, forbidden, rate-limited or access-control response;
- document bytes conflict unexpectedly;
- identity is ambiguous;
- chronology violates cutoff;
- acceptance transaction cannot commit fully.

## Stop conditions

Do not authorize implementation if:

- only public-page scraping or undocumented browser endpoints are available;
- permitted automation or retention cannot be demonstrated;
- CAPTCHA, stealth browser, proxy rotation, session impersonation or rate-limit bypass would be required;
- exact source/document identity remains unstable;
- multiple providers or a generic provider registry become necessary;
- human acceptance ownership is unresolved;
- the source contract cannot be represented by offline fixtures without secrets.

## Deliverables

1. this task snapshot;
2. `docs/cninfo_acquisition_preflight.md`;
3. synchronized `docs/architecture_baseline.md`;
4. one Draft architecture PR based exactly on the required base;
5. documentation validation and process-independent fixed-head review.

## Required approval

`AUTHORIZED CNINFO DISCLOSURE ACQUISITION PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`

## Locked exclusions

No production code, migration, dependency, credential, live request, public-page scraping, browser automation, reverse-engineered endpoint, scheduler, background worker, multiple source, news/social/research-report ingestion, OCR, generic Provider registry, fuzzy identity acceptance, automatic EvidenceItem or claim creation, automatic evidence grade, LLM-owned accepted state, market-attention scoring, alerts, recommendation, portfolio, trading, release, tag or version change.
