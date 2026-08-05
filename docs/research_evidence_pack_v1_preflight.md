# Research Evidence Pack v1 — Strict Architecture Preflight

## 1. Status and authority

This architecture preflight is governed by Issue #288 and Roadmap #137. It starts
from exact `main@8dd187c129c3e4a375f550758fab266719ccd0da` after the accepted
Manual Official PDF Import and Evidence Ledger Review v1 implementation.

The project owner authorized exactly two architecture artifacts. On 2026-08-05
the owner separately authorized repair of the three blocking findings on PR #289,
restricted to those same artifacts, followed by full CI and a fresh independent
fixed-HEAD architecture review.

This document contains no production implementation authority. It does not
authorize schema, migration, dependency, API/UI, fixture, test, workflow,
Provider/network, OCR, AI, automatic evidence acceptance, recommendation,
portfolio, trading, release, tag, version, Ready, merge, Issue closure or PR #241
changes.

Risk classification is Strict because the proposed read crosses frozen Evidence
Ledger and local-document acceptance boundaries. A later implementation may be
Standard read-only only if every decision below is preserved without a new owner,
schema or write path.

## 2. Fixed-HEAD review repair

The first fixed-HEAD review at
`a06318e833d7ebca67cc90ef0cb8d484ccf0f66e` withheld approval for three High
findings. This revision closes them through three exact decisions:

1. A local-document citation is authoritative only after complete set-wise replay
   of the bounded atomic receipt transition: source and accepted revisions,
   candidate/decision/source/request/accepted fingerprints, exact copied decision
   set, all sibling acceptance links and the exact produced Ledger graph.
2. Research membership is authoritative per Claim binding. The Evidence entry has
   no lossy scalar membership; it exposes a closed derived summary including the
   mixed linked/unlinked case.
3. Supersession validation explicitly permits one bounded set-wise minimal target
   load. It follows the accepted owner chronology, including valid equal recorded
   timestamps, while target payload remains excluded from the response.

No other product or owner boundary expands.

## 3. Product problem

The local PDF flow can accept page-cited facts into the Evidence Ledger, and the
research flow can preserve exact historical Case revisions. The ordinary user
still lacks one bounded view answering:

> For this exact Research Case revision and historical boundary, which accepted
> evidence exists, which exact Claim revisions does it support, contradict or
> contextualize, which bindings are already members of this frozen research
> snapshot, and which intact local PDF receipt proves each citation?

Existing Evidence Ledger detail is complete-Case/date-oriented. Existing Document
Import detail starts from one receipt or review identity. The required product is
one bounded dual-as-of Evidence-first projection.

## 4. Product boundary

Research Evidence Pack v1 is:

- local and read-only;
- anchored to one explicit Research Case and one explicit Case revision;
- bounded by one information date and one recorded UTC timestamp;
- Evidence-first and keyset-paginated;
- exhaustive for visible accepted Evidence Items page by page;
- exact about Claim bindings, selected-revision roles and receipt provenance;
- deterministic and zero-network/zero-OCR/zero-AI.

It is not:

- a persisted pack or saved snapshot;
- a document inbox, Provider catalog or acquisition workflow;
- an automatic research refresh;
- an AI summary, sentiment classifier or evidence generator;
- an Evidence Ledger or Document Import mutation path;
- a candidate scorer, recommendation, portfolio or trading feature.

## 5. Existing authoritative owners

### 5.1 Research Case

`ResearchCase` owns stable Case identity. `ResearchCaseRevision` owns append-only
research question, summary, workflow/conclusion state, information cutoff,
recorded time and supersession history.

The exact Case revision supplied in the request is the research-snapshot anchor.
The pack never chooses a latest Case revision.

### 5.2 Evidence Ledger

| Meaning | Owner |
| --- | --- |
| Accepted source metadata and evidence grade | `EvidenceItem` |
| Stable Claim identity | `Claim` |
| Exact Claim statement/status/history | `ClaimRevision` |
| Evidence relation | `ClaimEvidenceLink` |
| Claim role in one exact Case revision | `CaseRevisionClaimLink` |
| Accepted writes and invariants | `EvidenceLedgerCommandService` |

The pack cannot create or mutate any of these rows.

### 5.3 Local Document Import

