# Market Data Persistence

v0.3A implements explicit PostgreSQL persistence for the existing normalized stock-basic, daily-price, and trade-calendar contracts. v0.3B adds canonical snapshot-series identity and a manually invoked, bounded AKShare collection path. It does not implement scheduling, research workflow tables, portfolio storage, or Dashboard database reads.

Schema changes are applied only through Alembic. Importing or starting FastAPI never creates or migrates tables.

## Engine And Session Boundary

- `backend.database.engine.build_engine()` creates a SQLAlchemy engine from an explicit URL or `DATABASE_URL`.
- `backend.database.engine.build_session_factory()` creates the session boundary used by repositories and ingestion services.
- The API does not construct a database engine during import and does not run migrations at startup.

## Ingestion Provenance

`ingestion_runs` records every physical import attempt: provider, dataset, import/completion timestamps, requested date range and scope, information cutoff, contract version, status, row counts, deterministic SHA-256 batch identifier, canonical series key and identity, snapshot mode, provider request metadata, adapter version, and a concise failure summary.

The batch identifier covers normalized, deterministically ordered records plus provider, scope, date range, cutoff, contract version, and snapshot mode. Attempts are immutable: a failed attempt remains `failed`, and a retry creates another run with the same batch identifier. A partial unique index permits only one successful run per `(batch_identifier, series_key)` pair. This keeps v0.3A content hashes stable while allowing identical content under incompatible series parameters to remain independent. Repeating a successfully imported fixture batch returns that successful run and writes zero rows. Concurrent identical imports converge on the same successful run without exposing a unique-key failure to callers. All market-data rows reference their successful ingestion attempt by foreign key; failed writes retain no market rows.

## Natural Keys And Corrections

Logical natural keys are:

- stock basic: `(source, stock_code)`;
- daily price: `(source, stock_code, trade_date, adjust_type)`;
- trade calendar: `(source, trade_date)`.

Physical uniqueness adds `ingestion_run_id` to each logical key. A corrected batch adds a new immutable version instead of overwriting the old row.

Each accepted batch is a **complete snapshot**, not a partial revision. `requested_scope.stock_codes` is an **exact scope**: stock-basic and daily-price code sets must both equal the declared set. A later eligible snapshot that omits an earlier key does not carry that key forward. Partial revisions and tombstones are not implemented in v0.3A and are rejected rather than interpreted ambiguously.

Compatible snapshots share a canonical **series key**. Its SHA-256 input includes provider, dataset/contract combination, exact stock-code scope, requested date range, adjustment policy, complete/exact semantics, and canonical compatibility parameters. For AKShare these parameters include all three endpoint identifiers, daily frequency, and an explicit adapter compatibility version. Timeout, retry, live/offline mode, and the installed package patch version are request provenance rather than compatibility dimensions. Different stock scopes, dates, adjustment policies, endpoint mappings, or adapter compatibility versions therefore cannot replace one another.

Repository callers must supply an explicit series key or an equivalent complete canonical selector. Provider-only lookup fails closed even when only one series currently exists. Current and as-of readback first select one eligible successful complete snapshot within that series, ordered by:

1. `information_cutoff_date DESC`;
2. `completed_at DESC`;
3. `ingestion_run_id DESC` as the deterministic final tie-break.

`as_of_cutoff` additionally requires `information_cutoff_date <= as_of_cutoff`. Rows are then read only from the selected snapshot. Prior values, failed attempts, and batch provenance remain queryable for audit.

Migration `20260718_0002` adds and indexes the series identity plus provider-request provenance. It deterministically backfills v0.3A runs from provider, bundle/contract, exact scope, requested dates, snapshot semantics, and persisted adjustment values. The migration supports both a clean upgrade from base and an in-place upgrade from `20260718_0001`. Before downgrade changes any index, constraint, or column, it detects successful duplicate batch identifiers across series. Such history cannot satisfy the v0.3A batch-only unique rule, so downgrade fails closed with an actionable error and does not delete, merge, or overwrite audit records.

## Validation And Transactions

Before commit, the service validates contract columns, missing/blank identifiers, six-digit stock codes, declared provider and exact scope, complete-snapshot mode, strict dates, duplicates, finite/non-negative numeric data, OHLC consistency, adjustment values, booleans, requested date range, and cutoff. Every daily-price date must also exist in the same batch's trade calendar and be marked open. The three datasets write in one transaction; any validation, reconciliation, constraint, or insert failure leaves no partial market-data rows.

## Migration And Fixture Import

With PostgreSQL available and `DATABASE_URL` pointing to the target database:

```bash
python -m alembic upgrade head
python -m alembic current
python -m scripts.persist_fixture_market_data
python -m scripts.persist_fixture_market_data
```

The first import writes 2 stock-basic rows, 4 daily-price rows, and 2 trade-calendar rows. The second prints the same ingestion ID with `rows_written: 0` and `idempotent: true`. The command uses only local deterministic DataFrames and never calls AKShare or another network provider.

Controlled AKShare collection uses `python -m scripts.ingest_akshare_market_data` and is documented in [akshare_ingestion.md](akshare_ingestion.md). It requires explicit codes, dates, adjustment policy, cutoff, and either real-network consent or the offline fixture mode. A live cutoff must equal the UTC collection date and the request records the exact UTC timestamp plus installed AKShare version. Because `stock_info_a_code_name` has no historical selector, live stock-basic data represents only what was available at collection time and cannot reconstruct a historical universe. API startup, Dashboard use, tests, CI, and the fixture demo never invoke it.

