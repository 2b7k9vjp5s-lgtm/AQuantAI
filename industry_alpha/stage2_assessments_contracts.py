"""Strict JSON-ready contracts for v0.6C assessment reads."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage2AssessmentListContract:
    as_of_cutoff: str | None
    assessments: tuple[dict[str, Any], ...]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Stage2AssessmentDetailContract:
    assessment: dict[str, Any]
    as_of_cutoff: str | None
    latest_revision: dict[str, Any]
    revision_history: tuple[dict[str, Any], ...]
    conflicts: tuple[dict[str, Any], ...]
    missing_evidence: tuple[dict[str, Any], ...]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
