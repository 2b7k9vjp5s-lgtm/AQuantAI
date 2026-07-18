# Provider-Attributed Benchmark Index Context v0.4B

v0.4B adds a separate, optional benchmark-index domain beside the selected-equity-universe Market Cockpit. Benchmark rows never share an equity series key, ingestion run, table, natural key, or calculation. One or more selected codes do not establish full-market coverage and are not described as an official exchange statement.

## Reviewed Endpoint And Mapping

The only v0.4B live endpoint is AKShare `index_zh_a_hist`, called with one explicit six-digit `symbol`, `period=daily`, and bounded `start_date`/`end_date`. The reviewed AKShare implementation attributes this response to Eastmoney; AQuantAI records AKShare as the adapter/provider and does not promote that mapping into an official exchange claim. There is no fallback endpoint.

| AKShare column | Normalized field | Rule |
| --- | --- | --- |
| `日期` | `trade_date` | Required, bounded date |
| request symbol | `index_code` | Required exact six-digit code |
| adapter provider | `source` | Required provider identity |
| `收盘` | `close` | Required, finite, positive |
| `开盘` / `最高` / `最低` | `open` / `high` / `low` | Optional as a complete group; finite, positive, and `low <= open/close <= high` |
| `成交量` / `成交额` | `volume` / `amount` | Optional, finite, nonnegative; provider-attributed units are retained without an exchange-level unit claim |

The normalized contract is `benchmark_index_daily` version `1.0`; adapter compatibility is `aquantai.akshare-benchmark-adapter.v1`. Installed AKShare version `>=1.16.0,<2.0.0` is checked at runtime and recorded as request provenance, not series compatibility.

## Series Identity And Snapshot Selection

The benchmark series key hashes canonical JSON containing benchmark series schema version, provider, contract and dataset, exact sorted index-code scope, requested dates, daily frequency, complete snapshot mode, exact-code semantics, endpoint, adapter compatibility version, and any additional normalized compatibility parameter. Timeout, retries, network mode, collection time, and installed patch version do not fragment a compatible series.

Reads require an explicit benchmark `series_key` or an equivalent complete canonical selector. Provider-only, code-only, and incomplete selection fail closed. Eligible successful complete runs are ordered by information cutoff descending, completion time descending, and ingestion-run ID descending. Exactly one physical run is read; histories are never stitched across runs, series, providers, endpoints, or domains.

## Cutoff And Alignment

Live collection uses one UTC collection timestamp and requires information cutoff to equal its UTC date. Offline fixture and injected mock collection may use a deterministic cutoff. Requested price dates are independently bounded and may not exceed cutoff.

For Market Cockpit use, the selected equity snapshot's persisted `trade_calendar` is the only v0.4B session reference. This keeps point-in-time eligibility tied to the same physical equity ingestion run that establishes the Market Cockpit as-of session; no live calendar, weekday inference, other equity run, or benchmark row order is used. The ordered sequence contains only persisted `is_open=true` sessions and is clipped by the requested `as_of_cutoff`, equity information cutoff, benchmark information cutoff, equity requested end/effective session, and benchmark requested end. A missing or contradictory selected-equity calendar fails closed.

Benchmark rows must be no later than that clipped sequence. Equity and benchmark runs remain selected independently and their data rows are never joined or stitched. Session alignment and cutoff alignment are reported separately:

- session `aligned`: every exact requested code has a latest valid row at the equity effective session;
- session `different_session`: every requested code is available on one shared earlier session;
- session `partial`: any code is unavailable or per-code latest sessions differ;
- cutoff `aligned`: selected equity and benchmark information cutoffs are equal;
- cutoff `different_cutoff`: selected information cutoffs differ.

Overall `aligned` requires both session and cutoff alignment. A partial session result remains `partial`; otherwise an earlier session is `different_session` and equal sessions with different cutoffs are `different_cutoff`. Requested, available, and equity-session-aligned code counts plus an exact sorted missing-code list make the status auditable. No relative-performance calculation is inferred.

## Close-Based Formulas

For each exact benchmark code, windows end at that code's latest valid close within the clipped expected-session sequence. Each metric is calculated only when every expected persisted open session in its exact ending window is present once with a finite positive close. Missing rows are not forward-filled, sparse rows do not substitute for expected sessions, and another code is never substituted.

```text
latest_return = close(t) / close(t-1) - 1                 # exact adjacent 2-session window
SMA(N) = arithmetic mean of one exact N-session window    # N = 20 or 60
above_SMA(N) = close(t) > SMA(N)
realized_volatility_20 = sample_std(last 20 returns, ddof=1) * sqrt(252)
wealth(0) = 1
wealth(k) = product(1 + return(j), j=1..k)                # 20 returns / 21 closes
max_drawdown_20 = min(wealth(k) / max(wealth(0..k)) - 1)
```

Latest close may expose the latest available valid row even when it is stale. Latest return requires the immediately preceding expected open session, SMA20/SMA60 require exact consecutive 20/60-session windows, and volatility/drawdown require one exact consecutive 21-session window producing 20 adjacent one-session returns. A gap outside a metric's ending window does not invalidate that metric.

Every metric window exposes its required count, present-valid count, start/end when definable, bounded missing and invalid session lists with total counts, and one stable reason: `available`, `insufficient_history`, `missing_expected_session`, or `invalid_close`. Broken windows return `null`; zero is returned only when it is a valid calculated value. Code and session diagnostics are sorted deterministically.

## Manual Commands

Offline normalization-only validation, with no engine or database rows:

```bash
python -m scripts.ingest_akshare_benchmark_data --index-code 000001 --start-date 20260105 --end-date 20260403 --cutoff 20260405 --offline-fixture --dry-run
```

Live collection additionally requires `--allow-network`; at most 20 explicit codes are accepted. It is never invoked by imports, FastAPI startup, page access, tests, CI, or fixture demos.

The Market Cockpit API remains equity-selector-first:

```text
GET /market-cockpit/snapshot?series_key=<equity>&benchmark_series_key=<benchmark>&as_of_cutoff=YYYYMMDD
```

Without `benchmark_series_key`, the v0.4A equity payload remains compatible and benchmark context is `null`. An invalid or unavailable benchmark selector returns 422 or 404 rather than silently omitting or replacing it.

## Provenance And Boundaries

The public benchmark view allowlists series/run, provider/source, contract/adapter, endpoint, frequency, exact codes, requested dates, selected/effective cutoff, effective session, collection/import/completion time, installed package version, network mode, timeout, retries, alignment, and view-generation time. Unknown and credential-like metadata is omitted.

The page and API are local-first, read-only, research-only, and non-advisory. v0.4B does not add official exchange certification, beta, correlation, alpha, excess return, relative-strength ranking, timing signals, recommendations, sector rotation, style, valuation, crowding, automatic collection, brokers, orders, or trading.
