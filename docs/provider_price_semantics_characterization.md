# Implemented Provider Price-Semantics Characterization

## Status and authority

- Architecture Preflight and characterization: Issue #128.
- Required base: `03d4f663cc4f8d0612dcf412f4ba78e352188e9f`.
- Work type: documentation-only characterization of implemented contracts.
- Released version remains `0.2.0`; merged capability remains v0.6D.
- Accepted application/consolidation implementation baseline remains
  `7705b7caf210d606473db6f24c5fadfad4918646`.
- Migration, schema, dependency, provider, API and runtime decisions: no change.

This report does not authorize provider changes, live requests, canonical evidence,
comparison eligibility, v0.6E or v0.7.

## Executive decision

No currently implemented provider plus deterministic offline fixture establishes
all minimum semantics required for canonical market-price evidence.

The AKShare path explicitly establishes a bounded daily endpoint call, the raw
close-column mapping, adjustment labels, provider identity, exact snapshot-series
identity, ingestion-run provenance and information-cutoff controls. Those are
necessary and reusable inputs.

The same path does not explicitly establish:

- exact instrument market or exchange identity;
- price dimension or unit;
- currency;
- the economic comparability of unadjusted, qfq and hfq values;
- a price-specific decimal scale and length;
- one deterministic success fixture containing all required semantics;
- an accepted equity endpoint/package compatibility rule narrow enough for a
  durable semantic claim.

The current stock-basic endpoint supplies code and name only. The adapter fills
`exchange` with an empty string, and the deterministic fixture does the same.
A six-digit code, security name, provider name or endpoint name must not be used
to infer exchange, currency or unit.

Therefore neither a production canonical-evidence implementation nor a
source-only provider-semantics descriptor reaches Definition of Ready. A
descriptor over the current rows could only report that required semantics are
missing; implementing that wrapper would not close the architecture gap.

## Reviewed implemented boundaries

### Normalized equity contract

`datasource.base` defines one equity daily-price row with:

- trade date;
- stock code;
- open, high, low and close;
- volume and amount;
- adjustment type;
- source/provider.

The stock-basic row has exchange as a normalized field, but the generic contract
does not require that it be nonblank or define how it maps to currency or price
unit.

The daily-price contract has no explicit measurement-kind, currency, unit,
instrument-market or source-row field. It is a transport-normalized data contract,
not a provider measurement-semantics descriptor.

### AKShare endpoint and adapter mapping

The implemented equity adapter uses exactly:

- `stock_info_a_code_name` for stock code and name;
- `stock_zh_a_hist` for daily OHLCV;
- `tool_trade_date_hist_sina` for open dates.

For daily prices it calls `stock_zh_a_hist` with:

- the explicit six-digit symbol supplied by the caller;
- `period="daily"`;
- explicit start and end dates;
- explicit adjustment value `""`, `qfq` or `hfq`.

The adapter requires the raw daily response to contain date, open, high, low,
close, volume and amount columns. It maps the raw close column to normalized
`close`, records `adjust_type`, sets source to `akshare` and normalizes the date.
Malformed responses fail before contract mapping.

This is sufficient repository evidence for the following narrow statement:

> For one accepted adapter invocation, normalized `close` is the value mapped
> from the raw close column returned by the configured AKShare daily endpoint
> called with `period="daily"` and the recorded adjustment argument.

It is not sufficient to claim that the value is a fully qualified canonical
market price because market identity, unit, currency and adjustment economics
remain absent.

### Stock identity limitation

`stock_info_a_code_name` is normalized from code and name only. The adapter fills:

- `exchange` with an empty string;
- `industry` with an empty string;
- `listing_date` with missing data;
- status with `active`;
- source with `akshare`.

The current deterministic fixture and focused provider fake also contain only code
and name. Existing focused tests verify normalized columns and source but do not
establish a nonblank exchange or market identifier.

Consequences:

- stock code is explicit but market identity is incomplete;
- the same six-digit representation cannot be promoted into a provider-neutral
  instrument identity by prefix rules;
- currency and per-share unit cannot be derived from the persisted stock-basic
  row;
- a canonical measurement must fail closed rather than assign a default market,
  currency or unit.

### Adjustment semantics

The adapter, CLI, persistence validator and snapshot-series identity all preserve
one explicit adjustment value from this closed set:

- empty/unadjusted;
- qfq;
- hfq.

