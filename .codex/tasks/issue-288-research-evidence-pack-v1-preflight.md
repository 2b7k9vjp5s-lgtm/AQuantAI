# Issue #288 — Research Evidence Pack v1 Strict Architecture Preflight

## Authority

Project-owner authorization received on 2026-08-05:

> 批准从 main@8dd187c129c3e4a375f550758fab266719ccd0da
> 启动 Research Evidence Pack v1 Strict Architecture Preflight；
> 仅允许两份架构工件。

Project-owner repair authorization received on 2026-08-05:

> 授权修复 PR #289 上述三项架构阻断；仅修改现有两份架构工件，
> 产生新 HEAD 后运行完整 CI，并重新进行独立 fixed-HEAD 架构审核。

This snapshot freezes architecture scope only. It authorizes no production code,
schema, migration, dependency, API/UI implementation, fixture, test, workflow,
Provider, network, credential, OCR, AI, automatic evidence acceptance,
recommendation, portfolio, trading, release, tag, version change, Ready transition,
merge, Issue closure or modification of PR #241.

## Exact architecture start

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

The superseded review candidate was
`a06318e833d7ebca67cc90ef0cb8d484ccf0f66e`. Its CI and fixed-HEAD review are
invalid for every later commit.

## Repair closure

The first independent fixed-HEAD review recorded three High blockers. This
revision closes them by freezing all of the following:

1. complete receipt-level validation of the atomic local-document acceptance
   transition, including both review revisions, all fingerprints, exact copied
   decisions and every receipt link;
2. authoritative research membership on each exact Claim binding, plus a closed
   entry summary that represents mixed linked/unlinked bindings without loss;
3. one bounded set-wise minimal supersession-target load used only for graph
   integrity, while target content remains excluded from the response.

No other architecture boundary is changed.

## Product objective

Define one bounded, local, read-only Research Evidence Pack for an explicit
Research Case revision. The pack lets an ordinary user inspect:

- the exact research snapshot selected by ID;
- all accepted Evidence Ledger items visible at explicit dual-as-of boundaries;
- every exact ClaimRevision and ClaimEvidenceLink reached from each Evidence Item;
- per-binding membership in the selected Research Case revision;
- exact local-PDF provenance only when proved by an intact acceptance receipt;
- conflicts, missing links and unavailable history without inference.

The pack is a transient projection. It is not a saved pack, accepted-state owner,
recommendation, score, generated summary or acquisition flow.

## Exact owner inventory

At the exact base:

1. `ResearchCase` and `ResearchCaseRevision` own Case identity and frozen research
   revisions.
2. `EvidenceItem`, `Claim`, `ClaimRevision`, `ClaimEvidenceLink` and
   `CaseRevisionClaimLink` own accepted Evidence Ledger meaning.
3. `EvidenceLedgerCommandService` remains the only accepted Evidence Ledger write
   owner and is outside the future read implementation boundary.
4. `LocalDocumentContent`, `LocalDocumentImportAttempt`, `LocalDocumentPage`,
   `LocalDocumentReviewSession`, `LocalDocumentCandidate`,
   `LocalDocumentReviewRevision`, `LocalDocumentReviewCandidateDecision`,
   `LocalDocumentAcceptanceReceipt` and `LocalDocumentAcceptanceLink` own the
   local-document acceptance proof.
5. `LocalDocumentAcceptanceLink.evidence_item_id` is unique and is the only
   authority that classifies an Evidence Item as accepted through Document
   Import. `EvidenceItem.source_locator` is descriptive only.
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

## Frozen request contract

```text
GET /research-evidence-pack/api/cases/{research_case_id}/revisions/{research_case_revision_id}
    ?information_cutoff_date=YYYY-MM-DD
    &recorded_at_utc=<UTC RFC3339 timestamp>
    &limit=<1..100, default 50>
    [&cursor=<opaque request-bound keyset cursor>]
```

Required behavior:

- both IDs are explicit UUIDs and the revision must belong to the Case;
- `information_cutoff_date <= recorded_at_utc.date()`;
- the exact Case revision must be visible under both applicable boundaries;
- no latest, newest, only-option, same-name, same-ticker or unique-reachable
  selection is allowed;
