# Issue #70 - v0.6E Evidence-Backed Price Observation Judgments Plan

## Authorization state

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#70`
- Branch: `feat/v06e-price-observation-judgments`
- Draft PR: `[v0.6E] Plan evidence-backed price observation judgments`
- Required base and ancestor: `9cc5a0e5dda97efa6b9c7b3a43eb3b5c4ead91ec`
- Version must remain `0.2.0`
- This task snapshot and Draft PR setup are the only authorized changes.

Read `.codex/WORKFLOW.md`, Issue #70, this task file, the Draft PR, its latest review, and latest CI before any later implementation work. Issue #70 is authoritative.

Keep Issue #70 Open and the PR Draft/Open/unmerged. Do not implement application code until ChatGPT separately accepts this plan and synchronizes explicit implementation authorization. Do not release/tag, change version, begin timing judgments or v0.7, add page/UI work, rebase/force-push reviewed history, or modify PR #38.

## Objective

Plan the smallest local, append-only, cutoff-aware manual price-observation judgment slice for one state-qualified v0.6A company-research identity. The proposed record preserves exact price, valuation, quality-judgment, claim, and evidence provenance while remaining a descriptive research observation.

This slice must not become a target-price, fair-value, expected-return, recommendation, good-price, good-timing, alert, portfolio, order, or trading system. No application behavior is authorized by this planning PR.

## Proposed domain boundary

Create a stable `price_observation_judgments` identity attached to one `Stage2CompanyResearch` identity and a canonical non-editable key. Add immutable, sequential `price_observation_judgment_revisions` with exact supersedes chains.

Each proposed revision contains bounded manual research fields:

- one strict `observation_context` value from the proposed vocabulary below;
- one existing-style `evidence_state` value;
- an explicit comparison basis that names what the observed price is being compared with, without computing value or return;
- evidence-based rationale;
- uncertainty;
- a bounded immutable `后续验证清单`;
- information cutoff date;
- timezone-aware UTC recorded timestamp.

The observation is descriptive and manually asserted. The system must not derive, upgrade, score, rank, recommend, or translate it into timing or trading language.

## Exact frozen boundary

Every proposed revision must freeze all of the following:

1. one exact v0.6A `Stage2CompanyResearchRevision` from its own stable company-research identity, qualified by the executable workflow/conclusion rules below;
2. exact relevant v0.6B market-expectation and valuation-snapshot revisions from that same company-research identity;
3. one exact local `daily_price` row from one successful ingestion run whenever price context is present;
4. one exact accepted v0.6D company-quality judgment revision from that same company-research identity;
5. exact material v0.5A claim revisions and exact visible claim-evidence links;
6. exact stock code, trade date, adjustment mode, series key, ingestion-run identity, provider, adapter/contract provenance, information cutoff, imported UTC timestamp, and completed UTC timestamp associated with the frozen price row;
7. the revision information cutoff and timezone-aware UTC recorded timestamp.

Exact revision coherence is mandatory rather than identity-level compatibility:

- every selected v0.6B expectation revision's `company_research_revision_id` must equal the one exact frozen v0.6A revision ID;
- every selected v0.6B valuation revision's `company_research_revision_id` must equal that same exact v0.6A revision ID;
- the selected v0.6D company-quality judgment revision's `company_research_revision_id` must equal that same exact v0.6A revision ID;
- the price-specific v0.6B expectation and valuation revision IDs must each be a non-empty subset of the exact corresponding revision IDs already frozen by the selected v0.6D judgment revision;
- every price-specific v0.6B subset member must have frozen status `supported` or `disputed`; these are the only statuses admitted by the v0.6D frozen boundary;
- additional v0.6B revisions outside the v0.6D frozen sets are prohibited, even when they belong to the same stable company-research identity or were recorded earlier;
- reads must return both the complete v0.6D frozen sets and the selected price-specific subsets so compatibility remains auditable.

Same identity with a different v0.6A revision fails closed. Empty required subsets, mixed v0.6A revisions, or a price-specific v0.6B revision absent from the v0.6D frozen set fail closed in the same transaction. Every selected subset member must also satisfy the revision cutoff and UTC chronology rules independently.