Different adjustment values produce different series identities and are not
mixed by repository reads. This is a strong compatibility boundary.

The repository does not establish the transformation basis, reference date or
economic interpretation required to compare qfq or hfq numeric levels with an
unadjusted per-share market price. The deterministic fixture returns the same
synthetic values for every adjustment argument and therefore verifies label
propagation, not adjustment economics.

The safe characterization is:

- adjustment identity is explicit and preserved;
- the three policies are never interchangeable;
- an empty adjustment is only a plausible future initial candidate;
- even an empty adjustment does not resolve market identity, unit or currency.

### Provider and compatibility provenance

The adapter exposes:

- `ADAPTER_VERSION = "akshare-normalizer-v1"`;
- `ADAPTER_COMPATIBILITY_VERSION = "aquantai.akshare-adapter.v1"`;
- exact equity endpoint identifiers;
- installed AKShare package version in request metadata;
- bounded timeout and retry metadata;
- network mode and collection timestamp.

The equity adapter accepts an AKShare package range from `1.16.0` inclusive to
`2.0.0` exclusive. The exact installed version is recorded in request metadata,
but it is not part of the equity series compatibility parameters. The series
identity includes the adapter compatibility version and endpoint names.

Required columns and numeric validation fail closed against obvious response
shape changes. That does not by itself establish that all endpoint semantics are
identical across every accepted package version. A durable price-semantics claim
needs either:

- a separately accepted adapter compatibility promise supported by deterministic
  fixtures for the semantic fields; or
- a narrower reviewed package/endpoint contract recorded in compatibility
  identity.

This report chooses neither implementation.

### Persistence and series provenance

The existing persistence path provides strong mechanical provenance:

- explicit provider;
- exact stock-code scope and requested date range;
- complete snapshot mode;
- explicit adjustment policy;
- canonical compatibility parameters and SHA-256 series key;
- immutable ingestion attempt and batch identifier;
- contract and adapter versions;
- sanitized provider request metadata;
- information cutoff;
- imported and completed UTC timestamps;
- exact persisted daily-price row ID and ingestion-run foreign key.

Repository reads require an explicit series key or complete validated selector and
select only one latest successful complete snapshot. They do not merge natural
keys across runs.

These mechanics can support a future canonical measurement selector. They do not
supply missing market, unit or currency semantics.

### Information and UTC visibility

The controlled live ingestion command records one timezone-aware UTC collection
timestamp and requires the live information cutoff to equal that UTC calendar
date. Offline fixture and injected-mock modes accept deterministic cutoffs.

The persisted run records imported and completed UTC timestamps. A later evidence
selector can therefore require:

- trade date not after evidence cutoff;
- run information cutoff not after evidence cutoff;
- imported UTC not after completed UTC;
- completed UTC not after the consuming record's recorded UTC.

Current latest-series DataFrame reads expose date-cutoff selection but not the
full row/run provenance in their output. This is a selection-surface issue, not a
provider-semantic substitute.

### Numeric validation

Market-data normalization requires finite, non-negative OHLCV values and coherent
high/low relationships. Values are stored as SQLAlchemy floats.

A future canonical price needs a separate deterministic conversion such as
`Decimal(str(source_value))`, a positive-price rule, plain decimal text and
reviewed maximum scale/length. The implemented provider fixtures use simple
binary floats and do not establish boundary cases for:

- excessive fractional scale;
- very large values;
- zero close;
- negative close;
- float string representations near precision boundaries;
- semantic equality across SQLite and PostgreSQL after canonical conversion.

The current validation is necessary but not a price-specific decimal contract.

## Implemented semantics matrix

| Requirement | Current AKShare path | Evidence state |
| --- | --- | --- |
| Provider | Explicit `akshare` source and run provider | Established |
| Daily frequency | Endpoint called with `period="daily"` | Established for adapter call |
| Close ownership | Raw close column mapped to normalized `close` | Established for adapter mapping |
| Trade date | Explicit normalized date | Established |
| Adjustment identity | Explicit empty/qfq/hfq in row and series | Established as identity, not economic equivalence |
| Exact source row/run/series | Persisted IDs, complete-snapshot series and metadata | Established mechanically |
| Information cutoff | Validated and persisted | Established |
| Imported/completed UTC | Persisted on run | Established |
| Exact market/exchange | Stock-basic exchange is blank | Missing |
| Unit/dimension | Not represented | Missing |
| Currency | Not represented | Missing |
| Price-specific decimal limits | Not represented or fixture-tested | Missing |
| Adjustment economics | Fixture only propagates label | Missing |
| Complete semantic success fixture | No fixture contains market/unit/currency | Missing |

