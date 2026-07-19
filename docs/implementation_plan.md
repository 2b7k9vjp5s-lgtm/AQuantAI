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

### v0.4A Authorized Foundation

The first v0.4 slice is limited to deterministic selected-universe breadth, participation, realized-volatility, drawdown, provenance, and completeness from existing persisted stock-basic, daily-price, and trade-calendar snapshots. Official indices, sectors, style, valuation, crowding, derived-snapshot persistence, and automatic refresh require later separately reviewed data coverage and are explicitly unsupported in v0.4A.

### v0.4B Authorized Benchmark Context

The second v0.4 slice is limited to separate provider-attributed benchmark-index daily persistence, one reviewed bounded AKShare endpoint, explicit benchmark series selection, close-based context, provenance, cutoff/session alignment, and read-only presentation. It does not authorize sectors, style, valuation, crowding, relative-performance signals, recommendations, or automatic collection.

### v0.4C Authorized Sector Market Context

The third v0.4 slice is limited to a separate provider-attributed Eastmoney industry-board taxonomy and daily-history series, exact stable-code selection, deterministic exact-session descriptive metrics, provenance, cutoff/session alignment, and optional read-only Market Cockpit presentation. It does not authorize sector constituents, company beneficiaries, Industry Alpha evidence or conclusions, style, valuation, crowding, composite scores, recommendations, automatic collection, or trading behavior.

### v0.4D Authorized Liquidity Distribution Context

The fourth v0.4 slice is limited to deterministic liquidity-distribution statistics over the same selected-equity complete snapshot, effective session, and persisted open-session sequence already selected for v0.4A. It uses only eligible positive `daily_price.amount` observations and adds latest total/median amount, descriptive top-5/top-decile concentration, exact fixed-cohort 5/20-prior-session activity ratios, and above-prior-20-median participation. It adds no provider endpoint, ingestion, persistence, migration, independent series, calendar, style, valuation, crowding conclusion, signal, recommendation, or automatic collection.

### v0.4E Authorized Price-Behavior Proxy Context

The fifth v0.4 slice is limited to deterministic selected-universe price-behavior proxies over the same physical equity snapshot, accepted effective session, filtered close lookup, and persisted open-session sequence. It adds exact complete-window 20/60-session momentum, per-stock 20-return sample volatility annualized by `sqrt(252)`, independent cohort summaries, and one fixed matched-cohort four-bucket distribution. It does not claim canonical style factors, factor exposures, a market regime, risk appetite, valuation, crowding, signals, recommendations, or investment rankings, and adds no provider, ingestion, persistence, migration, selector, series, calendar, or automatic collection.

## v0.5 Industry Alpha Stage 1 And Evidence Infrastructure

- **Objective:** model industry maps and evidence-backed causal research.
- **In scope:** research cases, drivers, chain maps, bottlenecks, value-pool shifts, evidence, claims, conflicts, and revisions.
- **Exclusions:** canonical scoring implementation, final investment screens, paper portfolios, LLM execution, and real trading.
- **Dependencies:** v0.3 persistence and an accepted canonical Industry Alpha scoring reference.
- **Acceptance:** facts, inferences, conflicts, missing evidence, and cutoff dates are explicit and versioned.
- **Tests:** evidence provenance, claim-link, conflict, revision, and fixture workflow tests.

### v0.5A Authorized Evidence Ledger Foundation

The first v0.5 slice is limited to a local, append-only research-case and evidence ledger. It separates workflow state from conclusion status; records immutable A/B/C/D evidence, versioned facts and inferences, explicit support and contradiction links, frozen case-revision claim membership, and mandatory follow-up verification metadata; and provides cutoff-aware read-only APIs plus an offline fixture demo. It does not authorize industry scoring, causal-chain conclusions, company-beneficiary mapping, Stage 2 stock research, LLM execution, scraping, recommendations, signals, portfolios, or trading.

### v0.5B Authorized Evidence-Backed Chain Maps

The second v0.5 slice is limited to append-only industry-map, node, directed-relationship, driver, bottleneck, and value-pool-shift observation revisions. Every assertion binds exact v0.5A claim revisions, map revisions freeze exact assertion revisions, and current/historical read-only views preserve A/B/C/D grades, conflicts, missing evidence, UTC chronology, and cutoff boundaries. It does not authorize scoring, weights, rankings, company beneficiaries, Stage 2 research, LLM/provider execution, scraping, recommendations, signals, portfolios, brokers, orders, or trading.

### v0.5C Authorized Stage 1 Beneficiary Classifications

The third v0.5 slice is limited to append-only direct, secondary, and potential company-beneficiary classifications. Every revision freezes one exact successful local `stock_basic` row, one exact v0.5B map revision, exact assertions contained in that map revision, and exact v0.5A claim revisions. Supported classifications require visible A/B/C-backed support without contradiction; D-only and disputed states remain explicit. Candidate-pool revisions freeze only exact supported classifications from one map boundary and have no score, weight, rank, target price, recommendation, or investment-priority semantics. Financial transmission, Stage 2 deep research, valuation, LLM/provider execution, scraping, recommendations, portfolios, brokers, orders, and trading remain unauthorized.

## v0.6 Stage 2 And Stock Research

- **Objective:** assess beneficiaries, financial transmission, expectations, valuation, catalysts, and risks from Stage 1 inputs.
- **In scope:** Stage 2 screens, company deep dives, valuation snapshots, independent industry/company/price/timing judgments, and Quant Core validation links.
- **Exclusions:** invented score weights, automatic final conclusions, real orders, and portfolio execution.
- **Dependencies:** accepted v0.5 evidence model and canonical scoring reference.
- **Acceptance:** Stage 2 cannot silently bypass Stage 1 evidence; assumptions and uncertainty remain visible.
- **Tests:** Stage handoff, beneficiary relationship, claim provenance, valuation snapshot, and Quant Core reference tests.

### v0.6A Authorized Company-Research Foundation

The first v0.6 slice is limited to append-only company-research files created from exact frozen v0.5C candidate-pool memberships and evidence-bound financial-transmission hypotheses. It freezes the exact beneficiary, map, company snapshot, claim and evidence boundaries; keeps UTC chronology and historical cutoffs fail-closed; and requires a `后续验证清单` for completed revisions. It does not authorize valuation, scores, weights, rankings, target prices, recommendations, Quant Core automatic scoring, LLM/provider execution, scraping, portfolios, brokers, orders or trading.

### v0.6B Authorized Expectation And Valuation Snapshots

The second v0.6 slice is limited to append-only market-expectation and valuation-observation snapshots bound to exact v0.6A company-research revisions, exact supported/disputed hypothesis revisions, and exact claim/evidence boundaries. Valuation snapshots may optionally bind one exact local `daily_price` row from a successful ingestion run for provenance. They never compute target price, fair value, expected return, upside/downside, score, rank, recommendation, good-price/good-timing, catalyst/risk judgment, provider collection, LLM output, portfolio action, broker action, order, or trade.

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
