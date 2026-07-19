"""Cutoff-aware read models for frozen Stage 2 company research."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerNotVisible
from industry_alpha.stage2_contracts import (
    Stage2CompanyResearchDetailContract,
    Stage2CompanyResearchListContract,
)
from industry_alpha.stage2_repository import Stage2CompanyResearchRepository, Stage2Rows

STAGE2_NOTICES = {
    "read_only": True,
    "research_only": True,
    "fixture_or_local_data": True,
    "not_investment_advice": True,
    "no_scores_weights_or_rankings": True,
    "no_target_prices_or_recommendations": True,
    "description": (
        "Stage 2 outputs are local evidence-bound research hypotheses, not scores, "
        "rankings, target prices, recommendations, or investment advice."
    ),
}


class Stage2CompanyResearchQueryService:
    def __init__(self, repository: Stage2CompanyResearchRepository) -> None:
        self._repository = repository

    def list_research(
        self,
        *,
        candidate_pool_revision_id: UUID | None = None,
        map_id: UUID | None = None,
        as_of_cutoff: date | None = None,
    ) -> Stage2CompanyResearchListContract:
        items: list[dict[str, Any]] = []
        for identity in self._repository.list_research(
            candidate_pool_revision_id=candidate_pool_revision_id, map_id=map_id
        ):
            if not _recorded_visible(identity.created_at_utc, as_of_cutoff):
                continue
            rows = self._repository.load(identity.id)
            if rows is None:
                continue
            revisions = self._visible_research_revisions(rows, as_of_cutoff)
            if not revisions:
                continue
            latest = revisions[-1]
            items.append(
                {
                    "company_research_id": str(identity.id),
                    "case_id": str(identity.case_id),
                    "map_id": str(identity.map_id),
                    "candidate_pool_revision_id": str(
                        identity.candidate_pool_revision_id
                    ),
                    "candidate_pool_membership_id": str(
                        identity.candidate_pool_membership_id
                    ),
                    "source": identity.source,
                    "stock_code": identity.stock_code,
                    "created_at_utc": _timestamp(identity.created_at_utc),
                    "latest_revision": self._research_revision_summary(
                        rows, latest, as_of_cutoff
                    ),
                }
            )
        items.sort(
            key=lambda item: (
                item["source"],
                item["stock_code"],
                item["company_research_id"],
            )
        )
        return Stage2CompanyResearchListContract(
            as_of_cutoff=_date(as_of_cutoff),
            company_research=tuple(items),
            notices=STAGE2_NOTICES,
        )

    def get_research(
        self, research_id: UUID, *, as_of_cutoff: date | None = None
    ) -> Stage2CompanyResearchDetailContract:
        rows = self._repository.load(research_id)
        if rows is None:
            raise EvidenceLedgerNotFound(
                f"Stage 2 company research {research_id} was not found."
            )
        if not _recorded_visible(rows.research.created_at_utc, as_of_cutoff):
            raise EvidenceLedgerNotVisible(
                f"Stage 2 company research {research_id} is not visible at the requested cutoff."
            )
        revisions = self._visible_research_revisions(rows, as_of_cutoff)
        if not revisions:
            raise EvidenceLedgerNotVisible(
                f"Stage 2 company research {research_id} has no visible revision."
            )
        history = tuple(
            self._research_revision_payload(rows, item, as_of_cutoff)
            for item in revisions
        )
        hypotheses = self._hypothesis_payloads(rows, as_of_cutoff)
        conflicts = tuple(
            sorted(
                (
                    conflict
                    for hypothesis in hypotheses
                    for revision in hypothesis["revision_history"]
                    for conflict in revision["conflicts"]
                ),
                key=lambda item: (
                    item["hypothesis_revision_id"],
                    item["claim_key"],
                    item["evidence_id"],
                ),
            )
        )
        missing = tuple(
            sorted(
                (
                    item
                    for hypothesis in hypotheses
                    for revision in hypothesis["revision_history"]
                    for item in revision["missing_evidence"]
                ),
                key=lambda item: (
                    item["hypothesis_revision_id"], item["claim_key"]
                ),
            )
        )
        return Stage2CompanyResearchDetailContract(
            company_research={
                "company_research_id": str(rows.research.id),
                "case_id": str(rows.research.case_id),
                "map_id": str(rows.research.map_id),
                "source": rows.research.source,
                "stock_code": rows.research.stock_code,
                "created_at_utc": _timestamp(rows.research.created_at_utc),
            },
            as_of_cutoff=_date(as_of_cutoff),
            frozen_stage1_handoff=self._handoff_payload(rows),
            latest_revision=history[-1],
            revision_history=history,
            hypotheses=hypotheses,
            conflicts=conflicts,
            missing_evidence=missing,
            notices=STAGE2_NOTICES,
        )

    @staticmethod
    def _visible_research_revisions(
        rows: Stage2Rows, cutoff: date | None
    ) -> list[Any]:
        return [
            item
            for item in rows.research_revisions
            if _dated_visible(
                item.information_cutoff_date, item.recorded_at_utc, cutoff
            )
        ]

    def _research_revision_payload(
        self, rows: Stage2Rows, revision: Any, cutoff: date | None
    ) -> dict[str, Any]:
        payload = self._research_revision_summary(rows, revision, cutoff)
        verification = [
            {
                "verification_item_id": str(item.id),
                "item_no": item.item_no,
                "description": item.description,
                "status": item.status,
                "due_date": _date(item.due_date),
                "recorded_at_utc": _timestamp(item.recorded_at_utc),
            }
            for item in rows.verification_items
            if item.company_research_revision_id == revision.id
            and _recorded_visible(item.recorded_at_utc, cutoff)
        ]
        verification.sort(key=lambda item: (item["item_no"], item["verification_item_id"]))
        payload["后续验证清单"] = verification
        return payload

    @staticmethod
    def _research_revision_summary(
        rows: Stage2Rows, revision: Any, cutoff: date | None
    ) -> dict[str, Any]:
        links = [
            item
            for item in rows.research_hypothesis_links
            if item.company_research_revision_id == revision.id
            and _recorded_visible(item.recorded_at_utc, cutoff)
            and _stored_utc(item.recorded_at_utc)
            <= _stored_utc(revision.recorded_at_utc)
        ]
        links.sort(key=lambda item: (str(item.hypothesis_id), str(item.id)))
        return {
            "revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "workflow_state": revision.workflow_state,
            "conclusion_status": revision.conclusion_status,
            "research_question": revision.research_question,
            "summary": revision.summary,
            "information_cutoff_date": _date(revision.information_cutoff_date),
            "recorded_at_utc": _timestamp(revision.recorded_at_utc),
            "supersedes_revision_id": _uuid(revision.supersedes_revision_id),
            "frozen_hypothesis_revision_ids": [
                str(item.hypothesis_revision_id) for item in links
            ],
        }

    def _hypothesis_payloads(
        self, rows: Stage2Rows, cutoff: date | None
    ) -> tuple[dict[str, Any], ...]:
        payload: list[dict[str, Any]] = []
        for hypothesis in rows.hypotheses:
            if not _recorded_visible(hypothesis.created_at_utc, cutoff):
                continue
            revisions = [
                item
                for item in rows.hypothesis_revisions
                if item.hypothesis_id == hypothesis.id
                and _dated_visible(
                    item.information_cutoff_date, item.recorded_at_utc, cutoff
                )
            ]
            if not revisions:
                continue
            history = tuple(
                self._hypothesis_revision_payload(rows, item, cutoff)
                for item in revisions
            )
            payload.append(
                {
                    "hypothesis_id": str(hypothesis.id),
                    "hypothesis_key": hypothesis.hypothesis_key,
                    "stage1_assertion_link_id": str(
                        hypothesis.stage1_assertion_link_id
                    ),
                    "created_at_utc": _timestamp(hypothesis.created_at_utc),
                    "latest_revision": history[-1],
                    "revision_history": history,
                }
            )
        payload.sort(key=lambda item: (item["hypothesis_key"], item["hypothesis_id"]))
        return tuple(payload)

    @staticmethod
    def _hypothesis_revision_payload(
        rows: Stage2Rows, revision: Any, cutoff: date | None
    ) -> dict[str, Any]:
        claim_by_id = {item.id: item for item in rows.claim_revisions}
        claim_identity = {item.id: item for item in rows.claims}
        link_by_id = {item.id: item for item in rows.claim_evidence_links}
        evidence_by_id = {item.id: item for item in rows.evidence_items}
        claim_links = [
            item
            for item in rows.hypothesis_claim_links
            if item.hypothesis_revision_id == revision.id
            and _recorded_visible(item.recorded_at_utc, cutoff)
        ]
        claim_links.sort(key=lambda item: (str(item.claim_revision_id), str(item.id)))
        evidence_boundaries = [
            item
            for item in rows.hypothesis_evidence_links
            if item.hypothesis_revision_id == revision.id
            and _recorded_visible(item.recorded_at_utc, cutoff)
        ]
        claims: list[dict[str, Any]] = []
        conflicts: list[dict[str, Any]] = []
        missing: list[dict[str, Any]] = []
        grades: Counter[str] = Counter()
        for claim_link in claim_links:
            claim_revision = claim_by_id[claim_link.claim_revision_id]
            claim = claim_identity[claim_revision.claim_id]
            evidence_payload: list[dict[str, Any]] = []
            for boundary in evidence_boundaries:
                if boundary.claim_revision_id != claim_revision.id:
                    continue
                source_link = link_by_id[boundary.claim_evidence_link_id]
                evidence = evidence_by_id[boundary.evidence_id]
                item = {
                    "claim_evidence_link_id": str(source_link.id),
                    "evidence_id": str(evidence.id),
                    "evidence_grade": evidence.evidence_grade,
                    "relation": source_link.relation,
                    "source_title": evidence.source_title,
                    "information_date": _date(evidence.information_date),
                    "recorded_at_utc": _timestamp(evidence.recorded_at_utc),
                }
                evidence_payload.append(item)
                grades[evidence.evidence_grade] += 1
                if source_link.relation == "contradicts":
                    conflicts.append(
                        {
                            "hypothesis_revision_id": str(revision.id),
                            "claim_revision_id": str(claim_revision.id),
                            "claim_key": claim.claim_key,
                            "evidence_id": str(evidence.id),
                            "evidence_grade": evidence.evidence_grade,
                            "source_title": evidence.source_title,
                        }
                    )
            evidence_payload.sort(
                key=lambda item: (
                    item["relation"], item["evidence_grade"], item["evidence_id"]
                )
            )
            if not evidence_payload:
                missing.append(
                    {
                        "hypothesis_revision_id": str(revision.id),
                        "claim_revision_id": str(claim_revision.id),
                        "claim_key": claim.claim_key,
                        "reason": "no evidence was frozen at the hypothesis revision boundary",
                    }
                )
            claims.append(
                {
                    "claim_id": str(claim.id),
                    "claim_key": claim.claim_key,
                    "claim_revision_id": str(claim_revision.id),
                    "revision_no": claim_revision.revision_no,
                    "statement": claim_revision.statement,
                    "claim_status": claim_revision.claim_status,
                    "information_cutoff_date": _date(
                        claim_revision.information_cutoff_date
                    ),
                    "evidence": evidence_payload,
                }
            )
        claims.sort(key=lambda item: (item["claim_key"], item["revision_no"]))
        conflicts.sort(key=lambda item: (item["claim_key"], item["evidence_id"]))
        missing.sort(key=lambda item: (item["claim_key"], item["claim_revision_id"]))
        return {
            "hypothesis_revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "hypothesis_status": revision.hypothesis_status,
            "mechanism": revision.mechanism,
            "direction": revision.direction,
            "operating_metric": revision.operating_metric,
            "financial_statement_line": revision.financial_statement_line,
            "expected_lag_horizon": revision.expected_lag_horizon,
            "confidence": revision.confidence,
            "basis": revision.basis,
            "information_cutoff_date": _date(revision.information_cutoff_date),
            "recorded_at_utc": _timestamp(revision.recorded_at_utc),
            "supersedes_revision_id": _uuid(revision.supersedes_revision_id),
            "claims": claims,
            "evidence_grade_counts": {
                grade: grades[grade] for grade in ("A", "B", "C", "D")
            },
            "conflicts": conflicts,
            "missing_evidence": missing,
        }

    @staticmethod
    def _handoff_payload(rows: Stage2Rows) -> dict[str, Any]:
        claims = {item.id: item for item in rows.claim_revisions}
        claim_identities = {item.id: item for item in rows.claims}
        source_links = {item.id: item for item in rows.claim_evidence_links}
        evidence = {item.id: item for item in rows.evidence_items}
        frozen_claims: list[dict[str, Any]] = []
        conflicts: list[dict[str, Any]] = []
        missing: list[dict[str, Any]] = []
        for handoff_link in rows.handoff_claim_links:
            revision = claims[handoff_link.claim_revision_id]
            identity = claim_identities[revision.claim_id]
            boundary = [
                item
                for item in rows.handoff_evidence_links
                if item.claim_revision_id == revision.id
            ]
            evidence_payload = []
            for item in boundary:
                link = source_links[item.claim_evidence_link_id]
                source = evidence[item.evidence_id]
                evidence_payload.append(
                    {
                        "claim_evidence_link_id": str(link.id),
                        "evidence_id": str(source.id),
                        "evidence_grade": source.evidence_grade,
                        "relation": link.relation,
                        "source_title": source.source_title,
                    }
                )
                if link.relation == "contradicts":
                    conflicts.append(
                        {
                            "claim_key": identity.claim_key,
                            "evidence_id": str(source.id),
                            "source_title": source.source_title,
                        }
                    )
            evidence_payload.sort(
                key=lambda item: (
                    item["relation"], item["evidence_grade"], item["evidence_id"]
                )
            )
            if not evidence_payload:
                missing.append(
                    {
                        "claim_revision_id": str(revision.id),
                        "claim_key": identity.claim_key,
                        "reason": "no evidence was visible at the accepted Stage 2 handoff boundary",
                    }
                )
            frozen_claims.append(
                {
                    "claim_id": str(identity.id),
                    "claim_key": identity.claim_key,
                    "claim_revision_id": str(revision.id),
                    "claim_status": revision.claim_status,
                    "evidence": evidence_payload,
                }
            )
        frozen_claims.sort(key=lambda item: (item["claim_key"], item["claim_revision_id"]))
        assertion_payload = []
        for link in rows.assertion_links:
            if link.node_revision_id is not None:
                kind, revision_id = "node", link.node_revision_id
            elif link.relationship_revision_id is not None:
                kind, revision_id = "relationship", link.relationship_revision_id
            else:
                kind, revision_id = "observation", link.observation_revision_id
            assertion_payload.append(
                {
                    "stage1_assertion_link_id": str(link.id),
                    "assertion_kind": kind,
                    "assertion_revision_id": str(revision_id),
                    "recorded_at_utc": _timestamp(link.recorded_at_utc),
                }
            )
        assertion_payload.sort(
            key=lambda item: (item["assertion_kind"], item["assertion_revision_id"])
        )
        return {
            "candidate_pool": {
                "candidate_pool_id": str(rows.pool.id),
                "candidate_pool_revision_id": str(rows.pool_revision.id),
                "revision_no": rows.pool_revision.revision_no,
                "candidate_pool_membership_id": str(rows.membership.id),
                "information_cutoff_date": _date(
                    rows.pool_revision.information_cutoff_date
                ),
                "recorded_at_utc": _timestamp(rows.pool_revision.recorded_at_utc),
            },
            "beneficiary": {
                "beneficiary_id": str(rows.beneficiary.id),
                "beneficiary_revision_id": str(rows.beneficiary_revision.id),
                "revision_no": rows.beneficiary_revision.revision_no,
                "beneficiary_kind": rows.beneficiary_revision.beneficiary_kind,
                "assessment_status": rows.beneficiary_revision.assessment_status,
                "selected_map_revision_id": str(rows.map_revision.id),
            },
            "company_snapshot": {
                "stock_basic_record_id": rows.stock.id,
                "stock_code": rows.stock.stock_code,
                "stock_name": rows.stock.stock_name,
                "source": rows.stock.source,
                "ingestion_run_id": rows.ingestion_run.id,
                "provider": rows.ingestion_run.provider,
                "series_key": rows.ingestion_run.series_key,
                "information_cutoff_date": _date(
                    rows.ingestion_run.information_cutoff_date
                ),
                "completed_at_utc": _timestamp(rows.ingestion_run.completed_at),
            },
            "map_assertions": assertion_payload,
            "frozen_claims": frozen_claims,
            "conflicts": sorted(conflicts, key=lambda item: (item["claim_key"], item["evidence_id"])),
            "missing_evidence": sorted(missing, key=lambda item: item["claim_key"]),
        }


def _dated_visible(
    information_date: date, recorded_at: datetime, cutoff: date | None
) -> bool:
    return cutoff is None or (
        information_date <= cutoff and _stored_utc(recorded_at).date() <= cutoff
    )


def _recorded_visible(recorded_at: datetime, cutoff: date | None) -> bool:
    return cutoff is None or _stored_utc(recorded_at).date() <= cutoff


def _stored_utc(value: datetime | None) -> datetime:
    if value is None:
        raise EvidenceLedgerNotVisible("required UTC timestamp is unavailable.")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime | None) -> str:
    return _stored_utc(value).isoformat().replace("+00:00", "Z")


def _date(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def _uuid(value: UUID | None) -> str | None:
    return None if value is None else str(value)