| Meaning | Owner |
| --- | --- |
| Immutable PDF bytes/extractor provenance | `LocalDocumentContent` |
| User import occurrence and filename | `LocalDocumentImportAttempt` |
| Exact stored page text and fingerprint | `LocalDocumentPage` |
| Case-scoped review identity | `LocalDocumentReviewSession` |
| Page/span/quote and user statement | `LocalDocumentCandidate` |
| Append-only review snapshot | `LocalDocumentReviewRevision` |
| Exact candidate decision snapshot | `LocalDocumentReviewCandidateDecision` |
| Atomic accepted transition | `LocalDocumentAcceptanceReceipt` |
| Exact Document-to-Ledger graph | `LocalDocumentAcceptanceLink` |

`LocalDocumentAcceptanceLink.evidence_item_id` is unique. Its presence is the
only authority for classifying an Evidence Item as accepted through the local
Document Import path.

### 5.4 Existing reads

`EvidenceLedgerRepository.load_case` and `EvidenceLedgerQueryService` retain their
existing complete-Case/date-only semantics. They are not reinterpreted as this
bounded dual-as-of pack.

`DocumentImportQueryService.acceptance_detail` remains the exact receipt detail
surface. The pack may read the same immutable rows set-wise, but it may not weaken
or redefine the accepted transaction.

## 6. Owner and schema audit result

The exact base already contains every identity and relationship required for a
transient projection:

- Evidence rows carry Case and dual-time fields;
- Claim revisions and relations carry exact IDs and chronology;
- Case-revision links preserve frozen membership and role;
- acceptance receipts preserve source/accepted revisions and transition
  fingerprints;
- review decisions preserve the complete selected/non-selected snapshot;
- acceptance links freeze Evidence, Claim, ClaimRevision and relation IDs;
- import/content/candidate/page rows preserve the citation path;
- append-only constraints preserve historical identity.

```text
read_only_projection_reachable = true
saved_pack_reachable = false
new_owner_for_v1 = none
existing_write_owner_change = none
schema_change = none
migration = none
backfill = none
```

A durable pack, saved selection or required index is a STOP condition, not
permission to reuse an unrelated field.

## 7. Core architecture

The pack is composed in three layers.

### Layer A — Frozen research anchor

The request supplies exact Case and Case revision IDs. Layer A validates identity,
ownership and dual-as-of visibility. It exposes persisted Case-revision fields
only and writes nothing.

### Layer B — Visible accepted Case evidence

Layer B pages all accepted `EvidenceItem` rows belonging to the Case and visible
under both boundaries. Every exact visible Claim binding is preserved. Evidence
need not already be linked to the selected Case revision.

### Layer C — Exact provenance enrichment

Layer C enriches an Evidence Item only through an exact
`LocalDocumentAcceptanceLink`. It replays the complete bounded receipt transition
and citation graph. It never classifies provenance from free text.

The following equation is false and prohibited:

```text
accepted Evidence Ledger item
= accepted conclusion/context/risk in selected Case revision
```

Only an exact `CaseRevisionClaimLink` gives an exact ClaimRevision a role in the
selected frozen revision.

## 8. Canonical route and selectors

```text
GET /research-evidence-pack/api/cases/{research_case_id}/revisions/{research_case_revision_id}
```

| Field | Required | Contract |
| --- | --- | --- |
| `information_cutoff_date` | yes | ISO date |
| `recorded_at_utc` | yes | timezone-aware RFC3339 normalized to UTC |
| `limit` | no | default 50, closed range 1..100 |
| `cursor` | no | opaque request-bound keyset cursor |

Rules:

- both IDs are explicit UUIDs;
- the revision must belong to the Case;
- `information_cutoff_date <= recorded_at_utc UTC date`;
- the exact Case revision must be visible under applicable boundaries;
- no route may ask the server to choose a revision;
- no latest, newest, only-option, same-name, same-ticker or unique-reachable
  inference is permitted;
- out-of-range limits fail rather than clamp.

## 9. Dual-as-of semantics

| Row | Information boundary | Recorded boundary |
| --- | --- | --- |
| selected Case revision | its information cutoff | `recorded_at_utc` |
| Evidence Item | `information_date` | `recorded_at_utc` |
| ClaimRevision | `information_cutoff_date` | `recorded_at_utc` |
| ClaimEvidenceLink | n/a | `recorded_at_utc` |
| CaseRevisionClaimLink | exact selected revision | `recorded_at_utc` |
| accepted document revision | `information_date` | `recorded_at_utc` |
| acceptance receipt | through accepted revision | `accepted_at_utc` |

