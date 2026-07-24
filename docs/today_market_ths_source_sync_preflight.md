# Today Market THS Source Sync — Architecture Preflight

## 1. Decision status

- Governing Issue: #223.
- Product roadmap: #137.
- Accepted THS account-capability architecture: Issue #219 / merged PR #220.
- Accepted Today Market automatic-refresh architecture: Issue #221 / merged PR #222.
- Required exact base: `8e6cce15df9b327e5dbe1afa1ae420e253af1f68`.
- Risk tier: **Strict Architecture Preflight**.
- Architecture only; no production code, live access, credential setup, schema, migration, fixture creation or implementation Issue is authorized.

This architecture prospectively supersedes the source candidate selected by PR #222:

```text
previous_candidate = tushare-pro-daily-market-v1
preferred_provider_candidate = ths-account-structured-provider-v1
```

PR #222 remains authoritative historical evidence of the earlier decision. This document does not rewrite or delete that history.

The current final gate is:

```text
overall_gate = blocked_pending_retention_or_use
production_implementation_authorized = false
```

## 2. Source policy

```text
preferred_provider_candidate = ths-account-structured-provider-v1
tushare_provider = deferred_by_owner_decision
akshare_adapter = deferred_by_owner_decision
runtime_provider_fallback = disabled
cross_provider_row_mixing = prohibited
browser_session_batch_download = prohibited
undocumented_endpoint_use = prohibited
```

When THS is unavailable, invalid or blocked, the system retains the prior complete local snapshot and exposes a stable unavailable/stale state. It does not fetch substitute rows from Tushare, AKShare, webpages, browser sessions or hidden endpoints.

## 3. Non-secret evidence boundary

### 3.1 Account capability evidence

Owner-supplied local validation completed at `2026-07-24T14:59:47Z`:

```text
source_key = ths-account-structured-provider-v1
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

Confirmed account entitlements:

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

No tested capability returned `not_entitled`.

Unsupported or undocumented in the reviewed boundary:

```text
ths_index_historical_constituents
dated_membership_supported = false
```

This evidence proves reachable account capability and sanitized schema observation only. It does not prove local retention permission, fixture retention permission, quotas, all field units, data completion time, correction behavior, revision behavior, late-arrival behavior or production suitability.

### 3.2 Public use evidence interpretation

Public Provider documentation supports programmatic API access, quantitative-research use, personal-developer use and local secret handling. The public material reviewed for Issue #223 does not explicitly grant unlimited storage of complete responses, distributable fixtures or redistribution.

Record the evidence without expanding it by inference:

```text
automated_api_access = supported_by_official_api_documentation
quantitative_research_use = supported_by_official_product_documentation
personal_developer_use = supported_by_official_product_documentation
local_secret_storage = supported_by_official_guidance
noncommercial_self_use = conditional_on_applicable_product_or_special_agreement
local_response_retention = unknown_not_explicitly_granted
sanitized_fixture_retention = unknown_not_explicitly_granted
redistribution = not_authorized
commercial_redistribution = not_authorized
```

An architecture preference cannot create Provider permission. The retention gate may be closed only with non-secret official terms, an official support response, an account-visible applicable agreement, or an owner-supplied redacted contract excerpt.

## 4. Preserved Today Market invariants

The following PR #222 decisions remain unchanged:

1. Render the latest complete published local snapshot before network work.
2. Determine freshness from one reviewed trading calendar, not weekdays.
3. Fetch only missing completed sessions.
4. Automatic startup refresh covers at most 10 missing completed sessions.
5. Initialization and larger catch-up require a visible plan and explicit user action.
6. One bounded attempt is made unless a reviewed contract permits one bounded transient retry.
7. Publish only after complete validation and deterministic calculation.
8. Any failure retains the prior complete snapshot.
9. No scheduler, daemon, service worker, push, continuous polling or work after shutdown.
10. No automatic mutation of Canonical Price, Evidence Ledger, Industry Map, beneficiary, valuation, Investment Candidate, recommendation, portfolio or trading state.

## 5. Why the implementation plan changes

The THS account validation confirms many product-facing capabilities, but it does not prove the same acquisition shape assumed by PR #222.

### 5.1 Full-market daily acquisition is not yet ready

The validation proved a bounded raw historical-daily capability. It did not prove any of the following:

- one all-market daily request per completed session;
- a documented multi-symbol batch ceiling sufficient for the configured universe;
- deterministic pagination over the complete A-share universe;
- a quota-compatible per-security loop;
- complete daily coverage and terminal conditions;
- a production-safe request/day/row/byte plan.

Therefore:

```text
full_market_daily_acquisition = blocked_pending_bounded_batch_contract
per_security_startup_loop = prohibited
full_market_breadth = deferred
full_market_turnover = deferred
full_market_anomaly_scan = deferred
```

A later architecture amendment or implementation Issue must identify an exact documented batch/pagination contract and prove bounded request counts before these functions can enter a production slice.

### 5.2 Corporate actions and adjusted returns are not yet ready

The P0 run did not validate a corporate-action or adjustment-event capability. Therefore:

```text
corporate_action_entitlement = pending_separate_validation
adjusted_return_features = deferred
price_discontinuity_factor_inference = prohibited
provider_precomputed_adjusted_price_as_canonical_history = prohibited
```

Raw daily bars may support exact same-session calculations when the required fields and units are reviewed. Multi-session adjusted returns, 60-session highs/lows and calculations crossing corporate-action dates remain unavailable.

### 5.3 Historical sector breadth is unsupported

Current constituents are confirmed. Dated historical membership is unsupported or undocumented.

```text
current_sector_membership = supported
current_session_current_membership_breadth = candidate_subject_to_coverage
historical_dated_membership = unsupported
historical_sector_breadth = prohibited
current_membership_backfilled_into_history = prohibited
```

Allowed after other gates close:

- industry and concept index historical strength from source-owned index bars;
- current constituent display;
- same-session current-membership observations with explicit coverage wording.

Not allowed:

- historical breadth using today's membership;
- historical constituent claims;
- survivorship-bias-hidden backfill;
- prior-session breadth transitions requiring unavailable dated membership.

### 5.4 Limit-up pools do not establish full-market limit prices

Confirmed `limit_up_pool` and `limit_up_ladder` capabilities support Provider-defined limit-up pool and ladder presentation within their documented meaning.

They do not by themselves establish:

- exact upper and lower limit prices for every security/session;
- full-market down-limit counts;
- touched-but-opened limit states;
- complete per-security daily limit-price coverage.

Therefore:

```text
provider_limit_up_pool_analysis = candidate_supported
provider_limit_up_ladder_analysis = candidate_supported
full_market_exact_limit_price_analysis = not_confirmed
full_market_down_limit_analysis = not_confirmed
```

### 5.5 Market-attention data remains separate

```text
hot_stock_list.role = market_attention_candidate
stock_anomaly_reasons.role = market_attention_candidate
```

These records may support an attention panel. They do not create accepted evidence, causal conclusions, beneficiaries, company fundamentals, research acceptance or investment recommendations.

## 6. Revised delivery plan

### Stage A — Issue #223 architecture synchronization

Current authorized work:

- select THS prospectively as the preferred candidate;
- record account validation fingerprints and capability status;
- define the secret-free manifest;
- preserve PR #222 invariants;
- define staged degradation and stop conditions;
- keep the final gate blocked where evidence is missing.

No production implementation occurs in Stage A.

### Stage B — Close non-secret external gates

Obtain reviewed evidence for:

```text
automated_personal_research_use_permission
local_response_retention_permission
sanitized_fixture_retention_permission
qps_limit
daily_total_limit
concurrency_limit
retry_contract
volume_unit
turnover_unit
currency
snapshot_market_time
daily_data_completion_time
stable_sorting_contract
natural_key_contract
provider_correction_behavior
provider_revision_behavior
late_data_behavior
api_key_expiry
api_key_revocation
api_key_rotation
```

Also perform separate bounded validation for:

- corporate actions/adjustment events;
- exact full-market or bounded batch daily acquisition;
- any exact per-security upper/lower limit-price capability required by a later slice.

### Stage C — Candidate first Strict implementation

Name:

```text
THS Provider Foundation + Index Market Overview
```

Candidate scope only after required Stage B gates close and the owner separately authorizes an implementation Issue:

- source authorization and capability revisions;
- runtime-only credential reference boundary;
- reviewed HTTP transport adapter;
- trading calendar;
- core index identity and index daily history;
- industry/concept index catalogs and index daily history;
- current constituent display;
- Provider limit-up pool and ladder;
- hot-stock and anomaly-reason attention projections;
- refresh attempts and redacted diagnostics;
- atomic complete-snapshot publication;
- prior-snapshot retention and ordinary-Chinese state projection.

Stage C explicitly excludes:

- full-market individual-security daily ingestion;
- full-market breadth and turnover claims;
- historical sector breadth;
- adjusted multi-session returns;
- 60-session high/low rules;
- full-market exact up/down-limit price claims;
- production fixtures until retention permission is reviewed;
- scheduler, notification, recommendation, portfolio or trading behavior.

### Stage D — Bounded full-market daily acquisition

May begin only after one exact documented and validated acquisition shape exists:

```text
one all-market endpoint
or documented bounded multi-symbol batches
or deterministic bounded pagination
```

The implementation must prove request/day/page/row/byte ceilings, complete terminal conditions, identity mapping coverage and missing-row semantics before publishing full-market claims.

Candidate functions:

- mapped-universe advance/decline/unchanged counts;
- mapped-universe turnover with reviewed units;
- current-session individual-security state;
- current-membership same-session sector breadth;
- coverage and exclusion diagnostics.

### Stage E — Corporate actions and adjusted analytics

May begin only after entitlement, schema, units, chronology, correction behavior and production-reachable sanitized fixtures are reviewed.

Candidate functions:

- append-only adjustment-event observations;
- deterministic factor derivation under a versioned rule;
- adjusted 5/20/60-session returns;
- adjusted high/low and relative-strength rules.

### Stage F — Historical sector breadth

Only available if a reviewed source later provides dated membership intervals or a separately governed authoritative source is approved. No other stage waits for this capability.

## 7. Candidate product outcome for Stage C

The first THS-backed page may answer:

> 主要指数和行业/概念指数表现如何，涨停与连板结构怎样，当前有哪些市场关注线索，数据日期和更新状态是什么？

It must not yet claim:

> 全A股涨跌家数、全市场成交额、完整个股异常扫描、历史行业宽度或复权多周期强弱已经可用。

Candidate presentation order:

1. Exact data date, source readiness and retained-snapshot status.
2. Core index performance.
3. Industry index strength.
4. Concept index strength.
5. Provider limit-up pool and ladder.
6. Market-attention candidates.
7. Unavailable capabilities and reasons.
8. Advanced technical provenance.

## 8. Scope and identity

A candidate stable scope revision must freeze product choices rather than moving result dates:

```json
{
  "scope_schema": "aquantai.today-market-scope.v1",
  "source_key": "ths-account-structured-provider-v1",
  "source_authorization_revision_id": "<exact>",
  "capability_revision_ids": ["<exact>"],
  "market_scope": "cn_a_share_primary_v1",
  "core_index_identity_set_revision_id": "<exact>",
  "ths_industry_catalog_revision_id": "<exact>",
  "ths_concept_catalog_revision_id": "<exact>",
  "market_rule_version": "aquantai.today-market-market-rules.v1",
  "sector_index_rule_version": "aquantai.today-market-ths-sector-index-rules.v1",
  "market_attention_rule_version": "aquantai.today-market-ths-attention-rules.v1",
  "auto_refresh_consent_revision_id": "<exact>"
}
```

Provider codes remain candidates until explicitly mapped to accepted local identities. Code prefixes, display names, current membership and LLM inference may not establish identity.

## 9. Transport and credential boundary

Validated local transport:

```text
curl.exe + Schannel + HTTP/1.1
```

This proves a reachable validation path. It does not require production shell-out to curl.

A future implementation must define one reviewed application transport contract with:

- TLS certificate verification;
- exact HTTPS host allowlist;
- no redirect following unless explicitly reviewed;
- bounded connect/read/total timeouts;
- bounded response bytes;
- no verbose credential-bearing traces;
- secret injection outside command arguments, repository, database and logs;
- complete header and error redaction;
- deterministic response-envelope validation;
- no fallback host or client path.

The earlier incompatible Python `urllib` request-construction path may not be reused without exact request comparison and a new sanitized validation.

Credential values remain runtime-only. Persistent state may contain only a non-secret profile label and readiness/status projection.

Any key exposed in chat is considered compromised and must be revoked.

## 10. Request planning

Every request plan must freeze:

- exact source authorization revision;
- exact capability revision;
- approved host and endpoint contract key;
- selector and parameter names;
- requested date/window/page;
- timeout, row and byte ceilings;
- credential profile label, never the value;
- deterministic request fingerprint;
- acquisition reason;
- startup-auto or explicit-user-action mode.

Unknown quotas prohibit automatic network execution. The application may still render the prior complete snapshot.

Retry rules:

- authentication, authorization, schema, retention and validation errors: no retry;
- quota/rate-limit errors: no same-attempt retry;
- transient transport failure: at most one retry only when the reviewed contract permits it;
- no background loop, alternate host or alternate Provider.

## 11. Chronology and publication

Keep separate:

- source trade/effective date;
- source market/update time when documented;
- fetched-at UTC;
- locally recorded-at UTC;
- dataset information cutoff;
- snapshot published-at UTC.

A current-day row is not treated as complete merely because it exists. If the reviewed completion-time contract is missing, the system selects the latest safely completed prior session or blocks refresh.

One published snapshot must bind exact:

- scope revision;
- source authorization/capability revisions;
- acquisition attempt and immutable source observations;
- accepted identity mappings;
- calendar revision;
- index/catalog/current-membership/pool/attention observations required by the slice;
- calculation rule versions;
- completeness and coverage diagnostics;
- information cutoff and recorded-UTC boundary.

No partial acquisition replaces the prior published pointer.

## 12. Persistence candidate

Architecture only; no migration is authorized.

A future source-specific implementation may propose append-only families for:

```text
ths_source_authorization_revisions
ths_capability_revisions
ths_acquisition_attempts
ths_raw_response_object_revisions
ths_instrument_candidates
ths_trade_calendar_observations
ths_index_identity_candidates
ths_index_daily_observations
ths_index_catalog_revisions
ths_current_membership_observations
ths_limit_up_pool_observations
ths_limit_up_ladder_observations
ths_market_attention_observations
today_market_scope_revisions
today_market_auto_refresh_consent_revisions
today_market_refresh_attempt_revisions
today_market_dataset_revisions
today_market_calculation_revisions
today_market_published_snapshot_revisions
```

Raw response persistence and sanitized fixtures remain prohibited until retention permission is reviewed. The architecture may retain request/response schema metadata, fingerprints and sanitized validation report references without storing Provider market values.

Secrets, private headers, account identifiers and request identifiers remain outside persisted product records.

## 13. Migration, rollback and downgrade

Candidate rules only:

- additive migration;
- no rewrite of legacy `IngestionRun`, local daily-price, benchmark, sector or Canonical Price history;
- no conversion of Tushare, AKShare or prior local rows into THS observations;
- no automatic code-to-Listed-Instrument acceptance;
- feature rollback returns Today Market to the accepted local-only read path;
- source suspension disables new THS attempts while retaining published local snapshots;
- key revocation invalidates the credential profile status without deleting historical non-secret provenance;
- populated downgrade refuses before destructive source/dataset/calculation/publication removal;
- no source switch inside an existing immutable dataset revision.

## 14. Production-realistic offline golden path

The architecture requires one zero-network golden path for the first implementation candidate:

1. Select one secret-free THS authorization/capability revision.
2. Render one prior complete local Today Market snapshot immediately.
3. Use a reviewed trading-calendar fixture to identify one missing completed session.
4. Produce a bounded request plan without network.
5. Demonstrate that every sanitized fixture field is reachable through the reviewed production endpoint/schema.
6. Bind immutable content hashes, request fingerprints and chronology.
7. Resolve Provider symbols only through exact reviewed mappings.
8. Validate index/catalog/current-membership/pool/attention records under exact semantics.
9. Never represent current membership as historical membership.
10. Compute one deterministic index-led overview under exact rule versions.
11. Atomically publish one complete new snapshot.
12. Make no automatic accepted-evidence, research, valuation, recommendation, portfolio or trading mutation.

Fixture values may not enter the repository until fixture retention permission is reviewed. Until then, the architecture can define fixture schemas and expected transformations only.

## 15. Primary failure path

When any required use/retention permission, quota, unit, completion time, schema, endpoint, corporate-action contract, bounded batch contract or credential state is missing or invalid:

- readiness remains blocked or refresh fails closed;
- the prior complete snapshot remains visible;
- no partial snapshot is published;
- no alternate Provider or host is selected;
- no guessed unit, identity, date, quota, membership or adjustment rule is persisted;
- no secret or account identifier is recorded;
- the user receives one stable Chinese reason and one explicit next action where applicable.

## 16. Stop conditions

Stop and return for project-owner review if work would require:

- credential, token, account identifier or request identifier in GitHub or repository;
- treating product positioning as unlimited retention permission;
- browser Cookie/session replay, reverse-engineered signature or undocumented endpoint;
- probing hidden quotas or entitlements;
- a generic multi-provider framework before one complete source path exists;
- runtime fallback or cross-source row mixing;
- per-security unbounded startup loops;
- current membership represented as historical membership;
- hidden survivorship bias or partial coverage represented as full-market coverage;
- adjusted analytics without reviewed corporate-action semantics;
- production network inside imports, tests, CI or ordinary local reads;
- scheduler, background notification, recommendation, portfolio or trading behavior.

## 17. Deterministic readiness

At this architecture revision:

```text
ths_transport_gate = confirmed
ths_authentication_gate = confirmed
ths_required_p0_entitlements = confirmed
ths_use_intent_evidence = supported_by_public_docs
ths_local_retention_evidence = pending_owner_or_provider_evidence
ths_fixture_retention_evidence = pending_owner_or_provider_evidence
ths_quota_and_revision_contract = pending_owner_or_provider_evidence
ths_full_market_batch_contract = pending_separate_validation
ths_corporate_action_entitlement = pending_separate_validation
ths_historical_membership = unsupported
architecture_sync_required = true
production_implementation_authorized = false
overall_gate = blocked_pending_retention_or_use
```

The architecture is not ready for an implementation Issue. Even after this PR is approved and merged, a separate project-owner instruction is required before creating any Strict implementation Issue.