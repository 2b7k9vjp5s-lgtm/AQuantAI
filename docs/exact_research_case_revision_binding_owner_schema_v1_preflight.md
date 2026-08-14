# Exact Research Case Revision Binding Owner/Schema Amendment v1

## Strict Architecture Preflight

### Status

```text
issue = #297
roadmap = #137
base = main@04c6683cd7820851556d01528848eafd421135f8
upstream = Issue #295 / merged PR #296
risk_tier = Strict Architecture Preflight
implementation_authorized = false
schema_or_migration_authorized = false
preflight_outcome = implementable_two_owner_append_only_binding_amendment
```

This preflight resolves the authority gap identified by PR #296. It freezes how a later, separately authorized Strict implementation must persist an exact `ResearchCaseRevision` decision for newly reviewed/accepted Industry Thesis outputs and newly created Stage2 Company Research revisions. It does not implement schema, migration, write-owner or Evidence Pack UI changes.

---

## 1. Problem being solved

`aquantai.research-evidence-pack.v1` intentionally requires an exact historical anchor:

```text
research_case_id
research_case_revision_id
information_cutoff_date
recorded_at_utc
```

Current accepted Industry Thesis and Company Research owners preserve exact Case, Map, Stage1, Claim and Evidence identities, but no authoritative owner persists one exact `ResearchCaseRevision.id` for the accepted Industry output or Company Research revision.

A future ordinary-user evidence integration therefore cannot safely answer which Case Revision was represented by a historical accepted research result without first adding an explicit owner decision.

The missing identity may never be inferred from:

```text
latest Case Revision
max revision_no
maximum matching Claim coverage
only currently reachable revision
nearest information cutoff
nearest recorded timestamp
same Map
same company
same Claim set
```

Any such rule could silently reinterpret accepted history after later Case Revisions are appended.

---

## 2. Exact-main owner inventory

### 2.1 Research Case

`industry_alpha/models.py` owns `ResearchCaseRevision` with exact revision identity, `case_id`, revision number, workflow/conclusion state, `information_cutoff_date`, `recorded_at_utc` and supersession identity. `ResearchCaseRevision.id` is the Evidence Pack membership anchor.

### 2.2 Industry Thesis accepted output

`IndustryThesisOutputLinkRevision` already freezes:

```text
research_case_id
accepted_industry_map_identity_id
accepted_industry_map_revision_id
accepted_candidate_pool_revision_id
reviewed_plan_fingerprint_sha256
acceptance_plan_fingerprint_sha256
owner_transaction_id
information_cutoff_date
recorded_at_utc
```

It is append-only, but contains no Case Revision identity.

### 2.3 Industry Thesis review/acceptance

The current accepted flow is:

```text
proposal review
-> reviewed-plan snapshot/fingerprint
-> acceptance workbench view
-> acceptance-view snapshot fingerprint
-> owner-acceptance preview
-> explicit commit with matching preview fingerprint
-> atomic accepted output
```

Current exact-main contracts are:

```text
reviewed plan = aquantai.industry-thesis-acceptance-plan.v2
Owner Context = aquantai.industry-thesis-owner-context.v1
owner-acceptance plan = aquantai.industry-thesis-owner-acceptance-plan.v1
output link = aquantai.industry-thesis-output-links.v1
```

Owner Context v1 freezes Case + Map + Map Revision, but not Case Revision.

The active ordinary-user review submit path is the candidate-review surface:

```text
industry_analysis/static/candidate_review.html
industry_analysis/static/candidate_review.js
POST /industry-analysis/api/session-revisions/{id}/reviews
```

The server-side review DTO already owns `owner_context`; therefore the exact Case Revision decision belongs on this review surface, not on a later result page or as an acceptance-time hidden selector.

`industry_analysis/static/review_result.js` is downstream of review and currently gates owner acceptance by reviewed-plan contract version, so it also must recognize the future v3 plan. `review_result.html` needs no structural change for this amendment.

### 2.4 Stage2 Company Research

