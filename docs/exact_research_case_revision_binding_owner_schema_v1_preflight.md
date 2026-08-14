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

This preflight resolves the blocking authority gap identified by PR #296. It freezes **how a future separately authorized implementation must persist an exact `ResearchCaseRevision` decision** for Industry Thesis accepted outputs and Stage2 Company Research revisions. It does not implement the schema or write path.

---

## 1. Problem being solved

`aquantai.research-evidence-pack.v1` intentionally requires:

```text
research_case_id
research_case_revision_id
information_cutoff_date
recorded_at_utc
```

The accepted Industry Thesis and Company Research owners currently preserve exact Case, Map, Stage1, Claim and Evidence identities, but not one exact `ResearchCaseRevision.id`.

Therefore a future ordinary-user evidence integration cannot safely answer:

```text
Is this accepted Evidence linked into the exact research revision represented by this historical Industry/Company result?
```

without first persisting the missing owner decision.

The amendment is not allowed to infer the missing identity by:

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

Those selectors can change the meaning of historical research after newer Case Revisions are appended.

---

## 2. Current owner inventory on exact main

### 2.1 Research Case

`industry_alpha/models.py` owns `ResearchCaseRevision` with:

```text
id
case_id
revision_no
workflow_state
conclusion_status
information_cutoff_date
recorded_at_utc
supersedes_revision_id
```

`ResearchCaseRevision.id` is the exact Evidence Pack membership anchor. Accepted ledger rows are append-only.

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

It is append-only but contains no `research_case_revision_id`.

### 2.3 Industry Thesis review and acceptance

The accepted flow is:

```text
proposal review
-> exact reviewed-plan snapshot/fingerprint
-> acceptance workbench view
-> acceptance-view snapshot fingerprint
-> owner-acceptance preview
-> explicit commit with matching preview fingerprint
-> atomic accepted output
```

Current active versions are:

```text
reviewed plan = aquantai.industry-thesis-acceptance-plan.v2
Owner Context = aquantai.industry-thesis-owner-context.v1
owner-acceptance plan = aquantai.industry-thesis-owner-acceptance-plan.v1
output link = aquantai.industry-thesis-output-links.v1
```

Owner Context v1 freezes Case + Map + Map Revision, but not Case Revision.

### 2.4 Stage2 Company Research

`Stage2CompanyResearch` freezes Case/Map and exact Stage1 handoff identities.

`Stage2CompanyResearchRevision` freezes:

```text
company_research_id
revision_no
workflow_state
conclusion_status
research_question
summary
information_cutoff_date
recorded_at_utc
supersedes_revision_id
```

`Stage2CompanyResearchCommandService` owns creation of the first revision and every append. It does not currently accept a Case Revision.

---

## 3. Chosen owner shape

The amendment introduces exactly two narrow link owners.

### 3.1 Industry Thesis binding

Model:

```text
IndustryThesisOutputCaseRevisionBinding
```

Table:

```text
industry_thesis_output_case_revision_bindings
```

Semantic meaning:

```text
one exact IndustryThesisOutputLinkRevision
  -> one exact ResearchCaseRevision
```

### 3.2 Company Research binding

Model:

```text
Stage2CompanyResearchRevisionCaseBinding
```

Table:

```text
stage2_company_research_revision_case_bindings
```

Semantic meaning:

```text
one exact Stage2CompanyResearchRevision
  -> one exact ResearchCaseRevision
```

### 3.3 Rejected alternatives

A generic polymorphic owner such as:

```text
research_context_bindings(target_type, target_id, ...)
```

is rejected for v1. It weakens direct database referential integrity and introduces a generic abstraction not needed by the P0 product.

Adding a non-null `research_case_revision_id` column directly to existing owner revisions is also rejected. Existing historical rows have no trustworthy value and may not be heuristically backfilled.

Nullable columns would blur two different states:

```text
legacy decision was never persisted
vs
new owner intentionally selected no revision
```

The latter is not permitted for new writes, so explicit link-row presence is the cleaner contract.

---