A row outside a boundary is unavailable and is never replaced with another
revision.

## 10. Evidence-page membership and ordering

An Evidence Item is eligible only when:

```text
case_id = requested Research Case
information_date <= requested information cutoff
recorded_at_utc <= requested recorded boundary
```

Stable entry order is:

```text
EvidenceItem.information_date DESC
EvidenceItem.recorded_at_utc DESC
EvidenceItem.id ASC
```

The projection preserves Evidence Items with no visible Claim relation. They
remain accepted Evidence and are not silently dropped.

## 11. Claim binding contract

For every Evidence entry, the projection loads Claim bindings set-wise and
verifies:

- `ClaimEvidenceLink.evidence_id` equals the entry ID;
- the exact ClaimRevision exists and is visible;
- the ClaimRevision belongs to an exact Claim in the requested Case;
- relation is persisted `supports`, `contradicts` or `context`;
- selected-revision roles come only from exact visible
  `CaseRevisionClaimLink` rows for the requested Case revision;
- no other Case revision role is substituted.

The pack never selects a latest ClaimRevision. It returns the exact revisions
reached by visible ClaimEvidenceLinks for the current Evidence page.

### 11.1 Authoritative per-binding membership

Every `claim_bindings[]` member carries one authoritative
`research_membership_state`:

```text
linked_to_selected_case_revision
accepted_unlinked_to_selected_case_revision
```

A binding is linked only when at least one exact selected-revision role exists for
that exact ClaimRevision. Exact role and `CaseRevisionClaimLink` IDs are returned
inside `selected_case_revision_roles[]`.

### 11.2 Closed entry summary

The Evidence entry has no scalar `research_membership_state`. It exposes a derived
`membership_summary` with exactly four values:

```text
no_claim_bindings
all_bindings_linked
all_bindings_unlinked
mixed_linked_and_unlinked_bindings
```

The summary is computed only after the complete visible binding set is assembled.
It cannot override, merge or discard a binding. One Evidence Item may contain a
linked binding and an unlinked binding simultaneously.

Nested order is:

```text
Claim.claim_key ASC
ClaimRevision.revision_no ASC
ClaimEvidenceLink.relation ASC
ClaimRevision.id ASC
CaseRevisionClaimLink.role ASC
CaseRevisionClaimLink.id ASC
```

## 12. Supersession validation

Evidence and Claim supersession remain explicit history. Supersession never acts
as a hidden latest selector.

### 12.1 Bounded minimal target load

For all non-null supersession IDs reached by the bounded page, the projection is
explicitly permitted to issue one set-wise minimal target statement. The load may
cross the information boundary solely to validate identity and chronology.

Allowed columns are closed to:

```text
Evidence target:
  id
  case_id
  information_date
  recorded_at_utc

ClaimRevision target:
  id
  claim_id
  revision_no
  information_cutoff_date
  recorded_at_utc
```

No target statement, summary, source metadata, locator, quote, page text,
reviewer note or other payload field may be loaded through this path.

### 12.2 Owner-consistent integrity rules

A present `EvidenceItem.supersedes_evidence_id` must identify an existing Evidence
Item in the same Case and satisfy:

```text
target.recorded_at_utc <= superseding_evidence.recorded_at_utc
```

A present `ClaimRevision.supersedes_revision_id` must identify an existing
ClaimRevision of the same Claim, have a lower revision number, and satisfy:

```text
target.recorded_at_utc <= superseding_claim_revision.recorded_at_utc
```

This matches `EvidenceLedgerCommandService` chronology exactly. Equal recorded
timestamps are valid and must not fail integrity.

A valid target outside the requested information boundary is represented only by
its exact ID and `not_visible_as_of`. Its metadata is not exposed. Missing,
cross-Case, cross-Claim, invalid revision-order or later-recorded targets fail the
whole request as `evidence_pack_integrity_error`.

## 13. Local-document provenance authority

`LocalDocumentAcceptanceLink` is authoritative.
`EvidenceItem.source_locator` is not a selector and is never parsed to discover
content, page or offsets.

If any page Evidence Item reaches a receipt, the projection validates the full
receipt-level transition, including all sibling links and both complete decision
sets for every bounded receipt. Validating only the current page link is
prohibited.

