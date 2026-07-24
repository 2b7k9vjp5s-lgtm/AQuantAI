# Today Market Automatic Daily Refresh — Architecture Preflight

## 1. Decision status

- Governing Issue: #221.
- Product Roadmap: #137.
- Related THS gate: Issue #219 / merged PR #220.
- Required base: `16e21bc6e4e8f233ea6ed0a73b011619dad6449d`.
- Risk tier: **Strict Architecture Preflight**.
- Architecture only; no production code, migration, credential or live access is authorized.

The selected source candidate is the official Tushare Pro API under one source-specific contract:

```text
source_key = tushare-pro-daily-market-v1
```

The final architecture gate is:

```text
blocked_pending_tushare_account_facts
```

This preflight chooses a bounded candidate and closes the intended product, ownership, chronology, calculation and failure semantics. It does not claim that public documentation proves the project owner's account entitlement, automated-access right, exact host contract, retention right, quota or production fixture reachability.

A separate Strict implementation Issue must not be created until the companion capability manifest is completed with reviewed non-secret owner/account evidence and the gate is changed through a new fixed-head architecture review.

## 2. Ordinary-user product outcome

The Today Market page must answer:

> 今天市场怎么样，哪些方向值得看，当前看到的数据是什么日期，是否更新成功？

The future accepted path is:

```text
open application or first enter Today Market
  -> render the latest complete published local snapshot immediately
  -> check one exact configured scope once
  -> determine the latest expected completed trading session
  -> request only bounded missing sessions
  -> validate and append immutable source observations
  -> compute one versioned market/sector result
  -> atomically publish one new complete snapshot
  -> update the page without blocking navigation
```

On every failure:

```text
keep the prior complete snapshot visible
  -> preserve the failed attempt and redacted diagnostics
  -> show a readable Chinese state and next action
  -> perform no hidden retry or source fallback
```

No startup path may leave the page blank while network work is pending.

## 3. Locked automation boundary

### 3.1 Allowed future automatic behavior

The only automatic-network exception is one configured Today Market scope:

1. after one-time source setup and explicit persistent consent;
2. at application startup or first Today Market entry, whichever happens first;
3. once per application process and scope revision;
4. only after the prior valid local snapshot has been rendered;
5. only for a reviewed bounded stale-data plan;
6. only for missing completed daily sessions;
7. at most one documented transient retry when the source contract explicitly permits it;
8. no work after application shutdown.

Persistent consent is a non-secret append-only revision such as:

```text
auto_refresh_on_start = true
auto_refresh_consent_version = aquantai.today-market-auto-refresh-consent.v1
```

Changing or revoking consent creates a new revision. Consent does not authorize any other Provider, research, announcement, AI or background-network behavior.

### 3.2 Explicitly excluded

- operating-system scheduler, daemon, service worker or continuous poller;
- push notifications, alert center or background reminders;
- automatic full-history bootstrap on startup;
- per-stock remote request loops during startup;
- hidden Provider fallback, source blending or row mixing;
- browser replay, Cookie/session reuse, reverse-engineered signatures or undocumented endpoints;
- automatic evidence, Industry Map, beneficiary, thesis or Investment Candidate acceptance;
- automatic Canonical Price replacement;
- target price, expected return, position sizing, simulated holdings, broker or trading behavior.

## 4. Repository investigation and ownership findings

### 4.1 Existing local snapshot architecture

The accepted Today Market Phase 2A path is:

```text
IngestionRun + complete persisted source rows
  -> exact equity / benchmark / sector series identities
  -> MarketCockpitRepository / BenchmarkRepository / SectorRepository
  -> MarketCockpitService deterministic calculations
  -> non-persistent Today Market projection
  -> Chinese-first page
```

The following owners remain authoritative:

| Meaning | Existing owner | Decision |
|---|---|---|
| Provider rows, ingestion status and source chronology | market-data persistence | Reuse ownership; do not create a second market-data domain. |
| Listed Instrument identity | existing Listed Instrument owner | Provider symbols remain candidates until explicitly reviewed. |
| Canonical Price and purpose eligibility | Canonical Price / Comparison Eligibility | Automatic daily refresh never promotes or replaces canonical price. |
| Market overview, liquidity and price behavior calculations | existing Market Cockpit calculators/service | Extend through versioned deterministic contracts rather than duplicate UI calculations. |
| Today Market labels and progressive details | Today Market projection | Presentation only; no hidden calculation ownership. |
| Industry thesis, beneficiary and evidence meaning | existing research/evidence owners | Market movement never establishes industry causality or beneficiary status. |
| Valuation and Investment Candidate history | existing accepted owners | No automatic recomputation or historical rewrite. |

### 4.2 Why the legacy complete-snapshot identity cannot own automatic refresh

The current `IngestionRun` contract accepts only:

```text
snapshot_mode = complete
```

The current equity/benchmark/sector `series_key` identities freeze moving fields including:

- exact requested end date;
- exact stock/index/sector code set;
- exact source endpoint compatibility;
- exact adjustment policy.

Therefore each new end date or universe change produces a different immutable series identity. That is correct for historical complete imports but not sufficient as the ordinary user's stable automatic-refresh scope.

Decision:

- do not weaken, mutate or reinterpret the existing complete-snapshot identity;
- do not turn `IngestionRun` into an in-place incremental ledger;
- preserve existing local snapshot reads and historical reproducibility;
- introduce a stable Today Market scope identity plus append-only exact dataset revisions in a later authorized migration;
- project one exact published dataset revision into the existing Market Cockpit calculation owner through a bounded adapter.

### 4.3 Missing current semantics

The current runtime does not own:

- source authorization/capability revisions for automatic startup access;
- immutable raw Provider response objects;
- stable incremental Today Market scope identity;
- append-only provider correction revisions;
- dated stock-to-sector membership intervals;
- automatic refresh attempts and publish state;
- full-market limit-price observations;
- one versioned hotspot-state rule owner.

These are candidate additions only. No migration is implemented by this preflight.

## 5. Source selection

### 5.1 Selected candidate

The first candidate is Tushare Pro because the official documentation exposes distinct interfaces for the exact bounded families needed by the first ordinary-user slice:

| Product need | Candidate official interface | Required fields/meaning |
|---|---|---|
| Stock identity candidates | `stock_basic` | exact `ts_code`, exchange/market/security status, list/delist chronology and names; never accepted identity by source assertion alone |
| Trading calendar | `trade_cal` | exchange, calendar date, open state and prior trading date |
| A-share daily market | `daily` | exact code/date, OHLC, previous close, change, percentage change, volume and amount |
| Adjustment continuity | `adj_factor` | exact code/date/factor revisions; append-only source observation |
| Core indices | `index_daily` | exact index/date OHLCV and amount |
| Daily limit prices | `stk_limit` | exact code/date, previous close, upper limit and lower limit |
| Shenwan definitions | `index_classify` | exact source taxonomy code/name/level/version |
| Dated Shenwan membership | `index_member_all` | exact member code and `in_date` / `out_date` intervals across levels |

Public documentation reviewed on 2026-07-24 states, among other contract candidates:

- `daily` is an unadjusted daily interface;
- suspended securities do not produce ordinary daily rows for the suspended session;
- `daily.vol` is documented in lots and `daily.amount` in thousand yuan;
- `index_member_all` exposes dated membership fields;
- `stk_limit` exposes exact daily upper/lower prices rather than requiring a fixed-percentage guess;
- published point thresholds and call limits vary by interface and account level.

These are public contract candidates, not account entitlement evidence.

### 5.2 Product-level neutrality and runtime specificity

The ordinary product uses neutral language such as `数据源`, `更新状态` and `权限不足`. The runtime implementation, migration and fixture contract must remain source-specific for the first path.

Rejected:

- a generic multi-provider framework before one complete source path exists;
- automatic fallback to THS, AKShare, BaoStock, webpages or another Provider;
- mixing Tushare rows with another Provider inside one dataset revision;
- calling an aggregation library the authoritative source when its upstream contract differs.

### 5.3 Deferred source families

The first implementation candidate excludes:

- concept/theme membership and concept indices;
- hot-list or causal-reason text;
- intraday/minute/tick data;
- margin, northbound, dragon-tiger and fund-flow data;
- financial statements and announcements;
- automatic research or evidence linkage.

The first sector path is limited to one exact source taxonomy:

```text
Shenwan 2021 Level 1 industry
```

Any concept path requires a separate dated-membership contract and separate authorization.

## 6. Capability readiness

### 6.1 Required ready capabilities

The first implementation may not begin unless all required capabilities are `implementation_ready`:

1. source authorization and credential mechanism;
2. `stock_basic` identity candidates;
3. `trade_cal` calendar;
4. `daily` A-share bars;
5. `adj_factor` revisions;
6. `index_daily` for the selected core-index set;
7. `stk_limit` for exact daily limit prices;
8. `index_classify` for the exact Shenwan taxonomy version;
9. `index_member_all` for dated membership intervals;
10. one complete sanitized success/error fixture package reachable through the reviewed production contract.

### 6.2 Deterministic readiness predicate

A capability is `implementation_ready` only when every required fact is reviewed as `confirmed` or validly `not_applicable`:

- exact account entitlement;
- permitted automated personal use;
- permitted local retention and reproducibility;
- exact HTTPS host;
- exact method, API name/path and credential placement category;
- request/response schema and reviewed date/version;
- selector, pagination, ordering and terminal conditions;
- quota, concurrency, reset time and documented retry guidance;
- stable record/symbol identity;
- field units, null semantics, chronology and timezone;
- correction, late-arrival, deletion and revision behavior;
- production-reachable sanitized fixtures.

Otherwise choose exactly one:

- `deferred_not_entitled`;
- `deferred_contract_incomplete`;
- `rejected_undocumented`;
- `blocked_retention_or_use`.

The overall architecture remains blocked when any required capability is not ready.

## 7. Stable Today Market scope

### 7.1 Scope identity

A stable scope represents the user's product selection, not one acquired result. Its identity excludes moving data-through dates and the latest observed code set.

Candidate canonical scope payload:

```json
{
  "scope_schema": "aquantai.today-market-scope.v1",
  "source_key": "tushare-pro-daily-market-v1",
  "source_authorization_revision_id": "<exact>",
  "capability_revision_ids": ["<exact required revisions>"],
  "market_scope": "cn_a_share_primary_v1",
  "exchange_namespaces": ["SSE", "SZSE", "BSE"],
  "security_types": ["domestic_common_equity"],
  "daily_adjustment_policy": "raw_plus_exact_adjustment_factor",
  "core_index_codes": [
    "000001.SH",
    "399001.SZ",
    "399006.SZ",
    "000300.SH",
    "000905.SH",
    "000852.SH"
  ],
  "sector_taxonomy": "shenwan_2021",
  "sector_level": "L1",
  "market_rule_version": "aquantai.today-market-market-rules.v1",
  "sector_rule_version": "aquantai.today-market-sector-rules.v1",
  "anomaly_rule_version": "aquantai.today-market-anomaly-rules.v1",
  "auto_refresh_consent_revision_id": "<exact>"
}
```

Exact index codes and security-type field mappings remain capability-manifest facts. No code-prefix rule establishes security type or exchange.

### 7.2 Ordinary-user configuration

The ordinary settings surface shows only:

- data source status;
- whether an account capability profile is reviewed;
- whether startup daily refresh is enabled;
- last complete data date;
- last update result;
- a user-triggered `立即检查更新` action;
- a user-triggered `补齐历史数据` action when the gap exceeds the automatic ceiling.

Hosts, API names, credential profile keys, revision IDs, hashes and schema details remain under advanced technical details.

## 8. Initialization versus automatic increment

### 8.1 User-triggered initialization

A new installation has no prior complete snapshot. The first baseline may be materially larger than a normal daily increment and therefore is never hidden inside application startup.

Required behavior:

```text
no complete snapshot
  -> show 未初始化
  -> explain required source/account state
  -> user activates 初始化今日市场数据
  -> show bounded scope/date plan before network
  -> require explicit remote confirmation
  -> acquire and validate the baseline
  -> atomically publish the first complete snapshot
```

The architecture candidate baseline needs at least:

- 61 completed trading sessions for 60-session anomaly rules;
- 21 completed sessions for 20-day sector/risk calculations;
- a calendar range covering the requested history and a forward safety window;
- dated sector membership covering the complete calculation period;
- exact mapped instrument coverage and disclosed exclusions.

A later implementation Issue must set explicit request/day/row/byte ceilings. It may split a user-confirmed baseline into deterministic bounded pages without publishing a partial snapshot.

### 8.2 Automatic increment ceiling

After initialization, automatic startup refresh may cover at most:

```text
10 missing completed trading sessions
```

If the gap is larger:

- retain the prior snapshot;
- state `需要手动补齐`;
- generate no automatic large request;
- offer a user-triggered catch-up plan with explicit remote confirmation.

The ceiling is a product safety boundary, not a Provider quota inference.

## 9. Trading calendar and staleness

### 9.1 Calendar owner

One exact reviewed `trade_cal` capability revision owns source calendar observations. The accepted local calendar projection remains append-only and source-specific.

No wall-clock weekday guess substitutes for the calendar.

### 9.2 Latest expected completed session

For one exact scope revision:

1. convert the application clock to the reviewed exchange timezone, expected to be `Asia/Shanghai` only after confirmation;
2. ensure local calendar coverage includes today and a forward safety window;
3. use the exact open sessions from the reviewed calendar;
4. use the capability manifest's reviewed `daily_complete_after_local_time`;
5. when today is open but the completion time has not passed, select the previous open session;
6. when today is open and the completion time has passed, select today;
7. when today is closed, select the latest prior open session;
8. never select a partial/current session merely because some rows exist.

If calendar coverage or the completion-time contract is missing, return `calendar_or_completion_contract_unavailable` and make no daily request.

### 9.3 Staleness states

- `current` — published snapshot data-through equals the expected completed session;
- `no_new_trading_day` — calendar confirms no later completed session;
- `stale_bounded` — 1–10 completed sessions are missing;
- `stale_requires_manual_catchup` — more than 10 sessions are missing;
- `calendar_stale` — expected session cannot be determined safely;
- `not_initialized` — no complete published snapshot exists;
- `source_not_ready` — capability gate is not ready.

### 9.4 Concurrency and idempotency