## 4. Exact Industry binding schema

Future ORM model/table contract:

```text
IndustryThesisOutputCaseRevisionBinding
-------------------------------------------------------
id                         UUID PRIMARY KEY NOT NULL
output_link_revision_id    UUID NOT NULL FK -> industry_thesis_output_link_revisions.id ON DELETE RESTRICT
research_case_revision_id  UUID NOT NULL FK -> research_case_revisions.id ON DELETE RESTRICT
binding_contract_version   VARCHAR(128) NOT NULL
```

Required constraints:

```text
UNIQUE(output_link_revision_id)
CHECK(binding_contract_version = 'aquantai.industry-thesis-output-case-revision-binding.v1')
INDEX(research_case_revision_id, output_link_revision_id)
```

No independent mutable status, latest pointer, note or nullable fallback field is added.

Binding contract version:

```text
aquantai.industry-thesis-output-case-revision-binding.v1
```

Binding identity is deterministic:

```text
namespace = UUIDv5(NAMESPACE_URL, binding_contract_version)
id = UUIDv5(namespace, output_link_revision_id + ':' + research_case_revision_id)
```

The model is included in the Industry Thesis append-only mutation guard. Update/delete through ordinary ORM paths must fail exactly like accepted output history.

The binding has no separate `recorded_at_utc`. Its lifecycle is owned by the exact output transaction and its historical visibility is inherited from the owning `IndustryThesisOutputLinkRevision`. Avoiding a duplicated timestamp prevents two supposed transaction times from diverging.

The query/read integrity path must still verify that the binding exists only for the exact output and that the bound Case Revision is compatible with the output's frozen Case and boundary.

---

## 5. Exact Company Research binding schema

Future ORM model/table contract:

```text
Stage2CompanyResearchRevisionCaseBinding
-------------------------------------------------------
id                           UUID PRIMARY KEY NOT NULL
company_research_revision_id UUID NOT NULL FK -> stage2_company_research_revisions.id ON DELETE RESTRICT
research_case_revision_id    UUID NOT NULL FK -> research_case_revisions.id ON DELETE RESTRICT
binding_contract_version     VARCHAR(128) NOT NULL
```

Required constraints:

```text
UNIQUE(company_research_revision_id)
CHECK(binding_contract_version = 'aquantai.stage2-company-research-case-revision-binding.v1')
INDEX(research_case_revision_id, company_research_revision_id)
```

Binding contract version:

```text
aquantai.stage2-company-research-case-revision-binding.v1
```

Deterministic identity:

```text
namespace = UUIDv5(NAMESPACE_URL, binding_contract_version)
id = UUIDv5(namespace, company_research_revision_id + ':' + research_case_revision_id)
```

The model is included in `STAGE2_MODELS`, so existing append-only update/delete rejection applies.

Like the Industry binding, it has no second timestamp. Its owner is the exact Company Research revision transaction.

---

## 6. Cross-table invariants

Simple SQL foreign keys cannot express all semantic constraints across owner rows, so the authoritative write services must validate them inside the same transaction before binding insertion.

For every binding:

```text
ResearchCaseRevision exists
binding owner exists/is being created in this transaction
ResearchCaseRevision.case_id == owner authoritative case_id
ResearchCaseRevision.information_cutoff_date <= owner information_cutoff_date
ResearchCaseRevision.recorded_at_utc <= owner recorded_at_utc
```

For Industry Thesis, `owner authoritative case_id` is `IndustryThesisOutputLinkRevision.research_case_id` and must also equal the Case frozen by Owner Context v2.

For Company Research, it is `Stage2CompanyResearch.case_id` reached through the exact `Stage2CompanyResearchRevision.company_research_id`.

No database trigger is introduced. The repository already uses transaction-owned validation plus append-only constraints; v1 follows that convention and requires focused PostgreSQL negative coverage.

---

## 7. Industry Thesis — reviewed Owner Context v2

The exact Case Revision must be a **reviewed context choice**, not a hidden acceptance-time field.

### 7.1 New active versions

