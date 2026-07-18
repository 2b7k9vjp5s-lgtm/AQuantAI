"""Cutoff-aware deterministic reads for evidence-backed industry maps."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from industry_alpha.chain_map_contracts import (
    IndustryMapDetailContract,
    IndustryMapListContract,
)
from industry_alpha.chain_map_repository import (
    IndustryChainMapRepository,
    IndustryMapRows,
)
from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerNotVisible

MAP_NOTICES = {
    "read_only": True,
    "purpose": "Local evidence-backed industry research only; not investment advice.",
    "evidence_boundary": "Every map assertion references exact v0.5A claim revisions.",
    "d_grade_boundary": "D-grade evidence cannot independently support an assertion.",
    "conflict_visibility": "Conflicts and missing evidence remain explicit.",
    "unsupported": [
        "industry scoring or ranking",
        "company beneficiary mapping",
        "Stage 2 stock research",
        "recommendations, signals, brokers, orders, or trading",
    ],
    "allowed_actions": ["read_industry_chain_map"],
}


class IndustryChainMapQueryService:
    def __init__(self, repository: IndustryChainMapRepository) -> None:
        self._repository = repository

    def list_maps(
        self, *, as_of_cutoff: date | None = None
    ) -> IndustryMapListContract:
        payload: list[dict[str, Any]] = []
        for industry_map in self._repository.list_maps():
            rows = self._repository.load_map(industry_map.id)
            if rows is None:
                continue
            revisions = self._visible_map_revisions(rows, as_of_cutoff)
            if not revisions:
                continue
            latest = revisions[-1]
            memberships = self._visible_memberships(rows, latest, as_of_cutoff)
            payload.append(
                {
                    "map_id": str(industry_map.id),
                    "case_id": str(industry_map.case_id),
                    "map_key": industry_map.map_key,
                    "created_at_utc": _timestamp(industry_map.created_at_utc),
                    "latest_revision": self._map_revision_dict(
                        latest, memberships
                    ),
                }
            )
        payload.sort(key=lambda item: (item["map_key"], item["map_id"]))
        return IndustryMapListContract(
            as_of_cutoff=_date(as_of_cutoff),
            maps=tuple(payload),
            notices=MAP_NOTICES,
        )

    def get_map(
        self, map_id: UUID, *, as_of_cutoff: date | None = None
    ) -> IndustryMapDetailContract:
        rows = self._repository.load_map(map_id)
        if rows is None:
            raise EvidenceLedgerNotFound(f"Industry map {map_id} was not found.")
        revisions = self._visible_map_revisions(rows, as_of_cutoff)
        if not revisions:
            raise EvidenceLedgerNotVisible(
                f"Industry map {map_id} has no revision visible at the requested cutoff."
            )
        latest = revisions[-1]
        memberships = self._visible_memberships(rows, latest, as_of_cutoff)
        evidence_ids_by_grade: dict[str, set[UUID]] = {
            grade: set() for grade in ("A", "B", "C", "D")
        }
        conflicts: list[dict[str, Any]] = []
        missing: list[dict[str, Any]] = []

        node_by_id = {item.id: item for item in rows.nodes}
        relationship_by_id = {item.id: item for item in rows.relationships}
        observation_by_id = {item.id: item for item in rows.observations}
        node_revision_by_id = {
            item.id: item
            for item in rows.node_revisions
            if _dated_visible(
                item.information_cutoff_date, item.recorded_at_utc, as_of_cutoff
            )
        }
        relationship_revision_by_id = {
            item.id: item
            for item in rows.relationship_revisions
            if _dated_visible(
                item.information_cutoff_date, item.recorded_at_utc, as_of_cutoff
            )
        }
        observation_revision_by_id = {
            item.id: item
            for item in rows.observation_revisions
            if _dated_visible(
                item.information_cutoff_date, item.recorded_at_utc, as_of_cutoff
            )
        }

        nodes: list[dict[str, Any]] = []
        relationships: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        for membership in memberships:
            if membership.node_revision_id is not None:
                revision = node_revision_by_id.get(membership.node_revision_id)
                if revision is None:
                    continue
                identity = node_by_id[revision.node_id]
                assertion = self._assertion_payload(
                    rows,
                    "node",
                    revision,
                    latest,
                    as_of_cutoff,
                    evidence_ids_by_grade,
                    conflicts,
                    missing,
                )
                nodes.append(
                    {
                        "node_id": str(identity.id),
                        "node_key": identity.node_key,
                        "created_at_utc": _timestamp(identity.created_at_utc),
                        "revision": assertion,
                    }
                )
            elif membership.relationship_revision_id is not None:
                revision = relationship_revision_by_id.get(
                    membership.relationship_revision_id
                )
                if revision is None:
                    continue
                identity = relationship_by_id[revision.relationship_id]
                assertion = self._assertion_payload(
                    rows,
                    "relationship",
                    revision,
                    latest,
                    as_of_cutoff,
                    evidence_ids_by_grade,
                    conflicts,
                    missing,
                )
                relationships.append(
                    {
                        "relationship_id": str(identity.id),
                        "relationship_key": identity.relationship_key,
                        "source_node_id": str(identity.source_node_id),
                        "source_node_key": node_by_id[identity.source_node_id].node_key,
                        "target_node_id": str(identity.target_node_id),
                        "target_node_key": node_by_id[identity.target_node_id].node_key,
                        "created_at_utc": _timestamp(identity.created_at_utc),
                        "revision": assertion,
                    }
                )
            elif membership.observation_revision_id is not None:
                revision = observation_revision_by_id.get(
                    membership.observation_revision_id
                )
                if revision is None:
                    continue
                identity = observation_by_id[revision.observation_id]
                assertion = self._assertion_payload(
                    rows,
                    "observation",
                    revision,
                    latest,
                    as_of_cutoff,
                    evidence_ids_by_grade,
                    conflicts,
                    missing,
                )
                observations.append(
                    {
                        "observation_id": str(identity.id),
                        "observation_key": identity.observation_key,
                        "observation_kind": identity.observation_kind,
                        "created_at_utc": _timestamp(identity.created_at_utc),
                        "revision": assertion,
                    }
                )
        nodes.sort(key=lambda item: (item["node_key"], item["node_id"]))
        relationships.sort(
            key=lambda item: (item["relationship_key"], item["relationship_id"])
        )
        observations.sort(
            key=lambda item: (
                item["observation_kind"],
                item["observation_key"],
                item["observation_id"],
            )
        )
        conflicts.sort(
            key=lambda item: (
                item["assertion_kind"],
                item["assertion_revision_id"],
                item["claim_key"],
                item["evidence_id"],
            )
        )
        missing.sort(
            key=lambda item: (
                item["assertion_kind"],
                item["assertion_revision_id"],
                item["claim_key"],
            )
        )
        history = tuple(
            self._map_revision_dict(
                revision,
                self._visible_memberships(rows, revision, as_of_cutoff),
            )
            for revision in revisions
        )
        return IndustryMapDetailContract(
            industry_map={
                "map_id": str(rows.industry_map.id),
                "case_id": str(rows.industry_map.case_id),
                "map_key": rows.industry_map.map_key,
                "created_at_utc": _timestamp(rows.industry_map.created_at_utc),
            },
            as_of_cutoff=_date(as_of_cutoff),
            latest_revision=self._map_revision_dict(latest, memberships),
            revision_history=history,
            frozen_snapshot={
                "map_revision_id": str(latest.id),
                "nodes": nodes,
                "relationships": relationships,
                "observations": observations,
                "counts": {
                    "nodes": len(nodes),
                    "relationships": len(relationships),
                    "drivers": sum(
                        item["observation_kind"] == "driver" for item in observations
                    ),
                    "bottlenecks": sum(
                        item["observation_kind"] == "bottleneck"
                        for item in observations
                    ),
                    "value_pool_shifts": sum(
                        item["observation_kind"] == "value_pool_shift"
                        for item in observations
                    ),
                },
            },
            evidence_grade_summary={
                grade: len(evidence_ids_by_grade[grade])
                for grade in ("A", "B", "C", "D")
            },
            conflicts=tuple(conflicts),
            missing_evidence=tuple(missing),
            notices=MAP_NOTICES,
        )

    def _assertion_payload(
        self,
        rows: IndustryMapRows,
        kind: str,
        revision: Any,
        map_revision: Any,
        cutoff: date | None,
        evidence_ids_by_grade: dict[str, set[UUID]],
        conflicts: list[dict[str, Any]],
        missing: list[dict[str, Any]],
    ) -> dict[str, Any]:
        target_field = f"{kind}_revision_id"
        links = [
            link
            for link in rows.assertion_claim_links
            if getattr(link, target_field) == revision.id
            and _recorded_visible(link.recorded_at_utc, cutoff)
            and _stored_utc(link.recorded_at_utc)
            <= _stored_utc(map_revision.recorded_at_utc)
        ]
        links.sort(key=lambda item: (str(item.claim_revision_id), str(item.id)))
        claim_revision_by_id = {item.id: item for item in rows.claim_revisions}
        claim_by_id = {item.id: item for item in rows.claims}
        evidence_by_id = {item.id: item for item in rows.evidence_items}
        claims: list[dict[str, Any]] = []
        grade_counter: Counter[str] = Counter()
        conflict_count = 0
        missing_count = 0
        for link in links:
            claim_revision = claim_revision_by_id.get(link.claim_revision_id)
            if claim_revision is None or not _dated_visible(
                claim_revision.information_cutoff_date,
                claim_revision.recorded_at_utc,
                cutoff,
            ):
                continue
            claim = claim_by_id[claim_revision.claim_id]
            evidence_payload: list[dict[str, Any]] = []
            for evidence_link in rows.claim_evidence_links:
                if evidence_link.claim_revision_id != claim_revision.id:
                    continue
                evidence = evidence_by_id.get(evidence_link.evidence_id)
                if (
                    evidence is None
                    or not _dated_visible(
                        evidence.information_date, evidence.recorded_at_utc, cutoff
                    )
                    or not _recorded_visible(evidence_link.recorded_at_utc, cutoff)
                    or _stored_utc(evidence.recorded_at_utc)
                    > _stored_utc(map_revision.recorded_at_utc)
                    or _stored_utc(evidence_link.recorded_at_utc)
                    > _stored_utc(map_revision.recorded_at_utc)
                ):
                    continue
                item = {
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
                evidence_payload.append(item)
                grade_counter[evidence.evidence_grade] += 1
                evidence_ids_by_grade[evidence.evidence_grade].add(evidence.id)
                if evidence_link.relation == "contradicts":
                    conflict_count += 1
                    conflicts.append(
                        {
                            "assertion_kind": kind,
                            "assertion_revision_id": str(revision.id),
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
                missing_count += 1
                missing.append(
                    {
                        "assertion_kind": kind,
                        "assertion_revision_id": str(revision.id),
                        "claim_revision_id": str(claim_revision.id),
                        "claim_key": claim.claim_key,
                        "reason": "linked claim revision has no evidence visible in the frozen map revision",
                    }
                )
            claims.append(
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
                    "recorded_at_utc": _timestamp(claim_revision.recorded_at_utc),
                    "assertion_link_recorded_at_utc": _timestamp(
                        link.recorded_at_utc
                    ),
                    "evidence": evidence_payload,
                }
            )
        claims.sort(key=lambda item: (item["claim_key"], item["revision_no"]))
        base = {
            "revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "assertion_status": revision.assertion_status,
            "information_cutoff_date": _date(revision.information_cutoff_date),
            "recorded_at_utc": _timestamp(revision.recorded_at_utc),
            "supersedes_revision_id": _uuid(revision.supersedes_revision_id),
            "linked_claim_revisions": claims,
            "evidence_summary": {
                "linked_claim_count": len(claims),
                "grade_counts": {
                    grade: grade_counter[grade] for grade in ("A", "B", "C", "D")
                },
                "conflict_count": conflict_count,
                "missing_evidence_claim_count": missing_count,
            },
        }
        if kind == "node":
            base.update(
                {
                    "label": revision.label,
                    "description": revision.description,
                    "node_kind": revision.node_kind,
                }
            )
        elif kind == "relationship":
            base.update(
                {
                    "relation_kind": revision.relation_kind,
                    "description": revision.description,
                }
            )
        else:
            base.update(
                {"title": revision.title, "description": revision.description}
            )
        return base

    @staticmethod
    def _visible_map_revisions(
        rows: IndustryMapRows, cutoff: date | None
    ) -> list[Any]:
        return [
            item
            for item in rows.map_revisions
            if _dated_visible(
                item.information_cutoff_date, item.recorded_at_utc, cutoff
            )
        ]

    @staticmethod
    def _visible_memberships(
        rows: IndustryMapRows, revision: Any, cutoff: date | None
    ) -> list[Any]:
        memberships = [
            item
            for item in rows.memberships
            if item.map_revision_id == revision.id
            and _recorded_visible(item.recorded_at_utc, cutoff)
            and _stored_utc(item.recorded_at_utc)
            <= _stored_utc(revision.recorded_at_utc)
        ]
        memberships.sort(
            key=lambda item: (
                str(item.node_revision_id or ""),
                str(item.relationship_revision_id or ""),
                str(item.observation_revision_id or ""),
                str(item.id),
            )
        )
        return memberships

    @staticmethod
    def _map_revision_dict(
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
            "frozen_membership": {
                "node_revision_ids": sorted(
                    str(item.node_revision_id)
                    for item in memberships
                    if item.node_revision_id is not None
                ),
                "relationship_revision_ids": sorted(
                    str(item.relationship_revision_id)
                    for item in memberships
                    if item.relationship_revision_id is not None
                ),
                "observation_revision_ids": sorted(
                    str(item.observation_revision_id)
                    for item in memberships
                    if item.observation_revision_id is not None
                ),
            },
        }


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


def _stored_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return _stored_utc(value).isoformat().replace("+00:00", "Z")


def _date(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def _uuid(value: UUID | None) -> str | None:
    return None if value is None else str(value)