## 14. Complete atomic receipt transition

### 14.1 Receipt/session/Case identity

For each bounded receipt:

- receipt exists;
- review session exists;
- source and accepted review revisions exist;
- receipt, source, accepted and session share the same `review_session_id`;
- receipt target Case equals session target Case and requested Case;
- source recorded time is not after receipt accepted time;
- receipt accepted time is not after the requested recorded boundary;
- accepted revision information date is not after the requested information
  boundary.

Any mismatch fails the entire pack.

### 14.2 Contract and stored fingerprint equality

The following equalities are mandatory:

```text
receipt.acceptance_contract_version
= aquantai.local-document-acceptance.v1

receipt.source_review_fingerprint_sha256
= source.review_fingerprint_sha256

receipt.accepted_review_fingerprint_sha256
= accepted.review_fingerprint_sha256
```

Source state must be `draft` or `deferred`. Accepted state must be `accepted`.

### 14.3 Exact terminal immediate successor

The accepted revision must be the exact immediate successor:

```text
accepted.revision_number = source.revision_number + 1
accepted.expected_previous_revision_number = source.revision_number
accepted.supersedes_review_revision_id = source.id
accepted.review_session_id = source.review_session_id
accepted.recorded_at_utc = receipt.accepted_at_utc
```

The following accepted fields must be exact copies of the source revision:

```text
source_kind
evidence_grade
document_identity_candidate_id
subject_candidate_id
information_date
reviewer_note
```

A set-wise aggregate in the receipt statement must also prove that accepted is the
maximum revision number in that review session. A later revision, alternate
successor or substituted revision is an integrity failure.

## 15. Candidate and decision fingerprint replay

### 15.1 Candidate fingerprint

For every candidate owned by a bounded receipt review session, parse
`candidate_payload_json` and canonically rebuild the candidate shape under:

```text
aquantai.local-document-candidate.v1
```

The exact shape is:

```text
content_id
content_sha256
extractor_contract_version
candidate_kind
page_number
start_utf8_byte
end_utf8_byte
quote_sha256
statement
payload
```

The rebuilt SHA-256 must equal
`LocalDocumentCandidate.candidate_fingerprint_sha256`. This applies to document
identity, company identity, fact and event candidates, whether selected, rejected
or deferred.

### 15.2 Decision fingerprint

For every source and accepted decision, rebuild the normalized decision shape:

```text
candidate_id
rebuilt candidate_fingerprint_sha256
decision
claim_operation
claim_key
claim_status
evidence_relation
```

Its SHA-256 must equal
`LocalDocumentReviewCandidateDecision.decision_fingerprint_sha256`.

### 15.3 Full decision-copy equality

The projection loads all candidates and all source/accepted decision rows for each
bounded receipt session. It requires:

- every session candidate has exactly one source decision;
- every session candidate has exactly one accepted decision;
- source and accepted candidate-ID sets are identical;
- no accepted row is missing or added;
- every source/accepted pair matches exactly on:

```text
decision
claim_operation
claim_key
claim_status
evidence_relation
decision_fingerprint_sha256
```

A dropped, inserted, rebound or changed accepted decision invalidates the receipt.

## 16. Source review fingerprint replay

The source review fingerprint is rebuilt under:

```text
aquantai.local-document-review.v1
```

The exact canonical shape contains:

```text
review_session_id
revision_number
review_state
source_kind
evidence_grade
document_identity_candidate_id
subject_candidate_id
information_date
reviewer_note
candidate_decisions ordered by canonical candidate UUID
```

Each normalized candidate decision contains the exact fields from section 15.2.
The rebuilt fingerprint must equal both:

```text
source.review_fingerprint_sha256
receipt.source_review_fingerprint_sha256
```

Merely comparing two stored fingerprints without deterministic replay is not
sufficient.

## 17. Acceptance plan and request replay

### 17.1 Evidence fingerprint for selected facts/events

For every source decision satisfying:

```text
decision = selected
candidate_kind in {fact, event}
claim_operation = create_new_deterministic_claim
```

rebuild the Evidence fingerprint under:

```text
aquantai.local-document-evidence-item.v1
```

The exact shape contains content SHA, page, byte span, quote SHA, candidate kind
and reviewed statement.

### 17.2 Acceptance plan fingerprint

