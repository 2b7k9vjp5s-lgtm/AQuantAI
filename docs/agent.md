# AI Research Agent

Phase 5 creates a research-only agent boundary. The goal is structured, auditable report assembly, not autonomous investment decisions.

## Agent Boundaries

The agent consumes outputs from prior phases:

- normalized data contracts;
- factor and score outputs;
- backtest metrics;
- ML predictions;
- source references.

The agent does not own factor calculations, backtest calculations, ML training, trading decisions, broker actions, or dashboard rendering.

## Report Contract

Reports include:

- `report_date`
- `title`
- `scope`
- `summary`
- `factor_highlights`
- `backtest_highlights`
- `ml_highlights`
- `risks`
- `limitations`
- `disclaimer`
- `source_refs`

## Allowed Language

Reports may describe:

- observed factor scores;
- historical backtest metrics;
- model prediction ranks as research signals;
- risks, limitations, and source references.

## Disallowed Language

Reports must not include:

- buy, sell, or hold recommendation generation;
- guaranteed return language;
- automatic trade instructions;
- claims of predictive certainty;
- broker or order-placement actions.

## Required Disclaimer

All reports include:

```text
This report is for quantitative research and learning only. It is not investment advice, not a trading recommendation, and not an instruction to buy, sell, or hold any security.
```

## LLM Adapter Boundary

`agent/research_agent/llm_adapter.py` defines a lazy, mockable adapter for future LLM use. Deterministic report generation does not require OpenAI, LangGraph, network calls, or any LLM client.

## Phase 5 Limitations

Phase 5 does not implement dashboard UI, broker APIs, order placement, automatic trading, live data fetching inside tests, autonomous investment decisions, buy/sell/hold recommendation generation, guaranteed performance claims, or required OpenAI/LangGraph dependencies.
