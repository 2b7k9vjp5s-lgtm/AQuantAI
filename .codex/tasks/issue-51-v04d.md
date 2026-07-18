# Issue #51 — v0.4D Bounded Correctness Revision

## Task identity

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#51 [v0.4D] Liquidity distribution and trading concentration context`
- Pull request: `#52 [v0.4D] Add liquidity distribution context`
- Branch: `feat/v04d-liquidity-context`
- Required ancestor: v0.4C squash merge `98aed74f069a2e9751e2ed8e8dc529b0fe5bc435`
- Original task sync: `4652486b931f8c56fdc90752ed0ff219f0bc4898`
- Reviewed implementation Head: `c4e34e2088542186fb07f7030381e3fa8bad171f`
- Reviewed implementation Actions: `29645973558` — success
- Blocking COMMENT review: `4728584741`
- Project version remains `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #51, this task, PR #52, review `4728584741`, the current PR body, and the reviewed liquidity implementation before editing.

Keep PR #52 Draft. Do not merge, close Issue #51, release, tag, change version, begin v0.5, or modify PR #38.

## Accepted implementation

Preserve the reviewed architecture and product scope:

- additive `liquidity_context` on the existing Market Cockpit snapshot;
- the same physical `PersistedMarketDataSnapshot`, accepted effective session, filtered lookup, and persisted open-session sequence;
- finite positive observation eligibility;
- latest total/median distribution;
- amount-descending and stock-code-ascending deterministic ordering;
- top-5 and top-decile concentration formulas;
- exact fixed matched-cohort 5/20-prior-session activity windows;
- strict latest-above-prior-20-median participation;
- additive API/page integration and v0.4A/v0.4B/v0.4C compatibility;
- no provider, ingestion, selector, series, calendar, persistence, migration, dependency, Docker/CI, launcher, version, v0.5, LLM, portfolio, broker, order, or trading capability.

The revision is limited to the two blockers below and their tests/documentation.

## Blocker 1 — fail closed on non-finite aggregate arithmetic

Individual finite positive amounts do not guarantee that a floating-point aggregate is finite. Ordinary summation can overflow when multiple individually finite values are combined. The reviewed implementation can therefore expose:

- non-finite `latest_total_amount`;
- non-finite top-5 or top-decile numerators;
- `NaN` concentration from `Infinity / Infinity`;
- non-finite matched-cohort per-session totals;
- non-finite `latest_matched_total_amount` or activity ratios.

### Required behavior

1. Introduce one deterministic aggregate helper used for:
   - latest eligible total;
   - top-5 numerator;
   - top-decile numerator;
   - every matched-cohort session total.
2. The helper must reject arithmetic overflow and every non-finite aggregate result even when all inputs are individually finite.
3. Do not emit `NaN`, positive/negative `Infinity`, a fabricated zero, or a partially computed ratio.
4. Latest distribution behavior when its total is invalid:
   - `latest_total_amount = null`;
   - both concentration shares are `null`;
   - preserve exact eligible/unavailable observation counts;
   - use an explicit typed diagnostic/reason and make overall liquidity status non-complete.
5. Window behavior when any required matched-cohort session aggregate is invalid:
   - `latest_matched_total_amount = null`;
   - `baseline_total_amount = null`;
   - `activity_ratio = null`;
   - status is `unavailable`;
   - use an explicit stable reason such as `non_finite_aggregate` or an equivalently precise reviewed name.
6. Concentration shares require both a finite positive denominator and a finite numerator. They must be null otherwise.
7. Keep valid ordinary-value formulas and denominators unchanged.
8. The parent snapshot and API `to_dict()` output must remain strict JSON-safe.

### Required tests

Add deterministic regressions using multiple individually finite values near the floating-point limit so that aggregation overflows:

- latest total overflow;
- top-5/top-decile numerator/denominator safety;
- 5-session matched-cohort aggregate overflow;
- 20-session matched-cohort aggregate overflow;
- strict `json.dumps(payload, allow_nan=False)`;
- FastAPI snapshot serialization without `NaN` or `Infinity`;
- read-only page unavailable rendering for the null aggregate outputs.

Do not weaken individual amount validation or replace fail-closed behavior with arbitrary clipping.

## Blocker 2 — bound identifier diagnostics and warnings

The task requires bounded, stable diagnostics with exact counts. Source-exclusion identifiers are already bounded, but the reviewed implementation exposes unbounded selected-stock lists.

### Required behavior

1. Define one reviewed constant for displayed diagnostic/member identifier samples, following the existing bounded benchmark/sector style. A value such as 10 or 20 is acceptable when documented and tested.
2. Apply deterministic stock-code-ascending truncation to:
   - `diagnostics.latest_issues` or its exposed identifier sample;
   - `activity_5.unavailable_stock_codes`;
   - `activity_20.unavailable_stock_codes`;
   - any retained public top-decile membership code list that can grow with universe size.
3. Preserve exact counts independently from bounded samples:
   - latest unavailable count remains exact;
   - each activity window must expose an exact unavailable-stock count;
   - top-decile member count remains exact;
   - source-exclusion row counts remain exact.
4. Add explicit truncation flags for every bounded list.
5. Keep all bounded samples sorted deterministically.
6. Bound warnings. Do not interpolate the complete unavailable universe. Include exact count and an omitted-count suffix such as `(+N more)`.
7. Top-5 membership is naturally bounded at five and may remain complete.
8. The page must render the exact count, bounded sample, and truncation state without unsafe HTML.
9. Do not change metric cohorts, concentration denominators, matched-cohort membership, or formulas merely because displayed identifiers are truncated.

### Required tests

Add a selected universe larger than the diagnostic cap and prove:

- exact latest/window/top-decile counts;
- sorted stable bounded samples;
- correct truncation flags and omitted counts;
- bounded warning length/content;
- repeated calculations are identical;
- API JSON and page output are safe;
- concentration and activity calculations still use the complete eligible/matched cohort rather than the displayed sample.

## Files and scope

Expected revision files are limited to the narrow implementation surface, for example:

- `.codex/tasks/issue-51-v04d.md` for this synchronized task only;
- `market_cockpit/liquidity_contracts.py`;
- `market_cockpit/liquidity_calculator.py`;
- `market_cockpit/static/market_cockpit.js` if new truncation/aggregate diagnostics require rendering;
- `tests/test_liquidity_context.py`;
- focused API/page tests;
- `docs/market_cockpit.md` and narrow demo documentation if public semantics change.

Do not change datasource adapters, persistence models, migrations, provider code, dependencies, Docker/Compose, CI configuration, launcher behavior, version files, unrelated research modules, or PR #38.

## Validation

Run and report exact results for:

1. strict overflow/non-finite aggregate regressions;
2. large-universe bounded-diagnostic regressions;
3. focused liquidity contracts/calculator tests;
4. focused Market Cockpit service/API/page tests;
5. v0.4A breadth/risk regression tests;
6. v0.4B benchmark regression tests;
7. v0.4C sector regression tests;
8. no-network import/startup/page tests;
9. PostgreSQL persistence/migration regressions proving no schema change;
10. `python -m alembic check`;
11. all existing current/historical fixture demos;
12. `python -m compileall -q backend datasource market_cockpit scripts`;
13. `git diff --check`;
14. the complete offline test suite;
15. GitHub Actions for the final revision Head.

All validation must remain offline. Record exact pass/skip/warning counts and any environment limitations.

## GitHub handoff

After implementing the bounded revision:

1. Update the Draft PR #52 body with the new Head, exact files, aggregate fail-closed semantics, list cap, exact count/truncation fields, and validation results.
2. Add concise PR #52 and Issue #51 comments referencing blocking review `4728584741` and proving both blockers are closed.
3. Keep PR #52 Draft, open, and unmerged.
4. Stop for ChatGPT re-review.

Do not mark Ready, merge, close Issue #51, create a release/tag, change project version `0.2.0`, begin v0.5, or modify PR #38.
