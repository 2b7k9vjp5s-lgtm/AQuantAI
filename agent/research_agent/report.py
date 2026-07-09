"""Deterministic research report builder."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from agent.base import AgentRunConfig, AgentRunResult, RESEARCH_DISCLAIMER, ResearchContext, ResearchReport

DISALLOWED_RECOMMENDATION_TERMS = ["buy", "sell", "hold"]


class DeterministicResearchReportBuilder:
    """Build structured research-only reports without network or LLM calls."""

    def __init__(self, config: AgentRunConfig | None = None) -> None:
        self.config = config or AgentRunConfig()
        if self.config.include_llm:
            raise ValueError("DeterministicResearchReportBuilder does not call LLM adapters")

    def run(self, context: ResearchContext) -> AgentRunResult:
        report = self.build_report(context)
        return AgentRunResult(config=self.config, report=report)

    def build_report(self, context: ResearchContext) -> ResearchReport:
        _validate_context(context)
        factor_highlights = _factor_highlights(context.factor_scores)
        backtest_highlights = _backtest_highlights(context.backtest_metrics)
        ml_highlights = _ml_highlights(context.ml_predictions)
        risks = [
            "Research outputs depend on input data quality and may change as data contracts evolve.",
            "Historical metrics and model scores do not guarantee future outcomes.",
        ]
        limitations = [
            "This deterministic report does not use live data or an LLM.",
            "The report does not perform portfolio optimization or trading actions.",
        ]
        summary = (
            f"Research summary for {context.scope}: "
            f"{len(factor_highlights)} factor notes, {len(backtest_highlights)} backtest notes, "
            f"and {len(ml_highlights)} ML notes were assembled from local inputs."
        )
        report = ResearchReport(
            report_date=context.report_date,
            title=f"AQuantAI Research Report - {context.scope}",
            scope=context.scope,
            summary=summary,
            factor_highlights=factor_highlights,
            backtest_highlights=backtest_highlights,
            ml_highlights=ml_highlights,
            risks=risks,
            limitations=limitations,
            disclaimer=RESEARCH_DISCLAIMER,
            source_refs=list(context.source_refs),
        )
        _assert_safe_language(report)
        return report


def _validate_context(context: ResearchContext) -> None:
    if not context.report_date:
        raise ValueError("report_date must not be empty")
    if not context.scope:
        raise ValueError("scope must not be empty")


def _factor_highlights(factor_scores: pd.DataFrame | None) -> list[str]:
    if factor_scores is None or factor_scores.empty:
        return ["No factor score inputs were provided."]
    required = {"score_date", "stock_code", "factor_name", "score", "rank"}
    missing = required - set(factor_scores.columns)
    if missing:
        raise ValueError(f"factor_scores is missing required columns: {sorted(missing)}")
    top = factor_scores.sort_values(["score_date", "rank"]).head(3)
    return [
        f"{row.stock_code} ranked {int(row.rank)} for {row.factor_name} with score {_format_number(row.score)}."
        for row in top.itertuples(index=False)
    ]


def _backtest_highlights(metrics: dict[str, Any]) -> list[str]:
    if not metrics:
        return ["No backtest metrics were provided."]
    highlights = []
    for key in ["total_return", "annual_return", "max_drawdown", "sharpe_ratio"]:
        if key in metrics:
            highlights.append(f"{key}: {_format_number(metrics[key])}")
    return highlights or ["Backtest metrics were provided but no standard metric keys were found."]


def _ml_highlights(predictions: pd.DataFrame | None) -> list[str]:
    if predictions is None or predictions.empty:
        return ["No ML prediction inputs were provided."]
    required = {"prediction_date", "stock_code", "model_name", "prediction_score", "prediction_rank"}
    missing = required - set(predictions.columns)
    if missing:
        raise ValueError(f"ml_predictions is missing required columns: {sorted(missing)}")
    top = predictions.sort_values(["prediction_date", "prediction_rank"]).head(3)
    return [
        f"{row.model_name} ranked {row.stock_code} at {int(row.prediction_rank)} with prediction score {_format_number(row.prediction_score)}."
        for row in top.itertuples(index=False)
    ]


def _format_number(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(numeric):
        return "not available"
    return f"{numeric:.4f}"


def _assert_safe_language(report: ResearchReport) -> None:
    text = " ".join(
        [
            report.summary,
            *report.factor_highlights,
            *report.backtest_highlights,
            *report.ml_highlights,
            *report.risks,
            *report.limitations,
        ]
    ).lower()
    forbidden_phrases = ["recommendation to buy", "recommendation to sell", "guaranteed return", "place order"]
    if any(phrase in text for phrase in forbidden_phrases):
        raise ValueError("report contains disallowed investment-advice wording")
