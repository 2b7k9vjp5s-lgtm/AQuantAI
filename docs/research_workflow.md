# Personal Research Workflow

## Scope And Task Modes

Every research case records its scope, target market or industry, company set where applicable, and information cutoff date. The available planned task modes are:

- **Stage 1 industry map:** establish industry drivers, value and profit-pool shifts, chain structure, bottlenecks, and possible beneficiaries.
- **Stage 2 investment screen:** evaluate candidate companies, expectations, valuation, catalysts, crowding, downside, and risk-reward using the Stage 1 evidence base.
- **Full two-stage research:** complete Stage 1 before Stage 2; preserve the handoff between both stages.
- **Company deep dive:** investigate one company within an explicit industry and time scope without implying a complete industry screen.

An unspecified research request defaults to Stage 1. Stage 1 maps beneficiaries without excluding them because of market capitalization, valuation, prior share-price gains, or market attention. Those considerations belong to later screening and timing judgments.

Stage 2 may screen only companies that Stage 1 has identified as direct, secondary, or potential beneficiaries. Within that candidate-pool boundary, Stage 2 evaluates beneficiary purity, financial transmission, market expectations, business-type valuation, catalysts, crowding, downside, and risk-reward.

Exact scoring fields, score weights, and ranking thresholds are intentionally pending the canonical Industry Alpha scoring reference. This workflow does not invent them.

## Canonical Causal Chain

Every industry study follows this sequence:

```text
driver model -> value/profit-pool changes -> chain/process/business model
-> supply-demand bottlenecks -> products -> customer certification
-> competition -> direct beneficiaries -> financial transmission
-> market expectation -> valuation
```

The chain must remain traceable from the driver through beneficiary economics. A later valuation or timing view cannot substitute for missing upstream industry, product, customer-certification, or competition evidence.

## Two-Stage Workflow

1. Define the research question, scope, cutoff date, and required decisions.
2. Build the driver model and identify the value or profit-pool shifts it may cause.
3. Map the chain, process, business model, supply-demand bottlenecks, products, customer certification, competition, and direct beneficiary relationships in causal order.
4. Record evidence-backed facts before drawing valuation or timing conclusions.
5. Trace each candidate's financial transmission: revenue exposure, margin or cost mechanism, capacity, customer, certification, and execution dependencies.
6. Compare market expectations, valuation snapshots, catalysts, crowding, downside paths, and risk-reward.
7. Form independent judgments on good industry, good company, good price, and good timing.
8. Add verification tasks for assumptions, catalysts, conflicts, missing evidence, and thesis invalidation signals.
9. Review later evidence without rewriting the historical conclusion or its cutoff-date context.

Every completed research output must end with a section titled `后续验证清单`. It lists unresolved evidence, conflicts, assumptions, catalyst checks, financial-transmission checks, customer or certification checks, and thesis invalidation signals, each linked to a verification task or explicitly marked pending.

## Independent Judgments

The workflow keeps the following judgments separate:

- **Good industry:** durable driver, favorable value-pool shift, and an evidence-supported chain structure.
- **Good company:** a credible beneficiary relationship and financial transmission path, with execution risks stated.
- **Good price:** expectations and valuation are considered against the research case; no price conclusion is inferred from industry quality alone.
- **Good timing:** market state, catalyst schedule, crowding, liquidity, and downside are considered without changing established facts.

## Lifecycle And Conclusion Statuses

`case_lifecycle_status` controls workflow progress only. Its planned values are `draft`, `evidence-gathering`, `under-review`, `watching`, `verified`, `invalidated`, and `archived`. A lifecycle change records its reason and preserves history.

`research_conclusion_status` records the formal investment-research conclusion independently of workflow progress. Its canonical values are:

- `核心研究候选`
- `估值合理，可持续跟踪`
- `公司优秀但价格偏贵`
- `等待业绩验证`
- `认证期高赔率观察`
- `周期拐点观察`
- `产业相关但受益纯度低`
- `逻辑证伪或排除`

A case can be `under-review` in its lifecycle while retaining a prior conclusion status. Changes to either field are versioned; neither field silently rewrites the other.

A verification task has an owner in the personal workflow, a due or review date, a linked claim or thesis, a required evidence type, and a completion result. Completion can confirm, weaken, contradict, or leave a claim unresolved; it never silently deletes prior evidence.

## Evidence, Claims, And Revisions

- Evidence uses the following grades. Grades communicate source strength, not investment scores:
  - **A:** official or primary evidence.
  - **B:** reliable industry evidence.
  - **C:** auxiliary media or research evidence.
  - **D:** leads or rumors; D-grade material cannot independently support a conclusion.
- Every material claim records source, source date, information cutoff date, evidence grade, evidence summary, inference flag, inference basis, confidence, conflicts, and pending verification.
- Facts are observable and attributable. Inferences are explicitly labeled `推断` and include their basis and confidence.
- Conflicting evidence is linked to the same claim and displayed as unresolved until reviewed.
- When evidence is absent, the record uses the explicit language `尚未获得可靠公开证据` rather than filling gaps with assumptions.
- Material changes create a revision with the new cutoff date, rationale, and links to prior conclusions.

## No-Invention Boundary

- Do not fabricate customers, market share, capacity, orders, revenue proportions, certification status, or any other unsupported operating fact.
- Rumors, leads, concept-stock lists, and repeated market narratives are not facts and must not be presented as evidence-backed conclusions.
- D-grade material remains a pending lead until corroborated by stronger evidence. If corroboration is unavailable, state `尚未获得可靠公开证据` and add it to `后续验证清单`.
- Uncertainty must remain visible; confidence wording cannot convert an inference into a fact.

## Quant Core Role

Existing factor, ranking, backtest, ML-boundary, and report outputs can be attached as validation inputs. They are reproducible research artifacts, not substitutes for Stage 1 facts, Stage 2 judgment, or a final personal research conclusion.