Rebuild the plan under `aquantai.local-document-acceptance.v1` from:

```text
source review revision ID
rebuilt source review fingerprint
expected session latest revision number = source revision number
target Research Case ID
content ID and SHA
extractor contract version
rebuilt document identity candidate fingerprint
rebuilt subject identity candidate fingerprint
source kind
evidence grade
information date
ordered selected entries
```

Each selected entry contains rebuilt candidate fingerprint, rebuilt decision
fingerprint, claim key, claim status, evidence relation and rebuilt Evidence
fingerprint. Ordering uses canonical candidate UUID.

### 17.3 Request fingerprint

Rebuild the acceptance request fingerprint from:

```text
source review revision ID
source revision number
rebuilt source review fingerprint
expected session latest revision number = source revision number
target Research Case ID
ordered selected candidate IDs
ordered selected decision fingerprints
recorded_at_utc = receipt.accepted_at_utc
acceptance_contract_version = aquantai.local-document-acceptance.v1
rebuilt acceptance plan fingerprint
```

The rebuilt value must equal `receipt.request_fingerprint_sha256`.

## 18. Accepted review fingerprint replay

Rebuild the accepted review fingerprint under:

```text
aquantai.local-document-accepted-review.v1
```

The exact shape contains:

```text
source review revision ID
rebuilt source review fingerprint
accepted revision number
review_state = accepted
rebuilt acceptance request fingerprint
rebuilt acceptance plan fingerprint
target Research Case ID
accepted_at_utc = receipt.accepted_at_utc
```

The rebuilt value must equal both:

```text
accepted.review_fingerprint_sha256
receipt.accepted_review_fingerprint_sha256
```

A source/accepted swap, candidate/decision/source/request/accepted fingerprint
mismatch or contract mismatch is `evidence_pack_integrity_error`.

## 19. Receipt-link completeness

For each receipt, the exact `LocalDocumentAcceptanceLink` set must equal the
selected source fact/event decisions defined in section 17.1.

There must be exactly one link per selected decision and no extra link. The
projection validates every sibling link under the bounded receipt even when the
linked Evidence Item was not the row that discovered the receipt.

A missing link, duplicate semantic binding, extra link or link to a non-selected
decision invalidates the complete receipt.

## 20. Exact produced Ledger graph

For each acceptance link, validate all exact v1 production semantics.

### 20.1 Candidate and Evidence

- candidate belongs to the receipt review session;
- candidate kind is `fact` or `event`;
- Evidence belongs to the requested Case;
- Evidence source kind and grade equal source revision values;
- Evidence source title and publisher equal the selected document identity
  payload;
- Evidence canonical locator is exactly:

```text
local-document:{content_id}#page={page_number}
&start_utf8_byte={start_utf8_byte}
&end_utf8_byte={end_utf8_byte}
```

- Evidence information date equals source information date;
- Evidence recorded time equals receipt accepted time;
- Evidence summary equals candidate statement;
- Evidence content fingerprint equals the rebuilt fingerprint;
- `EvidenceItem.supersedes_evidence_id = null`.

### 20.2 Claim and ClaimRevision

- Claim belongs to the requested Case;
- Claim key equals the selected decision claim key;
- Claim creation time equals receipt accepted time;
- ClaimRevision belongs to that Claim;
- `revision_no = 1`;
- statement equals candidate statement;
- `claim_kind = fact`;
- status equals selected decision claim status;
- `inference_confidence = null`;
- `inference_basis = null`;
- information cutoff equals source information date;
- recorded time equals receipt accepted time;
- `supersedes_revision_id = null`.

### 20.3 ClaimEvidenceLink and acceptance link

- ClaimEvidenceLink binds the exact linked ClaimRevision and Evidence;
- relation equals selected decision evidence relation;
- `link_note = null`;
- recorded time equals receipt accepted time;
- acceptance-link Evidence, Claim, ClaimRevision and ClaimEvidenceLink IDs equal
  those exact rows.

Any mismatch fails the whole pack. The projection cannot omit the broken sibling
link or downgrade the affected item to ledger-only.

## 21. Citation graph validation

For each linked fact/event candidate:

- review session points to the exact import attempt;
- import attempt points to immutable content;
- candidate belongs to the review session;
- candidate page number identifies an exact page under that content;
- offsets are a valid half-open UTF-8 byte interval and scalar boundaries;
- the stored byte slice decodes exactly to `quote_text`;
- quote SHA-256 equals the exact quote bytes;
- page text SHA-256 equals the exact stored page text;
- candidate and Evidence fingerprints recompute exactly;
- extractor/content identities remain exact.

