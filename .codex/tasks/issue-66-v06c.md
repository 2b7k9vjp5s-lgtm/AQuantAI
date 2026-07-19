# Issue #66 — v0.6C Blocking Review Cycle

## State

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#66`
- Draft PR: `#67`
- Branch: `feat/v06c-catalyst-risk-assessments`
- Required base and ancestor: `571fa9396a9318f2e6c409e1d8b7a25ec2120b2f`
- Reviewed implementation Head: `7c78826016bbbaed19e5649da0d20f67acca4643`
- Blocking COMMENT review: `4730246609`
- Implementation CI: `29675419647` — success
- Version must remain `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #66, PR #67, review `4730246609`, and this task before editing. The Issue and review are authoritative.

## Review result

The v0.6C persistence, migration, command, chronology, cutoff, append-only, API-route and PostgreSQL concurrency foundations are retained. Do not redesign them.

One blocker remains: the read model drops the canonical frozen claim fact/inference provenance.

`ClaimRevision` already stores:

- `claim_kind` (`fact` or `inference`);
- `inference_confidence`;
- `inference_basis`;
- `recorded_at_utc`.

The catalyst/risk claim payload currently returns statement, status, cutoff and evidence but omits these fields. Consumers therefore cannot distinguish a frozen fact from a frozen inference or inspect its explicit basis/confidence.

## Authorized fix

Make the smallest focused change:

1. In the v0.6C query/read payload, expose the exact frozen claim revision fields:
   - `claim_kind`;
   - `inference_confidence`;
   - `inference_basis`;
   - `recorded_at_utc`.
2. Preserve `None` for fact-only inference fields; do not synthesize values.
3. Add focused query/API regressions proving:
   - a frozen fact is returned with `claim_kind == "fact"` and null inference fields;
   - a frozen inference is returned with its exact confidence and basis;
   - current and historical cutoff payloads preserve the same frozen provenance;
   - payloads remain deterministic and strict-JSON safe.
4. Update directly relevant documentation only if the response contract is documented there.

## Locked boundaries

Do not change:

- models, migrations, tables or persisted domain fields;
- create/append command semantics or evidence/status rules;
- routes or HTTP methods;
- fixture domain scope except the minimal test data needed to expose both a fact and inference;
- dependencies, CI, Docker, launchers, authentication or version metadata;
- v0.6D/v0.7 scope;
- PR #38.

Do not rebase or force-push reviewed history. Keep PR #67 Draft/Open/unmerged and Issue #66 Open.

## Validation

Run and record exact results for:

- focused SQLite v0.6C tests;
- focused PostgreSQL v0.6C tests when available;
- full offline suite;
- full PostgreSQL persistence/Industry Alpha suite when available;
- all offline demos;
- explicit no-network coverage;
- `python -m compileall -q backend industry_alpha scripts tests`;
- `git diff --check`.

No migration change is authorized; confirm `python -m alembic check` still reports no new upgrade operations.

## Delivery

Update PR #67 and Issue #66 with the new Head, exact changed files and exact validation counts. Keep the PR Draft and stop for ChatGPT re-review. Do not merge, close Issue #66, create a release/tag, change version, begin another slice, or modify PR #38.