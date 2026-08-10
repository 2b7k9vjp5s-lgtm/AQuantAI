"""Fail-closed Research Evidence Pack v1 query projection."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.document_import_contracts import ACCEPTANCE_CONTRACT_VERSION
from industry_alpha.document_import_rules import fingerprint, sha256_hex
from industry_alpha.research_evidence_pack_contracts import (
    CONTRACT_VERSION,
    EvidencePackRequest,
    MEMBERSHIP_LINKED,
    MEMBERSHIP_UNLINKED,
    ResearchEvidencePackError,
    ResearchEvidencePackResult,
)
from industry_alpha.research_evidence_pack_repository import ResearchEvidencePackRepository
from industry_alpha.research_evidence_pack_rules import (
    candidate_payload,
    decode_cursor,
    encode_cursor,
    membership_summary,
    normalized_decision,
    rebuild_acceptance_plan_fingerprint,
    rebuild_acceptance_request_fingerprint,
    rebuild_accepted_review_fingerprint,
    rebuild_candidate_fingerprint,
    rebuild_evidence_fingerprint,
    rebuild_source_review_fingerprint,
    requested_utc,
    stored_utc,
    utc_text,
)


_CLAIM_STATUSES = {"draft", "supported", "disputed", "rejected"}
_EVIDENCE_RELATIONS = {"supports", "contradicts", "context"}
_DECISIONS = {"selected", "rejected", "deferred"}


def _fail() -> None:
    raise ResearchEvidencePackError("evidence_pack_integrity_error")


def _uuid(value: UUID | None) -> str | None:
    return str(value) if value is not None else None


def _evidence_dict(item: Any, supersession_reference: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "evidence_id": str(item.id),
        "evidence_grade": item.evidence_grade,
        "source_kind": item.source_kind,
        "source_title": item.source_title,
        "publisher_or_author": item.publisher_or_author,
        "source_locator": item.source_locator,
        "information_date": item.information_date.isoformat(),
        "recorded_at_utc": utc_text(item.recorded_at_utc),
        "summary": item.summary,
        "content_fingerprint": item.content_fingerprint,
        "supersedes_evidence_id": _uuid(item.supersedes_evidence_id),
        "supersession_reference": supersession_reference,
    }


def _claim_dict(item: Any) -> dict[str, Any]:
    return {
        "claim_id": str(item.id),
        "claim_key": item.claim_key,
        "created_at_utc": utc_text(item.created_at_utc),
    }


def _claim_revision_dict(item: Any, supersession_reference: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "claim_revision_id": str(item.id),
        "revision_no": item.revision_no,
        "statement": item.statement,
        "claim_kind": item.claim_kind,
        "claim_status": item.claim_status,
        "inference_confidence": item.inference_confidence,
        "inference_basis": item.inference_basis,
        "information_cutoff_date": item.information_cutoff_date.isoformat(),
        "recorded_at_utc": utc_text(item.recorded_at_utc),
        "supersedes_revision_id": _uuid(item.supersedes_revision_id),
        "supersession_reference": supersession_reference,
    }


def _case_dict(item: Any) -> dict[str, Any]:
    return {
        "research_case_id": str(item.id),
        "case_key": item.case_key,
        "origin": item.origin,
        "created_at_utc": utc_text(item.created_at_utc),
    }


def _case_revision_dict(item: Any) -> dict[str, Any]:
    return {
        "research_case_revision_id": str(item.id),
        "revision_no": item.revision_no,
        "title": item.title,
        "research_question": item.research_question,
        "summary": item.summary,
        "workflow_state": item.workflow_state,
        "conclusion_status": item.conclusion_status,
        "information_cutoff_date": item.information_cutoff_date.isoformat(),
        "recorded_at_utc": utc_text(item.recorded_at_utc),
        "supersedes_revision_id": _uuid(item.supersedes_revision_id),
    }


class ResearchEvidencePackQueryService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_pack(self, request: EvidencePackRequest) -> ResearchEvidencePackResult:
        if not 1 <= request.limit <= 100:
            raise ResearchEvidencePackError("invalid_evidence_pack_cursor" if request.cursor else "invalid_evidence_pack_as_of")
        recorded = requested_utc(request.recorded_at_utc)
        if request.information_cutoff_date > recorded.date():
            raise ResearchEvidencePackError("invalid_evidence_pack_as_of")
        cursor = decode_cursor(request)

        with self._session_factory() as session:
            repo = ResearchEvidencePackRepository(session)
            anchor = repo.load_anchor(request.research_case_id, request.research_case_revision_id)
            if anchor is None:
                raise ResearchEvidencePackError("research_case_not_found")
            case_row, revision = anchor
            if revision is None:
                raise ResearchEvidencePackError("research_case_revision_not_found")
            if revision.case_id != case_row.id:
                raise ResearchEvidencePackError("research_case_revision_mismatch")
            if (
                stored_utc(case_row.created_at_utc) > recorded
                or revision.information_cutoff_date > request.information_cutoff_date
                or stored_utc(revision.recorded_at_utc) > recorded
            ):
                raise ResearchEvidencePackError("research_case_revision_not_visible_as_of")

            visible_count, remaining_count = repo.evidence_counts(
                case_id=case_row.id,
                information_cutoff_date=request.information_cutoff_date,
                recorded_at_utc=recorded,
                cursor=cursor,
            )
            evidence_page = repo.evidence_page(
                case_id=case_row.id,
                information_cutoff_date=request.information_cutoff_date,
                recorded_at_utc=recorded,
                limit=request.limit,
                cursor=cursor,
            )
            evidence_ids = tuple(row.id for row in evidence_page)
            evidence_by_id = {row.id: row for row in evidence_page}

            raw_bindings = repo.claim_bindings(evidence_ids, recorded_at_utc=recorded)
            visible_bindings: list[tuple[Any, Any, Any]] = []
            for link, claim_revision, claim in raw_bindings:
                evidence = evidence_by_id.get(link.evidence_id)
                if evidence is None:
                    _fail()
                if claim.case_id != case_row.id or claim_revision.claim_id != claim.id:
                    _fail()
                if stored_utc(claim.created_at_utc) > stored_utc(claim_revision.recorded_at_utc):
                    _fail()
                if (
                    stored_utc(link.recorded_at_utc) < stored_utc(claim_revision.recorded_at_utc)
                    or stored_utc(link.recorded_at_utc) < stored_utc(evidence.recorded_at_utc)
                ):
                    _fail()
                if (
                    claim_revision.information_cutoff_date > request.information_cutoff_date
                    or stored_utc(claim_revision.recorded_at_utc) > recorded
                    or stored_utc(claim.created_at_utc) > recorded
                ):
                    continue
                visible_bindings.append((link, claim_revision, claim))

            claim_revision_ids = tuple(sorted({row[1].id for row in visible_bindings}, key=str))
            roles = repo.selected_roles(
                case_revision_id=revision.id,
                claim_revision_ids=claim_revision_ids,
                recorded_at_utc=recorded,
            )
            roles_by_revision: dict[UUID, list[Any]] = defaultdict(list)
            for role in roles:
                if role.case_revision_id != revision.id or role.claim_revision_id not in claim_revision_ids:
                    _fail()
                roles_by_revision[role.claim_revision_id].append(role)
            for values in roles_by_revision.values():
                values.sort(key=lambda row: (row.role, str(row.id)))

            receipt_rows = repo.receipt_graph(evidence_ids)
            provenance, citation_checks = self._validate_receipt_graphs(
                receipt_rows,
                case_id=case_row.id,
                information_cutoff_date=request.information_cutoff_date,
                recorded_at_utc=recorded,
            )
            page_keys = tuple(
                sorted(
                    {(content.id, candidate.page_number) for content, candidate in citation_checks},
                    key=lambda value: (str(value[0]), value[1]),
                )
            )
            pages = repo.citation_pages(page_keys)
            self._validate_citation_pages(pages, citation_checks)

            evidence_target_ids = tuple(
                sorted(
                    {row.supersedes_evidence_id for row in evidence_page if row.supersedes_evidence_id is not None},
                    key=str,
                )
            )
            claim_target_ids = tuple(
                sorted(
                    {row[1].supersedes_revision_id for row in visible_bindings if row[1].supersedes_revision_id is not None},
                    key=str,
                )
            )
            target_rows = repo.supersession_targets(
                evidence_target_ids=evidence_target_ids,
                claim_revision_target_ids=claim_target_ids,
            )
            evidence_supersession, claim_supersession = self._validate_supersession(
                target_rows,
                evidence_page=evidence_page,
                visible_bindings=visible_bindings,
                case_id=case_row.id,
                information_cutoff_date=request.information_cutoff_date,
                recorded_at_utc=recorded,
            )

            bindings_by_evidence: dict[UUID, list[tuple[Any, Any, Any]]] = defaultdict(list)
            for binding in visible_bindings:
                bindings_by_evidence[binding[0].evidence_id].append(binding)
            for values in bindings_by_evidence.values():
                values.sort(
                    key=lambda row: (
                        row[2].claim_key,
                        row[1].revision_no,
                        row[0].relation,
                        str(row[1].id),
                    )
                )

            entries: list[dict[str, Any]] = []
            for evidence in evidence_page:
                claim_bindings: list[dict[str, Any]] = []
                states: list[str] = []
                for link, claim_revision, claim in bindings_by_evidence.get(evidence.id, []):
                    selected_roles = roles_by_revision.get(claim_revision.id, [])
                    state = MEMBERSHIP_LINKED if selected_roles else MEMBERSHIP_UNLINKED
                    states.append(state)
                    claim_bindings.append(
                        {
                            "claim": _claim_dict(claim),
                            "claim_revision": _claim_revision_dict(
                                claim_revision, claim_supersession.get(claim_revision.id)
                            ),
                            "claim_evidence_link": {
                                "claim_evidence_link_id": str(link.id),
                                "evidence_id": str(link.evidence_id),
                                "claim_revision_id": str(link.claim_revision_id),
                                "relation": link.relation,
                                "link_note": link.link_note,
                                "recorded_at_utc": utc_text(link.recorded_at_utc),
                            },
                            "relation": link.relation,
                            "research_membership_state": state,
                            "selected_case_revision_roles": [
                                {
                                    "case_revision_claim_link_id": str(role.id),
                                    "role": role.role,
                                    "recorded_at_utc": utc_text(role.recorded_at_utc),
                                }
                                for role in selected_roles
                            ],
                            "supersession_reference": claim_supersession.get(claim_revision.id),
                        }
                    )
                local = provenance.get(evidence.id)
                entries.append(
                    {
                        "evidence": _evidence_dict(
                            evidence, evidence_supersession.get(evidence.id)
                        ),
                        "claim_bindings": claim_bindings,
                        "membership_summary": membership_summary(states),
                        "local_document_provenance": local,
                        "integrity_state": "validated_local_document" if local else "ledger_only",
                    }
                )

            next_cursor = None
            if evidence_page and remaining_count > len(evidence_page):
                next_cursor = encode_cursor(request, evidence_page[-1])
            payload: dict[str, Any] = {
                "contract_version": CONTRACT_VERSION,
                "research_case": _case_dict(case_row),
                "selected_case_revision": _case_revision_dict(revision),
                "information_cutoff_date": request.information_cutoff_date.isoformat(),
                "recorded_at_boundary_utc": utc_text(recorded),
                "visible_evidence_count": visible_count,
                "entries": entries,
                "next_cursor": next_cursor,
                "notices": {
                    "read_only": True,
                    "membership_authority": "per_claim_binding",
                    "writes_per_get": 0,
                    "network_calls": 0,
                    "ocr_calls": 0,
                    "ai_calls": 0,
                },
            }
            if visible_count == 0:
                payload["state"] = "empty_evidence_pack"
            return ResearchEvidencePackResult(payload)

    @staticmethod
    def _validate_receipt_graphs(
        rows: tuple[object, ...],
        *,
        case_id: UUID,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
    ) -> tuple[dict[UUID, dict[str, Any]], list[tuple[Any, Any]]]:
        groups: dict[UUID, list[object]] = defaultdict(list)
        for row in rows:
            groups[row[0]].append(row)
        provenance: dict[UUID, dict[str, Any]] = {}
        citation_checks: list[tuple[Any, Any]] = []

        for discovered_id, group in groups.items():
            first = group[0]
            (
                _discovered,
                receipt,
                review,
                attempt,
                content,
                source,
                accepted,
                predecessor,
                _candidate,
                _source_decision,
                _accepted_decision,
                _sibling_link,
                _ledger_evidence,
                _ledger_claim,
                _ledger_revision,
                _ledger_relation,
                max_revision_number,
                link_count,
            ) = first
            if receipt is None or receipt.id != discovered_id:
                _fail()
            if review is None or attempt is None or content is None or source is None or accepted is None:
                _fail()
            if (
                receipt.review_session_id != review.id
                or source.review_session_id != review.id
                or accepted.review_session_id != review.id
                or receipt.source_review_revision_id != source.id
                or receipt.accepted_review_revision_id != accepted.id
                or receipt.target_research_case_id != case_id
                or review.target_research_case_id != case_id
                or attempt.id != review.import_attempt_id
                or attempt.content_id != content.id
                or attempt.content_sha256 != content.content_sha256
            ):
                _fail()
            if (
                receipt.acceptance_contract_version != ACCEPTANCE_CONTRACT_VERSION
                or receipt.source_review_fingerprint_sha256 != source.review_fingerprint_sha256
                or receipt.accepted_review_fingerprint_sha256 != accepted.review_fingerprint_sha256
                or stored_utc(source.recorded_at_utc) > stored_utc(receipt.accepted_at_utc)
                or stored_utc(receipt.accepted_at_utc) > recorded_at_utc
                or accepted.information_date > information_cutoff_date
            ):
                _fail()
            if source.review_state not in {"draft", "deferred"} or accepted.review_state != "accepted":
                _fail()

            if source.revision_number == 1:
                if (
                    source.expected_previous_revision_number != 0
                    or source.supersedes_review_revision_id is not None
                    or predecessor is not None
                ):
                    _fail()
            else:
                if (
                    source.expected_previous_revision_number != source.revision_number - 1
                    or source.supersedes_review_revision_id is None
                    or predecessor is None
                    or predecessor.id != source.supersedes_review_revision_id
                    or predecessor.review_session_id != review.id
                    or predecessor.revision_number != source.revision_number - 1
                    or stored_utc(predecessor.recorded_at_utc) > stored_utc(source.recorded_at_utc)
                ):
                    _fail()
            if (
                accepted.revision_number != source.revision_number + 1
                or accepted.expected_previous_revision_number != source.revision_number
                or accepted.supersedes_review_revision_id != source.id
                or stored_utc(accepted.recorded_at_utc) != stored_utc(receipt.accepted_at_utc)
                or max_revision_number != accepted.revision_number
            ):
                _fail()
            for field in (
                "source_kind",
                "evidence_grade",
                "document_identity_candidate_id",
                "subject_candidate_id",
                "information_date",
                "reviewer_note",
            ):
                if getattr(accepted, field) != getattr(source, field):
                    _fail()

            candidates: dict[UUID, Any] = {}
            source_decisions: dict[UUID, Any] = {}
            accepted_decisions: dict[UUID, Any] = {}
            links: dict[UUID, tuple[Any, Any, Any, Any, Any]] = {}
            payloads: dict[UUID, dict[str, Any]] = {}
            for row in group:
                candidate = row[8]
                source_decision = row[9]
                accepted_decision = row[10]
                sibling_link = row[11]
                ledger_evidence = row[12]
                ledger_claim = row[13]
                ledger_revision = row[14]
                ledger_relation = row[15]
                if candidate is None or candidate.review_session_id != review.id:
                    _fail()
                candidates[candidate.id] = candidate
                if source_decision is None or accepted_decision is None:
                    _fail()
                source_decisions[candidate.id] = source_decision
                accepted_decisions[candidate.id] = accepted_decision
                if sibling_link is not None:
                    links[candidate.id] = (
                        sibling_link,
                        ledger_evidence,
                        ledger_claim,
                        ledger_revision,
                        ledger_relation,
                    )

            if not candidates or set(candidates) != set(source_decisions) or set(candidates) != set(accepted_decisions):
                _fail()
            if int(link_count or 0) != len(links):
                _fail()

            normalized_source: dict[UUID, dict[str, Any]] = {}
            normalized_accepted: dict[UUID, dict[str, Any]] = {}
            for candidate_id, candidate in candidates.items():
                payload = candidate_payload(candidate)
                payloads[candidate_id] = payload
                semantic = candidate.candidate_kind in {"fact", "event"}
                citation_fields = (
                    candidate.page_number,
                    candidate.start_utf8_byte,
                    candidate.end_utf8_byte,
                    candidate.quote_text,
                    candidate.quote_sha256,
                    candidate.statement,
                )
                if semantic:
                    if any(value is None for value in citation_fields):
                        _fail()
                    if not (0 <= candidate.start_utf8_byte < candidate.end_utf8_byte):
                        _fail()
                    if candidate.page_number < 1 or candidate.page_number > content.page_count:
                        _fail()
                elif any(value is not None for value in citation_fields):
                    _fail()
                if candidate.candidate_kind == "event":
                    if date.fromisoformat(payload["event_date"]) > source.information_date:
                        _fail()
                if rebuild_candidate_fingerprint(content, candidate, payload) != candidate.candidate_fingerprint_sha256:
                    _fail()

                source_decision = source_decisions[candidate_id]
                accepted_decision = accepted_decisions[candidate_id]
                if (
                    source_decision.candidate_id != candidate_id
                    or accepted_decision.candidate_id != candidate_id
                    or source_decision.review_revision_id != source.id
                    or accepted_decision.review_revision_id != accepted.id
                    or source_decision.decision not in _DECISIONS
                    or accepted_decision.decision not in _DECISIONS
                ):
                    _fail()
                source_value = normalized_decision(candidate, source_decision)
                accepted_value = normalized_decision(candidate, accepted_decision)
                if fingerprint(source_value) != source_decision.decision_fingerprint_sha256:
                    _fail()
                if fingerprint(accepted_value) != accepted_decision.decision_fingerprint_sha256:
                    _fail()
                if source_value != accepted_value or source_decision.decision_fingerprint_sha256 != accepted_decision.decision_fingerprint_sha256:
                    _fail()
                normalized_source[candidate_id] = source_value
                normalized_accepted[candidate_id] = accepted_value

                selected_semantic = semantic and source_decision.decision == "selected"
                claim_fields = (
                    source_decision.claim_operation,
                    source_decision.claim_key,
                    source_decision.claim_status,
                    source_decision.evidence_relation,
                )
                if selected_semantic:
                    if (
                        source_decision.claim_operation != "create_new_deterministic_claim"
                        or source_decision.claim_key != f"local-document-v1:{candidate.candidate_fingerprint_sha256}"
                        or source_decision.claim_status not in _CLAIM_STATUSES
                        or source_decision.evidence_relation not in _EVIDENCE_RELATIONS
                    ):
                        _fail()
                    if source_decision.claim_status == "supported" and (
                        source_decision.evidence_relation != "supports" or source.evidence_grade == "D"
                    ):
                        _fail()
                    if source_decision.claim_status == "disputed" and source_decision.evidence_relation != "contradicts":
                        _fail()
                elif any(value is not None for value in claim_fields):
                    _fail()

            document = candidates.get(source.document_identity_candidate_id)
            subject = candidates.get(source.subject_candidate_id)
            if (
                document is None
                or subject is None
                or document.candidate_kind != "document_identity"
                or subject.candidate_kind != "company_identity"
                or source_decisions[document.id].decision != "selected"
                or source_decisions[subject.id].decision != "selected"
            ):
                _fail()
            if date.fromisoformat(payloads[document.id]["document_date"]) > source.information_date:
                _fail()

            selected_ids = tuple(
                sorted(
                    (
                        candidate_id
                        for candidate_id, decision in source_decisions.items()
                        if decision.decision == "selected"
                        and candidates[candidate_id].candidate_kind in {"fact", "event"}
                    ),
                    key=str,
                )
            )
            if not 1 <= len(selected_ids) <= 200 or set(links) != set(selected_ids):
                _fail()

            source_fingerprint = rebuild_source_review_fingerprint(source, normalized_source)
            if (
                source_fingerprint != source.review_fingerprint_sha256
                or source_fingerprint != receipt.source_review_fingerprint_sha256
            ):
                _fail()
            plan_fingerprint = rebuild_acceptance_plan_fingerprint(
                source=source,
                review=review,
                content=content,
                document_candidate=document,
                subject_candidate=subject,
                candidates=candidates,
                decisions=source_decisions,
                selected_ids=selected_ids,
            )
            request_fingerprint = rebuild_acceptance_request_fingerprint(
                source=source,
                receipt=receipt,
                review=review,
                selected_ids=selected_ids,
                decisions=source_decisions,
                plan_fingerprint=plan_fingerprint,
            )
            if request_fingerprint != receipt.request_fingerprint_sha256:
                _fail()
            accepted_fingerprint = rebuild_accepted_review_fingerprint(
                source=source,
                accepted=accepted,
                receipt=receipt,
                request_fingerprint=request_fingerprint,
                plan_fingerprint=plan_fingerprint,
            )
            if (
                accepted_fingerprint != accepted.review_fingerprint_sha256
                or accepted_fingerprint != receipt.accepted_review_fingerprint_sha256
            ):
                _fail()

            document_payload = payloads[document.id]
            for candidate_id in selected_ids:
                candidate = candidates[candidate_id]
                decision = source_decisions[candidate_id]
                sibling_link, evidence, claim, claim_revision, relation = links[candidate_id]
                if any(value is None for value in (evidence, claim, claim_revision, relation)):
                    _fail()
                if (
                    sibling_link.receipt_id != receipt.id
                    or sibling_link.candidate_id != candidate.id
                    or sibling_link.evidence_item_id != evidence.id
                    or sibling_link.claim_id != claim.id
                    or sibling_link.claim_revision_id != claim_revision.id
                    or sibling_link.claim_evidence_link_id != relation.id
                    or evidence.case_id != case_id
                    or evidence.evidence_grade != source.evidence_grade
                    or evidence.source_kind != source.source_kind
                    or evidence.source_title != document_payload["document_title"]
                    or evidence.publisher_or_author != document_payload["publisher_or_author"]
                    or evidence.information_date != source.information_date
                    or stored_utc(evidence.recorded_at_utc) != stored_utc(receipt.accepted_at_utc)
                    or evidence.summary != candidate.statement
                    or evidence.content_fingerprint != rebuild_evidence_fingerprint(content, candidate)
                    or evidence.supersedes_evidence_id is not None
                ):
                    _fail()
                expected_locator = (
                    f"local-document:{content.id}#page={candidate.page_number}"
                    f"&start_utf8_byte={candidate.start_utf8_byte}"
                    f"&end_utf8_byte={candidate.end_utf8_byte}"
                )
                if evidence.source_locator != expected_locator:
                    _fail()
                if (
                    claim.case_id != case_id
                    or claim.claim_key != decision.claim_key
                    or stored_utc(claim.created_at_utc) != stored_utc(receipt.accepted_at_utc)
                    or claim_revision.claim_id != claim.id
                    or claim_revision.revision_no != 1
                    or claim_revision.statement != candidate.statement
                    or claim_revision.claim_kind != "fact"
                    or claim_revision.claim_status != decision.claim_status
                    or claim_revision.inference_confidence is not None
                    or claim_revision.inference_basis is not None
                    or claim_revision.information_cutoff_date != source.information_date
                    or stored_utc(claim_revision.recorded_at_utc) != stored_utc(receipt.accepted_at_utc)
                    or claim_revision.supersedes_revision_id is not None
                    or relation.claim_revision_id != claim_revision.id
                    or relation.evidence_id != evidence.id
                    or relation.relation != decision.evidence_relation
                    or relation.link_note is not None
                    or stored_utc(relation.recorded_at_utc) != stored_utc(receipt.accepted_at_utc)
                ):
                    _fail()
                citation_checks.append((content, candidate))
                provenance[evidence.id] = {
                    "receipt_id": str(receipt.id),
                    "review_session_id": str(review.id),
                    "source_review_revision_id": str(source.id),
                    "accepted_review_revision_id": str(accepted.id),
                    "content_id": str(content.id),
                    "content_sha256": content.content_sha256,
                    "extractor_contract_version": content.extractor_contract_version,
                    "candidate_id": str(candidate.id),
                    "page_number": candidate.page_number,
                    "start_utf8_byte": candidate.start_utf8_byte,
                    "end_utf8_byte": candidate.end_utf8_byte,
                    "quote_text": candidate.quote_text,
                    "quote_sha256": candidate.quote_sha256,
                    "candidate_fingerprint_sha256": candidate.candidate_fingerprint_sha256,
                    "decision_fingerprint_sha256": decision.decision_fingerprint_sha256,
                    "accepted_at_utc": utc_text(receipt.accepted_at_utc),
                }
        return provenance, citation_checks

    @staticmethod
    def _validate_citation_pages(
        pages: tuple[Any, ...], citation_checks: list[tuple[Any, Any]]
    ) -> None:
        page_by_key = {(row.content_id, row.page_number): row for row in pages}
        expected_keys = {(content.id, candidate.page_number) for content, candidate in citation_checks}
        if set(page_by_key) != expected_keys:
            _fail()
        for content, candidate in citation_checks:
            page = page_by_key[(content.id, candidate.page_number)]
            if (
                page.content_id != content.id
                or page.text_sha256 != sha256_hex(page.extracted_text.encode("utf-8"))
                or page.text_char_count != len(page.extracted_text)
            ):
                _fail()
            raw = page.extracted_text.encode("utf-8")
            if not (0 <= candidate.start_utf8_byte < candidate.end_utf8_byte <= len(raw)):
                _fail()
            try:
                exact_quote = raw[candidate.start_utf8_byte:candidate.end_utf8_byte].decode("utf-8")
            except UnicodeDecodeError:
                _fail()
            if (
                exact_quote != candidate.quote_text
                or sha256_hex(exact_quote.encode("utf-8")) != candidate.quote_sha256
            ):
                _fail()

    @staticmethod
    def _validate_supersession(
        target_rows: tuple[object, ...],
        *,
        evidence_page: tuple[Any, ...],
        visible_bindings: list[tuple[Any, Any, Any]],
        case_id: UUID,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
    ) -> tuple[dict[UUID, dict[str, Any]], dict[UUID, dict[str, Any]]]:
        targets = {(row.kind, row.id): row for row in target_rows}
        evidence_result: dict[UUID, dict[str, Any]] = {}
        claim_result: dict[UUID, dict[str, Any]] = {}
        for successor in evidence_page:
            if successor.supersedes_evidence_id is None:
                continue
            target = targets.get(("evidence", successor.supersedes_evidence_id))
            if (
                target is None
                or target.owner_id != case_id
                or stored_utc(target.recorded_at_utc) > stored_utc(successor.recorded_at_utc)
            ):
                _fail()
            visible = target.information_date <= information_cutoff_date and stored_utc(target.recorded_at_utc) <= recorded_at_utc
            evidence_result[successor.id] = {
                "evidence_id": str(target.id),
                "visibility_state": "visible_as_of" if visible else "not_visible_as_of",
            }
        seen_claims: set[UUID] = set()
        for _link, successor, claim in visible_bindings:
            if successor.id in seen_claims or successor.supersedes_revision_id is None:
                continue
            seen_claims.add(successor.id)
            target = targets.get(("claim_revision", successor.supersedes_revision_id))
            if (
                target is None
                or target.owner_id != claim.id
                or target.revision_no != successor.revision_no - 1
                or stored_utc(target.recorded_at_utc) > stored_utc(successor.recorded_at_utc)
            ):
                _fail()
            visible = target.information_date <= information_cutoff_date and stored_utc(target.recorded_at_utc) <= recorded_at_utc
            claim_result[successor.id] = {
                "claim_revision_id": str(target.id),
                "visibility_state": "visible_as_of" if visible else "not_visible_as_of",
            }
        return evidence_result, claim_result
