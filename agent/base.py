"""AI research-agent contracts for AQuantAI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

RESEARCH_DISCLAIMER = (
    "This report is for quantitative research and learning only. It is not investment advice, "
    "not a trading recommendation, and not an instruction to buy, sell, or hold any security."
)

REPORT_FIELDS = [
    "report_date",
    "title",
    "scope",
    "summary",
    "factor_highlights",
    "backtest_highlights",
    "ml_highlights",
    "risks",
    "limitations",
    "disclaimer",
    "source_refs",
]


@dataclass(frozen=True)
class ResearchContext:
    """Inputs available to a deterministic research report builder."""

    report_date: str
    scope: str
    factor_scores: pd.DataFrame | None = None
    backtest_metrics: dict[str, Any] = field(default_factory=dict)
    ml_predictions: pd.DataFrame | None = None
    source_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReportSection:
    """One structured report section."""

    title: str
    content: list[str]


@dataclass(frozen=True)
class ResearchReport:
    """Structured research-only report output."""

    report_date: str
    title: str
    scope: str
    summary: str
    factor_highlights: list[str]
    backtest_highlights: list[str]
    ml_highlights: list[str]
    risks: list[str]
    limitations: list[str]
    disclaimer: str
    source_refs: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {field_name: getattr(self, field_name) for field_name in REPORT_FIELDS}


@dataclass(frozen=True)
class AgentRunConfig:
    """Research-agent runtime settings."""

    agent_name: str = "deterministic_research_agent"
    include_llm: bool = False


@dataclass(frozen=True)
class AgentRunResult:
    """Result of one research-agent run."""

    config: AgentRunConfig
    report: ResearchReport
