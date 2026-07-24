# Issue #223 Task Snapshot — Today Market THS Source Sync

## Authority

- Governing Issue: #223.
- Product roadmap: #137.
- Related accepted architecture: Issue #219 / PR #220 and Issue #221 / PR #222.
- Required exact base: `8e6cce15df9b327e5dbe1afa1ae420e253af1f68`.
- Risk tier: **Strict Architecture Preflight**.
- Project-owner authorization recorded on 2026-07-24: synchronize the revised plan and proceed with the next development step.

This task authorizes architecture and governance documentation only. It does not authorize production Provider code, live application network access, credentials, database schema, migration, dependency changes, fixtures containing Provider values, scheduler behavior, implementation Issue creation, merge, release, tag or version change.

## Objective

Prospectively supersede the Tushare source candidate selected by PR #222 with:

```text
source_key = ths-account-structured-provider-v1
```

Preserve PR #222 as historical governance evidence. Do not rewrite history to imply that THS was the original selected candidate.

## Accepted non-secret validation evidence

Owner-supplied local validation completed at `2026-07-24T14:59:47Z`:

```text
transport = curl.exe + Schannel + HTTP/1.1
authentication = X-api-key
api_key_status = confirmed
cookie_used = false
browser_session_used = false
raw_provider_response_persisted = false
security_scan = passed
p0_report_sha256 = b1b0648a33dcd677c91430370d20d22a83cc2eb88c227c54a418f570302451f1
transport_v3_sha256 = 544d9a63aaa50fcca4a6629274df8009bbbb99de3ea1911db578375c9622569e
```

Confirmed entitlements:

```text
a_share_ticker_list
a_share_trading_calendar
a_share_daily_history_raw
a_share_index_ticker_list
a_share_index_daily_history
ths_industry_index_catalog
ths_concept_index_catalog
ths_index_current_constituents
limit_up_pool
limit_up_ladder
hot_stock_list
stock_anomaly_reasons
```

Unsupported or undocumented:

```text
ths_index_historical_constituents
dated_membership_supported = false
```

No secret, account identifier, request identifier or actual market value may be introduced into this task, repository, Issue or PR.

## Locked source policy

```text
preferred_provider_candidate = ths-account-structured-provider-v1
tushare_provider = deferred_by_owner_decision
akshare_adapter = deferred_by_owner_decision
runtime_provider_fallback = disabled
cross_provider_row_mixing = prohibited
browser_session_batch_download = prohibited
production_implementation_authorized = false
```

## Required architecture decisions

1. Preserve the accepted PR #222 invariants:
   - render the prior complete local snapshot first;
   - calendar-based completed-session detection;
   - at most 10 automatically missing completed sessions;
   - explicit user confirmation for initialization and larger catch-up;
   - atomic complete-snapshot publication;
   - retain prior snapshot on every failure;
   - no daemon, scheduler, continuous polling, push or post-shutdown work.
2. Replace Tushare-specific capability mapping with THS-specific mapping without creating a generic multi-provider runtime.
3. Split the delivery plan into bounded stages:
   - THS Provider foundation and index-led market overview;
   - full-market daily acquisition only after a bounded batch contract is reviewed;
   - adjusted-return features only after corporate-action entitlement and semantics are reviewed;
   - historical sector breadth remains unavailable while dated membership is unsupported.
4. Keep current sector membership separate from historical membership.
5. Keep hot-list and anomaly-reason records in a market-attention candidate layer only.
6. Treat Provider use, local retention and sanitized fixture retention as contract gates, not owner preferences.
7. Record quota, concurrency, retry, completion time, units, revisions and key lifecycle as unresolved until non-secret evidence exists.
8. Do not mandate production shell-out to curl merely because curl proved local transport reachability.

## Revised implementation sequence candidate

```text
A. Issue #223 architecture synchronization
B. Close non-secret use/retention, quota and semantic gates
C. Strict implementation: THS Provider Foundation + Index Market Overview
D. Strict implementation: bounded full-market daily acquisition
E. Strict implementation: corporate actions and adjusted multi-session analytics
F. Historical sector breadth only if dated membership becomes available
```

Stage C candidate scope after all gates close:

```text
source authorization/capability revisions
runtime-only credential reference boundary
trading calendar
core index identities and daily bars
industry/concept index catalogs and index bars
current constituent display
limit-up pool and ladder within documented meaning
hot stock and anomaly reason as market-attention candidates
refresh attempts, validation and atomic publication
prior snapshot retention and ordinary-Chinese status projection
```

Stage C exclusions:

```text
full-market individual-security daily refresh
historical sector breadth
current-member backfill into history
adjusted 5/20/60-session returns
60-session high/low rules
full-market exact up/down-limit price claims
commercial redistribution
runtime Provider fallback or row mixing
```

## Authorized file families

- `.codex/tasks/issue-223-today-market-ths-source-sync-preflight.md`
- `docs/today_market_ths_source_sync_preflight.md`
- `docs/ths_today_market_capability_manifest.md`
- optional focused documentation synchronization explicitly within Issue #223

No production code may change.

## Required validation

Before fixed-head review:

- confirm merge base remains exactly `8e6cce15df9b327e5dbe1afa1ae420e253af1f68`;
- confirm the complete diff is documentation-only and secret-free;
- confirm no Provider values, credentials, account identifiers or request identifiers are present;
- confirm no production code, schema, migration, dependency or workflow file changes;
- run repository documentation and existing local checks as applicable;
- record the exact immutable HEAD and validation result in the PR.

## Required fixed-head review phrase

```text
AUTHORIZED TODAY MARKET THS SOURCE SYNC PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

Any new commit invalidates prior fixed-head CI and review evidence.

## Completion gate

The architecture must end in exactly one of:

```text
ready_for_separate_strict_implementation_issue
blocked_pending_retention_or_use
blocked_pending_contract_facts
blocked_required_capability_not_entitled
```

At task creation the correct state is:

```text
overall_gate = blocked_pending_retention_or_use
production_implementation_authorized = false
```

Architecture approval or merge does not authorize an implementation Issue. A separate project-owner instruction is required.