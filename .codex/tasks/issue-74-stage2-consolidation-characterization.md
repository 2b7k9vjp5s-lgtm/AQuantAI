# Issue #74 - Stage 2 Consolidation Characterization

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#74`
- Work type: consolidation/refactoring characterization
- Base and required ancestor: `09c33f6b2da2432ec18e0dd104931a5879d2f5d6`
- Branch: `docs/stage2-consolidation-characterization`
- Draft PR: `[Consolidation] Characterize Stage 2 shared infrastructure`
- Released version remains `0.2.0`.

This task authorizes documentation-only characterization. It does not authorize application refactoring.

## Authorized files

The complete branch diff may contain only:

- `.codex/tasks/issue-74-stage2-consolidation-characterization.md`
- `docs/stage2_consolidation_characterization.md`

Do not modify application code, models, migrations, repositories, commands, APIs, fixtures, demos, tests, provider behavior, dependencies, Docker, CI, frontend/UI, version metadata, releases/tags, v0.6E, v0.7, or PR #38.

## Objective

Characterize repeated Stage 2 infrastructure across v0.6A-v0.6D and choose one smallest safe later refactor. Separate mechanical duplication from domain semantics. Do not generalize schemas or behavior for aesthetic consistency.

## Required evidence

Inspect the merged file families introduced by PRs #63, #65, #67 and #69:

- models and append-only listeners;
- command services;
- frozen upstream-boundary validation;
- repositories;
- cutoff-aware queries and evidence serialization;
- fixtures;
- SQLite and PostgreSQL tests.

Record concrete evidence, including:

- repeated ordered row loaders and linked-row loaders;
- repeated identity/revision transaction shape;
- repeated revision locks, integrity translation and latest-revision selection;
- repeated UTC/cutoff visibility and chronology helpers;
- repeated claim/evidence graph loading and read serialization;
- repeated append-only SQLAlchemy listeners;
- v0.6D private imports from `stage2_assessments_commands.py`.

## Classification

Classify each candidate as:

1. safe pure extraction;
2. shareable only after a neutral contract is explicit;
3. domain-specific and must remain local;
4. deferred because concurrency, ORM event, schema or compatibility risk is too high.

## Required first-slice decision

Determine whether the first later implementation should extract only the neutral v0.6A/v0.6B frozen-boundary mechanics currently shared by v0.6C and v0.6D.

The candidate neutral module may own:

- an immutable typed base boundary value object;
- exact unique upstream revision loading;
- company-research row locking;
- normalized UTC/cutoff visibility helpers;
- construction of the exact v0.6A/v0.6B base boundary.

The report must keep these domain-local:

- assessment and judgment status vocabularies;
- supported/disputed eligibility rules specific to a slice;
- quality-judgment outcome/evidence-state rules;
- v0.6C catalyst/risk extension validation;
- domain payload fields and API notices;
- repository/query/model/listener consolidation in the first slice.

## No-migration decision

The characterization must explicitly state that the first extraction requires no migration, no schema change, no persisted-data rewrite and no API contract change.

## Rollback and proof

Design the later extraction so rollback is a pure import/source move. Existing v0.6C/v0.6D SQLite and PostgreSQL behavior, payloads, error messages, transaction rollback and concurrency tests must remain unchanged.

## Validation

Run and report:

- exact base-to-head two-file inventory;
- `git diff --check` where available;
- unchanged `python -m pytest -q`;
- unchanged `python -m scripts.demo_research_flow`;
- final GitHub Actions status;
- environment limitations.

## Stop gate

Open the Draft PR, synchronize Issue #74 and stop for ChatGPT review.

Do not create a shared module, change imports, modify tests, or begin any later feature or migration from this task.