# Authorized CNINFO Disclosure Acquisition v1 Architecture Preflight

## 1. Decision status

This document defines the Strict Definition of Ready for the first authorized external evidence-acquisition slice after Normalized Valuation and Expectation Metrics v1.

- Governing Issue: #188.
- Product Roadmap: #137, Slice 6.
- Required base: `2cb894c1547380d2e350d4200150ad50a5461236`.
- Release remains `0.2.0`.
- Architecture only; no production schema, migration, dependency, credential or network adapter is authorized by this document alone.

### Architecture decision

The only accepted source candidate is a **licensed and documented CNINFO / 巨潮资讯 data service** operated by 深圳证券信息有限公司 for public listed-company announcement metadata and official document objects.

The accepted future acquisition mode is named `licensed_api`.

The following are not accepted acquisition contracts:

- public website HTML availability;
- undocumented JSON or download endpoints observed in a browser;
- replay of browser requests, cookies or session state;
- private or unpublished endpoints discovered through reverse engineering;
- crawling, browser automation or headless rendering;
- a generic Provider adapter that can silently switch sources;
- manual PDF import as the primary product workflow.

The project may proceed to implementation only after the owner supplies or confirms an official service agreement or equivalent written authorization and the exact API contract required by section 3.

### Why the earlier preflight is not reused

Issue #154 / PR #155 selected user-initiated offline PDF import. The project owner rejected that as the primary workflow and closed the PR unmerged. Its separation of raw capture, normalization, candidate identity and human acceptance remains useful, but its acquisition mode is not authorized for production implementation.

This preflight therefore keeps those ownership boundaries while replacing `offline_file` with a contract-gated `licensed_api` mode.

## 2. Product boundary

The capability answers:

> What official announcement objects were acquired under one exact authorized source contract, what bytes and metadata were preserved, which internal identities are candidates, what did a human accept, and which exact accepted Evidence Ledger record resulted?

It does not answer:

- whether the announcement is bullish or bearish;
- whether a company is a beneficiary or investment candidate;
- whether a security should be bought, sold or held;
- whether an announcement should change a score automatically;
- whether a different source should be tried after failure.

Acquisition is a provenance and review workflow, not a recommendation, alert or autonomous research agent.

## 3. Source-contract gate

### 3.1 Required owner-supplied contract package

Before any implementation Issue may authorize a live request, the repository record must identify a reviewed contract package containing all of:

1. service/product name and operator;
2. official documentation version or effective date;
3. permitted automated access method;
4. permitted announcement/document class;
5. account, token, signature or entitlement mechanism;
6. allowed hosts and transport requirements;
7. endpoint paths and HTTP methods;
8. request fields, pagination and sorting semantics;
9. response fields, types, nullability and stable identifiers;
10. document-object locator/download semantics;
11. rate limits, quotas and concurrency limits;
12. retention, local storage and replay permissions;
13. correction, deletion or supersession behavior supplied by the source;
14. error codes and access-control behavior;
15. contract expiry, suspension and re-review conditions.

The package itself must not place credentials or confidential commercial documents into the public repository. The Issue/PR records only a non-secret contract label, review date, approved capabilities and SHA-256 fingerprint of the locally retained contract package where permitted.

### 3.2 Gate result

The source authorization revision has one of:

- `pending_review`;
- `active`;
- `suspended`;
- `retired`.

Only an exact `active` revision may be used for acquisition.

Missing documentation, uncertain retention rights, undocumented endpoints or an expired entitlement keep the source at `pending_review` or `suspended`. They are not engineering tasks to bypass.

### 3.3 Source identity

The first source identity is fixed as:

- `source_key`: `cninfo-authorized-disclosure-v1`;
- operator: `深圳证券信息有限公司`;
- source class: `official_disclosure_data_service`;
- document class: `listed_company_announcement`;
- acquisition mode: `licensed_api`;
- evidence source kind after acceptance: `filing`;
- adapter family: `cninfo_disclosure`.

No second source can share this source identity or adapter.

## 4. Domain ownership

