# Issue #185 — Normalized Valuation and Expectation Metrics v1 Implementation

## Authority

- GitHub Issue: #185
- Product Roadmap: #137, Slice 5
- Merged Architecture Issue: #183
- Merged Architecture PR: #184
- Architecture fixed head: `adc6e71e4d9893642204171988c8dfadab9bd375`
- Required implementation base: `c7627a76cd7e571c7eee6485d18550113e40d4cf`
- Risk tier: **Strict**
- Owner authorization: `审核通过，确认合并并进入下一步开发` on 2026-07-22

## Objective

Implement the merged append-only contract for structured financial observations, normalized valuation arithmetic, frozen historical/peer comparison context and structured numeric expectation gaps.

The feature remains research-only and non-advisory. It must not create target prices, fair value, expected returns, buy/sell/hold outputs, portfolio actions or trading controls.

## Rule versions

- `aquantai.structured-financial-observation.v1`
- `aquantai.normalized-valuation.v1`
- `aquantai.normalized-comparison-context.v1`
- `aquantai.normalized-expectation-gap.v1`

## Delivery sequence

1. Deterministic pure-rule layer and focused tests.
2. Exactly thirteen append-only tables in migration `20260722_0015`.
3. ORM models, append-only guards and expected-latest concurrency behavior.
4. Local JSON-only commands and atomic services.
5. Exact-ID read repositories/APIs.
6. Chinese-first `/company-research/valuation-context` surface.
7. PostgreSQL/SQLite migration, concurrency, query-count and offline golden-path validation.
8. Final inventory, architecture-baseline synchronization and fixed-head review.

## Exact schema inventory

1. `structured_financial_observations`
2. `structured_financial_observation_revisions`
3. `structured_financial_observation_claim_links`
4. `structured_financial_observation_evidence_links`
5. `normalized_valuation_metrics`
6. `normalized_valuation_metric_revisions`
7. `normalized_valuation_metric_input_links`
8. `valuation_comparison_sets`
9. `valuation_comparison_set_revisions`
10. `valuation_comparison_members`
11. `normalized_expectation_gaps`
12. `normalized_expectation_gap_revisions`
13. `investment_candidate_normalized_metric_links`

No existing table may be altered or backfilled. Populated downgrade must refuse before any drop.

## Deterministic arithmetic

```text
equity_value = price * diluted_shares_outstanding
enterprise_value = equity_value + net_debt
pe = equity_value / net_profit_attributable
ps = equity_value / revenue
ev_ebitda = enterprise_value / ebitda
fcf_yield_pct = free_cash_flow / equity_value * 100

absolute_gap = actual - expected
percentage_gap = (actual - expected) / abs(expected) * 100
```

- input/amount storage scale: 6
- valuation output scale: 4
- percentile output scale: 2
- working precision: 28 digits
- rounding: `ROUND_HALF_EVEN`
- exact decimals serialize as strings

## Fail-closed gates

- exact instrument identity;
- accepted unadjusted official-close Canonical Price;
- eligible Comparison Eligibility purpose `normalized_valuation_metric_v1`;
- price no more than seven calendar days before valuation date;
- diluted-share effective range contains price date;
- TTM/instant financial observations no more than 120 days old;
- exact currency, unit, target period, period basis, horizon and accounting scope;
- exact cutoff and recorded-UTC visibility;
- no FX, corporate-action inference, free-text parsing or newest-row fallback;
- no missing-value imputation or hidden period substitution.

## Comparison rules

Historical context requires at least eight eligible observations, 730 calendar days, four distinct financial period ends and unique valuation dates.

Peer context requires at least three eligible members. The explicit manifest must equal persisted membership; ineligible members remain visible.

```text
percentile = (count(value < x) + 0.5 * count(value = x)) / n * 100
```

No persisted ordinal attractiveness label is permitted.

## Commands

```text
python -m scripts.record_structured_financial_observation --input <local-json-path>
python -m scripts.record_normalized_valuation_metric --input <local-json-path>
python -m scripts.record_valuation_comparison_set --input <local-json-path>
python -m scripts.record_normalized_expectation_gap --input <local-json-path>
```

All commands are local-only, strict-field, dry-run capable, expected-latest protected and atomic.

## Read boundary

```text
GET /normalized-valuation/financial-observation-revisions/{revision_id}
GET /normalized-valuation/metric-revisions/{revision_id}
GET /normalized-valuation/comparison-set-revisions/{revision_id}
GET /normalized-valuation/expectation-gap-revisions/{revision_id}
```

Every read requires `as_of_cutoff` and timezone-aware `as_of_recorded_at_utc`.

## Golden path

At 2026-06-30, subject A uses CNY 20 price, 1bn shares, CNY 10bn revenue, CNY 2bn profit, CNY 3bn EBITDA, CNY 1bn FCF and CNY 1bn net debt.

Expected outputs:

- PE `10.0000`
- PS `2.0000`
- EV/EBITDA `7.0000`
- FCF yield `5.0000`
- one loss-making peer remains visible with non-meaningful PE
- consensus profit CNY 2bn versus actual CNY 2.2bn yields CNY 200m, `10.0000%`, `above_expected`

## Validation gates

- focused deterministic rule tests;
- exact thirteen-table migration inventory;
- SQLite and PostgreSQL upgrade/round-trip/populated-downgrade tests;
- append-only mutation rejection;
- concurrent first-revision conflict;
- as-of non-leakage;
- complete historical/peer membership;
- exact query ceiling no higher than 18 statements;
- production-reachable offline golden path;
- full relevant regression and zero hidden network.

## Merge gate

The implementation PR remains Draft/Open/unmerged until green CI, complete base-to-head inventory, author fixed-head review, independent fixed-head implementation approval and separate explicit owner merge authorization.

Required approval:

`NORMALIZED VALUATION AND EXPECTATION METRICS IMPLEMENTATION APPROVED at fixed head <FULL_HEAD_SHA>`

## Locked exclusions

No external network, Provider, ingestion, crawling, browsing, hidden consensus feed, FX acquisition, corporate-action engine, automatic peer discovery, free-text parsing, target price, fair value, expected return, performance promise, buy/sell/hold output, portfolio, position sizing, broker/trading, AI-owned accepted state, automatic Investment Candidate score/status change, existing-row mutation/backfill, release, tag or version change.
