# Evidence Ingestion v1 Architecture Preflight

## 1. Decision status

This document defines the Definition of Ready for the first Evidence Ingestion implementation slice.

- Governing Issue: #154.
- Required base: `a945b111cf97fa93d8257d6f5d495a4a842af3f2`.
- Roadmap: Issue #137, Slice 4.
- Work type: Architecture Task.
- Release remains `0.2.0`.
- This document does not authorize implementation until independently approved at one fixed HEAD and merged.

### Accepted preflight direction

The first slice is deliberately offline-first:

```text
user-supplied official CNINFO announcement PDF
  -> immutable local raw capture
  -> deterministic CNINFO PDF normalization
  -> exact duplicate and natural-identity checks
  -> deterministic company candidates
  -> explicit human review
  -> accepted EvidenceItem
  -> optional explicit link to one existing claim revision
```

No live crawling, browser automation, scheduler, API adapter, feed adapter or hidden network request is part of v1.

This boundary is selected because source access controls, terms, robots rules and anti-bot behavior are source contracts. They are not obstacles that the application is allowed to bypass.

## 2. Existing accepted facts

### Evidence Ledger

The accepted Evidence Ledger already owns:

- `ResearchCase` and append-only case revisions;
- `EvidenceItem`;
- `Claim` and append-only claim revisions;
- `ClaimEvidenceLink`;
- cutoff and recorded-UTC validation;
- accepted evidence grades, source kinds and relations;
- append-only mutation protection.

`EvidenceItem` currently stores:

- `case_id`;
- `evidence_grade`;
- `source_kind`;
- source title, publisher/author and locator;
- information date and recorded UTC;
- summary;
- optional content fingerprint;
- optional superseded evidence ID.

The existing unique boundary is `(case_id, content_fingerprint)`. Evidence Ingestion must not change the meaning of an accepted `EvidenceItem` merely to store acquisition workflow state.

### Existing evidence command boundary

`EvidenceLedgerCommandService.add_evidence` validates accepted grade, source kind, chronology, case identity, fingerprint uniqueness and optional supersession, then inserts one append-only `EvidenceItem` in one transaction.

It does not currently create an evidence item, optional claim link and ingestion-review provenance in one shared transaction. The implementation slice therefore requires a small evidence-ledger-owned session-scoped write primitive, described in section 12.

### Market-data ingestion is a different domain

The existing market-data `IngestionRun` owns complete-snapshot market-data attempts, Provider series, dataset cutoffs and normalized market rows.

Document ingestion must not reuse `IngestionRun` because:

- an announcement is an immutable document, not a complete market-data snapshot;
- source authorization and anti-bot state differ from Provider-series state;
- document normalization can be retried with a new parser version without changing the raw bytes;
- human identity review and accepted Evidence Ledger creation have no equivalent in market-data ingestion.

## 3. First source registration

### Source identity

The first source registration is:

- `source_key`: `cninfo-company-announcement`;
- display name: `巨潮资讯上市公司公告`;
- operator: `深圳证券信息有限公司 / CNINFO`;
- source class: `official_disclosure_platform`;
- accepted document class: `listed_company_announcement_pdf`;
- Evidence Ledger source kind after acceptance: `filing`;
- allowed acquisition mode in v1: `offline_file` only.

The source registration does not imply that every file carrying a CNINFO-looking name is authentic. In v1, authenticity is **user asserted and human reviewed**, not remotely verified by the application.

### Source scope

Included:

- public listed-company announcement PDFs presented as originating from CNINFO;
- one file per capture command;
- explicit source locator and announcement metadata supplied by the user.

Excluded:

- news articles;
- research reports;
- social-media or community posts;
- interactive Q&A;
- market-price datasets;
- data-browser exports;
- bulk archives;
- other exchanges or websites under the same adapter;
- multiple-source fallback.

### Authorization state

The source has revisioned authorization state:

- `active`: offline import of the accepted document class is allowed;
- `suspended`: new imports fail closed, existing raw and accepted records remain readable;
- `retired`: no new imports, history remains readable;
- `pending_review`: not usable by production commands.

