"""Cutoff-aware read models for v0.6C catalyst and risk assessments."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any
from uuid import UUID

from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerNotVisible
from industry_alpha.stage2_assessments_contracts import Stage2AssessmentDetailContract, Stage2AssessmentListContract
from industry_alpha.stage2_assessments_repository import Stage2AssessmentRepository, Stage2AssessmentRows
from industry_alpha.stage2_query_values import (
    date_text as _date,
    dated_visible as _dated_visible,
    recorded_visible as _recorded_visible,
    stored_utc as _stored_utc,
    timestamp_text as _timestamp,
    uuid_text as _uuid,
)


V06C_NOTICES = {
    "read_only": True,
    "research_only": True,
    "not_investment_advice": True,
    "no_scores_rankings_recommendations_or_trading": True,
    "no_good_price_good_timing_or_final_conclusion": True,
    "no_automatic_monitoring_alerts_or_reminders": True,
    "description": "v0.6C records dated catalyst and company-risk research judgments over exact frozen evidence boundaries. It is not a monitor, score, recommendation, timing model, or trading system.",
}


class _AssessmentQuery:
    kind: str

    def __init__(self, repository: Stage2AssessmentRepository) -> None:
        self._repository = repository

    def list(self, *, company_research_id: UUID | None = None, as_of_cutoff: date | None = None) -> Stage2AssessmentListContract:
        source = self._repository.list_catalysts(company_research_id) if self.kind == "catalyst" else self._repository.list_risks(company_research_id)
        payload = []
        for identity in source:
            if not _recorded_visible(identity.created_at_utc, as_of_cutoff):
                continue
            rows = self._load(identity.id)
            if rows is None:
                continue
            revisions = _visible_revisions(rows.revisions, as_of_cutoff)
            if not revisions:
                continue
            payload.append(self._identity_payload(identity, self._revision_payload(rows, revisions[-1], as_of_cutoff)))
        key = f"{self.kind}_key"
        payload.sort(key=lambda item: (item[key], item[f"{self.kind}_id"]))
        return Stage2AssessmentListContract(_date(as_of_cutoff), tuple(payload), V06C_NOTICES)

    def get(self, identity_id: UUID, *, as_of_cutoff: date | None = None) -> Stage2AssessmentDetailContract:
        rows = self._load(identity_id)
        if rows is None:
            raise EvidenceLedgerNotFound(f"Stage 2 {self.kind} assessment {identity_id} was not found.")
        if not _recorded_visible(rows.identity.created_at_utc, as_of_cutoff):
            raise EvidenceLedgerNotVisible(f"{self.kind} assessment is not visible at the requested cutoff.")
        history = tuple(self._revision_payload(rows, item, as_of_cutoff) for item in _visible_revisions(rows.revisions, as_of_cutoff))
        if not history:
            raise EvidenceLedgerNotVisible(f"{self.kind} assessment has no visible revision.")
        conflicts = tuple(sorted((item for revision in history for item in revision["conflicts"]), key=lambda item: (item["claim_key"], item["evidence_id"])))
        missing = tuple(sorted((item for revision in history for item in revision["missing_evidence"]), key=lambda item: (item["claim_key"], item["claim_revision_id"])))
        return Stage2AssessmentDetailContract(
            assessment=self._identity_payload(rows.identity, None), as_of_cutoff=_date(as_of_cutoff),
            latest_revision=history[-1], revision_history=history, conflicts=conflicts,
            missing_evidence=missing, notices=V06C_NOTICES,
        )

    def _load(self, identity_id: UUID) -> Stage2AssessmentRows | None:
        return self._repository.load_catalyst(identity_id) if self.kind == "catalyst" else self._repository.load_risk(identity_id)

    def _identity_payload(self, identity: Any, latest: dict[str, Any] | None) -> dict[str, Any]:
        payload = {
            f"{self.kind}_id": str(identity.id),
            "company_research_id": str(identity.company_research_id),
            f"{self.kind}_key": getattr(identity, f"{self.kind}_key"),
            "created_at_utc": _timestamp(identity.created_at_utc),
        }
        if latest is not None:
            payload["latest_revision"] = latest
        return payload

    def _revision_payload(self, rows: Stage2AssessmentRows, revision: Any, cutoff: date | None) -> dict[str, Any]:
        evidence = _evidence_payload(rows, revision.id, self.kind, cutoff)
        payload = {
            "revision_id": str(revision.id),
            "company_research_revision_id": str(revision.company_research_revision_id),
            "revision_no": revision.revision_no,
            f"{self.kind}_category": getattr(revision, f"{self.kind}_category"),
            "subject": revision.subject,
            "status": revision.status,
            "confidence": revision.confidence,
            "basis": revision.basis,
            "uncertainty": revision.uncertainty,
            "information_cutoff_date": _date(revision.information_cutoff_date),
            "recorded_at_utc": _timestamp(revision.recorded_at_utc),
            "supersedes_revision_id": _uuid(revision.supersedes_revision_id),
            "frozen_hypothesis_revision_ids": _link_ids(rows.hypothesis_links, revision.id, self.kind, "hypothesis_revision_id", cutoff),
            "frozen_expectation_revision_ids": _link_ids(rows.expectation_links, revision.id, self.kind, "expectation_revision_id", cutoff),
            "frozen_valuation_revision_ids": _link_ids(rows.valuation_links, revision.id, self.kind, "valuation_revision_id", cutoff),
            **evidence,
        }
        if self.kind == "catalyst":
            payload["expected_observation_window"] = revision.expected_observation_window
            payload["trigger_observation_criteria"] = revision.trigger_observation_criteria
        else:
            payload["downside_path"] = revision.downside_path
            payload["thesis_invalidation_condition"] = revision.thesis_invalidation_condition
            payload["mitigants"] = revision.mitigants
        return payload


class Stage2CatalystQueryService(_AssessmentQuery):
    kind = "catalyst"

    def list_catalysts(self, **kwargs: Any) -> Stage2AssessmentListContract:
        return self.list(**kwargs)

    def get_catalyst(self, catalyst_id: UUID, **kwargs: Any) -> Stage2AssessmentDetailContract:
        return self.get(catalyst_id, **kwargs)


class Stage2RiskQueryService(_AssessmentQuery):
    kind = "risk"

    def list_risks(self, **kwargs: Any) -> Stage2AssessmentListContract:
        return self.list(**kwargs)

    def get_risk(self, risk_id: UUID, **kwargs: Any) -> Stage2AssessmentDetailContract:
        return self.get(risk_id, **kwargs)


def _evidence_payload(rows: Stage2AssessmentRows, revision_id: UUID, kind: str, cutoff: date | None) -> dict[str, Any]:
    claim_revisions = {item.id: item for item in rows.claim_revisions}
    claims_by_id = {item.id: item for item in rows.claims}
    source_links = {item.id: item for item in rows.source_evidence_links}
    evidence_by_id = {item.id: item for item in rows.evidence}
    revision_field = f"{kind}_revision_id"
    claim_links = [item for item in rows.claim_links if getattr(item, revision_field) == revision_id and _recorded_visible(item.recorded_at_utc, cutoff)]
    evidence_links = [item for item in rows.evidence_links if getattr(item, revision_field) == revision_id and _recorded_visible(item.recorded_at_utc, cutoff)]
    claims, conflicts, missing = [], [], []
    grades: Counter[str] = Counter()
    for boundary in sorted(claim_links, key=lambda item: str(item.claim_revision_id)):
        revision = claim_revisions[boundary.claim_revision_id]
        identity = claims_by_id[revision.claim_id]
        evidence_payload = []
        for frozen in evidence_links:
            if frozen.claim_revision_id != revision.id:
                continue
            link, item = source_links[frozen.claim_evidence_link_id], evidence_by_id[frozen.evidence_id]
            evidence_payload.append({
                "claim_evidence_link_id": str(link.id), "evidence_id": str(item.id),
                "evidence_grade": item.evidence_grade, "relation": link.relation,
                "source_title": item.source_title, "information_date": _date(item.information_date),
                "recorded_at_utc": _timestamp(item.recorded_at_utc),
            })
            grades[item.evidence_grade] += 1
            if link.relation == "contradicts":
                conflicts.append({"claim_revision_id": str(revision.id), "claim_key": identity.claim_key, "evidence_id": str(item.id), "evidence_grade": item.evidence_grade, "source_title": item.source_title})
        evidence_payload.sort(key=lambda item: (item["relation"], item["evidence_grade"], item["evidence_id"]))
        if not evidence_payload:
            missing.append({"claim_revision_id": str(revision.id), "claim_key": identity.claim_key, "reason": "尚未获得可靠公开证据"})
        claims.append({
            "claim_id": str(identity.id), "claim_key": identity.claim_key,
            "claim_revision_id": str(revision.id), "revision_no": revision.revision_no,
            "statement": revision.statement, "claim_kind": revision.claim_kind,
            "claim_status": revision.claim_status,
            "inference_confidence": revision.inference_confidence,
            "inference_basis": revision.inference_basis,
            "information_cutoff_date": _date(revision.information_cutoff_date),
            "recorded_at_utc": _timestamp(revision.recorded_at_utc),
            "evidence": evidence_payload,
        })
    claims.sort(key=lambda item: (item["claim_key"], item["claim_revision_id"]))
    conflicts.sort(key=lambda item: (item["claim_key"], item["evidence_id"]))
    missing.sort(key=lambda item: (item["claim_key"], item["claim_revision_id"]))
    return {"claims": tuple(claims), "evidence_grade_counts": {grade: grades[grade] for grade in ("A", "B", "C", "D")}, "conflicts": tuple(conflicts), "missing_evidence": tuple(missing)}


def _link_ids(links: tuple[Any, ...], revision_id: UUID, kind: str, value_field: str, cutoff: date | None) -> list[str]:
    revision_field = f"{kind}_revision_id"
    return sorted(str(getattr(item, value_field)) for item in links if getattr(item, revision_field) == revision_id and _recorded_visible(item.recorded_at_utc, cutoff))


def _visible_revisions(revisions: tuple[Any, ...], cutoff: date | None) -> list[Any]:
    return [
        item
        for item in revisions
        if _dated_visible(
            item.information_cutoff_date,
            item.recorded_at_utc,
            cutoff,
        )
    ]
