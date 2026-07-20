# Issue #132 — Architecture Rebalance Documentation Sync

## Authority

Issue #132 is the authoritative source for this task. This snapshot records the exact scope and state for the fixed-head review.

## Task Information

- **Base SHA:** `995381a8702e5b431e8985b7df27fb7feb5d02fd`
- **Branch:** `docs/issue-132-architecture-rebalance`
- **Work type:** docs-only architecture/status synchronization
- **Authorized files (exactly four):**
  1. `.codex/tasks/issue-132-architecture-rebalance-sync.md`
  2. `docs/architecture_baseline.md`
  3. `docs/review.md`
  4. `docs/roadmap.md`

## Preserved Invariants

- Released software version: `0.2.0`
- Merged capability stage: v0.6D
- Accepted implementation baseline: `7705b7caf210d606473db6f24c5fadfad4918646`
- Hithink remains deferred
- AKShare remains the implemented provider path
- No silent provider fallback
- No cross-provider natural-key stitching
- No exchange inference via security-code prefix, name, free text or provider name
- Canonical market-price production implementation remains not at DoR
- Comparison eligibility not authorized
- v0.6E not authorized
- v0.7 not authorized
- Watchlist not authorized
- No migration created
- No schema modified
- No runtime Provider behavior changed

## Changes Introduced

### 1. Semantic Level (L0–L3)

Added unified data semantics tier to architecture baseline:

- **L0 — Raw Provider Data:** direct provider output, no semantics guaranteed.
- **L1 — Provider Normalized:** adapter-mapped internal fields, provider semantics still apply.
- **L2 — Standardized:** measurement kind, format, unit or other fields standardized by explicit contract.
- **L3 — Canonical:** full canonical contract satisfied (measurement identity, unit, currency, market identity, adjustment semantics, provenance, cutoff/UTC visibility, freeze method, decimal contract, missing-state contract).

Semantic Level is a consumption qualification, not a quality label. No Enum, model, database field, API field or migration was created.

### 2. Evidence Qualification / Derivation Level (D0–D3)

Added derivation level framework to architecture baseline:

- **D0 — Direct Fact:** directly supported by explicit source.
- **D1 — Deterministic Aggregation:** produced from recorded input set, window and deterministic algorithm.
- **D2 — Rule Classification:** depends on explicit versioned classification rules.
- **D3 — Analytical Judgment:** contains analysis, interpretation or research judgment.

No Enum, model, database field, API field or migration was created.

### 3. Dual-Track Development Classification

Formalized distinction between:

- **Architecture Task:** requires full Architecture Preflight, DoR and fixed-head review. Triggered by schema, migration, Provider change, semantic change, provenance change, fallback/identity/join rule change, new persistent state, computation contract change, classification contract change, or security change.
- **Product Task:** lightweight process. Requires reading-only from accepted data contracts, no new persistence, no semantic change, no system invariant change, no computation contract change, no Provider behavior change, no cutoff/revision/provenance change, no Semantic Level elevation, no D2/D3 disguised as D0/D1.

Uncertain tasks default to Architecture Task.

### 4. Evidence Intelligence MVP as Next Product Gate

The product-facing mainline shifts from the old linear path (canonical price → comparison → v0.6E → Watchlist) to:

**Phase 1 main delivery direction: Evidence Intelligence MVP**

Goal: user can see within ~5 minutes what research objects, industries, companies and evidence changed recently.

First phase limited to read-only capabilities based on existing accepted contracts. Candidate content includes Research Feed, Evidence Timeline, Industry → Company Mapping, evidentiary counts, unresolved conflict counts, recent research record timestamps, existing beneficiary relations and evidence links.

Must not output buy/sell signals, target prices, opportunity rankings, return predictions, automated investment advice or unsupervised positive/negative judgments.

Industry → Company Mapping displays existing relationships; it is not automatic stock recommendation.

### 5. Canonical Price as Parallel Infrastructure Track

Canonical price continues as an independent track but no longer blocks all product-facing capability. It remains required for:

- canonical comparison
- price judgment
- comparison eligibility

Provider isolation, provenance, cutoff, append-only, no silent fallback and no inference requirements are not relaxed. No temporary price assumptions are authorized.

### 6. Preserved Provider Semantics no-DoR Conclusion

Canonical market-price evidence retains independent value. Preferred ownership remains in market-data/evidence layer. Current Provider semantics remain insufficient for production DoR. No exchange inference, no default currency, no silent fallback and no provider-name-based inference are authorized.

## Stop Conditions

This task completes at:

- Working branch pushed
- Draft PR created (Open, Unmerged)
- Fixed head recorded

No Evidence Intelligence Architecture Preflight, Research Feed implementation, Dashboard implementation, Price Semantic Level implementation, Canonical Price implementation, Issue creation for next phase, PR merge or Issue closure.

Next step requires independent fixed-head review before any merge.

## Validation

- `git diff --check`: to be run before commit
- Scope check: exactly four authorized files, no production code, tests, fixtures, schema, migration, Provider or runtime changes
- Version and baseline unchanged: 0.2.0, v0.6D, 7705b7caf210d606473db6f24c5fadfad4918646