The pack returns receipt/content/page/span/quote identifiers and citation metadata.
It does not return raw PDF bytes or whole page text.

When no acceptance link exists, provenance is `ledger_only`, even if a locator
resembles `local-document:` or a title resembles a filename. A present invalid
link cannot be omitted or downgraded.

## 22. Stable nested ordering

Evidence entries:

```text
information_date DESC
recorded_at_utc DESC
Evidence UUID ASC
```

Claim bindings:

```text
claim_key ASC
claim_revision_no ASC
relation ASC
ClaimRevision UUID ASC
```

Selected-revision roles:

```text
role ASC
CaseRevisionClaimLink UUID ASC
```

Document citations use receipt UUID then candidate UUID. UUID comparison uses
lowercase canonical strings across SQLite and PostgreSQL.

## 23. Cursor contract

The cursor is URL-safe base64 encoding of canonical compact JSON containing:

```text
contract_version
research_case_id
research_case_revision_id
information_cutoff_date
recorded_at_utc
limit
last_information_date
last_recorded_at_utc
last_evidence_id
payload_sha256
```

Canonical JSON uses sorted keys, compact separators, UTC `Z`, lowercase UUIDs,
no floats and no Unicode normalization. The checksum binds the cursor to the
exact request; it is not authentication.

Malformed tokens, unknown keys, version mismatch, checksum mismatch, boundary
mismatch or limit mismatch return `invalid_evidence_pack_cursor` before database
projection. Offset pagination is prohibited.

## 24. Response contract

```text
contract_version = aquantai.research-evidence-pack.v1
```

Top-level fields include:

```text
contract_version
research_case
selected_case_revision
information_cutoff_date
recorded_at_boundary_utc
visible_evidence_count
entries
next_cursor
notices
```

Each Evidence entry contains:

```text
evidence
claim_bindings[]
membership_summary
local_document_provenance | null
integrity_state
```

Each Claim binding contains:

```text
claim
claim_revision
claim_evidence_link
relation
research_membership_state
selected_case_revision_roles[]
supersession_reference
```

No entry-level scalar `research_membership_state` exists. Mixed membership is
represented by exact per-binding values plus:

```text
membership_summary = mixed_linked_and_unlinked_bindings
```

The pack may map closed codes to deterministic Chinese labels, but may not
summarize, rank, score, infer sentiment, generate causal explanations or rewrite
accepted text.

## 25. Empty and missing states

An exact visible Case revision with no visible Evidence Items returns HTTP 200:

```text
state = empty_evidence_pack
entries = []
next_cursor = null
```

Evidence without Claim links remains an entry with
`membership_summary = no_claim_bindings`. Evidence with Claim links but no roles
has per-binding `accepted_unlinked_to_selected_case_revision` and
`all_bindings_unlinked`.

Missing local provenance is not an error unless an acceptance link exists and its
receipt graph is invalid.

## 26. Error taxonomy

| Stable code | Meaning |
| --- | --- |
| `research_case_not_found` | exact Case absent |
| `research_case_revision_not_found` | exact revision absent |
| `research_case_revision_mismatch` | revision belongs to another Case |
| `research_case_revision_not_visible_as_of` | anchor outside a boundary |
| `invalid_evidence_pack_as_of` | boundary chronology invalid |
| `invalid_evidence_pack_cursor` | cursor malformed or request-mismatched |
| `evidence_pack_integrity_error` | accepted Evidence/Claim/receipt graph broken |
| `database_unavailable` | local database unavailable |

Ordinary-user copy must explain the next action without stack traces or claims
that retrying repairs corrupted accepted history.

## 27. Query architecture and exact ceiling

A later implementation may add a pack-specific read repository/query/rules family.
Direct set-based reads over accepted models are permitted because the module is a
projection, not an owner.

One page requires at most eight SQL statements:

1. exact Case and selected revision validation;
2. visible Evidence count;
3. bounded Evidence page;
4. Claim/ClaimRevision/ClaimEvidenceLink rows for page Evidence IDs;
5. selected Case-revision roles for reached Claim revisions;
6. complete bounded receipt/session/source+accepted revision/candidate/decision/
   sibling-link/Ledger rows plus a set-wise maximum-review-revision aggregate for
   every receipt reached from page Evidence IDs;
