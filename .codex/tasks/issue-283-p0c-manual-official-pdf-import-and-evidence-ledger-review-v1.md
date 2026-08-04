# Issue #283 — P0-C Manual Official PDF Import and Evidence Ledger Review v1

## Authority

Project-owner architecture-revision authorization on 2026-08-03:

> 批准按 Issue #283 preflight STOP 结论启动 Document Import/Evidence Ledger 架构修订；仅允许架构工件，不得实现生产功能。

This snapshot freezes architecture scope only. It authorizes no production code,
dependency, schema, migration, API, UI, fixture, test, workflow, Provider, network,
OCR, AI, automatic acceptance, recommendation, portfolio or trading change.

## Exact architecture start

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
base_branch = main
base_sha = eb4407a262cd9511fca903b75f6d01148ae79d81
issue = #283
roadmap = #137
risk_tier = Strict Architecture Revision
preflight_stop_record = issue comment 5162962922
implementation_authorized = false
```

PR #241 remains excluded and must not be modified.

## Owner inventory result

At the exact base:

1. `EvidenceLedgerCommandService` is the only accepted Evidence Ledger write owner.
2. `EvidenceItem` owns accepted, case-scoped source metadata, not local document
   import identity, bytes, pages or review history.
3. `Claim` / `ClaimRevision` and exact evidence links own accepted research
   statements and relationships, not pre-acceptance document candidates.
4. `EvidenceLedgerRepository` / `EvidenceLedgerQueryService` and the
   `/industry-alpha/cases` API are exact read owners.
5. Evidence Intelligence is stateless and read-only.
6. No Document, local Import, immutable page-text, document-review-history or
   document-acceptance-receipt owner exists.
7. Existing Evidence Ledger commands use separate transactions. No existing
   command can atomically accept a reviewed document boundary and its complete
   Evidence Ledger bridge.

```text
existing_owner_sufficient = false
schema_required = true
migration_required = true
evidence_ledger_owner_amendment_required = true
architecture_revision_required = true
```

## Frozen architecture direction

The proposed implementation boundary is:

```text
explicit local PDF selection
-> immutable local document content + import attempt
-> deterministic embedded-text pages
-> user-authored identity and page/span candidates
-> append-only human review revisions
-> explicit acceptance through EvidenceLedgerCommandService
-> atomic Evidence Ledger rows + exact acceptance receipt
```

The local document owner may persist import, extraction, candidate and review
history. It may not write accepted Evidence Ledger rows. The existing Evidence
Ledger owner must be amended with one explicit document-acceptance command that
opens the complete transaction, revalidates the exact reviewed boundary, creates
the permitted Evidence/Claim/link rows, creates the exact receipt and rolls back
everything on any failure.

## Frozen safety boundary

```text
user trigger required = true
local files only = true
network/provider/credential use = none
OCR/image recognition/cloud conversion = none
AI/model calls = none
background work/scheduler/polling = none
automatic official-source classification = none
automatic company/document identity acceptance = none
automatic evidence/claim acceptance = none
Industry/Company Research writes = none
candidate recomputation/ranking/recommendation = none
portfolio/trading = none
```

## Proposed v1 admission contract

The architecture proposal freezes these limits for independent review:

```text
maximum input bytes = 52,428,800 (50 MiB)
maximum pages = 300
maximum extracted characters per page = 100,000
maximum extracted characters per document = 5,000,000
maximum synchronous extraction time = 30 seconds
maximum decoded content stream per page = 52,428,800 bytes
maximum decoded content streams per document = 209,715,200 bytes
maximum extractor worker memory = 536,870,912 bytes
maximum candidates per review session = 500
accepted fact/event candidates per commit = 1..200
page numbering = 1-based
content fingerprint = lowercase SHA-256 over exact input bytes
page fingerprint = lowercase SHA-256 over exact stored UTF-8 page text
extractor dependency = pypdf==6.14.2
reader mode = PdfReader(strict=True, password=None)
text mode = extract_text(extraction_mode="plain")
```

- Reject malformed input, invalid PDF signature/media, any encrypted PDF,
  zero-page PDF, page/byte/text limit overflow and parser failure.
- Preserve exact extractor output per page. Do not normalize meaning, join pages,
  remove boilerplate or infer reading order beyond the extractor contract.
- Empty individual pages remain explicit. A document with zero non-whitespace
  embedded text across all pages is rejected as `embedded_text_unavailable`.
- The persisted extractor contract, package name and exact runtime version are
  provenance. Changing them creates a new extraction contract; it never silently
  rewrites old pages.
- Parsing runs only in a bounded, user-triggered synchronous child process. A
  30-second timeout terminates the worker and records `extractor_timeout`; it does
  not enqueue background work or retry with another parser.
- Worker startup must install the reviewed 512 MiB process-memory ceiling. Each
  decoded page content stream and their cumulative total are checked before text
  extraction. Failure to install/enforce a resource ceiling fails closed.
- No filesystem path is persisted or treated as authority.

## Duplicate and revision semantics

- Same byte SHA-256, same or different filename: `exact_content_duplicate`.
  Preserve the new import attempt, reuse the immutable content/pages and do not
  create accepted evidence automatically.
- Same filename with different bytes: `filename_content_conflict`.
- Same explicitly reviewed document identity with different bytes:
  `possible_document_revision`; only an explicit review may link supersession.
- Similar names, company names, dates or page text never merge records.
- Duplicate/revision decisions are append-only review facts and never update a
  previous exact-history view.

## Candidate and review semantics

Candidate kinds are closed to:

```text
document_identity
company_identity
fact
event
```

Fact/event candidates are explicitly user-created from one exact page and one
half-open UTF-8 byte range `[start_utf8_byte, end_utf8_byte)`. Both offsets must
fall on Unicode scalar boundaries in the exact stored page text. The selected
quote, its fingerprint, page number, offsets, user-authored statement and
candidate kind are persisted. There is no automatic NLP/AI candidate generation.

Document identity candidates require an explicit user-owned identity key, title,
publisher/author, document date and closed document kind. An optional exact prior
content ID may express a proposed revision, but no title/date similarity creates
that relationship. Company identity is either one explicitly selected exact local
`ListedInstrument` ID or the explicit state `not_company_specific`; ambiguous or
missing selection blocks acceptance.

Source layers remain distinct:

```text
extracted_page_text
user_authored_candidate
human_reviewed_candidate
accepted_evidence_ledger
```

Review revisions are append-only and closed to:

```text
draft
deferred
rejected
accepted
```

Defer/reject preserves exact history and creates no Evidence Ledger rows.
Acceptance requires explicit reviewed source kind, evidence grade, document
identity, subject/company decision, information date, candidate decisions, Claim
status and evidence relation. No default or heuristic may fill a missing choice.
Acceptance additionally requires at least one and at most 200 selected fact/event
candidates. A review with no fact/event candidate, or with every fact/event
candidate rejected/deferred, cannot enter `accepted`; preview and commit fail closed
with zero accepted review revisions, receipts or Evidence Ledger rows. Defer/reject
remains the explicit zero-Ledger terminal/nonterminal review path.

Document Import v1 supports only
`claim_operation = create_new_deterministic_claim`. For each selected fact/event
candidate, the exact Claim key is
`local-document-v1:<candidate_fingerprint_sha256>`. The operation never searches
for or appends an existing Claim, so `existing_claim_id` and expected existing
Claim latest revision are absent. The derived key, operation and absence of an
existing Claim target are part of review, preview and commit fingerprints. Outside
an exact acceptance-receipt replay, an existing `(case_id, claim_key)` or proposed
Evidence fingerprint fails closed as `previously_accepted_candidate_conflict`.

## Atomic acceptance contract

`EvidenceLedgerCommandService` remains the sole accepted owner. Its proposed
document command must, inside one transaction:

1. lock the exact review session;
2. read any receipt keyed by the exact `source_review_revision_id`;
3. when a receipt exists, compare the complete request fingerprint and immutable
   receipt bindings, then return the exact prior result with zero writes or fail as
   `acceptance_replay_conflict`; do not require the source revision to remain the
   session latest on this replay branch;
4. only when no receipt exists, verify the source revision ID, number and
   fingerprint, require it to be the current session latest, and allow only `draft`
   or `deferred`;
5. verify exact content, pages, spans, quotes and selected identity decisions;
6. lock and verify the exact target Research Case and both time boundaries;
7. require the complete selected fact/event set, ordered by candidate UUID, to
   contain `1..200` members and preflight every deterministic Claim key and
   Evidence fingerprint;
8. create one Evidence Item per accepted fact/event candidate;
9. create one new deterministic Claim/ClaimRevision and ClaimEvidenceLink explicitly
   selected by the reviewer;
10. append the terminal accepted review revision and acceptance receipt/link rows;
11. flush uniqueness constraints and commit all rows together or leave all accepted
    counts unchanged.

The acceptance request binds
`source_review_revision_id`, expected source revision number/fingerprint,
`expected_session_latest_revision_number`, the exact target Case, selected
candidate IDs and decision fingerprints in ascending candidate UUID order,
recorded time and contract version. The accepted
revision is a distinct row with number `source + 1`, state `accepted` and
`supersedes_review_revision_id = source_review_revision_id`. Its decision rows are
an exact transactional copy of the validated source decisions; acceptance cannot
add, remove or reinterpret a candidate decision.

The receipt stores unique `source_review_revision_id`, unique
`accepted_review_revision_id`, unique request fingerprint, both review
fingerprints, target Case and contract version. An exact replay returns that exact
accepted revision and result with zero writes; any difference is
`acceptance_replay_conflict`. The lock order is review session, receipt lookup,
an immediate exact/conflicting replay branch when a receipt exists, then—only for
a new acceptance—source/latest validation, target Case and candidates ordered by
UUID. Linear review-revision uniqueness and the receipt constraints are the
database final guards for concurrent acceptance.

The accepted review fingerprint is a canonical SHA-256 over its contract version,
source review ID/fingerprint, accepted revision number/state, acceptance
request/plan fingerprint, target Case and exact accepted timestamp; it is distinct
from the source review fingerprint and never depends on a mutable latest lookup.

The Evidence Item fingerprint is a canonical SHA-256 over the exact document
content fingerprint, page, offsets, quote fingerprint, reviewed statement and
candidate kind. `source_locator` contains only a stable local document/page/span
reference; it never contains a filesystem path or opaque JSON payload.

All request, candidate, review, preview and acceptance fingerprints use one
canonical UTF-8 JSON rule: sorted keys, compact separators, no floats, UUIDs in
lowercase canonical form, dates as ISO `YYYY-MM-DD`, timestamps normalized to UTC
`Z`, and string code points preserved without Unicode normalization.

Review/preview/acceptance fingerprints additionally include the deterministic
Claim operation/key, exact source review revision identity, expected session latest
revision and the complete source-to-accepted transition contract. A same candidate
submitted through another review never reuses an existing Claim or Evidence row.

## History and read contract

- All detail/reopen URLs use explicit import, content, review revision or receipt
  IDs plus explicit dual-as-of boundaries where accepted Evidence Ledger meaning
  is shown.
- No latest, closest-name, same-ticker, unique-reachable or one-option fallback.
- A later import, duplicate decision, review revision or accepted document never
  changes an exact historical response.
- Page navigation reads bounded batches of pages; no per-page HTTP request loop.
- Import/review views are local-only and write nothing. Preview writes nothing.
- Mutating HTTP routes require a loopback/same-origin Host and Origin plus an
  ephemeral SameSite=Strict double-submit CSRF token/header. Missing, cross-origin
  or stale tokens fail before parsing or database access. No wildcard CORS.
- Filename conflict comparison uses the exact validated basename code-point
  string: no case-folding, Unicode normalization or path-derived value.

Proposed query ceilings:

```text
import detail = <= 6 SQL statements
page batch (<= 30 pages) = <= 2 SQL statements
review detail/queue = <= 8 SQL statements
acceptance preview = <= 10 SQL statements and zero writes
acceptance commit = <= 16 SQL statements, independent of PDF page count
```

Candidate bulk insert may be set-based/batched. Acceptance cost may scale with
the number of explicitly selected candidates, never with all document pages.

## Proposed persistent concepts

One reviewed migration may add append-only tables for:

```text
local_document_contents
local_document_import_attempts
local_document_pages
local_document_review_sessions
local_document_candidates
local_document_review_revisions
local_document_review_candidate_decisions
local_document_acceptance_receipts
local_document_acceptance_links
```

The schema must support SQLite and PostgreSQL, exact foreign keys, deterministic
uniqueness, append-only ORM guards and upgrade/downgrade preflights that refuse
lossy history removal. This snapshot does not authorize creating the migration.

## Proposed future implementation allowlist

This list remains inactive until the architecture PR is independently approved,
merged with separate owner authorization, and Issue #283 is explicitly amended
for implementation:

```text
.codex/tasks/issue-283-p0c-manual-official-pdf-import-and-evidence-ledger-review-v1.md
docs/manual_official_pdf_import_evidence_ledger_v1_preflight.md
pyproject.toml
migrations/env.py
migrations/versions/20260803_0018_manual_official_pdf_import.py
industry_alpha/document_import_models.py
industry_alpha/document_import_contracts.py
industry_alpha/document_import_extractor.py
industry_alpha/document_import_rules.py
industry_alpha/document_import_repository.py
industry_alpha/document_import_query.py
industry_alpha/document_import_commands.py
industry_alpha/commands.py
backend/api/document_import.py
backend/main.py
document_import/static/document_import.html
document_import/static/document_import.js
document_import/static/document_import.css
tests/test_document_import_models.py
tests/test_document_import_extractor.py
tests/test_document_import_commands.py
tests/test_document_import_query.py
tests/test_document_import_api.py
tests/test_document_import_static.py
tests/test_document_import_postgres.py
tests/test_industry_alpha_ledger.py
tests/test_industry_thesis_migration.py
tests/test_investment_candidate_migration.py
tests/test_normalized_valuation_migration.py
scripts/demo_manual_document_import.py
.github/workflows/local-tests.yml
```

No additional path is authorized without an Issue amendment.

### Issue #285 minimal migration-test allowlist amendment

The project owner authorized this architecture-only amendment on 2026-08-04
after the authorized implementation first reached a complete local pytest run.
The exact architecture-amendment base is:

```text
main = 4849f8f680be85f266eba4d7377ec0b288a58916
implementation issue = #285
implementation commit = none
implementation PR = none
```

The complete run proved that adding the already-reviewed single migration
`20260803_0018_manual_official_pdf_import.py` advances Alembic `head` from
`20260725_0017` to `20260803_0018`. Three pre-existing migration-chain tests
assert the former repository head literally, so they fail even though their own
historical migration/table assertions remain valid. They were omitted from the
original future implementation allowlist.

This amendment adds exactly these existing tests to the future implementation
allowlist:

```text
tests/test_industry_thesis_migration.py
tests/test_investment_candidate_migration.py
tests/test_normalized_valuation_migration.py
```

They may be changed only to preserve their existing historical assertions while
recognizing the reviewed `20260803_0018` repository head and empty forward/
downgrade chain. This amendment does not authorize changes to their production
owners, historical migrations, table counts, downgrade-loss guards or unrelated
expectations. It adds no production file, schema concept, migration, dependency,
Provider/network, OCR, AI, automatic acceptance, recommendation, portfolio or
trading behavior.

## Required implementation validation after later authorization

Future implementation must prove:

- embedded-text golden path with exact page boundaries and citations;
- malformed, encrypted, image-only, empty-text and limit rejection;
- same-content/different-name duplicate and filename/content conflict;
- possible document revision without automatic supersession;
- ambiguous document/company identity fail closed;
- invalid page/span/quote fingerprint fail closed;
- no fact/event candidate, or all fact/event candidates rejected/deferred, makes
  preview and commit fail closed with zero accepted revision, receipt or Ledger
  writes;
- defer/reject history with zero accepted rows;
- interrupted acceptance leaves zero partial accepted rows;
- exact idempotent acceptance replay and conflicting replay rejection;
- accepted-state exact replay succeeds from the original source request even though
  the terminal accepted revision is now the session latest;
- deterministic Claim key plus pre-existing Claim/Evidence conflict;
- exact source-to-accepted review revision binding and concurrent receipt replay;
- later activity cannot change exact historical reopen;
- 1-page, 30-page and 300-page bounded query behavior;
- SQLite/PostgreSQL semantic parity;
- zero network, Provider, credential, OCR, AI, recommendation, portfolio and
  trading behavior.

## Current architecture delivery allowlist

The currently authorized architecture branch may change exactly two files:

```text
.codex/tasks/issue-283-p0c-manual-official-pdf-import-and-evidence-ledger-review-v1.md
docs/manual_official_pdf_import_evidence_ledger_v1_preflight.md
```

## STOP conditions

Stop and request another architecture amendment if review or later implementation
requires:

- a mutable filesystem path or unreviewed side store as provenance authority;
- packing page text/review state into Evidence Ledger free-text fields;
- bypassing `EvidenceLedgerCommandService` for accepted rows;
- partial acceptance across multiple transactions;
- a hidden identity, duplicate, revision or Claim-status default;
- OCR, AI, network, Provider, background execution or credential use;
- modification of Industry/Company Research, Investment Candidate,
  recommendation, portfolio or trading owners;
- any file outside the then-active allowlist.

## Governance gate

This architecture branch and any PR must remain Draft. A fresh independent
fixed-head architecture review must record zero blocking findings. Review approval
does not authorize merge. The project owner must separately authorize merge, then
separately authorize any implementation Issue/branch/PR.
