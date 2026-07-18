# Issue #49 — v0.4C Sector Market Data Foundation And Descriptive Rotation Context

## Task identity

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Required product ancestor: v0.4B squash merge `50147ecd7b796167d52a04e2ecc774010b8956b8`
- Branch: `feat/v04c-sector-market-context`
- Draft PR title: `[v0.4C] Add sector market context`
- Project version remains `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #49 and its latest authorization comment, merged PR #48, `docs/implementation_plan.md`, `docs/product_architecture.md`, `docs/akshare_ingestion.md`, `docs/market_cockpit.md`, `docs/benchmark_context.md`, the v0.3 persistence/series implementation, and the complete v0.4A/v0.4B Market Cockpit implementation before editing.

The exact authorized branch start must contain this task file and have merge commit `50147ecd7b796167d52a04e2ecc774010b8956b8` as an ancestor. Stop and report if ancestry, issue identity, branch, or task content differs.

## Objective

Add a bounded, provider-attributed selected-sector market-data foundation and deterministic read-only descriptive sector-rotation context to Market Cockpit.

This slice is an upstream market-observation layer only. It must not create Industry Alpha research cases, causal claims, beneficiary companies, investment conclusions, recommendations, or trading behavior.

## Required product semantics

1. Keep equity selected-universe, benchmark-index, and sector-market data as three separate domains and separate canonical series.
2. Require explicit complete selectors. Never guess sector scope by popularity, provider, latest run, display name, or a hidden default.
3. Never stitch rows, taxonomy, or histories across ingestion runs or series.
4. Use stable provider sector identifiers. A display name alone is not a canonical identity. If the installed provider contract cannot supply a stable identifier, stop and report rather than inventing one.
5. Treat sector outputs as descriptive selected-scope market context, not official exchange statements, full-market coverage, signals, scores, or advice.
6. Use the selected equity snapshot's persisted point-in-time open-session calendar as the only expected-session reference for sector calculations.
7. Preserve all accepted v0.4A and v0.4B routes, payloads, calculations, provenance, alignment, page behavior, and no-network boundaries.
8. Keep all behavior local-first, personal-use, read-only, auditable, research-only, and non-advisory.

## Implementation order

1. Pull current remote state and verify the exact authorized branch start.
2. Inspect current ingestion-run, canonical-series, migration, provider, CLI, repository, Market Cockpit contract/service/API/page, fixture, and test patterns.
3. Inspect the installed supported AKShare package range before selecting provider endpoints.
4. Document the provider taxonomy/history contract, canonical identity, formulas, cutoff/session rules, missing-data behavior, and presentation wording before implementing UI.
5. Implement contracts and persistence first, then provider/CLI, repository/calculation/service, API/page, documentation, fixtures, and tests.
6. Update the existing Draft PR only; keep it Draft and stop for ChatGPT review.

## Provider endpoint contract

Select the smallest reviewed AKShare endpoint set capable of providing both:

- a stable provider sector identifier with a human-readable display name and classification metadata; and
- historical daily sector-market observations for exact explicitly requested identifiers.

At most one taxonomy/list endpoint and one history endpoint are authorized. Record and test:

- exact endpoint names;
- installed-package compatibility range;
- arguments and identifier semantics;
- classification system and level, when the provider exposes them;
- returned column mapping;
- source attribution;
- frequency;
- price and activity-field units;
- contract and adapter compatibility versions.

Do not implement silent endpoint fallback. Changing either endpoint, identifier semantics, classification system, or normalized mapping must change canonical series identity and requires future review.

If no reviewed endpoint combination provides stable identifiers and bounded historical reads, stop and report instead of implementing a name-only or scraped heuristic identity.

## Normalized sector contracts and persistence

Add dedicated normalized sector-domain contracts and ORM persistence. Do not reuse benchmark-index, equity `daily_price`, or stock-code semantics.

### Sector definition snapshot

Persist the exact selected scope as immutable rows linked to one ingestion attempt. Required normalized fields:

- `ingestion_run_id`;
- provider/source identity;
- stable `sector_code` or equivalent provider identifier;
- `sector_name`;
- classification system/provider taxonomy name;
- classification level when explicitly supplied, otherwise `null`;
- parent identifier/name only when explicitly supplied, otherwise `null`.

Natural uniqueness must include ingestion run, source, classification identity, and stable sector identifier. Reject duplicate identifiers, blank names, conflicting duplicate metadata, unexpected sectors, and unstable name-only identities transactionally.

### Sector daily observations

Required fields:

- `ingestion_run_id`;
- provider/source identity;
- stable sector identifier;
- `trade_date`;
- finite positive `close`.

Optional fields may include `open`, `high`, `low`, `volume`, `amount`, and `turnover_rate` only when the reviewed endpoint semantics and units are documented. Missing optional values remain `null`; never manufacture zeroes. Validate finite values, positive prices, `low <= open/close <= high`, and nonnegative activity fields when present.

Natural uniqueness must include ingestion run, source, stable sector identifier, and trade date. Add bounded identifier/date lookup indexes suitable for exact one-run reads. Link rows restrictively to immutable ingestion attempts.

Update ingestion-run relationships and dataset counts without weakening complete-snapshot, rollback, failed-attempt, or idempotency behavior.

## Migration

Add one explicit Alembic migration after `20260718_0003`, expected revision `20260718_0004` unless repository conventions require another deterministic identifier.

The migration must:

- create only the sector definition and sector daily persistence required here;
- preserve all existing rows and constraints;
- have deterministic upgrade and downgrade behavior;
- use portable constraints where supported and application validation for semantics not portable across SQLite/PostgreSQL;
- pass clean `base -> head`, `0004 -> 0003 -> 0004`, and `python -m alembic check`;
- avoid unrelated schema cleanup.

## Canonical sector series identity

Sector data uses its own canonical identity and never shares equity or benchmark series keys.

Identity must include at least:

- series schema version;
- provider;
- sector definition and daily contract versions;
- exact taxonomy/list endpoint and history endpoint;
- classification system and requested level;
- exact sorted stable sector-code scope;
- requested start/end dates;
- daily frequency;
- complete snapshot mode;
- exact-scope semantics;
- adapter compatibility version;
- any parameter that changes normalized compatibility.

Display names, timeout, retry count, network mode, installed patch version, and collection timestamp remain request metadata unless they change normalized semantics.

Provider-only, display-name-only, partial-scope, or incomplete selectors fail closed. Snapshot reads must choose exactly one successful complete physical run using established deterministic ordering and must never merge taxonomy or history across runs.

## Controlled manual ingestion

Extend the provider abstraction and manual CLI for an explicit bounded list of sector identifiers.

Requirements:

- explicit `--allow-network` for live calls;
- at most 30 exact sector identifiers;
- no all-sector, latest-popular, search-by-name, or default-sector mode;
- finite child-process timeout and finite retries;
- no network during import, FastAPI startup, page access, tests, fixture demos, or CI;
- one UTC collection timestamp per attempt;
- established live information-cutoff discipline unless the reviewed endpoint has a separately documented point-in-time guarantee;
- independent requested history bounds and information cutoff;
- transactional rejection of unexpected identifiers, duplicate dates, conflicting taxonomy, invalid values, out-of-range rows, and incompatible metadata;
- fixed provider-metadata allowlist with no credentials, request headers, local paths, or arbitrary response payloads.

Offline fixture and injected-frame paths must cover taxonomy resolution, normalization, persistence, idempotency, and rollback without network access. Dry-run must create no engine, ingestion attempt, definition row, or daily row.

## Repository and selection

Add repository methods requiring an explicit complete `sector_series_key` or an equally complete canonical selector.

Requirements:

- one successful complete sector snapshot only;
- deterministic current and historical `as_of_cutoff` selection;
- exact stable-code scope and requested date range;
- no row after selected information cutoff or permitted effective session;
- no cross-series, cross-run, cross-provider, cross-taxonomy, cross-level, or endpoint substitution;
- actionable not-found/incompatible errors;
- lazy injectable session/engine construction;
- no fixture fallback disguised as persisted data.

## Exact session and per-sector calculation contract

Pass the selected equity snapshot's clipped, ordered persisted open-session sequence explicitly into sector calculations. Do not derive expected sessions from weekdays, sector row order, benchmark rows, live calendars, or another ingestion run.

For each exact requested sector calculate only when the full exact expected window is present once:

1. Latest eligible close and session.
2. Latest-session return: `close(t) / close(t-1) - 1`, requiring the latest two adjacent expected sessions.
3. Five-session return: `close(t) / close(t-5) - 1`, requiring exactly six consecutive expected closes.
4. Twenty-session return: `close(t) / close(t-20) - 1`, requiring exactly twenty-one consecutive expected closes.
5. SMA20 position: current close and arithmetic mean of exactly the latest twenty expected closes; expose the ratio or percentage distance using one documented formula.
6. Twenty-return realized volatility from exactly twenty-one expected closes using sample standard deviation `ddof=1` and annualization `sqrt(252)`.
7. Twenty-return maximum drawdown from the compounded wealth path built from exactly twenty-one expected closes, including initial wealth `1.0`.

A broken, duplicated, invalid, or insufficient window returns `null` for the affected metric plus bounded deterministic diagnostics. Do not shorten windows, forward-fill, substitute older rows, interpolate, infer closed-market values, or fabricate zeroes.

For every metric window expose auditable diagnostics at least equivalent to:

- required and present session counts;
- expected start/end sessions;
- bounded missing and invalid sessions;
- stable unavailability reason.

## Descriptive cross-sectional context

Build only transparent descriptive summaries across the exact selected sector scope:

- requested, available, and equity-session-aligned sector counts;
- sorted missing sector identifiers;
- positive latest-session-return count/share among sectors with valid latest-session returns;
- above-SMA20 count/share among sectors with valid SMA20 values;
- deterministic top and bottom lists by latest-session return;
- deterministic top and bottom lists by twenty-session return;
- each list contains at most five sectors, or fewer when fewer valid sectors exist;
- sort by metric, then stable sector identifier as the deterministic tie-breaker;
- expose denominator counts and exclude null metrics rather than treating them as zero.

These are descriptive selected-scope observations only. Do not add composite scores, weighted regimes, sector recommendations, momentum signals, alpha labels, buy/sell outputs, confidence claims, or automatic conclusions.

## Coverage, cutoff, and alignment

Expose enough bounded fields to audit sector context:

- exact requested sector identifiers and names;
- requested/available/aligned counts;
- sorted missing identifiers;
- per-sector latest eligible sessions;
- equity information cutoff and effective session;
- sector information cutoff and effective eligible session;
- independent coverage, session-alignment, cutoff-alignment, and overall status;
- generated time, selected run ID, provider, endpoints, taxonomy, classification level, series key, and warnings.

Rules:

- `aligned` requires every exact requested sector to have an eligible latest row at the equity effective session and the documented cutoff condition to hold;
- missing sectors or mixed per-sector latest sessions are `partial`;
- all available sectors sharing one earlier session is `different_session`;
- differing information cutoffs cannot remain misleadingly `aligned`;
- if no requested sector has an eligible row, effective sector session is `null`, available/aligned counts are zero, every identifier is missing, and status is `partial`;
- physical maximum persisted dates remain internal and must never be substituted for an eligible effective session.

## Market Cockpit API integration

Preserve the required equity `series_key` and optional `benchmark_series_key`. Add an optional explicit `sector_series_key`, for example:

`GET /market-cockpit/snapshot?series_key=<equity>&benchmark_series_key=<benchmark>&sector_series_key=<sector>&as_of_cutoff=YYYYMMDD`

Behavior:

- without `sector_series_key`, all accepted v0.4A/v0.4B responses remain compatible and sector context is omitted or represented through a backward-compatible unavailable state;
- with a valid sector key, select equity, benchmark when requested, and sector runs independently;
- invalid or incompatible selectors return actionable non-success responses rather than silent omission or replacement;
- sector rows are bounded by the requested cutoff and permitted equity effective session;
- sector provenance is separate from equity and benchmark provenance;
- no API request may collect or mutate data.

Keep documented error behavior: validation errors use 422, missing eligible data uses 404, and unavailable database/configuration/query state uses 503. Do not turn data-quality failures into HTTP 200 with fabricated values.

## Read-only page

Add a bounded sector market context section to `/market-cockpit` using existing semantic HTML, local CSS, and vanilla JavaScript patterns.

The page must:

- use DOM creation and `textContent`, never `innerHTML`, `eval`, inline remote scripts, or external assets;
- distinguish selected-universe equity, benchmark context, and selected-sector context;
- display exact sector identifiers/names, provider, endpoints, taxonomy, series/run, cutoff, effective session, formulas, counts, values, diagnostics, warnings, and limitations;
- show a compact sector metric table and deterministic top/bottom descriptive lists;
- render nulls as `Unavailable` and never display excluded dates as effective sessions;
- clearly state selected-scope, provider-attributed, non-official, descriptive, non-advisory limitations;
- remain usable without a sector key;
- contain no collection trigger, search/discovery control, write action, automatic refresh, recommendation, score, trading control, or external link requirement.

## Documentation

Add or update documentation covering:

- exact provider endpoint contracts and compatibility versions;
- stable sector identifiers and taxonomy semantics;
- persistence and canonical series identity;
- exact formulas and expected-session requirements;
- cross-sectional denominators, null handling, deterministic ordering, and limitations;
- cutoff/alignment states and all-ineligible behavior;
- controlled manual collection and no-network boundaries;
- separation from Industry Alpha facts, evidence, company beneficiaries, and recommendations.

Update `docs/implementation_plan.md` and `docs/product_architecture.md` only to record the accepted v0.4C scope/status wording needed for this implementation. Do not rewrite future roadmap stages.

## Compatibility requirements

Do not regress:

- `/`, `/health`, `/dashboard`, `/dashboard/overview`, `/dashboard/report`;
- `/market-cockpit` page behavior;
- equity-only and equity-plus-benchmark `/market-cockpit/snapshot` requests;
- v0.4A equity calculations, completeness, provenance, cutoff, and diagnostics;
- v0.4B benchmark calculations, exact-window diagnostics, alignment, nullable effective session, and provenance;
- v0.3 ingestion, canonical series, migration, rollback, and downgrade protections;
- import/startup/page/test/CI no-network behavior.

Any additive response field must be optional or have a backward-compatible default when no sector key is supplied.

## Required tests

Add deterministic SQLite and PostgreSQL coverage for at least:

1. migration upgrade, downgrade, existing-row preservation, and `alembic check`;
2. sector-definition normalization, stable identifiers, optional metadata nulls, and conflicting duplicate rejection;
3. sector-daily normalization, natural-key uniqueness, invalid OHLC/activity rejection, and transaction rollback;
4. canonical identity isolation across provider, taxonomy/history endpoint, classification, level, exact code scope, dates, contract, and adapter version;
5. provider-only, display-name-only, partial, and incomplete selector fail-closed behavior;
6. explicit network authorization, maximum 30-code scope, timeout/retry, dry-run, offline fixture, idempotency, rollback, and zero-network behavior;
7. deterministic current and historical snapshot selection from one physical run with no stitching;
8. exact equity-calendar clipping and future-row traps;
9. exact latest, 5-session, 20-session, SMA20, volatility, and drawdown formulas;
10. missing previous session, middle-window gaps, shared gaps across all sectors, duplicate sessions, invalid closes, and insufficient-history null behavior;
11. deterministic cross-sectional denominators, null exclusion, top/bottom list limits, and tie-breaking;
12. missing sector, mixed sessions, all sectors on an earlier session, differing cutoffs, same-session/different-cutoff, and all-ineligible alignment behavior;
13. API 422/404/503 behavior and equity-only/equity-plus-benchmark regressions;
14. page provenance, neutral wording, safe DOM rendering, `Unavailable` null rendering, limitations, and absence of controls;
15. all existing Dashboard, persistence, ingestion, v0.4A, and v0.4B tests.

## Required validation

Run and report exact results for:

1. `python -m pytest -q`
2. focused sector contracts/persistence/provider/repository tests;
3. focused sector calculations/alignment/API/page tests;
4. PostgreSQL migration and persistence tests;
5. clean Alembic `base -> head`;
6. `20260718_0004 -> 20260718_0003 -> 20260718_0004`;
7. `python -m alembic check`;
8. `python -m scripts.demo_research_flow`;
9. persisted equity current/historical demo regression;
10. benchmark current/historical demo regression;
11. new sector current/historical offline fixture demo;
12. sector offline dry-run proving no database writes;
13. repeated identical offline persistence proving idempotency;
14. no-network import/startup/page/test checks;
15. `python -m compileall -q backend datasource market_cockpit scripts`;
16. `git diff --check`.

All tests, demos, and CI must remain offline. Do not perform live AKShare requests during implementation validation.

## GitHub synchronization

During implementation:

1. Work only on `feat/v04c-sector-market-context`.
2. Keep the PR Draft.
3. Update the PR body with exact files, formulas, endpoint contracts, migration, compatibility notes, exclusions, and validation results.
4. Update Issue #49 with implementation Head, CI run, validation summary, and unresolved limitations.
5. Stop for ChatGPT review. Do not mark Ready or merge.

## Explicit exclusions

Do not implement or modify:

- sector constituents, company membership, beneficiary mapping, supply-chain maps, or stock screening;
- Industry Alpha Stage 1 evidence, claims, conflicts, causal drivers, research cases, or conclusions;
- company fundamentals, valuation, Stock Research, catalysts, or risks;
- style factors, market valuation, crowding, composite regimes, scoring, recommendations, or timing signals;
- cross-domain benchmark-relative alpha, beta, correlation, or excess-return claims;
- automatic collection, scheduling, background refresh, notifications, or third-party messaging;
- LLM execution, embeddings, vector databases, RAG, or vendor-specific AI workflow state;
- watchlists, portfolios, simulated trades, broker integration, orders, or real trading;
- authentication, multi-user SaaS, subscriptions, or payments;
- unrelated refactors, dependency upgrades, release, tag, or project-version changes;
- PR #38.

Do not merge the Draft PR or close Issue #49. Do not begin v0.5.