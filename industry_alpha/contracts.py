"""Typed, JSON-safe read contracts for the evidence ledger."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CaseListContract:
    as_of_cutoff: str | None
    cases: tuple[dict[str, Any], ...]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of_cutoff": self.as_of_cutoff,
            "cases": list(self.cases),
            "case_count": len(self.cases),
            "notices": self.notices,
        }


@dataclass(frozen=True)
class CaseLedgerContract:
    case: dict[str, Any]
    as_of_cutoff: str | None
    latest_revision: dict[str, Any]
    case_revision_history: tuple[dict[str, Any], ...]
    claims: tuple[dict[str, Any], ...]
    evidence_items: tuple[dict[str, Any], ...]
    claim_evidence_links: tuple[dict[str, Any], ...]
    conflicts: tuple[dict[str, Any], ...]
    case_revision_claim_links: tuple[dict[str, Any], ...]
    verification_items: tuple[dict[str, Any], ...]
    label_metadata: dict[str, Any]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case": self.case,
            "as_of_cutoff": self.as_of_cutoff,
            "latest_revision": self.latest_revision,
            "case_revision_history": list(self.case_revision_history),
            "claims": list(self.claims),
            "evidence_items": list(self.evidence_items),
            "claim_evidence_links": list(self.claim_evidence_links),
            "conflicts": list(self.conflicts),
            "case_revision_claim_links": list(self.case_revision_claim_links),
            "verification_items": list(self.verification_items),
            "label_metadata": self.label_metadata,
            "notices": self.notices,
        }
