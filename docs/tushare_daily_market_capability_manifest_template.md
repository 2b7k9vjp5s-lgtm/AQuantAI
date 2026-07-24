# Tushare Pro Daily Market Capability Manifest Template

## Purpose

This template records only non-secret facts required to decide whether the source candidate selected by Issue #221 may enter a separate Strict implementation Issue.

Source candidate:

```text
tushare-pro-daily-market-v1
```

Current gate:

```text
blocked_pending_tushare_account_facts
```

Do not place any token, account identifier, private request header, credential-bearing request, Cookie/session value, restricted documentation copy, downloaded Provider dataset or credential-bearing screenshot in this file, an Issue, a PR, a fixture, a log or chat.

A public documentation statement is a source-contract candidate. It does not prove that the project owner's exact account is entitled to the capability or that automated local retention is permitted.

## Allowed fact states

Use exactly one:

- `confirmed` — supported by reviewed non-secret owner/account/contract evidence;
- `public_contract_candidate` — present in current official public documentation but not yet confirmed for the exact account;
- `unsupported` — the reviewed official contract explicitly does not support it;
- `not_entitled` — the exact account does not include it;
- `unknown` — no reliable evidence exists;
- `pending_owner_evidence` — owner/account evidence is expected but not supplied;
- `not_applicable` — the fact does not apply and the reason is recorded.

Only `confirmed` and validly justified `not_applicable` satisfy implementation readiness. `public_contract_candidate`, blank, unknown and pending values never become enabled automatically.

## Evidence reference rules

A public repository may record only:

- evidence kind: `official_public_documentation`, `official_account_console`, `official_contract`, `provider_support_reply` or `sanitized_sample`;
- non-secret document/interface title;
- public document review date;
- local evidence artifact SHA-256 when retention is permitted;
- short non-secret summary;
- local retention location category, never an account-bearing path;
- no copied restricted text beyond what its terms permit.

## Manifest header

| Field | Value |
|---|---|
| Manifest schema | `aquantai.tushare-daily-market-capability-manifest.v1` |
| Source key | `tushare-pro-daily-market-v1` |
| Governing Issue | `#221` |
| Intended use | personal, local, non-commercial research |
| Public documentation review date | `2026-07-24` |
| Owner/account review date | `PENDING` |
| Overall state | `pending_owner_evidence` |
| Evidence package fingerprint | `PENDING` |
| Credential profile key label | `PENDING` — label only, never a secret |
| Exact approved HTTPS host | `PENDING` |
| Auto-refresh consent revision | `PENDING` |

## Account-level authorization facts

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| Exact account product/tier | `pending_owner_evidence` |  |  | Do not infer from public point thresholds. |
| Exact current points/permission level | `pending_owner_evidence` |  |  | Do not record an account identifier. |
| Exact enabled API names | `pending_owner_evidence` |  |  | Must include every required capability below. |
| Credential mechanism label | `public_contract_candidate` | token field / SDK profile category | Official API usage documentation reviewed 2026-07-24 | Confirm exact production mechanism without recording the value. |
| Credential issuance behavior | `pending_owner_evidence` |  |  |  |
| Credential renewal behavior | `pending_owner_evidence` |  |  |  |
| Credential revocation behavior | `pending_owner_evidence` |  |  |  |
| Personal-use permission | `public_contract_candidate` | personal, non-transferable, non-commercial use language | Official service agreement reviewed 2026-07-24 | Exact owner acceptance still required. |
| Automated API access permission | `pending_owner_evidence` |  |  | Website/API availability alone is insufficient. |
| Application-start bounded access permission | `pending_owner_evidence` |  |  | Must explicitly cover the Issue #221 startup exception. |
| Local database retention permission | `pending_owner_evidence` |  |  | Public examples recommending local storage do not settle exact contract rights. |
| Historical reproducibility retention permission | `pending_owner_evidence` |  |  | Includes raw response and corrected revision retention. |
| Retention duration/limits | `pending_owner_evidence` |  |  |  |
| Redistribution prohibition | `public_contract_candidate` | no redistribution / personal viewing boundary | Official service agreement reviewed 2026-07-24 | Confirm exact account contract. |
| Contract expiry/revalidation rule | `pending_owner_evidence` |  |  |  |
| Provider support escalation path | `pending_owner_evidence` |  |  | Non-secret label only. |

