"""Cross-row invariants for offline Industry Thesis Orchestration v1."""

from __future__ import annotations

from datetime import timezone

from sqlalchemy import event, select

import backend.database.canonical_price_models  # noqa: F401 - register listed instruments
import industry_alpha.chain_map_models  # noqa: F401 - register Industry Map targets
import industry_alpha.stage1_models  # noqa: F401 - register candidate-pool targets
from industry_alpha.errors import EvidenceLedgerImmutableError
from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateIdentity,
    IndustryThesisCandidateRevision,
    IndustryThesisSessionRevision,
)


def _utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@event.listens_for(IndustryThesisSessionRevision, "before_insert")
def validate_industry_thesis_session_revision_chain(
    _mapper: object,
    connection: object,
    target: IndustryThesisSessionRevision,
) -> None:
    """Session revisions form one exact, chronological, gap-free chain."""

    if target.supersedes_revision_id is None:
        if target.revision_number != 1:
            raise EvidenceLedgerImmutableError(
                "The first thesis-session revision must use revision number 1."
            )
        return
    prior = connection.execute(
        select(
            IndustryThesisSessionRevision.session_id,
            IndustryThesisSessionRevision.revision_number,
            IndustryThesisSessionRevision.information_cutoff_date,
            IndustryThesisSessionRevision.recorded_at_utc,
        ).where(
            IndustryThesisSessionRevision.id == target.supersedes_revision_id
        )
    ).one_or_none()
    if prior is None:
        raise EvidenceLedgerImmutableError(
            "A superseding thesis-session revision requires one exact prior revision."
        )
    if prior.session_id != target.session_id:
        raise EvidenceLedgerImmutableError(
            "A thesis-session revision may supersede only the same session identity."
        )
    if target.revision_number != prior.revision_number + 1:
        raise EvidenceLedgerImmutableError(
            "Thesis-session revision numbers must be consecutive."
        )
    if target.information_cutoff_date < prior.information_cutoff_date:
        raise EvidenceLedgerImmutableError(
            "Thesis-session information cutoff cannot move backward."
        )
    if _utc(target.recorded_at_utc) <= _utc(prior.recorded_at_utc):
        raise EvidenceLedgerImmutableError(
            "Thesis-session recorded UTC must move forward."
        )


@event.listens_for(IndustryThesisCandidateRevision, "before_insert")
def validate_industry_thesis_candidate_revision_chain(
    _mapper: object,
    connection: object,
    target: IndustryThesisCandidateRevision,
) -> None:
    """Candidate revisions remain exact children of one session and candidate identity."""

    session_row = connection.execute(
        select(
            IndustryThesisSessionRevision.session_id,
            IndustryThesisSessionRevision.information_cutoff_date,
            IndustryThesisSessionRevision.recorded_at_utc,
        ).where(IndustryThesisSessionRevision.id == target.session_revision_id)
    ).one_or_none()
    if session_row is None:
        raise EvidenceLedgerImmutableError(
            "Candidate revision requires one exact persisted thesis-session revision."
        )
    candidate_session_id = connection.execute(
        select(IndustryThesisCandidateIdentity.session_id).where(
            IndustryThesisCandidateIdentity.id == target.candidate_id
        )
    ).scalar_one_or_none()
    if candidate_session_id is None:
        raise EvidenceLedgerImmutableError(
            "Candidate revision requires one exact persisted candidate identity."
        )
    if candidate_session_id != session_row.session_id:
        raise EvidenceLedgerImmutableError(
            "Candidate and thesis-session revisions must belong to the same session."
        )
    if target.information_cutoff_date != session_row.information_cutoff_date:
        raise EvidenceLedgerImmutableError(
            "Candidate revision cutoff must equal its exact thesis-session revision cutoff."
        )
    if _utc(target.recorded_at_utc) <= _utc(session_row.recorded_at_utc):
        raise EvidenceLedgerImmutableError(
            "Candidate revision recorded UTC must be later than its thesis-session revision."
        )

    if target.supersedes_revision_id is None:
        if target.revision_number != 1:
            raise EvidenceLedgerImmutableError(
                "The first candidate revision must use revision number 1."
            )
        return
    prior = connection.execute(
        select(
            IndustryThesisCandidateRevision.candidate_id,
            IndustryThesisCandidateRevision.revision_number,
            IndustryThesisCandidateRevision.information_cutoff_date,
            IndustryThesisCandidateRevision.recorded_at_utc,
        ).where(
            IndustryThesisCandidateRevision.id == target.supersedes_revision_id
        )
    ).one_or_none()
    if prior is None:
        raise EvidenceLedgerImmutableError(
            "A superseding candidate revision requires one exact prior revision."
        )
    if prior.candidate_id != target.candidate_id:
        raise EvidenceLedgerImmutableError(
            "A candidate revision may supersede only the same candidate identity."
        )
    if target.revision_number != prior.revision_number + 1:
        raise EvidenceLedgerImmutableError(
            "Candidate revision numbers must be consecutive."
        )
    if target.information_cutoff_date < prior.information_cutoff_date:
        raise EvidenceLedgerImmutableError(
            "Candidate information cutoff cannot move backward."
        )
    if _utc(target.recorded_at_utc) <= _utc(prior.recorded_at_utc):
        raise EvidenceLedgerImmutableError(
            "Candidate recorded UTC must move forward."
        )