## Offline fixture assessment

### What the fixture proves

`_FrozenAkshareClient` deterministically supplies:

- two six-digit stock codes and names;
- two trade dates;
- one daily OHLCV row pattern per code/date;
- raw close-column mapping;
- bounded date filtering;
- an explicit adjustment argument propagated into normalized rows;
- an open-date calendar;
- no network access.

It is suitable for ingestion, scope, series, chronology and provider-mapping tests.

### What the fixture cannot prove

It supplies no exchange, market, currency or unit. Its price values do not vary by
adjustment policy. It has no canonical decimal boundary cases and no explicit
provider-semantic version payload beyond what the adapter adds as metadata.

The fixture therefore functions as a deterministic **missing-semantics** case for
canonical market-price evidence. It is not a semantic success fixture.

### Missing failure matrix

Existing focused tests cover normalized columns, argument propagation, empty and
malformed responses, bounded timeouts/retries, code-count limits and package
version range. They do not constitute an accepted fixture matrix for:

- blank versus explicit market identity;
- unknown or conflicting currency;
- unit mismatch;
- adjusted-row ineligibility;
- run completed after consuming record time;
- series/provider mismatch at a canonical evidence boundary;
- positive price and decimal scale limits;
- immutable frozen-provenance equality across supported databases.

This report does not authorize adding those tests yet because the success
semantics are still undefined.

## Candidate evaluation

| Candidate | Result | Decision |
| --- | --- | --- |
| Use current AKShare contract as-is | Daily close mapping and provenance exist, but market identity, unit, currency and semantic success fixture are absent | Not DoR |
| Add a versioned descriptor over current rows | Can expose established/missing fields and fail closed, but cannot manufacture the missing success semantics; a wrapper that always blocks is not an implementation milestone | Not DoR |
| Enrich AKShare stock identity through a reviewed explicit source | Could close market identity and support an explicit currency/unit rule, but requires endpoint/source selection, compatibility/version policy, fixture changes and provider behavior review | Preferred next architecture direction; not DoR |
| Use another provider as fallback | Violates the accepted no-silent-fallback and one-provider-per-run/series rules; Hithink is deferred and unverified | Rejected |

## Definition of Ready decision

No production, source-only or test implementation reaches Definition of Ready.

The smallest missing contract is an explicit, credential-free source of
instrument market identity that can be joined to the same provider-specific stock
code without prefix, name or free-text inference. That source must support a
versioned rule establishing:

- stable market/exchange identity;
- daily-close dimension and unit;
- currency;
- provider/endpoint/package compatibility;
- conflict and missing behavior;
- deterministic offline success and failure fixtures.

Until that contract exists, price-specific decimal and canonical evidence schema
work would be premature because a numeric value could not be assigned a verified
dimension or currency.

## Smallest next gate

A later separately authorized Architecture Preflight may inventory explicit,
credential-free AKShare or already implemented repository sources that return a
stable market/exchange field for the exact stock code. It must:

- use documented source fields rather than symbol-prefix inference;
- preserve one provider per run and series;
- define exact join keys and conflict behavior;
- choose a package/endpoint compatibility policy;
- define explicit CNY/unit semantics only when supported by the reviewed source;
- propose one deterministic semantic success fixture and bounded failure fixtures;
- make no live request and change no provider code during characterization.

That gate may conclude that AKShare cannot supply the required identity contract.
It must not reopen Hithink integration or adopt a hidden fallback.

## Migration, rollback and dependency

- Migration: none.
- Persisted schema: unchanged.
- Dependency: unchanged.
- Provider/runtime/API behavior: unchanged.
- Rollback: documentation reversion only.

## Explicit non-goals

This work does not authorize:

- provider endpoint or normalized-contract changes;
- a market/currency resolver;
- prefix-based exchange inference;
- fixture or test changes;
- canonical price models, tables, repositories, services or APIs;
- valuation comparison or price-judgment state;
- live network access, credentials or Hithink work;
- schema, migration, release, tag or version changes;
- v0.6E, v0.7, portfolio, order or trading behavior;
- modification of PR #38.
