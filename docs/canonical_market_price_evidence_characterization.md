# Canonical Market-Price Evidence Characterization

## Status and authority

- Architecture Preflight and characterization: Issue #124.
- Required base: `b2bb75fbbd10ad765b99e8a0dee3d57f6aaae54e`.
- Work type: documentation-only architecture characterization.
- Released version remains `0.2.0`; merged capability remains v0.6D.
- Accepted application/consolidation implementation baseline remains
  `7705b7caf210d606473db6f24c5fadfad4918646`.
- Migration, schema, dependency, provider, API and runtime decisions: no change.

This report is descriptive and does not authorize production code, a price model,
comparison eligibility, v0.6E or v0.7.

## Executive decision

A standalone canonical market-price evidence contract has independent user value.
It would provide one auditable point-in-time representation of a market-price
measurement that can be inspected directly and reused by later research features
without allowing each downstream feature to reinterpret a raw float, provider
row or valuation field.

No production implementation currently reaches Definition of Ready.

The existing repository has strong provider, complete-snapshot, series and cutoff
provenance, but it does not yet provide all of the following as one accepted
contract:

- explicit price measurement kind;
- explicit price dimension/unit and currency from a reviewed source contract;
- a price-specific positive canonical decimal rule;
- durable historical meaning independent of later source-row metadata changes;
- one accepted ownership choice between a projection and an append-only evidence
  record;
- comparison eligibility kept separate from the measurement itself.

The next permissible gate is another bounded Architecture Preflight for explicit
provider price semantics and historical freezing. It is not an implementation
Issue.

## Current source boundaries

### Provider-normalized daily-price row

`datasource.base.DAILY_PRICE_COLUMNS` contains:

- `trade_date`;
- `stock_code`;
- `open`, `high`, `low`, `close`;
- `volume`, `amount`;
- `adjust_type`;
- `source`.

The provider contract therefore describes normalized OHLCV rows, not canonical
price evidence. It has no measurement-kind field, price dimension, currency,
observation timestamp, source-row identifier, ingestion-run identity or series
identity. `adjust_type` distinguishes empty, qfq and hfq policies, but the
contract does not define which of those values is suitable for a later
like-for-like valuation comparison.

### Persisted source row and ingestion provenance

`DailyPriceRecord` stores the normalized OHLCV values as SQLAlchemy `Float`
columns and retains:

- an integer source-row ID;
- the exact ingestion-run foreign key;
- source/provider token;
- stock code;
- trade date;
- adjustment type.

`IngestionRun` stores provider, canonical series key and payload, requested scope,
requested dates, information cutoff, adapter/contract versions, request metadata,
status, imported timestamp and completion timestamp.

This is strong ingestion provenance. It is still a source-data contract rather
than a canonical measurement contract because:

- price values remain binary floats;
- unit and currency are absent;
- measurement meaning is implied by the selected OHLC column;
- a source-row foreign key alone does not freeze the row's material meaning into
  a downstream accepted record;
- the reviewed persistence surfaces do not establish a separate append-only
  evidence identity for one selected price measurement.

### Canonical snapshot-series identity

`SnapshotSeriesIdentity` prevents incompatible complete snapshots from competing
under one latest-series selector. Its canonical payload includes provider,
dataset bundle, contract version, exact stock-code scope, requested date range,
adjustment type, snapshot mode, stock-code semantics and compatibility
parameters. The stable series key is the SHA-256 identity of that canonical
payload.

This identity is necessary provenance for canonical price evidence. It is not
sufficient by itself because a series identifies compatible snapshots, not one
instrument/date/measurement value, unit or currency.

### Latest-series and cutoff-aware read

`MarketDataRepository.read_daily_price` requires an explicit provider and series
key or validated selector. It can restrict trade dates and choose the latest
successful complete snapshot whose information cutoff is not later than an
optional cutoff.

The returned DataFrame intentionally reproduces only `DAILY_PRICE_COLUMNS`. It
does not expose source-row ID, ingestion-run ID, series canonical payload,
import/completion timestamps, contract/adapter versions or a canonical decimal
value. It is a deterministic market-data read, not a durable evidence object.

The current `as_of_cutoff` selector is date-granular. A later evidence contract
also needs UTC visibility: the selected run must have been imported and completed
by the research record's UTC time. Selecting by information cutoff alone is not
enough for point-in-time evidence.

