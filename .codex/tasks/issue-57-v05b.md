# Issue #57 — v0.5B Evidence-Backed Industry Chain Map Foundation

## State

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#57`
- Branch: `feat/v05b-industry-chain-map`
- Draft PR: `[v0.5B] Add evidence-backed industry chain maps`
- Required ancestor: `5930f7b19573dccc490c869453601fbf9ef05975`
- Version remains `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #57, the merged v0.5A evidence-ledger implementation, migrations, docs, tests, and current CI before editing.

Keep the PR Draft/Open/unmerged and Issue #57 Open. Do not modify PR #38, create release/tag, change version, or begin v0.5C.

## Objective

Add one bounded, local, append-only and cutoff-aware Industry Alpha chain-map foundation that reuses v0.5A claims and evidence. The map records reviewed structure; it does not score industries, identify investable beneficiaries, recommend securities, or execute an LLM/provider.

## Required domain

Add stable identities and immutable revisions for:

1. Industry map identity attached to exactly one `research_case`.
2. Industry map revisions with revision number, title, scope, information cutoff, recorded UTC timestamp and supersedes pointer.
3. Node identities and revisions.
4. Directed relationship identities and revisions.
5. Versioned observations for `driver`, `bottleneck`, and `value_pool_shift`.
6. Map-revision membership rows freezing exact node, relationship and observation revisions.
7. Assertion-to-claim links referencing exact v0.5A `claim_revisions`.

Reviewed node kinds:

- `upstream_input`
- `equipment`
- `component`
- `manufacturing`
- `distribution`
- `service`
- `customer_end_market`
- `regulation_infrastructure`
- `other`

Reviewed relationship kinds:

- `supplies`
- `enables`
- `depends_on`
- `substitutes`
- `competes_with`
- `distributes_to`
- `regulates`
- `other`

Assertion status must be explicit: `draft`, `supported`, `disputed`, or `rejected`.

## Evidence boundary

- v0.5B must not create free-standing factual claims that bypass v0.5A.
- Every asserted node, relationship or observation revision must link to at least one exact visible v0.5A claim revision.
- `supported` requires at least one linked supported claim revision backed by A/B/C evidence and no visible contradiction at the assertion/map revision timestamp.
- D-only support is insufficient.
- `disputed` requires a linked disputed claim or visible contradiction.
- Missing evidence and conflicts remain explicit in reads.
- All linked cases, maps, claims, nodes, relationships and observations must share the same research case and map boundary.

## Append-only and chronology

- Corrections append revisions; no accepted row may be updated or deleted.
- Use exact timezone-aware UTC chronology.
- New identities cannot predate their parent case/map.
- Revisions cannot predate their identities or previous revisions.
- Assertion links cannot predate either endpoint.
- Map revision membership cannot freeze records, claim links or qualifying evidence created later than the map revision.
- All multi-row commands are transactional and fully rollback on validation, uniqueness, chronology or cross-boundary failure.
- Deterministic revision numbering must be concurrency-safe on PostgreSQL.

## Persistence

Add exactly one focused Alembic migration after `20260718_0005`. Reuse the existing SQLAlchemy Base, engine, session and migration conventions. Downgrade removes only v0.5B objects in safe dependency order.

Do not add a second ORM, database, cache, queue, scheduler, vector database or background worker.

## API and query

Provide read-only routes:

- `GET /industry-alpha/maps`
- `GET /industry-alpha/maps/{map_id}`

Support optional `as_of_cutoff=YYYY-MM-DD` with the same dual information-date and recorded-date visibility semantics as v0.5A.

Detail output must include:

- map identity and latest visible revision;
- revision history;
- frozen nodes, relationships and observations;
- exact linked claim revisions;
- evidence-grade summaries;
- explicit conflicts and missing-evidence summaries;
- deterministic ordering and strict JSON-safe values;
- read-only/non-advisory notices.

No POST, PUT, PATCH or DELETE HTTP routes. No browser editing UI.

## Demo

Add one deterministic offline fixture/demo containing:

- one map and at least two map revisions;
- multiple node kinds and directed relationships;
- at least one driver, bottleneck and value-pool-shift observation;
- supported A/B/C-backed assertions;
- one D-only lead that remains unsupported/contextual;
- one visible contradiction/disputed assertion;
- current and earlier cutoff views proving no later-information leakage.

## Tests

Cover at minimum:

- schema and migration base-to-head, `0005 -> head`, downgrade/upgrade and Alembic check;
- stable identities, revision numbering and supersedes chains;
- append-only update/delete rejection;
- strict node/relation/observation/status enums and text bounds;
- cross-case/map link rejection and full rollback;
- supported/D-only/disputed/conflict rules;
- exact claim revision and evidence visibility at assertion/map timestamp;
- chronology and historical cutoff non-leakage;
- concurrency-safe PostgreSQL revision numbering;
- deterministic ordering and strict JSON;
- read-only API and no mutation routes;
- no-network startup/import/test/demo behavior;
- all existing v0.2-v0.5A regressions and demos;
- compileall and `git diff --check`;
- final GitHub Actions tests and local fixture demo.

## Exclusions

Do not implement scoring, weights, rankings, investment attractiveness, sector constituent or company beneficiary mapping, Stage 2 stock research, valuation, watchlist, portfolio, recommendation, signal, LLM/provider execution, scraping, ingestion automation, broker, order or trading behavior. Do not change dependency, Docker/Compose, CI, launcher, version, release/tag or PR #38.

## Delivery

Update Draft PR and Issue #57 with final Head, exact files, schema, evidence rules, cutoff semantics, tests and CI. Keep PR Draft and Issue Open, then stop for ChatGPT review.