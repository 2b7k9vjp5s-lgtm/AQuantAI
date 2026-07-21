# Issue #142 — Industry Beneficiary Workspace v1

## Authority

- GitHub Issue: #142
- Architecture authority: merged PR #141 / closed Issue #140
- Related roadmap: #137
- Required base: `42854199acb220dd581d68e1c87774966a46a9d9`
- Branch: `feat/industry-beneficiary-workspace-v1`
- Work type: application implementation — bounded Product Task
- Version remains `0.2.0`

## Objective

Implement a Chinese-first, local, read-only `/industry-research` workspace where the user explicitly selects one persisted industry map and optional cutoff, sees the complete cutoff-visible persisted Stage 1 beneficiary set before valuation filtering, and can explicitly open accepted Stage 1 and Stage 2 detail contracts.

## Mandatory start checks

Before editing implementation files:

1. Fetch and confirm `main` contains required base `42854199acb220dd581d68e1c87774966a46a9d9`.
2. Read `AGENTS.md`, `.codex/WORKFLOW.md`, `docs/architecture_baseline.md`, Issue #142 and `docs/industry_beneficiary_workspace_preflight.md`.
3. Confirm the active branch is `feat/industry-beneficiary-workspace-v1` and the Draft PR targets `main`.
4. Confirm no unexpected implementation commits exist after this task-synchronization commit.
5. Do not modify PR #38 or unrelated branches.

Stop without implementation if any authority or base mismatch exists.

## Authorized runtime surface

### New files

- `industry_alpha/beneficiary_workspace_contracts.py`
- `industry_alpha/beneficiary_workspace_repository.py`
- `industry_alpha/beneficiary_workspace_query.py`
- `backend/api/industry_research.py`
- `industry_research/static/industry_research.html`
- `industry_research/static/industry_research.css`
- `industry_research/static/industry_research.js`
- `tests/test_beneficiary_workspace_repository.py`
- `tests/test_beneficiary_workspace_query.py`
- `tests/test_industry_research_api.py`

### Modified file

- `backend/main.py` only for router/static-page registration.

Exact paths may be minimally adjusted only to match existing repository packaging conventions. No other production file is authorized without recording a blocker and stopping.

## Required implementation

### 1. Scalar selector

Implement `GET /industry-research/maps?as_of_cutoff=YYYY-MM-DD` using scalar map/revision reads only.

Return:

- map ID/key;
- latest cutoff-visible revision ID/number/title/scope;
- information cutoff date;
- recorded UTC.

Do not call `IndustryChainMapQueryService.list_maps()`.

### 2. Workspace overview

Implement `GET /industry-research/maps/{map_id}/workspace?as_of_cutoff=YYYY-MM-DD`.

Return:

- selected map identity/latest visible revision;
- accepted frozen map snapshot;
- every cutoff-visible persisted Stage 1 beneficiary for the map, represented by latest cutoff-visible revision;
- exact frozen stock row and ingestion-run provenance;
- optional exact Stage 2 identity and latest visible research revision summary;
- notices and unsupported-field disclosures.

Initial workspace load must not inline all Stage 1 evidence graphs or Stage 2 financial-hypothesis graphs.

### 3. Fixed-query repository

Add one stateless read-only repository/query boundary whose initial query count is independent of beneficiary count.

Do not compose:

- `IndustryChainMapQueryService.list_maps()`;
- `Stage1BeneficiaryQueryService.list_beneficiaries()`;
- `Stage2CompanyResearchQueryService.list_research()`.

Use explicit foreign keys and exact `map_id`. Never join by title, free text, Provider industry or stock-code similarity.

### 4. Exact Stage 2 history

A Stage 2 link is valid only through persisted `beneficiary_id` and `beneficiary_revision_id`.

When Stage 2 freezes an older beneficiary revision than the overview's latest visible revision:

- return both revision IDs;
- visibly label the Stage 2 revision as historical/frozen context;
- never relink it to the latest Stage 1 revision.

No Stage 2 record means null/unavailable. Multiple incompatible exact matches fail closed.

### 5. Cutoff and failures

Preserve existing owning-domain date-granular visibility:

- information date/cutoff and recorded UTC date must both be visible;
- frozen links cannot postdate the owning revision;
- no fallback to another map/revision, removed cutoff, candidate pool or all-stock universe.

Required API behavior:

- malformed UUID/date: 422;
- missing or cutoff-invisible map: 404;
- missing database configuration/query failure: deterministic 503 without raw details;
- empty beneficiary set: valid empty array with selected map context;
- unresolved exact stock/run/map provenance: fail closed;
- missing Stage 2: null/unavailable.

### 6. Presentation

Build a Chinese-first responsive page with:

1. explicit map and cutoff selector;
2. map summary;
3. driver/bottleneck/value-pool-shift observations;
4. `已录入受益公司全量` table;
5. explicit beneficiary detail region/drawer;
6. Stage 2 financial-transmission region or explicit unavailable state;
7. boundary notice.

No map is silently selected. Optional URL `map_id` may prefill explicit selection.

Raw persisted values remain visible:

- `direct / secondary / potential`;
- `draft / supported / disputed / rejected`;
- `driver / bottleneck / value_pool_shift`;
- `positive / negative / mixed / uncertain`.

Use neutral visual treatment. Facts/provenance, stored classifications, D3 rationale/hypotheses, conflicts and unavailable fields must be visually separated. Do not use `innerHTML` for untrusted data.

### 7. Neutral ordering

Use only:

1. beneficiary kind fixed order `direct`, `secondary`, `potential`;
2. source ascending;
3. stock code ascending;
4. beneficiary UUID ascending.

Label as `排序`, never `排名`. No evidence/status/confidence/recency/market/valuation ordering.

## Golden path

Add a production-realistic offline fixture path using accepted persistence contracts with:

- one persisted map and frozen observations;
- Stage 1 beneficiaries covering all three current kinds and supported/draft/disputed states;
- exact stock/run provenance;
- A/B/C/D evidence with contradiction and missing evidence;
- Stage 2 for only a subset;
- one Stage 2 historical beneficiary-revision mismatch.

The page/API must show every visible Stage 1 row, explicit missing Stage 2 state, exact conflict/missing evidence through on-demand detail, and no network request.

## Tests

At minimum cover:

- selector scalar fields and cutoff behavior;
- fixed initial query count independent of beneficiary count;
- complete persisted Stage 1 set at cutoff;
- exact stock/run provenance;
- raw classification preservation and neutral ordering;
- exact Stage 2 linkage and historical mismatch;
- empty set and no fallback;
- integrity failures closed;
- malformed UUID/date, 404 and 503 boundaries;
- no initial per-company graph loading;
- explicit detail integration;
- page loading/empty/error/keyboard-responsive behavior where repository conventions permit;
- safe DOM construction;
- no external network.

Run all repository-prescribed tests, existing demos and PostgreSQL CI path. Record exact pass/skip/warning counts without invention.

## Locked exclusions

- no `direct / conditional / indirect / conceptual` taxonomy;
- no mapping/renaming of current beneficiary kinds;
- no rule engine, rule version or analyst owner;
- no typed driver subtype;
- no typed product/customer/certification/capacity/production/order fields;
- no company discovery from text, Provider classifications or LLM;
- no schema, migration or persistent workspace state;
- no Provider/external ingestion/network path;
- no valuation, expectation gap, catalyst/risk comparison, canonical price, score, rank, recommendation, target price, expected return or signal;
- no release/tag/version change.

## Stop conditions

Stop and report a blocker in Issue #142 and the Draft PR if implementation requires any new semantic contract, persistent relationship/state, changed cutoff/provenance rule, inferred identity, price/valuation logic, or unauthorized file.

## Validation and handoff

Before stopping:

1. confirm complete base-to-head changed-file inventory matches Issue #142;
2. run every required test/demo;
3. record exact base and head SHA;
4. record exact pass/skip/warning counts and environment limits;
5. include production-realistic fixture output;
6. document known limitations and exclusions;
7. keep the PR Draft/Open/unmerged;
8. stop for ChatGPT review.

Do not merge, close Issue #142, create a release/tag, change version or start 2B without explicit owner authorization.
