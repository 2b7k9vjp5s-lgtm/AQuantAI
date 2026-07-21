# Issue #154 — Evidence Ingestion v1 Architecture Preflight

## Authority

- Work type: Architecture Preflight / Definition of Ready only.
- Required base: `a945b111cf97fa93d8257d6f5d495a4a842af3f2`.
- Branch: `docs/evidence-ingestion-preflight`.
- Related roadmap: Issue #137, Slice 4.
- Governing Issue: #154.
- Release remains `0.2.0`.
- No implementation, migration, Provider activation, release or version change is authorized.

## Objective

Define one bounded, implementable Evidence Ingestion v1 slice that can accept an official company-announcement document through a user-initiated offline import, preserve immutable raw provenance, normalize it deterministically, produce reviewable company/industry candidates and require explicit human acceptance before creating an existing Evidence Ledger `EvidenceItem` or claim link.

The architecture must treat anti-bot and source-access controls as contractual boundaries. It must never convert a blocked source into a bypass task.

## Selected first-source boundary

- Source: CNINFO / 巨潮资讯 official company-announcement documents only.
- Document class: public listed-company announcement PDF.
- v1 acquisition mode: `offline_file` only.
- The user supplies the downloaded official PDF plus explicit source metadata.
- No live HTTP, API, feed, browser automation, scheduler, login or hidden network access is authorized.
- Future `official_api`, `official_feed` or `public_http` modes require a separate reviewed source contract and Architecture Task.

This is not authorization for news media, research reports, social media, market prices, interactive Q&A or other CNINFO datasets.

## Anti-bot and source-contract invariant

The implementation Definition of Ready must prohibit:

- CAPTCHA solving or bypass;
- browser stealth, fingerprint spoofing or anti-detection tooling;
- proxy rotation or IP cycling used to evade controls;
- session/cookie impersonation or login-wall bypass;
- rate-limit evasion;
- robots or terms-of-use bypass;
- production dependence on unpublished/private endpoints discovered by reverse engineering;
- silent source or acquisition-mode fallback.

A future `403`, `429`, CAPTCHA/interstitial, login wall, robots denial or material source-contract change must become a persisted or explicit `blocked` attempt state with credential-safe diagnostics. It must not trigger another adapter automatically.

## Existing accepted boundaries

- Existing `EvidenceItem` is append-only and owns accepted evidence semantics.
- Existing `EvidenceItem` fields include `case_id`, grade, source kind/title, publisher, locator, information date, recorded UTC, summary, content fingerprint and supersession.
- Existing accepted claim/evidence links remain append-only.
- Existing market-data `IngestionRun` is a complete-snapshot market-data contract and must not be reused for document ingestion.
- Candidate entity matching is not accepted identity.
- LLM output cannot own D0/D1/D2 qualification, accepted identity, evidence grade or acceptance state.
- Ordinary reads, startup, tests, CI and fixture demos remain network-free.

## Authorized files

1. `docs/evidence_ingestion_preflight.md`
2. `.codex/tasks/issue-154-evidence-ingestion-preflight.md`

No other file is authorized.

## Required architecture decisions

### Source registration

Define a source registration with:

- stable `source_key`;
- operator/owner;
- source class and allowed document class;
- allowed acquisition modes;
- terms/robots/data-use review status and review date;
- active/suspended/retired lifecycle;
- no credentials or secrets in persisted metadata.

### Capture and immutable storage

Define:

- import attempt identity and status;
- immutable raw object identity;
- raw bytes, SHA-256, media type, byte length and original filename;
- source locator and optional source announcement ID;
- publication/information date, imported time and recorded UTC as separate fields;
- deterministic exact-duplicate behavior;
- retention, backup and rollback behavior.

### Normalization

Define:

- one source-specific normalizer contract;
- parser and normalizer versions;
- PDF text extraction from embedded text only;
- no OCR fallback;
- title, issuer text, security-code text, announcement identifier, publication date and normalized text;
- `text_unavailable` and `parse_failed` states;
- deterministic normalized fingerprint.