| State | Owner | Meaning |
| --- | --- | --- |
| Source authorization | acquisition domain | Whether one exact contract may be used and under what bounds |
| Credential material | environment/secret store | Runtime access only; never repository or database content |
| Acquisition attempt | acquisition domain | One explicit bounded remote operation and its result |
| Raw metadata response | acquisition domain, L0 | Immutable source bytes plus request/response provenance |
| Raw announcement document | acquisition domain, L0 | Immutable official document bytes plus provenance |
| Normalized announcement | acquisition domain, L1 | Deterministic source-specific metadata under one normalizer version |
| Candidate company/instrument match | acquisition domain, D2 candidate only | Reviewable candidate, never accepted identity |
| Review decision | human-owned D3 workflow state | Accept/reject/duplicate/ambiguous decision |
| Evidence grade and EvidenceItem | Evidence Ledger | Accepted evidence semantics |
| Claim link | Evidence Ledger | Explicit link to one existing exact ClaimRevision |

Market-data `IngestionRun` is not reused. It owns complete market-data snapshots and Provider rows, not immutable disclosure objects and human evidence acceptance.

## 5. Network and credential boundary

### 5.1 Disabled by default

The network adapter is disabled unless all of the following are supplied explicitly for one command:

- exact active source-authorization revision ID;
- named credential profile key;
- remote-transmission confirmation;
- bounded request selector;
- information cutoff;
- explicit recorded-at UTC;
- maximum page count and maximum item count.

Imports, FastAPI startup, ordinary reads, tests, CI and fixture demos never trigger source access.

### 5.2 Credential rules

Credential material may be loaded only from an implementation-approved environment variable or local secret-store adapter. Persistence may record only:

- credential profile key;
- credential mechanism code;
- non-secret entitlement label;
- last verification state and time.

Tokens, passwords, signatures, cookies, private headers and raw connection strings must not appear in:

- source code;
- database rows;
- fixtures;
- test output;
- logs;
- errors;
- Issues or PRs;
- request fingerprints.

### 5.3 Host allowlist

The active authorization revision freezes the exact approved HTTPS host set. Redirects are permitted only when the final host is also in that exact set and the contract explicitly requires the redirect.

Unexpected hosts, HTTP downgrade, certificate failure or redirect loops fail closed before body acceptance.

### 5.4 Request bounds

The v1 command is user initiated and bounded by:

- one source authorization;
- one company/source-security selector;
- one inclusive publication-date window of at most 31 calendar days;
- maximum 10 pages;
- maximum 200 metadata items;
- maximum 50 document-object downloads per command;
- one concurrent request;
- implementation-defined minimum inter-request delay not less restrictive than the source contract;
- no automatic continuation after the command limit.

The final implementation Issue may choose stricter limits but may not widen these architecture ceilings without a new preflight.

### 5.5 Timeout and retry

Candidate transport defaults:

- connect timeout: 10 seconds;
- read timeout: 30 seconds for metadata and 60 seconds for a document object;
- no retry for `400`, `401`, `403`, `404`, `409`, `422` or schema errors;
- `429` is recorded as `rate_limited` and is not retried within the same command;
- at most one retry for contract-approved transient `502`, `503`, `504` or connection reset;
- retry delay must respect documented `Retry-After` when present and otherwise use one deterministic bounded delay;
- no exponential retry loop and no cross-source fallback.

The exact transport policy is persisted by version code.

## 6. Explicit acquisition command

The future command candidate is:

`acquire-cninfo-disclosures`

Required UTF-8 strict-JSON fields:

- `source_authorization_revision_id`;
- `credential_profile_key`;
- `source_security_code`;
- `publication_date_from`;
- `publication_date_to`;
- `max_pages`;
- `max_items`;
- `max_documents`;
- `information_cutoff_date`;
- `recorded_at_utc`;
- `remote_access_confirmed`;
- optional `expected_latest_attempt_revision_id`;
- `dry_run`.

`dry_run=true` performs no network operation. It validates authorization, selector, bounds and builds a redacted request plan with a deterministic request fingerprint.

`dry_run=false` requires `remote_access_confirmed=true` and an active authorization revision.

No API read endpoint may call this command or trigger equivalent behavior.

## 7. Request identity and acquisition attempts

### 7.1 Request fingerprint

The request fingerprint is SHA-256 over a canonical UTF-8 JSON object containing only non-secret reviewed fields:

- source authorization revision ID;
- adapter contract version;
- source security code;
- publication date range;
- page size and ordering contract;
- maximum bounds;
- normalized endpoint contract key;
- transport-policy version.

Credential values and runtime timestamps are excluded.

### 7.2 Attempt identity

Each explicit command creates or dry-runs one attempt identity. A persisted attempt contains append-only revisions because source outcomes and operator annotations may be recorded without rewriting the initial request.