- one in-process refresh lock per exact scope revision;
- a second page entry observes the current attempt rather than creating another;
- one request fingerprint per exact capability revision, selector, fields, page and date;
- exact raw duplicates are idempotent;
- changed content creates a new append-only revision;
- application restart may retry only when no succeeded/terminal attempt exists for the same exact plan and the automatic attempt ceiling has not been consumed for that process.

## 10. Request planning

### 10.1 Request shape

The preferred daily acquisition pattern is by completed trading date, not by stock:

```text
one all-market daily request per missing trade_date
one all-market adjustment-factor request per missing trade_date
one all-market limit-price request per missing trade_date
one request per core-index date/window under its documented contract
```

This avoids an unbounded per-stock request loop.

Calendar, stock identity and sector membership requests are generated only when their exact local coverage or revision validity requires them.

### 10.2 Required plan fields

Every request plan freezes:

- exact source authorization revision;
- exact capability revision;
- exact approved HTTPS host;
- API/endpoint contract key;
- exact selector and requested fields;
- exact missing date/page;
- timeout and byte/row ceilings;
- credential profile key label, never its secret;
- deterministic request fingerprint;
- reason for acquisition;
- whether the attempt is automatic startup or explicit user action.

### 10.3 Retry

- authentication, permission, schema, validation and retention errors: no retry;
- quota/rate-limit errors: no same-attempt retry;
- documented transient transport error: at most one retry when the reviewed source contract permits it;
- no alternate host or Provider;
- no exponential background loop.

## 11. Raw capture and chronology

### 11.1 Immutable raw objects

Each response is retained as one immutable source-specific L0 object with:

- exact source/capability/attempt revisions;
- request fingerprint;
- API/endpoint contract key;
- selector/page/date identity;
- media type, byte length and SHA-256;
- source response status/error code after redaction;
- fetched-at UTC and locally recorded-at UTC;
- schema/document review version;
- exact parser/adapter version;
- no private header, token, account identifier or credential-bearing content.

Candidate project ceilings:

- 10 MiB per raw response object;
- 50 MiB aggregate raw bytes per automatic refresh attempt;
- oversized responses fail without truncation or partial publication.

Final ceilings must be lower when the reviewed Provider contract requires it.

### 11.2 Separate times

Keep separate:

- source effective/trade date;
- source update time when documented;
- response fetched-at UTC;
- local recorded-at UTC;
- dataset information cutoff;
- snapshot published-at UTC.

Provider timestamps never replace local recording chronology.

## 12. Instrument identity

### 12.1 Candidate only

`stock_basic.ts_code` and documented exchange/security fields may create one deterministic Provider instrument candidate.

They may not automatically create or change an accepted Listed Instrument.

Rejected identity inputs:

- security-code prefix guessing;
- fuzzy company-name matching;
- industry or concept membership;
- latest daily-row presence;
- LLM inference.

### 12.2 New and changed instruments

When a new, changed or conflicting Provider instrument has no accepted mapping:

- preserve the candidate and exact source provenance;
- create a local pending-review item;
- exclude it from accepted company-linked projections;
- disclose the excluded count and coverage impact;
- do not call the remaining universe `全A股` unless the exact accepted coverage rule is satisfied;
- do not block rendering of the prior valid snapshot.

Automatic refresh never performs identity acceptance.

## 13. Daily-price, unit and adjustment semantics

### 13.1 Raw daily bars

The first source contract treats `daily` as raw/unadjusted source observation.

Required normalized source fields:

- exact instrument candidate/mapping reference;
- trade date;
- open/high/low/close;
- source previous close;
- source change and percentage change;
- source volume plus original unit;
- source amount plus original unit;
- source record identity/fingerprint;
- raw response reference;
- fetched/recorded chronology.

### 13.2 Units

Public candidate semantics currently describe:

- volume: lots (`手`);
- amount: thousand yuan (`千元`).

A future adapter may derive normalized values only through an exact versioned formula:

```text
amount_cny = Decimal(source_amount_thousand_cny) * 1000
```

Share-volume conversion requires a reviewed board-lot contract. Until confirmed, retain the source unit and do not silently label it shares.

All persisted numeric normalization uses Decimal rules defined by the implementation Issue. Source float fidelity remains visible in provenance.

### 13.3 Suspensions and missing rows

A missing daily row is not automatically zero return or zero amount.

For each expected mapped instrument/session, classify one of:

- valid traded row;
- documented suspension/no-trade;
- not yet listed;
- already delisted under accepted chronology;
- missing unexpectedly;
- invalid/duplicate;
- pending identity mapping.

Only valid traded rows enter return and activity denominators. Every excluded count is exposed.

### 13.4 Adjustment factors

Adjustment factors are append-only source observations. No existing historical daily row is overwritten.

For multi-session total return, the candidate deterministic price basis is:

```text
factor_price_t = raw_close_t * adj_factor_t
return(a, b) = factor_price_b / factor_price_a - 1
```

