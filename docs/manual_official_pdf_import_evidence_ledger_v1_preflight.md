# Manual Official PDF Import and Evidence Ledger Review v1 — Architecture Revision

## Status and authority

```text
status = proposed architecture
issue = #283
roadmap = #137 P0-C step 1
exact_base = eb4407a262cd9511fca903b75f6d01148ae79d81
implementation_authorized = false
production_changes = none
schema_or_migration_changes_in_this_revision = none
```

This document resolves the STOP returned by the exact-base owner/schema audit.
It proposes the smallest durable local-document boundary that can preserve PDF
provenance, extracted page text, human review history and atomic acceptance into
the existing Evidence Ledger. It does not itself authorize implementation.

## Product objective

The ordinary-user flow is:

```text
用户主动选择本地官方 PDF
-> 本地校验和不可变导入记录
-> 仅提取内嵌文本并保留稳定页边界
-> 用户建立并审核文档/公司身份与页码候选
-> 用户明确接受
-> 通过现有 Evidence Ledger owner 原子写入
-> 精确历史可离线重开
```

The software never declares a document official merely because it is a PDF or
because a filename resembles an issuer. Official/source strength, document
identity, subject identity, page citation, evidence grade, Claim status and link
relation are explicit human-reviewed inputs.

## Exact-base inventory

### Evidence Ledger accepted owner

`industry_alpha.models` owns append-only Research Case, Evidence Item, Claim
revision, exact evidence links and verification checklist rows.

`EvidenceItem` provides:

```text
case_id
evidence_grade
source_kind
source_title
publisher_or_author
source_locator
information_date
recorded_at_utc
summary
content_fingerprint
supersedes_evidence_id
```

It does not own PDF bytes, a user import attempt, filename, byte size, page count,
extractor identity, page text, page spans, document/company identity candidates,
review revisions or acceptance receipts.

`EvidenceLedgerCommandService` is the only accepted write owner. Its methods are
transactional individually, but Evidence append, Claim creation and standalone
link creation are separate commands/transactions. The existing owner therefore
cannot receive the complete document bridge atomically.

### Read owners

`EvidenceLedgerRepository` and `EvidenceLedgerQueryService` provide exact Case
ledger reads. `/industry-alpha/cases` is GET-only. Evidence Intelligence is a
stateless read projection. Neither is a write or review owner.

### Missing owners

At the exact base there is no:

- Document content/import owner;
- immutable extracted-page owner;
- document/company identity candidate owner;
- page-cited fact/event candidate owner;
- append-only document review owner;
- exact document-to-ledger acceptance receipt owner.

## Why existing fields cannot be reused

The following shortcuts are rejected:

| Shortcut | Reason |
| --- | --- |
| Put metadata/page text into `source_locator` | Bounded free text, no typed provenance, page ordering, extractor identity or history. |
| Put pages/review JSON into `summary` | Accepted Evidence summary is not a pre-acceptance document store. |
| Treat `content_fingerprint` as document owner | Optional, case-scoped uniqueness; no content/page/import/review graph. |
| Use Claim statuses for document review | Claim judgment is accepted research meaning, not import/review workflow. |
| Use Verification `deferred` | It is a Case revision checklist, not a document review revision. |
| Keep only a filesystem path | Mutable, non-portable, may disappear, and cannot reproduce exact history. |
| Add a sidecar JSON directory | Unreviewed second persistence owner with no shared atomic transaction. |
| Call existing Evidence commands sequentially | Failure can leave partial accepted rows. |

## Ownership decision

### Local Document owner

A new `DocumentImportCommandService` owns only:

- explicit import attempts;
- admitted immutable content and exact bytes;
- deterministic extraction and immutable pages;
- identity/fact/event candidates;
- append-only review revisions and candidate decisions.

It may never create or modify Evidence Item, Claim, ClaimRevision or
ClaimEvidenceLink rows.