`Stage2CompanyResearch` freezes Case/Map and exact Stage1 handoff identities. `Stage2CompanyResearchRevision` freezes revision state, question/summary, cutoff, recorded time and supersession. `Stage2CompanyResearchCommandService` owns creation of the first revision and every later append, but does not currently require a Case Revision.

---

## 3. Chosen owner shape

Introduce exactly two narrow append-only link owners.

### 3.1 Industry Thesis binding

```text
IndustryThesisOutputLinkRevision
  -> IndustryThesisOutputCaseRevisionBinding
  -> ResearchCaseRevision
```

Table:

```text
industry_thesis_output_case_revision_bindings
```

### 3.2 Company Research binding

```text
Stage2CompanyResearchRevision
  -> Stage2CompanyResearchRevisionCaseBinding
  -> ResearchCaseRevision
```

Table:

```text
stage2_company_research_revision_case_bindings
```

### 3.3 Rejected alternatives

A generic polymorphic table such as `research_context_bindings(target_type, target_id, ...)` is rejected for v1 because it weakens direct referential integrity and introduces an unnecessary generic owner.

Adding a non-null `research_case_revision_id` directly to existing historical owner revisions is rejected because legacy rows have no trustworthy value. A nullable column is also rejected because it conflates “historical decision was never persisted” with a new owner deliberately selecting no Case Revision. New writes are not permitted to select none.

---

## 4. Exact Industry binding schema

Future ORM/table contract:

```text
IndustryThesisOutputCaseRevisionBinding
-------------------------------------------------------
id                         UUID PRIMARY KEY NOT NULL
output_link_revision_id    UUID NOT NULL
research_case_revision_id  UUID NOT NULL
binding_contract_version   VARCHAR(128) NOT NULL
```

Foreign keys:

```text
output_link_revision_id
  -> industry_thesis_output_link_revisions.id
  ON DELETE RESTRICT

research_case_revision_id
  -> research_case_revisions.id
  ON DELETE RESTRICT
```

Required constraints/index:

```text
UNIQUE(output_link_revision_id)
CHECK(binding_contract_version = 'aquantai.industry-thesis-output-case-revision-binding.v1')
INDEX(research_case_revision_id, output_link_revision_id)
```

Binding contract:

```text
aquantai.industry-thesis-output-case-revision-binding.v1
```

Deterministic identity:

```text
namespace = UUIDv5(NAMESPACE_URL, binding_contract_version)
id = UUIDv5(namespace, output_link_revision_id + ':' + research_case_revision_id)
```

The model is added to the same append-only mutation guard used by accepted Industry Thesis history. Ordinary ORM update/delete must fail.

There is no separate binding `recorded_at_utc`. Binding lifecycle is owned by the exact accepted-output transaction; a second timestamp would create two competing transaction times. Historical visibility comes from the owning `IndustryThesisOutputLinkRevision` and integrity validation of the bound Case Revision.

---

## 5. Exact Company Research binding schema

Future ORM/table contract:

```text
Stage2CompanyResearchRevisionCaseBinding
-------------------------------------------------------
id                           UUID PRIMARY KEY NOT NULL
company_research_revision_id UUID NOT NULL
research_case_revision_id    UUID NOT NULL
binding_contract_version     VARCHAR(128) NOT NULL
```

Foreign keys:

```text
company_research_revision_id
  -> stage2_company_research_revisions.id
  ON DELETE RESTRICT

research_case_revision_id
  -> research_case_revisions.id
  ON DELETE RESTRICT
```

Required constraints/index:

```text
UNIQUE(company_research_revision_id)
CHECK(binding_contract_version = 'aquantai.stage2-company-research-case-revision-binding.v1')
INDEX(research_case_revision_id, company_research_revision_id)
```

Binding contract:

```text
aquantai.stage2-company-research-case-revision-binding.v1
```

Deterministic identity:

```text
namespace = UUIDv5(NAMESPACE_URL, binding_contract_version)
id = UUIDv5(namespace, company_research_revision_id + ':' + research_case_revision_id)
```

The model is included in `STAGE2_MODELS` so existing Stage2 append-only update/delete rejection applies. It also has no independent timestamp.

---

## 6. Cross-owner invariants

The write services must validate, inside the same transaction and before final commit:

