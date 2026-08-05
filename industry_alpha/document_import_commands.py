"""Transactional commands for immutable local PDF import and human review."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
from uuid import UUID, uuid4

from sqlalchemy import and_, func, literal, select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price_models import ListedInstrument
from industry_alpha.document_import_contracts import (
    ACCEPTANCE_CONTRACT_VERSION,
    ACCEPTED_REVIEW_CONTRACT_VERSION,
    EVIDENCE_FINGERPRINT_CONTRACT,
    AcceptanceInput,
    AcceptanceResult,
    CandidateInput,
    DecisionInput,
    DocumentImportError,
    ImportResult,
    ReviewRevisionInput,
)
from industry_alpha.document_import_extractor import extract_pdf
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
from industry_alpha.document_import_rules import (
    CANDIDATE_KINDS,
    DECISIONS,
    MAX_CANDIDATES,
    REVIEW_STATES,
    bounded_text,
    canonical_json,
    fingerprint,
    sha256_hex,
    utc_timestamp,
    validate_company_identity_payload,
    validate_document_identity_payload,
    validate_sha256,
    validated_basename,
)
from industry_alpha.models import (
    Claim,
    ClaimEvidenceLink,
    ClaimRevision,
    EvidenceItem,
    ResearchCase,
)
from industry_alpha.validation import (
    CLAIM_STATUSES,
    EVIDENCE_GRADES,
    EVIDENCE_RELATIONS,
    SOURCE_KINDS,
)


class _DocumentImportBase:
    """Own pre-acceptance document/import/review history only."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def import_pdf(
        self,
        *,
        pdf_bytes: bytes,
        original_filename: str,
        display_name: str | None = None,
        observed_media_type: str = "application/pdf",
        imported_at_utc: datetime | None = None,
    ) -> ImportResult:
        filename = validated_basename(original_filename)
        display = bounded_text(display_name or filename, "display_name", 300)
        recorded = utc_timestamp(imported_at_utc)
        content_sha = sha256_hex(pdf_bytes)
        persisted_media_type = self._safe_observed_media_type(observed_media_type)
        if observed_media_type != "application/pdf":
            return self._record_rejected_import(
                content_sha=content_sha,
                filename=filename,
                display_name=display,
                observed_media_type=persisted_media_type,
                byte_size=len(pdf_bytes),
                reason="invalid_media_type",
                recorded_at_utc=recorded,
            )

        with self._session_factory.begin() as session:
            duplicate = session.scalar(
                select(LocalDocumentContent).where(
                    LocalDocumentContent.content_sha256 == content_sha
                )
            )
            if duplicate is not None:
                return self._record_import_attempt(
                    session,
                    content=duplicate,
                    content_sha=content_sha,
                    filename=filename,
                    display_name=display,
                    observed_media_type=persisted_media_type,
                    byte_size=len(pdf_bytes),
                    state="exact_content_duplicate",
                    recorded_at_utc=recorded,
                )

        try:
            extracted = extract_pdf(pdf_bytes)
            if (
                extracted.content_sha256 != content_sha
                or extracted.byte_size != len(pdf_bytes)
                or extracted.extractor_package != "pypdf"
                or extracted.extractor_version != "6.14.2"
            ):
                raise DocumentImportError("extractor_contract_mismatch")
        except DocumentImportError as exc:
            return self._record_rejected_import(
                content_sha=content_sha,
                filename=filename,
                display_name=display,
                observed_media_type=persisted_media_type,
                byte_size=len(pdf_bytes),
                reason=exc.code,
                recorded_at_utc=recorded,
            )

        with self._session_factory.begin() as session:
            content = session.scalar(
                select(LocalDocumentContent).where(
                    LocalDocumentContent.content_sha256 == extracted.content_sha256
                )
            )
            if content is not None:
                return self._record_import_attempt(
                    session,
                    content=content,
                    content_sha=content_sha,
                    filename=filename,
                    display_name=display,
                    observed_media_type=persisted_media_type,
                    byte_size=len(pdf_bytes),
                    state="exact_content_duplicate",
                    recorded_at_utc=recorded,
                )
            filename_conflict = session.scalar(
                select(LocalDocumentImportAttempt.id).where(
                    LocalDocumentImportAttempt.original_filename == filename,
                    LocalDocumentImportAttempt.content_sha256 != content_sha,
                    LocalDocumentImportAttempt.admission_state != "rejected",
                ).limit(1)
            )
            content = LocalDocumentContent(
                content_sha256=extracted.content_sha256,
                media_type="application/pdf",
                byte_size=extracted.byte_size,
                raw_pdf_bytes=pdf_bytes,
                page_count=len(extracted.pages),
                embedded_text_page_count=extracted.embedded_text_page_count,
                total_text_char_count=extracted.total_text_char_count,
                extractor_contract_version=extracted.extractor_contract_version,
                extractor_package=extracted.extractor_package,
                extractor_version=extracted.extractor_version,
                created_at_utc=recorded,
            )
            session.add(content)
            session.flush()
            session.add_all(
                LocalDocumentPage(
                    content_id=content.id,
                    page_number=page.page_number,
                    text_state=(
                        "embedded_text_present" if page.text.strip() else "empty"
                    ),
                    extracted_text=page.text,
                    text_sha256=page.text_sha256,
                    text_char_count=page.text_char_count,
                )
                for page in extracted.pages
            )
            return self._record_import_attempt(
                session,
                content=content,
                content_sha=content_sha,
                filename=filename,
                display_name=display,
                observed_media_type=persisted_media_type,
                byte_size=len(pdf_bytes),
                state=(
                    "filename_content_conflict" if filename_conflict else "admitted"
                ),
                recorded_at_utc=recorded,
            )

    def _record_rejected_import(
        self,
        *,
        content_sha: str,
        filename: str,
        display_name: str,
        observed_media_type: str,
        byte_size: int,
        reason: str,
        recorded_at_utc: datetime,
    ) -> ImportResult:
        with self._session_factory.begin() as session:
            attempt = LocalDocumentImportAttempt(
                content_sha256=content_sha,
                content_id=None,
                original_filename=filename,
                display_name=display_name,
                observed_media_type=observed_media_type,
                byte_size=byte_size,
                admission_state="rejected",
                admission_reason=reason,
                imported_at_utc=recorded_at_utc,
            )
            session.add(attempt)
            session.flush()
            result = ImportResult(
                attempt.id, None, content_sha, "rejected", reason
            )
        return result

    @staticmethod
    def _record_import_attempt(
        session: Session,
        *,
        content: LocalDocumentContent,
        content_sha: str,
        filename: str,
        display_name: str,
        observed_media_type: str,
        byte_size: int,
        state: str,
        recorded_at_utc: datetime,
    ) -> ImportResult:
        attempt = LocalDocumentImportAttempt(
            content_sha256=content_sha,
            content_id=content.id,
            original_filename=filename,
            display_name=display_name,
            observed_media_type=observed_media_type,
            byte_size=byte_size,
            admission_state=state,
            admission_reason=state,
            imported_at_utc=recorded_at_utc,
        )
        session.add(attempt)
        session.flush()
        return ImportResult(attempt.id, content.id, content_sha, state, state)

    @staticmethod
    def _safe_observed_media_type(value: str) -> str:
        if (
            isinstance(value, str)
            and 0 < len(value) <= 128
            and not any(ord(char) < 32 or ord(char) == 127 for char in value)
        ):
            return value
        return "invalid"


