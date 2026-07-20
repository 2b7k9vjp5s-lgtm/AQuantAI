# Issue #130 Status Sync

Issue #130 is authoritative.

## Base and scope

- Required ancestor: `995381a8702e5b431e8985b7df27fb7feb5d02fd`
- Branch: `docs/provider-price-semantics-status-sync`
- Work type: documentation-only architecture/status synchronization
- Version remains `0.2.0`; capability remains v0.6D.
- Accepted implementation baseline remains `7705b7caf210d606473db6f24c5fadfad4918646`.
- No migration, schema, dependency, provider, API or runtime change.

## Exact files

1. `.codex/tasks/issue-130-provider-price-semantics-status-sync.md`
2. `docs/architecture_baseline.md`
3. `docs/review.md`
4. `docs/roadmap.md`

Do not modify another path.

## Required result

Synchronize Issue #128 / PR #129:

- AKShare establishes daily/close mapping, adjustment identity and provenance;
- current identity rows and fixtures leave exchange blank;
- market identity, unit, currency, adjustment economics, price decimal limits and
  a complete semantic success fixture remain missing;
- no implementation reaches Definition of Ready;
- prefix/name/provider inference and provider fallback remain prohibited;
- the next gate is credential-free characterization of an explicit stable
  market/exchange source and deterministic success/failure fixtures.

Run full tests, the fixture demo and whitespace inspection. Open a Draft PR with
exactly the four files and stop for fixed-head review.
