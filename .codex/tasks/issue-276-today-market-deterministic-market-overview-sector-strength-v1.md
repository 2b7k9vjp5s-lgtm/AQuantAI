# Issue #276 — Today Market Deterministic Market Overview + Sector Strength v1

## Authority

Project-owner instruction on 2026-07-29 explicitly starts Slice B after closing Issue #273.

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
base = 49cb80ee5b37cf0cd04f3c5978c6f89d54eaac12
branch = feat/today-market-deterministic-market-overview-sector-strength-v1
issue = #276
risk_tier = Strict Implementation
architecture = #270 / merged PR #271
slice_a = #273 / merged PR #275 / completed
```

No rebase, force-push, silent base update, schema/migration, API/UI, Provider/runtime, recommendation, portfolio, trading, release/tag/version or PR #241 modification is authorized.

## Objective

Implement a pure deterministic, source-neutral rules layer:

```text
exact calculation inputs
  -> market overview v1
  -> sector hotspot v1
  -> stock anomaly v1
  -> deterministic read model for later Slice C
```

Rule versions are frozen by accepted PR #271:

```text
market_rule_version = aquantai.today-market-market-overview.v1
sector_rule_version = aquantai.today-market-sector-hotspot.v1
anomaly_rule_version = aquantai.today-market-stock-anomaly.v1
return_epsilon = 1e-12
```

## Repository audit and ownership boundary

Current main already has deterministic Market Cockpit primitives in:

```text
market_cockpit/calculator.py
market_cockpit/contracts.py
market_cockpit/sector_calculator.py
market_cockpit/sector_contracts.py
```

Existing DB models provide sector definition and sector daily observations, but there is no effective-dated sector-membership persistence owner. Slice A added no schema/migration and kept durable membership and standalone company-action/adjustment-factor persistence as stop conditions.

Therefore:

```text
schema_migration_required = false for this rules slice
new_database_owner = prohibited
```

A pure dated-membership calculation input may be defined, but it cannot be persisted or inferred from current constituents. Missing exact dated membership forces constituent-confirmed sector state to `insufficient_coverage`; sector price-only metrics may remain visible.

Cross-session calculations that require exact adjustment/reference-close semantics must receive an explicit validated input/status. Missing semantics make the affected metric unavailable; raw close substitution is prohibited.

## Exact allowlist

Only:

```text
.codex/tasks/issue-276-today-market-deterministic-market-overview-sector-strength-v1.md
market_cockpit/today_market_rule_contracts.py
market_cockpit/today_market_rules.py
market_cockpit/__init__.py
tests/test_today_market_deterministic_rules.py
tests/test_today_market_deterministic_rule_boundaries.py
scripts/demo_today_market_deterministic_rules.py
.github/workflows/local-tests.yml
```

`market_cockpit/__init__.py` and `.github/workflows/local-tests.yml` are optional and may change only for exports / additive offline demo invocation.

No additional path is authorized. If another production file becomes necessary, STOP and request an allowlist amendment before editing it.

## Frozen market overview rules

Headline eligibility:

```text
return_coverage_ratio >= 0.90
calendar_conflict = false
identity_conflict_count = 0
```

Else `insufficient_coverage`.

```text
advance_ratio = advancing / valid_return_count
breadth_balance = (advancing - declining) / valid_return_count
median_return = median(valid r1)
above_ma20_ratio = above_ma20_count / eligible_20_count
new_high_20_ratio = new_high_20_count / eligible_20_count
new_low_20_ratio = new_low_20_count / eligible_20_count
market_amount_ratio_20 = market_amount_t / median(previous 20 exact-session market amounts)
```

State:

```text
strong: breadth_balance >= 0.20 AND median_return > 0 AND above_ma20_ratio >= 0.55
weak: breadth_balance <= -0.20 AND median_return < 0 AND above_ma20_ratio <= 0.45
mixed: otherwise
```

## Frozen sector hotspot rules

```text
minimum_ranked_sector_count = 10
constituent_return_coverage_min = 0.90
constituent_ma20_coverage_min = 0.80
```

Percentile:

```text
sort descending by value
exact ties -> sector_code ascending
rank_pct = 1 - (rank - 1)/(N - 1)
N >= 10
```

Ordered state priority:

```text
1 insufficient_coverage
2 high_level_divergence
3 cooling
4 spreading
5 new
6 persistent_strong
7 strengthening
8 neutral
```

Use exact thresholds from accepted architecture #271. No opaque score and no missing-value-as-zero behavior.

## Frozen stock anomaly rules

Implement exact #271 rules for:

```text
large_move
unusual_volume
new_high
new_low
gap
persistent_relative_strength
sector_relative_outlier
```

One stock may emit multiple reasons. Stable order: rule-contract order, descending absolute primary metric, stock code ascending.

No anomaly may create or mutate research explanation, evidence, Industry Thesis, Investment Candidate, recommendation or trading state.

## Required validation

Positive coverage:

- market states strong / weak / mixed / insufficient_coverage;
- exact 0.90 coverage boundary;
- 20-session breadth and market amount ratio;
- deterministic sector percentile/tie breaks across >=10 sectors;
- every hotspot state plus neutral/insufficient_coverage;
- prior-state ordering;
- every anomaly type;
- multiple anomalies and stable ordering;
- deterministic fingerprints/replay equality;
- sector price-only output while membership is unavailable.

Negative coverage:

- non-dated/current membership cannot satisfy hotspot state;
- ranked sector count <10;
- constituent return coverage <0.90;
- MA20 coverage <0.80 for rules that require it;
- missing analysis-price/reference-close semantics;
- incomplete lookback;
- MAD=0 sector outlier;
- duplicate/ambiguous sector identity;
- no metric imputed as zero;
- no universal limit heuristic;
- no network/database/runtime/AI/research-mutation path in rule modules.

Normal CI/tests/demo remain zero-network and synthetic-only.

## Delivery gate

Before merge consideration:

1. Base remains exact `49cb80ee5b37cf0cd04f3c5978c6f89d54eaac12` unless separately governed.
2. Base→HEAD inventory stays inside this allowlist.
3. `behind = 0`.
4. No schema/migration/database model/API/UI/Provider/runtime changes.
5. Focused tests + full pytest + configured offline demos pass on one immutable HEAD.
6. Fresh fixed-head review contains exactly:

```text
AUTHORIZED TODAY MARKET DETERMINISTIC MARKET OVERVIEW + SECTOR STRENGTH V1 IMPLEMENTATION APPROVED at fixed head <FULL_HEAD_SHA>
```

7. unresolved review threads = 0.
8. Project owner separately authorizes Ready/merge.
9. Any new commit invalidates previous fixed-head CI/review evidence.

Keep PR Draft through implementation. Merge does not authorize Slice C and does not close Issue #276 automatically.