# Industry Beneficiary Workspace v1 Architecture Preflight

## Status and authority

- Authority: Issue #140.
- Related roadmap: Issue #137.
- Predecessor product slice: PR #139 / Issue #138, merged as `3a8b74a5ef76bd34092ff96985bae0d3d2733c8f`.
- Base branch: `main` at `3a8b74a5ef76bd34092ff96985bae0d3d2733c8f`.
- Work type: Architecture Preflight, documentation only.
- Released version remains `0.2.0`; merged capability remains v0.6D plus the read-only Evidence Intelligence product slice.
- This document authorizes no production code, API, UI, tests, fixtures, schema, migration, Provider, release or version change.

## One-sentence user job

A local user can explicitly select one persisted industry map and inspect the complete cutoff-visible **persisted Stage 1 beneficiary set** before any valuation or market-pricing filter, then open exact evidence, conflicts, revision history and any existing Stage 2 financial-transmission research without receiving a score or recommendation.

## Scope meaning: “complete beneficiary universe”

For v1, completeness means exactly:

> every `Stage1Beneficiary` identity for the explicitly selected `map_id` that has at least one cutoff-visible `Stage1BeneficiaryRevision`, represented by its latest cutoff-visible revision.

It does **not** mean:

- every A-share company that could benefit in the real world;
- every company in `stock_basic`;
- every company mentioned in evidence or free text;
- every member of a Provider industry classification;
- every candidate that a model, LLM or analyst might infer;
- a claim that industry coverage is exhaustive.

The UI must use wording such as “已录入受益公司全量” or “当前研究库可见受益公司”, not “全市场完整受益名单”. Coverage confidence remains unverified. An empty persisted beneficiary set remains empty and must not fall back to `stock_basic`, candidate pools, Provider industry membership or inferred names.

## Product decomposition

### 2A — Existing-contract Industry Beneficiary Workspace

2A is the candidate first implementation after independent Definition-of-Ready approval.

It may:

- show one explicitly selected persisted industry map;
- show exact frozen map nodes, relationships and `driver / bottleneck / value_pool_shift` observations;
- show every cutoff-visible persisted Stage 1 beneficiary for the map;
- preserve exact `direct / secondary / potential` values and `draft / supported / disputed / rejected` status;
- show exact rationale, frozen map assertions, claims, evidence, conflicts and missing evidence on explicit row detail;
- show exact Stage 2 company-research identity and financial-transmission hypotheses when an existing frozen handoff is available;
- keep all rows visible before downstream valuation or market-pricing analysis;
- provide deterministic neutral sorting and explicit missing states.

2A may not claim to implement the full roadmap taxonomy or real-world exhaustive coverage.

### 2B — New-semantic Industry Beneficiary Classification

2B is a later Architecture Task and is not authorized here.

2B would be required for any of the following:

- replacing or mapping `direct / secondary / potential` to `direct / conditional / indirect / conceptual`;
- adding a generic D2 rule engine or persisted `rule_version`;
- adding analyst identity or responsibility ownership;
- adding typed industry-driver subtypes such as demand expansion, supply contraction, policy change, technology substitution or event shock;
- adding typed product/service, customer, certification, capacity, production-stage or order-stage fields;
- claiming real-world exhaustive company coverage;
- automatically deriving beneficiary relationships from evidence text, stock codes, Provider classifications or LLM output.

2A and 2B must not be bundled into one implementation Issue.

## Existing source inventory