A source revision records the review date and a short human-authored authorization basis. It must not persist credentials, cookies, private tokens or raw terms text.

## 4. Anti-bot and access-control contract

### Absolute prohibitions

The system must not implement or invoke:

- CAPTCHA solving, outsourcing or bypass;
- stealth browser or browser-fingerprint evasion;
- proxy rotation, residential proxy use or IP cycling to evade controls;
- login/session impersonation;
- cookie theft or reuse of an unrelated browser session;
- rate-limit evasion;
- robots or terms-of-use bypass;
- production dependence on unpublished/private endpoints discovered by reverse engineering;
- automatic fallback from one source, domain or acquisition mode to another.

### Fail-closed behavior

For any future network adapter, the following are terminal attempt outcomes, not retry invitations beyond the reviewed policy:

- HTTP `403`;
- HTTP `429` after the bounded reviewed retry policy;
- CAPTCHA or anti-bot interstitial;
- login wall;
- robots denial;
- source terms or endpoint contract materially changed;
- TLS or hostname mismatch;
- unexpected redirect outside the registered domain allowlist.

The attempt becomes `blocked`. The error retains only safe fields such as source key, HTTP status, retry-after value and a stable error code. It never stores credentials, cookies, full headers or raw connection secrets.

### Future HTTP minimum contract

Not implemented in v1, but any later source-specific network preflight must require:

- an official API/feed where available before public-page HTML;
- explicit allowed hostnames and paths;
- an honest application User-Agent;
- bounded concurrency;
- a source-specific minimum request interval;
- connect/read timeouts;
- `ETag` and `Last-Modified` conditional requests when supported;
- local cache reuse;
- `Retry-After` handling;
- bounded exponential backoff with jitter;
- no source fallback;
- explicit `blocked` status.

Approval of this document does not approve that future HTTP contract.

## 5. Acquisition modes

The source model recognizes acquisition modes so that later work cannot silently change how data arrived:

| Mode | v1 status | Meaning |
| --- | --- | --- |
| `offline_file` | approved | User explicitly imports one local file and supplies source metadata |
| `official_api` | disabled | Requires separate source/API authorization and credentials review |
| `official_feed` | disabled | Requires separate feed contract |
| `public_http` | disabled | Requires terms/robots/rate-limit review |
| `browser` | prohibited | Not an accepted production acquisition mode |

No command may silently change modes.

## 6. Proposed persistent model

All IDs are UUIDs unless stated otherwise. All recorded timestamps are timezone-aware UTC. Accepted history is append-only.

### 6.1 `evidence_sources`

Stable source identity.

| Field | Contract |
| --- | --- |
| `id` | primary key |
| `source_key` | unique, stable, `cninfo-company-announcement` for v1 |
| `created_at_utc` | immutable identity creation time |

### 6.2 `evidence_source_revisions`

Append-only authorization and source-contract revisions.

| Field | Contract |
| --- | --- |
| `id` | primary key |
| `source_id` | FK to `evidence_sources` |
| `revision_no` | positive, unique per source |
| `display_name` | human-readable source name |
| `operator_name` | source operator |
| `source_class` | `official_disclosure_platform` in v1 |
| `document_class` | `listed_company_announcement_pdf` in v1 |
| `allowed_acquisition_mode` | `offline_file` in v1 |
| `authorization_status` | `pending_review / active / suspended / retired` |
| `authorization_basis` | short, credential-safe human note |
| `reviewed_at_utc` | source review time |
| `recorded_at_utc` | revision record time |
| `supersedes_revision_id` | previous source revision or null |

Constraints:

- unique `(source_id, revision_no)`;
- exactly one supersession chain;
- source revision is immutable after insert;
- a command may import only through the latest `active` source revision;
- a later suspension does not rewrite prior captures.

### 6.3 `evidence_capture_attempts`

One immutable terminal record per user-initiated import attempt. The offline command is short-lived, so v1 does not need a mutable `pending` row.