```text
ResearchCaseRevision exists
owner revision exists or is being created in this transaction
ResearchCaseRevision.case_id == owner authoritative case_id
ResearchCaseRevision.information_cutoff_date <= owner information_cutoff_date
ResearchCaseRevision.recorded_at_utc <= owner recorded_at_utc
```

For Industry Thesis, the authoritative Case is the Case frozen in Owner Context v2 and persisted by `IndustryThesisOutputLinkRevision.research_case_id`.

For Company Research, the authoritative Case is `Stage2CompanyResearch.case_id` reached through the exact Company Research revision owner.

No database trigger is added. v1 follows the repository’s existing transaction-owned validation + append-only constraint model and requires focused SQLite/PostgreSQL negatives.

---

## 7. Industry Thesis reviewed Owner Context v2

The exact Case Revision is a reviewed human choice, not an acceptance-time field.

### 7.1 Active contracts after implementation

New proposal reviews use:

```text
reviewed plan = aquantai.industry-thesis-acceptance-plan.v3
Owner Context = aquantai.industry-thesis-owner-context.v2
```

Owner Context v2 freezes exactly:

```json
{
  "owner_context_contract_version": "aquantai.industry-thesis-owner-context.v2",
  "map_mode": "reuse_exact_existing_map_revision",
  "research_case_id": "<UUID>",
  "research_case_revision_id": "<UUID>",
  "industry_map_id": "<UUID>",
  "industry_map_revision_id": "<UUID>"
}
```

### 7.2 Authoritative ordinary-user selection surface

The selection belongs in:

```text
industry_analysis/static/candidate_review.html
industry_analysis/static/candidate_review.js
```

The future implementation must extend the existing review surface so that it:

1. loads the owner-context options endpoint for the exact proposal/review context;
2. displays eligible **Case Revision + Map Revision pairs**;
3. never preselects a pair automatically;
4. requires an explicit user selection before review submission;
5. submits both exact IDs:

```json
{
  "owner_context": {
    "research_case_revision_id": "<UUID>",
    "industry_map_revision_id": "<UUID>"
  }
}
```

6. does not derive Case, Map or revision identities in JavaScript from title/name/order/array position;
7. re-renders the selected pair in the reviewed result as frozen context.

The existing server endpoint remains explicit-confirmation only:

```text
explicit_confirmation_required = true
automatic_default = null
```

The options response must represent valid exact pairs, not a Map Revision plus a separately inferred Case Revision.

`candidate_review.js` currently has stale client-side reviewed-plan assumptions relative to the server lineage; the implementation must update it to the v3 contract rather than preserve an obsolete client constant. This is a contract synchronization fix within the frozen review-owner scope, not a new feature branch.

### 7.3 Option eligibility and ordering

Both revisions in a selectable pair must be visible within the review boundaries:

```text
source thesis information_cutoff_date
review as_of_cutoff
review recorded UTC boundary
```

Ordering/cursor is deterministic and includes exact Case Revision and Map Revision identities as final tie breakers. Pagination cannot change the meaning of a selected pair.

No selector may use latest/max/coverage/first/only-row behavior.

### 7.4 Fingerprint participation

The exact Case Revision participates in:

- Owner Context v2 canonical value;
- reviewed decision seed;
- reviewed-plan fingerprint;
- deterministic reviewed session/candidate IDs through that fingerprint;
- reviewed plan recorded-time boundary.

The recorded-time boundary must be at least the maximum recorded time of the source thesis revision, reviewed candidate source boundary, exact Map Revision and exact Case Revision.

Appending a newer Case Revision later cannot change a frozen v3 plan.

---

## 8. Industry Thesis owner acceptance v2

### 8.1 New owner-acceptance plan

New bound writes use:

```text
aquantai.industry-thesis-owner-acceptance-plan.v2
```

The existing flat owner-acceptance plan gains exactly:

```text
research_case_revision_id
```

next to the already frozen Case/Map fields. Its canonical fingerprint includes the exact Case Revision.

### 8.2 Acceptance-view snapshot

