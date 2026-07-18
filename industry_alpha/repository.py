"""SQLAlchemy read adapter for complete evidence-ledger rows."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from industry_alpha.models import (
    CaseRevisionClaimLink,
    Claim,
    ClaimEvidenceLink,
    ClaimRevision,
    EvidenceItem,
    ResearchCase,
    ResearchCaseRevision,
    VerificationItem,
)


@dataclass(frozen=True)
class CaseLedgerRows:
    case: ResearchCase
    case_revisions: tuple[ResearchCaseRevision, ...]
    claims: tuple[Claim, ...]
    claim_revisions: tuple[ClaimRevision, ...]
    evidence_items: tuple[EvidenceItem, ...]
    claim_evidence_links: tuple[ClaimEvidenceLink, ...]
    case_claim_links: tuple[CaseRevisionClaimLink, ...]
    verification_items: tuple[VerificationItem, ...]


class EvidenceLedgerRepository:
    """Read immutable rows without exposing any mutation method."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_cases(self) -> tuple[ResearchCase, ...]:
        return tuple(
            self._session.scalars(
                select(ResearchCase).order_by(ResearchCase.case_key, ResearchCase.id)
            )
        )

    def load_case(self, case_id: UUID) -> CaseLedgerRows | None:
        case = self._session.get(ResearchCase, case_id)
        if case is None:
            return None
        case_revisions = tuple(
            self._session.scalars(
                select(ResearchCaseRevision)
                .where(ResearchCaseRevision.case_id == case_id)
                .order_by(ResearchCaseRevision.revision_no)
            )
        )
        claims = tuple(
            self._session.scalars(
                select(Claim)
                .where(Claim.case_id == case_id)
                .order_by(Claim.claim_key, Claim.id)
            )
        )
        claim_ids = [claim.id for claim in claims]
        claim_revisions = tuple(
            self._session.scalars(
                select(ClaimRevision)
                .where(ClaimRevision.claim_id.in_(claim_ids))
                .order_by(ClaimRevision.claim_id, ClaimRevision.revision_no)
            )
        ) if claim_ids else ()
        evidence_items = tuple(
            self._session.scalars(
                select(EvidenceItem)
                .where(EvidenceItem.case_id == case_id)
                .order_by(
                    EvidenceItem.information_date,
                    EvidenceItem.recorded_at_utc,
                    EvidenceItem.id,
                )
            )
        )
        claim_revision_ids = [revision.id for revision in claim_revisions]
        case_revision_ids = [revision.id for revision in case_revisions]
        claim_evidence_links = tuple(
            self._session.scalars(
                select(ClaimEvidenceLink).where(
                    ClaimEvidenceLink.claim_revision_id.in_(claim_revision_ids)
                )
            )
        ) if claim_revision_ids else ()
        case_claim_links = tuple(
            self._session.scalars(
                select(CaseRevisionClaimLink).where(
                    CaseRevisionClaimLink.case_revision_id.in_(case_revision_ids)
                )
            )
        ) if case_revision_ids else ()
        verification_items = tuple(
            self._session.scalars(
                select(VerificationItem)
                .where(VerificationItem.case_revision_id.in_(case_revision_ids))
                .order_by(VerificationItem.case_revision_id, VerificationItem.item_no)
            )
        ) if case_revision_ids else ()
        return CaseLedgerRows(
            case=case,
            case_revisions=case_revisions,
            claims=claims,
            claim_revisions=claim_revisions,
            evidence_items=evidence_items,
            claim_evidence_links=claim_evidence_links,
            case_claim_links=case_claim_links,
            verification_items=verification_items,
        )