| Field | Contract |
| --- | --- |
| `id` | primary key |
| `source_revision_id` | exact authorization revision used |
| `acquisition_mode` | `offline_file` |
| `attempt_status` | `succeeded / exact_duplicate / natural_key_collision / blocked / failed` |
| `requested_at_utc` | command start time |
| `completed_at_utc` | terminal time |
| `original_filename` | sanitized display name, not a persistent local path |
| `source_locator` | required HTTPS CNINFO locator metadata |
| `source_document_id` | required announcement identifier text |
| `declared_publication_date` | user-supplied official publication date |
| `declared_security_code` | exact source code text |
| `declared_exchange` | explicit exchange text; no inference |
| `declared_issuer_name` | user-supplied issuer text |
| `raw_object_id` | populated for succeeded or duplicate attempts |
| `duplicate_of_raw_object_id` | populated for exact duplicate |
| `error_code` | stable safe code or null |
| `error_summary` | bounded safe summary or null |

The attempt never stores the user machine path, credentials, cookies or full stack trace.

### 6.4 `evidence_raw_objects`

Immutable raw bytes.

| Field | Contract |
| --- | --- |
| `id` | primary key |
| `source_id` | stable source identity |
| `raw_sha256` | lowercase 64-character SHA-256 |
| `media_type` | `application/pdf` in v1 |
| `byte_length` | positive and at most 25 MiB in v1 |
| `original_filename` | sanitized display metadata |
| `raw_bytes` | PostgreSQL BYTEA / SQLite BLOB |
| `source_locator` | exact accepted locator metadata |
| `source_document_id` | source announcement identifier |
| `declared_publication_date` | separate from import time |
| `imported_at_utc` | local import completion time |
| `recorded_at_utc` | persistence record time |

Constraints and indexes:

- unique `(source_id, raw_sha256)`;
- index `(source_id, source_document_id)` without assuming uniqueness;
- index `(declared_publication_date, recorded_at_utc)`;
- rows are append-only and cannot be updated or deleted through ordinary ORM paths.

A repeated byte-identical file creates a new `exact_duplicate` attempt pointing to the existing raw object. It does not create a second raw row.

A repeated `source_document_id` with different bytes becomes `natural_key_collision` and requires review. It is not silently classified as correction or duplicate.

### 6.5 `evidence_normalized_documents`

Immutable parser/normalizer output.

| Field | Contract |
| --- | --- |
| `id` | primary key |
| `raw_object_id` | exact raw object |
| `parser_key` | `pypdf` in v1 |
| `parser_version` | exact installed version |
| `normalizer_key` | `cninfo-announcement-pdf` |
| `normalizer_version` | explicit application contract version |
| `normalization_status` | `normalized / text_unavailable / parse_failed` |
| `announcement_id` | normalized source identifier |
| `title` | normalized title |
| `issuer_name` | normalized issuer text |
| `security_code` | normalized exact security code text |
| `exchange` | explicit exchange text |
| `publication_date` | source information date |
| `normalized_text` | nullable UTF-8 text |
| `normalized_sha256` | nullable canonical-content fingerprint |
| `page_count` | non-negative |
| `text_char_count` | non-negative |
| `recorded_at_utc` | normalization record time |
| `supersedes_normalized_document_id` | prior normalizer result or null |

Constraints:

- unique `(raw_object_id, normalizer_key, normalizer_version)`;
- a new parser or normalizer version creates a new row;
- old normalized rows are never overwritten;
- `normalized_sha256` is required only for `normalized`;
- `normalized_text` is null for `text_unavailable` and `parse_failed`;
- parser errors are summarized safely and do not include raw PDF bytes.

### 6.6 `evidence_entity_candidates`

Deterministic candidate proposals. A candidate is not accepted identity.

