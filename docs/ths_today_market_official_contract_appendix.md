# THS Today Market Official Contract Appendix

## 1. Purpose and authority

This appendix records non-secret public Provider contract facts reviewed on 2026-07-24 for Issue #223 and PR #224.

It complements, but does not replace:

- owner-supplied sanitized account-capability validation;
- `docs/ths_today_market_capability_manifest.md`;
- a future production-reachable sanitized fixture package;
- applicable account/product use and retention terms.

Official documentation proves published endpoint shape. Local validation proves selected account reachability for the tested capability. Neither one alone establishes implementation readiness.

Official documentation roots:

- `https://fuyao.aicubes.cn/docs/introduction/`
- `https://fuyao.aicubes.cn/docs/quickstart/`
- `https://fuyao.aicubes.cn/docs/api-reference/overview/`
- `https://fuyao.aicubes.cn/llms-full.txt`

## 2. Common envelope and authentication

Published REST contract:

```text
base_url = https://fuyao.aicubes.cn
credential_header = X-api-key
http_business_status = 200 with ApiResponse code
response_envelope = code, message, request_id, data
```

Local transport validation additionally confirmed:

```text
curl.exe + Schannel + HTTP/1.1
HTTP 200
Content-Type application/json
code = 0 with the validated key
```

The local no-key snapshot probe returned Provider `code=2003`, while current public documentation describes `2001` for a missing or invalid key and `2003` for a capability not granted to the key. Runtime architecture must therefore parse the actual response envelope and message and must not hard-code one unauthenticated business code as universal.

`request_id` is operational Provider metadata and must be redacted from repository fixtures, Issues, PRs and durable product records unless a separately reviewed support workflow explicitly requires a short-lived local diagnostic value.

## 3. Metadata ticker list

Official page:

`https://fuyao.aicubes.cn/docs/api-reference/ticker-list/`

Contract:

```text
method = GET
path = /api/meta/tickers/list
query = asset_type, limit, offset
asset_type candidates = a-share, a-share-index
limit default = 1000
limit maximum = 10000
offset default = 0
terminal condition = item.length < requested limit
```

Response data:

```text
timestamp
item[].thscode
item[].ticker
item[].name
item[].exchange
item[].asset_type
item[].currency
```

Architecture interpretation:

- `thscode` and source fields create Provider identity candidates only.
- `exchange` and `asset_type` may be used only under the reviewed capability revision.
- The published list does not expose listing/delisting dates or an explicit active-status chronology.
- Complete listed-instrument chronology therefore remains unresolved and cannot be inferred from current list presence.
- Names are display metadata and never establish accepted identity.

## 4. A-share trading calendar

Official page:

`https://fuyao.aicubes.cn/docs/api-reference/calendar/`

Contract:

```text
method = GET
path = /api/a-share/calendar/trading-days
query = none
window = current Asia/Shanghai natural date minus one year through current date
ordering = ascending
```

Response data:

```text
timestamp
item[].date_ms
item[].date
```

Published semantics:

```text
date_ms = Asia/Shanghai 00:00:00 millisecond timestamp
date = yyyyMMdd
```

Architecture interpretation:

- The endpoint returns trading days, not a complete open/closed calendar containing every natural date.
- The fixed one-year backward window does not provide a documented forward safety window.
- A future implementation must decide how it safely handles tomorrow/holiday planning without weekday inference.
- Daily completion time is not established by the calendar endpoint.
- The endpoint is sufficient to identify completed prior sessions only when combined with a reviewed data-completion contract.

## 5. A-share current snapshot

Official page:

`https://fuyao.aicubes.cn/docs/api-reference/prices/`

Contract:

```text
method = GET
path = /api/a-share/prices/snapshot
query = thscodes, limit, offset
```

Two modes are documented:

### 5.1 Explicit symbol batch

```text
thscodes = comma-separated Provider codes
ordering = request order
pagination = ignored
```

### 5.2 Current full-market pagination

```text
thscodes = omitted
ordering = thscode ascending
limit default = 100
offset default = 0
data.total = full code-table total
```

Response fields:

```text
data.timestamp
data.total
item[].thscode
item[].ticker
item[].last_price
item[].price_change
item[].price_change_ratio_pct
item[].open_price
item[].high_price
item[].low_price
item[].prev_price
item[].volume
item[].turnover
```

Published units:

```text
price fields = original currency
A-share currency = CNY
volume = shares
turnover = original currency, therefore CNY for A shares
price_change_ratio_pct = percentage value, already multiplied by 100
```

Architecture interpretation:

- This public contract closes the basic published unit meaning for this endpoint.
- `data.timestamp` is the latest upstream effective time among returned records and may be `null` when no valid data exists.
- Full-market pagination is a current-snapshot capability, not a historical daily-by-date capability.
- It may become a same-session market-overview input after use/retention, quota, completion-time, correction and fixture gates close.
- It cannot repair one or more missed historical sessions and therefore does not satisfy PR #222's bounded missing-session catch-up contract by itself.
- A snapshot returned before the reviewed daily completion time must not be published as a completed daily dataset.

## 6. A-share historical prices

Official page:

`https://fuyao.aicubes.cn/docs/api-reference/prices/`

Contract:

```text
method = GET
path = /api/a-share/prices/historical
query = thscode, interval, start, end, adjust, offset
thscode count = exactly one
interval = 1d
maximum window = 10 years
adjust allowed = none, forward, backward
published default adjust = forward
offset default = 0
```

Required AQuantAI request rule:

```text
adjust = none must always be explicit for raw-price acquisition
```

Response fields:

```text
data.timestamp
item[].date_ms
item[].open_price
item[].high_price
item[].low_price
item[].close_price
item[].volume
item[].turnover
```

Published units:

```text
volume = shares
turnover = original currency, CNY for A shares
price = CNY
```

Architecture interpretation:

- The endpoint is single-security and does not document a multi-security or all-market historical mode.
- It cannot be used as an unbounded per-security startup loop.
- `offset` exists publicly, but page size, row ceiling and terminal condition are not established in the reviewed public page and remain contract facts to close.
- `data.timestamp` is the latest bar's upstream effective time, not local fetch/record chronology.
- Missing-row, suspension, listing and delisting semantics remain unresolved.

## 7. Index catalogs and current constituents

Official page:

`https://fuyao.aicubes.cn/docs/api-reference/a-share-index/`

### 7.1 THS index catalog

```text
method = GET
path = /api/a-share-index/catalog/ths-index-list
query = tag
tag values = cn_concept, region, tszs, industry
pagination = none; one tag returns the full current list
```

Response fields:

```text
data.timestamp
item[].thscode
item[].name
```

No pure `ticker` field is published for catalog entries.

### 7.2 Current constituents

```text
method = GET
path = /api/a-share-index/constituents/ths-stock-list
query = thscode
thscode count = exactly one
meaning = current constituent list
```

Response fields:

```text
data.timestamp
item[].thscode
item[].ticker
item[].name
```

Architecture interpretation:

- The published contract is current-state only.
- No `in_date`, `out_date`, effective interval or historical constituent-change endpoint is documented in the reviewed boundary.
- Current membership may not be carried backward into prior sessions.
- Catalog and membership names remain source display metadata and do not create an AQuantAI Industry Map or beneficiary relationship.

## 8. Index historical prices

Official page:

`https://fuyao.aicubes.cn/docs/api-reference/a-share-index/`

Contract:

```text
method = GET
path = /api/a-share-index/prices/historical
query = thscode, interval, start, end
thscode count = exactly one
interval = 1d
maximum window = 10 years
adjust parameter = not supported
offset parameter = not supported
```

Response fields:

```text
data.timestamp
data.adjust = null
item[].date_ms
item[].open_price
item[].high_price
item[].low_price
item[].close_price
item[].volume
item[].turnover
```

Architecture interpretation:

- The endpoint supports standard exchange indices and THS industry/concept indices under source-owned identities.
- It is a viable basis for index-led historical strength after units, completion, corrections, quotas, retention and fixtures close.
- Index history does not prove historical constituent membership.

## 9. Limit-up pool

Official page:

`https://fuyao.aicubes.cn/docs/api-reference/limit-up-data/`

Contract:

```text
method = GET
path = /api/a-share/special-data/limit-up-pool
query = date_ms, page, size, sort_field, sort_dir
page minimum = 1
size range = 1..200
sort_field = last_price, continue_day_cnt, seal_money, limit_up_time
sort_dir = asc, desc
```

Response data:

```text
timestamp
pagination.total
pagination.pages
pagination.size
pagination.page
item[].thscode
item[].ticker
item[].name
item[].is_st
item[].is_new
item[].last_price
item[].price_change_ratio_pct
item[].limit_up_time
item[].limit_up_reason
item[].continue_day_text
item[].continue_day_cnt
item[].seal_money
item[].max_seal_money
```

Published units:

```text
last_price = CNY
seal_money = CNY
max_seal_money = CNY
price_change_ratio_pct = percentage value, already multiplied by 100
limit_up_time = HH:MM
```

Architecture interpretation:

- This is a Provider-defined limit-up/continuous-limit pool for supported board categories.
- `limit_up_reason` is Provider text and belongs to market-attention presentation, not deterministic causal evidence.
- This endpoint does not publish a complete exact upper/lower limit-price reference for every security.
- It does not establish complete down-limit coverage.

## 10. Limit-up ladder

Official page:

`https://fuyao.aicubes.cn/docs/api-reference/limit-up-data/`

Contract:

```text
method = GET
path = /api/a-share/special-data/limit-up-ladder
query = none
window = recent 30 trading sessions
board buckets = two_board, three_board, four_board, five_board, six_board, seven_over
maximum records per bucket = 4
```

Response data includes:

```text
timestamp
window.length
window.date_list
window.board_caps
item[].date
item[].boards.*[].thscode
item[].boards.*[].ticker
item[].boards.*[].name
item[].boards.*[].board_num
item[].boards.*[].seal_nextday
item[].boards.*[].sign_level
```

Architecture interpretation:

- This is a bounded matrix for presentation and market-attention analysis.
- It is not a complete historical membership or full-market limit-state table.
- `seal_nextday` is unavailable for the latest session and is explicitly `null`.

