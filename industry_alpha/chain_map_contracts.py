"""JSON-safe contracts for read-only industry chain maps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IndustryMapListContract:
    as_of_cutoff: str | None
    maps: tuple[dict[str, Any], ...]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of_cutoff": self.as_of_cutoff,
            "maps": list(self.maps),
            "map_count": len(self.maps),
            "notices": self.notices,
        }


@dataclass(frozen=True)
class IndustryMapDetailContract:
    industry_map: dict[str, Any]
    as_of_cutoff: str | None
    latest_revision: dict[str, Any]
    revision_history: tuple[dict[str, Any], ...]
    frozen_snapshot: dict[str, Any]
    evidence_grade_summary: dict[str, int]
    conflicts: tuple[dict[str, Any], ...]
    missing_evidence: tuple[dict[str, Any], ...]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "industry_map": self.industry_map,
            "as_of_cutoff": self.as_of_cutoff,
            "latest_revision": self.latest_revision,
            "revision_history": list(self.revision_history),
            "frozen_snapshot": self.frozen_snapshot,
            "evidence_grade_summary": self.evidence_grade_summary,
            "conflicts": list(self.conflicts),
            "missing_evidence": list(self.missing_evidence),
            "notices": self.notices,
        }