| Field | Contract |
| --- | --- |
| `id` | primary key |
| `normalized_document_id` | exact normalized row |
| `candidate_kind` | `company_research / research_case / unresolved_company` |
| `candidate_target_id` | nullable exact UUID |
| `match_method` | `exact_security_code / exact_issuer_alias / manual_candidate` |
| `matched_source_value` | exact value used |
| `candidate_status` | `exact / ambiguous / unresolved` |
| `matcher_version` | deterministic rule version |
| `explanation` | bounded deterministic explanation |
| `recorded_at_utc` | candidate record time |

V1 automatic candidates are limited to exact company matches:

1. explicit source security code plus explicit exchange is normalized to the project stock-code format;
2. exact persisted `Stage2CompanyResearch.stock_code` matches are returned;
3. all matching research identities remain visible;
4. multiple matches are `ambiguous`;
5. no first-row selection occurs.

Exact issuer aliases may be used only from a separately reviewed deterministic alias table or configuration introduced by the implementation task. Name similarity and LLM matching are excluded.

There is no automatic industry candidate in v1 because CNINFO announcement metadata does not provide an accepted industry-map identity. A reviewer may manually choose an existing `ResearchCase` or industry context, and that choice is recorded as human selection rather than machine inference.

### 6.7 `evidence_review_decisions`

Append-only human review and acceptance provenance.

| Field | Contract |
| --- | --- |
| `id` | primary key |
| `normalized_document_id` | reviewed document |
| `decision_no` | positive, unique per document |
| `decision` | `deferred / accepted / rejected / duplicate` |
| `selected_candidate_id` | optional exact candidate |
| `case_id` | required for accepted evidence |
| `reviewer_label` | explicit local human label, not authentication |
| `decision_note` | bounded human note |
| `evidence_grade` | required explicit grade for acceptance |
| `source_kind` | fixed `filing` for accepted v1 records |
| `accepted_summary` | required human-authored EvidenceItem summary |
| `evidence_id` | created EvidenceItem or null |
| `claim_revision_id` | optional existing claim revision |
| `relation` | optional `supports / contradicts / context` |
| `claim_evidence_link_id` | created link or null |
| `recorded_at_utc` | decision time |
| `supersedes_decision_id` | previous deferred decision or null |

Rules:

- `deferred` may be superseded by a later decision;
- `accepted`, `rejected` and `duplicate` are terminal;
- only one terminal decision is allowed per normalized document;
- acceptance requires one explicit case ID and evidence grade;
- optional claim revision must belong to the selected case;
- optional relation is required when a claim revision is supplied;
- the decision, EvidenceItem and optional ClaimEvidenceLink commit or roll back together;
- rejection or duplicate decisions never remove raw or normalized rows.

## 7. Raw capture validation

The offline import command treats input as untrusted local bytes.

Required prechecks:

- source revision is latest and `active`;
- acquisition mode is exactly `offline_file`;
- file exists and is a regular file;
- byte length is between 1 byte and 25 MiB;
- MIME sniff and PDF header agree with `application/pdf`;
- source locator is HTTPS and belongs to an approved CNINFO hostname allowlist recorded in implementation configuration;
- source document ID, publication date, security code, exchange and issuer are explicit;
- local path is never persisted;
- SHA-256 is computed before database insert.

PDF safety boundary:

- no embedded script or action is executed;
- encrypted/password-protected PDF is rejected;
- embedded attachments are not extracted;
- external references are not fetched;
- maximum page count is 1,000;
- maximum normalized text length is 2,000,000 characters;
- normalization runs in a bounded subprocess with a wall-clock timeout;
- timeout or parser crash becomes `parse_failed` and does not damage the parent process.

## 8. Normalization contract

### Dependency

The implementation candidate is:

`pypdf>=6.14,<7`

Purpose:

- pure local PDF parsing;
- embedded-text extraction only;
- no network;
- no OCR;
- no image-to-text service.

The implementation task must update `pyproject.toml`, record the selected exact resolved version in validation output, and include license/security review notes. No dependency is added by this preflight.

### Text extraction

For each page:

1. extract embedded text using the reviewed parser call;
2. normalize Unicode to NFC;
3. convert CRLF/CR to LF;
4. strip trailing whitespace per line;
5. remove NUL characters;
6. collapse runs of more than two blank lines to two;
7. join pages with one deterministic page separator;
8. enforce the text-length limit.

