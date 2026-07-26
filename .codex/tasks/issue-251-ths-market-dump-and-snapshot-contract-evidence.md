# Issue #251 — THS Full-Market Snapshot and Market Dump Contract Evidence

## Authority

- Project-owner authorization on 2026-07-26: `启动 Today Market Automatic Daily Refresh — Daily Prices, Market Overview and Sector Strength`.
- Linked Issue: #251.
- Parent contract gate: #225.
- Product Roadmap: #137.
- Accepted automatic-refresh architecture: #221 / merged PR #222.
- Accepted THS source synchronization: #223 / merged PR #224.
- Accepted THS Stage C0: #227/#229 and #230/#231.
- Exact branch base: `fcecc3446847ceca0f595c7737323b721ea86ce4`.
- Branch: `docs/ths-market-dump-contract-evidence-20260727`.
- Risk tier: **Strict External Contract Evidence Amendment**.
- Workflow authority: `.codex/WORKFLOW.md`.

## Objective

Record current official Fuyao documentation for full-market snapshot pagination and full-market Parquet dump acquisition without inferring undocumented account entitlement, production authentication, numeric quota, completion time, correction/revision behavior or API-key lifecycle.

This slice narrows acquisition-shape uncertainty. It does not authorize production Provider code, live requests, credentials, browser Cookie replay, schema/migration, Provider-valued fixtures, ingestion, UI work, a Stage C implementation Issue, release, tag or version change.

## Evidence boundary

Official public sources observed on 2026-07-27:

```text
https://fuyao.aicubes.cn/llms-full.txt
https://fuyao.aicubes.cn/docs/introduction/
https://fuyao.aicubes.cn/docs/quickstart/
https://fuyao.aicubes.cn/docs/api-reference/market-dumps/
```

Canonical secret-free evidence excerpt SHA-256:

```text
0520898bee90dd97ce17f9403e2c1c54b2cf5e33da888c8af4c927b138610c01
```

No account-visible content, credential, account identifier, request ID, pre-signed URL or Provider market value may be retained.

## Accepted candidate determinations

```text
current_full_market_snapshot_contract = documented_publicly
current_full_market_snapshot_pagination = limit_offset_thscode_ascending
full_market_daily_k_10y_dump_contract = documented_publicly
full_market_daily_k_recent_10_trading_days_dump_contract = documented_publicly
full_market_adjustment_factor_dump_contract = documented_publicly
daily_k_natural_key = (thscode, date_ms)
adjustment_event_natural_key = (thscode, ex_date_ms)
daily_k_timezone = Asia/Shanghai
daily_k_currency = CNY
daily_k_volume_unit = shares
daily_k_turnover_unit = original_currency
dump_presigned_link_ttl = usually_5_minutes
business_code_4001 = agreed_qps_exceeded
api_key_management = create_named_key_list_manage_delete
```

## Required fail-closed interpretation

```text
dump_download_documented_ui_auth = login_cookie
production_dump_api_key_auth_contract = unresolved
browser_cookie_replay = prohibited
current_account_dump_entitlement = unresolved
numeric_qps_limit = unresolved
daily_total_limit = unresolved
concurrency_limit = unresolved
limit_scope = unresolved
dataset_completion_time = unresolved
correction_revision_late_data_behavior = unresolved
stable_source_update_timestamp = unresolved
api_key_expiry = unresolved
api_key_inactivity_expiry = unresolved
maximum_active_keys = unresolved
revocation_effect_time = unresolved
rotation_contract = unresolved
```

A documented endpoint or dump does not establish implementation readiness when the documented one-click path uses browser login Cookie or when account limits and chronology remain unknown.

## Gate outcome

```text
historical_full_market_gap_fill_contract = candidate_documented_not_implementation_ready
recent_full_market_incremental_contract = candidate_documented_not_implementation_ready
current_full_market_snapshot_contract = documented_not_implementation_ready
quota_gate = blocked
completion_and_revision_semantics_gate = blocked
production_implementation_authorized = false
overall_gate = blocked_quota_contract
```

The controlling #225 state remains fail closed. No Stage C implementation Issue may be created from this evidence amendment.

## Authorized files

Exactly:

```text
.codex/tasks/issue-251-ths-market-dump-and-snapshot-contract-evidence.md
docs/ths_market_dump_and_snapshot_contract_evidence_20260727.md
```

No accepted document is rewritten. The new evidence file has focused precedence only for facts it explicitly resolves.

## Offline evidence golden path

1. Pin exact official URLs and observation date.
2. Record only public endpoint, pagination, dump, schema, key, unit, timezone and authentication-category facts.
3. Verify the canonical evidence excerpt hash.
4. Separate documented data shape from account entitlement and production authentication readiness.
5. Preserve numeric quota, completion, revision and key-lifecycle facts as unresolved.
6. Verify the diff contains exactly two Markdown files and no secrets, Provider values, executable code or runtime configuration.
7. Keep live Stage C and automatic refresh unauthorized.

## Primary failure path

If a fact is absent from official public documentation, retain `unresolved`. Do not infer:

- API-key support for a download flow documented through browser login Cookie;
- numeric QPS from business code `4001`;
- completion or correction semantics from timestamps or successful calls;
- account entitlement from endpoint visibility;
- safe startup cadence from a short-lived pre-signed URL.

## Validation

- exact base-to-head inventory;
- exactly two authorized Markdown files;
- Markdown structure and repository-link review;
- canonical evidence excerpt SHA-256 check;
- secret and Provider-value scan;
- no production code, dependency, workflow, schema, migration or fixture change;
- no live request or credential use;
- zero unresolved review threads;
- fixed-head review containing exactly:

```text
AUTHORIZED THS MARKET DUMP AND SNAPSHOT CONTRACT EVIDENCE APPROVED at fixed head <FULL_HEAD_SHA>
```

## Stop conditions

Stop if work would require:

- API keys, account identifiers, private support content or pre-signed URLs;
- browser Cookie/session replay;
- Provider-valued public fixtures;
- load testing or hidden-limit probing;
- production network access, code, schema or migration;
- creation of a Stage C implementation Issue;
- modification of frozen PR #241;
- merge, Issue closure, release, tag or version change without separate owner authorization.

Any new commit invalidates prior fixed-head validation and review.