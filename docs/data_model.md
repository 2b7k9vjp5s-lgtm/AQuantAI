# Personal Research Conceptual Data Model

This document defines conceptual entities and relationships for later reviewed persistence work. It is not a database schema, migration plan, ORM model, or API contract.

## Research And Market Context

- **Market snapshot:** timestamped local view of indices, breadth, style, liquidity, sector rotation, crowding, and market risk.
- **Research case:** versioned work container with mode, scope, cutoff date, separate lifecycle and conclusion statuses, conclusions, and linked revisions.
- **Research scope:** market, industry, company universe, geography, horizon, and exclusion context for a research case.
- **Industry driver, chain node, bottleneck, and value-pool shift:** linked industry-map concepts that explain a proposed causal path.
- **Company beneficiary relationship:** a company's proposed relationship to a chain node, driver, product, customer, or bottleneck, including its financial transmission assumptions.

## Evidence And Research Judgment

- **Evidence:** dated source artifact with provenance and grade: A for official or primary evidence, B for reliable industry evidence, C for auxiliary media or research evidence, and D for leads or rumors. D-grade evidence cannot independently support a conclusion.
- **Claim:** a factual statement or explicitly labeled `推断` belonging to a research case. Every material claim records source, source date, information cutoff date, evidence grade, summary, inference flag, inference basis, confidence, conflicts, and pending verification. Missing support is recorded as `尚未获得可靠公开证据`.
- **Claim-evidence link:** the relationship that states whether evidence supports, contradicts, or contextualizes a claim.
- **Conflict:** a reviewed disagreement between evidence items or claims, with an explicit resolution state.
- **Screen, expectation, valuation snapshot, catalyst, and risk:** dated assessment artifacts linked to a research case or company relationship.
- **Case lifecycle status:** versioned workflow progress using `draft`, `evidence-gathering`, `under-review`, `watching`, `verified`, `invalidated`, or `archived`.
- **Research conclusion status:** a separate versioned conclusion using one of eight canonical values: `核心研究候选`, `估值合理，可持续跟踪`, `公司优秀但价格偏贵`, `等待业绩验证`, `认证期高赔率观察`, `周期拐点观察`, `产业相关但受益纯度低`, or `逻辑证伪或排除`.
- **Verification task:** the task used to confirm, weaken, contradict, or leave unresolved a linked claim or thesis. Pending tasks form the mandatory `后续验证清单` at the end of each completed research output.
- **Stage 1 beneficiary classification:** identifies a company as a direct, secondary, or potential beneficiary. Only companies with one of these Stage 1 classifications can enter a Stage 2 candidate pool.
- **Stage 2 company-research identity:** a stable identity created only from one exact frozen candidate-pool membership. It retains the exact pool revision, membership, beneficiary revision, map revision, Stage 1 assertion links, successful `stock_basic` row and handoff claim/evidence boundary.
- **Stage 2 research-file revision:** an immutable lifecycle/conclusion snapshot containing a research question, bounded summary, cutoff, UTC timestamp, exact accepted hypothesis revisions and a completed-state `后续验证清单`.
- **Financial-transmission hypothesis revision:** an explicitly labeled inference from an exact Stage 1 assertion to an operating metric and financial-statement line. It freezes direction, lag/horizon, confidence, basis, exact claim revisions, exact evidence links, conflicts and missing evidence.
- **Stage 2 market-expectation revision:** an immutable observation of a market or research expectation. It freezes one exact company-research revision, accepted hypothesis revisions, exact claim revisions, and exact evidence links. It is descriptive only and has no score, rank, recommendation, or trading meaning.
- **Stage 2 valuation snapshot revision:** an immutable valuation-context observation. It freezes the same Stage 2 boundaries and may optionally bind one exact local `daily_price` row from a successful ingestion run. It records observed context or explicit missing data; it does not produce target price, fair value, expected return, upside/downside, or good-price/good-timing output.

## Watchlists And History

- **Watchlist:** a personal collection of research cases or companies.
- **Watchlist entry:** current research status, catalysts, risks, verification tasks, and references to source cases.
- **Revision:** immutable historical snapshot of a conclusion, status change, or material thesis update.

## Paper Portfolio

- **Paper portfolio:** a named, simulated portfolio with base currency, benchmark reference, and local-only purpose.
- **Simulated order and simulated trade:** manual paper records only; they have no broker, real-order, or execution meaning.
- **Position, cash ledger, NAV, benchmark, and corporate action:** time-series records used to reconstruct simulated portfolio state and comparison.
- **Thesis snapshot:** an immutable copy of the relevant research conclusion, risks, catalysts, and evidence state associated with a simulated position at a point in time.

## Quant Core Records

Existing Quant Core concepts remain reusable records: normalized provider data, factor values and scores, ranking outputs, backtest results, ML feature/label/prediction artifacts, research reports, and read-only Dashboard payloads. Later product records reference these outputs as versioned validation inputs; Quant Core does not own product workflow state.

## Relationship Summary

```text
Market snapshot -> research case -> claims <-> evidence
Research case -> industry map -> Stage 1 beneficiary classification -> Stage 2 candidate pool
Stage 2 candidate-pool membership -> company research -> financial-transmission hypotheses / verification items
Research case -> screens / valuation snapshots / catalysts / risks / verification tasks
Research case -> watchlist entry -> revision history
Research case -> thesis snapshot -> paper portfolio -> simulated trades / positions / NAV
Quant Core records -> research-case validation inputs
```

The merged v0.5B boundary provides stable map, node, relationship, and observation identities with immutable revisions. The v0.5C boundary adds append-only Stage 1 beneficiary identities and revisions that freeze one exact local `stock_basic` row, one exact map revision, exact contained map assertions, and exact v0.5A claim revisions. Candidate-pool revisions freeze only exact supported beneficiary revisions from the same map boundary, without scores, weights, ranks, recommendations, or Stage 2 conclusions.

The v0.6A boundary starts from one exact candidate-pool membership and adds append-only Stage 2 research-file and financial-transmission hypothesis revisions. It freezes exact Stage 1 and evidence boundaries, applies dual cutoff visibility, and adds no valuation, score, rank, target price, recommendation or trading semantics. The v0.6B boundary adds append-only expectation and valuation-context observations over exact v0.6A boundaries, while preserving the same cutoff anti-leakage and non-advisory constraints.
