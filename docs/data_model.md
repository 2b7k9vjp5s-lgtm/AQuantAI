# Personal Research Conceptual Data Model

This document defines conceptual entities and relationships for later reviewed persistence work. It is not a database schema, migration plan, ORM model, or API contract.

## Research And Market Context

- **Market snapshot:** timestamped local view of indices, breadth, style, liquidity, sector rotation, crowding, and market risk.
- **Research case:** versioned work container with mode, scope, cutoff date, status, conclusions, and linked revisions.
- **Research scope:** market, industry, company universe, geography, horizon, and exclusion context for a research case.
- **Industry driver, chain node, bottleneck, and value-pool shift:** linked industry-map concepts that explain a proposed causal path.
- **Company beneficiary relationship:** a company's proposed relationship to a chain node, driver, product, customer, or bottleneck, including its financial transmission assumptions.

## Evidence And Research Judgment

- **Evidence:** dated source artifact with provenance, source quality, directness, and reproducibility information.
- **Claim:** a factual statement or labeled inference belonging to a research case.
- **Claim-evidence link:** the relationship that states whether evidence supports, contradicts, or contextualizes a claim.
- **Conflict:** a reviewed disagreement between evidence items or claims, with an explicit resolution state.
- **Screen, expectation, valuation snapshot, catalyst, and risk:** dated assessment artifacts linked to a research case or company relationship.
- **Research status and verification task:** versioned workflow state and the task used to confirm, weaken, or invalidate a linked claim or thesis.

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
Research case -> industry map -> company beneficiary relationship
Research case -> screens / valuation snapshots / catalysts / risks / verification tasks
Research case -> watchlist entry -> revision history
Research case -> thesis snapshot -> paper portfolio -> simulated trades / positions / NAV
Quant Core records -> research-case validation inputs
```
