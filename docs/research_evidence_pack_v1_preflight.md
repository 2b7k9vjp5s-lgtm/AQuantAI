# Research Evidence Pack v1 — Strict Architecture Preflight

## 1. Status and authority

This architecture preflight is governed by Issue #288 and Roadmap #137. It starts
from exact `main@8dd187c129c3e4a375f550758fab266719ccd0da` after the merge of
Manual Official PDF Import and Evidence Ledger Review v1.

The project owner authorized exactly two architecture artifacts. This document
contains no production implementation authority. It does not authorize schema,
migration, dependency, API/UI, fixture, test, workflow, Provider/network, OCR,
AI, automatic evidence acceptance, recommendation, portfolio, trading, release,
tag, version, Ready, merge, Issue closure or PR #241 changes.

Risk classification is Strict because the proposed read surface crosses frozen
Evidence Ledger and local-document provenance boundaries. The intended later
implementation remains read-only and may qualify as Standard only if every
decision in this preflight is preserved without a new owner or schema.

## 2. Product problem

The local PDF flow can now accept exact page-cited facts into the Evidence Ledger,
and the industry-research flow can produce an exact historical research result.
The ordinary user still lacks one bounded view that answers:

> For this exact Research Case revision and historical boundary, which accepted
> evidence exists, which exact Claims does it support or contradict, which items
> are already part of the selected research snapshot, and where can I inspect the
> original local PDF citation?

The global Evidence Intelligence feed is chronological rather than Case-pack
oriented. The existing Evidence Ledger detail returns the whole visible Case graph
under a date-only cutoff. The Document Import detail starts from an exact receipt
or review identity. None is the required bounded, dual-as-of, Evidence-first
projection.

## 3. Product boundary

Research Evidence Pack v1 is:

- local and read-only;
- anchored to one explicit Research Case and one explicit Research Case revision;
- bounded by one information date and one recorded UTC timestamp;
- Evidence-first and stably paginated;
- exhaustive for visible accepted Evidence Items in the selected Case, page by
  page, without claiming that all items are already part of the selected Case
  revision;
- exact about Claim, role and local-document provenance links;
- deterministic and zero-network/zero-AI.

It is not:

- a persisted pack or saved snapshot;
- a document inbox, Provider catalog or acquisition workflow;
- an automatic research refresh;
- an AI summary, sentiment classifier or evidence generator;
- an Evidence Ledger acceptance path;
- a candidate scorer, recommendation or portfolio feature.

## 4. Existing authoritative owners

### 4.1 Research Case

`ResearchCase` owns stable Case identity. `ResearchCaseRevision` owns append-only
research question, summary, workflow/conclusion state, information cutoff,
recorded time and supersession history.

The exact Case revision supplied in the request is the research-snapshot anchor.
The pack never chooses a latest Case revision.

### 4.2 Evidence Ledger

Accepted meaning remains owned by:

| Meaning | Owner |
| --- | --- |
| Accepted source metadata and evidence grade | `EvidenceItem` |
| Stable Claim identity | `Claim` |
| Exact Claim statement/status/history | `ClaimRevision` |
| Evidence relation | `ClaimEvidenceLink` |
| Claim role in one exact Case revision | `CaseRevisionClaimLink` |
| Accepted writes and invariants | `EvidenceLedgerCommandService` |

The pack is not permitted to create or mutate any of these rows.

### 4.3 Local Document Import

| Meaning | Owner |
| --- | --- |
| Immutable PDF bytes/extractor provenance | `LocalDocumentContent` |
| User import occurrence and filename | `LocalDocumentImportAttempt` |
| Exact stored page text and page fingerprint | `LocalDocumentPage` |
| Case-scoped review identity | `LocalDocumentReviewSession` |
| Page/span/quote and user statement | `LocalDocumentCandidate` |
| Append-only reviewed decision | `LocalDocumentReviewRevision` and decision rows |
| Atomic accepted transition | `LocalDocumentAcceptanceReceipt` |
| Exact Document-to-Ledger graph | `LocalDocumentAcceptanceLink` |

`LocalDocumentAcceptanceLink.evidence_item_id` is unique. Its presence is the
only authority for classifying an Evidence Item as accepted through the local
Document Import path.

### 4.4 Existing reads