def preview_local_document_acceptance(
    session: Session, request: AcceptanceInput
) -> AcceptanceResult:
    """Rebuild the exact plan without writing any row."""

    prepared = _prepare_acceptance(session, request)
    return AcceptanceResult(
        receipt_id=None,
        accepted_review_revision_id=None,
        acceptance_plan_fingerprint_sha256=prepared["plan_fingerprint"],
        request_fingerprint_sha256=_acceptance_request_fingerprint(
            request, prepared["plan_fingerprint"]
        ),
        selected_candidate_ids=prepared["selected_ids"],
        commit_ready=True,
    )


def accept_local_document_in_session(
    session: Session, request: AcceptanceInput
) -> AcceptanceResult:
    """Insert the accepted graph inside the Evidence Ledger owner's transaction."""

    if request.acceptance_contract_version != ACCEPTANCE_CONTRACT_VERSION:
        raise DocumentImportError("acceptance_contract_mismatch")
    source_anchor = session.get(
        LocalDocumentReviewRevision, request.source_review_revision_id
    )
    if source_anchor is None:
        raise DocumentImportError("source_review_revision_not_found")
    locked_review = session.scalar(
        select(LocalDocumentReviewSession)
        .where(LocalDocumentReviewSession.id == source_anchor.review_session_id)
        .with_for_update()
    )
    if locked_review is None:
        raise DocumentImportError("review_graph_invalid")
    supplied_request_fingerprint = _acceptance_request_fingerprint(
        request, request.acceptance_plan_fingerprint_sha256
    )
    receipt = session.scalar(
        select(LocalDocumentAcceptanceReceipt).where(
            LocalDocumentAcceptanceReceipt.source_review_revision_id
            == request.source_review_revision_id
        )
    )
    if receipt is not None:
        if (
            receipt.request_fingerprint_sha256 != supplied_request_fingerprint
            or receipt.source_review_fingerprint_sha256
            != request.expected_source_review_fingerprint_sha256
            or receipt.target_research_case_id != request.target_research_case_id
            or receipt.acceptance_contract_version != request.acceptance_contract_version
        ):
            raise DocumentImportError("acceptance_replay_conflict")
        selected = tuple(
            sorted(
                session.scalars(
                    select(LocalDocumentAcceptanceLink.candidate_id).where(
                        LocalDocumentAcceptanceLink.receipt_id == receipt.id
                    )
                ),
                key=str,
            )
        )
        return AcceptanceResult(
            receipt_id=receipt.id,
            accepted_review_revision_id=receipt.accepted_review_revision_id,
            acceptance_plan_fingerprint_sha256=request.acceptance_plan_fingerprint_sha256,
            request_fingerprint_sha256=receipt.request_fingerprint_sha256,
            selected_candidate_ids=selected,
            commit_ready=True,
            replayed=True,
        )

    prepared = _prepare_acceptance(
        session,
        request,
        lock=True,
        source_row=source_anchor,
        review_row=locked_review,
    )
    if prepared["plan_fingerprint"] != request.acceptance_plan_fingerprint_sha256:
        raise DocumentImportError("acceptance_plan_mismatch")
    source: LocalDocumentReviewRevision = prepared["source"]
    review: LocalDocumentReviewSession = prepared["review"]
    decisions: dict[UUID, LocalDocumentReviewCandidateDecision] = prepared["decisions"]
    candidates: dict[UUID, LocalDocumentCandidate] = prepared["candidates"]
    document_payload: dict[str, object] = prepared["document_payload"]
    content: LocalDocumentContent = prepared["content"]
    accepted_at: datetime = prepared["accepted_at"]

    accepted_number = source.revision_number + 1
    accepted_fingerprint = fingerprint(
        {
            "contract": ACCEPTED_REVIEW_CONTRACT_VERSION,
            "source_review_revision_id": source.id,
            "source_review_fingerprint_sha256": source.review_fingerprint_sha256,
            "accepted_revision_number": accepted_number,
            "review_state": "accepted",
            "acceptance_request_fingerprint_sha256": supplied_request_fingerprint,
            "acceptance_plan_fingerprint_sha256": prepared["plan_fingerprint"],
            "target_research_case_id": review.target_research_case_id,
            "accepted_at_utc": accepted_at,
        }
    )
    accepted = LocalDocumentReviewRevision(
        review_session_id=review.id,
        revision_number=accepted_number,
        review_state="accepted",
        review_fingerprint_sha256=accepted_fingerprint,
        expected_previous_revision_number=source.revision_number,
        source_kind=source.source_kind,
        evidence_grade=source.evidence_grade,
        document_identity_candidate_id=source.document_identity_candidate_id,
        subject_candidate_id=source.subject_candidate_id,
        information_date=source.information_date,
        reviewer_note=source.reviewer_note,
        recorded_at_utc=accepted_at,
        supersedes_review_revision_id=source.id,
    )
    session.add(accepted)
    session.flush()
    session.add_all(
        LocalDocumentReviewCandidateDecision(
            review_revision_id=accepted.id,
            candidate_id=row.candidate_id,
            decision=row.decision,
            claim_operation=row.claim_operation,
            claim_key=row.claim_key,
            claim_status=row.claim_status,
            evidence_relation=row.evidence_relation,
            decision_fingerprint_sha256=row.decision_fingerprint_sha256,
        )
        for row in decisions.values()
    )
    receipt = LocalDocumentAcceptanceReceipt(
        review_session_id=review.id,
        source_review_revision_id=source.id,
        accepted_review_revision_id=accepted.id,
        target_research_case_id=review.target_research_case_id,
        source_review_fingerprint_sha256=source.review_fingerprint_sha256,
        accepted_review_fingerprint_sha256=accepted_fingerprint,
        request_fingerprint_sha256=supplied_request_fingerprint,
        acceptance_contract_version=request.acceptance_contract_version,
        accepted_at_utc=accepted_at,
    )
    session.add(receipt)
    session.flush()

    title = str(document_payload["document_title"])
    publisher = str(document_payload["publisher_or_author"])
    evidence_and_claim_rows: list[object] = []
    claim_revision_rows: list[ClaimRevision] = []
    claim_evidence_link_rows: list[ClaimEvidenceLink] = []
    acceptance_link_rows: list[LocalDocumentAcceptanceLink] = []
    for candidate_id in prepared["selected_ids"]:
        candidate = candidates[candidate_id]
        decision = decisions[candidate_id]
        evidence_fp = _evidence_fingerprint(content, candidate)
        evidence = EvidenceItem(
            id=uuid4(),
            case_id=review.target_research_case_id,
            evidence_grade=source.evidence_grade,
            source_kind=source.source_kind,
            source_title=title,
            publisher_or_author=publisher,
            source_locator=(
                f"local-document:{content.id}#page={candidate.page_number}"
                f"&start_utf8_byte={candidate.start_utf8_byte}"
                f"&end_utf8_byte={candidate.end_utf8_byte}"
            ),
            information_date=source.information_date,
            recorded_at_utc=accepted_at,
            summary=candidate.statement,
            content_fingerprint=evidence_fp,
            supersedes_evidence_id=None,
        )
        claim = Claim(
            id=uuid4(),
            case_id=review.target_research_case_id,
            claim_key=decision.claim_key,
            created_at_utc=accepted_at,
        )
        claim_revision = ClaimRevision(
            id=uuid4(),
            claim_id=claim.id,
            revision_no=1,
            statement=candidate.statement,
            claim_kind="fact",
            claim_status=decision.claim_status,
            inference_confidence=None,
            inference_basis=None,
            information_cutoff_date=source.information_date,
            recorded_at_utc=accepted_at,
            supersedes_revision_id=None,
        )
        link = ClaimEvidenceLink(
            id=uuid4(),
            claim_revision_id=claim_revision.id,
            evidence_id=evidence.id,
            relation=decision.evidence_relation,
            link_note=None,
            recorded_at_utc=accepted_at,
        )
        acceptance_link = (
            LocalDocumentAcceptanceLink(
                id=uuid4(),
                receipt_id=receipt.id,
                candidate_id=candidate.id,
                evidence_item_id=evidence.id,
                claim_id=claim.id,
                claim_revision_id=claim_revision.id,
                claim_evidence_link_id=link.id,
            )
        )
        evidence_and_claim_rows.extend((evidence, claim))
        claim_revision_rows.append(claim_revision)
        claim_evidence_link_rows.append(link)
        acceptance_link_rows.append(acceptance_link)
    session.add_all(evidence_and_claim_rows)
    session.flush()
    session.add_all(claim_revision_rows)
    session.flush()
    session.add_all(claim_evidence_link_rows)
    session.flush()
    session.add_all(acceptance_link_rows)
    session.flush()
    return AcceptanceResult(
        receipt_id=receipt.id,
        accepted_review_revision_id=accepted.id,
        acceptance_plan_fingerprint_sha256=prepared["plan_fingerprint"],
        request_fingerprint_sha256=supplied_request_fingerprint,
        selected_candidate_ids=prepared["selected_ids"],
        commit_ready=True,
    )