Membership and status validation occur before observation-state evaluation. Any attempted selected v0.6B revision with status `draft` or `rejected` fails as an invalid v0.6D frozen-set member before any identity, revision, audit row, or link is created. The implementation must not add dead draft/rejected observation-state branches or weaken exact-subset validation to make them reachable.

The exact frozen v0.6A revision is executable only under this closed matrix:

- `workflow_state=completed` and `conclusion_status=supported` permits a comparative `below_recorded_comparison`, `at_recorded_point`, or `above_recorded_comparison`, subject to every stricter v0.6B/v0.6D/evidence/basis rule;
- `workflow_state=completed` and `conclusion_status=disputed` permits only `not_comparable` with observation `evidence_state=disputed`, preserving all visible disputes;
- `workflow_state` of `open`, `paused`, or `archived` fails closed for every observation context and evidence state;
- `conclusion_status` of `unassessed`, `insufficient_evidence`, or `rejected` fails closed for every workflow state, including `completed`;
- every unlisted or conflicting workflow/conclusion combination fails closed before any identity, revision, frozen audit row, or link is created.

The most restrictive upstream state always wins. The command must never infer completion, treat archived as completed, or upgrade/downgrade a conclusion. Current and historical reads must expose the exact frozen v0.6A `workflow_state` and `conclusion_status` alongside its revision ID, cutoff, and recorded UTC timestamp.

The price row is optional only for an explicitly unavailable or not-assessed observation. A revision that makes a comparative price observation must freeze exactly one visible local row. It must not select by provider alone, combine series, substitute a different adjustment mode, or silently use a later row.

Later prices, ingestion attempts, expectations, valuations, company-quality judgments, research revisions, claims, evidence, or links must not rewrite an accepted revision. Historical reads must evaluate both information-date visibility and actual UTC recorded/imported/completed visibility.

## Proposed categorical vocabulary

The following vocabulary is proposed for review and must not be implemented until accepted:

### `observation_context`

- `below_recorded_comparison`: the exact observed close is manually documented as below the explicitly named frozen comparison context;
- `at_recorded_point`: the exact observed close equals one frozen point comparison with compatible unit and currency;
- `above_recorded_comparison`: the exact observed close is manually documented as above the explicitly named frozen comparison context;
- `not_comparable`: the frozen materials do not provide a valid like-for-like comparison;
- `not_assessed`: no reliable comparison has been made.

These labels describe only the relationship to a recorded comparison basis. They must never be exposed as cheap/expensive, attractive/unattractive, favorable/unfavorable, buy/sell/hold, upside/downside, good-price, good-timing, or a recommendation.

### `evidence_state`

Reuse the reviewed vocabulary:

- `supported`;
- `disputed`;
- `insufficient_evidence`.

No confidence field may upgrade disputed or missing evidence. If inference confidence is exposed through frozen claims, it remains claim provenance rather than a price score.

### `comparison_basis_kind`

- `point`: exactly one designated selected `supported` v0.6B valuation revision; the point is derived only from that revision's canonical `observed_value` and cannot be supplied independently;
- `qualitative_non_comparable`: no numeric value, with a bounded non-empty incompatibility or missing-basis explanation and exact source provenance when available.

No command field may accept an independently entered comparison value. Numeric values must never be parsed from `comparison_basis`, `metric_context`, assumptions, rationale, uncertainty, verification notes, or any other free text. A point command accepts exactly one designated valuation revision ID. Zero, multiple, unselected, non-`supported`, or missing-data designated valuation revisions fail closed.

Each designated valuation revision must be in the selected price-specific valuation subset and therefore in the selected v0.6D frozen valuation set, bind the same exact v0.6A revision, be visible at the observation cutoff/UTC timestamp, have a non-`missing_data` method, and contain a canonical `observed_value`. The immutable observation boundary and read model freeze and expose for every designated revision:

- exact valuation revision ID and fixed role `point`;
- exact source field name, fixed as `observed_value`;
- valuation method and metric context;
- the exact upstream canonical `observed_value` string without caller replacement;
- unit, currency, information cutoff, and recorded UTC timestamp.

The command derives the point by locked read of those exact fields and verifies byte-for-byte canonical string equality when writing the immutable boundary. It must reject any caller-supplied duplicate value field and any mismatch between the frozen value and the designated upstream revision.