`EvidenceLedgerRepository.load_case` loads a complete Case graph and
`EvidenceLedgerQueryService` filters it by a single date cutoff. That contract is
retained for existing callers. It must not be silently reinterpreted as a
dual-as-of, bounded pack.

`DocumentImportQueryService.acceptance_detail` starts from one receipt and proves
one exact accepted graph. It remains the exact receipt detail owner. The pack may
project the same immutable rows set-wise for bounded Evidence IDs, but may not
change receipt semantics.

## 5. Owner and schema audit result

The exact base contains every required authoritative identity and relationship
for a transient projection:

- Evidence rows carry exact Case and dual-time fields;
- Claim revisions and relations carry exact IDs and chronology;
- Case-revision links preserve frozen research membership/role;
- acceptance links freeze Evidence, Claim, ClaimRevision and relation IDs;
- receipt/session/import/content/candidate/page rows preserve the document path;
- append-only constraints prevent later rewrite of the historical graph;
- existing uniqueness supports deterministic joins.

Therefore:

```text
read_only_projection_reachable = true
saved_pack_reachable = false
new_owner_for_v1 = none
existing_write_owner_change = none
schema_change = none
migration = none
backfill = none
```

The absence of a saved-pack owner is intentional. It becomes a STOP condition,
not permission to put opaque pack JSON into an existing field.

## 6. Core architecture decision

The pack is composed in three explicit layers.

### Layer A — Frozen research anchor

The request supplies an exact Case and Case revision. Layer A validates identity,
ownership and dual-as-of visibility. It exposes persisted Case revision fields
only and writes nothing.

### Layer B — Visible accepted case evidence

Layer B pages all accepted `EvidenceItem` rows belonging to the Case and visible
under both boundaries. Each entry preserves exact source metadata and every
visible Claim relation reached through explicit links.

Layer B does not require the Evidence Item to be linked to the selected Case
revision. This is essential because Document Import accepts Evidence/Claim rows
but does not automatically rewrite a Research Case revision.

### Layer C — Exact provenance enrichment

Layer C optionally enriches an Evidence Item through an exact
`LocalDocumentAcceptanceLink`. It revalidates the entire accepted document graph
and exposes citation metadata. It never classifies provenance from free text.

### Prohibited collapse

The following equation is false and prohibited:

```text
accepted Evidence Ledger item
= already accepted conclusion in selected Research Case revision
```

Only `CaseRevisionClaimLink` assigns a ClaimRevision a `conclusion`, `context` or
`risk` role in the selected frozen revision.

## 7. Canonical route and selectors

The future canonical read route is:

```text
GET /research-evidence-pack/api/cases/{research_case_id}/revisions/{research_case_revision_id}
```

Query fields:

| Field | Required | Contract |
| --- | --- | --- |
| `information_cutoff_date` | yes | ISO date |
| `recorded_at_utc` | yes | timezone-aware RFC3339 normalized to UTC |
| `limit` | no | default 50, closed range 1..100 |
| `cursor` | no | opaque request-bound keyset cursor |

No route without an exact Case revision is canonical in v1. A UI may help the
user navigate from an existing exact Case history surface, but it may not submit
an omitted revision and ask the server to choose.

## 8. Dual-as-of semantics

The request is valid only when:

```text
information_cutoff_date <= recorded_at_utc UTC date
```

Visibility rules are:

| Row | Information boundary | Recorded boundary |
| --- | --- | --- |
| selected Case revision | `information_cutoff_date` | `recorded_at_utc` |
| Evidence Item | `information_date` | `recorded_at_utc` |
| ClaimRevision | `information_cutoff_date` | `recorded_at_utc` |
| ClaimEvidenceLink | n/a | `recorded_at_utc` |
| CaseRevisionClaimLink | anchored exact revision | `recorded_at_utc` |
| document accepted revision | `information_date` | `recorded_at_utc` |
| document receipt | through accepted revision | `accepted_at_utc` |
| candidate/import/content | n/a | each available created/recorded timestamp |

A row outside either applicable boundary is unavailable. It is not replaced with
another revision.

## 9. Evidence-page membership

The top-level page member is one exact Evidence Item. It is eligible only when:

```text
case_id = requested Research Case
information_date <= requested information cutoff
recorded_at_utc <= requested recorded boundary
```

The projection preserves Evidence Items even when they have no visible Claim
relation. This produces an explicit state rather than silent loss.

Closed `research_membership_state` values are:

```text
linked_to_selected_case_revision
accepted_unlinked_to_selected_case_revision
accepted_evidence_without_claim_link
```

If an Evidence Item has multiple Claim relations, each exact relation appears.
If at least one related ClaimRevision has a selected-revision role, that binding
is linked; other bindings remain independently classified.

## 10. Claim binding contract

For every Evidence entry, the pack loads Claim bindings set-wise and verifies:

- `ClaimEvidenceLink.evidence_id` equals the entry ID;
- its exact ClaimRevision exists and is visible;
- the ClaimRevision belongs to an exact Claim in the requested Case;
- relation is the persisted `supports`, `contradicts` or `context` value;
- any selected-revision role comes from an exact visible
  `CaseRevisionClaimLink` whose Case revision equals the request anchor;
- no other Case revision role is substituted.

The pack never selects a latest ClaimRevision. It returns the exact revisions
reached by visible ClaimEvidenceLinks for the current Evidence page.

Evidence and Claim supersession chains remain explicit. A present
`EvidenceItem.supersedes_evidence_id` must identify an older recorded Evidence
Item in the same Case. A present `ClaimRevision.supersedes_revision_id` must
identify an older recorded revision of the same Claim. Both old and new visible
rows remain available; supersession is never a hidden latest selector. A target
outside the information boundary is returned only as an exact ID with
`not_visible_as_of`, not loaded or substituted. Missing, cross-Case, cross-Claim
or forward-recorded supersession targets are graph integrity failures.

## 11. Local-document provenance contract

### 11.1 Authority

`LocalDocumentAcceptanceLink` is authoritative. `EvidenceItem.source_locator` is
not a selector and is not parsed to discover content, page or offsets.

### 11.2 Required exact graph

When an acceptance link exists, the pack revalidates:

```text
EvidenceItem
<- LocalDocumentAcceptanceLink
-> LocalDocumentAcceptanceReceipt
-> LocalDocumentReviewSession
-> LocalDocumentImportAttempt
-> LocalDocumentContent
-> LocalDocumentCandidate
-> LocalDocumentPage
```

It also verifies the acceptance link's exact Claim, ClaimRevision and
ClaimEvidenceLink against the Evidence entry and the receipt target Case.

### 11.3 Citation validation

For one fact/event candidate:

- page number must identify an exact page under the content;
- offsets use the stored half-open UTF-8 byte interval;
- both offsets must be valid UTF-8 scalar boundaries;
- the exact byte slice must decode to `quote_text`;
- quote SHA-256 and page text SHA-256 must match stored values;
- Evidence statement/summary, ClaimRevision statement and candidate statement
  must retain the accepted v1 graph meaning;
- Evidence content fingerprint and canonical locator must match the accepted v1
  command contract.

The pack returns exact IDs, page, offsets, quote, quote fingerprint and content
fingerprint. It does not return raw PDF bytes or whole page text.

### 11.4 Ledger-only state

When no acceptance link exists, provenance state is:

```text
ledger_only
```

This remains true even if a locator begins with `local-document:` or a title
resembles an imported filename. No heuristic may upgrade it.

### 11.5 Integrity failure

A present acceptance link asserts an exact accepted graph. Any mismatch is a
material integrity failure. The entire request fails closed; the projection does
not omit the row or downgrade it to `ledger_only`.

## 12. Stable ordering

Evidence entries use:

```text
EvidenceItem.information_date DESC
EvidenceItem.recorded_at_utc DESC
EvidenceItem.id ASC
```

Nested Claim bindings use:

```text
Claim.claim_key ASC
ClaimRevision.revision_no ASC
ClaimEvidenceLink.relation ASC
ClaimRevision.id ASC
```

Nested selected-revision roles use:

```text
CaseRevisionClaimLink.role ASC
CaseRevisionClaimLink.id ASC
```

Nested document citations use receipt UUID then candidate UUID. UUID comparison
uses lowercase canonical strings so SQLite and PostgreSQL output agree.

## 13. Cursor contract

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
no floats and no Unicode normalization. `payload_sha256` detects corruption and
binds the cursor to the exact request; it is not authentication.

Malformed tokens, unknown keys, version mismatch, checksum mismatch, boundary
mismatch or limit mismatch return `invalid_evidence_pack_cursor` before database
projection. Offset pagination is prohibited.

## 14. Response contract

Contract version:

```text
aquantai.research-evidence-pack.v1
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

Each entry contains:

```text
evidence
claim_bindings[]
research_membership_state
local_document_provenance | null
integrity_state
```

The pack renders persisted Evidence and Claim statements. It may map closed
codes to deterministic Chinese labels, but may not summarize, rank, score,
infer sentiment, generate causal explanations or rewrite accepted text.

## 15. Empty and missing states

An exact visible Case revision with no visible Evidence Items returns HTTP 200
with:

```text
state = empty_evidence_pack
entries = []
next_cursor = null
```

This state triggers no acquisition, import, fallback, AI call or write.

Evidence without Claim links remains an entry. Evidence with Claim links but no
selected-revision role is explicitly unlinked. Missing local provenance is not an
error unless an acceptance link exists and its graph is invalid.

## 16. Error taxonomy

| Stable code | Meaning |
| --- | --- |
| `research_case_not_found` | exact Case absent |
| `research_case_revision_not_found` | exact revision absent |
| `research_case_revision_mismatch` | revision belongs to another Case |
| `research_case_revision_not_visible_as_of` | anchor outside a boundary |
| `invalid_evidence_pack_as_of` | boundary chronology invalid |
| `invalid_evidence_pack_cursor` | cursor malformed or request-mismatched |
| `evidence_pack_integrity_error` | accepted Evidence/Claim/document graph broken |
| `database_unavailable` | local database unavailable |

Ordinary-user copy must explain the action: choose a valid historical boundary,
return to exact Case history, or run integrity checks. It must not expose stack
traces or imply that retrying will repair corrupted accepted history.

## 17. Query architecture

A later implementation should add a pack-specific read repository/query/rules
family. Direct set-based reads over accepted models are permitted because the
module is a projection, not an owner. Existing write owners and exact-detail
queries remain unchanged.

One page requires at most:

1. exact Case/selected revision validation;
2. visible Evidence count;
3. bounded Evidence page;
4. Claim/ClaimRevision/ClaimEvidenceLink rows for page IDs;
5. selected Case-revision roles for those Claim revisions;
6. local acceptance receipt/session/import/content/candidate graph for page IDs;
7. exact referenced page rows;
8. one remaining bounded validation query if required.

```text
maximum SQL statements per page = 8
maximum page size = 100 Evidence Items
writes per GET = 0
```

The SQL count is independent of nested relation and citation counts within the
bounded page. Per-item, per-Claim and per-page query loops are prohibited.

The existing indexes are sufficient to state the correctness contract, not to
pre-authorize an unmeasured performance assumption. Future SQLite/PostgreSQL
tests must measure the bounded query. If the ceiling or acceptable bounded local
latency cannot be met without an additional index, implementation must trigger
the schema STOP condition and return to Strict architecture.

## 18. Security and local boundary

- The route is read-only; no CSRF token is needed for GET.
- It exposes no filesystem path, credential, Provider payload or environment
  secret.
- Raw PDF bytes require the existing exact explicit attachment action; the pack
  does not inline them.
- Whole page text remains behind the existing exact page read and is not included
  in list payloads.
- No network is invoked by import, startup, pack read, tests or demo.
- No wildcard CORS or remote-origin mutation is introduced.
- Existing accepted text may contain user-authored content and must be rendered
  with safe text semantics by any future UI.

## 19. Persistence and lifecycle

There is no persisted pack identity or mutable state:

```text
tables = unchanged
columns = unchanged
indexes = unchanged
migration = none
backfill = none
rollback = remove read surface only
downgrade = no data action
```

Reproducibility comes from explicit Case/revision IDs, dual-as-of boundaries,
append-only owners and stable pagination—not from saving opaque projection JSON.

## 20. Production-realistic offline golden path

The future fixture must use production-reachable commands:

1. create a Research Case and its initial revision;
2. import a small embedded-text official PDF through the actual local import
   boundary;
3. create user-owned document/company identity and page/span fact candidates;
4. append an explicit reviewed revision;
5. preview and atomically accept one exact candidate through
   `EvidenceLedgerCommandService`;
6. add one accepted ledger-only Evidence/Claim relation;
7. append the exact selected Research Case revision through the existing owner,
   linking the document ClaimRevision as `conclusion` and the ledger-only
   ClaimRevision as `context` in that same atomic Case-revision command;
8. accept a second local-document fact into the same Case after the selected Case
   revision without linking it to a later Case revision;
9. create a later Evidence Item outside the recorded boundary;
10. query the pack, anchored to the exact revision from step 7, with a page size
    that exercises a next cursor.

Expected result:

- the first local item is exact document provenance plus `conclusion`;
- the ledger-only item remains `ledger_only` plus `context`;
- the second local item retains exact citation and is explicitly accepted but
  unlinked to the selected research snapshot;
- the later item is absent;
- the next page is stable and duplicate-free;
- all reads perform zero writes/network/AI.

## 21. Decisive failure path

Construct a persisted integrity-failure fixture in which a present
`LocalDocumentAcceptanceLink` for a visible Evidence Item references a candidate
whose page/span or exact Claim graph does not match the receipt-bound accepted
graph.

The read must:

- return `evidence_pack_integrity_error`;
- return no partially authoritative entries;
- perform zero writes;
- make zero network, OCR or AI calls;
- avoid parsing `EvidenceItem.source_locator` as fallback.

This failure proves provenance authority rather than merely UI rendering.

## 22. Required future validation

A later separately authorized implementation must cover:

- exact local-document + ledger-only golden path;
- empty pack;
- Evidence without Claim link;
- multiple Claim relations and selected-revision roles;
- contradiction visibility;
- exact unlinked accepted document evidence;
- Case/revision mismatch and both as-of boundaries;
- later Evidence/Claim/receipt invisibility;
- malformed and cross-request cursor;
- stable pagination with identical timestamps;
- local-document receipt/candidate/page/span/quote/Claim graph corruption;
- source locator that resembles a local locator without an acceptance link;
- 1, 50 and 100 member SQL ceilings on SQLite and PostgreSQL;
- zero writes, network, Provider, OCR and AI;
- safe rendering of persisted user text;
- full configured regression and offline demos.

## 23. Expected implementation classification

After this architecture PR is independently approved and separately merged, a
new implementation Issue may classify as Standard only if it preserves:

- existing schema and owner contracts;
- read-only pack-specific projection;
- exact dual-as-of selectors;
- zero network/AI and zero accepted-state mutation;
- bounded set-based queries;
- separate explicit owner merge authorization.

Any persistent pack, source acquisition, accepted-owner change or core contract
expansion returns the work to Strict architecture.

## 24. Inactive future implementation boundary

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

`backend/main.py`, a future static UI family and workflow registration may be
included only by the later implementation Issue. No existing write-owner file is
implicitly authorized.

## 25. Locked exclusions

- production code in the architecture PR;
- schema/migration/dependency/configuration changes;
- persisted pack/snapshot/selection/export history;
- Provider, network, credential, external disclosure catalog or download;
- OCR, NLP, AI generation, automatic candidate creation or automatic acceptance;
- fuzzy document/company identity or hidden latest/default selection;
- Evidence Ledger, Document Import, Research Case or downstream research writes;
- Investment Candidate scoring, valuation recomputation or recommendations;
- target price, expected return, position sizing, portfolio, broker or trading;
- background work, polling, scheduler, notification;
- release, tag or version change;
- PR #241 modification.

## 26. STOP conditions

STOP and request a separately authorized architecture revision if:

1. a durable pack, selection, export or user preference must be persisted;
2. an existing index is insufficient and schema/migration becomes necessary;
3. Evidence Ledger or Document Import write owners must change;
4. exact provenance cannot be reached from `LocalDocumentAcceptanceLink`;
5. source-locator text, filesystem path, title, company name, ticker or similarity
   would become authority;
6. the complete accepted graph cannot fail closed without partial omission;
7. a Provider, network, credential, OCR, AI or automatic acceptance path appears;
8. recommendation, portfolio or trading meaning appears;
9. any file outside the authorized architecture or future implementation scope
   becomes necessary without an Issue amendment.

## 27. Delivery gates

The architecture PR must:

- remain based on exact `8dd187c129c3e4a375f550758fab266719ccd0da`;
- change exactly the Issue #288 task snapshot and this document;
- remain Draft;
- pass repository CI on one exact immutable HEAD;
- receive a fresh process-independent fixed-head review with zero blocking
  findings and the exact phrase:

```text
AUTHORIZED RESEARCH EVIDENCE PACK V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

Any new commit invalidates prior fixed-head CI and review evidence. Architecture
approval does not authorize Ready, merge, Issue closure or implementation. Each
requires separate project-owner authorization.
