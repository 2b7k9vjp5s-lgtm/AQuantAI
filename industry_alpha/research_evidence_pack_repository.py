"""Bounded set-wise SQL reads for Research Evidence Pack v1."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import and_, case as sql_case, func, literal, or_, select, union_all
from sqlalchemy.orm import Session, aliased

from industry_alpha.document_import_models import (
    LocalDocumentAcceptanceLink,
    LocalDocumentAcceptanceReceipt,
    LocalDocumentCandidate,
    LocalDocumentContent,
    LocalDocumentImportAttempt,
    LocalDocumentPage,
    LocalDocumentReviewCandidateDecision,
    LocalDocumentReviewRevision,
    LocalDocumentReviewSession,
)
from industry_alpha.models import (
    CaseRevisionClaimLink,
    Claim,
    ClaimEvidenceLink,
    ClaimRevision,
    EvidenceItem,
    ResearchCase,
    ResearchCaseRevision,
)
from industry_alpha.research_evidence_pack_contracts import EvidencePackCursor


class ResearchEvidencePackRepository:
    """Read-only repository whose public methods map to the frozen eight statements."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # Statement 1.
    def load_anchor(
        self, case_id: UUID, revision_id: UUID
    ) -> tuple[ResearchCase, ResearchCaseRevision | None] | None:
        revision = aliased(ResearchCaseRevision)
        return self._session.execute(
            select(ResearchCase, revision)
            .outerjoin(revision, revision.id == revision_id)
            .where(ResearchCase.id == case_id)
        ).one_or_none()

    @staticmethod
    def _keyset_after(cursor: EvidencePackCursor):
        return or_(
            EvidenceItem.information_date < cursor.last_information_date,
            and_(
                EvidenceItem.information_date == cursor.last_information_date,
                EvidenceItem.recorded_at_utc < cursor.last_recorded_at_utc,
            ),
            and_(
                EvidenceItem.information_date == cursor.last_information_date,
                EvidenceItem.recorded_at_utc == cursor.last_recorded_at_utc,
                EvidenceItem.id > cursor.last_evidence_id,
            ),
        )

    @staticmethod
    def _visible_evidence(case_id: UUID, information_cutoff_date: date, recorded_at_utc: datetime):
        return and_(
            EvidenceItem.case_id == case_id,
            EvidenceItem.information_date <= information_cutoff_date,
            EvidenceItem.recorded_at_utc <= recorded_at_utc,
        )

    # Statement 2.
    def evidence_counts(
        self,
        *,
        case_id: UUID,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
        cursor: EvidencePackCursor | None,
    ) -> tuple[int, int]:
        visible = self._visible_evidence(case_id, information_cutoff_date, recorded_at_utc)
        remaining_expr = literal(True) if cursor is None else self._keyset_after(cursor)
        total, remaining = self._session.execute(
            select(
                func.count(EvidenceItem.id),
                func.coalesce(
                    func.sum(sql_case((remaining_expr, 1), else_=0)),
                    0,
                ),
            ).where(visible)
        ).one()
        return int(total or 0), int(remaining or 0)

    # Statement 3.
    def evidence_page(
        self,
        *,
        case_id: UUID,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
        limit: int,
        cursor: EvidencePackCursor | None,
    ) -> tuple[EvidenceItem, ...]:
        conditions = [
            self._visible_evidence(case_id, information_cutoff_date, recorded_at_utc)
        ]
        if cursor is not None:
            conditions.append(self._keyset_after(cursor))
        return tuple(
            self._session.scalars(
                select(EvidenceItem)
                .where(*conditions)
                .order_by(
                    EvidenceItem.information_date.desc(),
                    EvidenceItem.recorded_at_utc.desc(),
                    EvidenceItem.id.asc(),
                )
                .limit(limit)
            )
        )

    # Statement 4.
    def claim_bindings(
        self,
        evidence_ids: tuple[UUID, ...],
        *,
        recorded_at_utc: datetime,
    ) -> tuple[tuple[ClaimEvidenceLink, ClaimRevision, Claim], ...]:
        if not evidence_ids:
            return ()
        return tuple(
            self._session.execute(
                select(ClaimEvidenceLink, ClaimRevision, Claim)
                .join(ClaimRevision, ClaimRevision.id == ClaimEvidenceLink.claim_revision_id)
                .join(Claim, Claim.id == ClaimRevision.claim_id)
                .where(
                    ClaimEvidenceLink.evidence_id.in_(evidence_ids),
                    ClaimEvidenceLink.recorded_at_utc <= recorded_at_utc,
                )
            ).all()
        )

    # Statement 5.
    def selected_roles(
        self,
        *,
        case_revision_id: UUID,
        claim_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime,
    ) -> tuple[CaseRevisionClaimLink, ...]:
        if not claim_revision_ids:
            return ()
        return tuple(
            self._session.scalars(
                select(CaseRevisionClaimLink).where(
                    CaseRevisionClaimLink.case_revision_id == case_revision_id,
                    CaseRevisionClaimLink.claim_revision_id.in_(claim_revision_ids),
                    CaseRevisionClaimLink.recorded_at_utc <= recorded_at_utc,
                )
            )
        )

    # Statement 6.
    def receipt_graph(self, evidence_ids: tuple[UUID, ...]) -> tuple[object, ...]:
        if not evidence_ids:
            return ()

        receipt = LocalDocumentAcceptanceReceipt
        review = LocalDocumentReviewSession
        attempt = LocalDocumentImportAttempt
        content = LocalDocumentContent
        candidate = LocalDocumentCandidate
        sibling_link = LocalDocumentAcceptanceLink
        ledger_evidence = EvidenceItem
        ledger_claim = Claim
        ledger_revision = ClaimRevision
        ledger_relation = ClaimEvidenceLink

        source = aliased(LocalDocumentReviewRevision, name="source_review")
        accepted = aliased(LocalDocumentReviewRevision, name="accepted_review")
        predecessor = aliased(LocalDocumentReviewRevision, name="source_predecessor")
        source_decision = aliased(
            LocalDocumentReviewCandidateDecision, name="source_decision"
        )
        accepted_decision = aliased(
            LocalDocumentReviewCandidateDecision, name="accepted_decision"
        )

        discovered = (
            select(LocalDocumentAcceptanceLink.receipt_id.label("receipt_id"))
            .where(LocalDocumentAcceptanceLink.evidence_item_id.in_(evidence_ids))
            .distinct()
            .cte("discovered_receipts")
        )
        discovered_sessions = (
            select(
                receipt.id.label("receipt_id"),
                receipt.review_session_id.label("review_session_id"),
            )
            .join(discovered, discovered.c.receipt_id == receipt.id)
            .cte("discovered_receipt_sessions")
        )
        max_review = (
            select(
                LocalDocumentReviewRevision.review_session_id.label("review_session_id"),
                func.max(LocalDocumentReviewRevision.revision_number).label("max_revision_number"),
            )
            .join(
                discovered_sessions,
                discovered_sessions.c.review_session_id
                == LocalDocumentReviewRevision.review_session_id,
            )
            .group_by(LocalDocumentReviewRevision.review_session_id)
            .subquery("bounded_max_review_revision")
        )
        link_counts = (
            select(
                LocalDocumentAcceptanceLink.receipt_id.label("receipt_id"),
                func.count(LocalDocumentAcceptanceLink.id).label("link_count"),
            )
            .join(
                discovered,
                discovered.c.receipt_id == LocalDocumentAcceptanceLink.receipt_id,
            )
            .group_by(LocalDocumentAcceptanceLink.receipt_id)
            .subquery("bounded_receipt_link_counts")
        )

        statement = (
            select(
                discovered.c.receipt_id,
                receipt,
                review,
                attempt,
                content,
                source,
                accepted,
                predecessor,
                candidate,
                source_decision,
                accepted_decision,
                sibling_link,
                ledger_evidence,
                ledger_claim,
                ledger_revision,
                ledger_relation,
                max_review.c.max_revision_number,
                link_counts.c.link_count,
            )
            .select_from(discovered)
            .outerjoin(receipt, receipt.id == discovered.c.receipt_id)
            .outerjoin(review, review.id == receipt.review_session_id)
            .outerjoin(attempt, attempt.id == review.import_attempt_id)
            .outerjoin(content, content.id == attempt.content_id)
            .outerjoin(source, source.id == receipt.source_review_revision_id)
            .outerjoin(accepted, accepted.id == receipt.accepted_review_revision_id)
            .outerjoin(
                predecessor,
                predecessor.id == source.supersedes_review_revision_id,
            )
            .outerjoin(
                candidate,
                candidate.review_session_id == review.id,
            )
            .outerjoin(
                source_decision,
                and_(
                    source_decision.review_revision_id == source.id,
                    source_decision.candidate_id == candidate.id,
                ),
            )
            .outerjoin(
                accepted_decision,
                and_(
                    accepted_decision.review_revision_id == accepted.id,
                    accepted_decision.candidate_id == candidate.id,
                ),
            )
            .outerjoin(
                sibling_link,
                and_(
                    sibling_link.receipt_id == receipt.id,
                    sibling_link.candidate_id == candidate.id,
                ),
            )
            .outerjoin(ledger_evidence, ledger_evidence.id == sibling_link.evidence_item_id)
            .outerjoin(ledger_claim, ledger_claim.id == sibling_link.claim_id)
            .outerjoin(ledger_revision, ledger_revision.id == sibling_link.claim_revision_id)
            .outerjoin(ledger_relation, ledger_relation.id == sibling_link.claim_evidence_link_id)
            .outerjoin(max_review, max_review.c.review_session_id == review.id)
            .outerjoin(link_counts, link_counts.c.receipt_id == receipt.id)
            .order_by(discovered.c.receipt_id, candidate.id)
        )
        return tuple(self._session.execute(statement).all())

    # Statement 7.
    def citation_pages(
        self, page_keys: tuple[tuple[UUID, int], ...]
    ) -> tuple[LocalDocumentPage, ...]:
        if not page_keys:
            return ()
        clauses = [
            and_(
                LocalDocumentPage.content_id == content_id,
                LocalDocumentPage.page_number == page_number,
            )
            for content_id, page_number in page_keys
        ]
        return tuple(
            self._session.scalars(select(LocalDocumentPage).where(or_(*clauses)))
        )

    # Statement 8.
    def supersession_targets(
        self,
        *,
        evidence_target_ids: tuple[UUID, ...],
        claim_revision_target_ids: tuple[UUID, ...],
    ) -> tuple[object, ...]:
        if not evidence_target_ids and not claim_revision_target_ids:
            return ()
        evidence_select = select(
            literal("evidence").label("kind"),
            EvidenceItem.id.label("id"),
            EvidenceItem.case_id.label("owner_id"),
            literal(None).label("revision_no"),
            EvidenceItem.information_date.label("information_date"),
            EvidenceItem.recorded_at_utc.label("recorded_at_utc"),
        ).where(EvidenceItem.id.in_(evidence_target_ids or (UUID(int=0),)))
        claim_select = select(
            literal("claim_revision").label("kind"),
            ClaimRevision.id.label("id"),
            ClaimRevision.claim_id.label("owner_id"),
            ClaimRevision.revision_no.label("revision_no"),
            ClaimRevision.information_cutoff_date.label("information_date"),
            ClaimRevision.recorded_at_utc.label("recorded_at_utc"),
        ).where(ClaimRevision.id.in_(claim_revision_target_ids or (UUID(int=0),)))
        return tuple(self._session.execute(union_all(evidence_select, claim_select)).all())
