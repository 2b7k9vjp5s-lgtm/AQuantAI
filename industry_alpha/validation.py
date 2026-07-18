"""Reviewed value sets and command-boundary validation."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Iterable

from industry_alpha.errors import EvidenceLedgerValidationError

ORIGINS = frozenset({"manual", "fixture"})
WORKFLOW_STATES = frozenset({"open", "paused", "completed", "archived"})
CONCLUSION_STATUSES = frozenset(
    {"unassessed", "insufficient_evidence", "supported", "disputed", "rejected"}
)
EVIDENCE_GRADES = frozenset({"A", "B", "C", "D"})
SOURCE_KINDS = frozenset(
    {"official", "regulatory", "filing", "statistics", "company", "research", "media", "industry", "community", "other"}
)
CLAIM_KINDS = frozenset({"fact", "inference"})
CLAIM_STATUSES = frozenset({"draft", "supported", "disputed", "rejected"})
INFERENCE_CONFIDENCES = frozenset({"low", "medium", "high"})
EVIDENCE_RELATIONS = frozenset({"supports", "contradicts", "context"})
CLAIM_ROLES = frozenset({"conclusion", "context", "risk"})
VERIFICATION_STATUSES = frozenset({"open", "completed", "deferred"})

MAX_LENGTHS = {
    "case_key": 96,
    "claim_key": 96,
    "title": 300,
    "research_question": 2000,
    "summary": 4000,
    "source_title": 500,
    "publisher_or_author": 300,
    "source_locator": 1500,
    "content_fingerprint": 128,
    "statement": 4000,
    "inference_basis": 4000,
    "link_note": 1000,
    "description": 2000,
}


def required_text(value: str, field: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise EvidenceLedgerValidationError(f"{field} must not be blank.")
    maximum = MAX_LENGTHS[field]
    if len(normalized) > maximum:
        raise EvidenceLedgerValidationError(f"{field} must not exceed {maximum} characters.")
    return normalized


def optional_text(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    maximum = MAX_LENGTHS[field]
    if len(normalized) > maximum:
        raise EvidenceLedgerValidationError(f"{field} must not exceed {maximum} characters.")
    return normalized


def reviewed_value(value: str, field: str, allowed: Iterable[str]) -> str:
    normalized = str(value).strip()
    if normalized not in allowed:
        choices = ", ".join(sorted(allowed))
        raise EvidenceLedgerValidationError(f"{field} must be one of: {choices}.")
    return normalized


def utc_timestamp(value: datetime | None) -> datetime:
    timestamp = value or datetime.now(timezone.utc)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise EvidenceLedgerValidationError("recorded timestamps must be timezone-aware UTC values.")
    return timestamp.astimezone(timezone.utc)


def validate_recorded_cutoff(information_date: date, recorded_at_utc: datetime) -> None:
    if information_date > recorded_at_utc.date():
        raise EvidenceLedgerValidationError(
            "information date/cutoff must not be after the UTC recording date."
        )


def validate_claim_fields(
    claim_kind: str,
    confidence: str | None,
    basis: str | None,
) -> tuple[str | None, str | None]:
    if claim_kind == "fact":
        if confidence is not None or basis is not None:
            raise EvidenceLedgerValidationError(
                "fact claims cannot carry inference_confidence or inference_basis."
            )
        return None, None
    if confidence is None:
        raise EvidenceLedgerValidationError("inference claims require inference_confidence.")
    normalized_confidence = reviewed_value(
        confidence, "inference_confidence", INFERENCE_CONFIDENCES
    )
    normalized_basis = required_text(basis or "", "inference_basis")
    return normalized_confidence, normalized_basis
