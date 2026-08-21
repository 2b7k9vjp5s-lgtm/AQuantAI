"""Transactional V1 research workspace over accepted ledger evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from threading import Lock, RLock
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

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
from industry_alpha.models import EvidenceItem, ResearchCase, ResearchCaseRevision
from industry_alpha.product_workspace_models import (
    ProductResearchCaseProfile,
    ProductResearchRevisionContent,
    ProductResearchRevisionEvidenceReference,
)

CASE_TYPES = frozenset({"industry", "company"})
WORKFLOW_STATES = frozenset({"open", "paused", "completed", "archived"})
CONCLUSION_STATUSES = frozenset(
    {"unassessed", "insufficient_evidence", "supported", "disputed", "rejected"}
)
CONTENT_FIELDS = {
    "industry": frozenset(
        {
            "driver_type",
            "demand_change",
            "supply_change",
            "technology_route",
            "process_bottlenecks",
            "chain_position",
            "related_companies",
            "customers_certifications",
            "research_conclusion",
            "risks",
            "watch_items",
        }
    ),
    "company": frozenset(
        {
            "company_profile",
            "business_structure",
            "products",
            "chain_position",
            "customers",
            "certifications",
            "competitive_advantages",
            "financial_research",
            "major_events",
            "research_conclusion",
            "risks",
            "watch_items",
        }
    ),
}

_LOCKS_GUARD = Lock()
_LOCKS: dict[UUID, RLock] = {}


class ProductWorkspaceError(ValueError):
    def __init__(self, code: str, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.public_message = message
        self.status_code = status_code


def _case_lock(case_id: UUID) -> RLock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(case_id, RLock())


def _utc(value: datetime | None = None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ProductWorkspaceError("invalid_recorded_at", "recorded_at_utc must include a UTC offset")
    return result.astimezone(timezone.utc)


def _stored_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _required(value: str, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ProductWorkspaceError("invalid_text", f"{field} must be text")
    cleaned = value.strip()
    if not cleaned or len(cleaned) > maximum:
        raise ProductWorkspaceError("invalid_text", f"{field} must contain 1 to {maximum} characters")
    return cleaned


def _optional(value: str | None, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    cleaned = _required(value, field, maximum)
    return cleaned


def _content(case_type: str, raw: dict[str, str]) -> tuple[str, str, dict[str, str]]:
    if not isinstance(raw, dict):
        raise ProductWorkspaceError("invalid_content", "content must be an object")
    unknown = set(raw) - CONTENT_FIELDS[case_type]
    if unknown:
        raise ProductWorkspaceError(
            "unsupported_content_field", f"Unsupported content fields: {', '.join(sorted(unknown))}"
        )
    normalized: dict[str, str] = {}
    for key in sorted(raw):
        normalized[key] = _required(raw[key], f"content.{key}", 12_000)
    canonical = json.dumps(normalized, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
    if len(canonical) > 100_000:
        raise ProductWorkspaceError("content_too_large", "Research content exceeds 100000 characters")
    return canonical, hashlib.sha256(canonical.encode("utf-8")).hexdigest(), normalized


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class ProductWorkspaceService:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def create_case(
        self,
        *,
        case_key: str,
        case_type: str,
        title: str,
        research_question: str,
        created_by: str,
        information_cutoff_date: date,
        content: dict[str, str],
        industry_theme: str | None = None,
        company_name: str | None = None,
        stock_code: str | None = None,
        recorded_at_utc: datetime | None = None,
    ) -> dict[str, Any]:
        if case_type not in CASE_TYPES:
            raise ProductWorkspaceError("invalid_case_type", "case_type must be industry or company")
        if case_type == "industry" and (company_name is not None or stock_code is not None):
            raise ProductWorkspaceError(
                "invalid_case_scope",
                "Industry research cannot carry company identity fields",
            )
        if case_type == "company" and industry_theme is not None:
            raise ProductWorkspaceError(
                "invalid_case_scope",
                "Company research cannot carry an industry theme identity",
            )
        key = _required(case_key, "case_key", 96)
        title = _required(title, "title", 300)
        question = _required(research_question, "research_question", 2000)
        actor = _required(created_by, "created_by", 128)
        recorded = _utc(recorded_at_utc)
        if information_cutoff_date > recorded.date():
            raise ProductWorkspaceError("future_cutoff", "information_cutoff_date cannot be in the future")
        canonical, fingerprint, normalized = _content(case_type, content)
        case_id = uuid4()
        revision_id = uuid4()
        try:
            with self._factory.begin() as session:
                session.add(
                    ResearchCase(id=case_id, case_key=key, created_at_utc=recorded, origin="manual")
                )
                session.add(
                    ProductResearchCaseProfile(
                        case_id=case_id,
                        case_type=case_type,
                        display_title=title,
                        industry_theme=_optional(industry_theme, "industry_theme", 300),
                        company_name=_optional(company_name, "company_name", 300),
                        stock_code=_optional(stock_code, "stock_code", 32),
                        created_by=actor,
                        created_at_utc=recorded,
                    )
                )
                session.add(
                    ResearchCaseRevision(
                        id=revision_id,
                        case_id=case_id,
                        revision_no=1,
                        title=title,
                        research_question=question,
                        summary=normalized.get("research_conclusion"),
                        workflow_state="open",
                        conclusion_status="unassessed",
                        information_cutoff_date=information_cutoff_date,
                        recorded_at_utc=recorded,
                        supersedes_revision_id=None,
                    )
                )
                session.add(
                    ProductResearchRevisionContent(
                        revision_id=revision_id,
                        content_json=canonical,
                        content_sha256=fingerprint,
                        change_summary="Initial research workspace revision",
                        created_by=actor,
                        recorded_at_utc=recorded,
                    )
                )
        except IntegrityError as exc:
            raise ProductWorkspaceError("case_key_conflict", "A research case with this key already exists", status_code=409) from exc
        return self.get_case(case_id)

    def append_revision(
        self,
        case_id: UUID,
        *,
        expected_latest_revision_no: int,
        title: str,
        research_question: str,
        created_by: str,
        information_cutoff_date: date,
        workflow_state: str,
        conclusion_status: str,
        content: dict[str, str],
        evidence_ids: list[UUID],
        change_summary: str | None = None,
        recorded_at_utc: datetime | None = None,
    ) -> dict[str, Any]:
        if workflow_state not in WORKFLOW_STATES or conclusion_status not in CONCLUSION_STATUSES:
            raise ProductWorkspaceError("invalid_revision_state", "Unsupported workflow or conclusion state")
        if expected_latest_revision_no < 1:
            raise ProductWorkspaceError("invalid_expected_revision", "expected_latest_revision_no must be positive")
        title = _required(title, "title", 300)
        question = _required(research_question, "research_question", 2000)
        actor = _required(created_by, "created_by", 128)
        recorded = _utc(recorded_at_utc)
        if information_cutoff_date > recorded.date():
            raise ProductWorkspaceError("future_cutoff", "information_cutoff_date cannot be in the future")
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ProductWorkspaceError("duplicate_evidence", "evidence_ids must be unique")
        with _case_lock(case_id):
            try:
                with self._factory.begin() as session:
                    case = session.scalar(select(ResearchCase).where(ResearchCase.id == case_id).with_for_update())
                    profile = session.get(ProductResearchCaseProfile, case_id)
                    if case is None or profile is None:
                        raise ProductWorkspaceError("case_not_found", "Research case was not found", status_code=404)
                    latest = session.scalar(
                        select(ResearchCaseRevision)
                        .where(ResearchCaseRevision.case_id == case_id)
                        .order_by(ResearchCaseRevision.revision_no.desc())
                        .limit(1)
                        .with_for_update()
                    )
                    if latest is None or latest.revision_no != expected_latest_revision_no:
                        raise ProductWorkspaceError("stale_revision", "The research case has a newer revision", status_code=409)
                    if recorded < _stored_utc(latest.recorded_at_utc):
                        raise ProductWorkspaceError("recorded_time_regression", "recorded_at_utc cannot precede the latest revision")
                    canonical, fingerprint, normalized = _content(profile.case_type, content)
                    accepted = self._accepted_evidence(
                        session,
                        case_id,
                        evidence_ids,
                        information_cutoff_date=information_cutoff_date,
                        recorded_at_utc=recorded,
                    )
                    if len(accepted) != len(evidence_ids):
                        raise ProductWorkspaceError(
                            "evidence_not_accepted",
                            "Every evidence reference must be accepted and belong to this research case",
                        )
                    if (workflow_state == "completed" or conclusion_status == "supported") and not evidence_ids:
                        raise ProductWorkspaceError(
                            "authoritative_revision_requires_evidence",
                            "Completed or supported research must cite accepted evidence",
                        )
                    revision = ResearchCaseRevision(
                        case_id=case_id,
                        revision_no=latest.revision_no + 1,
                        title=title,
                        research_question=question,
                        summary=normalized.get("research_conclusion"),
                        workflow_state=workflow_state,
                        conclusion_status=conclusion_status,
                        information_cutoff_date=information_cutoff_date,
                        recorded_at_utc=recorded,
                        supersedes_revision_id=latest.id,
                    )
                    session.add(revision)
                    session.flush()
                    session.add(
                        ProductResearchRevisionContent(
                            revision_id=revision.id,
                            content_json=canonical,
                            content_sha256=fingerprint,
                            change_summary=_optional(change_summary, "change_summary", 2000),
                            created_by=actor,
                            recorded_at_utc=recorded,
                        )
                    )
                    for index, evidence_id in enumerate(evidence_ids, start=1):
                        session.add(
                            ProductResearchRevisionEvidenceReference(
                                revision_id=revision.id,
                                evidence_id=evidence_id,
                                citation_order=index,
                                recorded_at_utc=recorded,
                            )
                        )
            except IntegrityError as exc:
                raise ProductWorkspaceError("revision_conflict", "Research revision conflicts with immutable history", status_code=409) from exc
        return self.get_case(case_id)

    @staticmethod
    def _accepted_evidence(
        session: Session,
        case_id: UUID,
        evidence_ids: list[UUID],
        *,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
    ) -> tuple[UUID, ...]:
        if not evidence_ids:
            return ()
        return tuple(
            session.scalars(
                select(EvidenceItem.id)
                .join(LocalDocumentAcceptanceLink, LocalDocumentAcceptanceLink.evidence_item_id == EvidenceItem.id)
                .join(
                    LocalDocumentAcceptanceReceipt,
                    LocalDocumentAcceptanceReceipt.id == LocalDocumentAcceptanceLink.receipt_id,
                )
                .where(
                    EvidenceItem.case_id == case_id,
                    EvidenceItem.id.in_(evidence_ids),
                    EvidenceItem.information_date <= information_cutoff_date,
                    EvidenceItem.recorded_at_utc <= recorded_at_utc,
                    LocalDocumentAcceptanceReceipt.accepted_at_utc <= recorded_at_utc,
                )
                .order_by(EvidenceItem.id)
            )
        )

    def list_cases(self, *, case_type: str | None = None) -> dict[str, Any]:
        if case_type is not None and case_type not in CASE_TYPES:
            raise ProductWorkspaceError("invalid_case_type", "case_type must be industry or company")
        with self._factory() as session:
            statement = select(ProductResearchCaseProfile).order_by(
                ProductResearchCaseProfile.case_type,
                ProductResearchCaseProfile.display_title,
                ProductResearchCaseProfile.case_id,
            )
            if case_type:
                statement = statement.where(ProductResearchCaseProfile.case_type == case_type)
            items = [self._case_summary(session, profile) for profile in session.scalars(statement)]
        return {"items": items, "count": len(items), "research_only": True}

    def get_case(self, case_id: UUID) -> dict[str, Any]:
        with self._factory() as session:
            profile = session.get(ProductResearchCaseProfile, case_id)
            case = session.get(ResearchCase, case_id)
            if profile is None or case is None:
                raise ProductWorkspaceError("case_not_found", "Research case was not found", status_code=404)
            revisions = tuple(
                session.scalars(
                    select(ResearchCaseRevision)
                    .where(ResearchCaseRevision.case_id == case_id)
                    .order_by(ResearchCaseRevision.revision_no)
                )
            )
            payloads = {
                item.revision_id: item
                for item in session.scalars(
                    select(ProductResearchRevisionContent).where(
                        ProductResearchRevisionContent.revision_id.in_([r.id for r in revisions])
                    )
                )
            }
            if len(payloads) != len(revisions):
                raise ProductWorkspaceError(
                    "research_case_integrity_error",
                    "Research case revision content is incomplete",
                    status_code=409,
                )
            revision_payloads = [self._revision_payload(session, item, payloads.get(item.id)) for item in revisions]
            authoritative = next(
                (
                    item
                    for item in reversed(revision_payloads)
                    if item["workflow_state"] == "completed" and item["conclusion_status"] == "supported"
                ),
                None,
            )
            return {
                "case": {
                    "case_id": str(case.id),
                    "case_key": case.case_key,
                    "case_type": profile.case_type,
                    "display_title": profile.display_title,
                    "industry_theme": profile.industry_theme,
                    "company_name": profile.company_name,
                    "stock_code": profile.stock_code,
                    "created_by": profile.created_by,
                    "created_at_utc": _timestamp(profile.created_at_utc),
                },
                "current_revision": revision_payloads[-1],
                "authoritative_revision": authoritative,
                "revision_history": revision_payloads,
                "notices": self._notices(),
            }

    def _case_summary(self, session: Session, profile: ProductResearchCaseProfile) -> dict[str, Any]:
        latest = session.scalar(
            select(ResearchCaseRevision)
            .where(ResearchCaseRevision.case_id == profile.case_id)
            .order_by(ResearchCaseRevision.revision_no.desc())
            .limit(1)
        )
        assert latest is not None
        return {
            "case_id": str(profile.case_id),
            "case_type": profile.case_type,
            "title": latest.title,
            "company_name": profile.company_name,
            "stock_code": profile.stock_code,
            "industry_theme": profile.industry_theme,
            "latest_revision_no": latest.revision_no,
            "workflow_state": latest.workflow_state,
            "conclusion_status": latest.conclusion_status,
            "recorded_at_utc": _timestamp(latest.recorded_at_utc),
        }

    def _revision_payload(
        self, session: Session, revision: ResearchCaseRevision, content: ProductResearchRevisionContent | None
    ) -> dict[str, Any]:
        references = tuple(
            session.scalars(
                select(ProductResearchRevisionEvidenceReference)
                .where(ProductResearchRevisionEvidenceReference.revision_id == revision.id)
                .order_by(ProductResearchRevisionEvidenceReference.citation_order)
            )
        )
        evidence = {
            item.id: item
            for item in session.scalars(
                select(EvidenceItem).where(EvidenceItem.id.in_([ref.evidence_id for ref in references]))
            )
        } if references else {}
        citations = [self._citation(session, ref, evidence[ref.evidence_id]) for ref in references]
        return {
            "revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "title": revision.title,
            "research_question": revision.research_question,
            "summary": revision.summary,
            "workflow_state": revision.workflow_state,
            "conclusion_status": revision.conclusion_status,
            "information_cutoff_date": revision.information_cutoff_date.isoformat(),
            "recorded_at_utc": _timestamp(revision.recorded_at_utc),
            "supersedes_revision_id": None if revision.supersedes_revision_id is None else str(revision.supersedes_revision_id),
            "content": {} if content is None else json.loads(content.content_json),
            "content_sha256": None if content is None else content.content_sha256,
            "change_summary": None if content is None else content.change_summary,
            "created_by": None if content is None else content.created_by,
            "evidence_references": citations,
        }

    @staticmethod
    def _citation(
        session: Session,
        reference: ProductResearchRevisionEvidenceReference,
        evidence: EvidenceItem,
    ) -> dict[str, Any]:
        acceptance = session.scalar(
            select(LocalDocumentAcceptanceLink).where(
                LocalDocumentAcceptanceLink.evidence_item_id == evidence.id
            )
        )
        page_number = None
        document_id = None
        source_url = None
        if acceptance is not None:
            candidate = session.get(LocalDocumentCandidate, acceptance.candidate_id)
            if candidate is not None:
                page_number = candidate.page_number
                review = session.get(LocalDocumentReviewSession, candidate.review_session_id)
                attempt = (
                    None
                    if review is None
                    else session.get(LocalDocumentImportAttempt, review.import_attempt_id)
                )
                document_id = (
                    None
                    if attempt is None or attempt.content_id is None
                    else str(attempt.content_id)
                )
            receipt = session.get(LocalDocumentAcceptanceReceipt, acceptance.receipt_id)
            accepted_revision = (
                None
                if receipt is None
                else session.get(
                    LocalDocumentReviewRevision,
                    receipt.accepted_review_revision_id,
                )
            )
            document_candidate = (
                None
                if accepted_revision is None
                else session.get(
                    LocalDocumentCandidate,
                    accepted_revision.document_identity_candidate_id,
                )
            )
            if document_candidate is not None:
                source_url = json.loads(
                    document_candidate.candidate_payload_json
                ).get("source_url")
        return {
            "reference_id": str(reference.id),
            "evidence_id": str(evidence.id),
            "citation_order": reference.citation_order,
            "source": evidence.source_title,
            "publisher": evidence.publisher_or_author,
            "document_id": document_id,
            "page": page_number,
            "source_locator": evidence.source_locator,
            "source_url": source_url,
            "evidence_grade": evidence.evidence_grade,
            "content_fragment": evidence.summary,
        }

    def evidence_ledger(self, *, status: str | None = None) -> dict[str, Any]:
        if status not in {None, "imported", "pending_review", "accepted", "rejected"}:
            raise ProductWorkspaceError("invalid_evidence_status", "Unsupported evidence status")
        with self._factory() as session:
            accepted_links = tuple(session.scalars(select(LocalDocumentAcceptanceLink)))
            accepted_ids = {item.evidence_item_id for item in accepted_links}
            links_by_evidence = {item.evidence_item_id: item for item in accepted_links}
            accepted = tuple(
                session.scalars(select(EvidenceItem).where(EvidenceItem.id.in_(accepted_ids)).order_by(EvidenceItem.recorded_at_utc.desc(), EvidenceItem.id))
            ) if accepted_ids else ()
            items: list[dict[str, Any]] = []
            if status in {None, "accepted"}:
                for item in accepted:
                    link = links_by_evidence[item.id]
                    receipt = session.get(LocalDocumentAcceptanceReceipt, link.receipt_id)
                    review = (
                        None
                        if receipt is None
                        else session.get(
                            LocalDocumentReviewRevision,
                            receipt.accepted_review_revision_id,
                        )
                    )
                    candidate = session.get(LocalDocumentCandidate, link.candidate_id)
                    review_session = (
                        None
                        if receipt is None
                        else session.get(LocalDocumentReviewSession, receipt.review_session_id)
                    )
                    import_attempt = (
                        None
                        if review_session is None
                        else session.get(
                            LocalDocumentImportAttempt,
                            review_session.import_attempt_id,
                        )
                    )
                    document_candidate = (
                        None
                        if review is None
                        else session.get(
                            LocalDocumentCandidate,
                            review.document_identity_candidate_id,
                        )
                    )
                    document_payload = (
                        {}
                        if document_candidate is None
                        else json.loads(document_candidate.candidate_payload_json)
                    )
                    items.append({
                        "status": "accepted",
                        "evidence_id": str(item.id),
                        "case_id": str(item.case_id),
                        "source": item.source_title,
                        "publisher": item.publisher_or_author,
                        "grade": item.evidence_grade,
                        "content_fragment": item.summary,
                        "information_date": item.information_date.isoformat(),
                        "recorded_at_utc": _timestamp(item.recorded_at_utc),
                        "reviewer": None if review is None else review.reviewer_identity,
                        "review_note": None if review is None else review.reviewer_note,
                        "reviewed_at_utc": None if receipt is None else _timestamp(receipt.accepted_at_utc),
                        "document_id": None if import_attempt is None or import_attempt.content_id is None else str(import_attempt.content_id),
                        "page": None if candidate is None else candidate.page_number,
                        "source_locator": item.source_locator,
                        "source_url": document_payload.get("source_url"),
                    })
            if status in {None, "pending_review", "rejected", "imported"}:
                sessions = tuple(session.scalars(select(LocalDocumentReviewSession).order_by(LocalDocumentReviewSession.created_at_utc.desc())))
                attempts_by_id = {
                    attempt.id: attempt
                    for attempt in session.scalars(select(LocalDocumentImportAttempt))
                }
                reviewed_content_ids = {
                    attempts_by_id[review.import_attempt_id].content_id
                    for review in sessions
                    if review.import_attempt_id in attempts_by_id
                    and attempts_by_id[review.import_attempt_id].content_id is not None
                }
                for review in sessions:
                    latest = session.scalar(
                        select(LocalDocumentReviewRevision)
                        .where(LocalDocumentReviewRevision.review_session_id == review.id)
                        .order_by(LocalDocumentReviewRevision.revision_number.desc())
                        .limit(1)
                    )
                    if latest is not None and latest.review_state == "accepted":
                        continue
                    state = "imported" if latest is None else ("rejected" if latest.review_state == "rejected" else "pending_review")
                    if status is None or status == state:
                        attempt = session.get(LocalDocumentImportAttempt, review.import_attempt_id)
                        items.append(
                            {
                                "status": state,
                                "review_session_id": str(review.id),
                                "case_id": str(review.target_research_case_id),
                                "document_id": None if attempt is None or attempt.content_id is None else str(attempt.content_id),
                                "reviewer": None if latest is None else latest.reviewer_identity,
                                "reviewed_at_utc": None if latest is None else _timestamp(latest.recorded_at_utc),
                            }
                        )
                if status in {None, "imported"}:
                    seen_content_ids: set[UUID] = set()
                    for attempt in sorted(
                        attempts_by_id.values(),
                        key=lambda row: (
                            _stored_utc(row.imported_at_utc),
                            row.original_filename.casefold(),
                            row.display_name.casefold(),
                            str(row.id),
                        ),
                    ):
                        if (
                            attempt.content_id is None
                            or attempt.content_id in reviewed_content_ids
                            or attempt.content_id in seen_content_ids
                        ):
                            continue
                        seen_content_ids.add(attempt.content_id)
                        items.append(
                            {
                                "status": "imported",
                                "import_attempt_id": str(attempt.id),
                                "case_id": None,
                                "document_id": None if attempt.content_id is None else str(attempt.content_id),
                                "content_fragment": attempt.display_name,
                                "reviewer": None,
                                "reviewed_at_utc": None,
                                "recorded_at_utc": _timestamp(attempt.imported_at_utc),
                            }
                        )
        items.sort(key=lambda item: (item.get("recorded_at_utc") or item.get("reviewed_at_utc") or "", str(item.get("evidence_id") or item.get("review_session_id"))), reverse=True)
        return {"items": items[:500], "count": len(items), "statuses": ["imported", "pending_review", "accepted", "rejected"]}

    def dashboard(self) -> dict[str, Any]:
        cases = self.list_cases()["items"]
        pending_count = self.evidence_ledger(status="pending_review")["count"]
        accepted_count = self.evidence_ledger(status="accepted")["count"]
        feed = self.change_feed(limit=8)["items"]
        return {
            "case_count": len(cases),
            "industry_case_count": sum(item["case_type"] == "industry" for item in cases),
            "company_case_count": sum(item["case_type"] == "company" for item in cases),
            "pending_evidence_count": pending_count,
            "accepted_evidence_count": accepted_count,
            "recent_changes": feed,
            "research_only": True,
        }

    def documents(self) -> dict[str, Any]:
        with self._factory() as session:
            items: list[dict[str, Any]] = []
            for attempt in session.scalars(
                select(LocalDocumentImportAttempt).order_by(
                    LocalDocumentImportAttempt.imported_at_utc.desc(),
                    LocalDocumentImportAttempt.id,
                )
            ):
                content = (
                    None
                    if attempt.content_id is None
                    else session.get(LocalDocumentContent, attempt.content_id)
                )
                items.append(
                    {
                        "import_attempt_id": str(attempt.id),
                        "document_id": None if content is None else str(content.id),
                        "original_filename": attempt.original_filename,
                        "display_name": attempt.display_name,
                        "sha256": attempt.content_sha256,
                        "byte_size": attempt.byte_size,
                        "page_count": None if content is None else content.page_count,
                        "extractor_contract_version": (
                            None if content is None else content.extractor_contract_version
                        ),
                        "admission_state": attempt.admission_state,
                        "admission_reason": attempt.admission_reason,
                        "imported_at_utc": _timestamp(attempt.imported_at_utc),
                    }
                )
        return {"items": items, "count": len(items)}

    def sources(self) -> dict[str, Any]:
        ledger = self.evidence_ledger(status="accepted")["items"]
        grouped: dict[tuple[str, str | None], dict[str, Any]] = {}
        for item in ledger:
            key = (item["source"], item["publisher"])
            current = grouped.setdefault(
                key,
                {
                    "title": item["source"],
                    "publisher": item["publisher"],
                    "accepted_evidence_count": 0,
                    "evidence_ids": [],
                },
            )
            current["accepted_evidence_count"] += 1
            current["evidence_ids"].append(item["evidence_id"])
        items = sorted(grouped.values(), key=lambda item: (item["title"], item["publisher"] or ""))
        return {"items": items, "count": len(items)}

    def change_feed(self, *, limit: int = 50) -> dict[str, Any]:
        if limit < 1 or limit > 100:
            raise ProductWorkspaceError("invalid_limit", "limit must be between 1 and 100")
        with self._factory() as session:
            events: list[dict[str, Any]] = []
            for revision, profile in session.execute(
                select(ResearchCaseRevision, ProductResearchCaseProfile)
                .join(ProductResearchCaseProfile, ProductResearchCaseProfile.case_id == ResearchCaseRevision.case_id)
            ):
                events.append({"event_type": "research_revision", "case_id": str(revision.case_id), "case_type": profile.case_type, "title": revision.title, "detail": f"Revision {revision.revision_no}: {revision.conclusion_status}", "recorded_at_utc": _timestamp(revision.recorded_at_utc)})
            for evidence in session.scalars(
                select(EvidenceItem)
                .join(
                    LocalDocumentAcceptanceLink,
                    LocalDocumentAcceptanceLink.evidence_item_id == EvidenceItem.id,
                )
                .order_by(EvidenceItem.recorded_at_utc, EvidenceItem.id)
            ):
                events.append({"event_type": "accepted_evidence", "case_id": str(evidence.case_id), "title": evidence.source_title, "detail": evidence.summary, "recorded_at_utc": _timestamp(evidence.recorded_at_utc)})
            for attempt in session.scalars(select(LocalDocumentImportAttempt)):
                events.append({"event_type": "document_import", "title": attempt.display_name, "detail": attempt.admission_state, "recorded_at_utc": _timestamp(attempt.imported_at_utc)})
        events.sort(key=lambda item: (item["recorded_at_utc"], item["event_type"], item.get("case_id", "")), reverse=True)
        return {"items": events[:limit], "count": len(events)}

    def search(self, query: str, *, limit: int = 50) -> dict[str, Any]:
        term = _required(query, "query", 200).lower()
        if limit < 1 or limit > 100:
            raise ProductWorkspaceError("invalid_limit", "limit must be between 1 and 100")
        results: list[dict[str, Any]] = []
        with self._factory() as session:
            for profile in session.scalars(select(ProductResearchCaseProfile)):
                haystack = " ".join(filter(None, [profile.display_title, profile.company_name, profile.stock_code, profile.industry_theme])).lower()
                if term in haystack:
                    results.append({"kind": "research_case", "id": str(profile.case_id), "title": profile.display_title, "snippet": profile.case_type})
            for evidence in session.scalars(select(EvidenceItem)):
                haystack = " ".join(filter(None, [evidence.source_title, evidence.publisher_or_author, evidence.summary])).lower()
                if term in haystack:
                    results.append({"kind": "evidence", "id": str(evidence.id), "title": evidence.source_title, "snippet": evidence.summary[:240]})
            for attempt in session.scalars(select(LocalDocumentImportAttempt)):
                if term in f"{attempt.original_filename} {attempt.display_name}".lower():
                    results.append({"kind": "document", "id": str(attempt.id), "title": attempt.display_name, "snippet": attempt.admission_state})
        results.sort(key=lambda item: (item["kind"], item["title"].lower(), item["id"]))
        return {"query": query.strip(), "items": results[:limit], "count": len(results)}

    def report(self, case_id: UUID, *, format: str = "markdown") -> tuple[str, str]:
        if format not in {"markdown", "html"}:
            raise ProductWorkspaceError("invalid_report_format", "format must be markdown or html")
        payload = self.get_case(case_id)
        revision = payload["current_revision"]
        case = payload["case"]
        lines = [
            f"# {revision['title']}",
            "",
            f"Generated at: {_timestamp(datetime.now(timezone.utc))}",
            f"Research case: {case['case_id']} ({case['case_type']})",
            f"Revision: {revision['revision_no']} / {revision['revision_id']}",
            f"Status: {revision['workflow_state']} / {revision['conclusion_status']}",
            "",
            "## Research question",
            revision["research_question"],
        ]
        for key, value in revision["content"].items():
            lines.extend(["", f"## {key.replace('_', ' ').title()}", value])
        lines.extend(["", "## Evidence citations"])
        if not revision["evidence_references"]:
            lines.append("No accepted evidence is bound to this revision.")
        for citation in revision["evidence_references"]:
            lines.append(
                f"{citation['citation_order']}. {citation['source']} | Document {citation['document_id'] or 'n/a'} | Page {citation['page'] or 'n/a'} | Evidence {citation['evidence_id']}"
            )
        lines.extend(["", "## Source list"])
        if not revision["evidence_references"]:
            lines.append("No accepted sources are bound to this revision.")
        for citation in revision["evidence_references"]:
            lines.append(
                f"- {citation['source']} | Publisher {citation['publisher'] or 'n/a'} | URL {citation['source_url'] or 'local document'} | Provenance {citation['source_locator'] or 'n/a'}"
            )
        lines.extend(["", "## Disclaimer", "Research use only. This report is not investment advice and contains no trading action."])
        markdown = "\n".join(lines) + "\n"
        if format == "markdown":
            return markdown, "text/markdown; charset=utf-8"
        import html

        body = "\n".join(f"<p>{html.escape(line)}</p>" if line and not line.startswith("#") else (f"<h{min(len(line) - len(line.lstrip('#')), 6)}>{html.escape(line.lstrip('#').strip())}</h{min(len(line) - len(line.lstrip('#')), 6)}>" if line else "") for line in lines)
        return f"<!doctype html><html lang='en'><meta charset='utf-8'><title>{html.escape(revision['title'])}</title><body>{body}</body></html>", "text/html; charset=utf-8"

    @staticmethod
    def _notices() -> dict[str, Any]:
        return {
            "research_only": True,
            "not_investment_advice": True,
            "no_trading_actions": True,
            "accepted_evidence_required_for_authoritative_revision": True,
            "ai_cannot_review_or_mutate_evidence": True,
        }
