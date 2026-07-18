# Issue #47 — v0.4B Benchmark Index Persistence And Market Cockpit Context

## Task identity

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#47 [v0.4B] Benchmark index persistence and Market Cockpit context`
- Required product ancestor: v0.4A squash merge `24a41ed7af400ed39babb6b5d5b9ea0da97fe059`
- Branch to create: `feat/v04b-benchmark-index-context`
- Draft PR title: `[v0.4B] Add benchmark index context`
- Project version remains `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #47 and its latest authorization comment, merged PR #46, `docs/implementation_plan.md`, `docs/product_architecture.md`, `docs/akshare_ingestion.md`, `docs/market_cockpit.md`, the v0.3 persistence/series code, and the complete v0.4A Market Cockpit implementation before editing.

The exact branch start SHA is the task-sync commit recorded in the latest authorization comment on Issue #47. It must contain this file and have v0.4A merge commit `24a41ed7af400ed39babb6b5d5b9ea0da97fe059` as an ancestor. Stop and report if the ancestry or task file differs.

## Objective

Add a bounded, provider-attributed benchmark-index daily-data foundation and deterministic read-only benchmark context beside the existing selected-universe Market Cockpit.

This slice closes only the benchmark-index gap. It does not implement sector rotation, style, valuation, crowding, Industry Alpha, recommendations, portfolios, or trading.

## Required product semantics

1. Keep equity selected-universe monitoring and benchmark-index context as separate data domains and separate snapshot series.
2. Require explicit compatible selectors. Never guess a benchmark series by provider, code popularity, recency, or a hard-coded default.
3. Never stitch rows across ingestion runs or series.
4. Never describe provider-attributed data as an official exchange statement unless the reviewed source contract proves that wording.
5. Never imply full-market coverage from one or several benchmark codes.
6. Keep all outputs local-first, personal-use, read-only, research-only, auditable, and non-advisory.
7. Preserve every accepted v0.4A route, payload, calculation, provenance, cutoff, diagnostic, and no-network boundary.

## Implementation order

1. Pull current `main` and verify the exact authorized start SHA from Issue #47.
2. Create `feat/v04b-benchmark-index-context` from that exact SHA.
3. Inspect the current ingestion-run, series-identity, migration, repository, provider, CLI, Market Cockpit service/API/page, fixture, and test boundaries before designing changes.
4. Document the benchmark contract, endpoint mapping, series identity, formulas, cutoff/alignment rules, and missing-data behavior before implementing presentation.
5. Implement contracts and persistence first, then provider/CLI, repository/service/calculation, API/page, documentation, fixtures, and tests.
6. Open one Draft PR and stop for ChatGPT review.

## Normalized benchmark contract

Add a dedicated normalized benchmark-index daily contract and ORM table. Use a clear name such as `benchmark_index_daily`; do not reuse `daily_price` or `stock_code` semantics.

Required fields:

- `ingestion_run_id`;
- `source` or provider identity;
- `index_code`;
- `trade_date`;
- finite positive `close`.

Optional fields may include `open`, `high`, `low`, `volume`, and `amount` only when the selected endpoint semantics are explicitly documented and validated. Missing optional values remain `null`; do not manufacture zeroes. If OHLC values are present, enforce finite values, positive prices, and `low <= open/close <= high`. Activity values, when present, must be finite and nonnegative.

Natural uniqueness must include ingestion run, source, exact index code, and trade date. Add code/date lookup indexes suitable for one-run bounded reads. Link rows restrictively to immutable ingestion attempts.

Update ingestion-run relationships and dataset counts without weakening complete-snapshot, rollback, idempotency, or failed-attempt behavior.

## Migration

Add one explicit Alembic migration after `20260718_0002`.

The migration must:

- create only the benchmark-index persistence required by this issue;
- preserve all existing rows and constraints;
- provide deterministic upgrade and downgrade behavior;
- include portable constraints where supported and application validation for semantics that cannot be expressed portably;
- pass clean `base -> head`, downgrade/upgrade coverage, and `python -m alembic check`;
- avoid unrelated schema cleanup.

## Benchmark snapshot-series identity

Benchmark data uses its own canonical series identity and must never share the equity series key.

Canonical identity must include at least:

- series schema version;
- provider;
- benchmark contract version;
- exact dataset names;
- exact sorted index-code scope;
- requested start and end dates;
- daily frequency;
- complete snapshot mode;
- exact-scope semantics;
- exact selected endpoint name;
- adapter compatibility version;
- any additional parameter that changes normalized compatibility.

Timeout, retry count, network mode, installed patch version, and collection timestamp remain request metadata rather than compatibility identity unless they change normalized semantics.

Provider-only, code-only, or incomplete selectors fail closed. Snapshot reads select exactly one successful complete physical ingestion run using the established deterministic ordering and never merge histories across runs.

## Controlled AKShare ingestion

Extend the provider abstraction and manual CLI for an explicit bounded list of benchmark index codes.

Before implementing the live mapping, inspect the installed supported AKShare package range and select exactly one index-history endpoint for v0.4B. Record in documentation and tests:

- exact endpoint name;
- arguments and date/code semantics;
- returned column mapping;
- source attribution;
- frequency;
- activity-field units or their unsupported status;
- adapter compatibility version.

Do not implement silent endpoint fallback. A different endpoint must produce a different series identity and requires a future reviewed change.

Live behavior:

- requires explicit `--allow-network`;
- accepts at most 20 explicit index codes;
- has no all-index or default-index mode;
- uses finite child-process timeout and finite retries;
- cannot run during import, FastAPI startup, page access, tests, or CI;
- records one UTC collection timestamp;
- applies the established live-cutoff discipline unless the chosen endpoint has a separately documented historical point-in-time metadata guarantee;
- bounds requested price dates independently from the information cutoff;
- rejects unexpected codes, duplicate dates, out-of-range rows, invalid closes, and incompatible metadata transactionally.

Offline fixture and injected-frame paths must cover normalization and persistence without network access. Dry-run creates no engine, ingestion run, or database row.

Provider metadata exposed to users must use a fixed allowlist: collection/import/completion time, effective cutoff, installed package version, endpoint, frequency, exact code scope, network mode, timeout/retries, contract version, and adapter version. Reject or omit unknown sensitive or credential-like keys.

## Repository and selection

Add benchmark repository methods that require an explicit benchmark `series_key` or an equally complete canonical selector.

Requirements:

- one successful complete benchmark snapshot only;
- deterministic current and historical `as_of_cutoff` selection;
- no row after the selected information cutoff or permitted effective session;
- exact code scope and requested date range;
- no cross-series, cross-run, cross-provider, or endpoint substitution;
- actionable not-found/incompatible errors;
- lazy injectable session/engine construction;
- no fixture fallback disguised as persisted data.

## Benchmark calculation contract

For each exact benchmark code, calculate only close-based context supportable by persisted rows.

Required values:

1. Latest available close and its session.
2. Latest-session return `close(t) / close(t-1) - 1`, requiring two valid ordered benchmark sessions.
3. SMA20 and SMA60 position using the current close and the arithmetic mean of exactly the latest 20 or 60 valid ordered sessions, including the current session.
4. Twenty-return realized volatility requiring exactly 21 valid ordered closes, using sample standard deviation `ddof=1` and annualization `sqrt(252)`.
5. Twenty-return maximum drawdown from the compounded wealth path built from exactly 21 valid ordered closes, including initial wealth `1.0`.
6. Available and required session counts, plus bounded warnings.

Insufficient or broken windows return `null` plus explicit warnings. Do not shorten windows, forward-fill missing closes, infer closed-market values, substitute another code, or fabricate zeroes.

Do not add beta, correlation, alpha, excess return, relative-strength ranking, timing signals, regime recommendations, or buy/sell outputs.

## Market Cockpit integration

Preserve the existing required equity `series_key`. Add an optional explicit `benchmark_series_key`, for example:

`GET /market-cockpit/snapshot?series_key=<equity>&benchmark_series_key=<benchmark>&as_of_cutoff=YYYYMMDD`

Behavior:

- without `benchmark_series_key`, the accepted equity-only v0.4A response remains compatible and benchmark context stays visibly unsupported/unavailable;
- with a valid benchmark key, select one equity run and one benchmark run independently and expose their provenance separately;
- with an invalid or incompatible benchmark selector, return an actionable non-success response instead of silently omitting or replacing it;
- benchmark rows must be at or before both the requested cutoff and the permitted equity effective as-of session;
- expose benchmark information cutoff, selected run ID, exact code scope, effective benchmark session, endpoint, source, generated time, and alignment status;
- surface differing equity/benchmark cutoffs or sessions as explicit warnings rather than hiding them;
- do not calculate cross-domain relative performance in this issue.

Keep error behavior consistent and documented: validation errors use 422, missing eligible data uses 404, and unavailable database/configuration/query state uses 503. Do not convert data-quality problems into HTTP 200 with fabricated values.

## Read-only page

Add a bounded benchmark section to `/market-cockpit` using the existing semantic HTML, local CSS, and vanilla JavaScript pattern.

The page must:

- use DOM creation and `textContent`, never `innerHTML`, `eval`, or external assets;
- display exact benchmark codes, provider/source, endpoint, series/run, cutoff, effective session, formulas, counts, values, warnings, and limitations;
- distinguish equity scope from benchmark context;
- use neutral wording such as `provider-attributed benchmark index context` unless a reviewed contract proves an official-source claim;
- remain usable without a benchmark key and explain the unsupported state;
- contain no forms, trading controls, recommendations, automatic refresh, collection trigger, or write action.

## Compatibility

Do not regress:

- `/`, `/health`, `/dashboard`, `/dashboard/overview`, `/dashboard/report`;
- `/market-cockpit` static page behavior;
- equity-only `/market-cockpit/snapshot` requests and payload semantics;
- v0.4A point-in-time calculations, provenance allowlist, selected-universe labels, completeness states, or latest-return diagnostics;
- v0.3A/v0.3B ingestion, series identity, migration, rollback, and downgrade protections;
- import/startup/page/test/CI no-network behavior.

Any additive response field must be optional or have a backward-compatible default when no benchmark key is supplied.

## Required tests

Add deterministic SQLite and PostgreSQL coverage for at least:

1. migration upgrade, downgrade, and existing-row preservation;
2. benchmark contract normalization and optional-field null behavior;
3. natural-key uniqueness, duplicate rejection, invalid close/OHLC/activity rejection, and transaction rollback;
4. deterministic series identity and isolation across code scope, dates, endpoint, provider, contract, and adapter version;
5. provider-only and incomplete-selector fail-closed behavior;
6. explicit CLI authorization, maximum 20-code scope, dry-run, offline fixture, timeout/retry, and zero-network behavior;
7. current and historical benchmark snapshot selection;
8. one physical benchmark run only and no cross-run/series stitching;
9. benchmark and equity series separation;
10. cutoff and future-row traps;
11. exact latest return, SMA20/SMA60, volatility, and drawdown formulas;
12. insufficient history, missing session, invalid close, and mismatched-session warnings;
13. API 422/404/503 behavior and equity-only regression;
14. page provenance, neutral wording, DOM-safe rendering, limitations, and no controls;
15. all existing Dashboard, persistence, ingestion, and v0.4A tests.

## Required validation

Run and report exact results for:

1. `python -m pytest -q`
2. focused benchmark contract/persistence/provider/repository/calculation/API/page tests
3. PostgreSQL benchmark and Market Cockpit current/as-of tests
4. existing PostgreSQL persistence and migration tests
5. clean Alembic `base -> head`
6. reviewed downgrade/upgrade path for the new migration
7. `python -m alembic check`
8. `python -m scripts.demo_research_flow`
9. existing persisted equity Market Cockpit current/historical demo
10. one deterministic persisted benchmark current/historical-cutoff demo
11. `python -m compileall -q backend datasource market_cockpit scripts`
12. import/startup/page no-network regressions
13. `git diff --check`

Automated validation must remain offline.

## Documentation

Update only directly relevant documentation to define:

- benchmark versus equity domain and series separation;
- exact endpoint and normalized field mapping;
- compatibility identity and snapshot-selection rules;
- cutoff and session-alignment behavior;
- formulas and minimum windows;
- provenance allowlist and missing-data behavior;
- CLI, API, page, and fixture use;
- provider-attributed and non-official-by-default wording;
- explicit unsupported areas and non-advisory boundary.

## GitHub synchronization

After implementation and push:

1. Open Draft PR `[v0.4B] Add benchmark index context` against `main`.
2. Update its body with exact base/head SHA, endpoint choice and mapping, contract/migration design, series identity, calculations, API/page behavior, changed files, exact validation output, current/historical demos, and limitations.
3. Add an Issue #47 completion comment with the same concise record.
4. Keep the PR Draft.
5. Stop for ChatGPT review.

## Exclusions and stop conditions

Do not:

- merge the Draft PR;
- close Issue #47;
- create a release or tag;
- change project version `0.2.0`;
- add sector/industry classification or rotation;
- add size/value/growth style, valuation, market-cap breadth, or crowding;
- persist derived Market Cockpit snapshots;
- add schedulers, background collection, page-triggered collection, or automatic refresh;
- begin v0.5 Industry Alpha or any later product stage;
- add Stock Research, Watchlist, paper portfolios, LLM execution, authentication, deployment, brokers, orders, recommendations, or trading;
- modify, close, rebase, or merge unrelated PR #38.

Stop immediately and report rather than improvising if the endpoint schema is incompatible with the normalized contract, if accepted v0.4A behavior would require a breaking change, if migration safety cannot be demonstrated, or if any network action would be needed during automated validation.