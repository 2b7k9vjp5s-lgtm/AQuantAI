# Issue #128 - Provider Price Semantics Characterization

Issue #128 is authoritative.

## Base and scope

- Required ancestor: `03d4f663cc4f8d0612dcf412f4ba78e352188e9f`
- Branch: `docs/provider-price-semantics-characterization`
- Work type: documentation-only Architecture Preflight
- Version remains `0.2.0`; capability remains v0.6D.
- Accepted implementation baseline remains `7705b7caf210d606473db6f24c5fadfad4918646`.
- No migration, schema, dependency, provider, API or runtime change.

## Exact files

1. `.codex/tasks/issue-128-provider-price-semantics-characterization.md`
2. `docs/provider_price_semantics_characterization.md`

Do not modify another path.

## Required result

Characterize whether current credential-free provider contracts and offline
fixtures can establish the accepted minimum market-price semantics:

- explicit instrument market identity;
- `daily_close` ownership;
- unit and currency;
- frequency and adjustment meaning;
- provider, adapter, package, endpoint, series, run and source-row provenance;
- information and UTC visibility;
- price-specific numeric rules and fail-closed missing state.

No market, exchange, currency or unit may be inferred from code prefixes, names,
free text or provider name. Keep Hithink deferred.

Compare the current AKShare contract, a versioned descriptor over current rows,
provider identity enrichment and provider fallback. State whether any
implementation reaches Definition of Ready and identify the smallest next gate.

Run the full test suite, fixture demo and whitespace check. Open a Draft PR with
exactly the two authorized files and stop for fixed-head review.
