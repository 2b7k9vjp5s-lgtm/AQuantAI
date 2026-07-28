# Today Market Automatic Daily Refresh v1 — Architecture Preflight

## 1. Status, authority and decision

This document is the Strict Architecture Preflight for Issue #270.

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
default_branch = main
exact_base = 2295bcf71968f0e00d88cd0a8fa5775060079995
architecture_issue = #270
parent_roadmap = #137
risk_tier = Strict Architecture Preflight
branch = arch/today-market-automatic-daily-refresh-v1
```

Project-owner authority on 2026-07-28 is limited to starting Issue #270 architecture
work and creating a Draft PR containing only the authorized architecture documents.
It does not authorize production implementation, source activation, credentials,
network access, schema/migration, tests/fixtures, release work, Issue closure or
merge.

The accepted product target is the first Roadmap #137 daily user job:

> 打开应用，立即看到最近完整市场状态；如果日行情过期，自动、有限、可解释地补齐缺失交易日，并刷新市场强弱、板块热点和个股异动。

The architecture outcome is intentionally split between a **complete product and
calculation design** and a **fail-closed live source gate**:

```text
architecture_contract = defined
preferred_source_candidate = ths-account-structured-provider-v1
live_source_contract_state = blocked_quota_contract
core_daily_market_live_gate = blocked_source_contract
company_action_gate = blocked_source_contract
historical_dated_membership_gate = blocked_source_contract
production_live_network_authorized = false
production_implementation_authorized = false
```

This means the architecture can be reviewed and accepted as a deterministic target,
but no live acquisition implementation may be inferred from it while the source
contract remains blocked.

PR #241 remains closed, Draft, unmerged and permanently read-only at exact HEAD
`3116a67ec472131eea3bf3d1bd9daee884c69ee9`.

---

## 2. Accepted predecessor architecture that remains authoritative

Issue #270 is not a greenfield redesign. It converges already accepted Today Market
work into a production-target architecture.

### 2.1 Automatic-refresh product architecture

Issue #221 / merged PR #222 established the durable product invariants:

```text
render prior complete snapshot first
calendar-based completed-session detection
at most 10 automatically missing completed sessions
explicit initialization / larger catch-up
one bounded automatic attempt
atomic publication only
retain prior valid snapshot on failure
no daemon / scheduler / continuous polling / push
```

PR #222 originally selected `tushare-pro-daily-market-v1` as a historical candidate.
That source decision was later prospectively superseded; PR #222 remains historical
governance evidence and is not silently rewritten.

### 2.2 Accepted source synchronization

Issue #223 / merged PR #224 prospectively selected:

```text
preferred_provider_candidate = ths-account-structured-provider-v1
tushare_provider = deferred_by_owner_decision
akshare_adapter = deferred_by_owner_decision
runtime_provider_fallback = disabled
cross_provider_row_mixing = prohibited
```

Accepted non-secret account/capability evidence established candidate support for
listed A-share identities, a trading calendar, raw A-share daily history, index
history, THS industry/concept catalogs and current constituents. Historical dated
constituents remained unsupported or undocumented. Corporate-action entitlement
was not closed.

### 2.3 Final THS external-contract resolution

Issue #225 / merged PR #265 closed the live THS gate with focused precedence:

```text
retention_gate = closed_for_documented_local_normalized_storage
fixture_policy = resolved_synthetic_only
retry_reference_contract = confirmed_from_official_client
quota_gate = blocked
completion_and_revision_semantics_gate = blocked
api_key_lifecycle_gate = blocked
production_dump_authentication_gate = blocked
production_implementation_authorized = false
overall_gate = blocked_quota_contract
resolution_mode = explicit_fail_closed
```

Therefore Issue #270 **must not reactivate THS** merely because transport,
authentication shape or some entitlements were previously demonstrated. It also
must not roll back to Tushare or AKShare without a separate owner-authorized source
architecture revision.

### 2.4 Provider-neutral acquisition and Mock

Accepted PRs #254 and #256 provide a provider-neutral application seam and a
zero-network deterministic Mock. The Mock is engineering infrastructure only.
It cannot:

- prove source entitlement;
- populate live quotas or completion facts;
- become canonical market truth;
- authorize credentials or network access;
- close Issue #225;
- justify Provider-valued repository fixtures.

### 2.5 Runtime integration

Issue #259 / PR #260 and Issue #261 / PR #262 established the current runtime
contract:

```text
runtime_scope_owner = runtime_scope_revision_id
runtime_status_owner = runtime_status_fingerprint
prior_snapshot_identity = server-owned and exact
GET runtime status = zero acquisition / zero write
POST runtime command = closed DTO
same-scope concurrent command = single-flight
completed identical command = replay without reacquisition
first eligible Mock entry = at most one bounded attempt
failure/cancellation = retain prior persisted snapshot
browser polling = prohibited
runtime identity in localStorage = prohibited
```

The default application remains Mock-disabled and performs zero acquisition.

Issue #270 preserves these runtime semantics. It does not relax the current
Mock-only `TodayMarketRefreshPlan` into a live plan.

---

## 3. Repository ownership findings

The current repository already has the main deterministic and persistence owners
needed for a large part of P0-A.

### 3.1 Existing normalized market-data owner

`backend.database.models.IngestionRun` already owns:

```text
batch_identifier
series_key
series_identity
provider
dataset
requested_start_date
requested_end_date
information_cutoff_date
provider_request_metadata
adapter_version
snapshot_mode = complete
contract_version
status = pending | succeeded | failed
row_count_received
row_count_written
dataset_counts
error_summary
```

Existing normalized families include:

```text
StockBasicRecord
DailyPriceRecord
TradeCalendarRecord
BenchmarkIndexDailyRecord
SectorDefinitionRecord
SectorDailyRecord
```

`IngestionRun.batch_identifier` is therefore the first candidate for binding all
component runs produced by one future refresh attempt. The architecture does not
create a second generic market-data domain.

### 3.2 Existing deterministic calculation owner

`MarketCockpitService` already loads exact persisted equity/benchmark/sector series
and delegates deterministic calculations to existing calculators.

The accepted Market Cockpit currently provides or already contains useful
building blocks for:

- latest-session advancing / declining / unchanged counts;
- advance ratio and breadth balance;
- 20-session and 60-session breadth/new-high/new-low proxies;
- volume and amount participation;
- 20-/60-session price behavior and volatility diagnostics;
- benchmark context;
- sector index 1-/5-/20-session returns, SMA20 distance, volatility and drawdown;
- exact provenance and alignment diagnostics.

Issue #270 extends this deterministic ownership through **versioned rules**; the
browser must not duplicate calculations.

### 3.3 Missing production-grade families

Current generic market persistence does not provide a first-class accepted owner
for all of the following required semantics:

```text
company-action / exact adjustment-factor revisions
exchange reference-close / exact daily price-limit semantics
effective-dated sector/theme constituent membership
source authorization / account capability revision as durable market-data authority
```

This architecture may identify those gaps. It does **not** authorize a table or
migration. A future Strict Implementation Issue must decide whether to add a new
normalized family, reuse a proven existing owner, or narrow its product slice.

---

## 4. Product path and architecture layers

The target ordinary-user flow is:

```text
open / first eligible Today Market entry
  -> read exact last valid complete local snapshot
  -> render it immediately
  -> build exact runtime scope over local snapshot + selected source contract revision
  -> determine expected latest completed trading session
  -> compute exact missing completed sessions
  -> current? stop with zero network
  -> not initialized? require explicit initialization
  -> >10 missing sessions? require explicit manual catch-up
  -> 1..10 missing sessions? one bounded automatic attempt
  -> acquire only the exact requested sessions/families
  -> validate identity / chronology / units / completeness / source consistency
  -> append immutable source observations
  -> resolve one coherent complete publication candidate
  -> calculate deterministic market / sector / anomaly results
  -> atomically make the candidate readable as the new last valid snapshot
  -> preserve exact older snapshots for historical reopen