`IndustryThesisOwnerAcceptanceWorkbenchQueryService` reads the exact v3 reviewed plan and loads the frozen:

```text
ResearchCase
ResearchCaseRevision
IndustryMap
IndustryMapRevision
```

The acceptance view presents Case Revision as non-editable reviewed context.

`backend/api/industry_analysis_acceptance.py` includes `research_case_revision_id` in both:

- strict preview/commit request DTOs;
- authoritative acceptance-view expected-vs-actual snapshot comparison.

A request that replaces only the Case Revision while preserving reviewed IDs/fingerprints must fail before writes.

### 8.3 Core validation and atomic binding

`IndustryThesisOwnerAcceptanceService` validates:

```text
submitted research_case_revision_id == reviewed Owner Context v2 value
ResearchCaseRevision exists
ResearchCaseRevision.case_id == reviewed research_case_id
ResearchCaseRevision.information_cutoff_date <= accepted output cutoff
ResearchCaseRevision.recorded_at_utc <= accepted transaction recorded boundary
```

After `IndustryThesisOutputLinkRevision` is appended, `IndustryThesisOutputCaseRevisionBinding` is appended in the same outer transaction before final flush/commit.

Any binding insert/FK/uniqueness/validation failure rolls back Stage1, semantics, candidate-pool, accepted-session, output and binding work together.

### 8.4 Output contract remains v1

Keep:

```text
OUTPUT_CONTRACT_VERSION = aquantai.industry-thesis-output-links.v1
```

The output row itself is not version-bumped merely to host the new association. The binding owns its own version contract. This preserves historical output read compatibility.

### 8.5 Result-page activation boundary

`industry_analysis/static/review_result.js` is in the future implementation allowlist because it currently determines whether an accepted reviewed plan may advance to owner acceptance. It must recognize v3 as the new active reviewed-plan contract while preserving historical read rendering.

`industry_analysis/static/review_result.html` is excluded: the frozen contract can render the added context through existing result containers. If implementation proves otherwise, scope expansion requires a separate owner amendment before commit.

---

## 9. Industry legacy and replay compatibility

### 9.1 Reviewed plan read versions

Readers support explicitly:

```text
v1 = historical pre-Owner-Context plan
v2 = Case/Map/MapRevision Owner Context v1
v3 = exact CaseRevision + Case/Map/MapRevision Owner Context v2
```

Only v3 is eligible for new bound acceptance after activation.

### 9.2 Unaccepted historical reviewed plans

An exact v1/v2 `reviewed_plan_ready` revision may enter an explicit v3 re-review only if no `IndustryThesisOutputLinkRevision` references it.

The re-review appends a new reviewed session/candidate revision. It never mutates the historical reviewed revision. The user explicitly selects the v3 Case Revision + Map Revision pair.

No v3 reviewed plan may be re-reviewed merely to swap its Case Revision; changing a reviewed context requires a new ordinary research/review lineage.

### 9.3 Accepted legacy outputs

Existing accepted outputs remain readable under output contract v1. Absence of a binding is represented exactly as:

```text
evidence_context_binding = unavailable
reason = exact_case_revision_binding_not_persisted
```

No endpoint/command in v1 may attach a new binding to an already accepted historical output.

### 9.4 Legacy owner-acceptance replay

Existing accepted owner-acceptance v1 transactions retain exact idempotent replay.

Version dispatch is frozen as:

```text
owner-acceptance-plan v1 -> legacy replay only
owner-acceptance-plan v2 -> active new writes
```

A v1 request succeeds only when it exactly replays an already accepted historical v1 graph under its original canonical shape. It may not create a new unbound accepted output after the amendment becomes active.

A legacy reviewed context with no already accepted output fails closed and requires explicit v3 re-review. The v1 fingerprint is never recomputed with a new Case Revision field.

---

## 10. Stage2 Company Research write-owner contract

`Stage2CompanyResearchCommandService` remains the sole owner of Company Research revisions.

### 10.1 First revision

`create_company_research(...)` requires:

```text
research_case_revision_id: UUID
```

The exact Stage1 handoff is validated as today. The service additionally loads/validates the exact Case Revision and inserts the first `Stage2CompanyResearchRevision` + its binding in the same transaction as the Stage2 research identity/handoff.

