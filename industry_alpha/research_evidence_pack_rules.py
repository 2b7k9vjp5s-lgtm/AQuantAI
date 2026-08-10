"""Deterministic rules for Research Evidence Pack v1."""

from __future__ import annotations

import base64
from datetime import date, datetime, timezone
import json
from typing import Any
from uuid import UUID

from industry_alpha.document_import_contracts import (
    ACCEPTANCE_CONTRACT_VERSION,
    ACCEPTED_REVIEW_CONTRACT_VERSION,
    EVIDENCE_FINGERPRINT_CONTRACT,
)
from industry_alpha.document_import_rules import (
    fingerprint,
    validate_company_identity_payload,
    validate_document_identity_payload,
)
from industry_alpha.research_evidence_pack_contracts import (
    CURSOR_CONTRACT_VERSION,
    EvidencePackCursor,
    EvidencePackRequest,
    MEMBERSHIP_LINKED,
    MEMBERSHIP_UNLINKED,
    ResearchEvidencePackError,
)


_CANDIDATE_CONTRACT = "aquantai.local-document-candidate.v1"
_REVIEW_CONTRACT = "aquantai.local-document-review.v1"


def stored_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def requested_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchEvidencePackError("invalid_evidence_pack_as_of")
    return value.astimezone(timezone.utc)


def utc_text(value: datetime) -> str:
    return stored_utc(value).isoformat().replace("+00:00", "Z")


def membership_summary(states: list[str]) -> str:
    if not states:
        return "no_claim_bindings"
    linked = sum(value == MEMBERSHIP_LINKED for value in states)
    unlinked = sum(value == MEMBERSHIP_UNLINKED for value in states)
    if linked == len(states):
        return "all_bindings_linked"
    if unlinked == len(states):
        return "all_bindings_unlinked"
    if linked + unlinked == len(states):
        return "mixed_linked_and_unlinked_bindings"
    raise ResearchEvidencePackError("evidence_pack_integrity_error")