### Deduplication and correction

Define separate outcomes for:

- exact raw duplicate;
- normalized duplicate;
- source-natural-key collision;
- corrected/superseding disclosure;
- ambiguous near duplicate requiring human review.

No fuzzy duplicate may be silently accepted.

### Candidate matching

Define deterministic candidates using only:

- exact source security-code text;
- exact issuer text;
- reviewed deterministic aliases.

Candidate rows must record method, matched value, target kind, target ID, confidence category and ambiguity. Candidate matching never creates accepted identity.

### Human review

Define explicit transitions from captured/normalized state to:

- awaiting review;
- accepted;
- rejected;
- duplicate;
- blocked;
- failed.

Acceptance must be one explicit transaction that records:

- reviewer identity label;
- target `ResearchCase`;
- selected company/industry identity if applicable;
- accepted `EvidenceItem` fields;
- evidence grade and source kind;
- optional existing claim revision and relation;
- exact raw and normalized document provenance.

Rejection or duplicate decisions must not mutate or delete raw capture.

### Evidence Ledger integration

Resolve:

- whether accepted `EvidenceItem.content_fingerprint` equals normalized fingerprint;
- how raw/normalized IDs remain traceable without changing accepted Evidence Ledger meaning;
- how accepted EvidenceItem creation and optional ClaimEvidenceLink creation remain append-only;
- how transaction rollback prevents partial acceptance;
- how cutoff and recorded UTC prevent later-information leakage.

### Schema and migration candidate

The preflight must define exact proposed tables, fields, constraints and indexes for:

- source registrations;
- capture attempts;
- immutable raw objects;
- normalized documents;
- entity candidates;
- review decisions/acceptance provenance.

It must define migration ordering and rollback. It must not reuse market-data `IngestionRun`.

### Dependency candidate

- Candidate dependency: `pypdf>=6.14,<7`.
- Purpose: local PDF embedded-text extraction only.
- No network calls, OCR, image extraction service or external parser process.
- License/security review and lock-file impact must be stated in the later implementation task.

### Commands and API

Define bounded user-initiated commands for:

1. register/inspect source;
2. import one offline PDF;
3. normalize one capture;
4. list/review candidates;
5. accept or reject one normalized document;
6. inspect provenance.

No scheduler, batch crawler or background worker is included.

### Testing

Require tests for:

- immutable bytes and SHA-256;
- exact/normalized duplicate behavior;
- source-natural-key collision;
- deterministic parser version and normalization;
- text-unavailable PDF;
- chronology and cutoff;
- ambiguous candidate identity;
- explicit acceptance and rollback;
- append-only accepted evidence;
- blocked anti-bot/source-contract state without bypass;
- no hidden network in imports, startup, tests, CI or fixtures;
- PostgreSQL and supported SQLite semantics;
- credential-safe errors.

## Locked exclusions

No production code, schema, migration, live scraping, browser automation, scheduler, multiple sources, API/feed adapter, news-media ingestion, social-media ingestion, OCR, external AI service, automatic identity acceptance, automatic EvidenceItem/claim creation, automatic evidence grading, LLM promotion to D0/D1/D2, Canonical Price, Comparison Eligibility, ranking, recommendation, monitoring, portfolio or trading behavior.

## Validation

- Base-to-head diff contains exactly the two authorized files.
- The preflight selects one source and one offline acquisition mode.
- Anti-bot controls are represented as fail-closed boundaries.
- Raw capture, normalized document, candidate identity and accepted EvidenceItem remain separate entities.
- Proposed schema, transitions, commands, dependency, migration, tests and stop conditions are specific enough for one later Product/Architecture implementation Issue.
- No implementation authorization appears in the documents.
- Draft PR remains open and unmerged pending independent fixed-head review.

## Independent approval

A clean review must comment exactly:

`DEFINITION OF READY APPROVED at fixed head <HEAD_SHA>`

The approval must be tied to one unchanged HEAD. Any documentation patch changes the HEAD and requires a fresh independent review.