The multiplicative factor normalization cancels inside a return ratio. This formula remains ineligible until the exact `adj_factor` contract, correction behavior and Decimal rule are reviewed and fixture-proven.

One-day market breadth may use a deterministic close-versus-source-pre-close calculation when both values are valid. Source `pct_chg` is retained for comparison and validation, not blindly trusted when it conflicts beyond a fixed tolerance.

### 13.5 Corrections

- exact raw duplicate: idempotent;
- same source identity and same normalized values: link to existing observation;
- same source identity with changed content: append a correction revision;
- source-declared late arrival/correction: preserve declaration;
- no last-write-wins overwrite;
- historical published snapshots remain frozen to exact prior revisions;
- a new corrected snapshot is published only through a new deterministic refresh/recompute attempt.

## 14. Limit-up and limit-down counts

Fixed percentages are not a complete A-share limit-price rule because boards, special-treatment state and listing chronology can differ.

Decision:

- use exact `stk_limit.up_limit` and `stk_limit.down_limit` only after that capability is reviewed and ready;
- compare valid close against the exact source limit price using one Decimal tick/tolerance contract;
- do not use hot-list reason text or a third-party limit pool as the deterministic owner;
- if limit-price coverage is incomplete, show `涨跌停统计暂不可用` rather than estimate;
- limit counts are market-state observations only and never create a catalyst or industry conclusion.

## 15. Index semantics

The first scope contains a fixed ordinary-user core-index list owned by the Today Market scope revision.

Each index requires:

- exact Provider index identity;
- exact accepted display label;
- daily row completeness for the expected session;
- explicit amount/volume unit semantics;
- exact information cutoff and local recording boundary.

Missing one optional index may be displayed as unavailable only if the scope contract marks it optional. Missing a required index prevents publication of a complete new snapshot.

Index values never act as Canonical Price for a listed company.

## 16. Industry taxonomy and dated membership

### 16.1 Source taxonomy

The first sector path uses only:

```text
source = Tushare Pro
classification = Shenwan 2021
level = L1
```

Source definitions do not create an Industry Map or beneficiary status.

### 16.2 Membership intervals

A source membership record becomes one source interval candidate:

```text
member instrument
sector code
in_date inclusive
out_date exclusive when present
source record/revision
fetched/recorded chronology
```

Exact interval boundary semantics must be confirmed by the capability manifest and fixture. Current membership must never be carried backward.

When historical intervals do not cover a calculation date:

```text
historical_membership_unavailable
```

The sector calculation for that date is unavailable; the implementation may not substitute today's members.

### 16.3 Membership corrections

Changed membership content is append-only. Published historical snapshots remain bound to the exact membership revision used at publication.

## 17. Deterministic market rules v1

Rule key:

```text
aquantai.today-market-market-rules.v1
```

### 17.1 Eligible universe

For one session, the eligible denominator contains only exact accepted scope members with:

- accepted Listed Instrument mapping;
- accepted active listing chronology for the date;
- one valid non-duplicate daily row or an explicit documented no-trade state;
- no unresolved source identity conflict.

The result exposes:

- configured scope count;
- mapped active count;
- valid traded count;
- documented no-trade count;
- missing/invalid count;
- pending identity count;
- coverage ratio.

A full-market label requires the future implementation to define and satisfy an exact coverage predicate. Otherwise the UI says `已映射A股范围` and displays the coverage ratio.

### 17.2 Market breadth

For every valid traded row:

```text
one_day_return = close / pre_close - 1
```

Use Decimal and one fixed epsilon corresponding to the reviewed source price precision.

Classify:

- advancing: return > epsilon;
- declining: return < -epsilon;
- unchanged: otherwise;
- unavailable: excluded from the traded denominator with reason.

Expose counts, valid denominator, advance ratio and breadth balance. Never impute unavailable instruments.

### 17.3 Turnover

```text
market_turnover_cny = sum(valid normalized amount_cny)
```

Expose excluded/missing count and amount coverage. Do not combine amounts with different unresolved units.

### 17.4 Market strength summary

The ordinary summary is deterministic text generated from disclosed components, not an LLM opinion.

Candidate bands:

- `偏强`: advance ratio >= 0.60 and breadth balance >= 0.20;
- `偏弱`: advance ratio <= 0.40 and breadth balance <= -0.20;
- `震荡`: otherwise;
- `数据不足`: valid traded coverage below 0.80 or required components unavailable.

The exact thresholds are rule-version constants and are shown in technical details.

## 18. Deterministic sector rules v1

Rule key:

```text
aquantai.today-market-sector-rules.v1
```

### 18.1 Eligible sector/session

One sector/session is eligible when:

- dated membership is available;
- at least 5 mapped active members exist;
- at least 80% of mapped active members have valid required return inputs;
- no unresolved taxonomy identity conflict exists.

Unavailable sectors retain exact reasons and never receive an imputed score.

### 18.2 Components

For each eligible sector:

- `sector_return_1d`: median eligible member one-day return;
- `sector_return_5d`: median eligible member factor-price 5-session return;
- `sector_return_20d`: median eligible member factor-price 20-session return;
- `relative_1d/5d/20d`: sector median minus same-session eligible-market median;
- `breadth_1d`: positive eligible members / eligible members;
- `activity_ratio`: current sector normalized amount / median prior-20-session sector amount;
- `coverage_ratio`: eligible members / mapped active members.

Use median returns to reduce single-stock dominance. Amount remains additive. No market-cap weighting is introduced in v1.

### 18.3 Percentile calculation

Within the same exact session and eligible sector set:

- use deterministic midrank percentile;
- ties share the same midrank;
- missing components remain missing;
- no winsorization, clipping or imputation;
- fewer than 10 eligible sectors makes hotspot classification unavailable.

### 18.4 Composite strength

Expose every component and calculate:

```text
strength_score =
    0.30 * percentile(relative_1d)
  + 0.30 * percentile(relative_5d)
  + 0.20 * percentile(relative_20d)
  + 0.15 * percentile(breadth_1d)
  + 0.05 * percentile(activity_ratio)
```

The score is a market-strength descriptor, not an investment recommendation. It may never hide its components or missing-data state.

### 18.5 Primary hotspot state

Use the following ordered deterministic rules:

1. `高位分化`
   - percentile(relative_20d) >= 0.80; and
   - percentile(relative_1d) < 0.40 or breadth_1d < 0.45.
2. `降温`
   - prior-session strength_score percentile >= 0.80; and
   - current strength_score percentile < 0.50; and
   - breadth_1d < 0.50.
3. `新出现`
   - current strength_score percentile >= 0.80; and
   - percentile(relative_1d) >= 0.80; and
   - prior-session strength_score percentile < 0.60.
4. `持续强化`
   - current strength_score percentile >= 0.80; and
   - percentile(relative_5d) >= 0.80; and
   - current strength_score - prior-session strength_score >= 0.10; and
   - breadth_1d >= 0.60.
5. `扩散`
   - current strength_score percentile >= 0.70; and
   - breadth_1d >= 0.65; and
   - breadth_1d minus its value five sessions earlier >= 0.15.
6. `一般`
   - no earlier rule matches.

When required prior-session/window inputs are unavailable, only rules whose complete inputs exist may be evaluated. The UI shows the missing reason.

### 18.6 Representative companies

Representative companies are market examples, not beneficiary conclusions.

Select at most three per sector by deterministic ordering:

1. valid member one-day return descending;
2. current normalized amount descending;
3. exact Listed Instrument ID ascending.

Expose the reason: `当日涨幅和成交活跃度代表`. Do not use LLM selection or causal labels.

## 19. Deterministic daily anomaly rules v1

Rule key:

```text
aquantai.today-market-anomaly-rules.v1
```

An anomaly is a price/volume observation only. It never creates an explanation, catalyst, evidence grade or research candidate.

For one valid mapped instrument:

- `大幅波动`: absolute one-day return >= 7%;
- `明显放量`: current source volume / median prior-20 valid-session volume >= 2.0, with at least 15 valid prior sessions;
- `60日新高`: current factor price > every prior 60 valid-session factor price;
- `60日新低`: current factor price < every prior 60 valid-session factor price;
- `明显跳空`: absolute(open / pre_close - 1) >= 3%;
- `持续相对强势`: member 5-session return minus eligible-market median 5-session return >= 5 percentage points and member 20-session return minus market median >= 10 percentage points.

Rules use exact versioned thresholds and disclose required history. Suspended, invalid, duplicate, unmapped or insufficient-history rows do not produce anomalies.

## 20. Refresh state machine

### 20.1 Internal states

```text
not_configured
source_contract_blocked
not_initialized
rendering_prior_snapshot
checking_calendar
current_no_action
refresh_planned
refreshing
validating
computing
publishing
succeeded
partial_acquisition_not_published
authentication_failed
permission_denied
credential_expired
quota_exhausted
source_unavailable
schema_changed
validation_failed
calendar_unavailable
manual_catchup_required
prior_snapshot_retained
```

Every terminal failure records a reason code and redacted diagnostics. Partial acquisition may persist immutable raw/source observations but never publishes a mixed or incomplete Today Market snapshot.

### 20.2 Ordinary-Chinese projection

| Internal state | Ordinary text |
|---|---|
| `not_configured` | 未配置数据源 |
| `source_contract_blocked` | 数据源权限尚未确认 |
| `not_initialized` | 尚未初始化今日市场数据 |
| `checking_calendar` | 正在检查是否有新交易日数据 |
| `current_no_action` | 已是最新 / 今日非交易日 / 暂无新数据 |
| `refreshing` | 正在更新缺失日线 |
| `succeeded` | 更新成功 |
| `manual_catchup_required` | 缺失数据较多，需要手动补齐 |
| `authentication_failed` / `credential_expired` | 凭据失效，请重新配置 |
| `permission_denied` | 当前账户权限不足 |
| `quota_exhausted` | 今日额度不足，已保留上次数据 |
| `source_unavailable` | 数据源暂不可用，已保留上次数据 |
| `schema_changed` / `validation_failed` | 数据校验失败，已保留上次数据 |
| `partial_acquisition_not_published` | 部分获取失败，未替换完整数据 |
| `calendar_unavailable` | 无法确认最新交易日，未执行更新 |