| Display object | Authoritative owner | Persisted source | Existing fields available to 2A | Important limitation |
| --- | --- | --- | --- | --- |
| Industry-map identity | v0.5B Industry Map | `industry_maps` | `id`, `case_id`, `map_key`, `created_at_utc` | No market-wide coverage statement. |
| Industry-map revision | v0.5B Industry Map | `industry_map_revisions` | `id`, `map_id`, `revision_no`, `title`, `scope`, `information_cutoff_date`, `recorded_at_utc`, `supersedes_revision_id` | Latest means latest visible at the requested cutoff. |
| Chain node | v0.5B Industry Map | `industry_map_nodes` and revisions | `node_key`, `label`, `description`, `node_kind`, `assertion_status`, cutoff, UTC, revision | `node_kind` is the exact persisted allow-list; no additional process taxonomy. |
| Chain relationship | v0.5B Industry Map | relationship identities and revisions | source/target node IDs, `relationship_key`, `relation_kind`, description, status, cutoff, UTC, revision | No inferred relationship beyond the frozen persisted revision. |
| Industry observation | v0.5B Industry Map | observation identities and revisions | `observation_kind`, title, description, status, cutoff, UTC, revision | Only `driver`, `bottleneck`, `value_pool_shift`; no driver subtype. |
| Map evidence and conflict state | v0.5A/v0.5B | exact assertion/claim/evidence links | exact claim revisions, evidence IDs/grades/relations, conflicts, missing evidence | Evidence count or grade is not attractiveness. |
| Beneficiary identity | v0.5C Stage 1 | `stage1_beneficiaries` | `id`, `case_id`, `map_id`, `source`, `stock_code`, `created_at_utc` | Identity exists only because it was explicitly persisted. |
| Beneficiary revision | v0.5C Stage 1 | `stage1_beneficiary_revisions` | revision, selected map revision, exact stock row, `beneficiary_kind`, `assessment_status`, rationale, cutoff, UTC, supersedes | Taxonomy is exactly `direct / secondary / potential`; no rule version or analyst owner. |
| Company snapshot | market-data persistence frozen by Stage 1 | exact `stock_basic` row and ingestion run | stock name/code, exchange, Provider industry text, listing/status, source, run/series, cutoff/completion UTC | L1 Provider-normalized context; Provider `industry` is not Industry Alpha membership. |
| Stage 1 assertion and claim links | v0.5C Stage 1 | exact frozen link rows | node/relationship/observation revisions, claim revisions, evidence, conflict and missing states | No re-linking to newer compatible-looking revisions. |
| Candidate-pool state | v0.5C Stage 1 | candidate-pool revisions/memberships | exact supported frozen beneficiary revisions and unranked membership | Candidate-pool membership is not the complete Stage 1 set and must not replace it. |
| Company-research identity | v0.6A | `stage2_company_research` | exact Stage 1 beneficiary/pool/map/stock foreign keys, source, stock code, created UTC | Exists only for an explicit frozen Stage 1 handoff. |
| Company-research revision | v0.6A | company-research revisions | workflow, conclusion status, question, summary, cutoff, UTC, supersedes | Not an investment recommendation. |
| Financial-transmission hypothesis | v0.6A | financial hypothesis identities/revisions | mechanism, direction, operating metric, statement line, lag horizon, confidence, basis, cutoff, UTC, evidence/conflicts/missing | D3 analytical hypothesis, not a forecast promise. |

## Requested field gap matrix

| Roadmap request | 2A status | Rule |
| --- | --- | --- |
| Industry driver | Partially available | Display exact persisted observation title/description with raw `observation_kind=driver`; do not infer subtype. |
| Chain node and process position | Available within existing node model | Display exact `node_kind`, label and description. Do not invent process stages not persisted. |
| Bottleneck | Available | Display exact `observation_kind=bottleneck` records and their evidence. |
| Value-pool shift | Available | Display exact `observation_kind=value_pool_shift` records and their evidence. |
| Company product/service | Not typed | May appear only inside exact rationale/claims/hypothesis text. Do not extract or categorise automatically. |
| Directness of exposure | Available only as existing Stage 1 taxonomy | Display raw `direct / secondary / potential`; do not map to the roadmap four-level taxonomy. |
| D2 rule version | Unavailable | Display “未建模/不可用”; do not fabricate a rule version. |
| D3 analyst ownership | Unavailable | Display “未建模/不可用”; repository user or Git author is not analyst ownership. |
| Customer evidence | Not typed | Display exact claims/evidence only; no customer tag inferred from text. |
| Certification evidence | Not typed | Display exact claims/evidence only; no certification-stage field exists. |
| Capacity evidence | Not typed | Display exact claims/evidence only; no capacity category or unit normalization exists. |
| Production stage | Not typed | Display exact claims/evidence only; no production-stage enum exists. |
| Order stage | Not typed | Display exact claims/evidence only; no order-stage enum exists. |
| Financial transmission | Available when v0.6A research exists | Display exact frozen hypothesis revisions and missing/conflicting evidence. |
| Exact evidence/conflicts/revision/cutoff | Available | Existing detail contracts remain authoritative. |
| Recommendation-free table baseline | Available | Deterministic neutral table; no ranking score. |
| Graph view | Deferred | Optional later Product Task after table baseline; no need for v1 DoR. |