### v0.6B valuation observation

`Stage2ValuationSnapshotRevision` stores:

- a generic valuation method and metric context;
- optional canonical decimal-text `observed_value`;
- optional unit and currency;
- comparison basis and assumptions;
- status, confidence and chronology;
- an optional `daily_price_id` foreign key.

The command service verifies that a referenced price row exists, belongs to a
successful ingestion run, matches the frozen company source and stock code, and
is visible by information cutoff and UTC import/completion time.

That validation makes the row legitimate context. It does not make the
valuation's `observed_value` a canonical market price:

- `observed_value` is generic across multiples, asset references, historical
  ranges, market context and missing data;
- its unit and currency are optional;
- the generic decimal routine accepts values that a market-price contract may
  need to reject, including zero or negative values;
- the value is supplied by the valuation command rather than derived from the
  linked daily-price row;
- the command does not freeze the linked row's close, natural key, canonical
  series payload or complete run provenance into the valuation revision;
- a `daily_price_id` link remains provenance/context only.

### Superseded downstream v0.6E plan

Issue #70 and Draft PR #71 attempted to solve missing price semantics inside a
future price-observation judgment through a provider-specific resolver and a
revision-owned audit copy. That work was closed without merge and is not an
accepted design.

It remains useful as negative architecture evidence: solving currency, unit,
float normalization and historical provenance separately in every downstream
feature would duplicate policy and make the first consumer the accidental owner
of a reusable market-data concept.

## Independent user value

Canonical market-price evidence has independent value when it supports all of
these uses without creating investment advice:

1. inspect the exact price measurement that was visible at a historical cutoff;
2. audit provider, series, run and source-row provenance;
3. compare current and historical source snapshots without silently changing the
   meaning of an accepted research record;
4. supply a reusable input to a later, separately accepted comparison-eligibility
   decision;
5. support descriptive research while preserving missing or ambiguous
   provenance.

The evidence contract must not calculate fair value, expected return, discount,
premium, upside, downside, ranking, recommendation, good price or good timing.

## Required boundary distinctions

| Boundary | Current owner | Meaning |
| --- | --- | --- |
| Provider-normalized row | `datasource` provider contract | Transport-normalized OHLCV values for one provider call |
| Persisted source row | v0.3 market-data persistence | One row in one immutable-attempt/complete-snapshot provenance chain |
| Latest-series read | `MarketDataRepository` | Deterministic reconstruction of one selected compatible snapshot |
| Canonical market-price evidence | Future separately reviewed market-data/evidence owner | One exact measurement with canonical value, dimension, currency, chronology and frozen provenance |
| v0.6B valuation observation | Stage 2 valuation domain | Research observation that may describe many valuation dimensions; not automatically market price |
| Comparison eligibility | Future separate deterministic policy | Whether two exact evidence values are dimensionally and evidentially comparable |
| Price judgment/read state | Conceptual later workflow | A descriptive research conclusion, if ever authorized; not the measurement itself |

No downstream layer may collapse these boundaries.

## Minimum conceptual evidence contract

The following is the minimum semantic inventory for a future contract. It is not
a schema authorization.

### Measurement identity

One evidence item must identify exactly:

- one instrument under an explicit provider/source identity;
- one exact trade date;
- one measurement kind;
- one adjustment policy;
- one canonical series;
- one successful complete-snapshot ingestion run;
- one exact persisted source row and natural key.

A stock code alone is not a globally unique instrument identity. Any exchange or
market identity used by the contract must come from an explicit reviewed source
field or provider contract. It must not be inferred from code prefixes, names or
free text.

### Measurement kind

The smallest plausible initial kind is `daily_close`. Open, high, low, volume,
amount, benchmark, sector and intraday measurements are different contracts and
must not be admitted implicitly.

The measurement kind must be explicit even when the source column is fixed. A
consumer must never infer that an arbitrary numeric field means close price.

### Value representation

A future price value must be canonical decimal text, not a JSON float.

The only plausible conversion from the currently persisted source float is:

1. reject booleans and non-numeric or non-finite values;
2. require a price-specific positive value;
3. convert with `Decimal(str(source_value))`, never `Decimal(source_value)`;
4. render deterministic plain decimal text without exponent notation or
   insignificant trailing zeros;