`below_recorded_comparison`, `at_recorded_point`, and `above_recorded_comparison` require exactly one valid point. `at_recorded_point` requires exact canonical-Decimal equality. `not_comparable` and `not_assessed` may use only `qualitative_non_comparable`.

Observed close and the point value must represent the same per-share price dimension, unit, and currency. The numeric basis requires an explicit price-per-share unit and explicit matching currency on the designated valuation revision and the independently derived frozen daily-price provenance below. Multiples, ratios, percentages, aggregate enterprise/equity values, missing unit/currency, mixed dimensions, mixed currencies, or any requirement for FX/unit conversion fail closed; no conversion or arbitrary normalization is permitted. The validator may verify the direct point relation and provenance only. It must not calculate fair value, intrinsic value, expected return, discount/premium, upside/downside, recommendation, or timing.

v0.6E has no structured multi-value comparison capability. It must not define or expose any two-value band, endpoint role, inclusive interval, or paired-valuation relationship. A future multi-value capability requires a separately reviewed upstream structured evidence boundary and is outside this slice.

### Versioned daily-price unit and currency provenance

`DailyPriceRecord` has no unit or currency column. Numeric comparison therefore uses resolver `aquantai.a-share-price-unit-resolver/v2`, with two and only two ordered structured strategies. Both derive data from locked persisted rows; callers cannot select a strategy or submit/override resolver, exchange, series metadata, mapping result, unit, or currency.

#### Strategy 1: trusted structured exchange

- strategy ID: `trusted_exchange`;
- source field: exact persisted `stock_basic.exchange` from the `StockBasicRecord` whose `ingestion_run_id`, `source`, and `stock_code` equal the frozen daily-price row and whose row belongs to the same selected series/snapshot;
- allowed immutable entries, matched case-sensitively with no additional normalization: `exchange:SH -> (unit=close, currency=CNY)` and `exchange:SZ -> (unit=close, currency=CNY)`; here `close` means normalized per-share closing price, not an aggregate or multiple;
- blank, missing, malformed, differently cased, unknown, or any other exchange token does not match this strategy and proceeds only to Strategy 2.

#### Strategy 2: exact canonical AKShare A-share snapshot contract

- strategy ID: `canonical_akshare_a_share_snapshot`;
- immutable matched entry: `akshare:a-share-complete-snapshot:v1 -> (unit=close, currency=CNY)`;
- applicability requires raw persisted `stock_basic.exchange` to be exactly blank; the stock-basic and daily-price rows must have the same source and stock code and must both reference the exact selected `ingestion_run_id`, whose persisted series key identifies that one complete snapshot;
- load the persisted `IngestionRun.series_identity` canonical JSON and `series_key`; validate the exact `aquantai.snapshot-series.v1` field set with no missing or extra fields;
- independently rebuild the identity with `build_snapshot_series_identity` semantics from the persisted canonical values, require byte-equivalent canonical JSON, encode with `json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`, recompute the lowercase SHA-256 series key, and require it to equal the persisted run key used by all source rows through their common `ingestion_run_id`;
- require `status=succeeded`, `snapshot_mode=complete`, `provider=akshare`, `dataset=market_data_bundle`, and `contract_version=1.0`;
- require canonical `datasets` to equal exactly sorted `daily_price`, `stock_basic`, and `trade_calendar`, with no missing or extra dataset;
- require canonical `stock_codes` to equal the normalized `requested_scope.stock_codes`, require `requested_scope.stock_code_semantics=exact`, require the frozen stock code to be an exact member, and reject missing, duplicate, substituted, broader, or cross-run membership;
- require canonical requested dates and adjustment policy to equal the ingestion run and frozen daily-price provenance;
- require canonical `compatibility_parameters` to contain exactly `stock_basic_endpoint=stock_info_a_code_name`, `daily_price_endpoint=stock_zh_a_hist`, `trade_calendar_endpoint=tool_trade_date_hist_sina`, `frequency=daily`, and `adapter_compatibility_version=aquantai.akshare-adapter.v1`, with no missing, extra, or altered key;
- require persisted `adapter_version=akshare-normalizer-v1` and freeze both adapter versions and the complete canonical compatibility object;
- an exact match resolves `(unit=close, currency=CNY)` despite blank exchange. Provider name alone, a stored series key without payload validation, or a payload without key recomputation is never sufficient.

