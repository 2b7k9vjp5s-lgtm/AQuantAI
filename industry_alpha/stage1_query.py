"""Cutoff-aware deterministic reads for Stage 1 beneficiaries and pools."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerNotVisible
from industry_alpha.stage1_contracts import (
    Stage1BeneficiaryDetailContract,
    Stage1BeneficiaryListContract,
    Stage1CandidatePoolDetailContract,
    Stage1CandidatePoolListContract,
)
from industry_alpha.stage1_repository import (
    Stage1BeneficiaryRepository,
    Stage1MapRows,
)

STAGE1_NOTICES = {
    "read_only": True,
    "purpose": "Local Stage 1 research classifications only; not investment advice.",
    "classification_boundary": (
        "Beneficiary kinds are descriptive classifications, not scores, weights, "
        "rankings, recommendations, or investment-priority labels."
    ),
    "candidate_pool_boundary": (
        "The frozen candidate pool is an unranked handoff for separately authorized "
        "Stage 2 research; membership is not a recommendation."
    ),
    "unsupported": [
        "company financial-transmission analysis",
        "valuation or investment-attractiveness ranking",
        "recommendations, signals, brokers, orders, or trading",
    ],
    "allowed_actions": ["read_stage1_classifications"],
}


class Stage1BeneficiaryQueryService:
    def __init__(self, repository: Stage1BeneficiaryRepository) -> None:
        self._repository = repository

    def list_beneficiaries(
        self, map_id: UUID, *, as_of_cutoff: date | None = None
    ) -> Stage1BeneficiaryListContract:
        rows = self._repository.load_map(map_id)
        if rows is None:
            raise EvidenceLedgerNotFound(f"Industry map {map_id} was not found.")
        payload: list[dict[str, Any]] = []
        revisions_by_identity = self._beneficiary_revisions_by_identity(rows)
        stock_by_id = {item.id: item for item in rows.stock_records}
        for beneficiary in rows.beneficiaries:
            visible = [
                item
                for item in revisions_by_identity.get(beneficiary.id, [])
                if _dated_visible(
                    item.information_cutoff_date,
                    item.recorded_at_utc,
                    as_of_cutoff,
                )
            ]
            if not visible:
                continue
            latest = visible[-1]
            company = stock_by_id[latest.stock_basic_record_id]
            payload.append(
                {
                    "beneficiary_id": str(beneficiary.id),
                    "case_id": str(beneficiary.case_id),
                    "map_id": str(beneficiary.map_id),
                    "source": beneficiary.source,
                    "stock_code": beneficiary.stock_code,
                    "stock_name": company.stock_name,
                    "created_at_utc": _timestamp(beneficiary.created_at_utc),
                    "latest_revision": self._beneficiary_revision_summary(latest),
                }
            )
        payload.sort(
            key=lambda item: (
                item["latest_revision"]["beneficiary_kind"],
                item["source"],
                item["stock_code"],
                item["beneficiary_id"],
            )
        )
        return Stage1BeneficiaryListContract(
            map_id=str(map_id),
            as_of_cutoff=_date(as_of_cutoff),
            beneficiaries=tuple(payload),
            notices=STAGE1_NOTICES,
        )

    def get_beneficiary(
        self, beneficiary_id: UUID, *, as_of_cutoff: date | None = None
    ) -> Stage1BeneficiaryDetailContract:
        map_id = self._repository.find_beneficiary_map_id(beneficiary_id)
        if map_id is None:
            raise EvidenceLedgerNotFound(
                f"Stage 1 beneficiary {beneficiary_id} was not found."
            )
        rows = self._repository.load_map(map_id)
        beneficiary = next(
            (item for item in rows.beneficiaries if item.id == beneficiary_id), None
        )
        if beneficiary is None:
            raise EvidenceLedgerNotFound(
                f"Stage 1 beneficiary {beneficiary_id} was not found."
            )
        revisions = [
            item
            for item in rows.beneficiary_revisions
            if item.beneficiary_id == beneficiary_id
            and _dated_visible(
                item.information_cutoff_date, item.recorded_at_utc, as_of_cutoff
            )
        ]
        if not revisions:
            raise EvidenceLedgerNotVisible(
                f"Stage 1 beneficiary {beneficiary_id} has no revision visible at the requested cutoff."
            )
        history = tuple(
            self._beneficiary_revision_payload(rows, item, as_of_cutoff)
            for item in revisions
        )
        return Stage1BeneficiaryDetailContract(
            beneficiary={
                "beneficiary_id": str(beneficiary.id),
                "case_id": str(beneficiary.case_id),
                "map_id": str(beneficiary.map_id),
                "source": beneficiary.source,
                "stock_code": beneficiary.stock_code,
                "created_at_utc": _timestamp(beneficiary.created_at_utc),
            },
            as_of_cutoff=_date(as_of_cutoff),
            latest_revision=history[-1],
            revision_history=history,
            notices=STAGE1_NOTICES,
        )

    def list_candidate_pools(
        self, map_id: UUID, *, as_of_cutoff: date | None = None
    ) -> Stage1CandidatePoolListContract:
        rows = self._repository.load_map(map_id)
        if rows is None:
            raise EvidenceLedgerNotFound(f"Industry map {map_id} was not found.")
        payload: list[dict[str, Any]] = []
        for pool in rows.candidate_pools:
            revisions = [
                item
                for item in rows.candidate_pool_revisions
                if item.candidate_pool_id == pool.id
                and _dated_visible(
                    item.information_cutoff_date,
                    item.recorded_at_utc,
                    as_of_cutoff,
                )
            ]
            if not revisions:
                continue
            latest = revisions[-1]
            members = self._visible_memberships(rows, latest, as_of_cutoff)
            payload.append(
                {
                    "candidate_pool_id": str(pool.id),
                    "case_id": str(pool.case_id),
                    "map_id": str(pool.map_id),
                    "pool_key": pool.pool_key,
                    "created_at_utc": _timestamp(pool.created_at_utc),
                    "latest_revision": self._pool_revision_summary(latest, members),
                }
            )
        payload.sort(key=lambda item: (item["pool_key"], item["candidate_pool_id"]))
        return Stage1CandidatePoolListContract(
            map_id=str(map_id),
            as_of_cutoff=_date(as_of_cutoff),
            candidate_pools=tuple(payload),
            notices=STAGE1_NOTICES,
        )

    def get_candidate_pool(
        self, pool_id: UUID, *, as_of_cutoff: date | None = None
    ) -> Stage1CandidatePoolDetailContract:
        map_id = self._repository.find_candidate_pool_map_id(pool_id)
        if map_id is None:
            raise EvidenceLedgerNotFound(
                f"Stage 1 candidate pool {pool_id} was not found."
            )
        rows = self._repository.load_map(map_id)
        pool = next((item for item in rows.candidate_pools if item.id == pool_id), None)
        if pool is None:
            raise EvidenceLedgerNotFound(
                f"Stage 1 candidate pool {pool_id} was not found."
            )
        revisions = [
            item
            for item in rows.candidate_pool_revisions
            if item.candidate_pool_id == pool_id
            and _dated_visible(
                item.information_cutoff_date, item.recorded_at_utc, as_of_cutoff
            )
        ]
        if not revisions:
            raise EvidenceLedgerNotVisible(
                f"Stage 1 candidate pool {pool_id} has no revision visible at the requested cutoff."
            )
        history = tuple(
            self._pool_revision_summary(
                item, self._visible_memberships(rows, item, as_of_cutoff)
            )
            for item in revisions
        )
        latest = revisions[-1]
        beneficiary_by_id = {item.id: item for item in rows.beneficiaries}
        revision_by_id = {item.id: item for item in rows.beneficiary_revisions}
        candidates: list[dict[str, Any]] = []
        for membership in self._visible_memberships(rows, latest, as_of_cutoff):
            beneficiary = beneficiary_by_id[membership.beneficiary_id]
            revision = revision_by_id[membership.beneficiary_revision_id]
            candidates.append(
                {
                    "membership_id": str(membership.id),
                    "recorded_at_utc": _timestamp(membership.recorded_at_utc),
                    "beneficiary": {
                        "beneficiary_id": str(beneficiary.id),
                        "source": beneficiary.source,
                        "stock_code": beneficiary.stock_code,
                    },
                    "frozen_beneficiary_revision": self._beneficiary_revision_payload(
                        rows, revision, as_of_cutoff
                    ),
                }
            )
        candidates.sort(
            key=lambda item: (
                item["frozen_beneficiary_revision"]["beneficiary_kind"],
                item["beneficiary"]["source"],
                item["beneficiary"]["stock_code"],
                item["beneficiary"]["beneficiary_id"],
            )
        )
        return Stage1CandidatePoolDetailContract(
            candidate_pool={
                "candidate_pool_id": str(pool.id),
                "case_id": str(pool.case_id),
                "map_id": str(pool.map_id),
                "pool_key": pool.pool_key,
                "created_at_utc": _timestamp(pool.created_at_utc),
            },
            as_of_cutoff=_date(as_of_cutoff),
            latest_revision=history[-1],
            revision_history=history,
            frozen_candidates=tuple(candidates),
            notices=STAGE1_NOTICES,
        )

    @staticmethod
    def _beneficiary_revisions_by_identity(
        rows: Stage1MapRows,
    ) -> dict[UUID, list[Any]]:
        grouped: dict[UUID, list[Any]] = {}
        for revision in rows.beneficiary_revisions:
            grouped.setdefault(revision.beneficiary_id, []).append(revision)
        return grouped

    @staticmethod
    def _beneficiary_revision_summary(revision: Any) -> dict[str, Any]:
        return {
            "revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "beneficiary_kind": revision.beneficiary_kind,
            "assessment_status": revision.assessment_status,
            "information_cutoff_date": _date(revision.information_cutoff_date),
            "recorded_at_utc": _timestamp(revision.recorded_at_utc),
            "selected_map_revision_id": str(revision.selected_map_revision_id),
        }

    def _beneficiary_revision_payload(
        self, rows: Stage1MapRows, revision: Any, cutoff: date | None
    ) -> dict[str, Any]:
        map_revision = next(
            item
            for item in rows.map_revisions
            if item.id == revision.selected_map_revision_id
        )
        stock = next(
            item
            for item in rows.stock_records
            if item.id == revision.stock_basic_record_id
        )
        run = next(
            item for item in rows.ingestion_runs if item.id == stock.ingestion_run_id
        )
        assertions = self._assertion_payloads(rows, revision, cutoff)
        claims, grade_counts, conflicts, missing = self._claim_payloads(
            rows, revision, cutoff
        )
        return {
            "revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "beneficiary_kind": revision.beneficiary_kind,
            "assessment_status": revision.assessment_status,
            "rationale_summary": revision.rationale_summary,
            "information_cutoff_date": _date(revision.information_cutoff_date),
            "recorded_at_utc": _timestamp(revision.recorded_at_utc),
            "supersedes_revision_id": _uuid(revision.supersedes_revision_id),
            "selected_map_revision": {
                "map_revision_id": str(map_revision.id),
                "revision_no": map_revision.revision_no,
                "title": map_revision.title,
                "information_cutoff_date": _date(
                    map_revision.information_cutoff_date
                ),
                "recorded_at_utc": _timestamp(map_revision.recorded_at_utc),
            },
            "company_snapshot": {
                "stock_basic_record_id": stock.id,
                "stock_code": stock.stock_code,
                "stock_name": stock.stock_name,
                "exchange": stock.exchange,
                "industry": stock.industry,
                "listing_date": _date(stock.listing_date),
                "status": stock.status,
                "source": stock.source,
                "ingestion_run_id": run.id,
                "series_key": run.series_key,
                "provider": run.provider,
                "information_cutoff_date": _date(run.information_cutoff_date),
                "completed_at_utc": _timestamp(run.completed_at),
            },
            "map_assertions": assertions,
            "claims": claims,
            "evidence_summary": {
                "grade_counts": grade_counts,
                "conflict_count": len(conflicts),
                "missing_evidence_claim_count": len(missing),
            },
            "conflicts": conflicts,
            "missing_evidence": missing,
        }

    @staticmethod
    def _assertion_payloads(
        rows: Stage1MapRows, beneficiary_revision: Any, cutoff: date | None
    ) -> list[dict[str, Any]]:
        node_revisions = {item.id: item for item in rows.node_revisions}
        relationship_revisions = {
            item.id: item for item in rows.relationship_revisions
        }
        observation_revisions = {
            item.id: item for item in rows.observation_revisions
        }
        nodes = {item.id: item for item in rows.nodes}
        relationships = {item.id: item for item in rows.relationships}
        observations = {item.id: item for item in rows.observations}
        payload: list[dict[str, Any]] = []
        for link in rows.assertion_links:
            if (
                link.beneficiary_revision_id != beneficiary_revision.id
                or not _recorded_visible(link.recorded_at_utc, cutoff)
                or _stored_utc(link.recorded_at_utc)
                > _stored_utc(beneficiary_revision.recorded_at_utc)
            ):
                continue
            if link.node_revision_id is not None:
                kind = "node"
                revision = node_revisions[link.node_revision_id]
                identity = nodes[revision.node_id]
                key = identity.node_key
                detail = {"label": revision.label, "node_kind": revision.node_kind}
            elif link.relationship_revision_id is not None:
                kind = "relationship"
                revision = relationship_revisions[link.relationship_revision_id]
                identity = relationships[revision.relationship_id]
                key = identity.relationship_key
                detail = {"relation_kind": revision.relation_kind}
            else:
                kind = "observation"
                revision = observation_revisions[link.observation_revision_id]
                identity = observations[revision.observation_id]
                key = identity.observation_key
                detail = {
                    "title": revision.title,
                    "observation_kind": identity.observation_kind,
                }
            item = {
                "assertion_kind": kind,
                "assertion_key": key,
                "assertion_revision_id": str(revision.id),
                "revision_no": revision.revision_no,
                "assertion_status": revision.assertion_status,
                "information_cutoff_date": _date(
                    revision.information_cutoff_date
                ),
                "recorded_at_utc": _timestamp(revision.recorded_at_utc),
                "link_recorded_at_utc": _timestamp(link.recorded_at_utc),
            }
            item.update(detail)
            payload.append(item)
        payload.sort(
            key=lambda item: (
                item["assertion_kind"],
                item["assertion_key"],
                item["assertion_revision_id"],
            )
        )
        return payload

    @staticmethod
    def _claim_payloads(
        rows: Stage1MapRows, beneficiary_revision: Any, cutoff: date | None
    ) -> tuple[list[dict[str, Any]], dict[str, int], list[dict[str, Any]], list[dict[str, Any]]]:
        claim_revisions = {item.id: item for item in rows.claim_revisions}
        claims = {item.id: item for item in rows.claims}
        evidence_items = {item.id: item for item in rows.evidence_items}
        grade_counter: Counter[str] = Counter()
        payload: list[dict[str, Any]] = []
        conflicts: list[dict[str, Any]] = []
        missing: list[dict[str, Any]] = []
        links = [
            item
            for item in rows.claim_links
            if item.beneficiary_revision_id == beneficiary_revision.id
            and _recorded_visible(item.recorded_at_utc, cutoff)
            and _stored_utc(item.recorded_at_utc)
            <= _stored_utc(beneficiary_revision.recorded_at_utc)
        ]
        links.sort(key=lambda item: (str(item.claim_revision_id), str(item.id)))
        for link in links:
            claim_revision = claim_revisions[link.claim_revision_id]
            claim = claims[claim_revision.claim_id]
            evidence_payload: list[dict[str, Any]] = []
            for evidence_link in rows.claim_evidence_links:
                if evidence_link.claim_revision_id != claim_revision.id:
                    continue
                evidence = evidence_items.get(evidence_link.evidence_id)
                if (
                    evidence is None
                    or evidence.information_date
                    > beneficiary_revision.information_cutoff_date
                    or evidence.information_date
                    > claim_revision.information_cutoff_date
                    or not _dated_visible(
                        evidence.information_date,
                        evidence.recorded_at_utc,
                        cutoff,
                    )
                    or not _recorded_visible(evidence_link.recorded_at_utc, cutoff)
                    or _stored_utc(evidence.recorded_at_utc)
                    > _stored_utc(beneficiary_revision.recorded_at_utc)
                    or _stored_utc(evidence_link.recorded_at_utc)
                    > _stored_utc(beneficiary_revision.recorded_at_utc)
                ):
                    continue
                evidence_item = {
                    "evidence_id": str(evidence.id),
                    "evidence_grade": evidence.evidence_grade,
                    "relation": evidence_link.relation,
                    "source_title": evidence.source_title,
                    "information_date": _date(evidence.information_date),
                    "recorded_at_utc": _timestamp(evidence.recorded_at_utc),
                    "link_recorded_at_utc": _timestamp(
                        evidence_link.recorded_at_utc
                    ),
                }
                evidence_payload.append(evidence_item)
                grade_counter[evidence.evidence_grade] += 1
                if evidence_link.relation == "contradicts":
                    conflicts.append(
                        {
                            "claim_revision_id": str(claim_revision.id),
                            "claim_key": claim.claim_key,
                            "evidence_id": str(evidence.id),
                            "evidence_grade": evidence.evidence_grade,
                            "source_title": evidence.source_title,
                        }
                    )
            evidence_payload.sort(
                key=lambda item: (
                    item["relation"],
                    item["evidence_grade"],
                    item["evidence_id"],
                )
            )
            if not evidence_payload:
                missing.append(
                    {
                        "claim_revision_id": str(claim_revision.id),
                        "claim_key": claim.claim_key,
                        "reason": "linked claim revision has no evidence visible at the beneficiary revision boundary",
                    }
                )
            payload.append(
                {
                    "claim_id": str(claim.id),
                    "claim_key": claim.claim_key,
                    "claim_revision_id": str(claim_revision.id),
                    "revision_no": claim_revision.revision_no,
                    "statement": claim_revision.statement,
                    "claim_kind": claim_revision.claim_kind,
                    "claim_status": claim_revision.claim_status,
                    "information_cutoff_date": _date(
                        claim_revision.information_cutoff_date
                    ),
                    "recorded_at_utc": _timestamp(
                        claim_revision.recorded_at_utc
                    ),
                    "beneficiary_link_recorded_at_utc": _timestamp(
                        link.recorded_at_utc
                    ),
                    "evidence": evidence_payload,
                }
            )
        payload.sort(key=lambda item: (item["claim_key"], item["revision_no"]))
        conflicts.sort(
            key=lambda item: (
                item["claim_key"],
                item["evidence_id"],
            )
        )
        missing.sort(key=lambda item: (item["claim_key"], item["claim_revision_id"]))
        return (
            payload,
            {grade: grade_counter[grade] for grade in ("A", "B", "C", "D")},
            conflicts,
            missing,
        )

    @staticmethod
    def _pool_revision_summary(
        revision: Any, memberships: list[Any]
    ) -> dict[str, Any]:
        return {
            "revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "title": revision.title,
            "scope": revision.scope,
            "information_cutoff_date": _date(revision.information_cutoff_date),
            "recorded_at_utc": _timestamp(revision.recorded_at_utc),
            "supersedes_revision_id": _uuid(revision.supersedes_revision_id),
            "selected_map_revision_id": str(revision.selected_map_revision_id),
            "candidate_count": len(memberships),
            "beneficiary_revision_ids": sorted(
                str(item.beneficiary_revision_id) for item in memberships
            ),
        }

    @staticmethod
    def _visible_memberships(
        rows: Stage1MapRows, revision: Any, cutoff: date | None
    ) -> list[Any]:
        memberships = [
            item
            for item in rows.memberships
            if item.candidate_pool_revision_id == revision.id
            and _recorded_visible(item.recorded_at_utc, cutoff)
            and _stored_utc(item.recorded_at_utc)
            <= _stored_utc(revision.recorded_at_utc)
        ]
        memberships.sort(
            key=lambda item: (
                str(item.beneficiary_id),
                str(item.beneficiary_revision_id),
                str(item.id),
            )
        )
        return memberships


def _dated_visible(
    information_date: date, recorded_at: datetime, cutoff: date | None
) -> bool:
    return cutoff is None or (
        information_date <= cutoff and _utc_date(recorded_at) <= cutoff
    )


def _recorded_visible(recorded_at: datetime, cutoff: date | None) -> bool:
    return cutoff is None or _utc_date(recorded_at) <= cutoff


def _utc_date(value: datetime) -> date:
    return _stored_utc(value).date()


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