The page always shows the retained snapshot's exact data date beside the refresh state.

## 21. Atomic dataset and publication contract

### 21.1 Dataset revision

One immutable dataset revision freezes:

- stable Today Market scope revision;
- exact source authorization/capability revisions;
- exact acquisition attempt and raw-object set;
- exact accepted Listed Instrument mapping revision set;
- exact calendar revision;
- exact daily-bar, adjustment-factor, index, limit-price, sector-definition and membership revisions;
- requested missing-session range;
- effective data-through session;
- information cutoff and local recorded-UTC boundary;
- field/unit/adapter versions;
- completeness and coverage diagnostics.

### 21.2 Calculation revision

One deterministic calculation revision freezes:

- exact dataset revision;
- market, sector and anomaly rule versions;
- exact eligible/excluded universe diagnostics;
- all component values and missing reasons;
- deterministic output fingerprint.

### 21.3 Published snapshot

Publishing is one atomic pointer/revision append:

```text
scope revision
  -> exact complete dataset revision
  -> exact succeeded calculation revision
  -> published-at UTC
```

A new snapshot is publishable only when all scope-required families and calculations succeed. Optional display components remain explicitly unavailable. No partial attempt replaces the prior pointer.

Historical reads bind exact published snapshot revision and dual-as-of boundaries. They never resolve to a newer compatible-looking dataset.

## 22. Candidate persistence boundary

A future source-specific migration may propose the following append-only families:

### 22.1 Tushare source contract and raw acquisition

1. `tushare_source_authorization_revisions`;
2. `tushare_capability_revisions`;
3. `tushare_acquisition_attempts`;
4. `tushare_raw_response_objects`;
5. `tushare_instrument_candidates`;
6. `tushare_trade_calendar_observations`;
7. `tushare_daily_bar_observations`;
8. `tushare_adjustment_factor_observations`;
9. `tushare_index_daily_observations`;
10. `tushare_limit_price_observations`;
11. `tushare_sw_sector_definition_revisions`;
12. `tushare_sw_membership_interval_revisions`.

### 22.2 Product-domain refresh and publication

13. `today_market_scope_revisions`;
14. `today_market_auto_refresh_consent_revisions`;
15. `today_market_refresh_attempt_revisions`;
16. `today_market_dataset_revisions`;
17. `today_market_calculation_revisions`;
18. `today_market_published_snapshot_revisions`.

The final implementation migration may use fewer tables when one table preserves the same ownership and append-only contract. It may not collapse secrets, source raw bytes, accepted identity, deterministic calculations and published snapshots into one mutable record.

Credential values remain outside the database. Only a non-secret credential profile key label and existence/status projection may be stored.

## 23. Migration, rollback and downgrade

Architecture candidate only:

- additive tables and indexes;
- no change to legacy `IngestionRun`, daily-price, benchmark, sector or Canonical Price rows;
- no backfill from existing AKShare/local snapshots into Tushare source observations;
- no automatic promotion of existing `stock_basic` codes into accepted Listed Instrument mappings;
- deployment rollback disables the new feature flag and returns Today Market to the accepted local-only read path;
- populated downgrade refuses before dropping any source, dataset, calculation or publication revision;
- empty downgrade may remove only tables created by the exact migration;
- application code must tolerate the feature being absent or disabled without blanking the existing local snapshot page.

## 24. Future command and service boundaries

Candidate explicit commands for a later implementation:

```text
python -m scripts.review_tushare_daily_market_capability_manifest ...
python -m scripts.plan_today_market_initialization --scope-key <exact> --dry-run
python -m scripts.initialize_today_market --scope-key <exact> --confirm-remote
python -m scripts.plan_today_market_refresh --scope-revision-id <exact> --dry-run
python -m scripts.refresh_today_market --scope-revision-id <exact> --confirm-remote
python -m scripts.inspect_today_market_refresh --attempt-revision-id <exact>
```

The startup service may execute only the already-consented bounded refresh plan. Initialization and gaps above the automatic ceiling remain explicit commands/UI actions with remote confirmation.

Reads remain local and network-free:

```text
GET /today-market/api/status
GET /today-market/api/snapshot?published_snapshot_revision_id=<exact>
GET /today-market/api/history?...dual-as-of boundaries...
```

Exact route names remain implementation candidates. Ordinary page rendering never triggers an unbounded or hidden read-time network path.

## 25. Offline validation contract

All tests, CI and fixture demos remain zero-network.