## Network and request contract

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| Exact approved HTTPS host allowlist | `pending_owner_evidence` |  |  | No wildcard unless contract explicitly defines it. |
| TLS/transport requirements | `pending_owner_evidence` |  |  |  |
| HTTP method/request envelope | `public_contract_candidate` | documented API request envelope | Official API usage documentation reviewed 2026-07-24 | Confirm exact HTTPS production contract. |
| Credential placement category | `public_contract_candidate` | request token field / SDK profile | Official API usage documentation reviewed 2026-07-24 | Never record the token. |
| Response media type/root shape | `pending_owner_evidence` |  |  | Bind exact production response and schema. |
| Request timeout guidance | `pending_owner_evidence` |  |  |  |
| Documented transient retry guidance | `pending_owner_evidence` |  |  | No inferred retry. |
| Authentication error behavior | `pending_owner_evidence` |  |  | Sanitized example required. |
| Permission error behavior | `pending_owner_evidence` |  |  | Sanitized example required. |
| Quota/rate-limit error behavior | `pending_owner_evidence` |  |  | Sanitized example required. |
| Global concurrency limit | `pending_owner_evidence` |  |  |  |
| Quota reset timezone/time | `pending_owner_evidence` |  |  |  |
| Unknown API/field behavior | `pending_owner_evidence` |  |  | Must fail closed. |

## Shared chronology and revision facts

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| Exchange timezone | `public_contract_candidate` | Asia/Shanghai candidate | Interface date/time semantics reviewed 2026-07-24 | Confirm exact contract. |
| Daily data complete-after time | `public_contract_candidate` | official docs describe afternoon completion window | `daily` documentation reviewed 2026-07-24 | Record one exact reviewed time before implementation. |
| Calendar publication/update behavior | `pending_owner_evidence` |  |  |  |
| Late-arrival behavior | `pending_owner_evidence` |  |  |  |
| Historical correction behavior | `pending_owner_evidence` |  |  |  |
| Provider deletion/withdrawal behavior | `pending_owner_evidence` |  |  |  |
| Stable row identity behavior | `pending_owner_evidence` |  |  |  |
| Field/schema change notice behavior | `pending_owner_evidence` |  |  |  |

# Required capability records

Each capability remains `deferred_contract_incomplete` until every readiness fact is confirmed.

## Capability 1 — Stock identity candidates

| Field | Value |
|---|---|
| Capability key | `tushare.stock_basic.v1` |
| Official API name | `stock_basic` |
| Proposed family | `instrument_identity_candidate` |
| Required for first slice | `yes` |
| Account entitlement | `pending_owner_evidence` |
| Readiness state | `deferred_contract_incomplete` |

### Public contract candidates

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| API exists | `public_contract_candidate` | `stock_basic` | Official interface documentation reviewed 2026-07-24 |  |
| Published permission threshold | `public_contract_candidate` | current public threshold recorded by official docs | Official documentation reviewed 2026-07-24 | Not account entitlement. |
| Local storage guidance | `public_contract_candidate` | official docs recommend local storage for basic data | Official documentation reviewed 2026-07-24 | Does not settle exact retention rights. |
| Exact code field | `public_contract_candidate` | `ts_code` | Official documentation reviewed 2026-07-24 | Candidate only. |
| Exchange/market fields | `public_contract_candidate` | documented exchange/market fields | Official documentation reviewed 2026-07-24 | No prefix inference. |
| Listing status/date fields | `public_contract_candidate` | documented list status/date fields | Official documentation reviewed 2026-07-24 | Confirm delist chronology fields. |

### Required confirmations

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| Exact account entitlement | `pending_owner_evidence` |  |  |  |
| Exact API/schema revision | `pending_owner_evidence` |  |  |  |
| Exact selector/fields | `pending_owner_evidence` |  |  |  |
| Pagination/row ceiling | `pending_owner_evidence` |  |  |  |
| Stable symbol identity | `pending_owner_evidence` |  |  |  |
| Security type semantics | `pending_owner_evidence` |  |  |  |
| List/delist chronology | `pending_owner_evidence` |  |  |  |
| Correction behavior | `pending_owner_evidence` |  |  |  |
| Sanitized production response | `pending_owner_evidence` |  |  | No account data. |

## Capability 2 — Exchange trading calendar

