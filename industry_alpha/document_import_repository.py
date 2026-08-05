"""Bounded exact-ID persistence reads for local document history."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

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


class DocumentImportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def import_attempt(self, attempt_id: UUID) -> LocalDocumentImportAttempt | None:
        return self.session.get(LocalDocumentImportAttempt, attempt_id)

    def content_metadata(self, content_id: UUID) -> LocalDocumentContent | None:
        return self.session.scalar(
            select(LocalDocumentContent).where(LocalDocumentContent.id == content_id)
        )

    def content_bytes(self, content_id: UUID) -> bytes | None:
        return self.session.scalar(
            select(LocalDocumentContent.raw_pdf_bytes).where(
                LocalDocumentContent.id == content_id
            )
        )

    def pages(
        self, content_id: UUID, *, after_page: int = 0, limit: int = 30
    ) -> list[LocalDocumentPage]:
        return list(
            self.session.scalars(
                select(LocalDocumentPage)
                .where(
                    LocalDocumentPage.content_id == content_id,
                    LocalDocumentPage.page_number > after_page,
                )
                .order_by(LocalDocumentPage.page_number)
                .limit(min(max(limit, 1), 30))
            )
        )

    def review_session(self, review_id: UUID) -> LocalDocumentReviewSession | None:
        return self.session.get(LocalDocumentReviewSession, review_id)

    def candidates(
        self,
        review_id: UUID,
        *,
        after_candidate_id: UUID | None = None,
        limit: int = 51,
        review_revision_id: UUID | None = None,
    ) -> list[LocalDocumentCandidate]:
        query = select(LocalDocumentCandidate)
        if review_revision_id is not None:
            query = query.join(
                LocalDocumentReviewCandidateDecision,
                LocalDocumentReviewCandidateDecision.candidate_id
                == LocalDocumentCandidate.id,
            ).where(
                LocalDocumentReviewCandidateDecision.review_revision_id
                == review_revision_id
            )
        query = query.where(
            LocalDocumentCandidate.review_session_id == review_id
        )
        if after_candidate_id is not None:
            query = query.where(LocalDocumentCandidate.id > after_candidate_id)
        return list(
            self.session.scalars(
                query.order_by(LocalDocumentCandidate.id).limit(limit)
            )
        )

    def revisions(
        self, review_id: UUID, *, revision_id: UUID | None = None
    ) -> list[LocalDocumentReviewRevision]:
        query = select(LocalDocumentReviewRevision).where(
            LocalDocumentReviewRevision.review_session_id == review_id
        )
        if revision_id is not None:
            query = query.where(LocalDocumentReviewRevision.id == revision_id)
        return list(
            self.session.scalars(
                query.order_by(LocalDocumentReviewRevision.revision_number)
            )
        )

    def decisions(
        self, revision_id: UUID
    ) -> list[LocalDocumentReviewCandidateDecision]:
        return list(
            self.session.scalars(
                select(LocalDocumentReviewCandidateDecision)
                .where(
                    LocalDocumentReviewCandidateDecision.review_revision_id
                    == revision_id
                )
                .order_by(LocalDocumentReviewCandidateDecision.candidate_id)
            )
        )

    def revision_decisions(
        self,
        revision_ids: tuple[UUID, ...],
        candidate_ids: tuple[UUID, ...],
    ) -> list[LocalDocumentReviewCandidateDecision]:
        if not revision_ids or not candidate_ids:
            return []
        return list(
            self.session.scalars(
                select(LocalDocumentReviewCandidateDecision)
                .where(
                    LocalDocumentReviewCandidateDecision.review_revision_id.in_(
                        revision_ids
                    ),
                    LocalDocumentReviewCandidateDecision.candidate_id.in_(
                        candidate_ids
                    ),
                )
                .order_by(
                    LocalDocumentReviewCandidateDecision.review_revision_id,
                    LocalDocumentReviewCandidateDecision.candidate_id,
                )
            )
        )

    def receipt(self, receipt_id: UUID) -> LocalDocumentAcceptanceReceipt | None:
        return self.session.get(LocalDocumentAcceptanceReceipt, receipt_id)

    def receipt_links(self, receipt_id: UUID) -> list[LocalDocumentAcceptanceLink]:
        return list(
            self.session.scalars(
                select(LocalDocumentAcceptanceLink)
                .where(LocalDocumentAcceptanceLink.receipt_id == receipt_id)
                .order_by(LocalDocumentAcceptanceLink.candidate_id)
            )
        )