### Evidence Ledger owner amendment

`EvidenceLedgerCommandService` remains the only accepted write owner and gains a
single explicit command conceptually named:

```text
accept_reviewed_local_document(...)
```

This command owns the outer database transaction. It reads/locks the exact
immutable reviewed document boundary, applies all existing Evidence Ledger
validations, inserts the complete accepted graph, appends the accepted review
revision and writes acceptance receipts before one commit.

No generic public session injection is introduced. No document adapter receives
permission to insert accepted ledger models directly.

## Proposed persistence model

All new rows are append-only. Ordinary ORM update/delete is rejected.

### `local_document_contents`

One row per exact admitted byte content:

```text
id UUID primary key
content_sha256 CHAR(64) unique, lowercase
media_type = application/pdf
byte_size positive integer
raw_pdf_bytes binary, exact admitted bytes
page_count 1..300
embedded_text_page_count 1..page_count
total_text_char_count 1..5,000,000
extractor_contract_version
extractor_package
extractor_version
created_at_utc
```

Exact bytes are retained so local historical render/reopen does not depend on the
original path. A future switch to an immutable object store is a new architecture
decision; it is not an implementation fallback.

### `local_document_import_attempts`

One row per explicit user action, including rejected and duplicate attempts:

```text
id UUID primary key
content_sha256 CHAR(64)
content_id nullable exact FK
original_filename display-only
display_name
observed_media_type
byte_size
admission_state admitted|rejected|exact_content_duplicate
admission_reason closed code
imported_at_utc
```

No directory or filesystem path is persisted. Rejected malformed/encrypted files
retain fingerprint and safe metadata only, not bytes or parser exception text.

### `local_document_pages`

```text
id UUID primary key
content_id exact FK
page_number 1-based
text_state embedded_text_present|empty
extracted_text exact extractor output
text_sha256 SHA-256 of exact stored UTF-8 text
text_char_count
unique(content_id, page_number)
```

The API reads page batches. It never issues one HTTP or SQL query per page.

### Review and candidate identities

`local_document_review_sessions` binds one import attempt to one explicit target
Research Case without accepting evidence.

`local_document_candidates` contains immutable candidates:

```text
candidate_kind document_identity|company_identity|fact|event
page_number nullable for identity candidates
start_utf8_byte/end_utf8_byte nullable for identity candidates
quote_text and quote_sha256 for fact/event
statement for fact/event
candidate_payload_json strict canonical closed-schema JSON
candidate_fingerprint_sha256
recorded_at_utc
```

The JSON field is permitted only for closed candidate-kind fields validated by
the domain contract. It is not a generic metadata escape hatch.

Closed `document_identity` payload:

```text
identity_namespace = user_defined_document
identity_key required bounded exact user value
document_title required
publisher_or_author required
document_date required
document_kind = filing|announcement|regulatory|statistics|company_report|industry_report|other_official
revision_label optional display value
supersedes_document_content_id optional exact prior content UUID
```

The identity key is scoped to its explicitly reviewed publisher/namespace. Title,
publisher or date similarity never generates, merges or selects an identity. A
supersession candidate exists only when the user explicitly selects an exact prior
content UUID and later accepts that relationship.

Closed `company_identity` payload:

```text
subject_kind = listed_instrument|not_company_specific
listed_instrument_id required only for listed_instrument
display_label non-authoritative
```

The exact local `ListedInstrument` UUID is the only company authority. Company
name, ticker text and one-result queries are never identity fallbacks. Review may
retain multiple candidates, but acceptance requires exactly one selected subject
decision, including the explicit `not_company_specific` decision when applicable.

Closed fact/event payload:

```text
statement required bounded user text
event_date required only for event
claim_status explicit existing Evidence Ledger value
evidence_relation explicit existing Evidence Ledger value
```

Claim status and relation are frozen per selected candidate decision, not inferred
from candidate kind, Evidence grade or the act of accepting the document.

