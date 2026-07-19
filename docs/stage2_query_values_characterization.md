# Stage 2 Query Value Helpers Characterization

## Status

Issue #86 reviews the Stage 2 query modules at accepted `main` commit `cacf46ac9ccb37d0480e1fd3f02ea5f10da7cb70`. This report is characterization only. Version remains `0.2.0`, capability stage remains v0.6D, and no migration is required.

## Reviewed scope

The review compared:

- `stage2_query.py`;
- `stage2_expectations_query.py`;
- `stage2_assessments_query.py`;
- `stage2_judgments_query.py`.

Corresponding SQLite tests import public query services rather than private query helpers.

## Shared mechanics

v0.6A-v0.6C implement the same behavior for:

- required UTC normalization;
- interpreting naive datetimes as UTC;
- converting aware datetimes to UTC;
- raising `EvidenceLedgerNotVisible` with the exact text `required UTC timestamp is unavailable.` when a required timestamp is absent;
- recorded-date visibility against an optional cutoff;
- combined information-date and recorded-date visibility;
- UTC timestamp text ending in `Z`;
- optional ISO date text;
- optional UUID text.

The visibility rules remain date-granular. They do not introduce a time-of-day cutoff.

v0.6B and v0.6C wrap the dated predicate in local revision-list functions. Those collection wrappers must remain local.

## v0.6D difference

v0.6D has equivalent behavior for valid datetimes, but its local UTC and timestamp helpers require non-null values and do not translate `None` into the domain visibility error.

Replacing them in the first slice would change malformed-input exception behavior. Therefore the first implementation must leave `stage2_judgments_query.py` unchanged. A coherent A/B/C extraction is safer than a mixed nullable contract.

## Safe neutral boundary

A separate implementation Issue may add `industry_alpha/stage2_query_values.py` containing only stateless value functions equivalent to:

- required stored-UTC normalization;
- timestamp, date and UUID text formatting;
- recorded visibility;
- combined information-date and recorded-date visibility.

Required behavior:

1. missing required timestamps keep the exact existing exception class and text;
2. naive datetime wall-clock fields are preserved and assigned UTC;
3. aware datetimes use normal UTC conversion;
4. timestamp text uses ISO 8601 with `Z`;
5. optional date and UUID values preserve `None`;
6. visibility predicates preserve equal-date visibility;
7. no repository, session, payload or database behavior is added.

## First implementation candidate

A later implementation Issue may authorize only:

1. add the neutral query-value module;
2. delegate existing private helpers in v0.6A-v0.6C through import aliases or equivalent minimal wrappers;
3. keep v0.6B/v0.6C revision-list collection logic local while using the neutral dated predicate;
4. leave v0.6D unchanged;
5. add direct helper tests;
6. run all existing Stage 2 SQLite/PostgreSQL tests and the full offline Actions workflow.

Direct tests must cover:

- exact missing-timestamp error;
- naive and non-UTC aware datetime conversion;
- trailing-`Z` formatting;
- optional date and UUID formatting;
- cutoff absent, before, equal and after boundaries;
- late recorded date with visible information date;
- late information date with visible recorded date.

Existing payload tests remain the proof that public API output is unchanged.

## Responsibilities that remain local

The neutral module must not own:

- evidence payload construction or grade counts;
- conflict and missing-evidence text;
- claim, evidence or frozen-link selection;
- ID collection and sorting;
- list/detail payload fields or ordering;
- notices;
- aggregate not-found and visibility messages;
- repository loading;
- public contracts;
- v0.6D nullable timestamp policy.

The similar v0.6B-v0.6D evidence serializers are explicitly excluded. They contain different claim fields, missing-evidence reasons and domain boundaries and require a separate neutral read contract before extraction.

## Explicit exclusions

No v0.6D helper migration, evidence serializer unification, link-ID consolidation, public query change, cutoff-granularity change, timezone configuration, dependency, repository, command, model, schema, fixture, API, migration, v0.6E, v0.7, release, UI, deployment or PR #38 work.

## Definition of Ready

A minimal v0.6A-v0.6C query-value extraction is ready for a separate implementation Issue. Shared behavior, exact error text, the v0.6D edge difference, direct tests, no-migration decision and stop conditions are explicit.

This report does not authorize implementation.