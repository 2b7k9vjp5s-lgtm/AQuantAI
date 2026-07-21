# Issue #146 — Product Surface Baseline Synchronization

## Authority

- GitHub Issue: #146
- Required base: `c24b61822e995ee48ae9f06e5cd1e97a47b43be2`
- Related consolidation: Issue #144 / PR #145
- Related roadmap: Issue #137
- Work type: architecture/current-state synchronization, documentation only

## Objective

Synchronize `docs/architecture_baseline.md` with the product surfaces and consolidation decisions already merged to `main`, and identify Company Research Workspace v1 Architecture Preflight as the next product gate without authorizing implementation.

## Authorized files

1. `docs/architecture_baseline.md`
2. `.codex/tasks/issue-146-product-surface-baseline-sync.md`

No other file is authorized.

## Required state

The baseline must record:

- released version remains `0.2.0`;
- merged capability remains v0.6D plus reviewed read-only product surfaces;
- Evidence Intelligence / Research Change Feed is merged through PR #139;
- Industry Beneficiary Workspace v1 is merged through PR #143;
- consolidation review is completed through PR #145;
- no production consolidation refactor or generic workspace framework is required;
- domain serializers, notices, cutoff and failure semantics remain local;
- existing Stage 2 list services must not be composed for a future product overview;
- one explicit `company_research_id` is the candidate identity for the next preflight;
- Company Research Workspace v1 is only the next Architecture Preflight, not an authorized implementation;
- Canonical Price and Comparison Eligibility remain unresolved;
- computed expectation gap, fair value, target price, expected return, ranking, total score and recommendation state remain excluded.

## Constraints

- documentation only;
- no production code, API, UI, test, fixture, model, schema, migration, Provider, dependency, release or version change;
- no data-meaning, Semantic Level, Derivation Level, cutoff, revision or provenance change;
- no implementation Issue for Company Research Workspace before this synchronization is merged;
- no modification of unrelated PRs or branches, including PR #38.

## Validation

Verify:

1. base-to-head changed files are exactly the two authorized files;
2. the obsolete Evidence Intelligence-as-future sequence is removed;
3. current runtime/product surfaces are explicit;
4. the accepted consolidation decision is represented accurately;
5. the next preflight is bounded to existing v0.6A-v0.6D exact persisted contracts;
6. price/comparison/ranking/recommendation exclusions remain explicit;
7. full existing CI and fixture demo pass.

## Completion gate

Keep the PR Draft/Open/unmerged.

Record:

- exact base and head SHA;
- complete changed-file inventory;
- documentation decisions;
- CI run and results;
- limitations and exclusions.

Independent review must use:

`ARCHITECTURE BASELINE SYNC APPROVED at fixed head <HEAD_SHA>`

Do not merge or create the Company Research Workspace preflight Issue without explicit owner authorization after independent fixed-head approval.
