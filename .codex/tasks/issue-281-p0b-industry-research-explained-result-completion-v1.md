# Issue #281 — P0-B Industry Research Explained Result Completion v1

## Authority

Project-owner implementation authorization on 2026-07-31:

> 批准按 Issue #281 已冻结范围开始实现。以精确 `main@216df36e5297564cbb5960fb2ac546f47edcd208` 创建独立实现分支和一个 Draft PR；仅修改 #281 allowlist 文件。先完成 exact downstream owner inventory，再实现 P0-B Explained Result Completion。不得修改既有 Company Research / Investment Candidate 等 owner、schema/migration、Provider、推荐、组合或交易；如现有精确 read boundary 无法取得所需数据，立即 STOP 并提出 allowlist/架构修订。完成后跑 focused tests、full pytest 和全部 offline demos，保持 Draft，不得合并。

## Exact implementation start

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
base_branch = main
base_sha = 216df36e5297564cbb5960fb2ac546f47edcd208
branch = feat/p0b-industry-research-explained-result-completion-v1
issue = #281
roadmap = #137
risk_tier = Strict Implementation
```

PR #241 remains permanently frozen, closed, Draft and unmerged at `3116a67ec472131eea3bf3d1bd9daee884c69ee9`.

## Exact downstream owner inventory

The pre-code inventory proves implementation can remain read-only and inside Issue #281 without modifying accepted owners:

1. `IndustryResearchResultQueryService` already owns exact accepted-output + exact Map Revision + optional exact candidate-overlay composition.
2. `CandidateOverlayReader` validates zero/one explicitly selected exact `InvestmentCandidateSnapshotRevision`; it never auto-selects latest/only/closest and rejects wrong-pool overlays.
3. `InvestmentCandidateQueryService.get_snapshot_revision()` owner-validates the exact snapshot graph and returns frozen `beneficiary_revision_id`, `company_research_revision_id`, typed semantic, canonical price, comparison eligibility, candidate status/reasons and exact component revision IDs.
4. `InvestmentCandidateQueryService.get_component_revision()` exposes exact component rationale, verification/falsification state and exact typed input revision IDs.
5. Candidate component input kinds are closed to map, semantic, financial hypothesis, expectation, valuation, catalyst, risk, industry/company judgment, canonical price, comparison eligibility, claim and evidence revisions.
6. Existing Company Research / v0.6A-v0.6D owner models contain the explanation fields needed by the product, but identity-level workspace reads may select latest visible revisions and therefore MUST NOT be used as authority for frozen snapshot meaning.
7. The accepted result projection already uses product-local set-based read projections over accepted Stage 2 models after authoritative owner validation. The explained-result helper may follow the same read-only pattern only for exact IDs already frozen by the owner-validated snapshot/components.

Conclusion:

```text
owner_modification_required = false
schema_or_migration_required = false
provider_or_network_required = false
implementation_may_proceed = true
```

## Frozen implementation contract

### 1. Authority chain

```text
exact accepted output
-> explicit exact selected candidate snapshot
-> owner-validated snapshot graph
-> exact candidate component revision IDs
-> exact component input revision IDs
-> set-based read-only explanation projection
```

No downstream row may enter the explained result because it is newer, latest, uniquely reachable, same-stock, same-company-name, same-ticker or high-coverage.

### 2. Explained-result contract

Add a deterministic presentation contract:

```text
explained_result_contract_version = aquantai.industry-research-explained-result.v1
```

Each accepted member remains present in frozen accepted order and receives a read-only `explained_research` projection with closed sections when exact links exist:

```text
overall_state
source_layers
company_research
beneficiary_semantics
product_and_chain
customer_certification_capacity_order
earnings_transmission
expectation
valuation
catalysts
risks
industry_judgments
company_judgments
candidate_explanation
missing_inputs
technical_exact_links
```

The projection may normalize persisted closed statuses and deterministic labels only. It may not generate new research meaning, score, ranking, recommendation or forecast.

### 3. Exact link behavior

The helper may read only exact IDs already present in the owner-validated candidate snapshot or its exact component input links.

For every exact downstream row:

- `information_cutoff_date <= as_of_cutoff` when the model owns such a field;
- `recorded_at_utc <= as_of_recorded_at_utc` when the model owns such a field;
- any frozen `company_research_revision_id` must match the selected member's exact frozen Company Research revision;
- beneficiary semantic revisions must match the exact beneficiary revision;
- any missing, invisible or graph-incompatible exact revision becomes stable `unavailable`/missing diagnostics;
- there is never a replacement lookup.

The accepted result remains readable when an optional downstream explanation is unavailable.

### 4. Source-layer labels

Closed presentation layers:

```text
accepted_snapshot
accepted_fact
accepted_research_judgment
deterministic_candidate
missing_or_unavailable
```

An AI draft may never be promoted to any accepted source layer.

### 5. Candidate meaning

Candidate status, reasons, scores, component values and contribution fields come only from the explicitly selected persisted snapshot/component revisions.

Prohibited:

```text
candidate recomputation
status reinterpretation
new score/ranking
one-option auto-selection
latest candidate selection
fallback candidate pool
```

### 6. Read-only/local boundary

```text
writes = zero
external network = zero
provider = zero
credentials = zero
AI calls = zero
background work = zero
```

GET, page load, overlay selection, drawer expansion, back/refresh/history reopen must not mutate state.

## Frozen allowlist

Exactly these paths may change unless Issue #281 is explicitly amended first:

```text
.codex/tasks/issue-281-p0b-industry-research-explained-result-completion-v1.md
industry_alpha/industry_research_result_query.py
industry_alpha/industry_research_result_rules.py
industry_alpha/industry_research_result_candidate.py
industry_alpha/industry_research_result_company.py
backend/api/industry_research_result.py
industry_analysis/static/accepted_result.html
industry_analysis/static/accepted_result.js
industry_analysis/static/accepted_result_assembly.css
tests/test_industry_research_result_query.py
tests/test_industry_research_result_scale.py
tests/test_industry_research_result_static.py
tests/test_industry_research_explained_result.py
scripts/demo_industry_research_result_assembly.py
.github/workflows/local-tests.yml
```

No other file is authorized.

## Explicit exclusions

Do not modify:

- existing Company Research / Stage 2 owner command/query/model semantics;
- Investment Candidate command/scoring/rule owners;
- Stage 1 or Industry Map write owners;
- Evidence acceptance/mutation owners;
- `backend/database/**`;
- `migrations/**`;
- `datasource/**`;
- recommendation / portfolio / trading paths;
- release/tag/version files;
- PR #241.

No schema, migration, new owner, Provider, network, AI, automatic acceptance, automatic Company Research, automatic candidate snapshot creation, recommendation, target price, expected return, position sizing, holdings or trading.

## Required positive validation

At minimum prove:

1. three accepted beneficiaries remain visible in frozen order;
2. zero/one candidate snapshot remains explicit; no selection means no inferred explanation snapshot;
3. selected exact snapshot enriches only exact matching beneficiary revisions;
4. exact typed semantic assertions expose offering/customer/certification/capacity/production/order fields where frozen;
5. exact financial hypothesis exposes earnings-transmission mechanism, operating metric, financial-statement line, lag horizon, basis and confidence;
6. exact expectation/valuation/catalyst/risk/judgment component inputs project only their frozen revision values;
7. candidate reasons/components/verification/falsification remain persisted owner values;
8. result clearly separates accepted snapshot meaning from deterministic current candidate overlay;
9. exact URL + dual-as-of reopen is deterministic;
10. three-member and twenty-member query behavior stays bounded and does not become per-member HTTP/N+1;
11. GET/result rendering performs zero writes, network and AI.

## Required negative validation

At minimum prove:

1. wrong-pool candidate snapshot leaves accepted result readable and explanation unavailable;
2. no candidate overlay selected does not select a downstream latest revision;
3. newer Company Research/expectation/valuation/catalyst/risk/judgment revisions are ignored unless exact IDs are frozen;
4. an exact downstream revision outside either as-of boundary is unavailable with no replacement;
5. missing exact Company Research revision is unavailable with no fallback;
6. mismatched frozen `company_research_revision_id` fails the affected explanation closed;
7. missing/incomplete component input graph does not invent a reason;
8. duplicate company labels with distinct beneficiary revisions remain distinct;
9. zero-supported accepted output remains readable;
10. browser does not compute candidate rules/scores or auto-select snapshots.

## CI / delivery gate

Final immutable HEAD must pass:

- focused explained-result tests;
- existing result assembly tests;
- full repository pytest;
- every configured zero-network offline demo.

Base-to-HEAD must stay entirely inside the allowlist and be behind `main` by zero at fixed-head review.

Fresh fixed-head implementation review must record exactly:

```text
AUTHORIZED P0-B INDUSTRY RESEARCH EXPLAINED RESULT COMPLETION V1 IMPLEMENTATION APPROVED at fixed head <FULL_HEAD_SHA>
```

Any new commit invalidates earlier CI and review evidence.

Keep PR Draft. Do not mark Ready, merge or close Issue #281 without separate project-owner authorization.

## STOP conditions

STOP and return for an explicit Issue/allowlist amendment if:

- required explanation cannot be obtained from exact IDs already frozen by accepted owners;
- an existing owner module must be modified;
- a latest/current fallback is needed;
- schema/migration/new persistence is needed;
- per-member network/API acquisition is needed;
- any recommendation, portfolio, trading, Provider or AI-owned accepted state appears.