def _prepare_acceptance(
    session: Session,
    request: AcceptanceInput,
    *,
    lock: bool = False,
    source_row: LocalDocumentReviewRevision | None = None,
    review_row: LocalDocumentReviewSession | None = None,
) -> dict[str, object]:
    accepted_at = utc_timestamp(request.recorded_at_utc)
    source = source_row or session.get(
        LocalDocumentReviewRevision, request.source_review_revision_id
    )
    if source is None:
        raise DocumentImportError("source_review_revision_not_found")
    review = review_row
    if review is None:
        review_query = select(LocalDocumentReviewSession).where(
            LocalDocumentReviewSession.id == source.review_session_id
        )
        if lock:
            review_query = review_query.with_for_update()
        review = session.scalar(review_query)
    if review is None:
        raise DocumentImportError("review_graph_invalid")
    if source.review_session_id != review.id:
        raise DocumentImportError("review_graph_invalid")
    if request.acceptance_contract_version != ACCEPTANCE_CONTRACT_VERSION:
        raise DocumentImportError("acceptance_contract_mismatch")
    if (
        source.revision_number != request.expected_source_review_revision_number
        or source.review_fingerprint_sha256
        != request.expected_source_review_fingerprint_sha256
    ):
        raise DocumentImportError("source_review_mismatch")
    latest_number = session.scalar(
        select(func.max(LocalDocumentReviewRevision.revision_number)).where(
            LocalDocumentReviewRevision.review_session_id == review.id
        )
    )
    if latest_number != request.expected_session_latest_revision_number or latest_number != source.revision_number:
        raise DocumentImportError("review_latest_mismatch")
    if source.review_state not in {"draft", "deferred"}:
        raise DocumentImportError("source_review_not_acceptable")
    if review.target_research_case_id != request.target_research_case_id:
        raise DocumentImportError("target_research_case_mismatch")
    case_query = select(ResearchCase).where(ResearchCase.id == review.target_research_case_id)
    if lock:
        case_query = case_query.with_for_update()
    case = session.scalar(case_query)
    if case is None:
        raise DocumentImportError("research_case_not_found")
    if (
        source.information_date > accepted_at.date()
        or accepted_at < _stored_utc(source.recorded_at_utc)
        or accepted_at < _stored_utc(review.created_at_utc)
        or accepted_at < _stored_utc(case.created_at_utc)
    ):
        raise DocumentImportError("acceptance_chronology_invalid")
    candidate_decision_rows = session.execute(
        select(LocalDocumentCandidate, LocalDocumentReviewCandidateDecision)
        .outerjoin(
            LocalDocumentReviewCandidateDecision,
            and_(
                LocalDocumentReviewCandidateDecision.candidate_id
                == LocalDocumentCandidate.id,
                LocalDocumentReviewCandidateDecision.review_revision_id
                == source.id,
            ),
        )
        .where(LocalDocumentCandidate.review_session_id == review.id)
    ).all()
    candidates = {candidate.id: candidate for candidate, _ in candidate_decision_rows}
    decisions = {
        decision.candidate_id: decision
        for _, decision in candidate_decision_rows
        if decision is not None
    }
    if set(candidates) != set(decisions):
        raise DocumentImportError("incomplete_candidate_decisions")
    selected_ids = tuple(
        sorted(
            (
                candidate_id
                for candidate_id, row in decisions.items()
                if row.decision == "selected"
                and candidates[candidate_id].candidate_kind in {"fact", "event"}
            ),
            key=str,
        )
    )
    if not 1 <= len(selected_ids) <= 200:
        raise DocumentImportError("nonempty_acceptance_required")
    supplied_ids = tuple(request.selected_candidate_ids)
    supplied_fingerprints = tuple(request.selected_decision_fingerprints)
    exact_fingerprints = tuple(decisions[value].decision_fingerprint_sha256 for value in selected_ids)
    if supplied_ids != selected_ids or supplied_fingerprints != exact_fingerprints:
        raise DocumentImportError("selected_candidate_snapshot_mismatch")
    document = candidates.get(source.document_identity_candidate_id)
    subject = candidates.get(source.subject_candidate_id)
    if (
        document is None
        or subject is None
        or document.candidate_kind != "document_identity"
        or subject.candidate_kind != "company_identity"
        or decisions[document.id].decision != "selected"
        or decisions[subject.id].decision != "selected"
    ):
        raise DocumentImportError("selected_identities_required")
    import_graph = session.execute(
        select(LocalDocumentImportAttempt, LocalDocumentContent)
        .join(
            LocalDocumentContent,
            LocalDocumentImportAttempt.content_id == LocalDocumentContent.id,
        )
        .where(LocalDocumentImportAttempt.id == review.import_attempt_id)
    ).one_or_none()
    if import_graph is None:
        raise DocumentImportError("review_graph_invalid")
    review_attempt, content = import_graph
    document_payload = json.loads(document.candidate_payload_json)
    claim_keys = [decisions[value].claim_key for value in selected_ids]
    evidence_fingerprints = [
        _evidence_fingerprint(content, candidates[value]) for value in selected_ids
    ]
    conflicts = session.execute(
        select(
            literal("claim").label("conflict_kind"),
            Claim.claim_key.label("conflict_value"),
        )
        .where(
            Claim.case_id == review.target_research_case_id,
            Claim.claim_key.in_(claim_keys),
        )
        .union_all(
            select(
                literal("evidence").label("conflict_kind"),
                EvidenceItem.content_fingerprint.label("conflict_value"),
            ).where(
                EvidenceItem.case_id == review.target_research_case_id,
                EvidenceItem.content_fingerprint.in_(evidence_fingerprints),
            )
        )
    ).all()
    existing_claim_keys = {
        value for kind, value in conflicts if kind == "claim"
    }
    existing_evidence_fingerprints = {
        value for kind, value in conflicts if kind == "evidence"
    }
    for candidate_id in selected_ids:
        candidate = candidates[candidate_id]
        decision = decisions[candidate_id]
        if decision.claim_operation != "create_new_deterministic_claim":
            raise DocumentImportError("claim_operation_mismatch")
        if decision.claim_key != f"local-document-v1:{candidate.candidate_fingerprint_sha256}":
            raise DocumentImportError("claim_key_mismatch")
        if decision.claim_status == "supported" and (
            decision.evidence_relation != "supports" or source.evidence_grade == "D"
        ):
            raise DocumentImportError("supported_claim_evidence_invalid")
        if decision.claim_status == "disputed" and decision.evidence_relation != "contradicts":
            raise DocumentImportError("disputed_claim_evidence_invalid")
        if candidate.candidate_kind == "event":
            event_date = date.fromisoformat(json.loads(candidate.candidate_payload_json)["event_date"])
            if event_date > source.information_date:
                raise DocumentImportError("event_date_exceeds_information_date")
        evidence_fp = _evidence_fingerprint(content, candidate)
        if (
            decision.claim_key in existing_claim_keys
            or evidence_fp in existing_evidence_fingerprints
        ):
            raise DocumentImportError("previously_accepted_candidate_conflict")
    plan_shape = {
        "contract": ACCEPTANCE_CONTRACT_VERSION,
        "source_review_revision_id": source.id,
        "source_review_fingerprint_sha256": source.review_fingerprint_sha256,
        "expected_session_latest_revision_number": request.expected_session_latest_revision_number,
        "target_research_case_id": review.target_research_case_id,
        "content_id": content.id,
        "content_sha256": content.content_sha256,
        "extractor_contract_version": content.extractor_contract_version,
        "document_identity_candidate_fingerprint": document.candidate_fingerprint_sha256,
        "subject_candidate_fingerprint": subject.candidate_fingerprint_sha256,
        "source_kind": source.source_kind,
        "evidence_grade": source.evidence_grade,
        "information_date": source.information_date,
        "selected": [
            {
                "candidate_fingerprint": candidates[value].candidate_fingerprint_sha256,
                "decision_fingerprint": decisions[value].decision_fingerprint_sha256,
                "claim_key": decisions[value].claim_key,
                "claim_status": decisions[value].claim_status,
                "evidence_relation": decisions[value].evidence_relation,
                "evidence_fingerprint": _evidence_fingerprint(content, candidates[value]),
            }
            for value in selected_ids
        ],
    }
    return {
        "source": source,
        "review": review,
        "candidates": candidates,
        "decisions": decisions,
        "selected_ids": selected_ids,
        "content": content,
        "document_payload": document_payload,
        "accepted_at": accepted_at,
        "plan_fingerprint": fingerprint(plan_shape),
    }