## Derivation and semantic qualification

### D0 direct persisted facts

Examples:

- stable IDs and foreign keys;
- revision numbers;
- stock code/name/exchange from the exact frozen `stock_basic` row;
- information cutoff dates and recorded UTC;
- exact source titles and evidence relations;
- raw `beneficiary_kind`, `assessment_status`, `observation_kind`, `node_kind` and `relation_kind` stored values.

A persisted enum value is a direct fact about what the system recorded. It is not automatically a direct fact about the real-world economy.

### D1 deterministic projections

Allowed 2A projections:

- selecting the latest cutoff-visible revision by existing revision ordering;
- counting the complete persisted Stage 1 set for the selected map and cutoff;
- stable neutral sorting;
- exact foreign-key presence of an existing Stage 2 company-research record;
- exact counts already produced by accepted map/beneficiary detail contracts.

Every D1 count must disclose its selected map, cutoff and input set. It must not be styled as confidence, importance or attractiveness.

### D2 rule classifications

Existing persisted allow-list classifications retain their owning-domain meaning. The 2A workspace does not create a new D2 rule.

Evidence grade, map assertion state and lifecycle/status fields must be labelled as stored classifications. They are not truth probabilities or investment scores.

### D3 analytical judgments

The following must be visually separated from facts and deterministic projections:

- `beneficiary_kind` as an analytical company-benefit classification;
- beneficiary rationale;
- claim statements whose `claim_kind` is inference;
- company-research conclusion and summary;
- financial-transmission mechanism, direction, lag, confidence and basis.

Because Stage 1 has no generic rule version or analyst-owner field, 2A must present `beneficiary_kind` as **existing Stage 1 analytical research state** rather than claiming a versioned D2 rule.

### Semantic Level

- Company identity context remains at the accepted level of the exact frozen market-data row and Provider run. Provider `industry` text remains Provider-attributed context only.
- Evidence, claims, map assertions, Stage 1 revisions and Stage 2 hypotheses retain their existing owning-domain qualification.
- The workspace does not upgrade any field to L2 or L3.
- No cross-provider, valuation or canonical-price comparison occurs.

## Selected-map and cutoff contract

### Explicit selector

- Workspace API requires one explicit `map_id`.
- Page startup may load a neutral map selector, but must not silently choose the first map.
- A `map_id` supplied in the page URL may prefill the explicit selection.
- No selection by map title, stock code, Provider industry or free-text similarity.

### Cutoff

- Optional `as_of_cutoff` uses existing date-granular domain visibility semantics.
- A revision is visible only when both its information cutoff/date and recorded UTC date are cutoff-visible under its owning domain.
- Frozen links must also be recorded no later than the owning frozen revision boundary.
- No fallback to a later or earlier revision when the exact frozen link is missing.
- An empty cutoff-visible set remains empty.

### Chronology

Information cutoff/date and recorded UTC must be displayed separately. A later-recorded judgment about older information remains later in chronology while retaining its older cutoff.

## Candidate 2A read surface

### Page

- Candidate page: `GET /industry-research`.
- Chinese-first, local, read-only and responsive.
- Primary navigation label: `产业研究`.
- The page does not replace `/industry-alpha` APIs; it is a product reading surface over accepted contracts.

### Selector API

Candidate:

```text
GET /industry-research/maps?as_of_cutoff=YYYY-MM-DD
```

Response contains scalar selector fields only:

- `map_id`;
- `map_key`;
- latest cutoff-visible revision ID/number/title/scope;
- information cutoff date;
- recorded UTC.

