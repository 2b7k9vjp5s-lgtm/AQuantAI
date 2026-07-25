# Issue #236 Task Snapshot — Industry Thesis Owner Acceptance and Exact Output Links Core

## Authority

- Authoritative implementation Issue: #236.
- Architecture authority: Issue #234, merged PR #235, `docs/industry_thesis_owner_acceptance_output_links_preflight.md`, and Issue #234 clarification comment `5076745911`.
- Product Roadmap: #137.
- Project-owner authorization on 2026-07-25:

```text
P0-1 — 启动 Core Implementation Slice：
Industry Thesis Owner Acceptance and Exact Output Links
```

- Exact implementation base: `b5b0abbeb3e4eb56eb0527bda0f18732105e9ad4`.
- Branch: `feat/industry-thesis-owner-acceptance-core`.
- Workflow: `.codex/WORKFLOW.md`.
- Risk tier: **Strict Implementation**.

## Objective

Implement the accepted offline transition:

```text
reviewed_plan_ready
  -> strict explicit owner-acceptance input
  -> deterministic dry-run preview and fingerprint
  -> explicit matching commit request
  -> one atomic transaction through existing owner ports
  -> accepted_outputs_linked
  -> exact output-link, complete-result and readiness reads
```

The implementation must preserve append-only history and existing domain ownership. No free text, draft graph, company label, Provider field or AI result may become accepted owner state by inference.

## Authorized file families

```text
.codex/tasks/issue-236-industry-thesis-owner-acceptance-core.md
industry_alpha/industry_thesis_*.py
industry_alpha/stage1_*.py only for session-bound Stage 1 owner ports
industry_alpha/beneficiary_semantics_*.py only for session-bound semantic owner ports
migrations/versions/20260725_0017_industry_thesis_owner_acceptance.py
migrations/env.py only if registration is required
scripts/*industry_thesis* for local JSON-only commands/demos
tests/test_industry_thesis_*.py
tests/test_stage1_beneficiaries*.py only for owner-port regression/concurrency
tests/test_beneficiary_semantics*.py only for owner-port regression
tests/*migration*.py and PostgreSQL migration tests only for migration 0017
docs/architecture_baseline.md only for accepted-state synchronization
industry_alpha/__init__.py or industry_alpha/industry_thesis_service.py only for bounded exports
```

No backend API, HTTP, browser or UI file is authorized.

## Required implementation

1. Migration `20260725_0017_industry_thesis_owner_acceptance` changes only thesis output-link schema.
2. Strict owner-acceptance plan parser, canonicalization and SHA-256 fingerprint.
3. Stable technical reason codes with ordinary-Chinese messages.
4. Session-bound Stage 1 owner write port reusing current validation.
5. Session-bound Typed Semantics owner write port reusing current validation.
6. One outer coordinator transaction with fixed database lock order.
7. Every append target uses exact expected-latest.
8. Only `draft / supported / disputed` Stage 1 revisions enter the accepted manifest; `rejected` is blocked.
9. Complete accepted result and supported-only Stage 1 pool remain separate.
10. Zero-supported acceptance stores a null pool revision and creates no fake pool.
11. Accepted thesis session transition freezes exact owner plan/result.
12. Exact output-link writer with deterministic UUIDv5 transaction key and idempotent replay.
13. Exact output/result/readiness query services with dual-as-of visibility and no latest fallback.
14. Local JSON-only preview, commit and read commands/demos.

## Migration contract

The migration may:

- make `accepted_candidate_pool_revision_id` nullable;
- add exact accepted and reviewed session revision IDs;
- add exact Research Case ID;
- add output contract version;
- add reviewed-plan fingerprint;
- add strict ordered per-candidate owner bindings;
- add uniqueness for one output revision per accepted session revision.

It must not modify Stage 1, Typed Semantics or another owner table.

Upgrade refuses before mutation when existing output-link rows cannot be deterministically backfilled. Downgrade refuses before any lossy action when populated v1 rows exist. Test supported SQLite and PostgreSQL separately.

## Golden path

One exact Research Case and exact existing Industry Map revision with three selected candidates:

- A: supported Stage 1, optional semantic revision, included in handoff;
- B: draft/disputed Stage 1, preserved in complete result, excluded from handoff;
- C: supported Stage 1 with downstream readiness gaps, included in handoff.

One atomic commit must produce exact owner outputs, accepted session revision and output link. Exact reads reproduce all three in frozen order. No Investment Candidate snapshot or score is created.

## Zero-supported path

Accept at least two valid draft/disputed members, freeze both, store null handoff pool, and create no empty or fabricated Stage 1 candidate pool.

## Primary blocked path

A selected candidate is listed-instrument-only or lacks exact Stage 1 assertion/claim bindings:

- preview returns a stable blocked reason;
- no commit-ready fingerprint is returned;
- commit fails before writes;
- no partial owner or thesis rows exist;
- reviewed plan remains unchanged.

## Additional validation

- strict unknown-field rejection;
- stable plan ordering/fingerprint;
- explicit separation of reviewed exposure, legacy kind and typed semantics;
- `rejected` Stage 1 state blocked;
- owner ports never commit or roll back;
- existing public Stage 1 and semantic commands retain behavior;
- expected-latest for beneficiary, semantic, pool and thesis session appends;
- fixed lock ordering;
- rollback after later candidate, semantic, pool or output-link failure;
- idempotent replay and conflicting replay;
- exact graph-integrity checks and dual-as-of reads;
- no network, Provider, AI or credential path;
- no recommendation, target price, expected return, position, portfolio, broker, order or trading fields.

## Locked exclusions

No FastAPI/API route, HTTP adapter, browser UI, ordinary-user selectors, background task, retry loop, scheduler, webhook, Provider/THS/CNINFO/news/disclosure access, credentials, external network, AI call, new Industry Map facts, draft-graph promotion, fuzzy identity bridge, automatic classification mapping, automatic Company Research, automatic component scoring, automatic Investment Candidate snapshot, recommendation, price target, expected return, position sizing, portfolio execution, broker, order, trading, release, tag or version change.

The `P0-1 Ordinary-User Completion Slice` remains separate and unauthorized.

## Stop conditions

Stop and return for owner review if implementation requires:

- free-text/draft-graph promotion;
- a missing authoritative Research Case/map/stock/assertion/claim owner;
- duplicated owner validation or direct coordinator writes to another owner’s ORM rows;
- fake supported state or inability to preserve a zero-supported result;
- hidden latest selection or history rewrite;
- another infrastructure boundary;
- network, Provider, AI, recommendation, portfolio or trading behavior.

## Delivery gates

1. Keep one implementation branch and one Draft PR.
2. Keep base-to-head inventory inside the authorized families.
3. Run focused tests, full relevant regression, complete pytest and every configured offline demo on the exact final HEAD.
4. Obtain process-independent fixed-head implementation review with:

```text
AUTHORIZED INDUSTRY THESIS OWNER ACCEPTANCE AND OUTPUT LINKS CORE IMPLEMENTATION APPROVED at fixed head <FULL_HEAD_SHA>
```

5. Resolve every review thread.
6. Any new commit invalidates previous exact-head CI and review.
7. Await separate owner authorization before merge:

```text
批准合并 PR #<number>
```

8. PR merge and Issue #236 closure require separate authorizations.