```

On every failure:

```text
last_valid_snapshot remains visible
candidate_new_snapshot is not published
refresh diagnostics are exposed
no hidden source switch
no hidden retry loop
no accepted research state changes
```

The architecture has five layers:

1. source authorization and capability gate;
2. acquisition planning and immutable source observations;
3. coherent publication identity;
4. deterministic market calculations;
5. source-neutral ordinary-user projection.

---

## 5. Source-capability decision table

### 5.1 Current candidate history

| Source | Current authority | Current state | May Issue #270 activate it? |
|---|---|---|---|
| Tushare Pro | historical PR #222 candidate | deferred by accepted owner decision | No |
| THS Fuyao | superseding PR #224 preferred candidate | `blocked_quota_contract` by #225 | No |
| AKShare | deferred by accepted owner decision | not selected as canonical live source | No |
| synthetic Mock | accepted test/demo infrastructure | zero-network only | Only tests/demos, never market truth |

There is currently **no production-live eligible source**.

### 5.2 THS candidate capability matrix

The following table is architecture evidence, not runtime authorization.

| Required family/fact | Accepted candidate evidence | Gate for P0-A |
|---|---|---|
| listed A-share identity candidates | account capability previously confirmed | blocked by overall source contract |
| trading calendar | account capability previously confirmed | blocked by completion/overall contract |
| raw A-share daily history | account capability previously confirmed | blocked by quota/completion/revision contract |
| core index daily history | account capability previously confirmed | blocked by quota/completion/revision contract |
| industry/concept index catalogs and history candidates | previously mapped/documented | blocked by overall source contract |
| current constituents | previously confirmed | display-only current membership; not historical breadth |
| historical dated constituents | unsupported/undocumented | **blocking for constituent-confirmed historical sector strength** |
| corporate action / adjustment | endpoint shape documented; account entitlement/semantics not closed | **blocking for exact adjusted cross-session metrics** |
| local normalized retention | closed for documented local normalized research storage | allowed only after source activation is otherwise authorized |
| public Provider-valued fixture | prohibited | synthetic/schema-only |
| numeric QPS / daily total / concurrency | unresolved | **blocked** |
| data-completion cutoff | unresolved | **blocked** |
| correction/revision/late-arrival behavior | unresolved | **blocked** |
| API-key lifecycle | unresolved | **blocked** |
| production dump API-key authentication/entitlement | unresolved | **blocked** |

Result:

```text
source_capability_decision = preserve_ths_candidate_but_fail_closed
source_gate_code = blocked_source_contract
source_gate_detail = blocked_quota_contract
alternate_source_fallback = none
```

### 5.3 Host and credential-reference boundary

Accepted historical THS documentation identifies the candidate host family and
`X-api-key` authentication shape. Issue #270 records that only as contract history.
It does not place a credential in application configuration or authorize a call.

A future production implementation, after a new source-contract amendment, must
use an opaque **credential reference**, not the secret value, in application
state. Secret values may exist only in a local secret boundary outside GitHub,
fixtures, normalized market rows, logs, screenshots and chat.

A source contract revision must bind at minimum:

```text
source_key
source_contract_revision_id
approved_host_family
authentication_mechanism
credential_reference_kind
entitled_capability_families
quota_contract_revision
completion_policy_revision
correction_revision_policy
retention_policy_revision
```

Unknown required fields fail closed.

---

## 6. Exact market scope and identities

### 6.1 Today Market scope

A future live scope is conceptually:

```text
TodayMarketScopeV1 = {
  source_contract_revision_id,
  instrument_universe_revision_id,
  trading_calendar_revision_id,
  benchmark_role_bindings,
  sector_taxonomy_revision_id,
  membership_policy_revision_id,
  analysis_price_policy_revision_id,
  market_rule_version,
  sector_rule_version,
  anomaly_rule_version,
  prior_snapshot_id,
  dual_as_of_boundaries
}
```

The existing server-owned `runtime_scope_revision_id` remains the sole runtime
scope identity. A live implementation must derive it from the exact closed scope
payload; it may not add a second competing scope fingerprint.

### 6.2 Listed-instrument identity

Provider symbols are source observations/candidates. Canonical Today Market equity
membership uses the existing accepted listed-instrument identity owner.

Rules:

- no automatic identity acceptance from same code/name;
- exchange is part of identity;
- duplicate/conflicting source identity blocks the affected snapshot;
- the expected active universe is effective-dated;
- delisted/not-yet-listed instruments are not silently counted as missing;
- suspension/no-trade is distinct from a missing Provider row;
- full-market scope claims require exact expected-universe accounting.

### 6.3 Benchmark roles

Ordinary-user reads should use stable semantic roles such as:

```text
broad_market
large_cap
growth
technology_or_other_configured_role
```

Each role binds to one exact source instrument identity in the source-contract
revision. The architecture does not hardcode a new Provider ticker into UI code.

### 6.4 Sector/theme identity

A sector/theme series must bind:

```text
source_key
classification_system
classification_level
sector_code
sector_definition_revision_id
effective taxonomy period
```

Same-name sectors from different taxonomies are not interchangeable.

---

## 7. Trading calendar, session completion and freshness

### 7.1 Source of truth

Freshness uses the reviewed trading calendar plus a reviewed **session completion
policy**. It must never use `today - last_date` as the canonical rule.

Required contract:

```text
calendar_timezone
open_session_dates
session_close_time
source_data_completion_rule
correction_or_late_arrival_rule
```

The accepted runtime timezone remains `Asia/Shanghai` only when the selected
source contract confirms that market/session interpretation.

### 7.2 Expected latest completed session

Given an exact planning timestamp `T`:

```text
eligible_calendar_sessions(T) =
  open sessions whose market session has ended AND whose source completion rule
  says canonical daily data should be available by T

