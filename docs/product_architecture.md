# Personal Investment Research Product Architecture

## Positioning And Boundaries

AQuantAI is planned as a local-first, personal-use AI investment research workbench. It supports disciplined research, review, and simulated portfolio record-keeping; it is not a SaaS product, investment-advice service, broker, or order-management system.

The implemented v0.2 baseline remains a fixture-backed, read-only research Dashboard. The architecture in this document is approved planning for future reviewed releases, not a statement of implemented runtime behavior.

## User Flow

```text
Market monitoring
  -> Industry Alpha research
  -> Company research and pricing
  -> Watchlist and verification tasks
  -> Paper portfolios and simulated trades
  -> Quant validation and review
```

Market observations can create research cases. Research produces evidence-backed claims, candidate companies, risks, catalysts, and verification tasks. A reviewed thesis may be watched or recorded in a paper portfolio. Later market, industry, company, and Quant Core outputs inform review; they do not overwrite historical conclusions or thesis snapshots.

## Information Architecture

| Area | Purpose | Current state |
| --- | --- | --- |
| Home | Local market summary, recent research changes, and verification reminders. | Planned |
| Market Cockpit | Selected-universe breadth, participation, liquidity distribution, risk, provenance, completeness, and optional separately selected provider-attributed benchmark and sector context. | v0.4A-v0.4C implemented; v0.4D selected-equity liquidity distribution in review; style, valuation, and crowding conclusions unsupported |
| Industry Alpha | Stage 1 industry mapping and Stage 2 investment screening with evidence and cutoff dates. | Planned |
| Stock Research | Company role, beneficiary relationship, financial transmission, expectations, valuation, catalysts, and risks. | Planned |
| Watchlist | Research status, catalysts, risks, verification tasks, and status history. | Planned |
| Paper Portfolio | Multiple simulated portfolios, manual simulated trades, positions, cash, NAV, benchmarks, concentration, and thesis snapshots. | Planned |
| Settings | Local market-data and LLM-provider configuration. | Planned |
| Quant Core | Existing provider, factor, ranking, backtest, ML-boundary, report, and read-only Dashboard capabilities. | Implemented v0.2 baseline |

## Modules And Dependency Direction

```text
Frontend pages
      -> FastAPI application services
      -> Product-domain modules and stable provider interfaces
      -> PostgreSQL persistence and external-provider adapters

Quant Core -> product-domain validation and review inputs
```

- Product workflow ownership stays in AQuantAI. External projects and vendors are adapters or infrastructure, never the owner of research workflow state.
- Business modules depend on stable provider interfaces, not directly on AKShare, Tushare, Qlib, VectorBT, or a single LLM vendor.
- Quant Core remains a supporting, deterministic research layer. It can validate a Stage 1 candidate pool, but does not independently create the final research conclusion.
- Market state informs timing and risk. It must not overwrite established industry facts, claim evidence, or versioned conclusions.
- Future persistence and user-facing modules are introduced only through separately reviewed stages.

## Research Discipline And Safety

- Facts require evidence, provenance, and an information cutoff date.
- Inferences must state their basis and confidence. Missing evidence and unresolved conflicts must be explicit.
- Workflow lifecycle and formal research-conclusion status are separate, independently versioned fields.
- Evidence follows A/B/C/D grading; D-grade leads or rumors cannot independently support a conclusion.
- The system must not fabricate customers, market share, capacity, orders, revenue proportions, certification status, or other unsupported operating facts. Rumors and concept-stock lists must never be presented as facts.
- Every completed research output ends with a mandatory `后续验证清单`.
- Important conclusions, watchlist state changes, and paper-position theses are versioned rather than overwritten.
- Paper portfolios contain simulated records only. They must expose no broker connectivity, real-order behavior, trading buttons, or automated execution.
- The system remains personal-use, local-first, research-only, and non-advisory. Authentication, multi-user SaaS, subscriptions, and payments are outside this architecture scope.