The v0.4A Market Cockpit adds no table or migration. Its repository adapter selects one successful complete ingestion run by explicit series/cutoff ordering and reads all three datasets by that physical run ID. The public view carries a fixed allowlist of immutable import/completion/collection and canonical endpoint/adapter provenance while excluding opaque request metadata. Database construction remains request-lazy and injectable; the API never performs provider-only selection or falls back to fixture Dashboard data.

Inside Compose, run the commands with `docker compose exec app`. The public `.env.example` URL uses service hostname `postgres`. For direct host execution, set `DATABASE_URL` to the exposed host address, for example `postgresql+psycopg://aquantai:aquantai@127.0.0.1:5432/aquantai`.

After a failed import, correct the fixture, configuration, or database availability and retry. The failed attempt remains available for audit, while the retry receives a new ingestion-run ID. A failed run has no partial market rows. Do not use `Base.metadata.create_all()` for local operation.

## stock_basic

- Purpose: Store basic stock identity and listing information.
- Core fields: stock_code, stock_name, exchange, industry, listing_date, delisting_date, status.
- Future extensions: Index membership, concept tags, trading board, data source lineage.

Normalized provider columns:

- `stock_code`
- `stock_name`
- `exchange`
- `industry`
- `listing_date`
- `status`
- `source`

## daily_price

- Purpose: Store daily OHLCV and market data.
- Core fields: trade_date, stock_code, open, high, low, close, volume, amount, adjustment_type.
- Future extensions: Adjusted prices, turnover metrics, limit-up and limit-down flags, suspension status.

Normalized provider columns:

- `trade_date`
- `stock_code`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount`
- `adjust_type`
- `source`

## trade_calendar

- Purpose: Store open trading dates for the A-share market.
- Core fields: trade_date, is_open, source.
- Future extensions: Exchange-specific calendars, half-day flags, holiday metadata, data source lineage.

Normalized provider columns:

- `trade_date`
- `is_open`
- `source`

## Future Tables Not Implemented In v0.3

The following sections remain planning references only.

### financial_data

- Purpose: Store financial statements and derived financial indicators.
- Core fields: report_date, announce_date, stock_code, revenue, net_profit, total_assets, total_liabilities, equity.
- Future extensions: Statement type, restatement handling, trailing twelve month metrics, data quality flags.

### factor_values

- Purpose: Store raw factor calculation outputs.
- Core fields: factor_date, stock_code, factor_name, factor_value, factor_version.
- Future extensions: Factor metadata, calculation windows, source data snapshots, neutralization flags.

Normalized factor output columns:

- `factor_date`
- `stock_code`
- `factor_name`
- `factor_value`
- `factor_group`
- `factor_version`

### factor_scores

- Purpose: Store normalized and comparable factor scores.
- Core fields: score_date, stock_code, factor_name, score, rank, universe.
- Future extensions: Industry-neutral scores, z-scores, percentile ranks, composite score components.

Normalized score output columns:

- `score_date`
- `stock_code`
- `factor_name`
- `factor_group`
- `score`
- `rank`
- `universe`

### portfolio

- Purpose: Store generated stock pools and portfolio holdings.
- Core fields: portfolio_date, portfolio_name, stock_code, weight, rank, rebalance_frequency.
- Future extensions: Constraints, turnover, sector exposure, risk budgets.

Backtest holding output columns:

- `rebalance_date`
- `stock_code`
- `weight`
- `rank`
- `score`
- `universe`

### backtest_result

- Purpose: Store backtest summaries and key performance metrics.
- Core fields: backtest_id, strategy_name, start_date, end_date, total_return, annual_return, max_drawdown, sharpe_ratio.
- Future extensions: Equity curves, trade logs, benchmark comparison, parameter snapshots.

Phase 3 result fields:

- `start_date`
- `end_date`
- `total_return`
- `annual_return`
- `max_drawdown`
- `volatility`
- `sharpe_ratio`
- `turnover`
- `rebalance_count`

### research_report

- Purpose: Store AI-assisted research reports and human review notes.
- Core fields: report_id, report_date, title, scope, content, model_name, source_refs.
- Future extensions: Report versioning, reviewer comments, generated charts, confidence and risk annotations.

Phase 5 report fields:

- `report_date`
- `title`
- `scope`
- `summary`
- `factor_highlights`
- `backtest_highlights`
- `ml_highlights`
- `risks`
- `limitations`
- `disclaimer`
- `source_refs`

### ml_features

- Purpose: Store feature snapshots for guarded ML experiments.
- Core fields: feature_date, stock_code, universe, feature columns derived from factors or normalized market data.
- Future extensions: Feature versioning, lineage, preprocessing metadata, train/test split tags.

### ml_labels

- Purpose: Store supervised learning labels for research experiments.
- Core fields: label_date, stock_code, future_return, label_window, universe.
- Future extensions: Label definitions, benchmark-relative returns, outlier policy, leakage checks.

### ml_predictions

- Purpose: Store model prediction outputs in a backtest-compatible format.
- Core fields: prediction_date, stock_code, model_name, prediction_score, prediction_rank, universe.
- Future extensions: Experiment ID, model version, confidence bands, calibration metadata.

### dashboard_views

- Purpose: Describe read-only dashboard payloads assembled from research outputs.
- Core fields: page_id, title, sections, disclaimer, allowed_actions, source_refs, read_only.
- Future extensions: User preferences, saved views, chart configuration, export metadata.
