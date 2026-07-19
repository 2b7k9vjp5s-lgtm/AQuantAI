"""Cutoff-aware read models for v0.6D quality judgments."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerNotVisible
from industry_alpha.stage2_judgments_contracts import Stage2JudgmentDetailContract, Stage2JudgmentListContract
from industry_alpha.stage2_judgments_repository import Stage2JudgmentRepository, Stage2JudgmentRows


V06D_NOTICES = {
    "read_only": True,
    "research_only": True,
    "not_investment_advice": True,
    "no_scores_rankings_recommendations_or_trading": True,
    "no_good_price_good_timing_or_formal_conclusion": True,
    "no_watchlist_or_task_lifecycle": True,
    "description": "v0.6D stores manual evidence-backed industry and company quality judgments over exact frozen research boundaries.",
}


class _JudgmentQuery:
    kind: str

    def __init__(self, repository: Stage2JudgmentRepository) -> None:
        self._repository = repository

    def list(self, *, company_research_id: UUID | None = None, as_of_cutoff: date | None = None) -> Stage2JudgmentListContract:
        source = self._repository.list_industry(company_research_id) if self.kind == "industry" else self._repository.list_company(company_research_id)
        payload = []
        for identity in source:
            if not _recorded_visible(identity.created_at_utc, as_of_cutoff):
                continue
            rows = self._load(identity.id)
            revisions = () if rows is None else tuple(item for item in rows.revisions if _revision_visible(item, as_of_cutoff))
            if revisions:
                payload.append(self._identity_payload(identity, self._revision_payload(rows, revisions[-1], as_of_cutoff)))
        payload.sort(key=lambda item: (item["judgment_key"], item["judgment_id"]))
        return Stage2JudgmentListContract(_date(as_of_cutoff), tuple(payload), V06D_NOTICES)

    def get(self, judgment_id: UUID, *, as_of_cutoff: date | None = None) -> Stage2JudgmentDetailContract:
        rows = self._load(judgment_id)
        if rows is None:
            raise EvidenceLedgerNotFound(f"Stage 2 {self.kind} judgment {judgment_id} was not found.")
        if not _recorded_visible(rows.identity.created_at_utc, as_of_cutoff):
            raise EvidenceLedgerNotVisible("judgment is not visible at the requested cutoff.")
        history = tuple(self._revision_payload(rows, item, as_of_cutoff) for item in rows.revisions if _revision_visible(item, as_of_cutoff))
        if not history:
            raise EvidenceLedgerNotVisible("judgment has no visible revision at the requested cutoff.")
        conflicts = tuple(sorted((item for revision in history for item in revision["conflicts"]), key=lambda item: (item["claim_key"], item["evidence_id"])))
        missing = tuple(sorted((item for revision in history for item in revision["missing_evidence"]), key=lambda item: (item["claim_key"], item["claim_revision_id"])))
        return Stage2JudgmentDetailContract(self._identity_payload(rows.identity, None), _date(as_of_cutoff), history[-1], history, conflicts, missing, V06D_NOTICES)

    def _load(self, identity: UUID) -> Stage2JudgmentRows | None:
        return self._repository.load_industry(identity) if self.kind == "industry" else self._repository.load_company(identity)

    def _identity_payload(self, identity: Any, latest: dict[str, Any] | None) -> dict[str, Any]:
        payload = {"judgment_id": str(identity.id), "company_research_id": str(identity.company_research_id), "judgment_key": identity.judgment_key, "judgment_kind": self.kind, "created_at_utc": _timestamp(identity.created_at_utc)}
        if latest is not None:
            payload["latest_revision"] = latest
        return payload

    def _revision_payload(self, rows: Stage2JudgmentRows, revision: Any, cutoff: date | None) -> dict[str, Any]:
        payload = {
            "revision_id": str(revision.id), "revision_no": revision.revision_no,
            "company_research_revision_id": str(revision.company_research_revision_id),
            "outcome": revision.outcome, "evidence_state": revision.evidence_state,
            "confidence": revision.confidence, "decision_criteria": revision.decision_criteria,
            "rationale": revision.rationale, "uncertainty": revision.uncertainty,
            "follow_up_verification": revision.follow_up_verification,
            "information_cutoff_date": _date(revision.information_cutoff_date),
            "recorded_at_utc": _timestamp(revision.recorded_at_utc),
            "supersedes_revision_id": None if revision.supersedes_revision_id is None else str(revision.supersedes_revision_id),
            "frozen_hypothesis_revision_ids": _link_ids(rows.hypothesis_links, revision.id, "hypothesis_revision_id", cutoff),
            "frozen_expectation_revision_ids": _link_ids(rows.expectation_links, revision.id, "expectation_revision_id", cutoff),
            "frozen_valuation_revision_ids": _link_ids(rows.valuation_links, revision.id, "valuation_revision_id", cutoff),
            "frozen_catalyst_revision_ids": _link_ids(rows.catalyst_links, revision.id, "catalyst_revision_id", cutoff),
            "frozen_risk_revision_ids": _link_ids(rows.risk_links, revision.id, "risk_revision_id", cutoff),
            **_evidence_payload(rows, revision.id, cutoff),
        }
        if self.kind == "industry":
            payload.update(driver_durability=revision.driver_durability, value_pool_direction=revision.value_pool_direction, chain_bottleneck_support=revision.chain_bottleneck_support)
        else:
            payload.update(beneficiary_credibility=revision.beneficiary_credibility, financial_transmission_credibility=revision.financial_transmission_credibility, execution_risks=revision.execution_risks)
        return payload


class Stage2IndustryJudgmentQueryService(_JudgmentQuery):
    kind = "industry"

    def list_judgments(self, **kwargs: Any) -> Stage2JudgmentListContract:
        return self.list(**kwargs)

    def get_judgment(self, judgment_id: UUID, **kwargs: Any) -> Stage2JudgmentDetailContract:
        return self.get(judgment_id, **kwargs)


class Stage2CompanyJudgmentQueryService(_JudgmentQuery):
    kind = "company"

    def list_judgments(self, **kwargs: Any) -> Stage2JudgmentListContract:
        return self.list(**kwargs)

    def get_judgment(self, judgment_id: UUID, **kwargs: Any) -> Stage2JudgmentDetailContract:
        return self.get(judgment_id, **kwargs)


def _evidence_payload(rows: Stage2JudgmentRows, revision_id: UUID, cutoff: date | None) -> dict[str, Any]:
    claim_revisions = {item.id: item for item in rows.claim_revisions}
    claims_by_id = {item.id: item for item in rows.claims}
    source_links = {item.id: item for item in rows.source_evidence_links}
    evidence_by_id = {item.id: item for item in rows.evidence}
    claim_links = [item for item in rows.claim_links if item.judgment_revision_id == revision_id and _recorded_visible(item.recorded_at_utc, cutoff)]
    evidence_links = [item for item in rows.evidence_links if item.judgment_revision_id == revision_id and _recorded_visible(item.recorded_at_utc, cutoff)]
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


def _link_ids(links: tuple[Any, ...], revision_id: UUID, field: str, cutoff: date | None) -> list[str]:
    return sorted(str(getattr(item, field)) for item in links if item.judgment_revision_id == revision_id and _recorded_visible(item.recorded_at_utc, cutoff))


def _revision_visible(row: Any, cutoff: date | None) -> bool:
    return cutoff is None or (row.information_cutoff_date <= cutoff and _stored_utc(row.recorded_at_utc).date() <= cutoff)


def _recorded_visible(value: datetime, cutoff: date | None) -> bool:
    return cutoff is None or _stored_utc(value).date() <= cutoff


def _stored_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return _stored_utc(value).isoformat().replace("+00:00", "Z")


def _date(value: date | None) -> str | None:
    return None if value is None else value.isoformat()
