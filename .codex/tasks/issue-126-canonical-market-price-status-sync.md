# Issue #126 Status Sync

Issue #126 is authoritative.

## Base

- Required ancestor: `8955e419c79f592ee9edcccdb446ebbe249de1dd`
- Branch: `docs/canonical-market-price-status-sync`
- Work type: documentation-only status synchronization
- Version remains `0.2.0`; merged capability remains v0.6D.
- Accepted implementation baseline remains `7705b7caf210d606473db6f24c5fadfad4918646`.
- No migration, schema, dependency, provider, API or runtime change.

## Exact files

1. `.codex/tasks/issue-126-canonical-market-price-status-sync.md`
2. `docs/architecture_baseline.md`
3. `docs/review.md`
4. `docs/roadmap.md`

Do not modify another path.

## Required result

Synchronize the accepted Issue #124 / PR #125 characterization:

- the evidence boundary has independent audit and point-in-time value;
- normalized rows, persisted source rows, selected reads, canonical evidence,
  valuation observations, comparison decisions and later judgment state remain
  separate;
- a market-data/evidence layer is the preferred future owner;
- no production implementation is ready;
- the next gate is an offline characterization of provider measurement semantics
  and deterministic fixtures.

Preserve all exclusions in Issue #126. Run the full test suite, fixture demo and
whitespace check. Open a Draft PR with exactly these four files and stop for
fixed-head review.