If Strategy 1 matches, it wins and Strategy 2 is not used. Otherwise Strategy 2 must satisfy every condition. If neither strategy matches, numeric comparison fails closed and only `qualitative_non_comparable` with `not_comparable` and an explicit provenance reason may be created; no `not_assessed` fallback may conceal the mismatch.

The resolver continues to prohibit stock-code prefix/suffix inference, security-name or free-text parsing, provider-name-only inference, caller metadata, valuation-currency borrowing, fallback/default currency, FX conversion, and silent normalization.

The immutable price audit boundary freezes resolver ID/version, selected strategy, stock-basic source integer ID/natural key, raw exchange token including blank, persisted and recomputed series keys, complete canonical series payload, canonical payload hash input, contract and adapter versions, exact matched strategy entry, derived unit, and derived currency. Reads return those frozen values and never recompute accepted provenance from later-mutated metadata or a later resolver version.

A numeric `below_recorded_comparison`, `at_recorded_point`, or `above_recorded_comparison` requires a resolver match and exact agreement with the designated valuation revision's explicit `close`/`CNY` dimension. Missing, forged, partial, extra, unknown, cross-run, later, or mismatched provenance permits no numeric context.

### Canonical close and comparison decimal

There is one permitted `daily_price.close` Float-to-canonical-Decimal conversion:

1. reject booleans, non-numeric values, non-finite floats, and values `<= 0` before conversion;
2. convert the source Float with `Decimal(str(source_close))`; direct `Decimal(source_close)` is prohibited;
3. pass that Decimal through the existing v0.6B canonical decimal routine `_decimal_text` to produce plain canonical decimal text without exponent notation or insignificant trailing zeros;
4. reject a canonical result that is non-finite, `<= 0`, longer than 64 characters, or has more than 18 fractional digits;
5. freeze that canonical string in the immutable price audit boundary and expose it as the authoritative close value.

The same positive, finite, maximum-64-character and maximum-18-fractional-digit restrictions apply to the designated valuation revision's already-canonical `observed_value` before it can serve as a point. This additional comparison eligibility check does not rewrite the upstream v0.6B revision.

All relation checks construct `Decimal` only from the frozen canonical close and frozen upstream canonical `observed_value` strings. Binary float comparison, direct float equality, float-derived relation checks, tolerance/epsilon matching, and comparing a source Float with an upstream decimal are prohibited. Current, historical, fixture, demo, and API payloads return the canonical strings so SQLite and PostgreSQL cannot diverge through floating representation.

## Upstream status compatibility matrix

The implementation must apply the following matrix before creating any identity, revision, or link. v0.6B state and v0.6D outcome/evidence provenance remain separately visible in the read model; neither may be rewritten, collapsed, or used to automatically generate the price-observation state.

| Frozen upstream state | Allowed observation context | Allowed observation evidence state | Required behavior |
| --- | --- | --- | --- |
| v0.6A is `completed/supported`; every selected v0.6B expectation and valuation is `supported`; valuation input is observed and complete; one reproducible compatible point exists; v0.6D evidence is `supported` with outcome `affirmed` or `not_affirmed` | `below_recorded_comparison`, `at_recorded_point`, or `above_recorded_comparison` | `supported`, `disputed`, or `insufficient_evidence`, subject to the observation's own evidence | Upstream support permits comparison but never generates its context/evidence state. A `supported` observation still requires its own visible A/B/C support and no contradiction. |
| v0.6A is `completed/disputed` | `not_comparable` only | `disputed` only | Preserve the original v0.6A workflow/conclusion and visible disputes. Every comparative context is rejected regardless of later upstream support. |
| v0.6A has any other workflow/conclusion combination | none | none | Fail closed before any row is created; preserve the rejected source states in validation diagnostics without creating a research record. |
| Selected v0.6B and v0.6D records otherwise satisfy the supported row, but no reproducible compatible point exists | `not_comparable` only | `insufficient_evidence` only | Preserve the qualitative incompatibility reason; lack of a point cannot become a supported comparison. |
| Any selected v0.6B input is `disputed` | `not_comparable` only | `disputed` only | Preserve the disputed revision and conflicts; comparative below/at/above is rejected. |
| Any required valuation input has method/state `missing_data`, or an observed numeric/unit/currency field is absent | `not_comparable` or `not_assessed` | `insufficient_evidence` only | No below/at/above context is allowed and missing fields remain explicit. |
| Neither trusted exchange nor exact recomputed canonical AKShare snapshot contract resolves, or provenance is absent, forged, unknown, malformed, later, cross-run, caller-supplied, or valuation-mismatched | `not_comparable` only | `insufficient_evidence` or `disputed`, according to visible evidence | Preserve resolver attempts, raw exchange, and exact failure reason; no numeric context or silent fallback is allowed. |
| v0.6D evidence is `disputed`, or its frozen claims contain a visible contradiction | `not_comparable` only | `disputed` only | Preserve v0.6D outcome, evidence state, and conflicts without upgrading them. |
| v0.6D evidence is `insufficient_evidence`, or outcome is `uncertain`/`not_assessed` without a stronger compatible row above | `not_comparable` or `not_assessed` | `insufficient_evidence` only | Preserve v0.6D outcome and missing evidence; no comparison is supported. |
| Any combination not listed, or multiple rows conflict | none | none | Fail closed and roll back. The most restrictive compatible row wins; states are never silently upgraded. |

