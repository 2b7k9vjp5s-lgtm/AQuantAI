"""Strict JSON-ready contracts for Stage 2 company-research reads."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage2CompanyResearchListContract:
    as_of_cutoff: str | None
    company_research: tuple[dict[str, Any], ...]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Stage2CompanyResearchDetailContract:
    company_research: dict[str, Any]
    as_of_cutoff: str | None
    frozen_stage1_handoff: dict[str, Any]
    latest_revision: dict[str, Any]
    revision_history: tuple[dict[str, Any], ...]
    hypotheses: tuple[dict[str, Any], ...]
    conflicts: tuple[dict[str, Any], ...]
    missing_evidence: tuple[dict[str, Any], ...]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