expected_latest_complete_trading_date = max(eligible_calendar_sessions(T))
```

If the completion rule is unknown:

```text
refresh_state = blocked_source_contract
network_attempt = none
prior_snapshot = retained
```

Issue #225 leaves THS completion semantics unresolved, so the current live path
cannot compute this value authoritatively from THS.

### 7.3 Local latest complete session

`latest_complete_local_trading_date` comes only from the exact last valid coherent
Today Market snapshot, not from the newest row found in any one dataset.

### 7.4 Missing sessions

```text
missing_trading_dates =
  sorted open sessions s where
  latest_complete_local_trading_date < s <= expected_latest_complete_trading_date
```

Decision:

```text
0 sessions  -> current / zero acquisition
1..10       -> acquisition_required / one bounded automatic attempt
>10         -> manual_catchup_required
no prior snapshot -> not_initialized / explicit initialization
```

The automatic ceiling remains exactly 10 completed sessions, preserving accepted
architecture and the existing Mock planner.

### 7.5 Automatic trigger

The selected v1 automatic trigger is the **first eligible Today Market entry after
the prior snapshot has rendered and an exact scope exists**.

FastAPI import/startup and raw static page loading continue to perform no network
acquisition. `APPLICATION_START` may remain a domain trigger vocabulary value,
but it cannot bypass explicit scope resolution or prior-snapshot-first rendering.

---

## 8. Acquisition plan and source batch

### 8.1 Current Mock plan remains Mock-only

The existing `TodayMarketRefreshPlan` verifies
`assumption_profile_id = aquantai.today-market.mock-planning-assumption.v1`.

That strictness is preserved. A future live adapter must not achieve production
readiness by changing that constant or marking Mock provenance Provider-confirmed.

A live path requires a separately reviewed contract such as a future
`SourceSpecificDailyRefreshPlanV1` with its own source-contract identity and quota
bounds.

### 8.2 Bounded request planning

A future live plan must contain exact closed fields equivalent to:

```text
runtime_scope_revision_id
refresh_attempt_id
trigger
prior_snapshot_id
source_contract_revision_id
requested_completed_sessions
required_family_set
per-family request bounds
information_cutoff
planning_recorded_at_utc
plan_contract_version
plan_fingerprint
```

Client fields cannot select source, host, endpoint, credentials, quota or hidden
fallback.

### 8.3 One coherent batch identifier

All normalized `IngestionRun` components from one attempt should share one exact
`batch_identifier` derived from the server-owned refresh attempt.

This permits a coherent publication rule without inventing a second generic
market-ingestion owner.

Required component families for a target snapshot profile are explicit. A
production-target full profile is expected to need at least:

```text
listed_instrument_identity
trading_calendar
equity_daily_bar
benchmark_daily_bar
sector_definition
sector_daily_bar
analysis_price_adjustment_or_reference_close
sector_dated_membership
```

A future implementation may define a narrower core profile, but it must never
label unavailable constituent-confirmed hotspot or adjusted anomaly sections as
complete.

---

## 9. Immutable daily-bar and company-action semantics

### 9.1 Raw daily observation

The minimum source observation is conceptually:

```text
DailyBarObservationV1 = {
  source_key,
  source_contract_revision_id,
  instrument_id,
  source_instrument_id,
  exchange,
  trading_date,
  open,
  high,
  low,
  close,
  volume,
  amount,
  source_unit_contract,
  source_record_identity_or_natural_key,
  ingestion_run_id,
  batch_identifier,
  observed_at_or_recorded_at_utc,
  validation_state
}
```

Raw bars are immutable per exact source revision/run. A later Provider correction
creates a new immutable revision/run; it does not update historical rows in place.

### 9.2 Units

Volume and amount units are source-contract facts. They are normalized only after
an exact source unit contract is bound. UI and calculators consume normalized
units and retain source provenance.

### 9.3 Analysis-price policy

Cross-session calculations use:

```text
analysis_price_policy_version = aquantai.today-market-analysis-price.v1
```

The policy requires one of:

1. an exact source-defined adjusted series with immutable revision identity; or
2. raw close plus exact company-action/adjustment-factor revisions sufficient to
   reproduce an adjusted/reference-close series.

The derived `analysis_close` is a calculation result; it never replaces raw close.

If a corporate action intersects a required window and exact adjustment/reference
semantics are missing:

```text
metric_state = insufficient_adjustment_semantics
```

There is no silent fallback to incompatible raw closes.

### 9.4 One-session exchange limit semantics

Exact limit-up/limit-down counts require authoritative daily limit-price or exact
exchange reference-close/rule semantics. The architecture must not infer a universal
10%/20% threshold because board, ST, IPO and other rules vary.

If the selected source contract cannot supply exact semantics:

```text
limit_up_count.status = unsupported_limit_semantics
limit_down_count.status = unsupported_limit_semantics
```

---

## 10. Dated sector/theme membership

### 10.1 Membership interval contract

Constituent-confirmed sector metrics require effective-dated membership:

```text
SectorMembershipRevisionV1 = {
  source_key,
  classification_system,
  sector_id,
  instrument_id,
  effective_from_session,
  effective_to_session_exclusive | null,
  source_revision_identity,
  recorded_at_utc
}
```

For trading session `t`, a member is eligible only when:

```text
effective_from_session <= t < effective_to_session_exclusive
```

when an end boundary exists.

### 10.2 Current constituents are not historical membership

The accepted THS source evidence currently includes current constituents but not
historical dated constituents. Therefore:

```text
current_constituent_display = potentially representable after source activation
historical_constituent_breadth = blocked
historical_representative_company_strength = blocked
historical_sector_relative_stock_anomaly = blocked
```

A present-day constituent list must never be applied backward to D0/D1 history.

### 10.3 Sector index price metrics remain separate

Sector index daily history may support exact sector-index price metrics such as
1-/5-/20-session return. Those metrics are not by themselves proof of
constituent-confirmed breadth or spreading.

The read model therefore separates:

```text
sector_price_metrics
sector_constituent_metrics
hotspot_state
```

If dated membership is unavailable, `sector_price_metrics` may be readable from an
otherwise authorized source, but `hotspot_state` is `insufficient_coverage` when
the claimed state requires constituent confirmation.

---

## 11. Atomic publication and last-valid-snapshot rule

### 11.1 Three distinct states

The server maintains a conceptual distinction:

```text
last_valid_snapshot
refresh_attempt_state
candidate_new_snapshot
```

Only `last_valid_snapshot` is ordinary-user market truth.

### 11.2 Component run eligibility

A component can participate in a new snapshot only when:

```text
IngestionRun.status = succeeded
snapshot_mode = complete
batch_identifier = exact refresh batch
provider/source = exact selected source
information_cutoff_date = target data-through session
series identity = expected exact scope
normalized rows = validation complete
no duplicate/conflicting natural keys
```

A failed/partial family cannot be hidden by successful families.

### 11.3 Publication eligibility

A candidate snapshot becomes eligible only if every family required by its exact
`snapshot_profile_revision` is complete and mutually consistent.

```text
candidate.data_through_session = target session
all required component runs use one batch_identifier
all component source keys agree
all chronology bounds agree
all exact identities resolve
calculation inputs meet rule-version coverage requirements
```

Until then, the read path keeps the prior snapshot.

### 11.4 No silent delete of failed evidence

A failed acquisition may leave a failed `IngestionRun` and redacted diagnostics.
That evidence does not become a published snapshot and must not rewrite the prior
successful source history.

---

## 12. Deterministic snapshot identity and historical reopen

### 12.1 Snapshot contract

A complete Today Market snapshot is identified by canonical content equivalent to:

```text
TodayMarketSnapshotIdentityV1 = {
  snapshot_contract_version,
  source_key,
  source_contract_revision_id,
  batch_identifier,
  data_through_session,
  equity_ingestion_run_id,
  calendar_ingestion_run_id,
  benchmark_ingestion_run_ids,
  sector_definition_ingestion_run_id,
  sector_daily_ingestion_run_id,
  adjustment_revision_identity,
  dated_membership_revision_identity,
  market_rule_version,
  sector_rule_version,
  anomaly_rule_version,
  dual_as_of_boundaries
}

