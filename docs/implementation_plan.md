# Personal Investment Research Implementation Plan

This plan is prospective. Each stage requires a separate authorized review issue before implementation. The current v0.2 fixture-backed Dashboard remains the active baseline.

## v0.2.1 Local Launcher Completion

- **Objective:** finish a safe local launcher handoff for ordinary users.
- **In scope:** reviewed launcher scripts, local usage documentation, Docker startup diagnostics, and focused tests.
- **Exclusions:** product workflow, real data, persistence, new APIs, and frontend frameworks.
- **Dependencies:** v0.2 baseline and Docker Compose configuration.
- **Acceptance:** launcher behavior is documented, non-destructive, bounded, and verified on available platforms; review is complete.
- **Tests:** local launcher checks, `python -m pytest -q`, and fixture demo.

## v0.3 Real-Data Persistence Foundation

- **Objective:** introduce reviewed provider interfaces, local persistence foundations, provenance, and validation for research inputs.
- **In scope:** data contracts, persistence design and migrations, local configuration, reconciliation, and local tests.
- **Exclusions:** cockpit calculations, Industry Alpha execution, portfolio simulation, broker behavior, and production operations.
- **Dependencies:** accepted product architecture, data-model decisions, and provider boundaries.
- **Acceptance:** persisted inputs are attributable, validated, and recoverable with clear cutoff-date handling.
- **Tests:** migration, provider-contract, provenance, validation, and fixture integration tests.

## v0.4 Market Cockpit

- **Objective:** provide local market-state monitoring for research timing and risk.
- **In scope:** snapshot models, indices, breadth, style, liquidity, sector rotation, crowding, market risk, and read-only presentation.
- **Exclusions:** trading signals, automatic recommendations, broker actions, and replacement of industry facts.
- **Dependencies:** v0.3 persistence and reviewed data sources.
- **Acceptance:** every snapshot has date, source, and missing-data behavior; outputs are local and auditable.
- **Tests:** calculation fixtures, cutoff-date checks, read-only contract tests, and no-live-network unit tests.

## v0.5 Industry Alpha Stage 1 And Evidence Infrastructure

- **Objective:** model industry maps and evidence-backed causal research.
- **In scope:** research cases, drivers, chain maps, bottlenecks, value-pool shifts, evidence, claims, conflicts, and revisions.
- **Exclusions:** canonical scoring implementation, final investment screens, paper portfolios, LLM execution, and real trading.
- **Dependencies:** v0.3 persistence and an accepted canonical Industry Alpha scoring reference.
- **Acceptance:** facts, inferences, conflicts, missing evidence, and cutoff dates are explicit and versioned.
- **Tests:** evidence provenance, claim-link, conflict, revision, and fixture workflow tests.

## v0.6 Stage 2 And Stock Research

- **Objective:** assess beneficiaries, financial transmission, expectations, valuation, catalysts, and risks from Stage 1 inputs.
- **In scope:** Stage 2 screens, company deep dives, valuation snapshots, independent industry/company/price/timing judgments, and Quant Core validation links.
- **Exclusions:** invented score weights, automatic final conclusions, real orders, and portfolio execution.
- **Dependencies:** accepted v0.5 evidence model and canonical scoring reference.
- **Acceptance:** Stage 2 cannot silently bypass Stage 1 evidence; assumptions and uncertainty remain visible.
- **Tests:** Stage handoff, beneficiary relationship, claim provenance, valuation snapshot, and Quant Core reference tests.

## v0.7 Watchlist And Verification Tasks

- **Objective:** manage personal research follow-up and historical status changes.
- **In scope:** watchlists, statuses, catalysts, risks, verification tasks, reminders, and revision history.
- **Exclusions:** multi-user collaboration, subscriptions, automated notifications to third parties, and trading actions.
- **Dependencies:** v0.5/v0.6 research records.
- **Acceptance:** status and task changes are attributable, reviewable, and never overwrite prior conclusions.
- **Tests:** status transition, task completion, revision-history, and fixture reminder tests.

## v0.8 Paper Portfolio And Simulated Trades

- **Objective:** record multiple personal simulated portfolios and their thesis context.
- **In scope:** manual simulated trades, positions, cash ledger, NAV, benchmarks, concentration, corporate actions, and thesis snapshots.
- **Exclusions:** broker integration, real orders, automated trading, performance promises, and tax/accounting advice.
- **Dependencies:** accepted watchlist/research records and persistence foundations.
- **Acceptance:** all records are explicitly simulated, reconstructable, and linked to immutable thesis snapshots.
- **Tests:** ledger, position, NAV, benchmark, concentration, corporate-action, and no-broker boundary tests.

## v0.9 Portfolio Analysis And Quant Core Integration

- **Objective:** compare simulated portfolio outcomes with versioned research and Quant Core validation artifacts.
- **In scope:** portfolio review, attribution-oriented analysis, benchmark comparison, research-thesis review, and controlled Quant Core references.
- **Exclusions:** autonomous allocation, live execution, broker actions, mandatory Qlib/LLM production runs, and SaaS features.
- **Dependencies:** v0.8 simulated records and stable Quant Core interfaces.
- **Acceptance:** analysis remains traceable to simulated records, research revisions, and reproducible Quant Core outputs.
- **Tests:** portfolio-review fixtures, traceability checks, Quant Core contract tests, and safety-boundary tests.