Required future fixtures:

- reviewed source/account capability manifest with no secret;
- prior complete published snapshot;
- deterministic Asia/Shanghai clock and calendar;
- one missing completed-session success set;
- no-new-trading-day set;
- more-than-10-session manual-catchup set;
- suspension and missing-row cases;
- adjustment-factor correction case;
- new unmapped instrument case;
- dated membership entry/exit case;
- duplicate and changed-content cases;
- 401/403/429 and credential-expiry redacted errors;
- schema drift and unknown-field response;
- partial family failure proving no publication;
- successful full calculation and atomic publication;
- application shutdown/cancellation proving no background continuation.

Network-denial guards must fail tests if startup, import, read, migration, CI or demo attempts a socket/HTTP call outside the explicitly injected fake transport.

A real smoke test is:

- disabled by default;
- excluded from CI;
- explicit local invocation only;
- limited to one reviewed capability and bounded selector;
- requires a credential profile outside repository/database/logs;
- requires explicit remote confirmation;
- never writes downloaded Provider data into GitHub artifacts.

## 26. Production-realistic offline golden path

1. A completed non-secret manifest marks all required capabilities `implementation_ready`.
2. One exact active source authorization, capability set, scope and consent revision exist.
3. A prior complete snapshot through session `D0` is visible immediately.
4. The reviewed calendar and clock determine `D1` as the only missing completed session.
5. Dry-run emits exact bounded `daily`, `adj_factor`, `index_daily`, `stk_limit` and any required metadata/membership plans without network.
6. Sanitized fixtures bind to the exact production contract revisions.
7. Raw bytes, hashes, request fingerprints and chronology are appended.
8. Provider instrument candidates resolve only through exact accepted Listed Instrument mappings; one unmapped new listing is preserved and disclosed, not auto-accepted.
9. Daily, calendar, index, limit and sector interval observations validate under exact units and chronology.
10. One complete dataset revision through `D1` is created.
11. Market, sector and anomaly rules calculate deterministically with complete component diagnostics.
12. One snapshot is atomically published and becomes visible under exact dual-as-of boundaries.
13. The prior snapshot remains reproducible.
14. No Canonical Price, Evidence Ledger, Industry Map, beneficiary, Company Research, valuation, Investment Candidate, recommendation, portfolio or trading state changes.

## 27. Primary failure path

When any required account/source fact is unknown, the architecture remains blocked and no implementation Issue is opened.

After implementation readiness, when any runtime request or validation fails:

1. preserve every permitted immutable raw/source revision already received;
2. mark the exact refresh attempt terminal with a redacted reason;
3. create no complete dataset/calculation revision when required families are incomplete;
4. do not change the published snapshot pointer;
5. continue showing the prior snapshot and its date;
6. show the ordinary-Chinese failure state and one permitted user action;
7. perform no hidden retry, probing, alternate host or Provider fallback.

## 28. Security and secret boundary

Never place any of the following in chat, GitHub, repository, database, fixture, log, screenshot or error text:

- token/API key;
- account identifier;
- private request header;
- credential-bearing URL or request body;
- Cookie/session/CAS ticket;
- unrestricted downloaded Provider dataset;
- local secret-storage path that reveals account identity.

Redaction happens before persistence and before error serialization. Request fingerprints exclude secret values and private headers.

## 29. Locked exclusions and stop conditions

Stop and return for project-owner review if architecture or implementation would require:

- guessing or probing entitlement, quota, host, endpoint, units or revision behavior;
- browser replay, reverse engineering or undocumented access;
- current membership represented as historical membership;
- partial coverage represented as full-market coverage;
- source text or LLM inference owning identity, causality or accepted research state;
- generic fallback or mixed-source revisions;
- network in tests, CI, migrations, ordinary reads or fixture demos;
- a scheduler, daemon, continuous poller, notification or work after application close;
- automatic Canonical Price, Evidence Ledger, Industry Map, beneficiary, valuation or candidate mutation;
- recommendation, target price, expected return, holdings, position sizing, broker or trading behavior;
- release, tag or version change.

## 30. Final readiness result

```text
selected_source_candidate = tushare-pro-daily-market-v1
architecture_gate = blocked_pending_tushare_account_facts
implementation_issue_authorized = false
live_network_authorized = false
credential_setup_authorized = false
migration_authorized = false
```

Missing evidence is enumerated in `docs/tushare_daily_market_capability_manifest_template.md`.

The next permitted action after this architecture PR is fixed at its immutable final HEAD is:

1. documentation validation and complete diff inventory;
2. process-independent fixed-head architecture review using:

```text
AUTHORIZED TODAY MARKET AUTOMATIC DAILY REFRESH PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

3. resolution of all review threads;
4. separate explicit project-owner authorization before merge.

Architecture merge alone does not authorize production implementation. The source/account gate must be closed through reviewed non-secret evidence and a separately authorized Strict implementation Issue.
