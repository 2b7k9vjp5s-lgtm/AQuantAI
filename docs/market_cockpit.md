# Market Cockpit v0.4A

v0.4A is a local, read-only, database-backed monitor for one explicitly selected persisted universe. It does not describe full-market or official-index breadth. Every result is tied to one successful complete snapshot selected by `series_key` or an equivalent complete canonical selector.

## Point-In-Time Selection

1. Select one successful ingestion run inside the requested series. With `as_of_cutoff`, only runs whose `information_cutoff_date <= as_of_cutoff` are eligible.
2. Order eligible runs by `information_cutoff_date DESC`, `completed_at DESC`, and ingestion-run ID `DESC`.
3. Read stock basic, daily price, and trade calendar rows only from that run ID. Never combine natural keys or history across runs or series.
4. The effective as-of session is the latest persisted open calendar date no later than the selected run cutoff, optional `as_of_cutoff`, and requested end date.
5. Ignore every calendar or price row after the effective as-of session. Rolling windows contain only persisted open sessions ending on or before that session.

Missing a series selector, database configuration, eligible run, or effective open session is an error. The service never falls back to Dashboard fixtures.

## Exact Formulas

All returns are decimal values. A value of `0.01` means one percent.

### Latest-session breadth

For stock `i` on effective session `t` and its immediately preceding persisted open session `t-1`:

```text
r(i,t) = close(i,t) / close(i,t-1) - 1
```

A stock is available only when both finite positive closes exist and both rows are traded observations. A row with both `volume == 0` and `amount == 0` is deterministically classified as `no_trade`; it is unavailable and cannot become an unchanged return. Advancing means `r > 1e-12`, declining means `r < -1e-12`, and unchanged means `abs(r) <= 1e-12`. An unchanged close with positive trading activity remains valid.

- equal-weight mean return: arithmetic mean of available `r(i,t)`;
- median return: median of available `r(i,t)`;
- unavailable count: selected-universe count minus available return count;
- advance ratio: advancing count divided by available return count;
- breadth balance: `(advancing - declining) / available return count`;
- cross-sectional dispersion: population standard deviation of available returns (`ddof=0`).

If no stock has an available return, return `null` for ratios and return statistics. Counts remain factual integers.

Latest-return metrics and diagnostics consume one shared stock-code-sorted eligibility classification. Each unavailable return has exactly one issue, with effective-session causes taking precedence over previous-session causes. Stable reason values are:

- `missing_effective_session_row`;
- `invalid_effective_session_row`;
- `no_trade_effective_session_row`;
- `missing_previous_session_row`;
- `invalid_previous_session_row`;
- `no_trade_previous_session_row`.

Each issue reports the blocking session, the last valid traded session strictly before that blocking session, and their persisted open-session gap. A previous-session failure never reports the valid effective session as its last-valid reference. If no earlier valid traded session exists, the last-valid session and gap are `null`. The bounded contract enforces:

```text
latest_return_unavailable_count == metrics.latest_session.unavailable_count
len(latest_return_issues) == metrics.latest_session.unavailable_count
```

### Moving-average breadth

For `N` equal to 20 or 60, a stock is eligible only when it has one finite positive close on every one of the last `N` persisted open sessions, including the effective session.

```text
SMA(i,N,t) = mean(close(i,s) for s in last N open sessions through t)
above_sma(i,N,t) = close(i,t) > SMA(i,N,t)
above_sma_ratio(N,t) = above count / eligible count
```

Fewer than `N` calendar sessions, any missing stock close, or any no-trade row makes that stock unavailable for the metric. A zero eligible count returns `null`, never zero.

### New highs and lows

Using the same complete `N`-session close window:

```text
new_high(i,N,t) = close(i,t) == max(close(i,s))
new_low(i,N,t) = close(i,t) == min(close(i,s))
```

The response reports high count, low count, and eligible coverage for 20 and 60 sessions. Counts are `null` when coverage is zero. A factual zero is returned only when at least one stock has the full window.

