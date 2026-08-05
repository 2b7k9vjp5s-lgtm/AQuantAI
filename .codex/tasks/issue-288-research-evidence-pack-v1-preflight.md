# Issue #288 — Research Evidence Pack v1 Strict Architecture Preflight

## Authority

Project-owner authorization received on 2026-08-05:

> 批准从 main@8dd187c129c3e4a375f550758fab266719ccd0da
> 启动 Research Evidence Pack v1 Strict Architecture Preflight；
> 仅允许两份架构工件。

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
risk_tier = Strict Architecture Preflight
implementation_authorized = false
```

The exact base passed `Local Tests #1069`, run `30988479592`, job
`92248720124`. PR #241 remains closed, Draft, unmerged and read-only at
`3116a67ec472131eea3bf3d1bd9daee884c69ee9`.

## Product objective

Define one bounded, read-only Research Evidence Pack for an explicit Research
Case revision. The pack must let an ordinary user see:

- the exact research snapshot they selected;
- all accepted Evidence Ledger items visible at explicit dual-as-of boundaries;
- the exact Claim revisions and relations bound to each item;
- whether a Claim revision is part of the selected Research Case revision or is
  accepted case evidence not yet linked into that frozen research snapshot;
- exact local-PDF provenance, page and UTF-8 byte-span citations where an
  accepted Document Import receipt provides them;
- conflicts, missing links and unavailable provenance without inference.

The pack is a transient read projection. It is not a saved pack, accepted-state
owner, recommendation, score, summary generator or external acquisition flow.

## Exact owner inventory

At the exact base:

1. `ResearchCase` and `ResearchCaseRevision` own case identity and frozen
   research revisions.
2. `EvidenceItem`, `Claim`, `ClaimRevision`, `ClaimEvidenceLink` and
   `CaseRevisionClaimLink` own accepted Evidence Ledger meaning.
3. `EvidenceLedgerCommandService` remains the only accepted Evidence Ledger
   write owner and is outside the future read-only implementation boundary.
4. `EvidenceLedgerRepository` / `EvidenceLedgerQueryService` provide existing
   case-ledger reads, but their date-only, whole-case projection is not the
   bounded dual-as-of Evidence Pack contract.
5. `LocalDocumentContent`, `LocalDocumentImportAttempt`, `LocalDocumentPage`,
   `LocalDocumentReviewSession`, `LocalDocumentCandidate`,
   `LocalDocumentReviewRevision`, `LocalDocumentAcceptanceReceipt` and
   `LocalDocumentAcceptanceLink` own exact local-document provenance and the
   accepted bridge.
6. `LocalDocumentAcceptanceLink.evidence_item_id` is unique and is the only
   authority that classifies an Evidence Item as accepted through Document
   Import. `EvidenceItem.source_locator` is descriptive and must never be parsed
   to infer provenance.
7. Document content, page text, review history, receipts and Evidence Ledger
   rows are append-only and already contain the exact graph required for a
   read-only pack.
8. No persisted Evidence Pack, saved selection, export-history or pack-snapshot
   owner exists.

```text
existing_owner_sufficient_for_read_projection = true
existing_owner_sufficient_for_saved_pack = false
schema_required_for_v1 = false
migration_required_for_v1 = false
new_write_owner_required = false
owner_modification_required = false
```

## Frozen architecture decision

Research Evidence Pack v1 is a deterministic read model over existing accepted
owners:

```text
exact Research Case
+ exact Research Case Revision
+ information_cutoff_date
+ recorded_at_utc
-> visible accepted Evidence Items for that exact Case
-> exact visible Claim/ClaimRevision/Evidence relations
-> exact selected-revision CaseRevisionClaimLink roles
-> optional exact LocalDocumentAcceptanceLink provenance graph
-> stable paginated Evidence Pack response
```

The selected Research Case revision is the frozen research anchor. All accepted
case evidence visible at the boundaries remains discoverable, but the response
must distinguish:

```text
linked_to_selected_case_revision
accepted_unlinked_to_selected_case_revision
accepted_evidence_without_claim_link
```

Unlinked accepted evidence must never be presented as a conclusion, context or
risk already accepted by the selected Research Case revision.

## Canonical selectors

The future canonical request is:

```text
GET /research-evidence-pack/api/cases/{research_case_id}/revisions/{research_case_revision_id}
    ?information_cutoff_date=YYYY-MM-DD
    &recorded_at_utc=<UTC RFC3339 timestamp>
    &limit=<1..100, default 50>
    [&cursor=<opaque boundary-bound cursor>]
```

Required behavior:

- both IDs are explicit UUIDs;
- `research_case_revision_id` must belong to `research_case_id`;
- `information_cutoff_date <= recorded_at_utc.date()`;
- the exact Case revision must be visible under both boundaries;
- no latest, newest, only-option, same-name, same-ticker or unique-reachable
  selection is allowed;
- the cursor binds contract version, both IDs, both boundaries, page size and
  the last ordering tuple; a cursor from another request fails before row
  projection;
- page size is bounded to `1..100`; values outside the range fail rather than
  clamp silently.

## Membership and chronology

An Evidence Item is visible only when:

```text
EvidenceItem.case_id = research_case_id
EvidenceItem.information_date <= information_cutoff_date
EvidenceItem.recorded_at_utc <= recorded_at_utc
```

Every returned Claim binding must preserve its exact Claim, ClaimRevision and
ClaimEvidenceLink IDs. The Claim must belong to the same Research Case and all
time-bearing rows must be visible at the recorded boundary. A ClaimRevision is
classified as part of the selected research snapshot only through an exact
visible `CaseRevisionClaimLink` for the selected Case revision.

The pack does not collapse Claim history into an inferred latest revision. It
returns only exact revisions reached by visible links for the current Evidence
page and preserves every relation (`supports`, `contradicts`, `context`).

Visible Evidence and Claim supersession identities remain explicit history.
`supersedes_evidence_id` must identify an older recorded Evidence Item in the same
Case when present; `ClaimRevision.supersedes_revision_id` must identify an older
recorded revision of the same Claim. A target outside the information boundary is
reported by ID as `not_visible_as_of`, without exposing its fields or replacing
it. The pack never removes a superseded row or turns either chain into an
implicit current-row selector. A missing, cross-owner or forward-recorded
supersession graph is `evidence_pack_integrity_error`.

Evidence without any visible ClaimEvidenceLink remains visible with an explicit
`accepted_evidence_without_claim_link` state. It is never dropped or treated as
support for a claim.

## Exact local-document provenance

An Evidence Item receives local-document provenance only when an exact
`LocalDocumentAcceptanceLink` exists for its ID. The projection must set-wise
revalidate:

- acceptance link, receipt and review-session identity;
- receipt target Research Case;
- exact accepted review revision and its visibility;
- acceptance-link candidate, Evidence, Claim, ClaimRevision and
  ClaimEvidenceLink identities;
- import attempt, immutable content and exact candidate page/span;
- candidate quote fingerprint and exact UTF-8 byte slice in the stored page;
- Evidence content fingerprint and canonical local-document locator produced by
  the accepted v1 command.

The pack returns citation metadata and the reviewed quote, not whole PDF bytes or
whole page text. The existing exact content/page surfaces remain responsible for
explicit document inspection.

If no acceptance link exists, the source is `ledger_only`; no source-locator
string, title, filename, company name or content similarity may upgrade it to
local-document provenance.

Any present-but-invalid local-document acceptance graph fails the complete pack
request closed as `evidence_pack_integrity_error`. It must not omit the broken
item, fall back to source text or return a partially authoritative pack.

## Stable ordering and pagination

The top-level entry is one accepted Evidence Item. Stable order is:

```text
information_date DESC,
recorded_at_utc DESC,
evidence_id ASC
```

Within an entry:

- Claim bindings: `claim_key`, `claim_revision_no`, relation, ClaimRevision UUID;
- selected-revision roles: role, CaseRevisionClaimLink UUID;
- local-document citations: receipt UUID, candidate UUID;
- all UUID tie-breakers use lowercase canonical string order.

The opaque cursor uses the final Evidence ordering tuple and a deterministic
SHA-256 checksum over canonical UTF-8 JSON. It is integrity/binding metadata, not
an authorization token or secret. Malformed or mismatched cursors return
`invalid_evidence_pack_cursor` before database work.

No offset pagination is allowed.

## Read contract

The future response contract version is:

```text
aquantai.research-evidence-pack.v1
```

It contains:

- exact request selectors and boundaries;
- exact Research Case and selected Case revision identity/status;
- visible Evidence count and page cursor state;
- Evidence entries with accepted source metadata;
- exact Claim revision bindings and relation;
- exact selected-revision role or explicit unlinked state;
- optional exact local-document receipt/content/page/span/quote provenance;
- conflict and missing-link states;
- deterministic notices that accepted evidence does not automatically rewrite
  the selected research snapshot;
- zero recommendation, priority, valuation, expected-return or trading meaning.

No AI summary, generated conclusion or sentiment label is part of v1. Existing
Evidence/Claim statements are rendered verbatim as persisted accepted fields.

## Query architecture and ceilings

The expected future implementation is a new read-only, pack-specific projection
module over existing models. It may use set-based scalar queries in the same
style as accepted result projections. It may not modify existing repositories or
write owners merely to force the pack through a whole-graph loader.

