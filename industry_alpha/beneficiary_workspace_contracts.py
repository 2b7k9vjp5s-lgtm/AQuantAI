"""JSON-ready contracts for the read-only Industry Beneficiary Workspace."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class IndustryResearchMapListContract:
    as_of_cutoff: str | None
    maps: tuple[dict[str, Any], ...]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IndustryBeneficiaryWorkspaceContract:
    as_of_cutoff: str | None
    industry_map: dict[str, Any]
    latest_revision: dict[str, Any]
    frozen_snapshot: dict[str, Any]
    map_evidence_summary: dict[str, Any]
    beneficiaries: tuple[dict[str, Any], ...]
    detail_routes: dict[str, str]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
