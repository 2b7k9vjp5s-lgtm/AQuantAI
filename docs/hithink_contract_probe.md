# Hithink Contract Acceptance Probe

This bounded probe gathers sanitized contract evidence for a future provider decision. It is not a `DataProvider`, ingestion path, database writer, dump downloader or default-provider change.

## Safety boundary

- Offline and live modes are explicit and mutually exclusive.
- Live mode requires `--allow-network`; offline mode uses synthetic contract envelopes and never reads `HITHINK_FINANCE_API_KEY`.
- Live mode reads `HITHINK_FINANCE_API_KEY` from the local environment only after live opt-in and input validation. There is no CLI key argument.
- The fixed base URL is `https://fuyao.aicubes.cn`, requests use `X-api-key`, a 10-second timeout and one attempt per capability.
- Output contains only sanitized counts, schema fingerprints, suffix coverage, business-code categories and evidence-completeness booleans.
- The probe imports no persistence or database boundary and performs no database write.

Do not paste credentials into a terminal command, chat, Issue, PR, file or log. A live probe is optional and should be run only by the account owner with a locally configured secret.

## Offline contract mode

Use one exact six-digit representative for each reviewed suffix and a bounded date range:

```bash
python -m scripts.probe_hithink_contracts \
  --offline-contract \
  --representative 600000.SH \
  --representative 000001.SZ \
  --representative 430001.BJ \
  --start-date 2026-07-01 \
  --end-date 2026-07-10
```

Without local manifest and rights evidence, endpoint shapes can pass while the overall result remains `blocked`. This is intentional.

## Optional local evidence

Evidence files are local, untracked JSON. The probe summarizes completeness only and never echoes notes, account identifiers or credentials.

The manifest contract requires:

- `dump_id`: `a_share_daily_k_1d_none_10d`;
- non-empty `version`;
- `mode`: `RECENT_TRADING_DAYS`;
- ISO `coverage_start` and `coverage_end`;
- positive integer `row_count` and `ticker_count`;
- empty `failed_tickers`;
- a safe `.parquet` `file_name`;
- lowercase 64-character `sha256`;
- the reviewed daily-bar `schema` fields.

The rights evidence requires entries for enabled capabilities, quotas/QPS, local storage, caching/transformation, local display, redistribution/deployment, retention/deletion and dump reproducibility. Values are not copied into output.

Pass local paths with:

```bash
python -m scripts.probe_hithink_contracts \
  --offline-contract \
  --representative 600000.SH \
  --representative 000001.SZ \
  --representative 430001.BJ \
  --start-date 2026-07-01 \
  --end-date 2026-07-10 \
  --manifest-evidence D:/private/hithink-manifest.json \
  --rights-evidence D:/private/hithink-rights.json
```

## Live contract mode

The account owner may configure `HITHINK_FINANCE_API_KEY` locally and replace `--offline-contract` with `--allow-network`. Live mode permits only the reviewed ticker list, trading calendar, three single-symbol unadjusted historical-bar calls and the recent-dump link contract. It validates the HTTPS dump link and immediately discards it; it never downloads or parses the dump.

HTTP success and business-envelope success are validated separately. Known validation, authentication, permission, data-state, rate-limit, timeout and upstream-unavailable codes are classified. Unknown codes fail closed. Transport exceptions are reported without raw exception text.

Probe output does not authorize a REST adapter, market-dump importer, provider fallback or production ingestion.