For one page of at most 100 Evidence Items:

```text
evidence pack page = <= 8 SQL statements
HTTP GET writes = 0
network calls = 0
AI calls = 0
```

The ceiling is independent of the number of Claim bindings and local-document
citations within that bounded Evidence page. Per-item or per-citation query loops
are prohibited. Full PDF bytes and full page text are not returned by the pack.
The existing schema is sufficient for correctness; if measured SQLite/PostgreSQL
validation proves an additional index is required to meet the bounded product
contract, implementation must STOP rather than add it silently.

## Error and recovery states

Closed service states include:

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

Empty visible evidence is a successful, explicit `empty_evidence_pack` result.
It is not replaced with newer evidence and does not trigger acquisition.

## Persistence, rollback and downgrade

Research Evidence Pack v1 persists nothing:

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

Removing a future read-only implementation removes only the projection surface;
all authoritative accepted rows remain unchanged. If implementation proves a
durable pack identity, saved selection, snapshot, export history or additional
index is required, it must STOP and return to separately authorized Strict
architecture.

## Production-realistic offline golden path

The required future zero-network fixture contains:

1. one exact Research Case with its initial revision;
2. one accepted official local PDF with immutable pages;
3. one human-authored page/span fact accepted atomically through the production
   Document Import boundary;
4. one later, explicitly selected Research Case revision created through the
   existing owner with that exact ClaimRevision linked as `conclusion`;
5. one accepted non-document Evidence Item linked as `context`;
6. one later accepted local-document fact visible at the requested boundaries
   but not linked to the selected Case revision;
7. one Evidence Item recorded after the requested boundary and therefore absent.

The response anchored to that later Case revision must preserve all three visible Evidence Items, show the exact PDF
citation for both document-derived items, label the later accepted fact as
unlinked, preserve the non-document source as `ledger_only`, and write nothing.

## Decisive failure path

Create an otherwise visible local-document Evidence Item whose
`LocalDocumentAcceptanceLink` points to a candidate/page/span or Claim graph that
does not match the receipt and accepted Evidence graph. The pack must return
`evidence_pack_integrity_error`, perform zero writes, make zero network/AI calls
and must not fall back to parsing `EvidenceItem.source_locator`.

## Expected future implementation classification

A later separately authorized implementation may be Standard read-only work only
when it:

- uses existing tables and immutable links;
- adds no persistence or accepted contract;
- leaves every write owner unchanged;
- remains local, zero-network and zero-AI;
- stays inside a separately approved implementation Issue/PR.

Return to Strict architecture if any STOP condition below appears.

## Proposed inactive future implementation families

This preflight does not activate an implementation allowlist. A later Issue may
authorize only the minimum required families, expected to include:

```text
industry_alpha/research_evidence_pack_*.py
backend/api/research_evidence_pack.py
backend/main.py
research_evidence_pack/static/**        (only if separately included)
tests/test_research_evidence_pack_*.py
scripts/demo_research_evidence_pack.py
.github/workflows/local-tests.yml        (only to register focused validation)
```

No existing Evidence Ledger or Document Import write-owner file is presumed
modifiable.

## Locked exclusions

- production implementation in this PR;
- schema, migration, dependency, fixture, test or workflow changes;
- saved pack, saved selection, export history or background refresh;
- Provider/network/credential use or external announcement catalog/download;
- OCR, NLP, AI summary, sentiment, candidate generation or automated extraction;
- automatic Evidence/Claim/Research Case acceptance or mutation;
- fuzzy identity, company-name/ticker matching or hidden latest/default selection;
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
- a table, column, index, migration, backfill or destructive history operation;
- modification of Evidence Ledger or Document Import write owners;
- packing provenance into free text or parsing a filesystem path/source locator
  as authority;
- latest, unique-reachable, title, company-name, ticker or similarity inference;
- partial success that hides a broken accepted provenance graph;
- Provider, network, credential, OCR, AI or automatic acceptance;
- recommendation, portfolio or trading owners;
- any file outside the then-authorized allowlist.

## Governance and delivery gate

1. Base remains exact `8dd187c129c3e4a375f550758fab266719ccd0da`.
2. Base-to-HEAD inventory contains exactly the two architecture artifacts.
3. PR remains Draft; no Ready transition, merge or Issue closure is authorized.
4. Repository CI succeeds on one exact immutable HEAD.
5. A fresh process-independent fixed-head architecture review records zero
   blockers and exactly:

```text
AUTHORIZED RESEARCH EVIDENCE PACK V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

6. Any new commit invalidates prior fixed-head CI and review evidence.
7. Separate project-owner authorization is required for merge and again for any
   implementation Issue, branch or PR.