today_market_snapshot_id = sha256(canonical_json(identity))
```

Only fields actually present in the exact snapshot profile are included; absence is
explicit and changes profile/completeness rather than being inferred.

### 12.2 Exact historical reopen

Historical reopen must bind to the exact snapshot identity/components. It may not
select:

- a newer successful IngestionRun;
- a newer Provider correction;
- newer adjustment factors;
- current sector membership;
- a newer rule version;
- a different source contract revision.

A historical request that cannot resolve all exact components fails closed with a
local integrity error rather than falling back to latest.

### 12.3 New persistence decision

Issue #270 does not require a new publication table as an architecture assumption.
The first implementation candidate should attempt to derive exact coherent snapshot
identity from existing `IngestionRun` components plus exact rule revisions.

If implementation review proves that durable atomic publication/indexing cannot be
achieved safely or efficiently without a new persisted publication owner, that is a
stop condition requiring an explicit schema/migration Issue. It is not implicitly
authorized here.

---

## 13. Market overview rule contract

### 13.1 Rule identity

```text
market_rule_version = aquantai.today-market-market-overview.v1
return_epsilon = 1e-12
```

The v1 architecture extends existing Market Cockpit formulas rather than replacing
them with browser logic.

### 13.2 Eligible universe accounting

For session `t`:

```text
expected_active_count = effective-dated active listed instruments in scope
accounted_count = valid traded rows + explicit no-trade/suspension states
missing_source_count = expected_active_count - accounted_count
identity_conflict_count = exact unresolved/conflicting identities
```

Full source coverage requires:

```text
missing_source_count = 0
identity_conflict_count = 0
```

A suspended/no-trade instrument is accounted for but is not a valid return
observation.

Metric coverage is separately reported:

```text
return_coverage_ratio = valid_return_count / expected_active_count
```

The headline market-state classifier requires:

```text
return_coverage_ratio >= 0.90
no calendar conflict
no identity conflict
```

Otherwise:

```text
market_state = insufficient_coverage
```

The exact numerator/denominator and unavailable reason counts are always shown in
technical details.

### 13.3 Latest-session return

For eligible instrument `i` with exact analysis/reference semantics:

```text
r1(i,t) = analysis_close(i,t) / analysis_close(i,previous_open_session) - 1
```

Classification:

```text
advancing = r1 > +1e-12
declining = r1 < -1e-12
unchanged = otherwise
```

### 13.4 Breadth

```text
advance_ratio = advancing / valid_return_count
breadth_balance = (advancing - declining) / valid_return_count
median_return = median(valid r1)
```

Existing Market Cockpit latest-session calculation remains the preferred owner.

### 13.5 20-session position breadth

For instruments with 20 valid analysis closes ending at `t`:

```text
ma20(i,t) = mean(last 20 analysis_close)
above_ma20(i,t) = analysis_close(i,t) > ma20(i,t)
new_high_20(i,t) = analysis_close(i,t) >= max(last 20 analysis_close)
new_low_20(i,t) = analysis_close(i,t) <= min(last 20 analysis_close)
```

Aggregate:

```text
above_ma20_ratio = above_ma20_count / eligible_20_count
new_high_20_ratio = new_high_20_count / eligible_20_count
new_low_20_ratio = new_low_20_count / eligible_20_count
```

No forward fill is allowed through missing required sessions.

### 13.6 Turnover/activity

```text
market_amount_t = sum(normalized amount for valid session-t equity rows)
market_amount_ratio_20 = market_amount_t / median(market_amount for previous 20 open sessions)
```

The ratio is unavailable unless the exact normalized universe and 20 prior sessions
are sufficiently complete under the same rule/source profile.

### 13.7 Core index returns

Each configured benchmark role exposes exact 1-/5-/20-session returns where history
is complete. Missing benchmark history affects that benchmark card; it does not
change equity breadth by fallback to another index.

### 13.8 Limit-up / limit-down

Counts are available only under exact daily limit semantics. They never use a
universal percentage heuristic.

### 13.9 Ordinary-user market state

When coverage is sufficient:

```text
strong if
  breadth_balance >= +0.20
  AND median_return > 0
  AND above_ma20_ratio >= 0.55