After the future implementation activates, new proposal reviews use:

```text
ACCEPTANCE_PLAN_VERSION = aquantai.industry-thesis-acceptance-plan.v3
OWNER_CONTEXT_VERSION = aquantai.industry-thesis-owner-context.v2
```

Owner Context v2 freezes:

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

### 7.2 Review input

The review API contract changes from:

```text
owner_context.industry_map_revision_id
```

to the explicit pair:

```text
owner_context.research_case_revision_id
owner_context.industry_map_revision_id
```

The server resolves the Case and Map identities and verifies both selected revisions belong to the same Research Case.

### 7.3 No automatic choice

Owner-context options remain explicit-confirmation only:

```text
explicit_confirmation_required = true
automatic_default = null
```

The options query returns valid exact pairs, never a separately selected Map followed by an inferred Case Revision.

Eligibility requires both revisions to be visible within:

```text
source thesis information_cutoff_date
review as_of_cutoff
review recorded UTC boundary
```

The ordering/cursor must be deterministic and include both revision identities as tie breakers. Pagination may not change which pair the user selected.

### 7.4 Fingerprint participation

The exact Case Revision is included in:

- Owner Context v2 canonical value;
- reviewed decision seed;
- reviewed-plan fingerprint;
- deterministic reviewed session/candidate IDs through that fingerprint;
- reviewed plan `recorded_at_utc_boundary` computation.

The plan recorded boundary must be at least the maximum recorded time of the source thesis revision, reviewed candidate source boundary, exact Map Revision and exact Research Case Revision.

Consequently later creation of another Case Revision cannot alter a frozen v3 reviewed plan.

---

## 8. Industry Thesis — owner acceptance v2

### 8.1 New active owner-acceptance plan

New writes use:

```text
aquantai.industry-thesis-owner-acceptance-plan.v2
```

The flat plan adds exactly:

```text
research_case_revision_id
```

next to the existing `research_case_id`/Map fields.

The canonical plan fingerprint includes it. The caller may not submit a different Case Revision while preserving the same reviewed-plan ID.

### 8.2 Acceptance-view snapshot

`IndustryThesisOwnerAcceptanceWorkbenchQueryService` must read the exact v3 reviewed plan and load:

```text
ResearchCase
ResearchCaseRevision
IndustryMap
IndustryMapRevision
```

from the frozen Owner Context v2.

The acceptance view exposes the exact Case Revision as non-editable reviewed context. `backend/api/industry_analysis_acceptance.py` includes `research_case_revision_id` in both:

- the strict request DTO;
- authoritative acceptance-view expected-vs-actual snapshot comparison.

A changed body Case Revision with unchanged top-level reviewed IDs/fingerprint must fail before any write.

### 8.3 Core validation and atomic output binding

`IndustryThesisOwnerAcceptanceService` validates all of the following before owner writes:

```text
submitted research_case_revision_id == reviewed Owner Context v2 value
ResearchCaseRevision exists
ResearchCaseRevision.case_id == reviewed research_case_id
ResearchCaseRevision.information_cutoff_date <= accepted output cutoff
ResearchCaseRevision.recorded_at_utc <= accepted transaction recorded boundary
```

After the exact `IndustryThesisOutputLinkRevision` is appended, the service appends `IndustryThesisOutputCaseRevisionBinding` in the **same outer transaction** before the final flush/commit.

Any binding insert, FK, uniqueness or validation failure rolls back Stage1, semantics, candidate-pool, accepted-session and output writes together.

### 8.4 Output contract remains v1

Keep:

```text
OUTPUT_CONTRACT_VERSION = aquantai.industry-thesis-output-links.v1
```

The output row itself does not acquire a new field. Bumping the singleton output contract would force the current exact-output query path either to reject historical outputs or to add unnecessary multi-version output semantics.

The new binding has its own version contract and optional read projection.

---

## 9. Industry legacy/replay compatibility

Version evolution must not reinterpret accepted history.

### 9.1 Reviewed plan reads

Read support remains explicit for:

```text
v1 = historical pre-Owner-Context plan
v2 = exact Case/Map/MapRevision Owner Context v1
v3 = exact CaseRevision + Case/Map/MapRevision Owner Context v2
```

Only v3 is eligible for **new bound owner acceptance** after activation.

### 9.2 Unaccepted historical reviewed plans

An exact v1 or v2 `reviewed_plan_ready` revision may be re-reviewed under v3 only when:

```text
no IndustryThesisOutputLinkRevision references that reviewed revision
```

The process appends a new reviewed session/candidate revision. It does not update the historical reviewed plan.

The user explicitly selects the v3 Owner Context pair. No Case Revision is inferred from the old Case/Map context.

A v3 reviewed plan cannot be re-reviewed merely to replace Case Revision context; a new ordinary research revision/review path is required if the reviewed choice must change.

### 9.3 Accepted legacy outputs

Existing accepted outputs remain readable under output contract v1.

If no binding row exists, their state is:

```text
evidence_context_binding = unavailable
reason = exact_case_revision_binding_not_persisted
```

This amendment provides **no endpoint or command to attach a binding later**.

### 9.4 Legacy owner-acceptance replay

Existing accepted v1 owner-acceptance transactions must preserve exact idempotent replay.

Implementation therefore requires version-dispatched normalization:

```text
owner-acceptance-plan v1 -> legacy replay only
owner-acceptance-plan v2 -> active new writes
```

A v1 request may succeed only when it exactly replays an already accepted v1 output graph under the historical canonical shape. It may not create a new unbound output after the binding amendment is active.

If no exact accepted output exists for a v1/v2 reviewed context, the request fails closed and requires explicit v3 re-review.

The legacy v1 canonical fingerprint is never recomputed with a new `research_case_revision_id` field.

---

## 10. Company Research write-owner contract

`Stage2CompanyResearchCommandService` remains the sole owner of Stage2 Company Research revisions.

### 10.1 First revision

`create_company_research(...)` must require:

```text
research_case_revision_id: UUID
```

The exact handoff is validated as today. Before inserting the binding, the command also loads and validates the exact Case Revision.

The first `Stage2CompanyResearchRevision` and its binding are inserted in the same existing transaction as the Stage2 research identity and frozen handoff.

### 10.2 Later revisions

`append_research_revision(...)` must also require:

```text
research_case_revision_id: UUID
```

There is no default from the prior revision.

If revision N used R1 and revision N+1 should also use R1, the caller explicitly supplies R1 again. This is valid.

If the caller supplies R2, it must independently satisfy same-Case and chronology constraints.

### 10.3 Internal insert function

`_insert_research_revision(...)` receives the exact Case Revision or its ID as a required argument and creates:

```text
Stage2CompanyResearchRevision
Stage2CompanyResearchRevisionCaseBinding
```

before returning.

This guarantees every newly created post-amendment Company Research revision has exactly one binding.

### 10.4 No legacy amendment command

There is no `bind_existing_company_research_revision` command in v1.

Existing Stage2 revisions stay unbound. A future explicit user-reviewed historical repair workflow, if ever needed, requires a new architecture decision.

---

## 11. Failure semantics

### 11.1 Industry stable codes

Add/freeze these owner-acceptance codes:

```text
INDUSTRY_THESIS_ACCEPTANCE_CASE_REVISION_REQUIRED
INDUSTRY_THESIS_ACCEPTANCE_CASE_REVISION_MISMATCH
INDUSTRY_THESIS_ACCEPTANCE_CASE_REVISION_NOT_VISIBLE
INDUSTRY_THESIS_ACCEPTANCE_CASE_REVISION_CONTEXT_STALE
INDUSTRY_THESIS_ACCEPTANCE_CASE_REVISION_BINDING_CONFLICT
INDUSTRY_THESIS_ACCEPTANCE_LEGACY_CONTEXT_UNBOUND
```

Intended meanings:

- `...REQUIRED`: active v3/v2 write path omitted exact Case Revision;
- `...MISMATCH`: Case Revision does not belong to the frozen Case;
- `...NOT_VISIBLE`: cutoff/recorded chronology invalid;
- `...CONTEXT_STALE`: request body or acceptance-view Case Revision differs from reviewed frozen context;
- `...BINDING_CONFLICT`: duplicate/conflicting binding or DB uniqueness/FK conflict;
- `...LEGACY_CONTEXT_UNBOUND`: legacy accepted/read context has no persisted exact binding where a bound action is required.

### 11.2 Stage2 stable identifiers

Stage2 currently uses `EvidenceLedgerValidationError` rather than a code-bearing Stage2 exception family. This amendment must not create a broad new error framework solely for two validation paths.

Freeze exact validation identifiers in the error text/tests:

```text
stage2_case_revision_required
stage2_case_revision_case_mismatch
stage2_case_revision_not_visible
stage2_case_revision_binding_conflict
```

A future HTTP product adapter may map these to Chinese UI errors in its own separately authorized slice. No fallback selector is permitted.

---

## 12. Migration contract

Current exact migration head on the architecture base is:

```text
20260803_0018
```

Future implementation migration is exactly:

```text
path = migrations/versions/20260814_0019_exact_research_case_revision_bindings.py
revision = 20260814_0019
down_revision = 20260803_0018
```

### Upgrade

Upgrade only:

1. creates `industry_thesis_output_case_revision_bindings`;
2. creates its bounded Case Revision audit index;
3. creates `stage2_company_research_revision_case_bindings`;
4. creates its bounded Case Revision audit index.

Explicitly forbidden in migration:

```text
INSERT
UPDATE
SELECT latest/max to populate rows
heuristic historical matching
nullable placeholder binding rows
```

### Downgrade

Because binding history is accepted immutable owner state, downgrade must:

```text
if either binding table contains a row:
    raise RuntimeError and preserve database
else:
    drop only the two binding tables in FK-safe order
```

The migration does not remove or rewrite any pre-existing table/column.

---

## 13. Read semantics after the amendment

The owner/schema implementation may expose an exact optional binding projection needed for tests and later read integration, but it does **not** implement the final Evidence Pack UI.

For one exact Industry output or Company revision:

```text
binding row present + valid -> exact_bound
binding row absent on legacy owner -> exact_case_revision_binding_not_persisted
binding row present but graph/case/chronology invalid -> integrity failure, no fallback
```

A reader never searches other Case Revisions to make `absent` look bound.

`aquantai.research-evidence-pack.v1` remains the only authority for:

- selected Case Revision Claim membership;
- linked vs accepted-unlinked Evidence;
- local PDF receipt/citation replay;
- supersession visibility;
- provenance integrity.

This amendment owns only the **selection/binding of the exact Case Revision**.

---

## 14. Ordinary-user boundary

The minimal Industry review UI change belonging to this owner amendment is only what is necessary to make the new owner decision explicit:

```text
Owner Context selection
  -> user chooses exact Case Revision + exact Map Revision pair
  -> no automatic default
  -> selected pair is shown in reviewed-plan result/acceptance context
```

It does not add Evidence Pack drawers, evidence counts, PDF citations or research conclusion rewrites.

Company Research has no new ordinary-user UI in this amendment; its command owner simply requires the exact input from any authorized caller.

The full Evidence Pack → Industry/Company ordinary-user read integration remains a later separately authorized slice after these binding owners are accepted on main.

---

## 15. Atomicity and idempotency tests required later

A future Strict implementation must prove at least:

### Industry

- v3 review freezes exact Case Revision in fingerprint;
- replacing Case Revision with same reviewed revision ID fails;
- Case mismatch fails before writes;
- future-cutoff or future-recorded Case Revision fails;
- acceptance preview performs zero persisted writes;
- commit inserts output + binding atomically;
- injected binding failure rolls back Stage1/semantics/pool/accepted session/output;
- identical v2 owner-acceptance replay returns same output/binding identities;
- conflicting replay fails and preserves first accepted graph;
- accepted legacy v1 output remains readable with explicit unbound binding state;
- exact legacy v1 owner-acceptance replay remains idempotent;
- legacy v1/v2 reviewed plan cannot create a new unbound output;
- explicit v3 re-review does not mutate legacy reviewed revision.

