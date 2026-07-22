# Canonical Price and Comparison Eligibility v1 — Architecture Preflight

## 1. Decision summary

Canonical Price and Comparison Eligibility v1 is an additive, local-first market-data contract. It creates no new Provider, performs no external request, changes no existing market-data row and does not calculate valuation attractiveness, expected return, ranking or recommendation.

The accepted design separates four meanings that must not be collapsed:

1. **Provider-normalized source observation (L1)** — existing `DailyPriceRecord` plus its exact `IngestionRun`.
2. **Explicit listed-instrument identity** — locally recorded market, exchange, currency and listing chronology; never inferred from a code prefix, company name, Provider or UI context.
3. **Canonical price revision (L3 inside AQuantAI's reviewed contract)** — one deterministic decimal value created from one exact L1 observation under one exact versioned series contract.
4. **Comparison Eligibility (D2)** — a separate versioned assessment that states whether exact canonical-price revisions satisfy one named comparison purpose. Eligibility is not a score, ranking, valuation conclusion or recommendation.

V1 supports only the eligibility purpose `company_research_price_context_v1`. It authorizes exact canonical close-price context to be displayed or frozen by downstream research. It does **not** authorize arithmetic across companies, raw-price magnitude comparison, expectation-gap computation, fair value, target price, expected return or price-attractiveness labels.

A later comparison purpose, such as normalized return-window inputs or valuation-metric comparison, requires a separate reviewed rule version and may require additional contracts.

## 2. Authority and scope

- GitHub Issue: #175
- Required base: `22c1951ba23c495cc6070b948149f4118a86ab6d`
- Risk tier: Strict
- Roadmap: Issue #137, parallel market-price infrastructure track
- Owner authorization: `审核完成，继续` on 2026-07-22
- Current released version remains `0.2.0`

This document is architecture only. It does not authorize production code, migration execution, Provider changes, network access, release or version changes.

## 3. Existing state and non-negotiable boundaries

### 3.1 Existing L1 source observations

`DailyPriceRecord` currently stores:

- exact `ingestion_run_id`;
- `source` and `stock_code`;
- `trade_date`;
- OHLC values as Python/SQL floating-point numbers;
- volume and amount;
- Provider-specific `adjust_type`.

`IngestionRun` owns:

- one explicit Provider and dataset;
- one series identity and series key;
- requested scope and dates;
- information cutoff;
- adapter and contract versions;
- status and completion time.

These rows remain Provider-normalized L1 observations. They are not relabeled L2 or L3 and are never mutated or backfilled by Canonical Price.

### 3.2 Existing identity limitations

`StockBasicRecord.exchange` is Provider-normalized text. It is not an accepted exchange identity. Existing security codes, names, exchange text and Provider labels cannot establish:

- stable listed-instrument identity;
- ISO MIC or equivalent accepted exchange identity;
- market identity;
- currency;
- security type;
- listing or delisting chronology;
- corporate-action adjustment meaning.

The new contract therefore requires an explicit listed-instrument revision before any canonical-price write.

### 3.3 Existing Stage 2 and product behavior

Existing valuation observations may reference one `DailyPriceRecord`. That reference remains L1 source context and is not automatically upgraded or rebound.

Company Research Comparison Matrix v1, merged through PR #174, remains component-only. It must not display or compute canonical price until a later implementation explicitly consumes this reviewed contract.

## 4. Semantic-level contract

### 4.1 L0 — raw Provider data

L0 is the Provider payload before internal normalization. The current database does not retain a universal exact raw lexical decimal for every `DailyPriceRecord`; therefore L0 is not reconstructed from the float value.

### 4.2 L1 — Provider normalized

Existing `DailyPriceRecord` is L1. L1 retains Provider meaning and may have:

- Provider-specific code aliases;
- Provider-specific adjustment labels;
- incomplete market/exchange/currency identity;
- binary floating-point representation;
- no cross-Provider comparability.

### 4.3 L2 — standardized source value

The future canonicalization command first creates a deterministic standardized decimal candidate from one exact L1 close value.

V1 decimal conversion rule is exactly:

- rule code: `float_repr_decimal_v1`;
- reject NaN, positive infinity and negative infinity;
- convert the Python round-trip representation of the source float to `Decimal`;
- quantize to the exact `decimal_scale` recorded by the accepted price-series contract;
- rounding mode: `ROUND_HALF_EVEN`;
- preserve the pre-quantized decimal text and final decimal text in the candidate/write manifest;
- record numeric fidelity as `binary_float_normalized`.

This rule is deterministic but does not recreate a lost Provider lexical decimal. The fidelity limitation remains visible in every canonical-price read.

### 4.4 L3 — canonical inside the reviewed AQuantAI contract

A value reaches L3 only when all of the following are bound and validated:

- exact listed-instrument revision;
- exact market code;
- exact exchange MIC or explicitly accepted exchange code namespace;
- exact ISO-4217 currency code;
- exact unit `currency_per_share`;
- exact price kind `official_close`;
- exact adjustment basis from the closed v1 vocabulary;
- exact trade date;
- exact price-series contract revision;
- exact succeeded `IngestionRun`;
- exact `DailyPriceRecord`;
- deterministic decimal conversion rule, scale and rounding;
- information cutoff and recorded UTC;
- append-only revision and source provenance.

L3 means canonical for AQuantAI's reviewed local research contract. It does not claim exchange certification, official redistribution status or recovery of the original Provider decimal text.

## 5. Closed vocabularies

### 5.1 Market and listing

- `security_type`: `common_equity`
- `listing_status`: `active`, `suspended`, `delisted`
- `currency_code`: uppercase ISO-4217 code
- `exchange_code_namespace`: `ISO_MIC` or another explicitly reviewed namespace

V1 does not infer a MIC from `StockBasicRecord.exchange`.

### 5.2 Price

- `price_kind`: `official_close`
- `unit_code`: `currency_per_share`
- `adjustment_basis`: `unadjusted`, `forward_adjusted`, `backward_adjusted`
- `numeric_fidelity`: `binary_float_normalized`
- `canonical_status`: `accepted`, `conflicting`, `rejected`

Provider `adjust_type` values are never mapped by string convention. The accepted series-contract revision records the exact source value and explicit canonical adjustment basis.

### 5.3 Comparison Eligibility

- `purpose_code`: `company_research_price_context_v1`
- `state`: `eligible`, `ineligible`, `missing`, `stale`, `conflicting`, `not_applicable`
- `rule_version`: `aquantai.company-research-price-context-eligibility.v1`

Reason codes are a deterministic, sorted tuple chosen from:

- `canonical_price_accepted`
- `canonical_price_missing`
- `canonical_price_not_visible`
- `canonical_price_conflicting`
- `canonical_price_rejected`
- `instrument_revision_mismatch`
- `market_missing`
- `exchange_missing`
- `currency_missing`
- `unit_mismatch`
- `price_kind_mismatch`
- `adjustment_basis_mismatch`
- `trade_date_mismatch`
- `source_contract_mismatch`
- `source_run_not_succeeded`
- `source_numeric_fidelity_disclosed`
- `stale_for_requested_context`
- `purpose_not_supported`

## 6. Listed-instrument identity

### 6.1 Ownership

The listed-instrument contract owns accepted market, exchange, currency and listing chronology. It does not own issuer fundamentals, Company Research or Provider source rows.

### 6.2 Recording rule

A future local command records one listed-instrument revision from explicit structured input. Required fields:

- stable `instrument_key` supplied by the user or migration fixture;
- canonical symbol;
- security type;
- market code;
- exchange code namespace;
- exchange code;
- currency code;
- listing date;
- optional delisting date;
- listing status;
- explicit `recorded_by`;
- information cutoff date;
- recorded UTC;
- expected latest revision when appending.

No field is derived from code prefix, Provider name, company name, free text or AI output.

### 6.3 Source alias binding

A price-series contract revision binds one exact source alias:

- Provider;
- dataset;
- series key;
- source stock code;
- source adjustment type;
- exact listed-instrument revision.

The alias belongs to that series contract and does not become a global identity inference rule.

## 7. Candidate persistence model

All tables are additive, append-only and UUID-keyed unless an existing project convention requires another deterministic identifier.

### 7.1 `listed_instruments`

Stable identity fields:

- `id`
- `instrument_key` — unique, explicit, immutable
- `created_at_utc`

### 7.2 `listed_instrument_revisions`

Fields:

- `id`
- `instrument_id`
- `revision_no`
- `canonical_symbol`
- `security_type`
- `market_code`
- `exchange_code_namespace`
- `exchange_code`
- `currency_code`
- `listing_date`
- `delisting_date`
- `listing_status`
- `recorded_by`
- `information_cutoff_date`
- `recorded_at_utc`
- `supersedes_revision_id`

Constraints:

- unique `(instrument_id, revision_no)`;
- positive revision number;
- exact closed vocabularies;
- uppercase currency and exchange namespace/code normalization;
- delisting date cannot precede listing date;
- supersedes must reference the same instrument and previous revision;
- ordinary ORM update/delete rejected.

### 7.3 `canonical_price_series`

Stable identity fields:

- `id`
- `series_contract_key` — unique, explicit, immutable
- `instrument_id`
- `created_at_utc`

### 7.4 `canonical_price_series_revisions`

Fields:

- `id`
- `series_id`
- `revision_no`
- `instrument_revision_id`
- `provider`
- `dataset`
- `series_key`
- `source_stock_code`
- `source_adjust_type`
- `price_kind`
- `adjustment_basis`
- `unit_code`
- `currency_code`
- `decimal_scale`
- `decimal_rule_code`
- `rounding_mode`
- `status`: `draft`, `accepted`, `retired`
- `recorded_by`
- `information_cutoff_date`
- `recorded_at_utc`
- `supersedes_revision_id`

Constraints:

- unique `(series_id, revision_no)`;
- one accepted cutoff-visible series revision for one exact series identity at a time;
- `price_kind = official_close`;
- `unit_code = currency_per_share`;
- `decimal_rule_code = float_repr_decimal_v1`;
- bounded decimal scale, proposed `0..10`;
- series currency must equal the frozen instrument-revision currency;
- no mutation or delete.

### 7.5 `canonical_prices`

Stable natural identity fields:

- `id`
- `series_id`
- `trade_date`
- `price_kind`
- `adjustment_basis`
- `created_at_utc`

Constraint:

- unique `(series_id, trade_date, price_kind, adjustment_basis)`.

### 7.6 `canonical_price_revisions`

Fields:

- `id`
- `canonical_price_id`
- `revision_no`
- `series_revision_id`
- `instrument_revision_id`
- `source_daily_price_id`
- `source_ingestion_run_id`
- `source_value_text`
- `standardized_value_text`
- `value_decimal` — proposed `NUMERIC(28,10)`
- `numeric_fidelity`
- `currency_code`
- `unit_code`
- `trade_date`
- `canonical_status`
- `conflict_summary`
- `recorded_by`
- `information_cutoff_date`
- `recorded_at_utc`
- `supersedes_revision_id`

Constraints:

- unique `(canonical_price_id, revision_no)`;
- exact source row belongs to exact succeeded source run;
- source row code, trade date, Provider and adjustment type match the frozen series revision;
- instrument, currency, unit, price kind and adjustment basis match the frozen series revision;
- accepted value is positive and finite;
- `conflicting` requires non-empty conflict summary;
- `accepted` forbids conflict summary;
- no mutation or delete.

A new source observation or corrected series contract appends a new canonical-price revision. It never overwrites the prior revision.

### 7.7 `comparison_eligibility_assessments`

Stable identity fields:

- `id`
- `assessment_key`
- `purpose_code`
- `created_at_utc`

### 7.8 `comparison_eligibility_revisions`

Fields:

- `id`
- `assessment_id`
- `revision_no`
- `rule_version`
- `state`
- `reason_codes` — deterministic sorted strict JSON array
- `requested_trade_date`
- `recorded_by`
- `information_cutoff_date`
- `recorded_at_utc`
- `supersedes_revision_id`

Constraints:

- unique `(assessment_id, revision_no)`;
- one closed v1 purpose and rule version;
- state/reason consistency;
- no mutation or delete.

### 7.9 `comparison_eligibility_members`

Fields:

- `id`
- `eligibility_revision_id`
- `position`
- `canonical_price_revision_id`
- `recorded_at_utc`

Constraints:

- unique `(eligibility_revision_id, position)`;
- unique `(eligibility_revision_id, canonical_price_revision_id)`;
- nonnegative position;
- member revision must be visible and accepted for `eligible` state;
- no mutation or delete.

## 8. Canonicalization command boundary

Candidate commands:

```text
python -m scripts.record_listed_instrument --input <local-json-path>
python -m scripts.record_canonical_price_series --input <local-json-path>
python -m scripts.record_canonical_price --input <local-json-path>
python -m scripts.record_price_comparison_eligibility --input <local-json-path>
```

Every command must:

- accept local structured input only;
- perform no network access;
- require explicit IDs and `recorded_by`;
- require information cutoff and recorded UTC;
- support dry-run manifest output;
- validate expected-latest revision;
- re-read exact frozen graph inside one transaction;
- commit identity, revision and links atomically;
- fail closed with credential-safe errors;
- never infer market, exchange, currency, unit, adjustment or source selection.

## 9. Canonicalization validation sequence

For one requested canonical-price write:

1. parse strict input and reject unknown fields;
2. load exact listed-instrument revision;
3. load exact accepted price-series revision;
4. load exact `DailyPriceRecord` and exact `IngestionRun`;
5. require source run status `succeeded`;
6. require Provider, dataset, series key, source code, trade date and source adjustment type to match the series revision;
7. require source `close` to be finite and positive;
8. apply `float_repr_decimal_v1` and exact quantization;
9. require instrument, currency, unit, price kind and adjustment basis consistency;
10. validate chronology and expected latest revision;
11. produce deterministic dry-run manifest;
12. revalidate inside the write transaction;
13. append canonical-price identity/revision and source links atomically.

No fallback source row is selected when the requested row fails.

## 10. Comparison Eligibility v1 rule

Purpose `company_research_price_context_v1` evaluates one or more exact canonical-price revisions for display/freeze as research price context.

### Eligible

State is `eligible` only when every member:

- exists and is visible at both requested as-of boundaries;
- has `canonical_status = accepted`;
- uses `price_kind = official_close`;
- uses `unit_code = currency_per_share`;
- has explicit market, exchange and currency;
- matches the requested trade date;
- has a visible accepted series-contract revision;
- links an exact succeeded source run and exact source observation;
- discloses numeric fidelity.

The rule does not require all members to share the same currency because v1 does not calculate or rank values across members. Currency remains visible per member. A later arithmetic comparison purpose must define same-currency or explicit FX rules separately.

### Ineligible

Use `ineligible` for a complete, visible graph that violates the supported purpose, such as wrong price kind, unit or requested trade date.

### Missing

Use `missing` when a required canonical-price or identity record does not exist.

### Stale

Use `stale` when the exact canonical price exists but falls outside the requested context's explicit freshness rule. V1 does not invent a default freshness window; the caller must provide the requested trade date.

### Conflicting

Use `conflicting` when the canonical-price revision or source graph is explicitly conflicting or impossible duplicates are present.

### Not applicable

Use `not_applicable` when the requested purpose is unsupported or the target has no meaningful market price under this contract.

## 11. Read-only API candidates

```text
GET /market-data/listed-instruments/{instrument_id}?as_of_cutoff=YYYY-MM-DD&as_of_recorded_at_utc=<UTC>
GET /market-data/canonical-prices/{canonical_price_id}?as_of_cutoff=YYYY-MM-DD&as_of_recorded_at_utc=<UTC>
GET /market-data/comparison-eligibility/{assessment_id}?as_of_cutoff=YYYY-MM-DD&as_of_recorded_at_utc=<UTC>
```

Rules:

- exact UUID selector only;
- both as-of boundaries required;
- no default current time;
- no symbol/name/code-prefix lookup;
- no similarity or fallback;
- expose exact revisions, source IDs, rule version, reason codes and fidelity;
- load no unrelated Provider rows;
- no network;
- no valuation, ranking or recommendation fields.

## 12. Cutoff, chronology and historical freeze

A record is visible only when:

- its information cutoff is on or before `as_of_cutoff`; and
- its recorded UTC is on or before `as_of_recorded_at_utc`.

All frozen upstream revisions and links must also be visible. A later accepted listing, series, canonical-price or eligibility revision never replaces an older frozen revision in a historical read.

Downstream records that require reproducibility must freeze:

- exact listed-instrument revision;
- exact series-contract revision;
- exact canonical-price revision;
- exact Comparison Eligibility revision and rule version.

No automatic relinking is allowed.

## 13. Migration candidate

Candidate migration name:

`20260722_0013_canonical_price_comparison_eligibility.py`

The migration creates only the nine new tables listed above. It does not:

- alter `ingestion_runs`;
- alter `stock_basic`;
- alter `daily_price`;
- alter any Evidence Ledger table;
- alter any Stage 1 or Stage 2 table;
- backfill existing rows;
- infer market, exchange or currency;
- relink valuation observations.

Upgrade is atomic.

Downgrade must first verify all nine tables are empty. If any row exists, downgrade fails before dropping any table. Empty downgrade drops in reverse dependency order in one transaction where supported.

## 14. Production-realistic offline golden path

Fixture prerequisites:

- one succeeded `IngestionRun` with Provider `fixture`, dataset `daily_price`, exact series identity and explicit cutoff;
- one `StockBasicRecord` and one `DailyPriceRecord` reachable through normal persistence;
- source close is finite and positive;
- no external request.

Path:

1. record listed instrument `fixture-cn-equity-000001` with explicit market `CN_A`, exchange namespace `ISO_MIC`, exchange `XSHE`, currency `CNY`, security type `common_equity` and listing date;
2. record accepted series contract binding the exact fixture Provider, dataset, series key, source code and source adjustment type to `official_close`, `currency_per_share` and explicit adjustment basis;
3. dry-run canonicalization and assert deterministic source/standardized decimal text;
4. append one accepted canonical-price revision linked to the exact source row and run;
5. append one `company_research_price_context_v1` eligibility revision with the exact canonical-price revision as member;
6. read all three surfaces at explicit as-of boundaries;
7. verify exact IDs, chronology, rule version, reason codes, numeric fidelity and no hidden network.

## 15. Primary failure path

Use an exact `DailyPriceRecord` whose source alias appears compatible but whose listed-instrument revision lacks accepted exchange or currency.

Expected behavior:

- dry-run fails before any identity or revision insert;
- no code-prefix or Provider inference occurs;
- no alternative source row is selected;
- error reports a stable public code such as `canonical_identity_incomplete`;
- private database details and credentials are absent;
- transaction writes zero rows.

Additional fail-closed cases:

- source run not succeeded;
- wrong series key;
- duplicate exact source natural key;
- non-finite or nonpositive source close;
- incompatible adjustment basis;
- expected latest revision changed;
- later information outside either as-of boundary;
- eligibility member is conflicting or rejected.

## 16. Testing requirements for future implementation

### Persistence and migration

- all new histories are append-only;
- revision numbers and supersedes chains are deterministic;
- no existing table is altered or backfilled;
- populated downgrade refuses before any drop;
- PostgreSQL and supported SQLite constraints behave consistently.

### Identity

- explicit market/exchange/currency required;
- no prefix, name, Provider or free-text inference;
- ambiguous source alias fails closed;
- listing chronology validated.

### Decimal and source provenance

- deterministic `float_repr_decimal_v1` conversion;
- exact scale and `ROUND_HALF_EVEN` behavior;
- NaN/infinity/nonpositive rejection;
- exact source row and succeeded run linkage;
- no Provider mixing or fallback;
- numeric fidelity visible.

### Cutoff and revisions

- both as-of boundaries required;
- later listing, series, price and eligibility revisions excluded;
- historical frozen reads never auto-rebind;
- expected-latest conflicts rollback atomically.

### Eligibility

- every state and reason-code path;
- eligible does not imply arithmetic comparability or attractiveness;
- unsupported purposes return `not_applicable`;
- no score, order, recommendation or target-price wording.

### Network and API

- imports, startup, tests, CI, fixture demos and ordinary reads are network-free;
- exact ID selectors only;
- malformed UUID/date/time rejected;
- private integrity diagnostics redacted.

## 17. Downstream integration boundary

After a future implementation is independently approved and merged, Company Research Comparison may later add only:

- exact canonical close value as contextual data;
- currency, unit, trade date and adjustment basis;
- source and canonical revision provenance;
- numeric fidelity notice;
- explicit Comparison Eligibility state and reason codes.

It still may not add without separate authorization:

- cross-company raw-price ordering;
- expectation-gap calculation;
- valuation normalization;
- fair value or target price;
- expected return or upside/downside;
- attractiveness labels;
- ranking, score, watchlist priority or recommendation.

## 18. Stop conditions

Do not authorize implementation if any of the following remains unresolved:

- listed-instrument market/exchange/currency owner;
- deterministic source alias binding;
- explicit adjustment mapping;
- decimal conversion, scale or rounding;
- append-only revision ownership;
- eligibility purpose and rule meaning;
- as-of chronology;
- populated downgrade safety;
- a production-reachable offline golden path.

Stop and open a new architecture decision if implementation requires:

- Provider or ingestion changes;
- raw-payload retention changes;
- external network access;
- FX conversion;
- corporate-action reconstruction;
- automatic identity inference;
- valuation, expected return, ranking or recommendation.

## 19. Implementation decomposition after approval

The architecture may be implemented in one Strict implementation Issue only if the issue preserves the following internal order:

1. listed-instrument identities and revisions;
2. canonical series contracts and revisions;
3. canonical price identities/revisions and exact source linkage;
4. Comparison Eligibility identities/revisions and members;
5. local commands;
6. read-only APIs;
7. bounded product integration, if separately authorized in that implementation Issue.

The implementation PR must remain Draft until focused tests, full relevant regression, offline golden path, author-side review and one independent fixed-head implementation review succeed.

## 20. Locked exclusions

- no runtime implementation in this preflight;
- no migration execution;
- no Provider, ingestion or external-source changes;
- no network, browsing, scraping or hidden fallback;
- no automatic market, exchange, currency, unit or adjustment inference;
- no mutation or backfill of existing rows;
- no automatic relinking of existing valuation or research records;
- no raw-price magnitude comparison;
- no FX or corporate-action engine;
- no expectation gap, fair value, target price, expected return or upside/downside;
- no ranking, score, recommendation, alerts, portfolio or trading;
- no release, tag or version change.