### Volume and amount participation

Participation requires 21 sessions: the effective session plus the prior 20 persisted open sessions. For field `x` equal to volume or amount:

```text
baseline(i,x,t) = median(x(i,s) for the 20 open sessions before t)
participation(i,x,t) = x(i,t) / baseline(i,x,t)
aggregate_participation(x,t) = mean(participation(i,x,t) over eligible stocks)
```

The current session is excluded from the baseline. A stock is unavailable when any required value is missing/non-finite, any required row is no-trade, or the baseline is not positive. The aggregate is `null` when no stock is eligible and always includes a coverage count.

### Equal-weight risk

Risk uses the latest 20 close-to-close return sessions. A session return is eligible only when every selected stock has finite positive closes and traded observations on that session and its preceding open session. This strict complete-universe rule keeps equal weights stable.

```text
universe_return(t) = mean(r(i,t) for every selected stock)
realized_volatility_20 = sample_std(last 20 universe returns, ddof=1) * sqrt(252)
wealth(0) = 1
wealth(k) = product(1 + universe_return(j), j=1..k)
drawdown(k) = wealth(k) / max(wealth(0..k)) - 1
max_drawdown_20 = min(drawdown(k), k=0..20)
```

Both metrics require exactly 20 eligible return sessions. Otherwise they are `null` with an insufficient-history warning. A zero drawdown is valid only after the full window is available.

## Calculation, Scope Coverage, And Overall Completeness

`calculation_status` describes only internal metric availability for the exact selected universe:

- `ready`: exact selected rows are present, latest returns cover every stock, and all 20/60-session and participation/risk windows have full-scope coverage;
- `partial`: core breadth is calculable, but at least one stock/window/field is missing, stale, no-trade, duplicated, inactive, or otherwise unavailable;
- `insufficient_data`: no available latest return exists for core breadth calculations.

`scope_coverage_status` is `unverified_selected_scope` throughout v0.4A. There is no reviewed policy establishing representative A-share coverage, and no stock-count threshold is invented as a substitute. Therefore the conservative user-facing `completeness_status` is always `partial` when calculations exist and `insufficient_data` when core breadth cannot be calculated. Internally ready calculations do not establish representative A-share or full-market coverage.

Warnings identify exact missing effective/previous rows, no-trade observations, inactive stock records, duplicate sessions, incomplete scope, unavailable windows, and future rows that were excluded. Current-session health aggregates (`stale_or_missing_latest_count` and `no_trade_latest_count`) remain separate from latest-return eligibility. `latest_return_unavailable_count` and `latest_return_issues` cover both required sessions and can never be empty when the latest metric reports an unavailable stock. Diagnostics describe observations as potentially suspended or no-trade and never claim a confirmed suspension.

## Response Provenance

Every response exposes the exact stock-code scope, selected and available counts, series key, ingestion-run ID, provider, contract version, adapter version, selected-run information cutoff, requested historical cutoff, effective as-of session, requested date range, adjustment policy, calculation/scope/overall status, warnings, and unsupported sections.

The immutable provenance view uses a fixed allowlist only: ingestion import and completion timestamps, collection timestamp, effective information cutoff, installed AKShare package version, stock-basic/daily-price/trade-calendar endpoint identifiers, frequency, and adapter compatibility version. Unknown request metadata and fields representing secrets, tokens, passwords, API keys, credentials, connection strings, or cookies are never serialized. Missing fixture/backfill fields are `null`. Timestamps are normalized to UTC ISO-8601. `generated_at_utc` is explicitly view-generation time and is distinct from collection/import time.

## Unsupported In v0.4A

- official index levels or returns;
- sector or industry rotation;
- size, value, or growth style analysis;
- valuation or market-cap breadth;
- crowding or positioning indicators.

The page and API are read-only, research-only, and non-advisory. v0.4A adds no collection endpoint, scheduler, automatic refresh, recommendation, broker action, order, or trading behavior.
