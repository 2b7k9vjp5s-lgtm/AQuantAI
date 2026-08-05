# Issue #288 — Research Evidence Pack v1 Strict Architecture Preflight

## Authority

Project-owner architecture authorization received on 2026-08-05:

> 批准从 main@8dd187c129c3e4a375f550758fab266719ccd0da
> 启动 Research Evidence Pack v1 Strict Architecture Preflight；
> 仅允许两份架构工件。

Project-owner repair authorization received on 2026-08-05:

> 授权修复 PR #289 上述三项架构阻断；仅修改现有两份架构工件，
> 产生新 HEAD 后运行完整 CI，并重新进行独立 fixed-HEAD 架构审核。

This snapshot freezes architecture only. It authorizes no production code,
schema, migration, dependency, API/UI implementation, fixture, test, workflow,
Provider, network, credential, OCR, AI, automatic evidence acceptance,
recommendation, portfolio, trading, release, tag, version, Ready transition,
merge, Issue closure or PR #241 modification.

## Exact start and governance

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
base_branch = main
base_sha = 8dd187c129c3e4a375f550758fab266719ccd0da
roadmap = #137
issue = #288
pull_request = #289
risk_tier = Strict Architecture Preflight
implementation_authorized = false
```

The exact base passed `Local Tests #1069`, run `30988479592`, job
`92248720124`. PR #241 remains closed, Draft, unmerged and read-only at
`3116a67ec472131eea3bf3d1bd9daee884c69ee9`.

The first reviewed candidate,
`a06318e833d7ebca67cc90ef0cb8d484ccf0f66e`, is superseded. Its CI and review
cannot authorize any later HEAD.

## Repair closure

The first independent fixed-HEAD review recorded three High blockers. This
revision closes them by freezing:

1. complete set-wise replay of every bounded local-document acceptance receipt,
   including source and accepted revisions, candidate and decision fingerprints,
   exact copied decisions, request/plan/accepted fingerprints and all receipt
   links;
2. authoritative membership on each exact Claim binding, with a closed Evidence
   summary that represents mixed linked/unlinked bindings without information
   loss;
3. one bounded set-wise minimal supersession-target load used only for identity
   and chronology validation, with target payload excluded from the response.

No other architecture boundary expands.

## Product objective

Research Evidence Pack v1 is one deterministic, local, read-only projection for
an explicit Research Case revision. It exposes:

- the exact selected Case and Case revision;
- all accepted Evidence Items visible at explicit information and recorded-time
  boundaries;
- every exact visible ClaimRevision and ClaimEvidenceLink reached from each item;
- exact selected-revision roles and per-binding membership;
- local-PDF citation metadata only after an intact receipt transition is proved;
- explicit empty, unlinked, conflict and unavailable states without inference.

It is not a saved pack, accepted-state owner, acquisition flow, generated summary,
score, recommendation or trading surface.

## Existing authoritative owners

1. `ResearchCase` and `ResearchCaseRevision` own Case identity and frozen research
   revisions.
2. `EvidenceItem`, `Claim`, `ClaimRevision`, `ClaimEvidenceLink` and
   `CaseRevisionClaimLink` own accepted Evidence Ledger meaning.
3. `EvidenceLedgerCommandService` remains the sole accepted Evidence Ledger write
   owner and is outside the future read implementation boundary.
4. `LocalDocumentContent`, `LocalDocumentImportAttempt`, `LocalDocumentPage`,
   `LocalDocumentReviewSession`, `LocalDocumentCandidate`,
   `LocalDocumentReviewRevision`, `LocalDocumentReviewCandidateDecision`,
   `LocalDocumentAcceptanceReceipt` and `LocalDocumentAcceptanceLink` own the
   local-document acceptance proof.
5. `LocalDocumentAcceptanceLink.evidence_item_id` is unique and is the only
   authority for local-document provenance. `EvidenceItem.source_locator` is
   descriptive and must never be parsed as authority.
6. No persisted Evidence Pack, saved selection, export history or pack-snapshot
   owner exists.

```text
existing_owner_sufficient_for_read_projection = true
existing_owner_sufficient_for_saved_pack = false
schema_required_for_v1 = false
migration_required_for_v1 = false
new_write_owner_required = false
owner_modification_required = false
```

## Canonical request

```text
GET /research-evidence-pack/api/cases/{research_case_id}/revisions/{research_case_revision_id}
    ?information_cutoff_date=YYYY-MM-DD
    &recorded_at_utc=<UTC RFC3339 timestamp>
    &limit=<1..100, default 50>
    [&cursor=<opaque request-bound keyset cursor>]
```

Rules:

- both IDs are explicit UUIDs and the revision must belong to the Case;
- `information_cutoff_date <= recorded_at_utc.date()`;
- the exact Case revision must be visible at both applicable boundaries;
- no latest, newest, only-option, same-name, same-ticker or unique-reachable
  selection is permitted;
- the cursor binds contract version, both IDs, both boundaries, limit and the
  final ordering tuple;
- malformed/mismatched cursors fail before row projection;
- limits outside `1..100` fail rather than clamp.

## Evidence visibility and pagination

An Evidence Item is eligible only when:

```text
EvidenceItem.case_id = research_case_id
EvidenceItem.information_date <= information_cutoff_date
EvidenceItem.recorded_at_utc <= recorded_at_utc
```

Stable order is:

```text
information_date DESC
recorded_at_utc DESC
evidence_id ASC
```

All UUID ordering uses lowercase canonical strings. Offset pagination is
prohibited.

## Claim binding and membership

Every returned Claim binding preserves exact Claim, ClaimRevision and
ClaimEvidenceLink IDs and the persisted relation. The Claim belongs to the
requested Case and every time-bearing row is visible at the recorded boundary.
No latest ClaimRevision is selected.

Each `claim_bindings[]` member has one authoritative state:

```text
linked_to_selected_case_revision
accepted_unlinked_to_selected_case_revision
```

A binding is linked only through one or more exact visible
`CaseRevisionClaimLink` rows for that exact ClaimRevision and selected Case
revision. Exact role and link IDs are returned.

The Evidence entry has no scalar `research_membership_state`. It has only a
derived `membership_summary`:

```text
no_claim_bindings
all_bindings_linked
all_bindings_unlinked
mixed_linked_and_unlinked_bindings
```

The summary is computed from the complete binding set and never replaces a
binding. One Evidence Item may contain linked and unlinked bindings
simultaneously. Evidence without a visible ClaimEvidenceLink remains visible with
`no_claim_bindings`.

Nested order is deterministic:

```text
Claim.claim_key ASC
ClaimRevision.revision_no ASC
ClaimEvidenceLink.relation ASC
ClaimRevision.id ASC
CaseRevisionClaimLink.role ASC
CaseRevisionClaimLink.id ASC
```

## Supersession integrity

Supersession IDs remain explicit history and never become implicit current-row
selectors.

For every non-null `EvidenceItem.supersedes_evidence_id` and
`ClaimRevision.supersedes_revision_id` reached by the page, the projection may
perform one bounded set-wise minimal target load, including targets outside the
information boundary solely for integrity validation.

Allowed target columns are exactly:

```text
Evidence target:
  id, case_id, information_date, recorded_at_utc

ClaimRevision target:
  id, claim_id, revision_no, information_cutoff_date, recorded_at_utc
```

Validation follows the accepted command owner chronology exactly:

- every target exists;
- an Evidence target belongs to the same Case and
  `target.recorded_at_utc <= successor.recorded_at_utc`;
- a ClaimRevision target belongs to the same Claim, has a lower revision number,
  and `target.recorded_at_utc <= successor.recorded_at_utc`;
- equality of recorded timestamps is valid and must not fail integrity;
- no target statement, summary, source metadata, quote, page text or other payload
  field is loaded through this path.

A valid target outside the information boundary is represented only by exact ID
plus `not_visible_as_of`. Missing, cross-owner, invalid revision order or
later-recorded targets fail the whole request as `evidence_pack_integrity_error`.

## Complete local-document acceptance proof

An Evidence Item receives local-document provenance only when an exact
`LocalDocumentAcceptanceLink` exists. If any page item reaches a receipt, the
projection validates the complete receipt transition and every sibling receipt
link set-wise. Validating only the page link is prohibited.

### Receipt, session and revision identity

The following must all hold:

- receipt, session, source revision and accepted revision exist;
- all four share the exact review-session identity;
- receipt target Case, session target Case and requested Case are identical;
- source state is `draft` or `deferred`;
- accepted state is `accepted`;
- source recorded time is not after receipt accepted time;
- receipt accepted time equals accepted revision recorded time and is visible;
- accepted information date is visible;
- receipt contract is `aquantai.local-document-acceptance.v1`;
- receipt source/accepted fingerprints equal the corresponding persisted revision
  fingerprints.

The accepted revision is the exact terminal immediate successor:

```text
accepted.revision_number = source.revision_number + 1
accepted.expected_previous_revision_number = source.revision_number
accepted.supersedes_review_revision_id = source.id
accepted.review_session_id = source.review_session_id
accepted is the maximum revision number in that review session
```

Accepted source kind, evidence grade, document identity candidate, subject
candidate, information date and reviewer note are exact source copies.

### Candidate and decision fingerprint replay

For every candidate in the receipt review session, the projection rebuilds
`candidate_fingerprint_sha256` under
`aquantai.local-document-candidate.v1` from exact content identity, extractor
contract, candidate kind, citation fields, quote SHA, statement and parsed
canonical payload.