7. exact referenced `LocalDocumentPage` rows;
8. set-wise minimal Evidence/ClaimRevision supersession-target rows.

```text
maximum SQL statements per page = 8
maximum page size = 100 Evidence Items
writes per GET = 0
network calls = 0
OCR calls = 0
AI calls = 0
```

Statement 6 is bounded by at most 100 page Evidence Items, at most 100 discovered
receipts, and the existing maximum 200 candidates per receipt. It may use CTEs,
unions and set-wise aggregates and must include every sibling link for those
receipts. Per-item, per-Claim, per-receipt and per-citation query loops are
prohibited.

Future SQLite/PostgreSQL tests must measure the exact bound. If an additional
index or ninth statement is required for correctness, implementation must STOP
and return to Strict architecture.

## 28. Security and local boundary

- The route is read-only and performs no mutation.
- It exposes no filesystem path, credential, Provider payload or environment
  secret.
- Raw PDF bytes remain behind the existing exact attachment action.
- Whole page text remains behind the exact page read and is absent from pack
  payloads.
- No network is invoked by startup, read, tests or demo.
- Existing accepted user-authored text must be rendered with safe text semantics.

## 29. Persistence and lifecycle

```text
tables = unchanged
columns = unchanged
indexes = unchanged
migration = none
backfill = none
rollback = remove read surface only
downgrade = no data action
```

Reproducibility comes from exact IDs, boundaries, append-only owners and stable
pagination, not from saving opaque projection JSON.

## 30. Production-realistic offline golden path

The future fixture must use production-reachable commands:

1. create a Research Case and initial revision;
2. import a small embedded-text official PDF;
3. create document/company identity and multiple page/span fact/event candidates;
4. append a source review revision with complete decisions;
5. preview and atomically accept multiple selected facts/events through the
   existing owner, producing one receipt with multiple sibling links;
6. add one accepted ledger-only Evidence Item;
7. append the selected Research Case revision, linking one document ClaimRevision
   as `conclusion` and the ledger-only ClaimRevision as `context`;
8. create another visible Claim binding on one Evidence Item that is not linked to
   the selected Case revision, producing mixed membership;
9. accept another document fact without rewriting the selected Case revision;
10. create valid supersession targets, including a same-recorded-time target and
    an information-hidden target;
11. create a later Evidence Item outside the recorded boundary;
12. query with a page size that exercises the next cursor.

Expected result:

- all visible Evidence Items remain present;
- one entry shows exact linked and unlinked bindings simultaneously;
- `membership_summary` is `mixed_linked_and_unlinked_bindings`;
- ledger-only provenance remains `ledger_only`;
- document items expose exact citations only after full receipt replay;
- same-timestamp supersession passes owner-consistent integrity;
- the information-hidden target exposes only ID plus `not_visible_as_of`;
- the later Evidence Item is absent;
- pagination is stable and duplicate-free;
- reads perform zero writes/network/OCR/AI.

## 31. Decisive failure families

Each persisted corruption below must make the complete request return
`evidence_pack_integrity_error`, with no partially authoritative entries:

- receipt source and accepted revision IDs swapped;
- receipt/session/Case mismatch;
- candidate fingerprint mismatch;
- source or accepted decision fingerprint mismatch;
- source review fingerprint mismatch;
- receipt request fingerprint or acceptance-contract mismatch;
- accepted review fingerprint mismatch;
- accepted revision not the exact terminal immediate successor;
- accepted copy field differs from source;
- accepted decision missing, added, rebound or changed;
- receipt link missing, extra or bound to a non-selected decision;
- link claim key/status/relation differs from its decision;
- link points to the wrong Evidence/Claim/ClaimRevision/ClaimEvidenceLink;
- produced Ledger default/identity/chronology field differs from v1;
- candidate page/span/quote/fingerprint mismatch;
- Evidence fingerprint or canonical locator mismatch;
- supersession target missing, cross-owner, invalid revision order or recorded
  later than its successor.

Every failure performs zero writes and makes zero network/OCR/AI calls. Locator
parsing is never a fallback.

## 32. Required future validation

A later separately authorized implementation must cover:

