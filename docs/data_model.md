# Personal Research Conceptual Data Model

This document describes conceptual entities and ownership through the merged v0.6D capability stage. It is not a database schema, migration plan or implementation authorization.

`docs/architecture_baseline.md` is authoritative for current state, dependencies, invariants and future delivery gates.

## Market-data evidence

- **Ingestion run:** immutable attempt metadata including provider, status, scope, cutoff, contract/adapter provenance and canonical series identity.
- **Snapshot series:** canonical identity separating incompatible stock scopes, datasets, date ranges, adjustment policies, contracts and compatibility parameters.
- **Stock-basic, daily-price and trade-calendar rows:** persisted provider-attributed observations belonging to an explicit ingestion run/series.
- **Market Cockpit context:** deterministic selected-series breadth, risk, benchmark/sector, liquidity and price-behavior read models. These are descriptive context, not workflow conclusions.

A provider row does not automatically possess every downstream semantic meaning. In particular, a canonical reusable market-price evidence object with explicit measurement kind, unit and currency is not yet an implemented standalone domain contract.

## Evidence ledger

- **Research case:** stable work container with immutable revisions, workflow state, conclusion state, cutoff and UTC chronology.
- **Evidence item:** dated source artifact with provenance and A/B/C/D source-strength grade.
- **Claim revision:** fact or explicit inference with source, cutoff, basis, confidence, uncertainty and missing-evidence semantics.
- **Claim-evidence link:** support, contradiction or context relation between exact claim and evidence revisions.
- **Conflict:** reviewed disagreement preserved with resolution state.
- **Verification metadata:** bounded follow-up items stored with research outputs. These are not yet scheduled tasks or reminders.

D-grade evidence cannot independently support a conclusion. Missing support remains explicit as `尚未获得可靠公开证据`.

## Stage 1 Industry Alpha

- **Industry map identity/revision:** versioned map scope and cutoff.
- **Node and relationship identities/revisions:** explicit chain structure and direction.
- **Driver, bottleneck and value-pool observations:** evidence-bound assertions included in an exact map revision.
- **Beneficiary identity/revision:** direct, secondary or potential company relationship bound to exact Stage 1 assertions, claims/evidence and one exact successful stock-basic snapshot.
- **Candidate-pool revision:** frozen set of exact supported beneficiary revisions from one accepted map boundary; it has no score, weight, rank or recommendation meaning.

## Stage 2 company research

### v0.6A company-research boundary

- **Company-research identity:** stable identity created only from one exact frozen candidate-pool membership.
- **Company-research revision:** immutable workflow/conclusion snapshot with research question, summary, cutoff, UTC timestamp and bounded follow-up verification.
- **Financial-transmission hypothesis identity/revision:** explicit inference from accepted Stage 1 assertions to operating metrics and financial-statement effects, with direction, lag/horizon, confidence, basis and exact evidence boundary.

### v0.6B expectations and valuation observations

- **Market-expectation identity/revision:** immutable descriptive expectation over one exact company-research revision, accepted hypotheses and exact claim/evidence links.
- **Valuation-snapshot identity/revision:** immutable valuation-context observation with method, metric context, optional canonical numeric text, unit/currency as recorded, comparison description, assumptions, status, confidence and explicit missing-data state.
- **Optional local-price provenance:** one exact `daily_price` row from a successful ingestion run may be linked for context and chronology.

A generic valuation `observed_value` is not automatically eligible as a price-comparison point. An optional local-price link remains provenance/context and does not by itself define canonical measurement kind, unit or currency semantics.

### v0.6C catalyst and risk assessments

- **Catalyst assessment identity/revision:** immutable dated assessment over exact v0.6A/v0.6B and evidence boundaries.
- **Risk assessment identity/revision:** immutable downside, thesis-invalidation and mitigant assessment over exact accepted upstream boundaries.

These are not monitoring jobs, alerts, reminders, task lifecycles, scores or recommendations.

### v0.6D quality judgments

- **Industry-quality judgment identity/revision:** manual outcome and evidence-state record with driver durability, value-pool direction, chain/bottleneck support, rationale, uncertainty, criteria and follow-up verification.
- **Company-quality judgment identity/revision:** manual outcome and evidence-state record with beneficiary credibility, financial-transmission credibility, execution risks, rationale, uncertainty, criteria and follow-up verification.
- **Frozen links:** exact company-research, hypothesis, expectation, valuation, catalyst, risk, claim and evidence revisions.

Outcome and evidence state remain separate. These records are not formal recommendations, price/timing judgments, Watchlist states or portfolio actions.

## Not implemented

The following conceptual entities are not current runtime models:

- price judgment;
- timing judgment;
- Watchlist and Watchlist-entry lifecycle;
- scheduled verification task/reminder;
- Paper Portfolio, simulated order/trade, position, cash ledger or NAV;
- thesis snapshot attached to a simulated position;
- product-workflow Quant Core score/link.

Issue #70 and PR #71 are superseded and closed without merge. No v0.6E table, migration or API exists.

## Ownership rules

| Information | Owner |
| --- | --- |
| Provider rows, ingestion status, scope, cutoff and series identity | Market-data persistence |
| Canonical reusable market-price measurement/value/unit/currency semantics | Future separately reviewed market-data/evidence contract |
| Evidence grades, claims, conflicts and support relations | v0.5 evidence ledger |
| Company-research state and financial-transmission hypotheses | v0.6A |
| Expectations and valuation observations | v0.6B |
| Catalyst and risk assessment state | v0.6C |
| Industry/company quality outcome and evidence state | v0.6D |
| Price/timing interpretation | Future conceptual workflow; not implemented |

A downstream module must not create missing upstream meaning through names, free text, identifier patterns, provider labels, copied currency or defaults.

## Shared historical rules

- Stable identities have append-only immutable revisions where applicable.
- Accepted downstream records bind exact upstream revisions and links.
- Corrections append revisions rather than updating accepted history.
- Information cutoff and actual UTC chronology both govern visibility.
- Current and historical reads use explicit selectors, deterministic ordering and strict JSON.
- Multi-row creation is atomic; failure rolls back the complete new boundary.
- Fixtures must use production-reachable fields and preserve cross-database semantic determinism.

## Relationship summary

```text
market-data evidence
  -> research case -> claims <-> evidence/conflicts
  -> industry map -> beneficiary classification -> candidate pool
  -> company research -> financial-transmission hypotheses
  -> expectations / valuation observations
  -> catalyst / risk assessments
  -> industry / company quality judgments
```

No later conceptual entity is authorized by this relationship summary. New persistence requires a separate accepted Issue and migration decision.