5. apply an explicitly reviewed maximum length and fractional scale;
6. freeze the source float only as audit provenance, never as the comparison
   value.

The existing v0.6B `_decimal_text` routine is useful prior art but cannot be
adopted unchanged as the price contract because it is generic and does not impose
positive-price or reviewed scale semantics.

The maximum price scale remains unresolved. Reusing the superseded PR #71
proposal would be an unreviewed decision.

### Unit and currency

A price evidence item needs both:

- a stable dimension such as currency per ordinary share; and
- an explicit currency, normally an ISO 4217 code.

The current generic provider and persistence contracts do not supply those
fields. `StockBasicRecord.exchange` may be useful provenance, but exchange tokens
can be blank or provider-specific and no accepted generic mapping currently
turns them into unit/currency semantics.

Unit or currency must never be:

- borrowed from a v0.6B valuation revision;
- inferred from stock-code prefix or suffix;
- parsed from security name or free text;
- defaulted from provider name alone;
- converted through implicit FX;
- filled through silent fallback.

A future provider price-semantics contract must supply or deterministically map
these fields through an independently reviewed, versioned rule.

### Adjustment meaning

The empty adjustment policy, qfq and hfq are distinct series identities and must
never be mixed.

For a future like-for-like market-price comparison, only an explicitly reviewed
unadjusted daily close is a plausible initial candidate. qfq and hfq values are
transformed time-series observations whose numeric level depends on an adjustment
method and reference basis. They may remain useful for descriptive return or
charting work, but they must not be silently treated as the same per-share market
price.

This report does not authorize an unadjusted-only implementation; it records the
minimum safe direction for later review.

### Provenance

A future item must retain or freeze at least:

- daily-price source-row ID and full natural key;
- ingestion-run ID and batch identifier;
- provider/source;
- canonical series key and canonical payload;
- requested stock scope and dates;
- adjustment policy;
- dataset, snapshot mode and contract version;
- adapter version and public compatibility parameters;
- trade date;
- information cutoff date;
- imported and completed UTC timestamps;
- source numeric value and canonical decimal text;
- explicit measurement kind, unit and currency;
- the versioned rule that established unit/currency and adjustment eligibility.

Provider request metadata must remain sanitized. Credentials or raw connection
details never enter the evidence payload.

### Point-in-time visibility

Selection must satisfy both information and system chronology:

- trade date is not later than the evidence cutoff;
- ingestion-run information cutoff is not later than the evidence cutoff;
- imported UTC is not later than completed UTC;
- completed UTC is not later than the consuming research record's recorded UTC;
- the exact provider and series selector are explicit;
- later successful runs or corrected rows do not rewrite historical evidence.

A date-only latest-series read cannot by itself prove all of these conditions.

### Missing and ambiguous state

Absence is not zero and ambiguity is not a default. A future contract needs
explicit machine-readable reasons such as:

- source row not found;
- series selector missing or ambiguous;
- ingestion run incomplete or not visible;
- numeric value invalid;
- adjustment policy unsupported;
- unit unknown;
- currency unknown;
- instrument identity incomplete;
- source provenance inconsistent.

The exact vocabulary remains a later review decision. Missing or ambiguous
measurements must not create a numeric evidence value.

### Deterministic output

Current and historical payloads must use canonical strings for decimal values,
compact date strings, timezone-aware UTC strings, explicit ordering and strict
JSON with non-finite numbers rejected. SQLite and PostgreSQL must produce the same
semantic payload.

## Comparison eligibility remains separate

A valid canonical price measurement is necessary but not sufficient for a
valuation comparison.

A later eligibility contract must independently verify at least:

- the valuation value is a supported, explicit point rather than a multiple,
  ratio, range, aggregate value or missing-data record;
- both values have the same dimension and currency;
- both are visible at the relevant cutoff and UTC time;
- adjustment semantics are compatible;
- evidence status and contradictions permit comparison;
- no FX, unit conversion or free-text parsing is required.

Eligibility must never mutate either source evidence item. It should produce a
separate deterministic decision or failure reason.

## Candidate evaluation

