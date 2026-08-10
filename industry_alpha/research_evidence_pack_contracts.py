"""Closed contracts for the bounded Research Evidence Pack v1 read projection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID


CONTRACT_VERSION = "aquantai.research-evidence-pack.v1"
CURSOR_CONTRACT_VERSION = "aquantai.research-evidence-pack.cursor.v1"

MEMBERSHIP_LINKED = "linked_to_selected_case_revision"
MEMBERSHIP_UNLINKED = "accepted_unlinked_to_selected_case_revision"
MEMBERSHIP_STATES = frozenset({MEMBERSHIP_LINKED, MEMBERSHIP_UNLINKED})
MEMBERSHIP_SUMMARIES = frozenset(
    {
        "no_claim_bindings",
        "all_bindings_linked",
        "all_bindings_unlinked",
        "mixed_linked_and_unlinked_bindings",
    }
)


class ResearchEvidencePackError(RuntimeError):
    """Fail closed with one stable public error code."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True)
class EvidencePackRequest:
    research_case_id: UUID
    research_case_revision_id: UUID
    information_cutoff_date: date
    recorded_at_utc: datetime
    limit: int = 50
    cursor: str | None = None


@dataclass(frozen=True)
class EvidencePackCursor:
    research_case_id: UUID
    research_case_revision_id: UUID
    information_cutoff_date: date
    recorded_at_utc: datetime
    limit: int
    last_information_date: date
    last_recorded_at_utc: datetime
    last_evidence_id: UUID


@dataclass(frozen=True)
class ResearchEvidencePackResult:
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return self.payload