`not_affirmed` is a manual v0.6D quality outcome and does not itself prohibit a price comparison when its independent evidence state is `supported`; it must remain visible and must not automatically downgrade or generate the price observation. Every matrix row and every rejected cross-product requires focused SQLite and PostgreSQL coverage.

## Proposed validation rules

- Comparative contexts require exactly one frozen daily-price audit boundary, non-empty compatible v0.6B expectation and valuation subsets, and one exact v0.6D company-quality judgment revision, all coherently bound to the same exact v0.6A revision.
- `supported` requires at least one bound supported claim revision with visible A/B/C supporting evidence and no visible contradiction.
- D-only evidence cannot independently produce `supported`.
- `disputed` requires a disputed claim revision or visible contradiction and must preserve the conflicting evidence in reads.
- `insufficient_evidence` must preserve explicit missing-evidence reasons.
- `not_comparable` requires a non-empty incompatibility reason and cannot use `supported`.
- `not_assessed` requires `insufficient_evidence`, explicit `尚未获得可靠公开证据` wording, and no comparative conclusion.
- Facts must retain null inference confidence/basis; inferences require the existing valid confidence vocabulary and a non-empty basis.
- Comparison basis, rationale, uncertainty, and verification notes accept only strings (or explicitly allowed `None`), enforce reviewed length bounds, reject blank values where required, and never coerce non-strings with `str()`.
- All dates, identifiers, enum values, prices, and provenance must be valid. Every numeric comparison value must satisfy the canonical positive finite Decimal, length, and scale rules above. Strict JSON output must reject `NaN` and `Infinity`.
- The frozen price stock code must equal the company-research stock code and belong to the exact selected stock scope.
- The price row must come from a successful ingestion run and the exact canonical series/adjustment boundary. Its trade date must be on or before the revision information cutoff. Its source and frozen audit scalars must match exactly at creation.
- The ingestion run must satisfy `imported_at_utc <= completed_at_utc <= revision.recorded_at_utc`; every frozen upstream record/link must be visible by both information cutoff and recorded UTC time.
- Cross-company, cross-case, cross-research, cross-series, later, invisible, incomplete, superseded-in-place, or backdated boundaries fail closed.
- Identity creation, revision append, and all frozen links occur in one transaction. Any validation, chronology, uniqueness, or concurrency failure rolls back every row.
- Accepted identities, revisions, and frozen links reject ordinary ORM update/delete. Corrections append a new revision.
- Revision numbers are deterministic and contiguous per identity. PostgreSQL allocation uses the established row-lock/concurrency pattern and preserves an exact supersedes chain.

### Immutable price and ingestion audit boundary

A `daily_price_id` or `ingestion_run_id` foreign key alone is insufficient because the referenced v0.3 rows are not protected by the Stage 2 append-only guards. The proposed implementation must therefore create one revision-owned immutable audit-boundary row whenever a price row is frozen. The boundary retains source foreign keys and canonical natural keys, and copies only the material audit scalars required to reproduce the accepted observation:

- stock code, trade date, source Float close for audit only, authoritative canonical decimal-text close, and exact frozen `aquantai.a-share-price-unit-resolver/v2` provenance;
- resolver strategy, stock-basic source integer ID/natural key, raw persisted exchange token including blank, persisted/recomputed series keys, canonical series payload/hash input, contract/adapter versions, matched entry, and derived `close`/`CNY` values;
- daily-price source integer ID and complete natural key;
- ingestion-run source integer ID, batch identifier, status, provider, series key, contract/adapter versions, requested scope, adjustment mode, and information cutoff;
- imported and completed UTC timestamps.

Creation must lock/re-read the daily-price, ingestion-run, and exact same-snapshot stock-basic source rows, require a successful ingestion run, validate all scalar/provenance/mapping values, and write the immutable audit boundary in the same transaction as the observation revision. Query/API payloads use the frozen boundary values for historical meaning and expose source IDs/natural keys only as provenance; they must never rehydrate accepted values from a later-mutated source row.

The source Float is retained only to audit the one approved conversion. It is never used for equality, ordering, point classification, or JSON numeric output. Recomputing `Decimal(str(source_close)) -> _decimal_text` at creation must exactly equal the frozen canonical close string.

This is a narrow audit copy, not a second daily-price dataset: it stores one material close/provenance boundary per observation revision, adds no OHLCV history or independent series, and cannot be queried as market data. The boundary and its links use the established append-only update/delete guards. Direct mutation tests must prove that:

- ORM and direct repository attempts to update/delete the frozen audit-boundary row fail and roll back;
- direct update/delete attempts against the referenced daily-price or successful-ingestion row either fail under existing database constraints or, where the source model permits mutation, cannot alter any current/historical observation payload because reads use frozen scalars;
- source mutation followed by revision append cannot silently reuse stale/mismatched provenance;
- stock-basic exchange, series identity/key, request metadata, adapter/contract metadata, or resolver changes after acceptance cannot alter frozen unit/currency provenance or existing current/historical payloads;
- SQLite and PostgreSQL preserve the accepted payload and unchanged observation row counts after every rejected mutation.

## Proposed persistence plan

If a later review authorizes implementation, add exactly one forward Alembic migration after `20260719_0011`. The reviewed migration identifier must be chosen in that authorization; this planning task does not reserve or create one.

Proposed tables:

- `price_observation_judgments`: stable identity, company-research identity, canonical key, creation cutoff and UTC timestamp;
- `price_observation_judgment_revisions`: immutable revision number, supersedes link, proposed enums, bounded text, information cutoff and UTC timestamp;
- frozen links for the exact company-research revision;
- frozen links for exact expectation and valuation revisions;
- one optional immutable revision-owned daily-price/ingestion audit boundary retaining source FKs/natural keys and the minimal frozen material scalars defined above;
- one frozen company-quality judgment revision link;
- frozen exact claim-revision and claim-evidence-link memberships.

The schema and migration plan must contain no paired valuation relationship or endpoint-role field. The read contract must contain no multi-value comparison representation. Only one point valuation link or one qualitative non-comparable basis is allowed per revision.

Prefer explicit foreign keys and uniqueness constraints matching established v0.5/v0.6 append-only conventions. The minimal immutable audit boundary is required and is not a duplicate market-data store; do not copy unrelated OHLCV rows, expose it as a price repository, or introduce a new price series, provider, calendar, cache, queue, ORM, database, ingestion path, or mutable snapshot.

Downgrade must be safe and scoped to the new tables only. It must not delete, rewrite, merge, or reinterpret existing v0.3-v0.6D audit history.

## Proposed read-only API

If later authorized, add deterministic strict-JSON list/detail routes under `/industry-alpha`:

- `GET /industry-alpha/price-observation-judgments`;
- `GET /industry-alpha/price-observation-judgments/{judgment_id}`;
- optional `as_of_cutoff=YYYY-MM-DD` on both routes.

The read model must expose the stable identity, selected revision, exact supersedes chain, observation/evidence states, the frozen v0.6A workflow/conclusion fields, rationale, uncertainty, bounded `后续验证清单`, exact upstream IDs, the optional single point valuation provenance, complete price/ingestion/stock-basic provenance, resolver ID/version/strategy, raw exchange, canonical series payload and persisted/recomputed keys, contract/adapter versions, exact matched entry, unit/currency, claim fact/inference fields, evidence grades/relations, contradictions, missing-evidence diagnostics, information cutoff, and UTC timestamps.