Attempt states are closed:

- `planned`;
- `running`;
- `succeeded`;
- `partial`;
- `unauthorized`;
- `forbidden`;
- `rate_limited`;
- `blocked`;
- `contract_changed`;
- `failed`.

`partial` means some raw objects committed before a later page/document failure. It never permits automatic Evidence Ledger acceptance. Every committed raw object remains inspectable.

### 7.3 No resume inference

A later command may explicitly replay the same request fingerprint or use a new bounded selector. The application does not silently infer a resume cursor from the newest failed attempt.

## 8. Immutable raw capture

### 8.1 Metadata response object

Every accepted metadata response body is persisted exactly once as immutable bytes with:

- raw-object UUID;
- attempt revision ID;
- request fingerprint;
- page/cursor identity from the reviewed contract;
- HTTP method and redacted canonical locator key;
- response status;
- response media type;
- byte length;
- SHA-256;
- source response date/header fields allowed by contract;
- fetched-at UTC;
- recorded-at UTC;
- adapter and schema-contract versions.

Headers are allowlisted. Authentication, cookie and other secret headers are never persisted.

### 8.2 Document object

Each official announcement object is a separate immutable raw document with:

- raw-document UUID;
- exact source natural announcement ID;
- exact document-object ID or contract locator key;
- parent metadata raw-object ID;
- media type;
- original source filename when supplied;
- byte length;
- SHA-256;
- fetched-at UTC;
- recorded-at UTC;
- source-declared publication/update values;
- download contract version.

The architecture does not require PDF specifically. The implementation accepts only media types explicitly listed in the owner-supplied contract package. OCR and image-to-text are excluded.

### 8.3 Immutability

Raw bytes and their fingerprints never change. A changed response or changed document under the same source natural ID creates a new raw object and an explicit collision/correction state.

## 9. Source-specific normalization

### 9.1 Normalizer boundary

The normalizer consumes only one exact raw metadata object and optional exact raw document object. It performs no network call.

The initial rule key is:

`aquantai.cninfo-disclosure-normalization.v1`

The contract must map documented source fields into:

- source natural announcement ID;
- source security code;
- source issuer text;
- title;
- publication timestamp and date;
- source update/correction timestamp when documented;
- documented announcement category codes;
- official document-object ID/locator key;
- media type;
- source contract version;
- metadata fingerprint;
- document fingerprint;
- normalization state and reason codes.

### 9.2 Normalization states

- `normalized`;
- `missing_required_field`;
- `unsupported_media_type`;
- `schema_mismatch`;
- `natural_identity_conflict`;
- `document_missing`;
- `document_fingerprint_conflict`;
- `invalid_chronology`.

No best-effort field guessing. Unknown fields may be retained only inside the immutable raw bytes, not promoted into normalized columns.

### 9.3 Text handling

v1 does not parse announcement body text for claims, metrics, company identity or sentiment. It may persist document bytes and source metadata only.

A later parser/OCR/text-extraction slice requires its own contract and cannot be hidden inside normalization.

## 10. Duplicate, correction and replay semantics

The system must classify each captured object as one of:

- `new` — unseen natural ID and fingerprints;
- `exact_raw_duplicate` — identical raw SHA-256 under the same request/page identity;
- `exact_document_duplicate` — identical document SHA-256 already linked to the same natural ID;
- `normalized_duplicate` — same normalized metadata fingerprint under another raw response;
- `natural_id_same_content` — same source natural ID and same normalized/document fingerprints;
- `natural_id_changed_content` — same source natural ID with changed metadata or document fingerprint;
- `source_declared_correction` — explicit correction/supersession relation supplied by the reviewed contract;
- `ambiguous_collision` — conflicting identity without a reviewed correction relation.

Exact duplicates are idempotent and do not create duplicate normalized revisions. Changed content appends a new normalized revision and remains unaccepted until explicit review.

No fuzzy title/text similarity is used for duplicate acceptance.

## 11. Candidate company and instrument matching

Candidate generation is deterministic and consumes normalized metadata only.

Allowed candidate methods:

1. exact source security code plus exact documented market/exchange namespace;
2. exact source security code where the reviewed contract guarantees a unique namespace;
3. exact issuer text against an explicit reviewed alias table, only when no code is available.

Candidate states:

- `single_exact_candidate`;
- `multiple_candidates`;
- `no_candidate`;
- `namespace_missing`;
- `alias_candidate`.