The selector must use one bounded scalar query path or one fixed small query set. It must not call `IndustryChainMapQueryService.list_maps()`, because that existing list service loads a complete map graph once per map.

### Workspace API

Candidate:

```text
GET /industry-research/maps/{map_id}/workspace?as_of_cutoff=YYYY-MM-DD
```

Response sections:

1. selected map identity and latest cutoff-visible revision;
2. frozen map snapshot from the accepted map-detail contract;
3. complete persisted Stage 1 beneficiary overview for the selected map/cutoff;
4. exact optional Stage 2 company-research link and latest visible research revision summary;
5. notices and unsupported fields.

The workspace response must not inline every company’s full evidence and financial-hypothesis graph. Full details are loaded only after explicit user action through existing accepted detail routes:

```text
GET /industry-alpha/beneficiaries/{beneficiary_id}?as_of_cutoff=YYYY-MM-DD
GET /industry-alpha/company-research/{company_research_id}?as_of_cutoff=YYYY-MM-DD
```

### Beneficiary overview fields

Each row may include only accepted scalar fields:

- beneficiary identity ID, case ID, map ID, source and stock code;
- exact stock name and exchange from the frozen `stock_basic` row;
- latest cutoff-visible beneficiary revision ID/number;
- raw `beneficiary_kind`;
- `assessment_status`;
- `rationale_summary`;
- selected map revision ID;
- information cutoff date and recorded UTC;
- supersedes revision ID;
- optional exact `company_research_id`;
- optional latest cutoff-visible company-research revision ID/number, workflow state, conclusion status, question, summary, cutoff and UTC.

No derived product, customer, certification, capacity, order or investment field may be added.

## Query architecture and N+1 boundary

### Existing services that may be reused

For one explicitly selected map, the implementation may call `IndustryChainMapQueryService.get_map()` once. Its complete map graph is the intended exact map-detail contract.

For explicit user-opened details, the implementation may call the existing Stage 1 beneficiary-detail and Stage 2 company-research-detail services once per user request.

### Existing services that must not be used for initial overview

- `IndustryChainMapQueryService.list_maps()` loads a complete map graph once per map.
- `Stage2CompanyResearchQueryService.list_research()` lists identities and then calls `load()` once per identity.
- `Stage1BeneficiaryQueryService.list_beneficiaries()` loads the complete Stage 1 map graph even though overview needs only scalar company and revision fields.

The new initial-load path must not compose those list services.

### Candidate stateless repository

A new read-only `IndustryBeneficiaryWorkspaceRepository` may perform a fixed query set independent of beneficiary count:

1. scalar map selector rows and visible map revisions;
2. all Stage 1 beneficiary identities for one explicit map;
3. their cutoff-visible revisions;
4. exact referenced `stock_basic` rows and ingestion runs;
5. Stage 2 company-research identities for the map and their cutoff-visible research revisions.

Grouping and latest-visible selection occur deterministically in application code using existing revision/cutoff rules. Queries use explicit foreign keys and selected `map_id`; no title, code-pattern or free-text join.

The implementation must assert that each overview row resolves exactly one required frozen stock row. Missing required identity/revision/provenance fails closed instead of synthesizing company data.

### Stage 2 link rule

A Stage 2 link is shown only when an exact persisted `Stage2CompanyResearch` row references the beneficiary identity/revision. No link is inferred from matching stock code alone.

If no exact Stage 2 record exists, return `company_research = null` and display “尚无冻结的公司财务传导研究”. The beneficiary row remains visible.

### Sorting

Default neutral order:

1. raw `beneficiary_kind` in the existing fixed order `direct`, `secondary`, `potential`;
2. source ascending;
3. stock code ascending;
4. beneficiary UUID text ascending.

This is a deterministic reading order, not a rank. The UI must say “排序” rather than “排名”.

No sorting by evidence count, assessment status, Stage 2 conclusion, confidence, recency, market performance or valuation.

## Presentation contract

### Page structure

