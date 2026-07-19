# Issue #86 - Stage 2 Query Value Helpers Characterization

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#86`
- Work type: architecture characterization only
- Base and required ancestor: `cacf46ac9ccb37d0480e1fd3f02ea5f10da7cb70`
- Branch: `docs/stage2-query-values-characterization`
- Released version remains `0.2.0`; merged capability stage remains v0.6D.

## Objective

Characterize repeated pure cutoff, UTC, date and UUID value mechanics in the v0.6A-v0.6D Stage 2 query modules. Distinguish safe shared mechanics from evidence serialization, link selection, payload ordering and domain notices.

## Authorized files

- `.codex/tasks/issue-86-stage2-query-values-characterization.md`
- `docs/stage2_query_values_characterization.md`

## Required analysis

- Compare `stage2_query.py`, `stage2_expectations_query.py`, `stage2_assessments_query.py` and `stage2_judgments_query.py`.
- Record exact UTC-null/error differences.
- Define the smallest behavior-preserving first implementation candidate.
- Preserve all public payloads, sorting, evidence text and domain ownership.
- Make an explicit no-migration decision.

## Locked exclusions

No application implementation, tests, fixtures, APIs, contracts, repositories, commands, models, schemas, migrations, providers, dependencies, CI, UI, release metadata, evidence serializer unification, v0.6E, v0.7 or PR #38 work.

## Stop gate

Open a Draft PR and keep it Open/Draft/unmerged until separate characterization review. Characterization does not authorize implementation.