Each candidate freezes:

- normalized announcement revision ID;
- method and rule version;
- matched source fields;
- target Listed Instrument identity/revision when applicable;
- target Company Research identity/revision when applicable;
- reason codes;
- generated-at UTC.

Candidate generation does not accept identity and cannot mutate upstream identities or aliases.

## 12. Human review and Evidence Ledger acceptance

### 12.1 Review identity

One review identity represents the disposition of one normalized announcement identity. Review revisions are append-only and expected-latest protected.

Review decisions:

- `pending`;
- `accepted`;
- `rejected`;
- `duplicate`;
- `superseded`;
- `identity_ambiguous`;
- `source_unauthorized`;
- `blocked`;
- `failed`.

### 12.2 Acceptance input

An `accepted` decision requires:

- exact active source authorization revision;
- exact succeeded/partial acquisition attempt revision containing the raw objects;
- exact raw metadata and document IDs;
- exact normalized announcement revision;
- selected exact candidate identity or explicit manually selected target;
- exact target `ResearchCase`;
- Evidence Ledger grade and source kind;
- source title, publisher, locator key, information date and summary supplied explicitly by the reviewer;
- exact reviewer label and rationale;
- optional exact existing ClaimRevision and relation;
- information cutoff and recorded-at UTC;
- expected-latest review revision.

### 12.3 Atomic acceptance

The future implementation requires one session-scoped Evidence Ledger write primitive so that these commit or roll back together:

1. review decision revision;
2. accepted EvidenceItem;
3. optional ClaimEvidenceLink;
4. acquisition-to-evidence provenance bridge.

A partial acceptance is prohibited.

Evidence grade remains human/rule-owned under the existing Evidence Ledger contract. Acquisition metadata cannot infer or upgrade the grade.

### 12.4 Rejection and duplicate decisions

Rejection, duplicate, superseded or ambiguity decisions never delete or mutate raw capture. They remain readable under both as-of boundaries.

## 13. Time semantics

The following timestamps are distinct:

- `source_published_at` — source-declared announcement publication time;
- `source_updated_at` — optional source-declared correction/update time;
- `requested_at_utc` — local command start;
- `fetched_at_utc` — response/document receipt;
- `recorded_at_utc` — database recording boundary;
- `reviewed_at_utc` — human decision time;
- `accepted_evidence_recorded_at_utc` — Evidence Ledger write time.

Rules:

- source publication date cannot exceed the command information cutoff;
- fetched/recorded/reviewed times cannot move backward within an identity history;
- later source corrections append history and cannot rewrite earlier accepted evidence;
- exact-ID reads require both information cutoff and recorded-at UTC;
- no newest-compatible fallback is allowed.

## 14. Persistence candidate

Candidate migration: `20260722_0016_authorized_cninfo_disclosure_acquisition` after `20260722_0015`.

Exactly twelve additive tables are proposed:

1. `disclosure_sources` — stable source identity;
2. `disclosure_source_revisions` — append-only authorization/contract revisions;
3. `disclosure_acquisition_attempts` — stable attempt identity and request fingerprint;
4. `disclosure_acquisition_attempt_revisions` — append-only status/result revisions;
5. `disclosure_raw_metadata_objects` — immutable response bytes and provenance;
6. `disclosure_raw_document_objects` — immutable document bytes and provenance;
7. `disclosure_announcements` — stable source-natural announcement identity;
8. `disclosure_announcement_revisions` — deterministic normalized metadata revisions;
9. `disclosure_announcement_input_links` — exact raw metadata/document inputs;
10. `disclosure_entity_candidates` — deterministic non-accepted target candidates;
11. `disclosure_review_revisions` — append-only human disposition revisions;
12. `disclosure_evidence_links` — exact accepted EvidenceItem/optional claim-link provenance.

### 14.1 Key constraints

The implementation preflight must preserve at least:

- unique `source_key`;
- unique source revision number per source;
- unique request fingerprint per attempt identity;
- unique attempt revision number;
- unique raw SHA-256 plus source/contract scope where exact dedupe is required;
- unique source natural announcement identity within one source;
- unique announcement revision number;
- one exact normalized revision input set;
- no duplicate target candidate per method/target revision;
- one latest review revision selected only through expected-latest validation;
- one evidence provenance link per review revision and EvidenceItem.

### 14.2 Database behavior