weak if
  breadth_balance <= -0.20
  AND median_return < 0
  AND above_ma20_ratio <= 0.45

mixed otherwise
```

Result vocabulary:

```text
strong
weak
mixed
insufficient_coverage
```

Turnover/activity is displayed as a separate dimension and does not override
breadth into an opaque composite market score.

---

## 14. Sector/theme strength and hotspot rules

### 14.1 Rule identity

```text
sector_rule_version = aquantai.today-market-sector-hotspot.v1
minimum_ranked_sector_count = 10
constituent_return_coverage_min = 0.90
constituent_ma20_coverage_min = 0.80
```

The same taxonomy and classification level are compared together. Industry and
concept groups are not ranked in one cross-section unless a future rule explicitly
says so.

### 14.2 Base sector metrics

For sector `s` at session `t`:

```text
sector_r1  = sector_index_close_t / prior_close - 1
sector_r5  = close_t / close_5_sessions_ago - 1
sector_r20 = close_t / close_20_sessions_ago - 1
sector_relative_5 = sector_r5 - broad_market_benchmark_r5
```

These use exact sector index history where authorized.

Constituent metrics require effective-dated membership:

```text
breadth_up_1 = advancing_members / valid_member_returns
breadth_above_ma20 = members_above_ma20 / eligible_member_ma20
sector_amount_t = sum(member amount at t)
activity_ratio_20 = sector_amount_t / median(previous 20 exact-session sector amounts)
new_high_20_share = member_new_high_20 / eligible_member_20
```

Representative-company diagnostic, where available:

```text
representative_set = top 3 members by median normalized amount over prior 20 sessions
representative_positive_share_5 =
  representatives with positive 5-session relative return / eligible representatives
```

This is a disclosed diagnostic, not an independent recommendation score.

### 14.3 Cross-sectional percentile

For metric `x` across `N >= 10` eligible sectors in the same taxonomy/level:

1. sort descending by metric value;
2. break exact value ties by `sector_code` ascending only to keep replay order stable;
3. `rank_pct = 1 - (rank - 1) / (N - 1)`.

Therefore top sector = 1 and bottom sector = 0.

Required percentiles:

```text
r1_pct
r5_pct
r20_pct
```

No missing value is imputed as zero.

### 14.4 Persistence diagnostic

For each of the last five sessions where ranking coverage is sufficient:

```text
strong_rank_session = r1_pct >= 0.60
strong_rank_sessions_5 = count(strong_rank_session)
```

### 14.5 Prior strong-state set

```text
STRONG_PRIOR_STATES = {
  new,
  strengthening,
  spreading,
  persistent_strong
}
```

`prior_state` always means the immediately preceding completed session calculated
with the **same sector rule version** and exact historical inputs.

### 14.6 State rules

Evaluation is deterministic and ordered. A higher-priority matching state wins.

#### Priority 1 — `insufficient_coverage`

Use when any core requirement fails:

```text
ranked sector count < 10
OR no exact dated membership for constituent-confirmed state
OR constituent_return_coverage < 0.90
OR required sector index windows are unavailable
OR exact taxonomy identity is ambiguous
```

A state-specific optional input may prevent only the state that requires it; it
must not be silently synthesized.

#### Priority 2 — `high_level_divergence`

```text
r20_pct >= 0.75
AND (r1_pct < 0.40 OR breadth_up_1 < 0.45)
AND activity_ratio_20 >= 1.00
```

Interpretation: medium-term rank remains high while current breadth/price action
has materially weakened under non-collapsing activity.

#### Priority 3 — `cooling`

```text
prior_state in STRONG_PRIOR_STATES
AND r5_pct < 0.50
AND breadth_up_1 < 0.50
```

#### Priority 4 — `spreading`

```text
r5_pct >= 0.70
AND r20_pct >= 0.65
AND breadth_up_1 >= 0.65
AND breadth_above_ma20 >= 0.60
AND new_high_20_share >= 0.10
```

#### Priority 5 — `new`

```text
prior_state not in STRONG_PRIOR_STATES
AND r1_pct >= 0.80
AND r5_pct >= 0.70
AND r20_pct < 0.60
AND breadth_up_1 >= 0.55
AND activity_ratio_20 >= 1.20
```

#### Priority 6 — `persistent_strong`

```text
r5_pct >= 0.70
AND r20_pct >= 0.70
AND breadth_above_ma20 >= 0.60
AND strong_rank_sessions_5 >= 3
```

#### Priority 7 — `strengthening`

```text
r5_pct >= 0.70
AND r20_pct >= 0.50
AND breadth_up_1 >= 0.55
AND (
  activity_ratio_20 >= 1.20
  OR breadth_above_ma20 >= 0.55
)
```

#### Priority 8 — `neutral`

All other sufficiently covered cases.

### 14.7 Missing optional components

If exact new-high inputs are unavailable, `spreading` cannot be claimed; a lower
state may still be evaluated if all of its required inputs are valid.

If dated membership is unavailable entirely, the full hotspot state is
`insufficient_coverage`; sector index 1/5/20 returns remain separately visible as
`sector_price_metrics` when source authority otherwise permits them.

### 14.8 Explainability

Each sector state returns:

```text
state
rule_version
matched_rule
component_values
component_thresholds
coverage
missing_inputs
prior_state
exact sector/taxonomy identity
```

The UI may translate labels but cannot recompute or override the state.

---

## 15. Deterministic stock anomaly rules

### 15.1 Rule identity

```text
anomaly_rule_version = aquantai.today-market-stock-anomaly.v1
```

All anomalies require exact listed-instrument identity and exact trading-session
alignment.

### 15.2 `large_move`

For valid adjusted/reference 1-session return `r1`:

```text
large_move if
  abs(r1) >= 0.07
  OR (
    abs_return_cross_section_percentile >= 0.975
    AND abs(r1) >= 0.04
  )