1. **明确选择** — map selector and optional cutoff.
2. **产业地图摘要** — title, scope, revision, cutoff, recorded UTC.
3. **驱动 / 瓶颈 / 利润池迁移观察** — exact persisted observations and evidence state.
4. **已录入受益公司全量** — all cutoff-visible Stage 1 rows before downstream filtering.
5. **公司详情抽屉/区域** — exact Stage 1 rationale, assertions, claims, evidence, conflicts and missing evidence on explicit open.
6. **财务传导研究** — existing Stage 2 hypotheses when available; explicit unavailable state otherwise.
7. **边界说明** — no real-world coverage guarantee, no final four-level taxonomy, no ranking/advice.

### Required raw-value visibility

Chinese display labels may accompany technical values, but raw persisted values remain visible:

- `direct / secondary / potential`;
- `draft / supported / disputed / rejected`;
- `driver / bottleneck / value_pool_shift`;
- `positive / negative / mixed / uncertain` for financial hypotheses.

A translation dictionary is presentation only and must not merge or remap categories.

### Visual separation

Use separate visual treatment for:

- persisted identity/time/provenance facts;
- stored classifications and statuses;
- D3 rationale and hypotheses;
- conflicts and missing evidence;
- unsupported/unavailable fields.

Do not use green/red market-signal styling for beneficiary kind, evidence grade, conclusion, confidence or hypothesis direction.

### Allowed labels

- 产业地图
- 驱动观察
- 瓶颈观察
- 利润池迁移观察
- 已录入受益公司全量
- 现有 Stage 1 分类
- 研究状态
- 分类依据
- 精确证据
- 冲突证据
- 缺失证据
- 财务传导假设
- 尚无公司研究
- 研究截止
- 系统记录时间

### Prohibited labels

- 全市场完整名单
- 最强受益 / 核心龙头 / 首选标的
- 推荐 / 买入 / 卖出 / 持有
- 机会分 / 强度分 / 确定性排名
- 目标价 / 预期收益 / 上涨空间
- 已验证客户 / 已认证 / 已投产 / 已获订单，除非 those exact words are part of displayed source text and are not promoted to typed state

## Golden path

A production-realistic offline fixture contains:

- one persisted industry map with an accepted current revision;
- frozen nodes, relationships and driver/bottleneck/value-pool observations;
- several Stage 1 beneficiary identities whose latest visible revisions include `direct`, `secondary` and `potential`, with supported, draft and disputed states;
- exact stock rows and ingestion-run provenance;
- exact claims and A/B/C/D evidence, including one contradiction and one missing-evidence case;
- a Stage 2 company-research record and financial hypothesis for only a subset of beneficiaries.

Expected flow:

1. User opens `/industry-research`.
2. Selector lists persisted maps without silently choosing one.
3. User selects the fixture map and optional cutoff.
4. Workspace displays the frozen map observations.
5. Workspace displays every cutoff-visible persisted Stage 1 beneficiary, including disputed/draft rows and rows with no Stage 2 research.
6. User opens one beneficiary detail and sees exact frozen assertions, claims, evidence, conflicts and missing evidence.
7. If an exact Stage 2 record exists, user opens its financial-transmission hypotheses; otherwise the page shows explicit unavailability.
8. No valuation, price, score, recommendation or external network request occurs.

Fixture data must use only fields reachable through existing accepted command/persistence boundaries. It may not add typed product/customer/certification/capacity/order semantics absent from production models.

## Primary failure paths

### No database configuration

Selector/workspace API returns the existing deterministic 503 database-configuration boundary. The static page remains available and displays a local configuration error without exposing connection details.

### Map not found or cutoff-invisible

Return 404. Do not choose another map, remove the cutoff or fall back to the newest map.

### Empty beneficiary set

Return a valid empty `beneficiaries` array with the selected map context and an explicit statement that no persisted Stage 1 beneficiary is visible at the cutoff. Do not query all stocks or candidate pools as substitute coverage.

### Missing required frozen provenance

A beneficiary revision that cannot resolve its exact required stock row, ingestion run or map revision fails closed at the API boundary. Do not reconstruct the identity from `source + stock_code`.

### Missing Stage 2 research

Return null/unavailable for Stage 2. Do not derive a financial-transmission hypothesis from Stage 1 rationale or evidence text.