V1 freezes one Claim identity mode only:

```text
claim_operation = create_new_deterministic_claim
claim_key = "local-document-v1:" + candidate_fingerprint_sha256
existing_claim_id = absent
expected_existing_claim_latest_revision_number = absent
```

The resulting key is 82 ASCII characters and fits the existing 96-character
`Claim.claim_key` boundary. Document acceptance never searches for, selects or
appends an existing Claim. A later general Evidence Ledger workflow may append a
revision to the resulting exact Claim under its existing owner, but that is not a
Document Import v1 acceptance operation.

`local_document_review_revisions` freezes:

```text
review_session_id
revision_number
review_state draft|deferred|rejected|accepted
review_fingerprint_sha256
expected_previous_revision_number
explicit source kind and evidence grade
explicit document identity decision
explicit subject/company decision
information date
reviewer note
recorded_at_utc
supersedes_review_revision_id
```

Revisions form one linear chain per session. The schema enforces
`unique(review_session_id, revision_number)` and at most one successor for a
non-null `supersedes_review_revision_id`. Every non-initial revision points to the
immediately preceding exact revision. A user-authored revision may be `draft`,
`deferred` or `rejected`; only the Evidence Ledger acceptance command may append
the terminal `accepted` revision.

`local_document_review_candidate_decisions` freezes selected/rejected/deferred
decisions for exact candidate IDs. Accepted review revisions may select only
fact/event candidates with valid page, span and quote fingerprints, and must select
at least one and at most 200 such candidates. A review with no fact/event candidate,
or with every fact/event candidate rejected/deferred, cannot enter `accepted`.

### Acceptance receipt

`local_document_acceptance_receipts` binds both sides of one acceptance transition:

```text
id UUID primary key
review_session_id exact FK
source_review_revision_id exact FK, unique
accepted_review_revision_id exact FK, unique
target_research_case_id exact FK
source_review_fingerprint_sha256
accepted_review_fingerprint_sha256
request_fingerprint_sha256 unique
acceptance_contract_version
accepted_at_utc
```

The source is the exact latest eligible `draft` or `deferred` revision supplied by
the acceptance request. The accepted revision is created by that request with
`revision_number = source.revision_number + 1`, `review_state = accepted` and
`supersedes_review_revision_id = source_review_revision_id`. A receipt therefore
never uses one ambiguous `review_revision_id` for both the pre-acceptance input and
the terminal result. In the same transaction, the accepted revision receives an
exact copy of the source revision's validated candidate decisions; it cannot add,
drop or reinterpret a decision during acceptance.

`local_document_acceptance_links` binds each exact selected candidate to its exact:

```text
evidence_item_id
claim_id
claim_revision_id
claim_evidence_link_id
```

Receipt/link rows are created in the same transaction as the accepted ledger
rows. They provide exact idempotence and historical reopen; they do not replace
the Evidence Ledger graph.

## Admission and extraction contract

### Limits

```text
max_bytes = 52,428,800
max_pages = 300
max_page_characters = 100,000
max_document_characters = 5,000,000
max_extraction_seconds = 30
max_decoded_page_content_bytes = 52,428,800
max_decoded_document_content_bytes = 209,715,200
max_worker_memory_bytes = 536,870,912
```

Validation order is deterministic:

1. explicit user action and bounded upload;
2. exact byte count and SHA-256;
3. PDF signature/media validation;
4. encrypted flag check;
5. strict parse and page count;
6. exact per-page embedded-text extraction;
7. per-page and total character limits;
8. reject all-empty embedded text;
9. persist content/pages/import result atomically.

Closed rejection reasons include:

```text
invalid_media_type
invalid_pdf_signature
file_too_large
encrypted_pdf_unsupported
malformed_pdf
page_count_out_of_range
page_text_too_large
document_text_too_large
decoded_content_stream_too_large
embedded_text_unavailable
extractor_failure
extractor_timeout
extractor_resource_limit
```