```

Cross-sectional percentile uses the same exact eligible market universe for `t`.

### 15.3 `unusual_volume`

Require current volume plus 20 previous valid traded-session volumes:

```text
volume_baseline_20 = median(previous 20 valid volumes)
volume_ratio_20 = volume_t / volume_baseline_20
unusual_volume = volume_ratio_20 >= 2.00
```

If baseline is zero/non-positive or history is incomplete, the anomaly is
unavailable rather than emitted.

### 15.4 `new_high` / `new_low`

Require 60 valid analysis closes ending at `t`:

```text
new_high = analysis_close_t >= max(last 60 analysis_close)
new_low  = analysis_close_t <= min(last 60 analysis_close)
```

Corporate-action ambiguity blocks these anomalies for affected windows.

### 15.5 `gap`

Require exact session `open_t` and exact adjusted/reference previous close:

```text
gap_return = open_t / reference_close_previous_session - 1
gap = abs(gap_return) >= 0.025
```

### 15.6 `persistent_relative_strength`

Require exact 5-session stock and broad-market benchmark returns:

```text
relative_return_5 = stock_r5 - broad_market_benchmark_r5
persistent_relative_strength if
  relative_return_5 >= 0.05
  AND stock_r5_cross_section_percentile >= 0.90
```

A negative-direction relative weakness rule is not added implicitly; a future rule
revision may add one explicitly.

### 15.7 `sector_relative_outlier`

Require exact dated sector membership at `t` and at least 10 eligible members.

```text
sector_median_r1 = median(member r1)
member_deviation = stock_r1 - sector_median_r1
MAD = median(abs(member r1 - sector_median_r1))
robust_z = 0.6745 * member_deviation / MAD

sector_relative_outlier if
  abs(member_deviation) >= 0.04
  AND abs(robust_z) >= 2.50
```

If `MAD = 0`, the robust-z test is unavailable and no sector-relative anomaly is
emitted from this rule.

### 15.8 Multiple anomalies and ordering

One instrument may carry multiple anomaly reason codes. No hidden composite score
is required.

Stable list order:

1. anomaly type in the fixed rule-contract order;
2. descending absolute primary metric;
3. stock code ascending as final tie-break.

### 15.9 Meaning boundary

An anomaly means only:

> 该股票在确定性价格/成交量规则下出现异常行为。

It does not mean:

- 原因已经确认；
- 产业逻辑成立；
- 值得买入；
- 是 Investment Candidate；
- 预期收益更高。

---

## 16. Market state and research state separation

The boundary is architectural, not merely UI wording:

```text
source observations
  -> deterministic Today Market calculations
  -> read-only market state

accepted research/evidence owners
  -> exact research explanation / thesis / beneficiary / candidate state
```

There is no automatic write edge from the first graph to the second.

If the Today Market page shows “已有研究解释”, it must resolve a pre-existing,
exact accepted research/evidence link under its own chronology. If no such link
exists, the anomaly remains “原因未确认 / 仅市场行为事实”.

No LLM may own market overview, sector state or anomaly classification. A future AI
feature may summarize already computed state only and remains separately governed.

---

## 17. Source-neutral read model

Ordinary-user Today Market reads should project source-neutral content:

```text
TodayMarketReadModelV1 = {
  snapshot_id,
  data_date,
  data_status,
  source_summary,
  coverage,
  refresh_state,
  market_state,
  core_indices,
  market_overview,
  sector_groups,
  stock_anomalies,
  research_link_summary,
  warnings,
  technical_details
}
```

### 17.1 `source_summary`

Ordinary view:

```text
source_label
last_complete_data_date
coverage_label
refresh_label
```

Advanced details may expose source contract revision/fingerprints but never secret
values.

### 17.2 `refresh_state`

Recommended source-neutral states:

```text
current
checking
refresh_required
refreshing
refreshed
not_initialized
manual_catchup_required
blocked_source_contract
failed_retained_prior
cancelled_retained_prior
```

### 17.3 `coverage`

At minimum:

```text
expected_instruments
accounted_instruments
valid_returns
no_trade_instruments
missing_source_rows
identity_conflicts
sector_count
sector_membership_coverage
history_window_coverage
unsupported_metric_reasons
```

### 17.4 `sector_groups`

The page groups exact deterministic states, for example:

```text
正在增强 = strengthening
新出现 = new
扩散 = spreading
持续强势 = persistent_strong
高位分化 = high_level_divergence
降温 = cooling
覆盖不足 = insufficient_coverage
```

`neutral` sectors may live below the first-screen focus list.

---

## 18. Ordinary-user page hierarchy

The target first screen is:

```text
1. 一句话市场状态 + 最新完整交易日 + 刷新状态
2. 核心指数 / 涨跌家数 / 市场宽度 / 成交活跃度
3. 正在增强 / 新出现 / 扩散 / 持续强势方向
4. 高位分化 / 降温方向
5. 有意义的个股异动
6. 数据覆盖与来源说明
7. 技术细节（折叠）
```

Rules:

- Chinese-first;
- one visually dominant refresh/retry action appropriate to current state;
- never blank the last valid snapshot during refresh;
- color never carries state alone;
- every state includes a text label;
- Provider/UUID/SHA/quota internals stay under progressive details;
- blocked source contract should say that automatic live refresh is not configured/
  authorized, while keeping the last local snapshot readable;
- no target price, position sizing, recommendation or expected-return wording.

---

## 19. Chinese-first failure taxonomy

Recommended stable codes and ordinary messages:

| Code | Ordinary Chinese message | Recovery |
|---|---|---|
| `today_market_source_contract_blocked` | 当前数据源合同条件尚未满足，未执行联网更新。 | 保留本地快照；完成单独的数据源授权/合同审核。 |
| `today_market_not_initialized` | 今日市场尚未完成首次本地初始化。 | 进入明确初始化流程，不自动拉取全历史。 |
| `today_market_manual_catchup_required` | 缺失交易日超过自动更新上限。 | 用户明确启动分段补齐。 |
| `today_market_calendar_incomplete` | 无法确认最新完整交易日。 | 检查交易日历/数据完成规则。 |
| `today_market_source_unavailable_retained_prior` | 数据源暂不可用，仍显示上一份完整快照。 | 用户可稍后明确重试。 |
| `today_market_incomplete_batch_retained_prior` | 新数据不完整，未替换上一份完整快照。 | 查看覆盖缺口并明确重试。 |
| `today_market_identity_conflict` | 部分证券身份无法唯一确认。 | 处理身份映射后再刷新。 |
| `today_market_adjustment_semantics_missing` | 公司行为/复权语义不足，相关历史指标未计算。 | 补充受审核的调整语义。 |
| `today_market_membership_not_dated` | 板块成分缺少历史生效日期，未生成成分确认型热点结论。 | 补充有效期明确的板块成分。 |
| `today_market_insufficient_coverage` | 当前覆盖不足，未生成完整市场/热点状态。 | 查看缺失范围；不要自动外推。 |
| `today_market_runtime_status_stale` | 页面状态已变化，本次更新请求未执行。 | 重新读取状态后再明确重试。 |
| `today_market_application_shutdown_retained_prior` | 应用关闭前更新未完成，旧快照保持有效。 | 下次打开后重新检查。 |
| `today_market_exact_history_incomplete` | 历史快照的精确组成已不完整。 | 停止最新回退并执行本地完整性检查。 |

Technical detail contains exact reason codes and component identities; the ordinary
message must not leak credentials or Provider response bodies.

---

## 20. Refresh state machine

The future runtime transition is derived, not a new accepted research workflow:

```text
LOCAL_PRIOR_VISIBLE
  -> CHECKING
  -> CURRENT
  -> BLOCKED_SOURCE_CONTRACT
  -> NOT_INITIALIZED
  -> MANUAL_CATCHUP_REQUIRED
  -> ACQUISITION_REQUIRED
  -> REFRESHING
  -> CANDIDATE_VALIDATING
  -> PUBLISHED_COMPLETE
  -> FAILED_RETAINED_PRIOR
  -> CANCELLED_RETAINED_PRIOR
