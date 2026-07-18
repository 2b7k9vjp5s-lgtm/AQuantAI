"""Cutoff-aware deterministic evidence-ledger query contracts."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from industry_alpha.contracts import CaseLedgerContract, CaseListContract
from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerNotVisible
from industry_alpha.models import ClaimRevision, ResearchCaseRevision
from industry_alpha.repository import CaseLedgerRows, EvidenceLedgerRepository

GRADE_LABELS = {
    "A": "Primary official or directly attributable evidence",
    "B": "Attributable secondary evidence with a discernible method",
    "C": "Attributable indirect or tertiary context",
    "D": "Unverified lead, rumor, community assertion, or concept list",
}
READ_ONLY_NOTICES = {
    "read_only": True,
    "purpose": "Local research record-keeping only; not investment advice.",
    "evidence_grading": "Evidence grades are user-assigned provenance classifications.",
    "d_grade_boundary": "D-grade evidence cannot independently support a claim or conclusion.",
    "conflict_visibility": "Conflicts, missing evidence, and D-grade leads remain visible.",
    "allowed_actions": ["read_research_ledger"],
}


class EvidenceLedgerQueryService:
    def __init__(self, repository: EvidenceLedgerRepository) -> None:
        self._repository = repository

    def list_cases(self, *, as_of_cutoff: date | None = None) -> CaseListContract:
        cases: list[dict[str, Any]] = []
        for case in self._repository.list_cases():
            rows = self._repository.load_case(case.id)
            if rows is None:
                continue
            visible_revisions = self._visible_case_revisions(rows, as_of_cutoff)
            if not visible_revisions:
                continue
            visible_evidence = self._visible_evidence(rows, as_of_cutoff)
            visible_claims, visible_claim_revisions = self._visible_claims(rows, as_of_cutoff)
            latest = visible_revisions[-1]
            cases.append(
                {
                    "case_id": str(case.id),
                    "case_key": case.case_key,
                    "origin": case.origin,
                    "created_at_utc": _timestamp(case.created_at_utc),
                    "latest_revision": self._case_revision_dict(latest),
                    "visible_counts": {
                        "case_revisions": len(visible_revisions),
                        "claims": len(visible_claims),
                        "claim_revisions": len(visible_claim_revisions),
                        "evidence_items": len(visible_evidence),
                    },
                }
            )
        return CaseListContract(
            as_of_cutoff=_date(as_of_cutoff),
            cases=tuple(cases),
            notices=READ_ONLY_NOTICES,
        )

    def get_case(self, case_id: UUID, *, as_of_cutoff: date | None = None) -> CaseLedgerContract:
        rows = self._repository.load_case(case_id)
        if rows is None:
            raise EvidenceLedgerNotFound(f"Research case {case_id} was not found.")
        visible_case_revisions = self._visible_case_revisions(rows, as_of_cutoff)
        if not visible_case_revisions:
            raise EvidenceLedgerNotVisible(
                f"Research case {case_id} has no revision visible at the requested cutoff."
            )
        visible_evidence = self._visible_evidence(rows, as_of_cutoff)
        evidence_by_id = {item.id: item for item in visible_evidence}
        visible_claims, visible_claim_revisions = self._visible_claims(rows, as_of_cutoff)
        claim_by_id = {claim.id: claim for claim in visible_claims}
        claim_revision_by_id = {revision.id: revision for revision in visible_claim_revisions}
        case_revision_by_id = {revision.id: revision for revision in visible_case_revisions}
        visible_claim_evidence = [
            link for link in rows.claim_evidence_links
            if link.claim_revision_id in claim_revision_by_id
            and link.evidence_id in evidence_by_id
            and _recorded_visible(link.recorded_at_utc, as_of_cutoff)
        ]
        visible_claim_evidence.sort(
            key=lambda link: (
                claim_by_id[claim_revision_by_id[link.claim_revision_id].claim_id].claim_key,
                claim_revision_by_id[link.claim_revision_id].revision_no,
                link.relation,
                str(link.evidence_id),
            )
        )
        visible_case_claim = [
            link for link in rows.case_claim_links
            if link.case_revision_id in case_revision_by_id
            and link.claim_revision_id in claim_revision_by_id
            and _recorded_visible(link.recorded_at_utc, as_of_cutoff)
        ]
        visible_case_claim.sort(
            key=lambda link: (
                case_revision_by_id[link.case_revision_id].revision_no,
                link.role,
                claim_by_id[claim_revision_by_id[link.claim_revision_id].claim_id].claim_key,
                claim_revision_by_id[link.claim_revision_id].revision_no,
            )
        )
        visible_verification = [
            item for item in rows.verification_items
            if item.case_revision_id in case_revision_by_id
            and _recorded_visible(item.recorded_at_utc, as_of_cutoff)
        ]
        visible_verification.sort(
            key=lambda item: (
                case_revision_by_id[item.case_revision_id].revision_no,
                item.item_no,
            )
        )

        claim_histories: list[dict[str, Any]] = []
        for claim in visible_claims:
            history = [r for r in visible_claim_revisions if r.claim_id == claim.id]
            history.sort(key=lambda revision: revision.revision_no)
            claim_histories.append(
                {
                    "claim_id": str(claim.id),
                    "claim_key": claim.claim_key,
                    "created_at_utc": _timestamp(claim.created_at_utc),
                    "current_revision": self._claim_revision_dict(history[-1]),
                    "revision_history": [self._claim_revision_dict(item) for item in history],
                }
            )
        conflicts = [
            {
                "claim_revision_id": str(link.claim_revision_id),
                "claim_key": claim_by_id[
                    claim_revision_by_id[link.claim_revision_id].claim_id
                ].claim_key,
                "claim_revision_no": claim_revision_by_id[link.claim_revision_id].revision_no,
                "evidence_id": str(link.evidence_id),
                "evidence_grade": evidence_by_id[link.evidence_id].evidence_grade,
                "source_title": evidence_by_id[link.evidence_id].source_title,
                "recorded_at_utc": _timestamp(link.recorded_at_utc),
            }
            for link in visible_claim_evidence
            if link.relation == "contradicts"
        ]
        latest = visible_case_revisions[-1]
        verification_payload = [self._verification_dict(item) for item in visible_verification]
        return CaseLedgerContract(
            case={
                "case_id": str(rows.case.id),
                "case_key": rows.case.case_key,
                "origin": rows.case.origin,
                "created_at_utc": _timestamp(rows.case.created_at_utc),
            },
            as_of_cutoff=_date(as_of_cutoff),
            latest_revision=self._case_revision_dict(latest),
            case_revision_history=tuple(
                self._case_revision_dict(item) for item in visible_case_revisions
            ),
            claims=tuple(claim_histories),
            evidence_items=tuple(self._evidence_dict(item) for item in visible_evidence),
            claim_evidence_links=tuple(
                {
                    "link_id": str(link.id),
                    "claim_revision_id": str(link.claim_revision_id),
                    "evidence_id": str(link.evidence_id),
                    "relation": link.relation,
                    "link_note": link.link_note,
                    "recorded_at_utc": _timestamp(link.recorded_at_utc),
                }
                for link in visible_claim_evidence
            ),
            conflicts=tuple(conflicts),
            case_revision_claim_links=tuple(
                {
                    "link_id": str(link.id),
                    "case_revision_id": str(link.case_revision_id),
                    "claim_revision_id": str(link.claim_revision_id),
                    "role": link.role,
                    "recorded_at_utc": _timestamp(link.recorded_at_utc),
                }
                for link in visible_case_claim
            ),
            verification_items=tuple(verification_payload),
            label_metadata={
                "verification_items": "后续验证清单",
                "evidence_grades": GRADE_LABELS,
            },
            notices=READ_ONLY_NOTICES,
        )

    @staticmethod
    def _visible_case_revisions(
        rows: CaseLedgerRows, cutoff: date | None
    ) -> list[ResearchCaseRevision]:
        return [
            revision for revision in rows.case_revisions
            if _dated_visible(
                revision.information_cutoff_date, revision.recorded_at_utc, cutoff
            )
        ]

    @staticmethod
    def _visible_evidence(rows: CaseLedgerRows, cutoff: date | None) -> list[Any]:
        return [
            item for item in rows.evidence_items
            if _dated_visible(item.information_date, item.recorded_at_utc, cutoff)
        ]

    @staticmethod
    def _visible_claims(
        rows: CaseLedgerRows, cutoff: date | None
    ) -> tuple[list[Any], list[ClaimRevision]]:
        visible_claims = [
            claim for claim in rows.claims if _recorded_visible(claim.created_at_utc, cutoff)
        ]
        visible_ids = {claim.id for claim in visible_claims}
        revisions = [
            revision for revision in rows.claim_revisions
            if revision.claim_id in visible_ids
            and _dated_visible(
                revision.information_cutoff_date, revision.recorded_at_utc, cutoff
            )
        ]
        claims_with_revision = {revision.claim_id for revision in revisions}
        return [claim for claim in visible_claims if claim.id in claims_with_revision], revisions

    @staticmethod
    def _case_revision_dict(revision: ResearchCaseRevision) -> dict[str, Any]:
        return {
            "revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "title": revision.title,
            "research_question": revision.research_question,
            "summary": revision.summary,
            "workflow_state": revision.workflow_state,
            "conclusion_status": revision.conclusion_status,
            "information_cutoff_date": _date(revision.information_cutoff_date),
            "recorded_at_utc": _timestamp(revision.recorded_at_utc),
            "supersedes_revision_id": _uuid(revision.supersedes_revision_id),
        }

    @staticmethod
    def _claim_revision_dict(revision: ClaimRevision) -> dict[str, Any]:
        return {
            "revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "statement": revision.statement,
            "claim_kind": revision.claim_kind,
            "claim_status": revision.claim_status,
            "inference_confidence": revision.inference_confidence,
            "inference_basis": revision.inference_basis,
            "information_cutoff_date": _date(revision.information_cutoff_date),
            "recorded_at_utc": _timestamp(revision.recorded_at_utc),
            "supersedes_revision_id": _uuid(revision.supersedes_revision_id),
        }

    @staticmethod
    def _evidence_dict(item: Any) -> dict[str, Any]:
        return {
            "evidence_id": str(item.id),
            "evidence_grade": item.evidence_grade,
            "source_kind": item.source_kind,
            "source_title": item.source_title,
            "publisher_or_author": item.publisher_or_author,
            "source_locator": item.source_locator,
            "information_date": _date(item.information_date),
            "recorded_at_utc": _timestamp(item.recorded_at_utc),
            "summary": item.summary,
            "content_fingerprint": item.content_fingerprint,
            "supersedes_evidence_id": _uuid(item.supersedes_evidence_id),
        }

    @staticmethod
    def _verification_dict(item: Any) -> dict[str, Any]:
        return {
            "verification_item_id": str(item.id),
            "case_revision_id": str(item.case_revision_id),
            "item_no": item.item_no,
            "description": item.description,
            "status": item.status,
            "due_date": _date(item.due_date),
            "recorded_at_utc": _timestamp(item.recorded_at_utc),
        }


def _dated_visible(information_date: date, recorded_at: datetime, cutoff: date | None) -> bool:
    return cutoff is None or (
        information_date <= cutoff and _utc_date(recorded_at) <= cutoff
    )


def _recorded_visible(recorded_at: datetime, cutoff: date | None) -> bool:
    return cutoff is None or _utc_date(recorded_at) <= cutoff


def _utc_date(value: datetime) -> date:
    if value.tzinfo is None:
        return value.date()
    return value.astimezone(timezone.utc).date()


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _date(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def _uuid(value: UUID | None) -> str | None:
    return None if value is None else str(value)
