# Issue #297 — Exact Research Case Revision Binding Owner/Schema Amendment v1 — Strict Architecture Preflight

## Authority

Project-owner instruction on 2026-08-14:

> 从新的精确 main@04c6683cd7820851556d01528848eafd421135f8，针对 Exact Research Case Revision Binding Owner/Schema Amendment 单独进入下一阶段

Exact architecture base:

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
base = main@04c6683cd7820851556d01528848eafd421135f8
issue = #297
roadmap = #137
upstream = Issue #295 / merged PR #296
risk_tier = Strict Architecture Preflight
implementation_authorized = false
schema_migration_authorized = false
```

Issue #295 remains open; this Issue does not authorize its closure.

## Scope

This preflight may change only:

```text
.codex/tasks/issue-297-exact-research-case-revision-binding-owner-schema-v1-preflight.md
docs/exact_research_case_revision_binding_owner_schema_v1_preflight.md
```

No production code, model, migration, API/UI, test, fixture, workflow, dependency, Provider/network/OCR/AI, evidence acceptance, candidate recomputation, recommendation, portfolio, trading, release, tag or version file may change.

## Frozen architecture decision

The smallest safe amendment is two narrow append-only exact binding owners:

```text
IndustryThesisOutputLinkRevision
  -> IndustryThesisOutputCaseRevisionBinding
  -> exact ResearchCaseRevision

Stage2CompanyResearchRevision
  -> Stage2CompanyResearchRevisionCaseBinding
  -> exact ResearchCaseRevision
```

A generic polymorphic context-binding owner is not introduced.

Legacy accepted outputs/revisions remain unbound. There is no heuristic backfill and no latest/max/coverage/nearest/same-map/same-Claim inference.

## Industry Thesis contract

New writes must freeze the exact Case Revision during proposal review, before owner acceptance:

```text
active reviewed plan = aquantai.industry-thesis-acceptance-plan.v3
active Owner Context = aquantai.industry-thesis-owner-context.v2
active owner-acceptance plan = aquantai.industry-thesis-owner-acceptance-plan.v2
existing output-link contract = aquantai.industry-thesis-output-links.v1 (unchanged)
new binding contract = aquantai.industry-thesis-output-case-revision-binding.v1
```

Owner Context v2 contains exact:

```text
research_case_id
research_case_revision_id
industry_map_id
industry_map_revision_id
map_mode = reuse_exact_existing_map_revision
```

The review UI/API must require explicit confirmation of a valid Case Revision + Map Revision pair. `automatic_default = None` remains mandatory.

The exact Case Revision participates in reviewed-plan IDs/fingerprints, acceptance-view snapshot comparison, owner-acceptance plan fingerprint and owner transaction semantics. Body substitution is rejected before writes.

Historical reviewed-plan v1/v2 reads remain supported. An unaccepted legacy reviewed plan may enter an explicit v3 re-review path only if no accepted output exists; the old reviewed revision is never mutated. New v1/v2 owner-acceptance writes are prohibited. Existing accepted legacy output idempotent replay remains supported without inventing a binding.

## Company Research contract

Every newly created `Stage2CompanyResearchRevision`, including the first revision created by `create_company_research` and all later `append_research_revision` calls, requires an explicit `research_case_revision_id`.

The exact Case Revision is validated and the binding is inserted in the same database transaction as the Company Research revision.

Rules:

- exact Case Revision must exist;
- `ResearchCaseRevision.case_id == Stage2CompanyResearch.case_id`;
- Case Revision information cutoff <= Company Research revision cutoff;
- Case Revision recorded UTC <= Company Research revision recorded UTC;
- explicitly reusing the same Case Revision for a later Company Research revision is valid;
- implicit inheritance from the prior Company Research revision is prohibited.

## Schema and migration contract

Future implementation migration is frozen as:

```text
migrations/versions/20260814_0019_exact_research_case_revision_bindings.py
revision = 20260814_0019
down_revision = 20260803_0018
```

It creates only:

```text
industry_thesis_output_case_revision_bindings
stage2_company_research_revision_case_bindings
```

Each table has UUID PK, one NOT NULL direct FK to its owning revision, one NOT NULL FK to `research_case_revisions.id`, a NOT NULL binding contract version, a unique constraint on the owning revision, and a bounded audit index on `research_case_revision_id`.

Binding IDs are deterministic UUIDv5 from the owner revision ID + exact Case Revision ID + binding contract version. Binding rows are included in the corresponding append-only ORM mutation guard.

The migration performs zero INSERT/UPDATE/backfill. Downgrade refuses if either immutable binding table contains any row; if both are empty, it drops only the two binding tables.

## Legacy state

```text
evidence_context_binding = unavailable
reason = exact_case_revision_binding_not_persisted
```

No accepted legacy Industry Thesis output or Stage2 Company Research revision is rebound by this slice.

## Stable fail-closed semantics

Industry owner path freezes stable reason codes for:

```text
INDUSTRY_THESIS_ACCEPTANCE_CASE_REVISION_REQUIRED
INDUSTRY_THESIS_ACCEPTANCE_CASE_REVISION_MISMATCH
INDUSTRY_THESIS_ACCEPTANCE_CASE_REVISION_NOT_VISIBLE
INDUSTRY_THESIS_ACCEPTANCE_CASE_REVISION_CONTEXT_STALE
INDUSTRY_THESIS_ACCEPTANCE_CASE_REVISION_BINDING_CONFLICT
INDUSTRY_THESIS_ACCEPTANCE_LEGACY_CONTEXT_UNBOUND
```

Stage2 command validation must use equally stable exact binding failure identifiers/messages and may not fall back to another Case Revision.

## Future implementation allowlist — inactive until separately authorized

The later Strict implementation may modify only the exact families frozen in the detailed preflight, centered on:

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
focused existing owner/API/migration/PostgreSQL tests
```

The detailed document lists the exact test allowlist. Ordinary-user Evidence Pack result/drawer integration remains a later slice after this binding owner implementation is accepted.

## Governance

Keep the architecture PR Draft. Merge consideration requires:

```text
exact immutable HEAD
applicable CI = success
fresh fixed-HEAD architecture review = zero blockers
unresolved review threads = 0
separate project-owner Ready/merge authorization
```

Required review phrase:

```text
AUTHORIZED EXACT RESEARCH CASE REVISION BINDING OWNER/SCHEMA AMENDMENT V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

Merging this preflight authorizes neither schema/migration/write-owner implementation nor ordinary-user Evidence Pack integration.