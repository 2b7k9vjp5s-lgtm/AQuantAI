# Issue #55 — v0.5A Focused Review Revision

## State to verify

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#55 [v0.5A] Research case and evidence ledger foundation`
- Branch: `feat/v05a-evidence-ledger`
- Draft PR: `#56 [v0.5A] Add research evidence ledger`
- Required ancestor: `dcd632040dd91340dbed94a34a5f11a532cf1832`
- Original task-sync Head: `d406faef299c3114c141240abb4f33231d59d2d9`
- Reviewed implementation Head: `220d1c3802ab3eb2ee5861f613de237470dc822c`
- Implementation Actions: `29650132399` — success
- Blocking COMMENT review: `4728781576`
- Project version must remain `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #55, PR #56 body/comments/review, this task, and the current v0.5A implementation before editing.

Keep PR #56 Draft/Open/Unmerged and Issue #55 Open. Do not modify PR #38, create a release/tag, change version, or begin v0.5B.

## Accepted implementation to preserve

Preserve the existing bounded v0.5A architecture and behavior:

- eight append-only ledger tables and migration `20260718_0005`;
- stable case/claim identities and immutable revisions;
- A/B/C/D evidence, fact/inference validation, support/contradiction/context links;
- supported/disputed conclusion validation;
- completed revisions requiring `后续验证清单`;
- read-only Industry Alpha APIs and offline fixture demo;
- deterministic ordering, strict JSON, no HTTP mutation routes, no network/provider/LLM/scoring/trading behavior;
- all v0.2-v0.4 compatibility and existing migrations.

Do not redesign the schema or widen product scope.

## Blocker 1 — monotonic recorded-time invariants

The query determines historical visibility from `recorded_at_utc`, but command services currently permit later operations to be assigned timestamps earlier than their accepted parents, endpoints, or previous revisions. That can make a later correction or relationship appear in an earlier `as_of_cutoff` view.

Add one reviewed UTC chronology validator and apply it transactionally.

Required invariants:

1. A case revision must not be recorded before the case identity creation timestamp or before the immediately previous case revision.
2. A claim identity/revision must not be recorded before its case identity; an appended claim revision must not be recorded before the claim identity or immediately previous claim revision.
3. Evidence must not be recorded before its case identity. Superseding evidence must not be recorded before the evidence it supersedes.
4. A claim revision created with evidence links must not be recorded before any linked evidence item.
5. A standalone claim/evidence link must not be recorded before either endpoint and must not use information unavailable to the immutable claim revision cutoff.
6. A case-revision claim membership must not freeze a claim revision or its required qualifying evidence/links that were recorded after the case revision.
7. A verification item must not be recorded before its case revision or before the latest existing verification item for that case revision.
8. Comparisons must be timezone-aware UTC. Use exact timestamps for append chronology; cutoff reads may continue to use UTC calendar dates as specified.
9. Validation failure must roll back every row in the command. Never silently clamp or rewrite caller timestamps.

Add focused tests proving:

- a later case revision cannot be backdated before case creation or the previous revision;
- a later claim revision cannot be backdated before claim creation or the previous revision;
- evidence cannot predate its case, and superseding evidence cannot predate the superseded item;
- a supported/disputed claim revision cannot use evidence recorded after the revision;
- standalone links cannot be backdated before either endpoint;
- a supported/disputed case conclusion cannot freeze qualifying evidence or links recorded after the case revision;
- verification items cannot predate their case revision or move backward relative to prior checklist items;
- every rejected chronology command leaves counts and histories unchanged;
- an earlier cutoff never exposes a later operation, correction, conflict, membership, or checklist item.

Keep deterministic fixtures valid by using explicit chronological timestamps.

## Blocker 2 — safe API configuration errors

`get_industry_alpha_session_factory()` currently includes `str(exc)` in a public 503 response. Replace it with a stable generic message that cannot echo a database URL, password, local path, driver detail, or stack information.

Add an API test that injects a configuration/engine exception containing a sentinel secret and proves the 503 response does not include the sentinel while remaining useful and deterministic.

Do not change successful route behavior or existing generic query-failure handling.

## Blocker 3 — strict text command boundaries

`required_text()` and `optional_text()` currently call `str(value)`, which accepts integers, objects, or `None` as text such as `"123"` or `"None"`.

Change command-boundary validation so:

- required text accepts only `str`, trims it, rejects blank values, and enforces the reviewed maximum length;
- optional text accepts only `str | None`, trims strings, normalizes blank strings to `None`, and enforces length;
- non-string values raise `EvidenceLedgerValidationError` and do not create partial rows;
- existing valid strings and fixture behavior remain unchanged.

Add parameterized tests across representative required and optional fields, including rollback assertions.

## Scope limits

Authorized implementation files are the existing v0.5A domain/API/tests/docs as needed for these fixes. Do not add tables or a second migration unless a demonstrated database constraint change is strictly required; prefer command/service validation because this revision addresses application chronology and boundary safety.

Do not add:

- provider/network/scraping/LLM execution;
- scoring, chain maps, beneficiary screening, recommendations, signals, watchlists, portfolios, brokers, orders, or trading;
- browser mutation UI or POST/PUT/PATCH/DELETE routes;
- dependencies, Docker/Compose, CI, launcher, release/tag, or version changes;
- v0.5B or PR #38 changes.

## Validation

Run and record at minimum:

- focused v0.5A domain/API tests including all new chronology, secret-redaction, strict-text, and rollback cases;
- PostgreSQL concurrency, append-only, migration, and chronology tests;
- clean Alembic `base -> head`;
- `20260718_0004 -> head` and `20260718_0005 -> downgrade/upgrade` checks as applicable;
- `python -m alembic check`;
- full offline test suite;
- PostgreSQL-enabled full suite;
- `python -m scripts.demo_evidence_ledger` and all existing demos;
- no-network validation;
- `python -m compileall -q backend datasource market_cockpit industry_alpha scripts`;
- `git diff --check`;
- final GitHub Actions with tests and local fixture demo successful.

## Delivery

After implementation:

1. Update PR #56 body with final revision Head, exact files, chronology rules, safety changes, tests, and CI.
2. Add concise PR #56 and Issue #55 comments with the same final facts.
3. Keep PR #56 Draft/Open/Unmerged and Issue #55 Open.
4. Stop for ChatGPT re-review.

Do not mark Ready, merge, close Issue #55, create release/tag, change version, begin later work, or modify PR #38.