### Multiple incompatible Stage 2 matches

If persisted integrity unexpectedly produces more than one incompatible exact Stage 2 identity for one beneficiary/revision, fail closed with a deterministic data-integrity error. Do not choose by latest timestamp or stock-code match.

## Product Task classification after DoR

The 2A implementation qualifies as a bounded **Product Task** only if it:

- reads existing accepted models and exact foreign keys;
- adds no schema, migration or persistent workspace state;
- preserves all existing cutoff, revision, append-only and provenance rules;
- adds no new classification taxonomy or rule engine;
- adds no inferred identity or text extraction;
- uses only existing map detail, beneficiary detail and company-research detail semantics;
- adds one stateless scalar overview repository/query boundary;
- adds neutral presentation and deterministic routing only.

Implementation must stop and return to Architecture Preflight if it requires:

- a new beneficiary kind;
- a renamed/mapped classification;
- a new rule version, analyst owner or coverage state;
- a typed industry-driver subtype;
- typed product/customer/certification/capacity/production/order fields;
- a new persistent relationship or saved workspace state;
- changed cutoff, revision, evidence, provenance or Provider semantics;
- price, valuation, ranking or recommendation logic.

## Candidate implementation scope after independent DoR approval

Candidate new files:

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

Candidate modified file:

- `backend/main.py` for router and static-page registration only.

A matching `.codex/tasks/` implementation snapshot is required. Exact paths may be minimally adjusted to repository conventions without changing semantics.

No existing model, migration, command, Provider, domain-detail query, fixture source contract, release or version file is in scope.

## Validation matrix for later implementation

| Layer | Required checks |
| --- | --- |
| Selector repository | scalar map/revision fields only; cutoff visibility; no full-graph per-map loading. |
| Workspace repository | exact selected map; complete persisted Stage 1 set; exact stock provenance; exact Stage 2 links; fixed query count independent of company count. |
| Query semantics | latest visible revision; raw classification preserved; neutral ordering; empty set; no fallback; no inferred fields. |
| Cutoff | information and recorded visibility; frozen link boundaries; later information excluded. |
| Integrity | missing stock/run/map references fail closed; incompatible Stage 2 duplicate fails closed. |
| API | explicit map selector; malformed UUID/date 422; missing/cutoff-invisible map 404; database failures 503. |
| Detail integration | explicit user-opened Stage 1 and Stage 2 detail routes; no initial N+1 detail loading. |
| Presentation | Chinese-first; responsive; keyboard usable; raw technical values visible; facts/classifications/judgments/conflicts separated. |
| Safety | no innerHTML injection; no guessed URL; no credentials/raw DB errors; no external network. |
| Boundary | no valuation, score, rank, advice, target price, return or final taxonomy. |
| Regression | full pytest suite, existing demos and PostgreSQL path remain green. |

## Definition of Ready conclusion

### 2A

The existing-contract Industry Beneficiary Workspace can reach Definition of Ready as a Product Task after independent fixed-head review, provided the implementation follows this exact boundary:

- explicit selected map;
- complete **persisted** Stage 1 set at cutoff;
- exact existing classification values;
- scalar initial overview plus explicit on-demand details;
- exact Stage 2 frozen links only;
- no new semantic contract.

### 2B

The final roadmap taxonomy and typed industry/company evidence dimensions do not reach Definition of Ready. They require a separate Architecture Preflight, explicit ownership, migration decision, command contract, historical treatment and fixture/provider parity.

## Independent review checklist

The reviewer must verify at the fixed head:

1. exactly two documentation files changed;
2. no production behavior changed;
3. current Stage 1 taxonomy is not remapped;
4. persisted-set completeness is not confused with real-world exhaustive coverage;
5. 2A and 2B are separated;
6. initial-load queries avoid known list-service N+1/full-graph behavior;
7. Stage 2 linkage uses exact foreign keys, not stock-code inference;
8. cutoff, frozen revision, evidence, conflict and missing-data rules remain intact;
9. implementation scope is bounded to one Product Task;
10. no implementation Issue is created until the reviewer records fixed-head DoR approval.