### 10.2 Later revisions

`append_research_revision(...)` also requires:

```text
research_case_revision_id: UUID
```

There is no implicit inheritance from the prior Company Research revision.

If revision N used R1 and N+1 intentionally remains on R1, the caller passes R1 again. Explicit reuse is valid.

If the caller passes R2, R2 independently must satisfy Case and chronology constraints.

### 10.3 Internal insert path

`_insert_research_revision(...)` receives the exact Case Revision as a required input and creates:

```text
Stage2CompanyResearchRevision
Stage2CompanyResearchRevisionCaseBinding
```

before returning from the transaction-owned operation.

Every post-amendment Company Research revision therefore has exactly one binding.

### 10.4 No legacy repair command

There is no `bind_existing_company_research_revision` command. Historical Stage2 revisions stay unbound. Any future historical repair workflow requires a new architecture decision and explicit user review.

---

## 11. Stable fail-closed semantics

### 11.1 Industry owner path

Freeze these codes:

```text
INDUSTRY_THESIS_ACCEPTANCE_CASE_REVISION_REQUIRED
INDUSTRY_THESIS_ACCEPTANCE_CASE_REVISION_MISMATCH
INDUSTRY_THESIS_ACCEPTANCE_CASE_REVISION_NOT_VISIBLE
INDUSTRY_THESIS_ACCEPTANCE_CASE_REVISION_CONTEXT_STALE
INDUSTRY_THESIS_ACCEPTANCE_CASE_REVISION_BINDING_CONFLICT
INDUSTRY_THESIS_ACCEPTANCE_LEGACY_CONTEXT_UNBOUND
```

Meanings:

- `...REQUIRED`: active v3/v2 write path omitted exact Case Revision;
- `...MISMATCH`: Case Revision does not belong to the frozen Case;
- `...NOT_VISIBLE`: cutoff/recorded chronology invalid;
- `...CONTEXT_STALE`: request/acceptance-view Case Revision differs from reviewed frozen context;
- `...BINDING_CONFLICT`: duplicate/conflicting binding or exact persistence conflict;
- `...LEGACY_CONTEXT_UNBOUND`: a bound-only action was requested for legacy history that never persisted a Case Revision.

### 11.2 Stage2 command path

Stage2 currently uses validation exceptions rather than a broad code-bearing family. Do not introduce a new general error framework solely for this amendment. Freeze exact identifiers/messages:

```text
stage2_case_revision_required
stage2_case_revision_case_mismatch
stage2_case_revision_not_visible
stage2_case_revision_binding_conflict
```

No failure path may search for a substitute Case Revision.

---

## 12. Migration contract

Current exact migration head on the architecture base is:

```text
20260803_0018
```

The future migration is exactly:

```text
path = migrations/versions/20260814_0019_exact_research_case_revision_bindings.py
revision = 20260814_0019
down_revision = 20260803_0018
```

### 12.1 Upgrade

Upgrade only:

1. creates `industry_thesis_output_case_revision_bindings`;
2. creates its bounded Case Revision audit index;
3. creates `stage2_company_research_revision_case_bindings`;
4. creates its bounded Case Revision audit index.

Forbidden migration behavior:

```text
INSERT
UPDATE
historical SELECT used to populate bindings
latest/max inference
coverage matching
nullable placeholder rows
```

Pre-existing accepted/research history is unchanged.

### 12.2 Downgrade

Binding rows are immutable accepted owner state. Downgrade must:

```text
if either binding table contains any row:
    raise RuntimeError and leave database unchanged
else:
    drop only the two binding tables in FK-safe order
```

It does not remove/rewrite any pre-existing table or column.

---

## 13. Read semantics after the amendment

The owner/schema implementation may expose an exact optional binding projection needed for focused tests and the later read integration, but it does not implement Evidence Pack UI.

For one exact owner revision:

```text
binding present + valid
  -> exact_bound

binding absent on legacy owner
  -> exact_case_revision_binding_not_persisted

binding present but graph/case/chronology invalid
  -> integrity failure, no fallback
```

