# Personal Research Workflow

This document describes research discipline and the implemented flow through v0.6D. `docs/architecture_baseline.md` controls current-state and authorization interpretation.

## Current workflow boundary

Implemented research direction:

```text
market-data evidence
  -> research case and evidence ledger
  -> industry map
  -> Stage 1 beneficiary classification and candidate pool
  -> v0.6A company research and financial-transmission hypotheses
  -> v0.6B expectations and valuation observations
  -> v0.6C catalyst and risk assessments
  -> v0.6D industry/company quality judgments
```

Price judgment, timing judgment, Watchlist state, verification-task lifecycle, Paper Portfolio and portfolio review are not current runtime workflow entities.

## Research modes

The implemented and conceptual research modes are:

- **Stage 1 industry map:** establish drivers, value/profit-pool shifts, chain structure, bottlenecks and possible beneficiaries.
- **Stage 2 company research:** evaluate exact Stage 1 candidates through financial transmission, expectations, valuation observations, catalysts, risks and quality judgments.
- **Full two-stage research:** complete and freeze Stage 1 before Stage 2.
- **Company deep dive:** investigate one company within an explicit industry, evidence and cutoff boundary.

An unspecified research request defaults conceptually to Stage 1. Stage 2 may use only an exact accepted Stage 1 candidate-pool membership and must preserve that handoff.

## Canonical causal chain

```text
driver model
  -> value/profit-pool changes
  -> chain/process/business model
  -> supply-demand bottlenecks
  -> products and customer requirements
  -> competition
  -> beneficiary relationship
  -> financial transmission
  -> market expectations
  -> valuation observations
  -> catalysts, risks and quality judgments
```

A later valuation or market context cannot replace missing upstream industry, product, customer or competition evidence.

## Implemented two-stage process

1. Define research question, scope and information cutoff.
2. Build the driver model and value/profit-pool hypothesis.
3. Map chain nodes, relationships, bottlenecks, products, customers and competition.
4. Record evidence-backed facts and explicit inferences.
5. Classify supported Stage 1 beneficiaries and freeze the candidate-pool handoff.
6. Create company-research revisions and financial-transmission hypotheses from that exact membership.
7. Record market expectations and valuation observations with exact provenance and explicit missing data.
8. Record catalyst and risk assessments over exact accepted upstream boundaries.
9. Record independent industry/company quality judgments with outcome and evidence state kept separate.
10. Add later revisions without rewriting historical cutoff context.

Every completed research output retains a bounded section titled `后续验证清单` for unresolved evidence, conflicts, assumptions and invalidation checks. This field is research metadata; it is not yet a scheduled task or reminder lifecycle.

## Conceptual future judgments

Long-term research may distinguish:

- industry quality;
- company quality;
- price interpretation;
- timing interpretation.

Only industry/company quality judgment records are implemented.

“Good price” and “good timing” remain conceptual labels. They must not be treated as current enums, tables, APIs, recommendations or automatic conclusions.

Before any price interpretation can be reconsidered, a separately reviewed upstream design must establish:

- canonical market-price measurement semantics;
- unit/currency and decimal ownership;
- production-reachable provenance;
- structured valuation comparison eligibility;
- fixture/provider parity.

A generic v0.6B `observed_value` and optional `daily_price` provenance link do not establish those semantics by themselves.

## Evidence and claims

- **A:** official or primary evidence.
- **B:** reliable industry evidence.
- **C:** auxiliary media or research evidence.
- **D:** leads or rumors; D-grade material cannot independently support a conclusion.

Every material claim records source, source date, information cutoff, evidence grade, summary, inference flag, inference basis, confidence, conflicts and pending verification.

Facts are observable and attributable. Inferences are explicitly labeled and include basis and confidence. Conflicting evidence stays linked and visible. When reliable public evidence is absent, record `尚未获得可靠公开证据` rather than filling the gap with an assumption.

## Lifecycle and conclusion discipline

Workflow progress and research conclusions are separate concepts. Implemented Stage 2 modules preserve their reviewed state vocabularies and exact revisions; one field cannot silently upgrade or rewrite another.

Future Watchlist lifecycle or formal personal conclusion vocabularies require their own accepted design and must not be inferred from v0.6A-v0.6D fields.

## Historical integrity

- Material changes create revisions.
- Accepted revisions bind exact upstream records and links.
- Both information cutoff and UTC recorded/imported/completed chronology prevent later-information leakage.
- Later evidence may strengthen, weaken or contradict a new revision but cannot rewrite a historical one.
- Current and historical reads use deterministic explicit ordering and strict JSON.

## No-invention boundary

Do not fabricate customers, market share, capacity, orders, revenue proportions, certification status or other unsupported operating facts.

Rumors, repeated narratives and concept lists are not facts. D-grade material remains a lead until corroborated. Uncertainty remains visible; confidence wording cannot convert an inference into a fact.

## Quant Core role

Factor, ranking, backtest, ML-boundary and report outputs may serve as reproducible validation artifacts. They do not replace Stage 1 facts, Stage 2 evidence or manual research judgment, and they do not automatically create product workflow state.

## Current authorization

Issue #72 authorizes documentation alignment only. No price/timing judgment, Watchlist behavior, migration or new application capability may begin from this workflow document.