def _evidence_fingerprint(
    content: LocalDocumentContent, candidate: LocalDocumentCandidate
) -> str:
    return fingerprint(
        {
            "contract": EVIDENCE_FINGERPRINT_CONTRACT,
            "document_content_sha256": content.content_sha256,
            "page_number": candidate.page_number,
            "start_utf8_byte": candidate.start_utf8_byte,
            "end_utf8_byte": candidate.end_utf8_byte,
            "quote_sha256": candidate.quote_sha256,
            "candidate_kind": candidate.candidate_kind,
            "reviewed_statement": candidate.statement,
        }
    )


def _acceptance_request_fingerprint(
    request: AcceptanceInput, plan_fingerprint: str
) -> str:
    return fingerprint(
        {
            "source_review_revision_id": request.source_review_revision_id,
            "expected_source_review_revision_number": request.expected_source_review_revision_number,
            "expected_source_review_fingerprint_sha256": request.expected_source_review_fingerprint_sha256,
            "expected_session_latest_revision_number": request.expected_session_latest_revision_number,
            "target_research_case_id": request.target_research_case_id,
            "selected_candidate_ids": request.selected_candidate_ids,
            "selected_decision_fingerprints": request.selected_decision_fingerprints,
            "recorded_at_utc": request.recorded_at_utc,
            "acceptance_contract_version": request.acceptance_contract_version,
            "acceptance_plan_fingerprint_sha256": plan_fingerprint,
        }
    )


