# Issue #124 - Canonical Market-Price Evidence Characterization

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: #124
- Required base and ancestor: `b2bb75fbbd10ad765b99e8a0dee3d57f6aaae54e`
- Branch: `docs/canonical-market-price-evidence-characterization`
- Work type: documentation-only Architecture Preflight and characterization
- Released version remains `0.2.0`; merged capability remains v0.6D.
- Accepted application/consolidation implementation baseline remains `7705b7caf210d606473db6f24c5fadfad4918646`.
- Migration, schema, dependency, API, provider and runtime decisions: no change.

## Objective

Determine whether a standalone canonical market-price measurement/evidence contract has independent user value, define its minimum ownership and point-in-time semantics, compare bounded implementation shapes, and decide whether any production implementation reaches Definition of Ready.

This work is upstream of valuation comparison eligibility and any future price judgment. It must not treat `DailyPriceRecord`, a latest-series DataFrame row, a v0.6B `observed_value`, or a `daily_price_id` link as automatically canonical or comparison eligible.

## Exact authorized files

1. `.codex/tasks/issue-124-canonical-market-price-evidence-characterization.md`
2. `docs/canonical_market_price_evidence_characterization.md`

Do not modify any other path.

## Required source inventory

Characterize only from the accepted repository state:

- `datasource/base.py`;
- `backend/database/models.py`;
- `backend/database/series.py`;
- `backend/database/market_data.py`;
- `industry_alpha/stage2_expectations_models.py`;
- `industry_alpha/stage2_expectations_commands.py`;
- superseded Issue #70 / Draft PR #71 as rejected/downstream design evidence only;
- current architecture baseline, review and roadmap after PR #123.

Do not revive or adopt the superseded v0.6E plan.

## Required questions

### Independent value

Decide whether canonical price evidence is independently useful for point-in-time inspection, audit, downstream provenance and later eligibility decisions without producing a recommendation, target price, expected return or timing state.

### Semantic boundary

Inventory and decide:

- value representation and source conversion;
- measurement kind;
- unit/dimension and currency;
- instrument identity;
- provider/source, series, run and exact row provenance;
- observation date/time and information cutoff;
- imported/completed/recorded UTC visibility;
- adjustment meaning;
- complete-snapshot and explicit-series requirements;
- missing/ambiguous/disputed semantics;
- strict JSON and cross-database determinism.

### Boundary distinctions

Keep separate:

1. provider-normalized row;
2. persisted source row;
3. latest-series/cutoff-aware DataFrame read;
4. canonical market-price evidence;
5. v0.6B valuation observation;
6. comparison eligibility;
7. later price-judgment or read-model state.

### Candidate comparison

Compare:

- deterministic read-only projection over existing rows/runs;
- standalone append-only canonical evidence;
- downstream revision-owned audit copies;
- enrichment/replacement of the normalized `daily_price` contract.

For each candidate state ownership, reachability, historical stability, provider specificity, migration impact, rollback, tests and duplication risk.

### Definition of Ready

Conclude either:

- no production implementation reaches DoR and identify the smallest missing gate; or
- exactly one bounded candidate reaches DoR with exact owner, contract, file family, migration decision, tests, rollback and stop conditions.

Plausibility alone is not authorization.

## Required invariants

- One provider and one canonical series per selected source row; no fallback, relabeling, row-level mixing or stitching.
- Exact source row/run/series provenance remains visible.
- Information-date and UTC visibility both apply.
- Adjustment semantics are explicit; adjusted and unadjusted values are never treated as interchangeable.
- Unit/currency never comes from stock-code/name/free-text inference, valuation borrowing or defaults.
- A linked row is context only until a separately accepted eligibility contract says otherwise.
- Missing or ambiguous provenance fails closed and remains visible.
- No LLM owns deterministic value, provenance, eligibility or state.

## Validation

- exact two-file base-to-head diff;
- `python -m pytest -q`;
- `python -m scripts.demo_research_flow`;
- `git diff --check`;
- GitHub Actions on one fixed head;
- exact counts only when actually available.

## Locked exclusions

No production code, test, fixture, dependency, provider behavior, live request, secret, database/schema/migration, API/runtime, comparison eligibility, price model, v0.6E, v0.7, portfolio/trading, release/tag/version or PR #38 change.

Do not reopen Hithink integration or alter AKShare behavior.

## Stop gate

Open a Draft PR containing exactly the two authorized files. Keep it Draft/Open/unmerged for independent fixed-head review. Do not create an implementation Issue or status-sync PR in the same work item.