"""Cutoff-aware deterministic reads for typed beneficiary semantic history."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from industry_alpha.beneficiary_semantics_contracts import (
    BeneficiarySemanticDetailContract,
    SEMANTICS_NOTICES,
    split_driver_state,
)
from industry_alpha.beneficiary_semantics_repository import (
    BeneficiarySemanticRepository,
    BeneficiarySemanticRows,
)
from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerNotVisible


class BeneficiarySemanticQueryService:
    def __init__(self, repository: BeneficiarySemanticRepository) -> None:
        self._repository = repository

    def get_profile(
        self, beneficiary_id: UUID, *, as_of_cutoff: date | None = None
    ) -> BeneficiarySemanticDetailContract:
        rows = self._repository.load(beneficiary_id)
        if rows is None:
            if self._repository.beneficiary_exists(beneficiary_id):
                raise EvidenceLedgerNotFound(
                    f"Stage 1 beneficiary {beneficiary_id} has no typed semantic profile."
                )
            raise EvidenceLedgerNotFound(
                f"Stage 1 beneficiary {beneficiary_id} was not found."
            )
        visible = [
            item
            for item in rows.profile_revisions
            if _visible(item.information_cutoff_date, item.recorded_at_utc, as_of_cutoff)
        ]
        if not visible:
            raise EvidenceLedgerNotVisible(
                f"Typed semantic profile for {beneficiary_id} has no revision visible at the requested cutoff."
            )
        history = tuple(self._revision_payload(rows, item) for item in visible)
        return BeneficiarySemanticDetailContract(
            beneficiary={
                "beneficiary_id": str(rows.beneficiary.id),
                "case_id": str(rows.beneficiary.case_id),
                "map_id": str(rows.beneficiary.map_id),
                "source": rows.beneficiary.source,
                "stock_code": rows.beneficiary.stock_code,
                "created_at_utc": _timestamp(rows.beneficiary.created_at_utc),
            },
            profile={
                "profile_id": str(rows.profile.id),
                "created_at_utc": _timestamp(rows.profile.created_at_utc),
            },
            as_of_cutoff=None if as_of_cutoff is None else as_of_cutoff.isoformat(),
            latest_revision=history[-1],
            revision_history=history,
            notices=SEMANTICS_NOTICES,
        )

    def _revision_payload(
        self, rows: BeneficiarySemanticRows, revision: Any
    ) -> dict[str, Any]:
        beneficiary_revision = next(
            item
            for item in rows.beneficiary_revisions
            if item.id == revision.beneficiary_revision_id
        )
        map_revision = next(
            item
            for item in rows.map_revisions
            if item.id == revision.selected_map_revision_id
        )
        assertions = [
            self._assertion_payload(rows, item, revision)
            for item in rows.assertions
            if item.profile_revision_id == revision.id
        ]
        assertions.sort(
            key=lambda item: (
                item["field_kind"],
                item["position"],
                item["assertion_key"],
            )
        )
        verification = [
            {
                "verification_item_id": str(item.id),
                "assertion_id": _uuid_text(item.assertion_id),
                "verification_question": item.verification_question,
                "expected_evidence_type": item.expected_evidence_type,
                "status": item.status,
                "recorded_at_utc": _timestamp(item.recorded_at_utc),
            }
            for item in rows.verification_items
            if item.profile_revision_id == revision.id
        ]
        verification.sort(
            key=lambda item: (
                item["recorded_at_utc"],
                item["verification_item_id"],
            )
        )
        return {
            "profile_revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "taxonomy_version": revision.taxonomy_version,
            "overall_status": revision.overall_status,
            "summary": revision.summary,
            "recorded_by": revision.recorded_by,
            "information_cutoff_date": revision.information_cutoff_date.isoformat(),
            "recorded_at_utc": _timestamp(revision.recorded_at_utc),
            "supersedes_revision_id": _uuid_text(revision.supersedes_revision_id),
            "frozen_stage1": {
                "beneficiary_revision_id": str(beneficiary_revision.id),
                "revision_no": beneficiary_revision.revision_no,
                "legacy_beneficiary_kind": beneficiary_revision.beneficiary_kind,
                "assessment_status": beneficiary_revision.assessment_status,
                "rationale_summary": beneficiary_revision.rationale_summary,
                "information_cutoff_date": beneficiary_revision.information_cutoff_date.isoformat(),
                "recorded_at_utc": _timestamp(beneficiary_revision.recorded_at_utc),
            },
            "frozen_map_revision": {
                "map_revision_id": str(map_revision.id),
                "revision_no": map_revision.revision_no,
                "title": map_revision.title,
                "scope": map_revision.scope,
                "information_cutoff_date": map_revision.information_cutoff_date.isoformat(),
                "recorded_at_utc": _timestamp(map_revision.recorded_at_utc),
            },
            "assertions": assertions,
            "missing_assertion_keys": [
                item["assertion_key"]
                for item in assertions
                if item["evidence_state"] == "missing"
            ],
            "disputed_assertion_keys": [
                item["assertion_key"]
                for item in assertions
                if item["evidence_state"] == "disputed"
            ],
            "verification_items": verification,
        }

    @staticmethod
    def _assertion_payload(
        rows: BeneficiarySemanticRows, assertion: Any, profile_revision: Any
    ) -> dict[str, Any]:
        links = [
            item
            for item in rows.assertion_claim_links
            if item.assertion_id == assertion.id
        ]
        claim_revisions = {item.id: item for item in rows.claim_revisions}
        claims = {item.id: item for item in rows.claims}
        evidence_items = {item.id: item for item in rows.evidence_items}
        claims_payload: list[dict[str, Any]] = []
        grade_counts: Counter[str] = Counter()
        for link in links:
            claim_revision = claim_revisions[link.claim_revision_id]
            claim = claims[claim_revision.claim_id]
            evidence_payload: list[dict[str, Any]] = []
            for evidence_link in rows.claim_evidence_links:
                if evidence_link.claim_revision_id != claim_revision.id:
                    continue
                evidence = evidence_items[evidence_link.evidence_id]
                if not _within_revision_boundary(
                    evidence.information_date,
                    evidence.recorded_at_utc,
                    evidence_link.recorded_at_utc,
                    profile_revision,
                ):
                    continue
                grade_counts[evidence.evidence_grade] += 1
                evidence_payload.append(
                    {
                        "claim_evidence_link_id": str(evidence_link.id),
                        "evidence_id": str(evidence.id),
                        "relation": evidence_link.relation,
                        "evidence_grade": evidence.evidence_grade,
                        "source_kind": evidence.source_kind,
                        "source_title": evidence.source_title,
                        "publisher_or_author": evidence.publisher_or_author,
                        "source_locator": evidence.source_locator,
                        "information_date": evidence.information_date.isoformat(),
                        "recorded_at_utc": _timestamp(evidence.recorded_at_utc),
                        "summary": evidence.summary,
                    }
                )
            evidence_payload.sort(
                key=lambda item: (
                    item["relation"],
                    item["information_date"],
                    item["recorded_at_utc"],
                    item["evidence_id"],
                )
            )
            claims_payload.append(
                {
                    "semantic_relation": link.relation,
                    "semantic_link_recorded_at_utc": _timestamp(link.recorded_at_utc),
                    "claim_id": str(claim.id),
                    "claim_key": claim.claim_key,
                    "claim_revision_id": str(claim_revision.id),
                    "revision_no": claim_revision.revision_no,
                    "statement": claim_revision.statement,
                    "claim_kind": claim_revision.claim_kind,
                    "claim_status": claim_revision.claim_status,
                    "inference_confidence": claim_revision.inference_confidence,
                    "inference_basis": claim_revision.inference_basis,
                    "information_cutoff_date": claim_revision.information_cutoff_date.isoformat(),
                    "recorded_at_utc": _timestamp(claim_revision.recorded_at_utc),
                    "evidence": evidence_payload,
                }
            )
        claims_payload.sort(
            key=lambda item: (
                item["semantic_relation"],
                item["claim_key"],
                item["claim_revision_id"],
            )
        )
        driver = None
        if assertion.field_kind == "driver":
            observation_revision = next(
                item
                for item in rows.observation_revisions
                if item.id == assertion.map_observation_revision_id
            )
            observation = next(
                item
                for item in rows.observations
                if item.id == observation_revision.observation_id
            )
            driver_type, driver_subtype = split_driver_state(assertion.state_code)
            driver = {
                "driver_type": driver_type,
                "driver_subtype": driver_subtype,
                "observation_id": str(observation.id),
                "observation_key": observation.observation_key,
                "observation_revision_id": str(observation_revision.id),
                "observation_title": observation_revision.title,
                "observation_description": observation_revision.description,
                "assertion_status": observation_revision.assertion_status,
                "information_cutoff_date": observation_revision.information_cutoff_date.isoformat(),
                "recorded_at_utc": _timestamp(observation_revision.recorded_at_utc),
            }
        return {
            "assertion_id": str(assertion.id),
            "assertion_key": assertion.assertion_key,
            "field_kind": assertion.field_kind,
            "state_code": assertion.state_code,
            "evidence_state": assertion.evidence_state,
            "subject_text": assertion.subject_text,
            "rationale": assertion.rationale,
            "position": assertion.position,
            "driver": driver,
            "claim_links": claims_payload,
            "evidence_grade_counts": {
                grade: grade_counts.get(grade, 0) for grade in ("A", "B", "C", "D")
            },
        }


def _visible(
    information_cutoff_date: date,
    recorded_at_utc: datetime,
    as_of_cutoff: date | None,
) -> bool:
    if as_of_cutoff is None:
        return True
    return (
        information_cutoff_date <= as_of_cutoff
        and _stored_utc(recorded_at_utc).date() <= as_of_cutoff
    )


def _within_revision_boundary(
    information_date: date,
    evidence_recorded_at: datetime,
    link_recorded_at: datetime,
    revision: Any,
) -> bool:
    boundary = _stored_utc(revision.recorded_at_utc)
    return (
        information_date <= revision.information_cutoff_date
        and _stored_utc(evidence_recorded_at) <= boundary
        and _stored_utc(link_recorded_at) <= boundary
    )


def _stored_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return _stored_utc(value).isoformat().replace("+00:00", "Z")


def _uuid_text(value: UUID | None) -> str | None:
    return None if value is None else str(value)