| Candidate | Strengths | Blocking problems | Decision |
| --- | --- | --- | --- |
| Deterministic read-only projection over existing rows/runs | No migration; can reuse explicit provider/series/cutoff selection and current provenance | Current reads omit row/run metadata; unit/currency are unresolved; date-only cutoff is insufficient; accepted historical meaning would depend on mutable source metadata unless fully frozen by every consumer | Plausible inspection surface, not durable canonical evidence and not DoR |
| Standalone append-only canonical measurement/evidence record | Correct reusable ownership; can freeze value and provenance once; downstream features can link exact evidence | Requires a new schema/migration, price-semantics source contract, immutability/selection rules, decimal scale, missing-state vocabulary and cross-database matrix | Preferred architectural direction, but not DoR |
| Revision-owned downstream audit copy | Can preserve one consumer's historical payload and rollback atomically | Repeats resolver/value/provenance policy in every consumer; makes v0.6E or another feature the accidental market-price owner; difficult to reuse and compare consistently | Rejected as canonical owner; a consumer may later freeze an exact canonical evidence ID |
| Enrich or replace normalized `daily_price` contract | Unit/currency could travel with all rows and providers | Broad provider/persistence/migration compatibility change; mixes transport normalization with accepted evidence semantics; existing historical rows require reinterpretation; still does not create an accepted point-in-time evidence identity | Too broad and not DoR |

## Ownership decision

The preferred future owner is a separately reviewed market-data/evidence layer,
not the Stage 2 valuation or price-judgment domain.

That owner should consume exact persisted source rows and ingestion provenance.
Stage 2 may later link an exact canonical evidence identity, but it must not own
provider interpretation, series selection, decimal conversion, unit/currency
resolution or source-row freezing.

This ownership decision is architectural direction only. No module name, table
name or public API is reserved by this report.

## Definition of Ready decision

No production implementation reaches Definition of Ready.

The standalone append-only evidence direction is the best fit, but the following
material contracts remain unresolved:

1. **Provider price semantics:** at least one implemented provider must supply a
   reviewed, versioned, credential-free rule for instrument identity,
   `daily_close`, unit, currency and adjustment meaning without code/name/free-text
   inference.
2. **Historical freezing:** decide whether the evidence row copies the minimum
   material provenance or relies on separately enforced immutable source rows.
3. **Decimal limits:** accept the maximum canonical length and scale for price
   values and prove cross-database equality.
4. **Selection surface:** define an exact row selector that includes provider,
   series, instrument, trade date, adjustment and measurement kind and fails
   closed on ambiguity.
5. **Visibility:** combine information cutoff with imported/completed UTC
   visibility in one deterministic contract.
6. **Missing-state vocabulary:** accept bounded reasons without manufacturing a
   numeric value.
7. **Migration and rollback:** define one forward schema only after the contract
   above is stable.

Creating a table, dataclass, resolver or API before these decisions would merely
move ambiguity into code.

## Smallest next gate

A later separately authorized Architecture Preflight may characterize an explicit
provider price-semantics descriptor and a deterministic fixture matrix. It should
answer, without network access or schema changes:

- which persisted provider/contract combinations can prove instrument market,
  daily-close meaning, unit and currency;
- whether blank or provider-specific exchange values fail closed;
- whether only unadjusted rows are admitted;
- exact float-to-decimal length and scale rules;
- exact row/run/series selector and UTC visibility;
- the minimum frozen provenance required for historical stability.

That gate may conclude that no current provider is sufficient. It must not use a
live credential, reopen Hithink integration, change AKShare behavior or authorize
v0.6E.

## Migration, rollback and dependency

- Migration: none in this characterization.
- Persisted schema: unchanged.
- Dependency: unchanged.
- Runtime/API/provider behavior: unchanged.
- Rollback: documentation reversion only.

## Explicit non-goals

This work does not authorize:

- a canonical price table, model, repository, service or endpoint;
- a unit/currency resolver;
- changes to `DataProvider`, AKShare, Hithink or normalized columns;
- source-row mutation policy or database triggers;
- valuation comparison eligibility;
- a target price, fair value, expected return, discount/premium, score, rank,
  recommendation, good-price or good-timing state;
- v0.6E, v0.7, Watchlist, portfolio, broker, order or trading behavior;
- migration, release, tag or version changes;
- modification of PR #38.
