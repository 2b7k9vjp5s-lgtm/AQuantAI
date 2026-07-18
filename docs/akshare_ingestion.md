# Controlled AKShare Ingestion

v0.3B provides one manually invoked adapter from AKShare responses to the existing normalized stock-basic, daily-price, and trade-calendar contracts. It is not a scheduler, background service, Dashboard source, or full-market crawler.

v0.4B adds a separate bounded benchmark command using only `index_zh_a_hist`. Its rows, canonical identity, persistence table, and Market Cockpit context remain separate from the equity bundle. There is no silent endpoint fallback; see [benchmark_context.md](benchmark_context.md).

v0.4C adds a separate bounded sector command using only `stock_board_industry_name_em` for stable Eastmoney `BK` identifiers and `stock_board_industry_hist_em` for exact-code bounded history. It has no display-name selector or endpoint fallback; see [sector_context.md](sector_context.md).

The sector taxonomy endpoint has no historical date selector. Live taxonomy names and classification metadata are collection-time observations and cannot reconstruct historical taxonomy membership or naming.

## Snapshot-Series Identity

A canonical series key is the SHA-256 hash of stable JSON containing:

- series schema version;
- provider;
- dataset bundle and contract version;
- sorted normalized dataset names;
- exact sorted stock-code scope;
- requested start and end dates;
- adjustment policy;
- `complete` snapshot mode;
- `exact` stock-code semantics;
- canonical compatibility parameters that can change snapshot compatibility.

The AKShare CLI compatibility parameters include daily frequency, the stock-basic endpoint, the daily-price endpoint, the trade-calendar endpoint, and the explicit `aquantai.akshare-adapter.v1` compatibility version. Different stock scopes, date ranges, adjustment policies, providers, contracts, endpoint mappings, or adapter compatibility versions produce different series keys. Operational timeout, retry, and network-mode settings remain request metadata and do not fragment a compatible series.

Repository current and as-of reads require either an explicit series key or a complete validated canonical selector. Provider-only reads fail closed. Within one series, successful complete snapshots are ordered by `information_cutoff_date DESC`, `completed_at DESC`, and `ingestion_run_id DESC`. Reads use only rows from the selected snapshot and never merge natural keys across snapshots.

Migration `20260718_0002` adds and indexes `series_key`, stores canonical identity and provider request metadata, records adapter version, and deterministically backfills v0.3A runs. Existing adjustment policy is recovered from persisted daily-price rows; a run without rows defaults to the unadjusted v0.3A policy. Downgrade performs a preflight before changing any schema: if valid multi-series history would violate the older batch-only uniqueness rule, it stops with an actionable Alembic error and preserves every ingestion run.

## Endpoint Mapping

- `stock_info_a_code_name` -> normalized `stock_basic` rows, filtered to the exact requested codes.
- `stock_zh_a_hist` -> normalized `daily_price` rows, called once per explicit code with `period=daily`, bounded dates, and explicit adjustment policy.
- `tool_trade_date_hist_sina` -> normalized open `trade_calendar` rows filtered to the requested dates.

Responses pass through the existing persistence validation: exact scope, strict dates and cutoff, finite OHLCV values, duplicate rejection, provider identity, daily-price/calendar reconciliation, transactional rollback, immutable attempts, and concurrent idempotency.

`stock_info_a_code_name` has no historical date selector. The adapter therefore cannot reconstruct a historical stock universe. In live mode, stock-basic rows mean only information available when this collection ran, not membership or status as of an arbitrary earlier date.

## Live Cutoff And Collection Time

Live `--allow-network` collection records one timezone-aware UTC collection timestamp and requires `--cutoff` to equal that timestamp's UTC calendar date. A past or future live cutoff is rejected before provider construction, provider calls, database-engine creation, or ingestion-run creation. This prevents a current stock-basic response from being labeled as historical point-in-time data.

Offline fixture and injected-mock modes may continue to use an explicit deterministic cutoff for repeatable tests. Provider request metadata records the collection timestamp, effective cutoff, installed AKShare package version, endpoints, scope, timeout, retries, and network mode. The adapter validates AKShare at runtime against the reviewed range `>=1.16.0,<2.0.0`; package patch versions are audited but do not change the canonical series key.

## Commands

Real network collection:

```bash
python -m scripts.ingest_akshare_market_data \
  --stock-code 000001 \
  --start-date 20260708 \
  --end-date 20260709 \
  --adjust qfq \
  --cutoff 20260718 \
  --allow-network
```

Normalization-only offline example:

```bash
python -m scripts.ingest_akshare_market_data \
  --stock-code 000001 \
  --stock-code 600000 \
  --start-date 20260708 \
  --end-date 20260709 \
  --adjust qfq \
  --cutoff 20260709 \
  --offline-fixture \
  --dry-run
```

`--dry-run` never creates a database engine or ingestion run. `--offline-fixture` never accesses the network. Without either `--allow-network` or `--offline-fixture`, the CLI exits nonzero. One invocation accepts at most 50 explicit stock codes; there is no all-market default.

## Bounded Failure Behavior

Live endpoint calls run in a child process with a finite timeout. A timed-out child is terminated. Retries are finite, and errors identify the endpoint and suggest reducing scope or retrying later. Provider request metadata stores the UTC collection timestamp, effective cutoff, installed AKShare package version, endpoint names, explicit scope, adjustment policy, network mode, timeout, retry count, and adapter version; sensitive credential-like fields are rejected.

Provider or normalization failures leave zero market-data rows and retain an immutable failed ingestion attempt when persistence mode is active. Dry-run failures do not write audit rows because dry-run guarantees zero database writes.

## Exclusions

- No automatic or scheduled collection.
- No unbounded full-market default.
- No Dashboard database reads or UI changes.
- No financial statements, factor persistence, research workflow, watchlists, or paper portfolios.
- No Market Cockpit, Industry Alpha, Qlib training, LLM execution, broker connectivity, order placement, or trading.
- Benchmark collection does not imply official exchange attribution or full-market coverage and adds no timing, recommendation, or relative-performance output.
