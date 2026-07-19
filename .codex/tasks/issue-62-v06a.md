# Issue #62 — v0.6A Acceptance Handoff

## Accepted state

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#62`
- Branch: `feat/v06a-company-research`
- PR: `#63` — `[v0.6A] Add Stage 2 company research foundation`
- Required base: `df6d78299d0761a6911457ca4a3b6959b195eeb4`
- Accepted implementation Head: `ad457b678af9b42aa7f77a67d653d0a3c9e1b086`
- Accepted COMMENT review: `4729744938`
- Final implementation CI: `29670722732` — success
- Version remains `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #62, PR #63, review `4729744938`, and this handoff before acting.

## Accepted scope

v0.6A is accepted as a bounded, local-first, append-only and cutoff-aware Stage 2 company-research foundation.

Accepted behavior includes:

- exact handoff from one frozen v0.5C candidate-pool revision and membership;
- exact beneficiary, map assertion, successful company snapshot, claim and evidence provenance;
- immutable company-research and financial-transmission hypothesis revisions;
- strict same-case/map/company ownership, UTC chronology, information-date and recorded-date cutoff boundaries;
- `supported` hypotheses requiring a visible supported A/B/C-backed claim revision with no visible contradiction;
- disputed, missing-evidence and D-only boundaries remaining explicit;
- Stage 1 handoff evidence frozen at the beneficiary revision cutoff and recorded timestamp;
- append-only verification items visible according to their own recorded timestamp;
- completed-research `后续验证清单` enforcement;
- deterministic read-only `/industry-alpha/company-research` APIs;
- deterministic no-network fixture/demo and transactional rollback;
- migration `20260719_0008` as the only v0.6A migration.

The focused correction from task-sync Head `2864c87dbaf0f1a02eee0b15faba61917ca8942f` to accepted implementation Head changed only:

- `industry_alpha/stage2_commands.py`
- `industry_alpha/stage2_query.py`
- `tests/test_stage2_company_research.py`

## Accepted validation

- focused Stage 2 SQLite/API: `39 passed, 1 warning`
- full offline: `437 passed, 40 skipped, 1 warning`
- full PostgreSQL: `468 passed, 9 skipped, 1 warning`
- GitHub Actions `29670722732`: success, tests and local fixture demo passed
- Alembic upgrade/check and `20260719_0008 -> 20260719_0007 -> 20260719_0008`: passed
- all offline demos: passed with the documented host `DATABASE_URL` correction for Compose hostname use
- explicit no-network test, compileall and `git diff --check`: passed

## Current instruction

Verify only that:

1. the branch contains accepted implementation Head `ad457b678af9b42aa7f77a67d653d0a3c9e1b086` as an ancestor;
2. the post-acceptance change is this task file only;
3. PR #63 is Ready/Open/Mergeable/unmerged after the handoff CI succeeds;
4. Issue #62 remains Open;
5. version remains `0.2.0`;
6. PR #38 remains unchanged at `a57f71d2677b35c678bc8477c9ce783c90294c66`.

Do not modify implementation code or this task file. Do not merge PR #63, close Issue #62, create a release/tag, change version, begin v0.6B, or modify PR #38. Stop and await explicit owner merge authorization.