| Field | Value |
|---|---|
| Capability key | `tushare.trade_cal.v1` |
| Official API name | `trade_cal` |
| Proposed family | `trading_calendar` |
| Required for first slice | `yes` |
| Account entitlement | `pending_owner_evidence` |
| Readiness state | `deferred_contract_incomplete` |

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| API exists | `public_contract_candidate` | `trade_cal` | Official documentation reviewed 2026-07-24 |  |
| Calendar/open fields | `public_contract_candidate` | exchange, calendar date, open state, previous trading date | Official documentation reviewed 2026-07-24 | Confirm exact field names/semantics. |
| Exact account entitlement | `pending_owner_evidence` |  |  |  |
| Exchange coverage | `pending_owner_evidence` |  |  | SSE/SZSE/BSE required. |
| Timezone | `pending_owner_evidence` |  |  |  |
| Forward calendar availability | `pending_owner_evidence` |  |  | Required for bounded staleness. |
| Holiday correction behavior | `pending_owner_evidence` |  |  |  |
| Stable ordering/pagination | `pending_owner_evidence` |  |  |  |
| Sanitized production response | `pending_owner_evidence` |  |  |  |

## Capability 3 — A-share unadjusted daily bars

| Field | Value |
|---|---|
| Capability key | `tushare.daily.v1` |
| Official API name | `daily` |
| Proposed family | `daily_market` |
| Required for first slice | `yes` |
| Account entitlement | `pending_owner_evidence` |
| Readiness state | `deferred_contract_incomplete` |

### Public contract candidates

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| API exists | `public_contract_candidate` | `daily` | Official documentation reviewed 2026-07-24 |  |
| Adjustment state | `public_contract_candidate` | unadjusted/raw | Official `daily` documentation reviewed 2026-07-24 | Must be fixture-confirmed. |
| Suspended-session behavior | `public_contract_candidate` | suspended sessions ordinarily have no daily row | Official `daily` documentation reviewed 2026-07-24 | Must not become zero return. |
| Required fields | `public_contract_candidate` | code/date/OHLC/pre-close/change/pct-change/volume/amount | Official `daily` documentation reviewed 2026-07-24 | Confirm exact optional/default field behavior. |
| Volume unit | `public_contract_candidate` | lots (`手`) | Official `daily` documentation reviewed 2026-07-24 | Share conversion remains unconfirmed. |
| Amount unit | `public_contract_candidate` | thousand yuan | Official `daily` documentation reviewed 2026-07-24 | Candidate Decimal conversion is ×1000. |
| Preferred date acquisition | `public_contract_candidate` | all-market by trade date is documented | Official `daily` documentation reviewed 2026-07-24 | Supports bounded no-per-stock startup plan. |

### Required confirmations

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| Exact account entitlement | `pending_owner_evidence` |  |  | Public low-tier availability is not proof. |
| Exact completed-data time | `pending_owner_evidence` |  |  | One exact local time required. |
| Single-date row ceiling | `pending_owner_evidence` |  |  | Must cover selected universe or define pages. |
| Rate/quota/concurrency | `pending_owner_evidence` |  |  |  |
| Null/duplicate semantics | `pending_owner_evidence` |  |  |  |
| Board-lot/share conversion | `pending_owner_evidence` |  |  | May remain source-unit only in v1. |
| Precision/tolerance | `pending_owner_evidence` |  |  | Decimal contract. |
| Correction/late-arrival behavior | `pending_owner_evidence` |  |  |  |
| Sanitized production success fixture | `pending_owner_evidence` |  |  |  |
| Sanitized missing/suspension fixture | `pending_owner_evidence` |  |  |  |
| Sanitized auth/permission/quota errors | `pending_owner_evidence` |  |  |  |

## Capability 4 — Adjustment factors

| Field | Value |
|---|---|
| Capability key | `tushare.adj_factor.v1` |
| Official API name | `adj_factor` |
| Proposed family | `company_action_adjustment_observation` |
| Required for first slice | `yes` |
| Account entitlement | `pending_owner_evidence` |
| Readiness state | `deferred_contract_incomplete` |

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| API exists | `public_contract_candidate` | `adj_factor` | Official documentation reviewed 2026-07-24 |  |
| Code/date/factor fields | `public_contract_candidate` | exact code/date/factor | Official documentation reviewed 2026-07-24 |  |
| Exact account entitlement | `pending_owner_evidence` |  |  |  |
| Factor formula semantics | `pending_owner_evidence` |  |  | Required before factor-price returns. |
| Factor update/correction behavior | `pending_owner_evidence` |  |  | No overwrite. |
| Missing-factor behavior | `pending_owner_evidence` |  |  |  |
| Date acquisition ceiling | `pending_owner_evidence` |  |  |  |
| Sanitized production response | `pending_owner_evidence` |  |  |  |

## Capability 5 — Core-index daily bars