- the cursor binds contract version, both IDs, both boundaries, limit and the
  final ordering tuple;
- malformed or mismatched cursors fail before row projection;
- limits outside `1..100` fail rather than clamp.

## Evidence visibility and ordering

An Evidence Item is eligible only when:

```text
EvidenceItem.case_id = research_case_id
EvidenceItem.information_date <= information_cutoff_date
EvidenceItem.recorded_at_utc <= recorded_at_utc
```

Stable page order is:

```text
information_date DESC,
recorded_at_utc DESC,
evidence_id ASC
```

All UUID tie-breakers use lowercase canonical string order. Offset pagination is
prohibited.

## Claim binding and research membership

Every returned binding preserves exact `Claim`, `ClaimRevision` and
`ClaimEvidenceLink` IDs and the persisted relation. The Claim must belong to the
requested Case, and every time-bearing row must be visible at the recorded
boundary. No latest ClaimRevision is selected.

Research membership is authoritative on each `claim_bindings[]` member:

```text
linked_to_selected_case_revision
accepted_unlinked_to_selected_case_revision
```

A binding is `linked_to_selected_case_revision` only when one or more exact,
visible `CaseRevisionClaimLink` rows reference that exact ClaimRevision and the
selected Case revision. Its exact roles and link IDs are returned. Otherwise that
binding is `accepted_unlinked_to_selected_case_revision`.

The Evidence entry has no scalar `research_membership_state`. It exposes only the
derived, closed `membership_summary`:

```text
no_claim_bindings
all_bindings_linked
all_bindings_unlinked
mixed_linked_and_unlinked_bindings
```

`membership_summary` is presentation metadata derived from the complete binding
set and never overrides a binding. One Evidence Item may simultaneously contain
linked and unlinked Claim bindings. Evidence without a visible ClaimEvidenceLink
remains visible with `no_claim_bindings`; it is never treated as support for any
Claim.

Nested order is deterministic:

```text
Claim.claim_key ASC
ClaimRevision.revision_no ASC
ClaimEvidenceLink.relation ASC
ClaimRevision.id ASC
CaseRevisionClaimLink.role ASC
CaseRevisionClaimLink.id ASC
```

## Supersession integrity with minimal target loads

Visible Evidence and Claim supersession IDs remain explicit history and never
become implicit current-row selectors.

For every non-null `EvidenceItem.supersedes_evidence_id` and every non-null
`ClaimRevision.supersedes_revision_id` reached by the page, the projection must
perform one bounded, set-wise minimal target load. The load is permitted to cross
the information boundary solely to validate identity and chronology.

The allowed target columns are exactly:

```text
Evidence target: id, case_id, information_date, recorded_at_utc
ClaimRevision target: id, claim_id, revision_no,
                      information_cutoff_date, recorded_at_utc
```

Validation requires:

- every referenced target exists;
- an Evidence target belongs to the same Research Case and is recorded strictly
  before the superseding Evidence Item;
- a ClaimRevision target belongs to the same Claim, has a lower revision number
  and is recorded strictly before the superseding ClaimRevision;
- no target statement, source metadata, quote, page text or other payload field is
  loaded or returned by this validation path.

If the minimal target is valid but outside the requested information boundary,
the response may expose only its exact ID plus `not_visible_as_of`. It must not
expose target fields or replace it with another row. A missing, cross-owner,
non-older or forward-recorded target fails the whole request as
`evidence_pack_integrity_error`.

## Complete local-document acceptance proof

An Evidence Item receives local-document provenance only when an exact
`LocalDocumentAcceptanceLink` exists. If any page Evidence Item reaches a receipt,
the projection validates the complete receipt transition set-wise, not merely the
one link shown on the current page.

### Receipt and revision identity

The following must all hold:

- every receipt and link exists and all receipt links are loaded for the bounded
  receipt set;
- receipt, source revision, accepted revision and review session share the exact
  `review_session_id`;