```

### 20.1 Query vs command

Read-only:

- static/page load;
- last-valid snapshot read;
- runtime status;
- exact historical reopen;
- technical details.

Explicit/automatic bounded command:

- one first-eligible automatic refresh command when source contract is live-ready;
- explicit retry after retained-prior failure;
- explicit manual catch-up/initialization.

No GET performs acquisition or persistence.

### 20.2 Concurrency

Reuse current rules:

- optimistic `runtime_status_fingerprint` comparison before planning;
- one active attempt per `runtime_scope_revision_id`;
- simultaneous same-scope command = single-flight;
- completed same-content command = replay, not second acquisition;
- changed prior snapshot/source contract/rule revision creates a new runtime scope.

---

## 21. Exact success, partial failure and retry

### 21.1 Success

A refresh is successful only when:

1. source contract is implementation-ready;
2. requested sessions equal the deterministic missing-session plan;
3. returned sessions contain no unrequested date;
4. exact identities resolve;
5. all required families meet schema/unit/chronology checks;
6. source and batch identities are coherent;
7. all required component IngestionRuns become `succeeded` and `complete`;
8. deterministic calculations meet their coverage rules;
9. candidate snapshot identity is reproducible;
10. only then does the read path move from prior snapshot to candidate.

### 21.2 Partial Provider success

If a source returns only some requested families/sessions:

```text
raw/normalized accepted evidence = may be retained under failed/non-published run semantics
new Today Market publication = none
last_valid_snapshot = unchanged
```

No section-by-section mixture from old/new snapshots is presented as one new
complete Today Market truth unless an explicit snapshot profile defines that
behavior and exact chronology. v1 does not authorize such mixing.

### 21.3 Retry

After the one bounded automatic attempt:

- no automatic loop;
- no exponential background retry service;
- user sees the reason;
- one explicit retry command rebuilds the scope/status and plan;
- stale status or changed prior snapshot fails before acquisition.

Reference-client retry facts from Issue #225 do not substitute for account quota
or automatically authorize transport retries.

---

## 22. Exact historical reproducibility

The following are fingerprint-bearing for historical replay:

```text
source contract revision
exact component IngestionRun IDs / series identities
batch_identifier
data-through session
instrument-universe revision
calendar revision
adjustment/reference-close revision
sector taxonomy and dated-membership revision
market rule version
sector rule version
anomaly rule version
dual-as-of boundaries
```

Non-authoritative request-time presentation timestamps may be excluded from
canonical content fingerprints if they do not affect calculation results, following
the already accepted runtime fingerprint principle.

A newer source correction creates a new snapshot candidate. It does not mutate an
older exact snapshot result.

---

## 23. Zero-network validation strategy

### 23.1 Fixture policy

Normal tests and CI use only synthetic/schema-reachable fixture values.

```text
external network = zero
Provider credentials = zero
Provider market values = zero
AI calls = zero
```

Synthetic source identity must be visibly synthetic and may never be represented
as THS/Tushare/AKShare data.

### 23.2 Golden fixture

Required fixture shape:

```text
D0 = prior complete published snapshot
D1, D2 = only later completed sessions
missing sessions = [D1, D2]
expected active equity universe >= 30 synthetic instruments
same source/contract identity across all required families
at least 4 synthetic sectors with effective-dated membership
20+ sessions of history for sector state inputs
60+ sessions where new-high/new-low anomaly examples are required
```

The fixture must deterministically produce examples of:

- market state with complete coverage;
- one strengthening or persistent-strong sector;
- one new or spreading sector;
- one cooling or high-level-divergence sector;
- one neutral sector;
- large-move anomaly;
- unusual-volume anomaly;
- persistent-relative-strength anomaly;
- exact historical reopen of D0 after D2 publication.

Golden sequence:

1. render D0;
2. resolve exactly D1/D2 missing;
3. create one bounded synthetic plan;
4. acquire synthetic complete family results;
5. validate zero unexpected sessions/identities;
6. bind coherent batch identifier;
7. derive D2 complete candidate;
8. calculate rule-versioned results;
9. publish/read D2;
10. reopen exact D0 unchanged.

### 23.3 Failure fixture

At least one family is missing or chronology-invalid for D2.

Expected:

```text
candidate D2 = rejected
last_valid_snapshot = D0
refresh_state = failed_retained_prior
partial D2 ordinary-user publication = prohibited
explicit retry = available
```

### 23.4 Source-contract-blocked fixture

The default live-source gate fixture must prove:

```text
source_gate = blocked_source_contract
network calls = 0
credential lookup = 0
prior snapshot remains readable
```

---

## 24. Decisive negative matrix

Future tests must fail closed for at least:

1. no uniquely authorized source contract;
2. `blocked_quota_contract` treated as live-ready;
3. client attempts to select Provider/host/credential;
4. source returns an unrequested session;
5. source omits a requested completed session;
6. duplicate/conflicting listed identity;
7. wrong exchange binding;
8. duplicate daily natural key;
9. mixed source keys in one canonical snapshot;
10. mixed batch identifiers in one candidate publication;
11. unsupported volume/amount unit conversion;
12. corporate action intersects a return window but adjustment semantics are absent;
13. universal limit-percentage inference attempted;
14. current sector constituents used for an older session;
15. membership interval has no effective boundary;
16. sector cross-section contains fewer than 10 eligible sectors;
17. constituent coverage below state threshold;
18. anomaly lookback incomplete;
19. sector-relative anomaly has fewer than 10 eligible members;
20. partial source family success represented as complete D2 snapshot;
21. prior snapshot changes between status and command;
22. same-scope simultaneous command performs two acquisitions;
23. completed replay reacquires;
24. application shutdown exposes a candidate as published;
25. source unavailable with prior snapshot;
26. source unavailable without prior snapshot;
27. >10 missing sessions silently auto-caught-up;
28. no prior snapshot silently triggers full-history acquisition;
29. exact history silently moves to newer adjustment/membership/source rows;
30. market anomaly automatically writes research/candidate state.

Every failure preserves already valid local history.

---

## 25. Implementation slicing after architecture acceptance

Architecture merge alone does not authorize any implementation. If the project
owner later authorizes implementation, use separately governed slices.

### Slice A — Daily Market Acquisition Foundation

Objective candidate:

```text
source contract revision -> exact calendar/identity planning -> bounded missing-session acquisition
-> immutable normalized rows -> coherent batch eligibility -> prior retention
```

Potential file families to inspect later, not authorized now:

```text
backend/today_market_refresh/*
backend/api/today_market.py
backend/database/series.py
source-specific Provider package only after source gate closes
backend/database/models.py + migration only if a separately approved schema need exists
bounded source-contract tests
one zero-network acquisition demo
.github/workflows/local-tests.yml only to add required offline validation
```

Stop conditions:

- #225 or replacement source contract still blocked;
- credential/network work needed without explicit source authorization;
- dated membership/company-action storage requires schema not separately approved.

### Slice B — Market Overview + Sector Strength + Hotspot/Anomaly Rules

Objective candidate:

```text
exact complete local source snapshot
  -> market overview v1
  -> sector hotspot v1
  -> stock anomaly v1
  -> source-neutral deterministic read model
```

Potential file families to inspect later:

```text
market_cockpit/calculator.py
market_cockpit/contracts.py
market_cockpit/sector_calculator.py
market_cockpit/sector_contracts.py
new bounded deterministic hotspot/anomaly rule modules if justified
backend/api/today_market.py only for projection
focused pure tests and zero-network rule demo
```

Do not rewrite existing Market Cockpit history; add versioned outputs or reuse exact
existing metrics.

### Slice C — Ordinary-User Today Market Runtime/UI Integration

Objective candidate:

```text
prior snapshot visible
  -> status
  -> one bounded automatic refresh
  -> refreshed complete snapshot
  -> Chinese-first market/sector/anomaly screen
```

Potential file families to inspect later:

```text
backend/today_market_refresh/runtime.py
backend/api/today_market.py
today_market/static/today_market.html
today_market/static/today_market.js
bounded UI/runtime tests and demo
```

Reuse current scope/status/single-flight/replay semantics; no polling or background
worker.

Each future Issue must freeze an exact file list after re-reading current `main`.

---

## 26. Source-gate amendment required before live Slice A

Because Issue #225 is closed fail-closed, a future project-owner decision has two
legitimate paths:

### Path 1 — New THS contract-evidence amendment

Only new applicable official/account evidence may change:

```text
quota / concurrency / limit scope
session completion semantics
correction / revision / late-arrival behavior
API-key lifecycle
production dump authentication/entitlement where required
corporate-action entitlement/semantics
historical dated membership if it becomes supported
```

That amendment requires a new separately authorized evidence Issue/PR. Do not
reopen #225 merely to overwrite its historical outcome.

### Path 2 — New source-selection architecture

The project owner may choose a different documented source. That requires a new
source-specific architecture revision with:

- exact entitlement;
- host/auth contract;
- retention rights;
- quotas;
- calendar/daily/index/company-action/membership capability;
- no fallback/mixing;
- migration/identity implications.

Issue #270 itself does not select such an alternate.

---

## 27. Scope exclusions

Not authorized in this architecture PR:

- production Provider adapter;
- live THS, Tushare, AKShare or other data request;
- API key/token/cookie/account identifier;
- production HTTP/DNS/socket/subprocess/browser automation;
- Provider-valued raw response or fixture;
- credential setup;
- schema or migration;
- new database table/column;
- production daily-bar persistence code;
- announcement/news acquisition;
- OCR/PDF import;
- AI causal explanation;
- automatic evidence/research acceptance;
- automatic Industry Map/beneficiary/candidate mutation;
- target price, expected return, position sizing;
- holdings, portfolio, broker or trading;
- scheduler, daemon, polling, notification;
- release, tag or version change;
- modification/reopen/rebase/force-push/merge of PR #241;
- `docs/architecture_baseline.md` synchronization.

---

## 28. Architecture acceptance and fixed-HEAD gate

Exact architecture files:

```text
.codex/tasks/issue-270-today-market-automatic-daily-refresh-v1.md
docs/today_market_automatic_daily_refresh_v1_preflight.md
```

Before merge consideration:

1. Base remains exact `2295bcf71968f0e00d88cd0a8fa5775060079995`.
2. Base-to-HEAD contains exactly the two Markdown files above.
3. `behind = 0`.
4. No production, API, UI, test, fixture, workflow, dependency, schema, migration,
   Provider, credential, network, release, tag or version file changed.
5. Applicable repository CI succeeds on one exact immutable HEAD.
6. Independent fixed-head review rechecks source-history precedence, fail-closed gate,
   formulas, thresholds, chronology, atomicity and no-hidden-fallback behavior.
7. Review contains exactly:

```text
AUTHORIZED TODAY MARKET AUTOMATIC DAILY REFRESH V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

8. Unresolved review threads = 0.
9. Project owner separately authorizes Ready/merge.

Any new commit invalidates all earlier exact-head CI and review evidence.

Merging this architecture would accept only the target contract and current
`blocked_source_contract` outcome. It would not authorize live acquisition, a
source-contract amendment, implementation Slice A/B/C, Issue #270 closure,
architecture-baseline synchronization or any release action.