A reader never searches other Case Revisions to turn `absent` into `bound`.

`aquantai.research-evidence-pack.v1` remains the sole authority for:

- Claim membership in the selected Case Revision;
- linked vs accepted-unlinked Evidence;
- local PDF acceptance receipt/citation replay;
- supersession visibility;
- provenance integrity.

This amendment owns only the exact Case Revision decision/binding.

---

## 14. Ordinary-user boundary of this amendment

The only ordinary-user UI work permitted in the future owner/schema implementation is what is necessary to make the new reviewed owner decision explicit:

```text
candidate review
  -> load exact Owner Context options
  -> user selects Case Revision + Map Revision pair
  -> no automatic default
  -> POST exact pair in owner_context
  -> reviewed result shows the frozen pair
  -> result page may advance v3 to acceptance
```

No evidence counts, Evidence Pack drawer, PDF citation navigation, conclusion rewrite or automatic acceptance belongs to this slice.

Company Research gets no new ordinary-user UI in this amendment; its authoritative command owner simply requires exact Case Revision input from an authorized caller.

---

## 15. Required future implementation tests

### 15.1 Industry core/review

Must prove:

- v3 review freezes exact Case Revision in Owner Context and reviewed fingerprint;
- replacing only Case Revision with unchanged reviewed identity fails;
- Case mismatch fails before writes;
- future cutoff/recorded Case Revision fails;
- owner-context options return exact pairs and `automatic_default = null`;
- ordering/pagination does not mutate selected identity;
- v3 review payload requires both revision IDs;
- explicit v3 re-review does not mutate a legacy reviewed revision.

### 15.2 Candidate-review UI contract

A new focused test:

```text
tests/test_industry_analysis_owner_context_v3_ui.py
```

must inspect/drive the active candidate-review surface and prove:

- `candidate_review.html` contains the explicit Owner Context v2 selection surface;
- `candidate_review.js` loads owner-context options;
- no first/only/latest automatic selection is applied;
- submit is blocked until one exact Case Revision + Map Revision pair is explicitly chosen;
- review payload sends both IDs under `owner_context`;
- UI does not infer Case/Map identities from display text or option index;
- stale reviewed-plan client constants are updated to v3;
- `review_result.js` recognizes v3 for the acceptance transition while preserving legacy rendering.

This test is the reason `candidate_review.html/js` are in the frozen implementation allowlist.

### 15.3 Industry owner acceptance

Must prove:

- preview has zero persisted writes;
- acceptance-view/request Case Revision mismatch fails before writes;
- commit inserts output + binding atomically;
- injected binding failure rolls back all owner writes;
- identical owner-acceptance v2 replay returns same output/binding identities;
- conflicting replay fails without altering the first graph;
- accepted legacy output remains readable with explicit unbound state;
- exact historical owner-acceptance v1 replay remains idempotent;
- legacy v1/v2 reviewed plans cannot create new unbound outputs.

### 15.4 Company Research

Must prove:

- initial Company Research revision requires exact Case Revision;
- append requires it every time;
- same Case Revision may be explicitly reused;
- no implicit inheritance;
- Case mismatch and chronology failure perform zero writes;
- revision + binding rollback together on injected failure;
- duplicate/conflicting binding fails closed;
- legacy unbound revisions remain untouched;
- SQLite/PostgreSQL behavior agrees.

### 15.5 Migration

Must prove:

- upgrade from `20260803_0018` creates exactly two tables;
- pre-existing owner history remains unchanged/unbound;
- no backfill SQL/historical mutation;
- empty upgrade/downgrade round trip succeeds;
- downgrade with either binding table non-empty refuses.

---

## 16. Exact future implementation allowlist

This allowlist is inactive until a separately authorized Strict Implementation Issue exists. It is intentionally limited so the owner/schema amendment cannot grow into Evidence Pack product integration.

### 16.1 Production owner/schema/API/UI files