def encode_cursor(request: EvidencePackRequest, evidence: Any) -> str:
    recorded = requested_utc(request.recorded_at_utc)
    base = {
        "contract_version": CURSOR_CONTRACT_VERSION,
        "research_case_id": str(request.research_case_id),
        "research_case_revision_id": str(request.research_case_revision_id),
        "information_cutoff_date": request.information_cutoff_date.isoformat(),
        "recorded_at_utc": utc_text(recorded),
        "limit": request.limit,
        "last_information_date": evidence.information_date.isoformat(),
        "last_recorded_at_utc": utc_text(evidence.recorded_at_utc),
        "last_evidence_id": str(evidence.id),
    }
    base["payload_sha256"] = fingerprint(base)
    raw = json.dumps(
        base,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(request: EvidencePackRequest) -> EvidencePackCursor | None:
    if request.cursor is None:
        return None
    try:
        padding = "=" * (-len(request.cursor) % 4)
        raw = base64.urlsafe_b64decode((request.cursor + padding).encode("ascii"))
        value = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ResearchEvidencePackError("invalid_evidence_pack_cursor") from exc
    expected_keys = {
        "contract_version",
        "research_case_id",
        "research_case_revision_id",
        "information_cutoff_date",
        "recorded_at_utc",
        "limit",
        "last_information_date",
        "last_recorded_at_utc",
        "last_evidence_id",
        "payload_sha256",
    }
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise ResearchEvidencePackError("invalid_evidence_pack_cursor")
    supplied_sha = value.pop("payload_sha256")
    if value.get("contract_version") != CURSOR_CONTRACT_VERSION or supplied_sha != fingerprint(value):
        raise ResearchEvidencePackError("invalid_evidence_pack_cursor")
    try:
        parsed = EvidencePackCursor(
            research_case_id=UUID(str(value["research_case_id"])),
            research_case_revision_id=UUID(str(value["research_case_revision_id"])),
            information_cutoff_date=date.fromisoformat(str(value["information_cutoff_date"])),
            recorded_at_utc=requested_utc(datetime.fromisoformat(str(value["recorded_at_utc"]).replace("Z", "+00:00"))),
            limit=int(value["limit"]),
            last_information_date=date.fromisoformat(str(value["last_information_date"])),
            last_recorded_at_utc=requested_utc(datetime.fromisoformat(str(value["last_recorded_at_utc"]).replace("Z", "+00:00"))),
            last_evidence_id=UUID(str(value["last_evidence_id"])),
        )
    except (TypeError, ValueError) as exc:
        raise ResearchEvidencePackError("invalid_evidence_pack_cursor") from exc
    if (
        parsed.research_case_id != request.research_case_id
        or parsed.research_case_revision_id != request.research_case_revision_id
        or parsed.information_cutoff_date != request.information_cutoff_date
        or parsed.recorded_at_utc != requested_utc(request.recorded_at_utc)
        or parsed.limit != request.limit
    ):
        raise ResearchEvidencePackError("invalid_evidence_pack_cursor")
    return parsed


def candidate_payload(candidate: Any) -> dict[str, Any]:
    try:
        payload = json.loads(candidate.candidate_payload_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ResearchEvidencePackError("evidence_pack_integrity_error") from exc
    if not isinstance(payload, dict):
        raise ResearchEvidencePackError("evidence_pack_integrity_error")
    try:
        if candidate.candidate_kind == "document_identity":
            return validate_document_identity_payload(payload)
        if candidate.candidate_kind == "company_identity":
            return validate_company_identity_payload(payload)
    except RuntimeError as exc:
        raise ResearchEvidencePackError("evidence_pack_integrity_error") from exc
    if candidate.candidate_kind == "fact":
        if payload != {}:
            raise ResearchEvidencePackError("evidence_pack_integrity_error")
        return {}
    if candidate.candidate_kind == "event":
        if set(payload) != {"event_date"}:
            raise ResearchEvidencePackError("evidence_pack_integrity_error")
        try:
            event_date = date.fromisoformat(str(payload["event_date"]))
        except ValueError as exc:
            raise ResearchEvidencePackError("evidence_pack_integrity_error") from exc
        return {"event_date": event_date.isoformat()}
    raise ResearchEvidencePackError("evidence_pack_integrity_error")


def rebuild_candidate_fingerprint(content: Any, candidate: Any, payload: dict[str, Any]) -> str:
    shape = {
        "contract": _CANDIDATE_CONTRACT,
        "content_id": content.id,
        "content_sha256": content.content_sha256,
        "extractor_contract_version": content.extractor_contract_version,
        "candidate_kind": candidate.candidate_kind,
        "page_number": candidate.page_number,
        "start_utf8_byte": candidate.start_utf8_byte,
        "end_utf8_byte": candidate.end_utf8_byte,
        "quote_sha256": candidate.quote_sha256,
        "statement": candidate.statement,
        "payload": payload,
    }
    return fingerprint(shape)


def normalized_decision(candidate: Any, decision: Any) -> dict[str, Any]:
    return {
        "candidate_id": candidate.id,
        "candidate_fingerprint_sha256": candidate.candidate_fingerprint_sha256,
        "decision": decision.decision,
        "claim_operation": decision.claim_operation,
        "claim_key": decision.claim_key,
        "claim_status": decision.claim_status,
        "evidence_relation": decision.evidence_relation,
    }


def rebuild_source_review_fingerprint(source: Any, normalized: dict[UUID, dict[str, Any]]) -> str:
    return fingerprint(
        {
            "contract": _REVIEW_CONTRACT,
            "review_session_id": source.review_session_id,
            "revision_number": source.revision_number,
            "review_state": source.review_state,
            "source_kind": source.source_kind,
            "evidence_grade": source.evidence_grade,
            "document_identity_candidate_id": source.document_identity_candidate_id,
            "subject_candidate_id": source.subject_candidate_id,
            "information_date": source.information_date,
            "reviewer_note": source.reviewer_note,
            "candidate_decisions": [normalized[key] for key in sorted(normalized, key=str)],
        }
    )


def rebuild_evidence_fingerprint(content: Any, candidate: Any) -> str:
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


def rebuild_acceptance_plan_fingerprint(
    *,
    source: Any,
    review: Any,
    content: Any,
    document_candidate: Any,
    subject_candidate: Any,
    candidates: dict[UUID, Any],
    decisions: dict[UUID, Any],
    selected_ids: tuple[UUID, ...],
) -> str:
    return fingerprint(
        {
            "contract": ACCEPTANCE_CONTRACT_VERSION,
            "source_review_revision_id": source.id,
            "source_review_fingerprint_sha256": source.review_fingerprint_sha256,
            "expected_session_latest_revision_number": source.revision_number,
            "target_research_case_id": review.target_research_case_id,
            "content_id": content.id,
            "content_sha256": content.content_sha256,
            "extractor_contract_version": content.extractor_contract_version,
            "document_identity_candidate_fingerprint": document_candidate.candidate_fingerprint_sha256,
            "subject_candidate_fingerprint": subject_candidate.candidate_fingerprint_sha256,
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
                    "evidence_fingerprint": rebuild_evidence_fingerprint(content, candidates[value]),
                }
                for value in selected_ids
            ],
        }
    )


def rebuild_acceptance_request_fingerprint(
    *,
    source: Any,
    receipt: Any,
    review: Any,
    selected_ids: tuple[UUID, ...],
    decisions: dict[UUID, Any],
    plan_fingerprint: str,
) -> str:
    return fingerprint(
        {
            "source_review_revision_id": source.id,
            "expected_source_review_revision_number": source.revision_number,
            "expected_source_review_fingerprint_sha256": source.review_fingerprint_sha256,
            "expected_session_latest_revision_number": source.revision_number,
            "target_research_case_id": review.target_research_case_id,
            "selected_candidate_ids": selected_ids,
            "selected_decision_fingerprints": tuple(
                decisions[value].decision_fingerprint_sha256 for value in selected_ids
            ),
            "recorded_at_utc": stored_utc(receipt.accepted_at_utc),
            "acceptance_contract_version": receipt.acceptance_contract_version,
            "acceptance_plan_fingerprint_sha256": plan_fingerprint,
        }
    )


def rebuild_accepted_review_fingerprint(
    *, source: Any, accepted: Any, receipt: Any, request_fingerprint: str, plan_fingerprint: str
) -> str:
    return fingerprint(
        {
            "contract": ACCEPTED_REVIEW_CONTRACT_VERSION,
            "source_review_revision_id": source.id,
            "source_review_fingerprint_sha256": source.review_fingerprint_sha256,
            "accepted_revision_number": accepted.revision_number,
            "review_state": "accepted",
            "acceptance_request_fingerprint_sha256": request_fingerprint,
            "acceptance_plan_fingerprint_sha256": plan_fingerprint,
            "target_research_case_id": receipt.target_research_case_id,
            "accepted_at_utc": stored_utc(receipt.accepted_at_utc),
        }
    )