- `receipt.target_research_case_id`,
  `LocalDocumentReviewSession.target_research_case_id` and the requested Case are
  identical;
- `receipt.source_review_fingerprint_sha256` equals the exact source revision
  fingerprint;
- `receipt.accepted_review_fingerprint_sha256` equals the exact accepted revision
  fingerprint;
- `receipt.acceptance_contract_version` equals
  `aquantai.local-document-acceptance.v1`;
- source revision state is `draft` or `deferred`;
- accepted revision state is `accepted`;
- accepted revision number is `source.revision_number + 1`;
- accepted `expected_previous_revision_number` equals the source revision number;
- accepted `supersedes_review_revision_id` equals the source revision ID;
- accepted and source revisions belong to the same review session;
- accepted source kind, evidence grade, document identity candidate, subject
  candidate, information date and reviewer note are exact copies of the source;
- receipt `accepted_at_utc` equals accepted revision `recorded_at_utc` and is
  visible at the requested recorded boundary;
- accepted information date is visible at the requested information boundary.

### Full decision-copy equality

The projection loads every candidate decision for both source and accepted
revisions for each bounded receipt and requires exact set equality by candidate
ID. Each paired row must match exactly on:

```text
decision
claim_operation
claim_key
claim_status
evidence_relation
decision_fingerprint_sha256
```

The decision sets must cover the exact complete candidate set owned by the review
session. Missing, added, rebound or changed accepted decisions are integrity
failures.

### Fingerprint replay

Using the accepted owner contracts, the projection deterministically rebuilds:

1. every selected candidate Evidence fingerprint under
   `aquantai.local-document-evidence-item.v1`;
2. the acceptance plan fingerprint from the exact source revision, session,
   content, identity candidates and ordered selected decision set;
3. the request fingerprint from source revision ID/number/fingerprint, expected
   session latest number equal to the source revision number, target Case,
   selected candidate IDs, selected decision fingerprints, receipt accepted time,
   `aquantai.local-document-acceptance.v1` and the rebuilt plan fingerprint;
4. the accepted review fingerprint under
   `aquantai.local-document-accepted-review.v1` from the exact source identity,
   accepted successor number/state, rebuilt request/plan fingerprints, target
   Case and accepted time.

The rebuilt request fingerprint must equal
`receipt.request_fingerprint_sha256`; the rebuilt accepted fingerprint must equal
both the accepted revision and receipt values. Contract or fingerprint mismatch
fails the whole request.

### Receipt-link completeness and semantics

For each receipt, the exact set of `LocalDocumentAcceptanceLink` rows must equal
the source decision set members where:

```text
decision = selected
candidate_kind in {fact, event}
claim_operation = create_new_deterministic_claim
```

There must be one and only one link for each selected fact/event decision and no
extra link. Every link must match that decision and produced Ledger graph:

- candidate ID and candidate review session;
- Evidence ID, requested Case, information date, recorded time, source kind,
  evidence grade, summary, content fingerprint and canonical local-document
  locator;
- Claim ID and Case;
- Claim key, ClaimRevision ID/revision number/statement/status/information date and
  recorded time;
- ClaimEvidenceLink ID, Evidence ID, ClaimRevision ID, relation and recorded time;
- decision claim key, claim status and evidence relation.

Any source/accepted revision swap, fingerprint or contract mismatch,
non-successor accepted revision, incomplete/changed decision copy, missing/extra
link or link/decision semantic mismatch fails the complete pack request as
`evidence_pack_integrity_error`.

### Citation graph

The same set-wise proof validates import attempt, immutable PDF content, candidate
and exact page/span:

- review session points to the exact import attempt and content;
- candidate belongs to the receipt review session;
- page belongs to that content and page number;
- half-open UTF-8 byte offsets are valid scalar boundaries;
- the exact stored byte slice decodes to `quote_text`;
- quote and page SHA-256 values match;
- candidate and Evidence fingerprints recompute exactly;
- canonical local-document locator matches the accepted v1 command.

The pack returns citation metadata and reviewed quote only. It never returns raw
PDF bytes or whole page text.