Ordering must be explicit and deterministic. Current and historical reads must fail closed when the selector or frozen boundary is absent, ambiguous, later, or inconsistent. The API must use the existing fixed generic 503 configuration-error message and must never reveal database URLs, credentials, paths, or raw exceptions.

No POST, PUT, PATCH, or DELETE route and no browser editing or presentation page is authorized.

## Proposed deterministic fixture and demo

If later authorized, add one completely offline fixture/demo that reuses the reviewed nested v0.5/v0.6A-v0.6D fixture boundary and contains:

- one supported comparative observation with exact A/B/C evidence and a frozen successful daily-price row;
- one exact same-snapshot `stock_basic.exchange=SZ` case resolved by `trusted_exchange` as `close`/`CNY`;
- one no-network AKShare-compatible successful complete snapshot with blank exchange resolved by `canonical_akshare_a_share_snapshot` after exact canonical payload validation and series-key recomputation;
- one `completed/disputed` v0.6A example that produces only `not_comparable/disputed` and preserves the original state;
- one disputed observation that visibly retains contradictory evidence;
- one `not_comparable` or `not_assessed` observation with explicit missing-data semantics;
- fact and inference claim provenance;
- a later price, valuation, company-quality judgment, claim/evidence addition, and later observation revision that remain visible currently but are excluded from an earlier cutoff;
- fixture-only UUIDv5 IDs for new and nested UUID identities while normal runtime UUIDv4 behavior remains unchanged;
- deterministic integer allocation for `ingestion_run.id` and `daily_price.id` through identical clean-database fixture insertion order, plus their canonical natural-key representations in the payload.

UUIDv5 must never be claimed or applied to integer IDs. The fixture must return complete list/detail and historical payloads with stable ordering. Two clean SQLite builds, two clean PostgreSQL builds, and cross-database canonical payload comparison must have identical semantic fields, every exposed UUID, every integer ID and natural key, and every collection order. Tests must separately assert UUID versions, integer types/values, natural-key equality, and normal runtime UUIDv4/integer allocation behavior. Serialization uses `json.dumps(..., allow_nan=False)`.

## Proposed SQLite and PostgreSQL tests

Any later implementation authorization must require focused tests for:

- one new migration, clean `base -> head`, previous-head upgrade, safe down/up round trip, and `python -m alembic check`;
- exact v0.6A research, v0.6B expectation/valuation, daily-price/ingestion, v0.6D quality-judgment, claim, and evidence boundaries;
- every v0.6A workflow/conclusion combination, permitting only `completed/supported` comparison and `completed/disputed -> not_comparable/disputed`, with all other combinations rejected before row creation and unchanged identity/revision/audit/link row counts;
- current/historical readback of the exact frozen v0.6A `workflow_state` and `conclusion_status` without upgrade or collapse;
- same stable company-research identity but different exact v0.6A revision rejection;
- price-specific v0.6B subset acceptance and out-of-v0.6D-set, empty-set, mixed-set, chronology, and provenance rejection;
- membership-stage rejection of selected v0.6B `draft`/`rejected` revisions before observation-state evaluation, with unchanged identity/revision/audit/link counts;
- same-company, same-case, same-series, exact stock, date, adjustment, and successful-ingestion enforcement;
- stable identities, immutable sequential revisions, deterministic numbering, and supersedes chains;
- all proposed observation/basis enums, single-point/qualitative field shapes, direct point relation checks, unit/currency compatibility, and every allowed/rejected status-matrix combination;
- point rejection for absent, multiple, unselected, non-supported, missing-data, altered, independently supplied, or wrong-field valuation values;
- exact freezing and readback of valuation revision IDs/roles, `observed_value` field name, method, metric context, canonical strings, units, currencies, cutoffs, and UTC timestamps;
- per-share price dimension enforcement and rejection of multiples, ratios, percentages, aggregates, absent/mixed units, absent/mixed currencies, FX conversion, and arbitrary normalization;
- exact trusted SH/SZ exchange resolution and blank-exchange canonical AKShare contract resolution, with immutable resolver ID/version/strategy, raw exchange, canonical payload/keys, adapter/contract versions, matched entry, and source row/natural key readback;
- forged or mismatched series key/payload, missing/extra/partial/wrong datasets, wrong provider/dataset/contract/snapshot mode/scope semantics/stock membership/date/adjustment, wrong endpoint/frequency/adapter version, duplicate or substituted scope, cross-run rows, unknown exchange plus nonmatching contract, caller overrides, and later metadata mutation;
- every resolver rejection keeps identity/revision/audit/link counts unchanged and permits only explicit qualitative non-comparable output when otherwise valid;
- the sole `Decimal(str(close)) -> _decimal_text` conversion, canonical string freeze, positive/finite/64-character/18-scale bounds, and rejection of `Decimal(float)`, direct float equality, epsilon matching, non-positive, non-finite, overlength, and overscale values;
- supported, disputed, D-only, contradiction, missing-evidence, not-comparable, and not-assessed behavior;
- chronology across information dates and UTC recorded/imported/completed timestamps;
- current and historical cutoff reads with no later price, valuation, judgment, claim, evidence, or link leakage;
- later upstream records not mutating an already accepted observation;
- append-only update/delete rejection;
- direct frozen-boundary and source daily-price/ingestion update/delete mutation behavior, proving no indirect rewrite of current or historical payloads;
- atomic rollback with unchanged row counts for every multi-row failure;
- deterministic PostgreSQL concurrent revision allocation;
- fixture-only UUIDv5 semantics, deterministic market-data integer IDs/natural keys, complete payload, all returned IDs, canonical close/basis strings, frozen resolver/stock-basic/canonical-series provenance, collection ordering, normal runtime ID behavior, two clean builds per database, and exact SQLite/PostgreSQL equality;
- strict JSON, invalid cutoff handling, fixed generic 503 behavior, and read-only route inventory;
- imports, FastAPI startup, tests, fixture demo, and API reads performing no network access;
- all existing v0.3-v0.6D regressions and demos.