- exact local-document plus ledger-only golden path;
- empty pack;
- Evidence without Claim links;
- all-linked and all-unlinked entries;
- one Evidence Item with linked and unlinked Claim bindings simultaneously;
- contradiction/context visibility and deterministic ordering;
- valid equal-timestamp Evidence and ClaimRevision supersession targets;
- valid information-hidden supersession targets without payload projection;
- missing, cross-Case/cross-Claim, invalid revision-order and later-recorded
  targets;
- exact unlinked accepted document evidence;
- Case/revision mismatch and both as-of boundaries;
- later Evidence/Claim/receipt invisibility;
- malformed and cross-request cursor;
- stable pagination with identical timestamps;
- every receipt-transition failure family in section 31;
- locator resembling local provenance without an acceptance link;
- 1, 50 and 100 member SQL ceilings on SQLite and PostgreSQL;
- zero writes, network, Provider, OCR and AI;
- safe rendering of persisted user text;
- full configured regression and all offline demos.

## 33. Expected implementation classification

After this architecture PR is independently approved and separately merged, a
new implementation Issue may classify as Standard only if it preserves:

- existing schema and owner contracts;
- read-only pack-specific projection;
- exact dual-as-of selectors;
- authoritative per-binding membership;
- complete candidate/decision/source/request/accepted receipt replay;
- bounded owner-consistent supersession target loads;
- no more than eight SQL statements;
- zero network/OCR/AI and zero accepted-state mutation;
- separate explicit owner authorization.

Any persistent pack, accepted-owner change, acquisition path or contract
expansion returns the work to Strict architecture.

## 34. Inactive future implementation boundary

Expected new read-only files may include:

```text
industry_alpha/research_evidence_pack_contracts.py
industry_alpha/research_evidence_pack_repository.py
industry_alpha/research_evidence_pack_query.py
industry_alpha/research_evidence_pack_rules.py
backend/api/research_evidence_pack.py
tests/test_research_evidence_pack_*.py
scripts/demo_research_evidence_pack.py
```

`backend/main.py`, static UI files and workflow registration may be included only
by the later implementation Issue. No existing write-owner file is implicitly
authorized.

## 35. Locked exclusions

- production code in this architecture PR;
- schema/migration/dependency/configuration changes;
- persisted pack/snapshot/selection/export history;
- Provider, network, credential or external acquisition;
- OCR, NLP, AI generation or automatic acceptance;
- fuzzy identity or hidden latest/default selection;
- Evidence Ledger, Document Import, Research Case or downstream research writes;
- Investment Candidate scoring, valuation recomputation or recommendation;
- target price, expected return, position sizing, portfolio, broker or trading;
- background work, polling, scheduler or notification;
- release, tag or version change;
- PR #241 modification.

## 36. STOP conditions

STOP and request a separately authorized architecture revision if:

1. a durable pack, selection, export or preference must be persisted;
2. an additional index, migration or ninth SQL statement is necessary;
3. Evidence Ledger or Document Import write owners must change;
4. complete receipt replay cannot be performed set-wise and fail closed;
5. exact provenance would require source-locator/path/title/company/ticker or
   similarity authority;
6. any broken accepted graph would be partially omitted or downgraded;
7. target payload fields beyond the closed minimal supersession set are needed;
8. Provider, network, credential, OCR, AI or automatic acceptance appears;
9. recommendation, portfolio or trading meaning appears;
10. any file outside the authorized architecture or future implementation scope
    becomes necessary without an Issue amendment.

## 37. Current architecture allowlist

Exactly these two files may change in PR #289:

```text
.codex/tasks/issue-288-research-evidence-pack-v1-preflight.md
docs/research_evidence_pack_v1_preflight.md
```

No production, schema, migration, workflow, test or fixture file is authorized.

## 38. Delivery gates

The architecture PR must:

- remain based on exact `8dd187c129c3e4a375f550758fab266719ccd0da`;
- change exactly the Issue #288 task snapshot and this document;
- remain Draft;
- pass full repository CI on one exact immutable new HEAD;
- receive a fresh process-independent fixed-HEAD architecture review with zero
  blocking findings and the exact phrase:

```text
AUTHORIZED RESEARCH EVIDENCE PACK V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

Any new commit invalidates prior fixed-HEAD CI and review evidence. Architecture
approval does not authorize Ready, merge, Issue closure or implementation. Each
requires separate project-owner authorization.