Parser exception strings and local paths are not persisted or returned to the
ordinary-user UI.

### Extraction provenance

Architecture contract:

```text
aquantai.local-pdf-embedded-text.v1
pypdf==6.14.2
PdfReader(BytesIO(exact_bytes), strict=True, password=None)
page.extract_text(extraction_mode="plain") or ""
```

The dependency is pinned exactly because pypdf documents that extracted ordering
can evolve. The exact installed version is also persisted. Any parser version,
family, strictness, extraction mode or normalization change requires a new
contract version and never rewrites old rows.

OCR, rendered-image text recognition, cloud conversion, external converters,
remote fonts/resources and model calls are prohibited. Parsing may run only in a
bounded user-triggered synchronous Python child process so a malformed document
cannot block the application indefinitely. The child has a 30-second deadline,
no network permission, no persistent queue and no alternate-parser fallback.

Before parsing, the child must install a 512 MiB process-memory ceiling using the
reviewed operating-system primitive; inability to enforce it is
`extractor_resource_limit`. Before `extract_text`, decoded content streams are
bounded to 50 MiB per page and 200 MiB per document. A limit breach rejects the
attempt and the parent persists only safe rejection metadata. The parent never
continues parsing in-process.

Primary dependency evidence:

- [pypdf 6.14.2 on PyPI](https://pypi.org/project/pypdf/)
- [pypdf 6.14.2 PdfReader API](https://pypdf.readthedocs.io/en/latest/modules/PdfReader.html)
- [pypdf text-extraction limits](https://pypdf.readthedocs.io/en/5.7.0/user/extract-text.html)

## Duplicate, conflict and supersession contract

Duplicate evaluation uses exact byte SHA-256 only.

| Condition | Result |
| --- | --- |
| Same SHA-256, same name | `exact_content_duplicate` |
| Same SHA-256, different name | `exact_content_duplicate`; preserve alias attempt |
| Same filename, different SHA-256 | `filename_content_conflict` |
| Same reviewed document identity, different SHA-256 | `possible_document_revision` |
| Similar name/text/company only | no duplicate identity |

Exact duplicate attempts reuse content/page identity but never reuse a prior
review decision or acceptance automatically. Supersession is an explicit review
link between exact document content identities. Existing Evidence Items are never
updated, merged or overwritten.

## Candidate contract

No automatic fact/event extraction exists in v1. The user selects text on one
page, producing an exact half-open UTF-8 byte span. The server re-reads stored
page text and verifies:

```text
1 <= page_number <= page_count
0 <= start_utf8_byte < end_utf8_byte <= len(page_text.encode("utf-8"))
both offsets are UTF-8 code-point boundaries
quote_text.encode("utf-8") == page_utf8[start_utf8_byte:end_utf8_byte]
quote_sha256 == sha256(quote_text UTF-8)
```

The user then supplies a bounded factual/event statement. Event date, when used,
is explicit and must not exceed the reviewed information date. Identity candidates
are also explicit user inputs or exact local identity selections; there is no
name/ticker/company heuristic.

Citation offsets are half-open UTF-8 byte offsets, not JavaScript UTF-16 code-unit
offsets or Python implementation-dependent display columns:

```text
0 <= start_utf8_byte < end_utf8_byte <= len(page_text.encode("utf-8"))
both offsets are UTF-8 code-point boundaries
quote_text.encode("utf-8") == page_utf8[start_utf8_byte:end_utf8_byte]
```

The browser must calculate byte offsets from the exact displayed stored text, and
the server remains authoritative by reconstructing and comparing the quote.

## Human review and source-layer separation

Review state transitions append revisions:

```text
draft -> draft|deferred|rejected|accepted
deferred -> draft|deferred|rejected|accepted
rejected -> terminal for that review session
accepted -> terminal; exact replay only
```

An accepted review requires every semantic field to be explicit. Missing or
ambiguous document identity, company/subject identity, source kind, evidence
grade, information date, candidate decision, Claim status or evidence relation
fails closed. It also requires `1..200` selected fact/event candidates. Zero
selected fact/event candidates fails closed in preview and commit with no accepted
review revision, receipt or Evidence Ledger row; defer/reject remains available and
preserves review history without Ledger writes.

Source-layer labels:

| Layer | Meaning |
| --- | --- |
| `extracted_page_text` | Deterministic parser output, not a research fact. |
| `user_authored_candidate` | Page/span-backed proposal, not reviewed. |
| `human_reviewed_candidate` | Explicit persisted judgment, not yet Ledger acceptance. |
| `accepted_evidence_ledger` | Exact rows created by the accepted owner transaction. |

The UI must show these states in Chinese and must not label earlier layers as
official/accepted evidence.

## Exact Evidence Ledger mapping

For each selected fact/event candidate, acceptance creates one Evidence Item and
one exact fact Claim revision plus link values selected by the reviewer.

Canonical Evidence Item fingerprint input:

```json
{
  "contract": "aquantai.local-document-evidence-item.v1",
  "document_content_sha256": "...",
  "page_number": 1,
  "start_utf8_byte": 0,
  "end_utf8_byte": 10,
  "quote_sha256": "...",
  "candidate_kind": "fact",
  "reviewed_statement": "..."
}
```

`source_locator` uses a bounded stable form:

```text
local-document:<content-uuid>#page=<n>&start_utf8_byte=<s>&end_utf8_byte=<e>
```

It never contains an OS path. Source kind, grade, title, publisher, information
date, Claim status and relation come from exact review fields, not PDF/file-name
heuristics. Existing Evidence Ledger validation remains authoritative.

For every selected candidate, the Claim mapping is closed and deterministic:

```text
claim_operation = create_new_deterministic_claim
claim_key = "local-document-v1:" + candidate_fingerprint_sha256
claim_kind = fact
claim statement = exact reviewed statement
claim status = exact reviewed claim_status
information_cutoff_date = exact reviewed information date
existing claim append = prohibited
```

Preview must check both `(target_research_case_id, claim_key)` and the proposed
Evidence Item fingerprint before commit. Outside an exact receipt replay, any
existing Claim key or Evidence fingerprint is
`previously_accepted_candidate_conflict`; v1 never silently reuses, links to or
appends the existing rows. This makes a duplicate review fail closed while leaving
the existing Claim identity available to the ordinary Evidence Ledger revision
workflow.

## Atomicity and idempotence

Acceptance request binds:

```text
source_review_revision_id
expected_source_review_revision_number
expected_source_review_fingerprint_sha256
expected_session_latest_revision_number
target_research_case_id
selected_candidate_ids and decision fingerprints in ascending candidate UUID order
recorded_at_utc
acceptance_contract_version
```

Every candidate, review, preview and acceptance fingerprint uses one canonical
JSON encoding:

```text
UTF-8
keys sorted lexicographically
compact separators
no floats or NaN/Infinity
UUID lowercase canonical strings
dates YYYY-MM-DD
timestamps UTC with Z
string code points preserved; no NFC/NFKC/case normalization
```

The fingerprint input includes the exact content/page/extractor identities,
target Case, all selected identity and fact/event candidate fingerprints, all
candidate decisions, source kind, grade, dates, Claim statuses/relations,
`claim_operation`, every derived `claim_key`, source review revision identity,
expected session latest revision and contract versions.

The service reloads and locks the exact graph. Preview performs the same validation
and returns a deterministic plan/fingerprint with zero writes. Commit compares the
request to a freshly rebuilt preview and then executes one transaction.

The transaction lock and transition order is fixed:

1. lock the exact review session;
2. read an existing receipt by `source_review_revision_id` for replay/conflict;
3. when a receipt exists, compare the complete request fingerprint and immutable
   receipt bindings, then return the exact result or fail as a conflicting replay;
4. only when no receipt exists, verify the source revision belongs to that session
   and matches its expected
   number and fingerprint;
5. verify it is the current session latest and is `draft` or `deferred`;
6. lock the exact target Research Case;
7. reload candidates/decisions in ascending candidate UUID order, require the
   complete selected fact/event set to contain `1..200` members, and run all
   identity, citation, Claim-key and Evidence-fingerprint checks;
8. insert the complete Ledger graph, terminal accepted revision, receipt and links;
9. flush all uniqueness constraints and commit once.

If a receipt already exists for the source revision, an exact request fingerprint,
source fingerprint, target Case and contract version returns that receipt's exact
`accepted_review_revision_id` and result links with zero writes. Any difference is
`acceptance_replay_conflict`. The unique source receipt, unique accepted revision,
linear revision constraints and session lock make concurrent identical requests
converge on the same receipt; a losing transaction reloads and applies the same
exact/conflicting replay rule. An exception at any insertion point rolls back
review acceptance, receipt and all Evidence Ledger rows.

The accepted review fingerprint is SHA-256 over canonical JSON containing the
accepted-review contract version, source review revision ID/fingerprint, accepted
revision number, `review_state = accepted`, acceptance request/plan fingerprint,
target Case and exact accepted timestamp. It is not copied from the source review
and cannot be rebuilt from a mutable latest revision.

## Access, visibility and exact history

V1 follows the existing local single-user boundary; it does not introduce remote
accounts or authorization roles. Every mutation remains an explicit local user
action.

All mutation routes require:

```text
Host restricted to the configured loopback/local application origin
Origin exactly matching that local origin
SameSite=Strict ephemeral CSRF cookie
matching X-AQuantAI-CSRF header
no wildcard CORS
```

The CSRF secret is process-ephemeral, is not a user credential and is never
persisted. Restart invalidates prior write tokens but changes no stored history.
The guard runs before request-body parsing, PDF extraction or database access.
Non-browser fixture/CLI callers use the command owner directly, not an HTTP bypass.

Reads use exact IDs. Historical accepted views also require explicit information
cutoff and recorded-at boundaries. A later import/review/duplicate/acceptance is
never substituted for an older explicit selection.

Exact persisted bytes are available only through an explicit download response
with `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`.
The ordinary-user page renders stored page text with text-safe DOM operations; it
does not embed the PDF in `iframe`, `object` or executable viewer content.
Filenames are escaped/display-only and never control filesystem access or response
headers without sanitization.

The server accepts only a validated basename containing no path separator, NUL or
control character. Filename conflict comparison uses exact code-point equality on
that stored basename. There is no case-folding or Unicode normalization; display
similarity is not identity.

## API and UI proposal

One bounded local router may expose conceptually:

```text
POST /document-imports                       explicit bounded local upload
GET  /document-imports/{import_id}           exact metadata/history
GET  /document-contents/{content_id}/pdf     exact local bytes
GET  /document-contents/{content_id}/pages   page batches, max 30
POST /document-reviews                       explicit review session
POST /document-reviews/{id}/candidates       explicit user candidate
POST /document-reviews/{id}/revisions        defer/reject/review revision
POST /document-reviews/{id}/acceptance-preview
POST /document-reviews/{id}/acceptance-commit
GET  /document-acceptances/{receipt_id}      exact receipt/result
```

The ordinary-user page is Chinese-first and exposes progressive technical detail.
No page load, GET, render, preview, navigation or history reopen writes state.

## Bounded query and performance contract

Page text is fetched in ordered batches of at most 30 pages. Review candidate
lists use stable cursor pagination. No API composition loops across pages.
Metadata, page, review and queue repositories select explicit columns and never
materialize `raw_pdf_bytes`; only the exact attachment endpoint may select that
column.

```text
maximum candidates per review session = 500
selected fact/event candidates per acceptance = 1..200
maximum import/review queue page size = 50
```

```text
import detail <= 6 SQL
page batch <= 2 SQL
review detail/queue <= 8 SQL
acceptance preview <= 10 SQL, zero writes
acceptance commit <= 16 SQL excluding bounded executemany batches
```

Acceptance queries depend on selected candidate count, not total PDF pages.
Required scale fixtures cover 1, 30 and 300 pages.

## Cross-database and migration proposal

One later reviewed migration, provisionally
`20260803_0018_manual_official_pdf_import.py`, may add only the proposed local
document tables and constraints. Raw bytes use cross-database compatible binary
storage; page text uses compatible text storage. UUID, uniqueness, check constraints
and append-only behavior must have SQLite and PostgreSQL tests.

Upgrade creates empty new tables only. No legacy backfill or Evidence Item rewrite.
Downgrade must preflight and refuse when any new document/import/review/receipt row
exists; it may not delete history silently.

## Dependency decision

The Python standard library does not extract PDF text. The proposed implementation
therefore permits exactly `pypdf==6.14.2` in `pyproject.toml`, without crypto,
image or full extras. Encrypted documents are rejected rather than decrypted.
This architecture decision is still subject to independent fixed-head review and
is not permission to modify dependencies now.

## Fixture-only validation matrix

Future tests/demos must use generated or repository-owned synthetic PDFs only and
must perform zero network calls.

Positive:

- 1-page, 30-page and 300-page embedded-text imports;
- stable page text and quote citations;
- explicit identity decisions;
- defer then accept history;
- atomic Evidence/Claim/link/receipt creation;
- deterministic Claim key creation and pre-existing Claim-key conflict;
- source-to-accepted review transition and concurrent receipt convergence;
- exact replay and exact historical reopen.

Negative:

- invalid media/signature, malformed, encrypted and image-only PDF;
- byte/page/text limit overflow;
- duplicate content under another name;
- filename conflict and possible revision;
- ambiguous company/document identity;
- invalid page, span, quote or fingerprint;
- no fact/event candidate and all fact/event candidates rejected/deferred; preview
  and commit must fail closed with zero accepted revision, receipt or Ledger rows;
- missing source grade/kind/Claim decision;
- reject/defer with zero accepted writes;
- injected mid-transaction failure;
- later review/duplicate/import cannot replace exact history;
- filesystem path traversal and header-injection filenames;
- zero Provider/network/OCR/AI/automatic acceptance/recommendation/portfolio/trading.

## Architecture artifact allowlist

The current revision changes only:

```text
.codex/tasks/issue-283-p0c-manual-official-pdf-import-and-evidence-ledger-review-v1.md
docs/manual_official_pdf_import_evidence_ledger_v1_preflight.md
```

## Candidate implementation allowlist

The candidate allowlist is recorded in the Issue #283 task snapshot. It is not
active and may not be used until this architecture is independently reviewed,
separately authorized for merge, merged, and followed by explicit project-owner
implementation authorization from a newly re-read exact `main`.

## Stop conditions

Stop if architecture review or later implementation discovers a need for:

- a mutable path or unreviewed side store as provenance authority;
- a second accepted Evidence Ledger write owner;
- sequential partial acceptance;
- opaque free-text/JSON reuse that bypasses typed contracts;
- implicit source, identity, duplicate, revision, evidence or Claim decisions;
- OCR, AI, Provider/network, credential or background behavior;
- automatic Industry/Company Research or Investment Candidate mutation;
- recommendation, portfolio or trading semantics;
- another migration or any repository file outside the active allowlist.

## Governance

This architecture revision requires a fresh fixed-head independent review. Even a
zero-blocker review does not authorize Ready, merge or implementation. Each later
step requires separate project-owner authorization. Any new commit invalidates
prior CI and review evidence.
