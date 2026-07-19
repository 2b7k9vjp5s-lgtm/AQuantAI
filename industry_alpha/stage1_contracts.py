"""Strict JSON-ready contracts for Stage 1 beneficiary reads."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage1BeneficiaryListContract:
    map_id: str
    as_of_cutoff: str | None
    beneficiaries: tuple[dict[str, Any], ...]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Stage1BeneficiaryDetailContract:
    beneficiary: dict[str, Any]
    as_of_cutoff: str | None
    latest_revision: dict[str, Any]
    revision_history: tuple[dict[str, Any], ...]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Stage1CandidatePoolListContract:
    map_id: str
    as_of_cutoff: str | None
    candidate_pools: tuple[dict[str, Any], ...]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Stage1CandidatePoolDetailContract:
    candidate_pool: dict[str, Any]
    as_of_cutoff: str | None
    latest_revision: dict[str, Any]
    revision_history: tuple[dict[str, Any], ...]
    frozen_candidates: tuple[dict[str, Any], ...]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