### Company Research

- initial Company Research revision requires exact Case Revision;
- append requires exact Case Revision every time;
- same Case Revision may be explicitly reused;
- no implicit inheritance test;
- Case mismatch and chronology failure produce zero writes;
- revision + binding rollback atomically on injected binding failure;
- duplicate binding conflicts fail closed;
- legacy unbound revisions remain untouched;
- SQLite and PostgreSQL behavior agree.

### Migration

- upgrade from `20260803_0018` creates exactly two tables;
- pre-existing owner history remains unchanged and unbound;
- upgrade/downgrade empty round trip succeeds;
- downgrade with either binding table non-empty refuses;
- no backfill SQL or historical mutation.

---

## 16. Exact future implementation allowlist

This allowlist is **inactive until a separately authorized Strict Implementation Issue exists**. It is frozen now so the owner/schema amendment cannot grow into the later Evidence Pack product integration.

### Production owner/schema/API/UI files

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
industry_analysis/static/review_result.js
migrations/versions/20260814_0019_exact_research_case_revision_bindings.py
```

`review_result.html` requires no structural change for the frozen contract and is excluded unless a later fixed-head implementation audit proves a Case Revision confirmation cannot be rendered safely through the existing containers. Expanding to it would require project-owner scope amendment before commit.

No accepted-result Evidence Pack UI file is authorized.

### Focused existing test files

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

A later implementation Issue may narrow this list further. It may not add files outside it without separate owner authorization.

Normal CI remains zero-network. No Provider/OCR/AI call is needed for any binding test.

---

## 17. Explicit exclusions

This amendment does not authorize or design:

- Evidence Pack evidence-summary counts in Industry result;
- Company Research evidence drawer;
- PDF page navigation UI;
- automatic Evidence acceptance;
- automatic Claim or Case Revision creation;
- automatic creation of a Case Revision merely to satisfy a binding;
- historical binding repair/backfill;
- candidate score/status recomputation;
- research conclusion rewrite;
- Provider/network/OCR/AI;
- recommendation, target price, expected return, portfolio or trading;
- scheduler, polling, background worker or notification;
- release/tag/version change.

If the explicit Case Revision the user/caller needs does not exist, the owner operation fails closed. This slice never creates one as a side effect.

---

## 18. Stop conditions

Stop and return to the project owner if implementation would require:

- choosing a Case Revision without explicit user/caller identity;
- populating a binding for existing accepted history;
- modifying an old reviewed plan/output/Company Research revision in place;
- changing the Research Evidence Pack selector contract;
- adding a generic polymorphic owner;
- adding a third binding owner not frozen here;
- adding a migration beyond `20260814_0019`;
- changing ordinary accepted-result Evidence Pack UI;
- touching Provider/network/OCR/AI, recommendation, portfolio or trading code;
- changing files outside the separately authorized implementation allowlist.

---

## 19. Governance gate for this preflight PR

This architecture PR must contain exactly:

```text
.codex/tasks/issue-297-exact-research-case-revision-binding-owner-schema-v1-preflight.md
docs/exact_research_case_revision_binding_owner_schema_v1_preflight.md
```

It remains Draft.

Merge consideration requires:

```text
base = exact main@04c6683cd7820851556d01528848eafd421135f8
one immutable HEAD
applicable CI = success
fresh fixed-HEAD architecture review = blocking_findings 0
unresolved review threads = 0
separate explicit project-owner merge authorization
```

Required review phrase:

```text
AUTHORIZED EXACT RESEARCH CASE REVISION BINDING OWNER/SCHEMA AMENDMENT V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

Merging this preflight would freeze architecture only. It would **not** authorize the model classes, migration `20260814_0019`, review/acceptance version changes, Stage2 command changes, tests, or subsequent Evidence Pack ordinary-user integration.