The normalizer does not paraphrase, summarize, translate or infer missing content.

If no meaningful embedded text exists, status is `text_unavailable`. OCR is not attempted.

### Metadata

The user-supplied announcement ID, source locator, publication date, security code, exchange and issuer are retained separately from parser-derived text.

The implementation may compare user-supplied title/issuer/code against extractable first-page text and expose mismatches. A mismatch is a review flag, not an automatic correction.

## 9. Fingerprints and duplicate semantics

### Raw fingerprint

```text
raw_sha256 = SHA256(exact file bytes)
```

This identifies byte-exact duplicates only.

### Normalized fingerprint

For a successfully normalized document, build canonical UTF-8 JSON with sorted keys and no insignificant whitespace from:

- source key;
- announcement ID;
- normalized title;
- issuer name;
- security code;
- exchange;
- publication date ISO text;
- normalized document text;
- normalizer key and version.

Then:

```text
normalized_sha256 = SHA256(canonical UTF-8 JSON)
```

The normalizer version is included so changed rules do not pretend to be the same derivation.

### Accepted EvidenceItem fingerprint

- `normalized` document: `norm-sha256:<normalized_sha256>`;
- `text_unavailable` document accepted after manual raw review: `raw-sha256:<raw_sha256>`.

Both fit the existing 128-character field.

A `parse_failed` document cannot be accepted.

### Duplicate states

- **Exact duplicate:** same source and raw SHA-256. Reuse raw object; record duplicate attempt.
- **Normalized duplicate:** different bytes but same normalized fingerprint. Human marks duplicate or selects a supersession relation; no silent collapse.
- **Natural-key collision:** same source announcement ID but different bytes. Human review required.
- **Correction/supersession:** reviewer explicitly accepts a new EvidenceItem with `supersedes_evidence_id` in the same case.
- **Near duplicate:** not computed in v1. No fuzzy text threshold.

## 10. Candidate matching boundary

Candidate generation is deterministic D1/D2 support metadata, not accepted evidence identity.

### Company candidate rule

Inputs:

- explicit six-digit security code;
- explicit exchange;
- matcher version.

Rule:

1. normalize the exact code/exchange into the existing stock-code format;
2. query exact `Stage2CompanyResearch.stock_code` values only;
3. preserve every matching `company_research_id`, its source and case ID;
4. zero matches -> unresolved;
5. one match -> exact candidate;
6. more than one match -> ambiguous candidates.

No company name similarity is used.

### Issuer alias rule

A future deterministic alias list may propose candidates only when:

- alias entries are explicit and reviewed;
- alias version is recorded;
- exact normalized string equality is used;
- all matches remain visible.

The first implementation may omit aliases entirely.

### Industry boundary

No automatic industry candidate is generated in v1. Industry identity requires a separate deterministic taxonomy/mapping contract or explicit human choice.

### LLM boundary

An LLM may not run during capture, normalization, candidate matching or acceptance. A later guarded-AI slice may propose candidates only as non-accepted suggestions behind explicit review.

## 11. Review and acceptance workflow

### Derived workflow states

```text
source inactive
  -> blocked

active source + valid offline file
  -> raw captured
  -> normalized | text_unavailable | parse_failed
  -> awaiting_review
  -> deferred | rejected | duplicate | accepted
```

No transition is hidden.

### Acceptance input

The reviewer must explicitly provide or confirm:

- normalized document ID;
- target `case_id`;
- selected company candidate or explicit manual selection;
- evidence grade;
- source kind `filing`;
- human-authored summary;
- optional superseded evidence ID;
- optional existing claim revision ID;
- optional relation and link note;
- reviewer label;
- recorded UTC defaults to current UTC but is visible.

### Acceptance projection

Accepted `EvidenceItem` fields are:

| EvidenceItem field | Source |
| --- | --- |
| `case_id` | explicit reviewer selection |
| `evidence_grade` | explicit reviewer value; never automatic |
| `source_kind` | fixed `filing` under this source contract |
| `source_title` | normalized title or explicit metadata title |
| `publisher_or_author` | issuer name plus CNINFO source attribution |
| `source_locator` | exact user-supplied CNINFO locator |
| `information_date` | publication date |
| `recorded_at_utc` | acceptance time |
| `summary` | explicit reviewer-authored summary |
| `content_fingerprint` | normalized or raw fingerprint contract |
| `supersedes_evidence_id` | optional explicit same-case evidence ID |

The raw file, normalized text or source metadata does not automatically determine evidence grade.

### Atomicity

The acceptance command owns one database transaction:

1. lock or otherwise guard the normalized document decision boundary;
2. confirm there is no terminal decision;
3. validate source, raw and normalized provenance;
4. validate case and optional claim revision;
5. insert accepted EvidenceItem through the Evidence Ledger write boundary;
6. optionally insert ClaimEvidenceLink;
7. insert terminal review decision referencing the created IDs;
8. commit once.

Any error rolls back all three accepted records.

## 12. Evidence Ledger write-boundary change

A later implementation may not call `EvidenceLedgerCommandService.add_evidence` and then create review/link rows in separate transactions.

The approved design is to extract a domain-local session-scoped primitive, for example:

```text
industry_alpha/evidence_ledger_write_boundary.py
```

Responsibilities:

- validate and insert one EvidenceItem using an existing SQLAlchemy session;
- validate and insert an optional ClaimEvidenceLink using the same session;
- perform no commit;
- remain owned by the Evidence Ledger domain;
- preserve existing validation and error semantics.

`EvidenceLedgerCommandService.add_evidence` is then characterized and refactored to call that primitive inside its existing transaction, with no public behavior change.

The Evidence Ingestion acceptance service calls the same primitive inside the larger acceptance transaction.

This is not a generic command framework.

## 13. Command surface

V1 is CLI-first and user-initiated. No background worker or scheduler is included.

Candidate commands:

```text
python -m scripts.evidence_ingestion source-show
python -m scripts.evidence_ingestion import-offline ...
python -m scripts.evidence_ingestion normalize --raw-object-id ...
python -m scripts.evidence_ingestion candidates --normalized-document-id ...
python -m scripts.evidence_ingestion review-show --normalized-document-id ...
python -m scripts.evidence_ingestion accept ...
python -m scripts.evidence_ingestion reject ...
python -m scripts.evidence_ingestion defer ...
python -m scripts.evidence_ingestion inspect --capture-attempt-id ...
```

Rules:

- every mutation requires explicit IDs and arguments;
- no command selects the first row;
- no command scans a directory unless a later task authorizes batch behavior;
- no command accesses the network;
- output is strict JSON plus concise human-readable errors;
- credentials and raw database errors are redacted;
- read commands expose exact IDs, fingerprints, parser/normalizer versions and UTC timestamps.

No FastAPI mutation endpoint or UI is included in the first implementation. A later Product Task may add a local review UI over the accepted command/query contracts.

## 14. Error vocabulary

Stable domain errors include:

- `source_not_active`;
- `acquisition_mode_not_allowed`;
- `invalid_source_locator`;
- `unsupported_media_type`;
- `file_too_large`;
- `encrypted_pdf`;
- `exact_duplicate`;
- `natural_key_collision`;
- `pdf_parse_failed`;
- `text_unavailable`;
- `normalizer_version_conflict`;
- `candidate_unresolved`;
- `candidate_ambiguous`;
- `terminal_review_exists`;
- `case_not_found`;
- `claim_revision_not_found`;
- `claim_case_mismatch`;
- `chronology_violation`;
- `evidence_fingerprint_conflict`;
- `blocked_source_contract`;
- `storage_failure`.

User errors contain no local absolute path, raw SQL, database URL, cookies, headers, secrets or stack trace.

## 15. Chronology and cutoff

The system keeps separate:

- source publication/information date;
- local import time;
- normalization recorded UTC;
- human review/acceptance recorded UTC.

Rules:

- publication date may not be later than acceptance recorded UTC date;
- raw imported time may not be later than its recorded UTC;
- normalized recorded UTC may not precede raw recorded UTC;
- review recorded UTC may not precede normalized recorded UTC;
- accepted EvidenceItem information date equals publication date;
- accepted EvidenceItem recorded UTC equals acceptance time;
- later parser output never rewrites an earlier accepted EvidenceItem;
- a corrected disclosure is a new raw object and, if accepted, a new EvidenceItem with explicit supersession.

## 16. Append-only and mutation policy

Append-only ordinary-path protection applies to:

- source revisions;
- raw objects;
- normalized documents;
- entity candidates;
- review decisions;
- accepted EvidenceItem and links.

Capture attempts are inserted terminally in v1 and are also immutable.

No ordinary command deletes raw files, normalized text, decisions or accepted evidence.

Administrative data-retention deletion is outside v1 and would require a separate Architecture Task because it changes audit history.

## 17. Storage, privacy and retention

- Raw PDF bytes are stored in the configured local database for v1.
- No cloud object store is introduced.
- No local source path is persisted.
- Original filename is sanitized and treated as untrusted display metadata.
- Maximum raw size is 25 MiB.
- Raw bytes are returned only through an explicit local inspection/export command, not ordinary list APIs.
- Logs include IDs and safe error codes, not raw content.
- Database backup is the raw-retention backup mechanism for v1.
- Source suspension or application rollback does not remove existing bytes.

## 18. Migration and rollback

### Migration

One Alembic migration may introduce the six model groups described above and the append-only ORM registration.

Migration ordering:

1. source identity and source revisions;
2. raw objects;
3. capture attempts;
4. normalized documents;
5. entity candidates;
6. review decisions and acceptance FKs;
7. indexes and partial uniqueness constraints supported by PostgreSQL/SQLite.

The implementation task must generate and inspect PostgreSQL and SQLite DDL.

### Rollback

Preferred rollback is application rollback while leaving new tables intact.

A database downgrade must fail closed when any accepted review decision exists, because dropping the ingestion tables would destroy provenance for surviving EvidenceItems. With no accepted decisions, the downgrade may drop the new tables in reverse order.

No downgrade may delete accepted Evidence Ledger rows.

## 19. Candidate implementation files

The later implementation Issue may authorize only a bounded set similar to:

New:

- `industry_alpha/evidence_ingestion_models.py`
- `industry_alpha/evidence_ingestion_contracts.py`
- `industry_alpha/evidence_ingestion_repository.py`
- `industry_alpha/evidence_ingestion_commands.py`
- `industry_alpha/evidence_ingestion_query.py`
- `industry_alpha/evidence_ingestion_cninfo.py`
- `industry_alpha/evidence_ledger_write_boundary.py`
- `scripts/evidence_ingestion.py`
- one Alembic migration;
- focused tests and synthetic PDF fixtures;
- matching `.codex/tasks/issue-<n>-evidence-ingestion-v1.md`.

Modify:

- `industry_alpha/commands.py` only to use the characterized Evidence Ledger write primitive;
- `industry_alpha/models.py` only if needed to register append-only ingestion models through a neutral model tuple or listener;
- `pyproject.toml` for the reviewed PDF dependency;
- package discovery only if required by actual module layout.

Not included:

- `backend/main.py`;
- new FastAPI mutation routes;
- browser tooling;
- scheduler/worker infrastructure;
- market-data Provider modules.

The exact implementation file list must be locked by the later Product/Architecture implementation Issue.

## 20. Required tests

### Source and anti-bot boundaries

- inactive source blocks import;
- acquisition mode other than `offline_file` is rejected;
- source revision is frozen on each attempt;
- a simulated future blocked response maps to `blocked_source_contract` and invokes no bypass/fallback adapter;
- imports, startup, tests, CI and fixture demos make zero external network requests.

### Raw capture