def _stored_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class DocumentImportCommandService(_DocumentImportBase):
    """Complete pre-acceptance command owner."""

    def create_review_session(
        self,
        *,
        import_attempt_id: UUID,
        target_research_case_id: UUID,
        created_at_utc: datetime | None = None,
    ) -> LocalDocumentReviewSession:
        recorded = utc_timestamp(created_at_utc)
        with self._session_factory.begin() as session:
            attempt = session.get(LocalDocumentImportAttempt, import_attempt_id)
            if attempt is None or attempt.content_id is None or attempt.admission_state == "rejected":
                raise DocumentImportError("import_not_reviewable")
            if session.get(ResearchCase, target_research_case_id) is None:
                raise DocumentImportError("research_case_not_found")
            existing = session.scalar(
                select(LocalDocumentReviewSession).where(
                    LocalDocumentReviewSession.import_attempt_id == import_attempt_id,
                    LocalDocumentReviewSession.target_research_case_id
                    == target_research_case_id,
                )
            )
            if existing is not None:
                return existing
            review = LocalDocumentReviewSession(
                import_attempt_id=import_attempt_id,
                target_research_case_id=target_research_case_id,
                created_at_utc=recorded,
            )
            session.add(review)
            session.flush()
            return review

    def add_candidate(
        self, review_session_id: UUID, candidate_input: CandidateInput
    ) -> LocalDocumentCandidate:
        kind = candidate_input.candidate_kind
        if kind not in CANDIDATE_KINDS:
            raise DocumentImportError("invalid_candidate_kind")
        with self._session_factory.begin() as session:
            review = session.get(LocalDocumentReviewSession, review_session_id)
            if review is None:
                raise DocumentImportError("review_session_not_found")
            latest_state = session.scalar(
                select(LocalDocumentReviewRevision.review_state)
                .where(
                    LocalDocumentReviewRevision.review_session_id
                    == review_session_id
                )
                .order_by(LocalDocumentReviewRevision.revision_number.desc())
                .limit(1)
            )
            if latest_state in {"accepted", "rejected"}:
                raise DocumentImportError("review_terminal")
            count = session.scalar(
                select(func.count(LocalDocumentCandidate.id)).where(
                    LocalDocumentCandidate.review_session_id == review_session_id
                )
            )
            if (count or 0) >= MAX_CANDIDATES:
                raise DocumentImportError("candidate_limit_exceeded")
            attempt = session.get(LocalDocumentImportAttempt, review.import_attempt_id)
            if attempt is None or attempt.content_id is None:
                raise DocumentImportError("review_graph_invalid")
            content = session.get(LocalDocumentContent, attempt.content_id)
            if content is None:
                raise DocumentImportError("review_graph_invalid")
            payload = self._validated_payload(
                session, kind, candidate_input.payload, content.id
            )
            candidate_recorded = utc_timestamp(candidate_input.recorded_at_utc)
            if candidate_recorded < _stored_utc(review.created_at_utc):
                raise DocumentImportError("candidate_chronology_invalid")
            page_number = start = end = None
            quote_text = quote_sha = statement = None
            if kind in {"fact", "event"}:
                page_number = candidate_input.page_number
                start = candidate_input.start_utf8_byte
                end = candidate_input.end_utf8_byte
                if page_number is None or start is None or end is None:
                    raise DocumentImportError("citation_required")
                page = session.scalar(
                    select(LocalDocumentPage).where(
                        LocalDocumentPage.content_id == content.id,
                        LocalDocumentPage.page_number == page_number,
                    )
                )
                if page is None:
                    raise DocumentImportError("page_not_found")
                quote_text = candidate_input.quote_text or ""
                quote_sha = validate_sha256(
                    candidate_input.quote_sha256 or "", "quote_sha256"
                )
                raw = page.extracted_text.encode("utf-8")
                if not (0 <= start < end <= len(raw)):
                    raise DocumentImportError("citation_span_invalid")
                try:
                    exact_quote = raw[start:end].decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise DocumentImportError("citation_span_invalid") from exc
                if exact_quote != quote_text or sha256_hex(quote_text.encode("utf-8")) != quote_sha:
                    raise DocumentImportError("citation_quote_mismatch")
                statement = bounded_text(candidate_input.statement or "", "statement", 4000)
                payload = self._validated_fact_payload(kind, payload, review)
            candidate_shape = {
                "contract": "aquantai.local-document-candidate.v1",
                "content_id": content.id,
                "content_sha256": content.content_sha256,
                "extractor_contract_version": content.extractor_contract_version,
                "candidate_kind": kind,
                "page_number": page_number,
                "start_utf8_byte": start,
                "end_utf8_byte": end,
                "quote_sha256": quote_sha,
                "statement": statement,
                "payload": payload,
            }
            candidate = LocalDocumentCandidate(
                review_session_id=review.id,
                candidate_kind=kind,
                page_number=page_number,
                start_utf8_byte=start,
                end_utf8_byte=end,
                quote_text=quote_text,
                quote_sha256=quote_sha,
                statement=statement,
                candidate_payload_json=canonical_json(payload),
                candidate_fingerprint_sha256=fingerprint(candidate_shape),
                recorded_at_utc=candidate_recorded,
            )
            session.add(candidate)
            session.flush()
            return candidate

    def append_review_revision(
        self, review_session_id: UUID, revision_input: ReviewRevisionInput
    ) -> LocalDocumentReviewRevision:
        if revision_input.review_state not in REVIEW_STATES:
            raise DocumentImportError("review_state_not_user_writable")
        if revision_input.source_kind not in SOURCE_KINDS:
            raise DocumentImportError("invalid_source_kind")
        if revision_input.evidence_grade not in EVIDENCE_GRADES:
            raise DocumentImportError("invalid_evidence_grade")
        recorded = utc_timestamp(revision_input.recorded_at_utc)
        with self._session_factory.begin() as session:
            review = session.scalar(
                select(LocalDocumentReviewSession)
                .where(LocalDocumentReviewSession.id == review_session_id)
                .with_for_update()
            )
            if review is None:
                raise DocumentImportError("review_session_not_found")
            latest = session.scalar(
                select(LocalDocumentReviewRevision)
                .where(LocalDocumentReviewRevision.review_session_id == review.id)
                .order_by(LocalDocumentReviewRevision.revision_number.desc())
                .limit(1)
            )
            latest_number = latest.revision_number if latest else 0
            if latest_number != revision_input.expected_previous_revision_number:
                raise DocumentImportError("review_revision_conflict")
            if latest is not None and latest.review_state in {"accepted", "rejected"}:
                raise DocumentImportError("review_terminal")
            if recorded < _stored_utc(review.created_at_utc) or (
                latest is not None and recorded < _stored_utc(latest.recorded_at_utc)
            ):
                raise DocumentImportError("review_chronology_invalid")
            if revision_input.information_date > recorded.date():
                raise DocumentImportError("information_date_after_recording")
            candidates = list(
                session.scalars(
                    select(LocalDocumentCandidate).where(
                        LocalDocumentCandidate.review_session_id == review.id
                    )
                )
            )
            by_id = {row.id: row for row in candidates}
            if set(by_id) != {decision.candidate_id for decision in revision_input.decisions}:
                raise DocumentImportError("incomplete_candidate_decisions")
            document = by_id.get(revision_input.document_identity_candidate_id)
            subject = by_id.get(revision_input.subject_candidate_id)
            if document is None or document.candidate_kind != "document_identity":
                raise DocumentImportError("document_identity_required")
            if subject is None or subject.candidate_kind != "company_identity":
                raise DocumentImportError("subject_identity_required")
            normalized = self._normalized_decisions(by_id, revision_input.decisions)
            if normalized[document.id]["decision"] != "selected" or normalized[subject.id]["decision"] != "selected":
                raise DocumentImportError("selected_identities_required")
            document_date = date.fromisoformat(
                json.loads(document.candidate_payload_json)["document_date"]
            )
            if document_date > revision_input.information_date:
                raise DocumentImportError("document_date_exceeds_information_date")
            revision_number = latest_number + 1
            reviewer_note = bounded_text(
                revision_input.reviewer_note or "",
                "reviewer_note",
                2000,
                optional=True,
            )
            review_shape = {
                "contract": "aquantai.local-document-review.v1",
                "review_session_id": review.id,
                "revision_number": revision_number,
                "review_state": revision_input.review_state,
                "source_kind": revision_input.source_kind,
                "evidence_grade": revision_input.evidence_grade,
                "document_identity_candidate_id": document.id,
                "subject_candidate_id": subject.id,
                "information_date": revision_input.information_date,
                "reviewer_note": reviewer_note,
                "candidate_decisions": [normalized[key] for key in sorted(normalized, key=str)],
            }
            revision = LocalDocumentReviewRevision(
                review_session_id=review.id,
                revision_number=revision_number,
                review_state=revision_input.review_state,
                review_fingerprint_sha256=fingerprint(review_shape),
                expected_previous_revision_number=revision_input.expected_previous_revision_number,
                source_kind=revision_input.source_kind,
                evidence_grade=revision_input.evidence_grade,
                document_identity_candidate_id=document.id,
                subject_candidate_id=subject.id,
                information_date=revision_input.information_date,
                reviewer_note=reviewer_note,
                recorded_at_utc=recorded,
                supersedes_review_revision_id=latest.id if latest else None,
            )
            session.add(revision)
            session.flush()
            session.add_all(
                LocalDocumentReviewCandidateDecision(
                    review_revision_id=revision.id,
                    candidate_id=candidate_id,
                    decision=value["decision"],
                    claim_operation=value["claim_operation"],
                    claim_key=value["claim_key"],
                    claim_status=value["claim_status"],
                    evidence_relation=value["evidence_relation"],
                    decision_fingerprint_sha256=fingerprint(value),
                )
                for candidate_id, value in normalized.items()
            )
            session.flush()
            return revision

    @staticmethod
    def _validated_payload(
        session: Session,
        kind: str,
        payload: dict[str, object],
        current_content_id: UUID,
    ) -> dict[str, object]:
        if kind == "document_identity":
            result = validate_document_identity_payload(payload)
            prior = result.get("supersedes_document_content_id")
            if prior is not None and session.get(LocalDocumentContent, UUID(str(prior))) is None:
                raise DocumentImportError("superseded_content_not_found")
            if prior is not None and UUID(str(prior)) == current_content_id:
                raise DocumentImportError("superseded_content_must_differ")
            return result
        if kind == "company_identity":
            result = validate_company_identity_payload(payload)
            instrument = result.get("listed_instrument_id")
            if instrument is not None and session.get(ListedInstrument, UUID(str(instrument))) is None:
                raise DocumentImportError("listed_instrument_not_found")
            return result
        return dict(payload)

    @staticmethod
    def _validated_fact_payload(
        kind: str, payload: dict[str, object], review: LocalDocumentReviewSession
    ) -> dict[str, object]:
        expected = {"event_date"} if kind == "event" else set()
        if set(payload) - expected:
            raise DocumentImportError("candidate_payload_unknown_field")
        if kind == "event":
            if payload.get("event_date") is None:
                raise DocumentImportError("event_date_required")
            try:
                event_date = date.fromisoformat(str(payload["event_date"]))
            except ValueError as exc:
                raise DocumentImportError("invalid_event_date") from exc
            return {"event_date": event_date.isoformat()}
        return {}

    @staticmethod
    def _normalized_decisions(
        by_id: dict[UUID, LocalDocumentCandidate], decisions: tuple[DecisionInput, ...]
    ) -> dict[UUID, dict[str, object]]:
        result: dict[UUID, dict[str, object]] = {}
        for spec in decisions:
            candidate = by_id[spec.candidate_id]
            if spec.decision not in DECISIONS:
                raise DocumentImportError("invalid_candidate_decision")
            semantic = candidate.candidate_kind in {"fact", "event"}
            selected = semantic and spec.decision == "selected"
            if selected:
                if spec.claim_status not in CLAIM_STATUSES:
                    raise DocumentImportError("claim_status_required")
                if spec.evidence_relation not in EVIDENCE_RELATIONS:
                    raise DocumentImportError("evidence_relation_required")
            elif spec.claim_status is not None or spec.evidence_relation is not None:
                raise DocumentImportError("claim_fields_forbidden")
            result[candidate.id] = {
                "candidate_id": candidate.id,
                "candidate_fingerprint_sha256": candidate.candidate_fingerprint_sha256,
                "decision": spec.decision,
                "claim_operation": "create_new_deterministic_claim" if selected else None,
                "claim_key": (
                    f"local-document-v1:{candidate.candidate_fingerprint_sha256}"
                    if selected
                    else None
                ),
                "claim_status": spec.claim_status if selected else None,
                "evidence_relation": spec.evidence_relation if selected else None,
            }
        return result