- PostgreSQL owns production concurrency semantics.
- Supported SQLite remains deterministic for local fixtures and single-writer use.
- First-revision races must produce exactly one success and one stable conflict.
- Identity, revision and links commit in one transaction.
- raw bytes use a reviewed binary storage type compatible with both supported databases or a reviewed immutable local-object-store reference; the implementation Issue must choose one and prove backup/restore behavior.

### 14.3 Downgrade

Populated downgrade refuses before dropping any acquisition table. Empty-table downgrade may remove tables in exact reverse dependency order.

No existing table is mutated or backfilled.

## 15. Command and read surfaces

### 15.1 Candidate write commands

1. `record-disclosure-source-authorization` — local JSON only;
2. `plan-cninfo-disclosure-acquisition` — no network;
3. `acquire-cninfo-disclosures` — explicit bounded network operation;
4. `normalize-cninfo-disclosure` — local only;
5. `generate-disclosure-identity-candidates` — local only;
6. `review-disclosure-announcement` — local only;
7. `inspect-disclosure-provenance` — read only.

All writes require strict fields, dry-run where meaningful, expected-latest protection and one transaction.

### 15.2 Read-only APIs

Future APIs are exact-ID only for:

- source authorization revision;
- acquisition attempt revision;
- raw object metadata without secret headers;
- normalized announcement revision;
- candidate set;
- review revision;
- accepted evidence provenance.

No read API performs network access, retries acquisition or falls back to another revision.

### 15.3 UI candidate

A later implementation may add a Chinese-first read/review surface under Research Feed. It must visually separate:

- raw source facts;
- deterministic normalized fields;
- candidate identity;
- human review decision;
- accepted Evidence Ledger state.

It must not display attention scores, sentiment, investment interpretation or automatic priority changes.

## 16. Golden path

The offline-replayable production-realistic fixture must prove:

1. one `active` CNINFO source authorization revision with a non-secret contract fingerprint;
2. one dry-run plan for an exact source security code and seven-day publication window;
3. one fixture transport response matching the reviewed metadata schema;
4. one immutable raw metadata object;
5. one fixture official document object and immutable SHA-256;
6. one normalized announcement identity/revision;
7. one exact Listed Instrument and Company Research candidate;
8. one explicit human `accepted` review;
9. one existing ResearchCase, accepted EvidenceItem and optional existing ClaimRevision link committed atomically;
10. exact provenance readback under both as-of boundaries;
11. a repeated identical capture returning exact-duplicate state without duplicate normalized/evidence records;
12. zero live network during the fixture demo.

The fixture may use synthetic or redacted data shaped exactly like the owner-supplied contract. It must not contain credentials or confidential contract material.

## 17. Primary failure path

The primary failure path is a contract or access mismatch before accepted-state mutation.

The command must fail closed and persist only credential-safe attempt diagnostics when any of these occurs:

- authorization revision is missing, non-active or expired;
- contract package fingerprint/version is not the implementation-approved value;
- requested host or endpoint contract key is not allowlisted;
- remote access confirmation is absent;
- request exceeds date/page/item/document limits;
- source returns `401`, `403`, `429`, access interstitial or equivalent denial;
- redirect target is unreviewed;
- response media type/schema/natural ID is inconsistent;
- document bytes fail length/fingerprint validation;
- publication chronology exceeds cutoff;
- identity candidate is ambiguous;
- acceptance expected-latest check fails;
- Evidence Ledger transaction cannot commit completely.

No alternate source, public page, browser, cached unbound object or newer compatible-looking record is selected automatically.

## 18. Testing contract

### 18.1 Source and transport

- active/pending/suspended/retired authorization behavior;
- contract fingerprint/version mismatch;
- host allowlist and redirect rejection;
- dry-run performs zero network;
- explicit confirmation required;
- pagination/order/request-fingerprint determinism;
- request ceilings;
- timeout and one-transient-retry behavior;
- `401`, `403`, `429`, blocked and schema-drift states;
- credential and header redaction.

### 18.2 Raw and normalized state

- immutable metadata/document bytes;
- SHA-256 and length validation;
- exact duplicate idempotency;
- same-natural-ID changed-content append behavior;
- source-declared correction;
- ambiguous collision;
- parser/normalizer version provenance;
- unsupported media and missing fields;
- no OCR or text inference.

### 18.3 Identity and acceptance

