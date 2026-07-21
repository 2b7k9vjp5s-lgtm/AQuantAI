"""JSON-ready contracts for the read-only Company Research Workspace."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CompanyResearchSelectorContract:
    as_of_cutoff: str | None
    research: tuple[dict[str, Any], ...]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompanyResearchWorkspaceContract:
    as_of_cutoff: str | None
    identity: dict[str, Any]
    frozen_stage1: dict[str, Any]
    company_research: dict[str, Any]
    hypotheses: tuple[dict[str, Any], ...]
    expectations: tuple[dict[str, Any], ...]
    valuation_observations: tuple[dict[str, Any], ...]
    catalysts: tuple[dict[str, Any], ...]
    risks: tuple[dict[str, Any], ...]
    industry_judgments: tuple[dict[str, Any], ...]
    company_judgments: tuple[dict[str, Any], ...]
    evidence_summary: dict[str, Any]
    detail_routes: dict[str, str]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
