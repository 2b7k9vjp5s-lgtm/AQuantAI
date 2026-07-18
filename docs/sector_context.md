# Provider-Attributed Sector Market Context v0.4C

v0.4C adds a separate, optional selected-sector domain beside the selected-equity and
benchmark domains. Sector rows never share an equity or benchmark series key, ingestion
run, table, natural key, or calculation. The output describes only the exact requested
Eastmoney industry-board codes. It is not an official exchange statement, full-market
coverage, an Industry Alpha conclusion, a signal, or advice.

## Reviewed AKShare Contract

The generic equity/benchmark adapter continues to accept AKShare `>=1.16.0,<2.0.0`.
Sector collection has a separate, narrower fail-closed contract: it accepts exactly
AKShare `1.18.64`. No other patch or generically accepted version is described as
sector-compatible.

This boundary is based on the official
[`release-v1.18.64`](https://github.com/akfamily/akshare/releases/tag/release-v1.18.64)
and its
[`stock_board_industry_em.py`](https://github.com/akfamily/akshare/blob/release-v1.18.64/akshare/stock/stock_board_industry_em.py)
source, plus deterministic local contract tests. That exact source exposes the reviewed
taxonomy columns, recognizes `BK` identifiers directly in the history function, and
accepts bounded start/end, daily period, and unadjusted arguments. Earlier releases were
not proven from recorded evidence, so the implementation does not guess a lower bound.

Exactly two endpoints are authorized, with no fallback:

- `stock_board_industry_name_em`: returns Eastmoney industry-board `板块代码` and
  `板块名称`. The stable provider identifier is the exact `BK` code, not the display name.
- `stock_board_industry_hist_em`: accepts an exact `BK` code plus bounded `start_date`,
  `end_date`, `period="日k"`, and `adjust=""` arguments.

The taxonomy is `eastmoney_industry_board`, classification level is unavailable and is
stored as `null`, and parent identity is unavailable and stored as `null`. A requested
code absent from the taxonomy response fails the complete snapshot. Display names are
metadata and are never accepted as selectors.

`stock_board_industry_name_em` has no historical date selector. In live mode its names and
classification metadata mean only what was available at the UTC collection time; this
adapter cannot reconstruct historical taxonomy membership or historical display names.

| AKShare field | Normalized field | Rule |
| --- | --- | --- |
| `板块代码` | `sector_code` | Required `BK` plus digits; exact requested scope |
| `板块名称` | `sector_name` | Required nonblank display metadata |
| `日期` | `trade_date` | Required and inside requested bounds/cutoff |
| `收盘` | `close` | Required, finite, positive |
| `开盘` / `最高` / `最低` | `open` / `high` / `low` | Optional complete group; finite, positive, range checked |
| `成交量` / `成交额` / `换手率` | `volume` / `amount` / `turnover_rate` | Optional, finite and nonnegative; provider-attributed units |

The definition contract is `sector_definition` version `1.0`, the daily contract is
`sector_daily` version `1.0`, and adapter compatibility is
`aquantai.akshare-sector-endpoints.v1.18.64`. Changing endpoint, identifier semantics,
taxonomy, mapping, contract, or this sector endpoint compatibility version creates a
different canonical series. The sector gate runs before endpoint access or database-engine
creation. Offline fixtures and injected adapters state the accepted deterministic package
version explicitly.

## Fixed Provider Metadata Contract

`IngestionRun.provider_request_metadata` accepts exactly these top-level fields:

- `taxonomy_endpoint`, `history_endpoint`;
- `classification_system`, `classification_level`;
- `frequency`, `adjust_type`;
- `sector_codes`, `start_date`, `end_date`;
- `network_mode`, `timeout_seconds`, `max_retries`;
- `akshare_package_version`;
- `definition_contract_version`, `daily_contract_version`;
- `adapter_version`, `adapter_compatibility_version`;
- `collection_timestamp_utc`, `effective_information_cutoff_date`.

The contract is flat except for the exact sorted unique `sector_codes` list. Unknown keys,
nested provider responses, debug dumps, headers, environment values, filesystem paths, and
other arbitrary payloads are rejected and never persisted. Sensitive-name rejection remains
an additional defense.

Every value is normalized and bounded. Dates use `YYYYMMDD`; collection time must be an
explicit UTC timestamp; timeout is finite and positive; retry count is a bounded integer;
classification level remains explicitly `null` for this endpoint pair. Endpoints,
classification, frequency, adjustment, exact code/date scope, contracts, adapter version,
compatibility version, and effective cutoff must agree with the canonical request. The same
validation applies before recording successful or failed attempts.

## Canonical Series And Persistence

The sector series key hashes canonical JSON containing the sector series schema,
provider, both contract versions and datasets, exact endpoints, taxonomy and nullable
level, exact sorted `BK` code scope, requested dates, daily frequency, unadjusted policy,
complete snapshot mode, exact-scope semantics, and sector endpoint compatibility version.
Display names, timeout, retry count, network mode, collection timestamp, and the separately
audited installed-package field are request provenance; the canonical compatibility version
already identifies the exact reviewed sector endpoint contract.

Each physical attempt stores immutable definition and daily rows linked to one ingestion
run. Successful snapshots are selected by cutoff descending, completion time descending,
and ingestion-run ID descending. Reads use exactly one successful complete run and never
stitch taxonomy or history across runs or series. Provider-only, name-only, partial, and
incomplete selectors fail closed.

## Exact Expected-Session Formulas

The selected equity snapshot's clipped, persisted `is_open=true` calendar is the only
expected-session source. For sector `i` at its latest eligible session `t`:

```text
latest_return(i,t) = close(i,t) / close(i,t-1) - 1       # exact 2 sessions
return_5(i,t) = close(i,t) / close(i,t-5) - 1            # exact 6 sessions
return_20(i,t) = close(i,t) / close(i,t-20) - 1          # exact 21 sessions
SMA20(i,t) = mean(exact latest 20 expected closes)
sma20_distance(i,t) = close(i,t) / SMA20(i,t) - 1
volatility_20(i,t) = sample_std(exact 20 returns, ddof=1) * sqrt(252)
wealth(0) = 1; wealth(k) = product(1 + return(j), j=1..k)
max_drawdown_20(i,t) = min(wealth(k) / max(wealth(0..k)) - 1)
```

A metric is available only when its full exact window is present once with valid positive
closes. Missing, duplicate, invalid, future, or insufficient rows produce `null` and a
bounded deterministic diagnostic. Windows are never shortened, filled, interpolated, or
replaced with zero.

## Descriptive Cross-Section

The response reports requested, available, and equity-session-aligned counts; sorted
missing codes; positive latest-return count/share; above-SMA20 count/share; and top/bottom
lists for latest and 20-session return. Null metrics are excluded from denominators. Lists
contain at most five sectors and sort by metric, then stable sector code for deterministic
ties. No composite score, regime, recommendation, alpha label, or automatic conclusion is
produced.

## Cutoff And Alignment

Sector selection honors `as_of_cutoff` before choosing a snapshot. Rows are then bounded
by sector cutoff, requested end, and the selected equity effective session. Alignment is:

- coverage `complete`: every exact requested sector has an eligible latest row;
- coverage `partial`: one or more exact requested sectors has no eligible row;
- session `aligned`: every requested sector has an eligible row at the equity session;
- session `different_session`: all requested sectors share one earlier eligible session;
- session `partial`: a sector is missing or latest eligible sessions differ;
- cutoff `aligned`: equity and sector information cutoffs match;
- cutoff `different_cutoff`: they differ.

Overall `aligned` requires both dimensions. If no sector is eligible, effective sector
session is `null`, available/aligned counts are zero, all requested codes are missing, and
status is `partial`. Persisted physical maximum dates are never substituted.

## Manual And Read-Only Boundaries

Live collection is manual only and requires `--allow-network`, one to thirty exact `BK`
codes, bounded dates, and a cutoff equal to the UTC collection date. Offline fixture and
injected-frame paths may use deterministic historical cutoffs. Dry-run creates no engine,
attempt, definition row, or daily row. Imports, FastAPI startup, page access, tests, CI,
and fixture demos never access the network.

The API adds optional `sector_series_key` to `/market-cockpit/snapshot`. Without it, the
accepted equity and benchmark payloads remain compatible and `sector_context` is `null`.
The page is read-only and provider-attributed. It contains no collection control, sector
search, company membership, beneficiary mapping, Industry Alpha claim, recommendation,
broker action, order, or trading behavior.
