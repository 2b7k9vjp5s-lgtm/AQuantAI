# Stage 2 Query Value Helpers Characterization

## Status

Issue #86 / PR #87 characterized the Stage 2 query-value mechanics. Issue #88 / PR #89 implemented the accepted v0.6A-v0.6C boundary and was squash-merged as `782b2362e1252aa87b21f7aa58f764837f5adb71`.

- Released version remains `0.2.0`.
- Merged capability stage remains v0.6D.
- Migration decision: no migration.
- This record documents completed work and does not authorize another implementation.

## Reviewed scope

The characterization compared:

- `stage2_query.py`;
- `stage2_expectations_query.py`;
- `stage2_assessments_query.py`;
- `stage2_judgments_query.py`.

The corresponding tests exercise public query services rather than private helpers.

## Accepted shared mechanics

v0.6A-v0.6C had identical behavior for:

- required UTC normalization;
- interpreting naive datetimes as UTC without changing wall-clock fields;
- converting aware datetimes to UTC;
- raising `EvidenceLedgerNotVisible` with the exact text `required UTC timestamp is unavailable.` for a missing required timestamp;
- recorded-date visibility against an optional cutoff;
- combined information-date and recorded-date visibility;
- UTC timestamp text ending in `Z`;
- optional ISO date text;
- optional UUID text.

Visibility remains calendar-date granular and inclusive. It does not introduce a time-of-day cutoff.

## Implemented neutral boundary

`industry_alpha.stage2_query_values` now owns:

- `stored_utc`;
- `timestamp_text`;
- `date_text`;
- `uuid_text`;
- `recorded_visible`;
- `dated_visible`.

The v0.6A-v0.6C query modules import these functions under their established private aliases. v0.6B and v0.6C retain local revision-list collection wrappers and delegate only the dated predicate.

## Preserved v0.6D difference

v0.6D has equivalent valid-datetime conversion but its local UTC/timestamp helpers require non-null values and do not translate `None` into the shared domain visibility error.

`stage2_judgments_query.py` therefore remains unchanged. The accepted implementation does not create a mixed nullable contract or silently alter malformed-input behavior.

## Responsibilities that remain local

The neutral module does not own:

- evidence payload construction or grade counts;
- conflict and missing-evidence text;
- claim, evidence or frozen-link selection;
- ID collection and sorting;
- revision collection wrappers;
- list/detail payload fields or ordering;
- notices;
- aggregate not-found and visibility messages;
- repository loading;
- public contracts;
- v0.6D nullable timestamp policy.

The similar v0.6B-v0.6D evidence serializers remain explicitly excluded. They contain different claim fields, missing-evidence reasons and domain boundaries and require a separate neutral read contract before any extraction.

## Acceptance evidence

Independent implementation review confirmed:

- exact six-file inventory;
- unchanged public payloads, sorting, notices and aggregate errors;
- unchanged v0.6D query module;
- direct coverage for exact missing-timestamp errors, naive/aware UTC conversion, trailing-`Z` formatting, optional date/UUID formatting and cutoff boundaries;
- successful GitHub Actions tests, local fixture demo and cleanup;
- honest reporting that PostgreSQL-focused tests were skipped where `AQUANTAI_TEST_POSTGRES_URL` was unavailable;
- no repository, command, model, schema, fixture, API, provider, dependency, CI, UI, release or migration change.

## Current conclusion

The minimal v0.6A-v0.6C query-value extraction is complete. No additional query-value implementation is active.

The next candidate is an independent characterization of a neutral evidence read-serialization contract. That work may conclude the serializers should remain local and does not receive implementation authorization from this report.