| Field | Value |
|---|---|
| Capability key | `tushare.index_daily.v1` |
| Official API name | `index_daily` |
| Proposed family | `benchmark_index_daily` |
| Required for first slice | `yes` |
| Account entitlement | `pending_owner_evidence` |
| Readiness state | `deferred_contract_incomplete` |

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| API exists | `public_contract_candidate` | `index_daily` | Official documentation reviewed 2026-07-24 |  |
| OHLCV/amount fields | `public_contract_candidate` | documented index daily fields | Official documentation reviewed 2026-07-24 |  |
| Exact account entitlement | `pending_owner_evidence` |  |  |  |
| Exact supported core-index codes | `pending_owner_evidence` |  |  | Confirm all scope codes. |
| Unit and null semantics | `pending_owner_evidence` |  |  |  |
| Update completion time | `pending_owner_evidence` |  |  |  |
| Correction behavior | `pending_owner_evidence` |  |  |  |
| Sanitized production response | `pending_owner_evidence` |  |  |  |

## Capability 6 — Daily upper/lower limit prices

| Field | Value |
|---|---|
| Capability key | `tushare.stk_limit.v1` |
| Official API name | `stk_limit` |
| Proposed family | `daily_limit_price` |
| Required for first slice | `yes` |
| Account entitlement | `pending_owner_evidence` |
| Readiness state | `deferred_contract_incomplete` |

### Public contract candidates

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| API exists | `public_contract_candidate` | `stk_limit` | Official documentation reviewed 2026-07-24 |  |
| Required fields | `public_contract_candidate` | trade date, code, previous close, upper limit, lower limit | Official documentation reviewed 2026-07-24 | Avoid fixed-percentage inference. |
| Published single-call ceiling | `public_contract_candidate` | current official row ceiling | Official documentation reviewed 2026-07-24 | Confirm exact account behavior. |

### Required confirmations

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| Exact account entitlement | `pending_owner_evidence` |  |  |  |
| Complete selected-universe coverage | `pending_owner_evidence` |  |  |  |
| Update timing | `pending_owner_evidence` |  |  | Documentation describes a pre-market update; confirm correction behavior. |
| Precision/tick comparison | `pending_owner_evidence` |  |  |  |
| Special listing/ST/board semantics | `pending_owner_evidence` |  |  | Source limit values should own the result. |
| Correction behavior | `pending_owner_evidence` |  |  |  |
| Sanitized production response | `pending_owner_evidence` |  |  |  |

## Capability 7 — Shenwan industry definitions

| Field | Value |
|---|---|
| Capability key | `tushare.index_classify.sw2021.v1` |
| Official API name | `index_classify` |
| Proposed family | `sector_definition` |
| Required for first slice | `yes` |
| Account entitlement | `pending_owner_evidence` |
| Readiness state | `deferred_contract_incomplete` |

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| API exists | `public_contract_candidate` | `index_classify` | Official documentation reviewed 2026-07-24 |  |
| Taxonomy source/version | `public_contract_candidate` | Shenwan 2021 candidate | Official documentation reviewed 2026-07-24 | Freeze exact source/version. |
| Level/code/name fields | `public_contract_candidate` | documented classification fields | Official documentation reviewed 2026-07-24 |  |
| Exact account entitlement | `pending_owner_evidence` |  |  |  |
| Exact L1 selector | `pending_owner_evidence` |  |  |  |
| Stable taxonomy identity | `pending_owner_evidence` |  |  |  |
| Revision/deprecation behavior | `pending_owner_evidence` |  |  |  |
| Sanitized production response | `pending_owner_evidence` |  |  |  |

## Capability 8 — Dated Shenwan membership intervals

| Field | Value |
|---|---|
| Capability key | `tushare.index_member_all.sw2021.v1` |
| Official API name | `index_member_all` |
| Proposed family | `sector_membership_interval` |
| Required for first slice | `yes` |
| Account entitlement | `pending_owner_evidence` |
| Readiness state | `deferred_contract_incomplete` |

### Public contract candidates

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| API exists | `public_contract_candidate` | `index_member_all` | Official documentation reviewed 2026-07-24 |  |
| Multi-level codes/names | `public_contract_candidate` | L1/L2/L3 fields | Official documentation reviewed 2026-07-24 | First slice uses L1 only. |
| Member identity | `public_contract_candidate` | exact member `ts_code` | Official documentation reviewed 2026-07-24 | Candidate mapping only. |
| Entry/exit fields | `public_contract_candidate` | `in_date`, `out_date` | Official documentation reviewed 2026-07-24 | Exact inclusivity must be confirmed. |
| Current flag | `public_contract_candidate` | current-membership flag | Official documentation reviewed 2026-07-24 | Never substitute for history. |

