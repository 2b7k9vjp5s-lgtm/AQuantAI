"""Cross-row invariants for offline Industry Thesis Orchestration v1."""

from __future__ import annotations

from datetime import timezone

from sqlalchemy import event, select

from industry_alpha.errors import EvidenceLedgerImmutableError
from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateRevision,
    IndustryThesisSessionRevision,
)


def _utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@event.listens_for(IndustryThesisCandidateRevision, "before_insert")
def validate_industry_thesis_candidate_chronology(
    _mapper: object,
    connection: object,
    target: IndustryThesisCandidateRevision,
) -> None:
    """Candidate proposals must be later, same-cutoff children of one exact thesis revision."""

    row = connection.execute(
        select(
            IndustryThesisSessionRevision.information_cutoff_date,
            IndustryThesisSessionRevision.recorded_at_utc,
        ).where(IndustryThesisSessionRevision.id == target.session_revision_id)
    ).one_or_none()
    if row is None:
        raise EvidenceLedgerImmutableError(
            "Candidate revision requires one exact persisted thesis-session revision."
        )
    if target.information_cutoff_date != row.information_cutoff_date:
        raise EvidenceLedgerImmutableError(
            "Candidate revision cutoff must equal its exact thesis-session revision cutoff."
        )
    if _utc(target.recorded_at_utc) <= _utc(row.recorded_at_utc):
        raise EvidenceLedgerImmutableError(
            "Candidate revision recorded UTC must be later than its thesis-session revision."
        )