If no acceptance link exists, provenance is `ledger_only`. Locator text, title,
filename, company name or content similarity may never upgrade it. A present but
invalid graph cannot be omitted or downgraded.

## Response contract

```text
contract_version = aquantai.research-evidence-pack.v1
```

Top-level fields include exact selectors, boundaries, Case and selected revision,
visible count, entries, next cursor and deterministic notices.

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

No AI summary, sentiment, rank, score, recommendation, valuation, expected return
or trading meaning is part of v1. Persisted statements are rendered verbatim.

## Query architecture and ceiling

The future implementation is a new pack-specific read projection over existing
models. It may use set-based scalar queries and SQL CTE/UNION shapes. It may not
modify write owners or issue per-item/per-Claim/per-citation queries.

For one page of at most 100 Evidence Items:

```text
maximum SQL statements = 8
HTTP GET writes = 0
network calls = 0
OCR calls = 0
AI calls = 0
```

The eight-statement budget includes:

1. exact Case and selected revision validation;
2. visible Evidence count;
3. bounded Evidence page;
4. Claim/ClaimRevision/ClaimEvidenceLink rows for page IDs;
5. selected Case-revision roles;
6. complete receipt-level local-document transition graph for all receipts reached
   by page IDs, including every sibling receipt link and both decision sets;
7. exact referenced page rows;
8. the set-wise minimal Evidence/ClaimRevision supersession-target load.

One statement may contain bounded CTEs/unions. The count is independent of nested
bindings, candidates and citations. If measured SQLite/PostgreSQL validation
requires another index or cannot meet the ceiling, implementation must STOP and
return to separately authorized Strict architecture.

## Error states

```text
research_case_not_found
research_case_revision_not_found
research_case_revision_mismatch
research_case_revision_not_visible_as_of
invalid_evidence_pack_as_of
invalid_evidence_pack_cursor
evidence_pack_integrity_error
database_unavailable
```

An exact visible Case revision with no visible Evidence returns HTTP 200 with
`empty_evidence_pack`; it triggers no acquisition or write.

## Required future validation

Positive and boundary coverage must include:

- exact document plus ledger-only golden path;
- empty pack and Evidence without Claim links;
- one Evidence Item with linked and unlinked Claim bindings simultaneously,
  proving per-binding states and `mixed_linked_and_unlinked_bindings`;
- contradiction/context relations and deterministic nested ordering;
- valid information-hidden supersession targets whose content is not projected;
- missing, cross-Case/cross-Claim, non-older and forward-recorded supersession
  targets, each failing closed;
- exact unlinked accepted document evidence;
- malformed and cross-request cursors;
- stable pagination with identical timestamps;
- source/accepted review revision swap;
- source, accepted, request and contract fingerprint mismatch;
- non-immediate-successor accepted revision;
- missing, added or changed accepted decision;
- missing, extra or semantically mismatched acceptance link;
- candidate/page/span/quote/Evidence/Claim graph corruption;
- locator that resembles a local locator without an acceptance link;
- 1, 50 and 100 member SQL ceilings on SQLite and PostgreSQL;
- zero writes, network, Provider, OCR and AI;
- full regression and all configured offline demos.

Every receipt-transition corruption above must fail the entire request as
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

Removing a future implementation removes only the read surface. Durable pack
identity, saved selection, export history or a required index is a STOP condition.

## Inactive future implementation families

This preflight activates no implementation allowlist. A later separately
approved Issue may authorize only minimum new read-only families such as:

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

STOP and request an explicit architecture amendment if review or implementation
requires:

- a persistent Evidence Pack/snapshot/selection/export-history owner;
- a table, column, index, migration, backfill or history rewrite;
- modification of Evidence Ledger or Document Import write owners;
- provenance authority from free text, path or locator parsing;
- latest, unique-reachable, title, company, ticker or similarity inference;
- partial success hiding any broken accepted graph;
- more than eight SQL statements for one bounded page;
- Provider, network, credential, OCR, AI or automatic acceptance;
- recommendation, portfolio or trading owners;
- any file outside the then-authorized allowlist.

## Governance and delivery gate

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