### Required confirmations

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| Exact account entitlement | `pending_owner_evidence` |  |  |  |
| Full historical interval coverage | `pending_owner_evidence` |  |  | Must cover baseline and increment windows. |
| `in_date` inclusivity | `pending_owner_evidence` |  |  |  |
| `out_date` inclusivity/exclusivity | `pending_owner_evidence` |  |  |  |
| Null open-ended interval semantics | `pending_owner_evidence` |  |  |  |
| Membership correction behavior | `pending_owner_evidence` |  |  |  |
| Pagination/ordering/row ceiling | `pending_owner_evidence` |  |  |  |
| Sanitized historical entry/exit fixture | `pending_owner_evidence` |  |  | Must prove dated membership. |

# Deferred capability records

## Concept/theme taxonomies and memberships

| Field | Value |
|---|---|
| Proposed family | `concept_definition_and_membership` |
| First-slice state | `deferred_contract_incomplete` |
| Reason | No exact first-slice account entitlement, stable taxonomy version and complete dated-membership contract is accepted. |

Current concept membership must never be carried backward. Concept strength remains unavailable until a separate bounded contract is reviewed.

## Hot lists and causal-reason text

| Field | Value |
|---|---|
| Proposed family | `market_attention_text` |
| First-slice state | `deferred_contract_incomplete` |
| Reason | Not required for deterministic daily prices, overview and sector strength; causal text cannot own evidence or industry conclusions. |

# Sanitized fixture package

The package must contain no account or credential data.

| Fixture | State | Required content |
|---|---|---|
| `stock_basic` success | `pending_owner_evidence` | one listed, one delisted/status example, exact exchange/security fields |
| `trade_cal` success | `pending_owner_evidence` | open day, closed day and previous trading day |
| `daily` success | `pending_owner_evidence` | valid OHLC/pre-close/volume/amount and units |
| `daily` suspension/missing | `pending_owner_evidence` | production-reachable absence or explicit state |
| `adj_factor` success | `pending_owner_evidence` | at least two dates and one correction/revision example if supported |
| `index_daily` success | `pending_owner_evidence` | all required core-index field shapes |
| `stk_limit` success | `pending_owner_evidence` | exact upper/lower prices and precision |
| `index_classify` success | `pending_owner_evidence` | exact Shenwan 2021 L1 definition |
| `index_member_all` success | `pending_owner_evidence` | historical entry and exit interval |
| authentication failure | `pending_owner_evidence` | redacted production-reachable error shape |
| permission failure | `pending_owner_evidence` | redacted production-reachable error shape |
| quota/rate-limit failure | `pending_owner_evidence` | redacted production-reachable error shape |
| schema/unknown-field case | `pending_owner_evidence` | fail-closed parser proof |

# Deterministic overall readiness

The source is eligible for a separate Strict implementation Issue only when:

1. every required capability record is `implementation_ready`;
2. exact account authorization, automated startup use and local retention are confirmed;
3. exact HTTPS host and credential placement category are confirmed without secrets;
4. exact quotas, concurrency, reset and retry behavior are confirmed;
5. exact field units, chronology and correction behavior are confirmed;
6. every required production-reachable sanitized fixture exists;
7. the project owner reviews and signs the complete non-secret package;
8. a fresh fixed-head architecture review changes the gate from blocked;
9. the project owner separately authorizes the bounded Strict implementation Issue.

Otherwise the gate remains:

```text
blocked_pending_tushare_account_facts
```

# Review sign-off

| Field | Value |
|---|---|
| Reviewed by project owner | `PENDING` |
| Owner/account review date | `PENDING` |
| Overall gate result | `blocked_pending_tushare_account_facts` |
| Ready capability keys |  |
| Deferred capability keys | `tushare.stock_basic.v1`, `tushare.trade_cal.v1`, `tushare.daily.v1`, `tushare.adj_factor.v1`, `tushare.index_daily.v1`, `tushare.stk_limit.v1`, `tushare.index_classify.sw2021.v1`, `tushare.index_member_all.sw2021.v1` |
| Rejected capability keys |  |
| Missing fact summary | exact account entitlement, approved HTTPS host, credential lifecycle, automated startup/local-retention rights, quota/retry behavior, correction semantics and sanitized production-reachable fixtures |

Completing this template does not itself authorize implementation, network access, credentials, migration, merge, release or Issue closure.
