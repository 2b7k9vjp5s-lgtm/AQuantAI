# Issue #181 — Investment Candidate Intelligence Layer v1

## Authority

- Implementation Issue: #181
- Architecture Issue: #179
- Architecture PR: #180
- Architecture fixed head at implementation start: `c2fdd00d1e2b68167fc6b15e19b0c64653f63290`
- Required implementation base: `ccb949beb08d25d4b91ae970b1e1781a09d92f8e`
- Risk tier: **Strict**
- Owner authorization: `进行下一阶段开发，完成目标实现` on 2026-07-22

Implementation may proceed in parallel, but it must not merge before the architecture is independently approved and merged.

## Objective

Implement a complete-universe, append-only and deterministic Investment Candidate snapshot that answers which industry beneficiaries are current priority research candidates and why.

Supported statuses:

- `priority_candidate`
- `watch_candidate`
- `awaiting_verification`
- `pricing_demanding`
- `evidence_insufficient`
- `not_current_candidate`

No buy/sell/hold, target price, expected return, portfolio or trading semantics.

## Required schema

Create migration `20260722_0014_investment_candidate_intelligence.py` with exactly:

1. `investment_candidate_component_assessments`
2. `investment_candidate_component_revisions`
3. `investment_candidate_component_input_links`
4. `investment_candidate_snapshots`
5. `investment_candidate_snapshot_revisions`
6. `investment_candidate_members`
7. `investment_candidate_member_component_links`
8. `investment_candidate_member_reason_codes`

No existing-table mutation or backfill. All new records are append-only. Populated downgrade refuses before any drop.

## Components

- `industry_opportunity`
- `beneficiary_strength`
- `earnings_conversion`
- `expectation_gap`
- `valuation_context`
- `catalyst_readiness`
- `evidence_quality`
- `risk_penalty`

Component revisions are explicit analyst-owned D3 inputs. Scores use decimal text in range 0.00–100.00, standardized with `ROUND_HALF_EVEN` to two decimal places.

## Deterministic rule

Positive weights:

- industry opportunity 15%
- beneficiary strength 20%
- earnings conversion 20%
- expectation gap 15%
- valuation context 15%
- catalyst readiness 10%
- evidence quality 5%

`risk_penalty_points = risk_penalty * 0.25`

`final_score = max(0.00, base_score - risk_penalty_points)`

Implement exact business-quality score, gates, status precedence, reason codes and tie breaks from the approved architecture. Never impute or redistribute missing weights.

## Complete-universe invariant

The explicit snapshot manifest must be set-equal to the exact persisted membership set of one `Stage1CandidatePoolRevision`.

Reject omission, duplication, substitution or revision mismatch before any insert with:

`investment_candidate_universe_mismatch`

## Commands

```text
python -m scripts.record_investment_candidate_component --input <local-json-path>
python -m scripts.record_investment_candidate_snapshot --input <local-json-path>
```

Both are local JSON-only, bounded, strict, dry-run capable, expected-latest protected, atomic, credential-safe and network-free.

## Read surfaces

```text
GET /investment-candidates/component-revisions/{component_revision_id}
GET /investment-candidates/snapshot-revisions/{snapshot_revision_id}
```

Both require `as_of_cutoff` and timezone-aware `as_of_recorded_at_utc`.

Add a Chinese-first read-only `/investment-candidates` workspace requiring one exact snapshot revision and both boundaries.

The page must highlight up to three priority/watch candidates and also show the entire candidate-pool universe with component/provenance/reason details.

## Golden path

One exact three-member pool produces:

- A: `priority_candidate`
- B: `pricing_demanding`
- C: `evidence_insufficient` without an aggregate score

All three remain visible. Verify exact revisions, as-of boundaries, Decimal calculations, reason sorting, priority ties, API/page output and zero hidden network.

## Primary failure path

Omit one member and substitute a newer revision for another. Expected:

- `investment_candidate_universe_mismatch`
- zero partial writes
- no fallback universe
- no automatic revision selection

## Authorized file families

- `.codex/tasks/issue-181-*`
- `industry_alpha/investment_candidate_*`
- `backend/api/investment_candidate.py`
- minimal `backend/main.py`
- product-local template/static files for `/investment-candidates`
- `scripts/record_investment_candidate_component.py`
- `scripts/record_investment_candidate_snapshot.py`
- bounded `scripts/README.md`
- `migrations/env.py`
- `migrations/versions/20260722_0014_investment_candidate_intelligence.py`
- focused `tests/test_investment_candidate*`
- migration-head assertion tests only for `20260722_0013` -> `20260722_0014`
- bounded `docs/architecture_baseline.md` completion update after implementation is stable

Do not create a generic scoring, rule, workspace, portfolio or trading framework.

## Validation

- focused component/snapshot tests
- threshold and Decimal tests
- complete-universe tests
- append-only and stale expected-latest rollback
- exact upstream revision and chronology tests
- canonical price/eligibility compatibility tests
- status precedence, pending, missing, disputed and falsification tests
- deterministic tie break and top-three tests
- exact-ID API and page tests
- bounded query-count tests
- SQLite and PostgreSQL migration round trip
- PostgreSQL concurrency and populated downgrade refusal
- full relevant regression
- offline golden-path fixture demo
- no-hidden-network tests

## Required implementation approval

`INVESTMENT CANDIDATE INTELLIGENCE IMPLEMENTATION APPROVED at fixed head <FULL_HEAD_SHA>`

## Locked exclusions

No external network, Provider, crawling, browsing, news/social/fund-flow acquisition, normalized peer valuation engine, target price, fair value, expected return, performance promise, buy/sell/hold instruction, portfolio, position sizing, broker/trading, AI-owned accepted state, hidden inputs, evidence-count scoring, missing-value imputation, automatic relinking, existing-row mutation/backfill, release, tag or version change.