- exact-code candidate;
- missing namespace and multiple candidates;
- alias candidate remains non-accepted;
- human acceptance fields and chronology;
- EvidenceItem plus optional claim link atomic commit;
- rollback leaves no partial accepted state;
- expected-latest conflict;
- exact provenance readback and no fallback.

### 18.4 Database and lifecycle

- PostgreSQL first-revision concurrency;
- SQLite deterministic fixture behavior;
- migration upgrade from `0015`;
- empty downgrade success;
- populated downgrade refusal before any drop;
- imports/startup/ordinary reads/CI/demo contain no hidden network.

### 18.5 Optional contract smoke test

A live contract smoke test, if later authorized, must be:

- separately marked;
- disabled by default;
- excluded from ordinary CI;
- explicitly invoked by the owner;
- bounded to a minimal read-only request;
- credential-redacted;
- incapable of Evidence Ledger acceptance.

## 19. Observability and error contract

Persisted diagnostics use closed reason codes and bounded text. Candidate codes include:

- `source_authorization_missing`;
- `source_authorization_inactive`;
- `contract_version_mismatch`;
- `credential_profile_missing`;
- `remote_confirmation_required`;
- `request_bounds_invalid`;
- `host_not_allowed`;
- `redirect_not_allowed`;
- `source_unauthorized`;
- `source_forbidden`;
- `source_rate_limited`;
- `source_blocked`;
- `transport_timeout`;
- `response_schema_mismatch`;
- `response_media_type_invalid`;
- `source_identity_missing`;
- `raw_fingerprint_conflict`;
- `identity_ambiguous`;
- `chronology_invalid`;
- `acceptance_conflict`.

Raw response bodies are not placed in user-facing errors. Secrets and private headers are never logged.

## 20. Security and privacy

- No user personal data is required by the announcement contract beyond account credentials held outside persistence.
- Credential access is least-privilege and source-specific.
- The adapter cannot call arbitrary URLs supplied by the user.
- Source locators are contract keys or validated official locators, not generic fetch URLs.
- Downloaded document bytes are treated as untrusted input and never executed.
- No archive extraction, macro execution, embedded link following or active-content rendering.
- UI rendering uses safe text and explicit download/open behavior.

## 21. Stop conditions

Implementation must not start if any condition remains true:

1. official documentation and permitted automated access are not demonstrated;
2. retention/local-storage rights are unclear;
3. only undocumented website endpoints are available;
4. credentials require browser session impersonation;
5. CAPTCHA, stealth tooling, proxy rotation or rate-limit evasion would be required;
6. stable announcement/document identity is absent;
7. response fixtures cannot be created without confidential material or secrets;
8. candidate identity must depend on fuzzy text or LLM inference;
9. Evidence Ledger atomic acceptance ownership is unresolved;
10. more than one source or a generic Provider framework is required;
11. source body-text extraction/OCR is needed for the first useful path;
12. implementation would automatically score, alert or change candidate state.

When a stop condition is met, record the blocked decision and return to source selection. Do not substitute another acquisition method.

## 22. Locked exclusions

No production implementation in this PR; no migration; no dependency change; no credential; no live request; no public-page scraping; no browser automation; no browser-session replay; no reverse-engineered endpoint; no scheduler; no background worker; no webhook; no multiple source; no news, social-media or research-report acquisition; no OCR; no announcement-body claim extraction; no generic Provider registry; no fuzzy identity acceptance; no automatic EvidenceItem, claim, grade or accepted identity; no AI-owned accepted state; no market-attention score; no alerts; no candidate rescore; no recommendation; no target price; no expected return; no portfolio; no broker or trading; no release, tag or version change.

## 23. Definition of Ready

This architecture is ready for fixed-head review when:

- the source decision is exactly licensed/documented CNINFO data service;
- undocumented public endpoints and scraping are explicitly rejected;
- implementation is gated on the complete owner-supplied contract package;
- source, attempt, raw, normalized, candidate, review and Evidence Ledger ownership are separate;
- exact request ceilings, time semantics, duplicate behavior and failure states are closed;
- the twelve-table migration candidate and atomic acceptance boundary are explicit;
- the offline production-realistic golden path and primary failure path are reachable;
- tests prove zero hidden network by default;
- stop conditions prevent implementation without source entitlement;
- the base-to-head diff contains only the task snapshot, this document and the bounded architecture-baseline synchronization.

Required fixed-head approval phrase:

`AUTHORIZED CNINFO DISCLOSURE ACQUISITION PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`