## 11. Hot-stock list

Official page:

`https://fuyao.aicubes.cn/docs/api-reference/hot-list-data/`

Confirmed contract facts:

```text
method = GET
path = /api/a-share/special-data/hot-stock-list
query = period
period values = day, hour
period default = day
maximum list = Top30
```

Published meaning:

```text
day = 24-hour-level hot-stock list
hour = hourly hot-stock list
```

Architecture interpretation:

- Role is `market_attention_candidate` only.
- Ranking time, exact item field contract, correction behavior and production completion semantics must be copied from the sanitized validation report or a successfully reviewed official page before implementation.
- The list must not create accepted evidence, beneficiary status or an investment recommendation.

## 12. Individual-stock anomaly reasons

Official page:

`https://fuyao.aicubes.cn/docs/api-reference/anomaly-analysis/`

Validated product capability maps to the stock-filtered endpoint:

```text
method = GET
path = /api/a-share/special-data/anomaly-analysis-stock
query = thscodes
maximum input tokens before deduplication = 50
ordering = first occurrence order for matching requested codes
no matching record = code 0 with item []
current-day data unavailable = code 3002
```

Response fields:

```text
data.timestamp
item[].stock_name
item[].analysis_content
item[].keyword_list
item[].thscode
item[].tag_name
```

The same documentation also publishes an all-current-day list endpoint:

```text
GET /api/a-share/special-data/anomaly-analysis-list
optional tag_codes = LIMIT_UP, LIMIT_DOWN, SHARP_RISE, SHARP_FALL, RAPID_RALLY, RAPID_DECLINE
```

Architecture interpretation:

- `analysis_content`, keywords and labels are Provider-authored market-attention text.
- They may not be promoted into accepted Evidence, causal conclusions, Industry Maps, beneficiaries or Investment Candidates.
- Zero rows for a valid stock is an ordinary no-match state, not a transport or entitlement failure.

## 13. Corporate-action event stream

Official page:

`https://fuyao.aicubes.cn/docs/api-reference/corporate-actions/`

Published contract:

```text
method = GET
path = /api/a-share/corporate-actions/adjustment-factors
query = thscode, from, to
thscode count = exactly one
from/to format = YYYY-MM-DD
ordering = ex_date_ms descending
```

Response fields:

```text
data.thscode
data.ticker
item[].ticker
item[].ex_date_ms
item[].dividend_per_share
item[].per_share_bonus
```

Published limitations:

```text
no event_type
no record_date
no precomputed adjust_factor
event distinction is implicit in numeric fields
```

Architecture interpretation:

- The current account entitlement for this capability was not included in the P0 validation and remains unknown.
- The published shape is per-security and therefore also requires a bounded acquisition plan before full-market use.
- Rights-issue semantics are described at product level but are not visible in the reviewed response field list; this discrepancy must be resolved before deterministic factor derivation.
- AQuantAI must not infer a canonical adjustment factor from price discontinuities.
- Provider forward/backward adjusted historical prices are not a substitute for append-only source event history when reproducible adjustment ownership is required.

## 14. Historical constituent status

The reviewed official documentation publishes current constituents only. A separate stock-to-index membership page is marked as planned, and no dated constituent interval endpoint is documented.

Current architecture status:

```text
historical_dated_membership = unsupported
historical_sector_breadth = prohibited
current_membership_backfilled_into_history = prohibited
```

This limitation does not block index-price history, current constituent display or same-session current-membership observations with explicit coverage wording.

## 15. Contract facts closed by public documentation

The reviewed public pages support the following updates:

```text
snapshot_volume_unit = shares
snapshot_turnover_unit = CNY for A shares
historical_volume_unit = shares
historical_turnover_unit = CNY for A shares
price_currency = CNY
snapshot_full_market_pagination = documented_current_state_only
ticker_list_limit_max = 10000
calendar_timezone = Asia/Shanghai
calendar_ordering = ascending
calendar_backward_window = one year
index_history_max_window = ten years
historical_price_max_window = ten years
limit_up_pool_page_size_max = 200
anomaly_stock_batch_max = 50
```

These public facts do not close:

```text
local_response_retention_permission
sanitized_fixture_retention_permission
qps_limit
daily_total_limit
concurrency_limit
retry_contract
daily_data_completion_time
stable correction/revision/late-arrival behavior
API key expiry/rotation/suspension behavior
historical all-market gap-fill acquisition
corporate-action entitlement
production-reachable fixture permission
```

## 16. Resulting implementation gate

```text
public_endpoint_contract_gate = materially_documented
account_entitlement_gate = confirmed_for_tested_p0_capabilities
current_full_market_snapshot_contract = documented_but_not_gap_fill
historical_full_market_gap_fill = blocked_pending_bounded_contract
corporate_action_entitlement = pending_separate_validation
historical_sector_membership = unsupported
retention_and_fixture_gate = blocked_pending_owner_or_provider_evidence
production_implementation_authorized = false
overall_gate = blocked_pending_retention_or_use
```

This appendix contains no credentials, account identifiers, request identifiers from the validation run or actual Provider market values.