- bytes round-trip exactly;
- SHA-256 matches exact bytes;
- exact duplicate reuses raw object;
- same announcement ID with changed bytes becomes natural-key collision;
- invalid MIME, encrypted PDF and oversized file fail safely;
- local absolute path is absent from database and output.

### Normalization

- parser/normalizer versions are stored;
- Unicode/line-ending rules are deterministic;
- repeated normalization under one version is idempotent;
- new normalizer version appends a row;
- textless PDF becomes `text_unavailable`;
- malformed PDF becomes `parse_failed`;
- no OCR or external request occurs;
- page and text limits are enforced.

### Candidate matching

- exact code/exchange produces all exact company-research candidates;
- zero matches remain unresolved;
- multiple matches remain ambiguous;
- no first-row selection;
- company-name similarity does not create a candidate;
- no automatic industry candidate.

### Review and acceptance

- deferred decision can be superseded;
- terminal decision cannot be replaced;
- explicit grade and case are required;
- claim revision must belong to selected case;
- acceptance creates EvidenceItem, optional link and decision atomically;
- injected failure rolls all records back;
- content fingerprint follows normalized/raw rule;
- duplicate accepted fingerprint in one case fails closed;
- supersession requires same case;
- rejection preserves raw and normalized history.

### Chronology and databases

- publication/import/normalization/review chronology is enforced;
- later-information leakage is rejected;
- PostgreSQL constraints and indexes compile and execute;
- supported SQLite fixture behavior remains deterministic;
- migration upgrade succeeds;
- downgrade refuses when accepted decisions exist;
- existing full pytest and fixture demo remain green.

### Fixture policy

Tests use a small synthetic or project-authored PDF fixture with no live download and no copyrighted third-party announcement text. The fixture may contain a fictional issuer, code and announcement.

## 21. Locked exclusions

The first implementation must not include:

- live CNINFO scraping;
- unofficial/private endpoint use;
- browser automation;
- CAPTCHA handling;
- proxy rotation;
- scheduler or background worker;
- directory/bulk ingestion;
- multiple sources;
- news-media, research-report, social-media or market-price ingestion;
- OCR or image recognition;
- external AI service;
- automatic accepted company or industry identity;
- automatic EvidenceItem creation without review;
- automatic claim creation;
- automatic evidence grade;
- AI promotion to D0, D1 or D2;
- mutation of accepted history;
- Canonical Price or Comparison Eligibility;
- ranking, recommendation, alerts, portfolio or trading state;
- release/version change.

## 22. Stop conditions

Implementation must not start, or must stop, if:

- the source authorization basis cannot be documented;
- public offline retention of the selected document class is not acceptable for personal local research;
- the required flow would need anti-bot bypass;
- source locator and document identity cannot be represented deterministically;
- raw bytes cannot be retained immutably;
- PDF parsing cannot be bounded safely;
- candidate identity remains silently inferred;
- evidence grade ownership is ambiguous;
- acceptance cannot be atomic with optional claim linkage;
- migration rollback would delete accepted evidence;
- tests require live network access;
- implementation expands beyond one official source and one offline document class.

## 23. Definition of Ready checklist

The later implementation Issue may be created only after independent approval confirms:

- one source and one document class are selected;
- v1 acquisition mode is offline-only;
- anti-bot bypass is explicitly prohibited;
- source revisions and blocked states are defined;
- raw bytes, fingerprints and chronology are exact;
- source-specific normalization is deterministic and versioned;
- OCR is excluded;
- duplicate/correction states are distinct;
- company candidates are exact and non-accepted;
- industry auto-matching is excluded;
- human review is explicit and append-only;
- accepted EvidenceItem fields have exact owners;
- optional claim linkage is atomic;
- Evidence Ledger public behavior remains compatible;
- schema, migration, dependency, command surface and file candidates are bounded;
- tests, rollback, exclusions and stop conditions are explicit;
- no implementation has been smuggled into the preflight.

Independent approval must use:

`DEFINITION OF READY APPROVED at fixed head <HEAD_SHA>`
