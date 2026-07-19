# Issue #64 — v0.6B Deterministic Fixture Follow-up

## State

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#64`
- Branch: `feat/v06b-expectations-valuation`
- Draft PR: `#65`
- Required base: `c94c5ecbac66e43c2c369f36ba64c9b7a13655b6`
- Re-reviewed implementation Head: `490ba647db14ab4d8bf186f67d77002e76bdd999`
- Re-review COMMENT: `4729972569`
- Implementation CI: `29672819935` — success
- Version remains `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #64, PR #65, review `4729972569`, and this task before editing.

Keep PR #65 Draft/Open/unmerged and Issue #64 Open. Do not merge, release/tag, change version, begin v0.6C, or modify PR #38.

## Review result

The three blockers from review `4729846016` are closed. Preserve those accepted fixes unchanged.

One deterministic-fixture blocker remains in `build_stage2_expectation_valuation_fixture()`:

- after both valuation revisions exist, `valuation_revision_id` is populated by selecting `Stage2ValuationSnapshotRevision` using only `valuation_id`;
- without an exact `revision_no` predicate or explicit deterministic ordering, SQL may return either revision;
- this can make `valuation_revision_id` backend/query-plan dependent or equal to `later_valuation_revision_id`, violating the stable fixture-ID contract.

## Required fix

1. Make `valuation_revision_id` deterministically identify the intended initial valuation revision (`revision_no == 1`). Prefer capturing the exact revision before the later append or selecting it with an exact revision predicate.
2. Keep `later_valuation_revision_id` bound to the later revision and prove the two IDs are distinct.
3. Add focused SQLite and PostgreSQL assertions that:
   - `valuation_revision_id` resolves to revision number 1;
   - `later_valuation_revision_id` resolves to revision number 2;
   - the IDs differ;
   - repeated fixture construction in clean databases preserves these semantics.
4. Do not change the domain model, migration `20260719_0009`, API routes, command/query behavior, dependencies, CI, Docker, launchers, docs unrelated to this correction, or any other roadmap stage.

## Validation

Run and report exact results for:

- focused SQLite v0.6B tests;
- focused PostgreSQL v0.6B tests;
- full offline suite;
- full PostgreSQL persistence/Industry Alpha suite when available;
- clean Alembic `base -> head`;
- `20260719_0009 -> 20260719_0008 -> 20260719_0009`;
- `python -m alembic check`;
- all offline demos;
- explicit no-network coverage;
- `python -m compileall -q backend industry_alpha scripts tests`;
- `git diff --check`.

## Delivery

Update PR #65 and Issue #64 with the new Head, exact changed files and exact validation results. Keep PR Draft and Issue Open, then stop for ChatGPT re-review. Do not merge, begin v0.6C, release/tag, change version, or modify PR #38.