## Proposed implementation validation gate

The later implementation task must list and report exact results for:

- focused SQLite v0.6E tests;
- focused PostgreSQL v0.6E tests;
- full offline suite;
- full PostgreSQL persistence/Industry Alpha suite when available;
- clean PostgreSQL Alembic `base -> head`;
- previous head -> new head and new head -> previous head -> new head;
- `python -m alembic check`;
- all offline demos;
- explicit no-network coverage;
- `python -m compileall -q backend industry_alpha scripts tests`;
- `git diff --check`;
- final GitHub Actions success on the implementation Head.

This planning PR runs only the current unchanged offline test suite and local fixture demo requested by Issue #70.

## Explicit exclusions

No target price, fair value, intrinsic value, expected return, upside/downside amount or percentage, discount/premium calculation, risk-reward ratio, numeric score, weight, rank, investment priority, buy/sell/hold label, recommendation, automatic conclusion, good-price judgment, good-timing judgment, timing signal, alert/reminder/task lifecycle, Quant Core link or score, provider collection, scraping, live network, LLM execution, page/UI work, watchlist, portfolio, broker, order, or trading behavior.

Do not add or modify application code, models, migrations, APIs, fixtures, demos, tests, documentation outside this task snapshot, dependencies, Docker, Compose, CI, launchers, authentication, or version metadata in this planning slice.

Do not begin timing judgments, v0.7 Watchlist, release/tag work, or any later roadmap phase. Do not modify PR #38.

## Task-sync validation

Run the unchanged repository commands and report exact results:

- `python -m pytest -q`;
- `python -m scripts.demo_research_flow`.

Before commit, verify that the complete branch diff from `9cc5a0e5dda97efa6b9c7b3a43eb3b5c4ead91ec` contains only `.codex/tasks/issue-70-v06e.md` and passes `git diff --check`.

## Delivery and execution gate

1. Commit and push only this task file on `feat/v06e-price-observation-judgments`.
2. Create Draft PR `[v0.6E] Plan evidence-backed price observation judgments`.
3. Record base/head SHA, the single changed file, proposed frozen boundary, enums, validation, API, fixture/test plan, exact test results, exclusions, and known environment limitations in the PR and Issue #70.
4. Keep the PR Draft/Open/unmerged and Issue #70 Open.
5. Stop for ChatGPT review.

No business implementation may begin until a later GitHub-synchronized review explicitly authorizes it.
