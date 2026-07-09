"""Dashboard data contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.safety import RESEARCH_DISCLAIMER, validate_allowed_actions, validate_research_text

DASHBOARD_DISCLAIMER = RESEARCH_DISCLAIMER


@dataclass(frozen=True)
class DashboardMetric:
    label: str
    value: str | float | int
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "value": self.value, "description": self.description}


@dataclass(frozen=True)
class DashboardTable:
    title: str
    columns: list[str]
    rows: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "columns": self.columns, "rows": self.rows}


@dataclass(frozen=True)
class DashboardCard:
    title: str
    body: str
    metrics: list[DashboardMetric] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "body": self.body,
            "metrics": [metric.to_dict() for metric in self.metrics],
        }


@dataclass(frozen=True)
class DashboardReportView:
    title: str
    summary: str
    risks: list[str]
    limitations: list[str]
    source_refs: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "risks": self.risks,
            "limitations": self.limitations,
            "source_refs": self.source_refs,
        }


@dataclass(frozen=True)
class DashboardPage:
    page_id: str
    title: str
    sections: dict[str, Any]
    disclaimer: str = DASHBOARD_DISCLAIMER
    allowed_actions: list[str] = field(default_factory=lambda: ["view", "inspect", "export_research"])
    source_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "page_id": self.page_id,
            "title": self.title,
            "sections": self.sections,
            "disclaimer": self.disclaimer,
            "allowed_actions": self.allowed_actions,
            "source_refs": self.source_refs,
            "read_only": True,
        }
        _assert_read_only(payload)
        return payload


def _assert_read_only(payload: dict[str, Any]) -> None:
    validate_allowed_actions(payload.get("allowed_actions", []))
    validate_research_text(payload)