```text
industry_alpha/industry_thesis_models.py
industry_alpha/industry_thesis_review.py
industry_alpha/industry_thesis_owner_acceptance_contracts.py
industry_alpha/industry_thesis_owner_acceptance.py
industry_alpha/industry_thesis_owner_acceptance_query.py
industry_alpha/industry_thesis_owner_acceptance_workbench.py
industry_alpha/stage2_models.py
industry_alpha/stage2_commands.py
backend/api/industry_analysis_review.py
backend/api/industry_analysis_acceptance.py
industry_analysis/static/candidate_review.html
industry_analysis/static/candidate_review.js
industry_analysis/static/review_result.js
migrations/versions/20260814_0019_exact_research_case_revision_bindings.py
```

`review_result.html` is excluded unless a later fixed-head implementation audit proves the exact frozen context cannot be rendered through existing containers. Any expansion requires project-owner authorization before commit.

No Evidence Pack result/drawer UI file is authorized.

### 16.2 Existing focused test files

```text
tests/test_industry_thesis_proposal_review.py
tests/test_industry_thesis_proposal_review_postgres.py
tests/test_industry_thesis_proposal_review_regressions.py
tests/test_industry_thesis_owner_context_v2_core.py
tests/test_industry_thesis_owner_acceptance.py
tests/test_industry_thesis_owner_acceptance_postgres.py
tests/test_industry_thesis_owner_acceptance_strict_negatives.py
tests/test_industry_thesis_owner_acceptance_workbench_v2.py
tests/test_industry_analysis_review_api.py
tests/test_industry_analysis_acceptance_v2_api.py
tests/test_industry_thesis_migration.py
tests/test_stage2_company_research.py
tests/test_stage2_company_research_postgres.py
tests/test_benchmark_migration.py
```

### 16.3 One new focused UI contract test

```text
tests/test_industry_analysis_owner_context_v3_ui.py
```

A later implementation Issue may narrow this list; it may not add files outside it without a separate owner scope amendment.

Normal CI remains zero-network. No Provider/OCR/AI dependency is needed.

---

## 17. Explicit exclusions

This amendment does not authorize or design:

- Evidence Pack summary/counts in Industry result;
- Company Research evidence drawer;
- PDF page navigation UI;
- automatic Evidence acceptance;
- automatic Claim creation;
- automatic Case Revision creation merely to satisfy a binding;
- historical binding repair/backfill;
- candidate score/status recomputation;
- accepted research conclusion rewrite;
- Provider/network/credentials/OCR/AI;
- recommendation/target price/expected return/portfolio/trading;
- scheduler/background worker/notification;
- release/tag/version change.

If the exact Case Revision needed by the user/caller does not exist, the owner operation fails closed. This slice never creates one as a side effect.

---

## 18. Stop conditions

Stop and return to the project owner if implementation would require:

- choosing a Case Revision without explicit user/caller identity;
- populating a binding for existing accepted history;
- modifying old reviewed plans, accepted outputs or Company Research revisions in place;
- changing the Research Evidence Pack selector contract;
- adding a generic polymorphic owner;
- adding a third binding owner;
- adding a migration beyond `20260814_0019`;
- adding accepted-result Evidence Pack UI;
- changing files outside the separately authorized implementation allowlist;
- touching Provider/network/OCR/AI, recommendation, portfolio or trading code.

---

## 19. Governance gate for this architecture PR

This preflight PR may contain exactly:

```text
.codex/tasks/issue-297-exact-research-case-revision-binding-owner-schema-v1-preflight.md
docs/exact_research_case_revision_binding_owner_schema_v1_preflight.md
```

It remains Draft.

Merge consideration requires:

```text
base = exact main@04c6683cd7820851556d01528848eafd421135f8
one immutable final HEAD
applicable CI = success on that HEAD
fresh fixed-HEAD architecture review = blocking_findings 0
unresolved review threads = 0
separate explicit project-owner Ready/merge authorization
```

Required review phrase:

```text
AUTHORIZED EXACT RESEARCH CASE REVISION BINDING OWNER/SCHEMA AMENDMENT V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

Merging this preflight freezes architecture only. It does **not** authorize model/table creation, migration `20260814_0019`, review/acceptance version changes, Stage2 command changes, tests, or subsequent Evidence Pack ordinary-user integration.