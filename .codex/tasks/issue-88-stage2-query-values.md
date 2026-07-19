# Issue #88 - Stage 2 Query Value Helpers

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#88`
- Accepted characterization: Issue #86 / PR #87
- Base and required ancestor: `686b6f4facd031556c8da244c905342c046860f9`
- Branch: `refactor/stage2-query-values`
- Work type: behavior-preserving consolidation implementation
- Version remains `0.2.0`; capability stage remains v0.6D.

## Objective

Extract the exact v0.6A-v0.6C required UTC, date-granular cutoff visibility, timestamp/date/UUID formatting functions into `industry_alpha.stage2_query_values` without changing public payloads or domain semantics.

## Authorized files

- `.codex/tasks/issue-88-stage2-query-values.md`
- `industry_alpha/stage2_query_values.py`
- `industry_alpha/stage2_query.py`
- `industry_alpha/stage2_expectations_query.py`
- `industry_alpha/stage2_assessments_query.py`
- `tests/test_stage2_query_values.py`

## Required edits

1. Keep the supplied neutral module and direct tests unless a correction is needed inside the authorized contract.
2. In `stage2_query.py`, import neutral functions as the existing private names `_stored_utc`, `_timestamp`, `_date`, `_uuid`, `_recorded_visible`, `_dated_visible`; remove the duplicate local definitions only.
3. In `stage2_expectations_query.py`, import the same applicable aliases. Keep `_visible_revisions` local, but implement its predicate with `_dated_visible`. Remove duplicate `_recorded_visible`, `_stored_utc`, `_timestamp`, `_date` and `_uuid` definitions. Keep `_ids`, evidence payload and price reference local.
4. In `stage2_assessments_query.py`, import the same applicable aliases. Keep `_visible_revisions` local, but implement its predicate with `_dated_visible`. Remove duplicate `_recorded_visible`, `_stored_utc`, `_timestamp`, `_date` and `_uuid` definitions. Keep `_link_ids` and evidence payload local.
5. Do not edit `stage2_judgments_query.py`.
6. Do not rename public query services or change payload fields, ordering, notices, exceptions, missing-evidence text, link filtering or collection types.

## Exact neutral behavior

- `stored_utc(None)` raises `EvidenceLedgerNotVisible("required UTC timestamp is unavailable.")`.
- Naive datetimes retain wall-clock fields and receive UTC.
- Aware datetimes convert with `astimezone(timezone.utc)`.
- Timestamp text uses ISO 8601 and replaces `+00:00` with `Z`.
- Date and UUID formatting preserve `None`.
- Recorded visibility and dated visibility use calendar dates and include equality.

## Validation

- Run `python -m pytest tests/test_stage2_query_values.py`.
- Run existing v0.6A-v0.6C SQLite tests.
- Run applicable PostgreSQL Stage 2 tests.
- Run the full repository test workflow and local fixture demo.
- Confirm exact six-file diff and no migration.
- Open a Draft PR related to #88 and keep it unmerged for independent implementation review.

## Locked exclusions

No v0.6D edit, evidence serializer/link-ID consolidation, repository, command, model, schema, fixture, API, provider, dependency, Docker, CI, UI, release, migration, v0.6E, v0.7 or PR #38 work.