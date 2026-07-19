# Issue #62 — v0.6A Blocking Review Revision

## State

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#62`
- Branch: `feat/v06a-company-research`
- Draft PR: `#63` — `[v0.6A] Add Stage 2 company research foundation`
- Required base and ancestor: `df6d78299d0761a6911457ca4a3b6959b195eeb4`
- Reviewed implementation Head: `51023297d14fdb90067182e1782eafd06f24a457`
- Blocking COMMENT review: `4729717724`
- Implementation CI: `29669976949` — success
- Version remains `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #62, PR #63, review `4729717724`, the merged v0.5A-v0.5C boundaries and the current Stage 2 implementation before editing.

Keep PR #63 Draft/Open/unmerged and Issue #62 Open. Do not modify PR #38, create a release/tag, change version, begin v0.6B, or broaden the feature.

## Objective

Fix only the three blocking correctness defects identified in review `4729717724`. Preserve the accepted v0.6A architecture, schema, public routes and exclusions.

## Required correction 1 — supported hypothesis claim status

`Stage2CompanyResearchCommandService._insert_hypothesis_revision()` currently treats any visible A/B/C `supports` evidence as sufficient for `hypothesis_status="supported"`, regardless of the bound `ClaimRevision.claim_status`.

Change the rule to match the reviewed Stage 1 contract:

- at least one bound claim revision must have `claim_status == "supported"`;
- that same supported claim revision must have visible A/B/C evidence with relation `supports` at the hypothesis cutoff and recorded-time boundary;
- no visible contradiction may exist across the bound claim/evidence boundary;
- D-only evidence remains insufficient;
- a draft, disputed or rejected claim revision must not independently support a `supported` hypothesis, even when it has an A/B/C supporting evidence link;
- keep the existing `disputed` rule: a disputed claim revision or visible contradiction is required.

Add focused regressions for:

1. draft claim + A/B/C support rejected for a supported hypothesis;
2. disputed claim + A/B/C support but no contradiction rejected for a supported hypothesis;
3. rejected claim + A/B/C support rejected for a supported hypothesis;
4. supported claim + visible A/B/C support accepted when no contradiction is visible;
5. transaction rollback leaves no partial hypothesis identity, revision or links after rejection.

## Required correction 2 — exact Stage 1 evidence boundary

`_freeze_handoff_boundary()` currently freezes evidence using the later Stage 2 creation cutoff and timestamp. This can admit evidence or claim-evidence links appended after the frozen Stage 1 beneficiary revision.

Freeze the Stage 1 handoff exactly as the accepted beneficiary revision saw it:

- claim and assertion links must remain limited to links recorded no later than `beneficiary_revision.recorded_at_utc`;
- evidence information dates must be no later than both the claim revision cutoff and `beneficiary_revision.information_cutoff_date`;
- evidence rows and claim-evidence links must be recorded no later than `beneficiary_revision.recorded_at_utc`;
- the later Stage 2 creation cutoff/timestamp may additionally restrict visibility, but must never expand the Stage 1 boundary;
- frozen Stage 2 handoff reads must remain unchanged after later Stage 1 evidence/link additions.

Prefer reusing or mirroring the already accepted Stage 1 evidence-boundary semantics rather than introducing a new interpretation.

Add regressions that:

1. create or identify a supported beneficiary revision;
2. append a new evidence item and claim-evidence link after that beneficiary revision but before Stage 2 creation;
3. create Stage 2 research later;
4. prove the late evidence/link is absent from `stage2_handoff_evidence_links` and `frozen_stage1_handoff`;
5. prove the original evidence boundary remains deterministic and sufficient;
6. prove failed handoff validation rolls back all Stage 2 rows.

## Required correction 3 — append-only verification-item visibility

`add_verification_item()` permits later checklist rows, but `_research_revision_payload()` currently requires each item timestamp to be no later than the parent research revision timestamp. A legitimately appended item is therefore permanently invisible.

Correct the read semantics:

- a verification item belongs to its exact company-research revision;
- it becomes visible when its own `recorded_at_utc` is visible under `as_of_cutoff`;
- do not require an appended item to have been recorded at or before the parent revision timestamp;
- current reads must include later accepted items;
- an earlier cutoff must exclude items recorded after that cutoff;
- ordering remains deterministic by `item_no` and stable ID;
- chronology validation in `add_verification_item()` must continue to prevent backdating before the research revision or prior checklist history.

Add regressions for:

1. appending an item after the research revision;
2. current detail includes the appended item;
3. a cutoff before the item excludes it;
4. a cutoff on/after the item's UTC date includes it;
5. item numbering and strict JSON ordering are deterministic;
6. invalid backdating remains atomic.

## Allowed implementation scope

Expected files are limited to the smallest necessary subset of:

- `industry_alpha/stage2_commands.py`
- `industry_alpha/stage2_query.py`
- `industry_alpha/stage2_fixtures.py` only if a deterministic fixture change is genuinely needed
- `tests/test_stage2_company_research.py`
- `tests/test_stage2_company_research_postgres.py` only if PostgreSQL-specific coverage is needed
- focused Stage 2 documentation only when behavior text must be corrected
- this task file

Do not add or alter migrations unless a demonstrated schema defect makes it unavoidable. The current schema migration `20260719_0008` should remain the only v0.6A migration.

Do not alter public route shapes, introduce HTTP mutation routes, change dependencies, Docker/Compose, CI, launchers, version, release/tag state, valuation, scoring, ranking, recommendations, Quant automatic scoring, LLM/provider execution, scraping, watchlists, portfolios, brokers, orders or trading.

## Validation

Run and report exact results for:

- focused Stage 2 SQLite/API tests;
- focused PostgreSQL Stage 2 tests when `TEST_DATABASE_URL` is available;
- full offline suite;
- full PostgreSQL suite when available;
- clean Alembic `base -> head`;
- `20260719_0008 -> 20260719_0007 -> 20260719_0008` round trip;
- `python -m alembic check`;
- all offline demos, including `python -m scripts.demo_stage2_company_research`;
- explicit no-network coverage;
- `python -m compileall -q backend industry_alpha scripts tests`;
- `git diff --check`.

Confirm:

- no new migration;
- no dependency/CI/launcher/version changes;
- PR #38 remains unchanged at `a57f71d2677b35c678bc8477c9ce783c90294c66`;
- PR #63 remains Draft/Open/unmerged;
- Issue #62 remains Open.

## Delivery

1. Implement only these three corrections on `feat/v06a-company-research`.
2. Update PR #63 and Issue #62 with the new Head, exact changed files, defect closures and exact validation counts.
3. Keep PR #63 Draft and Issue #62 Open.
4. Stop for ChatGPT re-review. Do not merge, close Issue #62, create a release/tag, change version, begin v0.6B or modify PR #38.