For every source and accepted decision, the projection rebuilds
`decision_fingerprint_sha256` from exact candidate ID, rebuilt candidate
fingerprint, decision, claim operation, claim key, claim status and evidence
relation.

All candidates must have exactly one source decision and exactly one accepted
decision. Source and accepted decision sets must have identical candidate IDs and
match exactly on:

```text
decision
claim_operation
claim_key
claim_status
evidence_relation
decision_fingerprint_sha256
```

Missing, added, rebound or changed accepted decisions are integrity failures.

### Source review fingerprint replay

The source review fingerprint is rebuilt under
`aquantai.local-document-review.v1` from:

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
all normalized source decisions ordered by candidate UUID
```

The rebuilt value must equal both the source revision fingerprint and the
receipt source fingerprint.

### Plan, request and accepted-review replay

For each selected fact/event candidate, rebuild the Evidence fingerprint under
`aquantai.local-document-evidence-item.v1`.

Rebuild the acceptance plan from exact source revision, session, content,
document/subject identity candidates and ordered selected decisions. Rebuild the
request fingerprint from:

```text
source revision ID and number
rebuilt source review fingerprint
expected session latest number = source revision number
target Case ID
ordered selected candidate IDs
ordered selected decision fingerprints
recorded_at_utc = receipt.accepted_at_utc
acceptance contract version
rebuilt plan fingerprint
```

The rebuilt request fingerprint must equal the receipt value.

Rebuild the accepted review fingerprint under
`aquantai.local-document-accepted-review.v1` from source ID/fingerprint,
accepted successor number/state, rebuilt request/plan fingerprints, target Case
and accepted time. It must equal both accepted revision and receipt values.

### Receipt-link completeness and Ledger semantics

For each receipt, the exact link set equals source decisions where:

```text
decision = selected
candidate_kind in {fact, event}
claim_operation = create_new_deterministic_claim
```

There is exactly one link per selected fact/event decision and no extra link.
Every link must match the selected decision and the exact v1 produced Ledger
graph:

- candidate belongs to the receipt session;
- Evidence belongs to the requested Case and has exact source kind, grade, title,
  publisher, canonical locator, information date, accepted time, candidate
  statement, rebuilt content fingerprint and `supersedes_evidence_id = null`;
- Claim belongs to the requested Case, has the decision claim key and
  `created_at_utc = receipt.accepted_at_utc`;
- ClaimRevision belongs to that Claim, has `revision_no = 1`, `claim_kind = fact`,
  exact statement/status/information date/accepted time,
  `inference_confidence = null`, `inference_basis = null`, and
  `supersedes_revision_id = null`;
- ClaimEvidenceLink binds the exact ClaimRevision and Evidence, has the decision
  relation, accepted time and `link_note = null`;
- acceptance-link IDs match those exact Ledger rows.

Any source/accepted swap, candidate/decision/source/request/accepted fingerprint
mismatch, contract mismatch, non-successor accepted revision, incomplete decision
copy, missing/extra link or semantic mismatch fails the complete pack request as
`evidence_pack_integrity_error`.

### Citation graph

The same proof validates import attempt, immutable content, candidate and page:

- session points to the exact import attempt and content;
- candidate belongs to the session;
- page belongs to the content and exact page number;
- half-open UTF-8 offsets are valid scalar boundaries;
- the exact stored byte slice decodes to `quote_text`;
- quote and page SHA-256 values match;
- candidate and Evidence fingerprints recompute exactly;
- canonical locator matches the accepted v1 command.

The pack returns citation metadata and reviewed quote only. It never returns raw
PDF bytes or whole page text.

Without an acceptance link, provenance is `ledger_only`. Locator text, title,
filename, company name or content similarity may never upgrade it. A present
invalid graph cannot be omitted or downgraded.

## Response contract

```text
contract_version = aquantai.research-evidence-pack.v1
```

Each Evidence entry contains:

```text
evidence
claim_bindings[]
membership_summary
local_document_provenance | null
integrity_state
```

Each binding contains exact Claim/ClaimRevision/ClaimEvidenceLink values,
relation, per-binding membership, selected-revision roles and supersession
reference.

No AI summary, sentiment, ranking, score, recommendation, valuation, expected
return or trading meaning is part of v1. Persisted accepted statements are
rendered verbatim.

## Query architecture and ceiling

A future implementation is a new pack-specific read projection over existing
models. It may use bounded set-based scalar queries, CTEs and unions. It may not
modify write owners or issue per-item/per-Claim/per-receipt/per-citation loops.

For one page of at most 100 Evidence Items:

```text
maximum SQL statements = 8
HTTP GET writes = 0
network calls = 0
OCR calls = 0
AI calls = 0
```

The eight-statement budget is:

1. exact Case and selected revision validation;
2. visible Evidence count;
3. bounded Evidence page;
4. Claim/ClaimRevision/ClaimEvidenceLink rows for page IDs;
5. selected Case-revision roles;
6. complete receipt/session/revision/candidate/decision/link/Ledger transition
   rows for every receipt reached by page IDs, including sibling links and a
   set-wise maximum-revision check;
7. exact referenced page rows;
8. set-wise minimal Evidence/ClaimRevision supersession targets.

The count is independent of nested binding, decision and citation counts. If
measured SQLite/PostgreSQL validation needs an index or ninth statement,
implementation must STOP and return to separately authorized Strict architecture.

## Required future validation

At minimum cover:

- document plus ledger-only golden path;
- empty pack and Evidence without Claim links;
- all-linked, all-unlinked and mixed binding entries;
- contradiction/context relations and deterministic ordering;
- valid same-timestamp supersession targets;
- valid information-hidden supersession targets without payload projection;
- missing, cross-Case/cross-Claim, invalid revision-order and later-recorded
  targets, each failing closed;
- malformed/cross-request cursors and stable identical-timestamp pagination;
- source/accepted revision swap;
- candidate, decision, source, request, accepted and contract fingerprint
  corruption;
- non-immediate or non-terminal accepted revision;
- missing/added/changed accepted decision;
- missing/extra/semantically mismatched acceptance link;
- candidate/page/span/quote/Evidence/Claim graph corruption;
- local-looking locator without acceptance link;
- 1, 50 and 100 member SQL ceilings on SQLite and PostgreSQL;
- zero writes, network, Provider, OCR and AI;
- full regression and all configured offline demos.

Every receipt-transition corruption fails the entire request as
`evidence_pack_integrity_error`; partial authoritative output is prohibited.

## Persistence and lifecycle

```text
new table = none
new column = none
new index = none
migration = none
backfill = none
history rewrite = none
rollback data action = none
downgrade data action = none
```

A durable pack, saved selection, export history or required index is a STOP
condition.

## Inactive future implementation families

This preflight activates no implementation allowlist. A later approved Issue may
authorize only minimum new read-only families such as:

```text
industry_alpha/research_evidence_pack_*.py
backend/api/research_evidence_pack.py
backend/main.py
research_evidence_pack/static/**        (only if separately included)
tests/test_research_evidence_pack_*.py
scripts/demo_research_evidence_pack.py
.github/workflows/local-tests.yml        (only to register validation)
```

No Evidence Ledger or Document Import write-owner file is presumed modifiable.

## Locked exclusions

- production implementation in this PR;
- schema, migration, dependency, fixture, test or workflow changes;
- saved pack, saved selection, export history or background refresh;
- Provider/network/credential use or external acquisition;
- OCR, NLP, AI summary, candidate generation or automated extraction;
- automatic Evidence/Claim/Research Case acceptance or mutation;
- fuzzy identity or hidden latest/default selection;
- Company Research, Industry Map, beneficiary, Investment Candidate or valuation
  mutation;
- recommendation, target price, expected return, position sizing, portfolio,
  broker, order or trading behavior;
- release, tag or version changes;
- PR #241 modification.

## Current architecture allowlist

Exactly these two files may change:

```text
.codex/tasks/issue-288-research-evidence-pack-v1-preflight.md
docs/research_evidence_pack_v1_preflight.md
```

## STOP conditions

STOP and request a separately authorized architecture amendment if work requires:

- persistent pack/snapshot/selection/export state;
- table, column, index, migration, backfill or history rewrite;
- Evidence Ledger or Document Import write-owner modification;
- provenance authority from free text, path or locator parsing;
- latest, unique-reachable, title, company, ticker or similarity inference;
- partial success hiding any broken accepted graph;
- more than eight SQL statements for a bounded page;
- target payload beyond the closed supersession fields;
- Provider, network, credential, OCR, AI or automatic acceptance;
- recommendation, portfolio or trading owners;
- any file outside the then-authorized allowlist.

## Delivery gate

1. Base remains exact `8dd187c129c3e4a375f550758fab266719ccd0da`.
2. Base-to-HEAD inventory contains exactly the two architecture artifacts.
3. PR remains Draft; no Ready transition, merge or Issue closure is authorized.
4. Full repository CI succeeds on one exact immutable new HEAD.
5. A fresh process-independent fixed-HEAD architecture review records zero
   blockers and exactly:

```text
AUTHORIZED RESEARCH EVIDENCE PACK V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

6. Any new commit invalidates prior fixed-HEAD CI and review evidence.
7. Separate project-owner authorization is required for merge and again for any
   implementation Issue, branch or PR.
