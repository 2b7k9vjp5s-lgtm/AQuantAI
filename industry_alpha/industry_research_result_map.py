"""Exact-ID Industry Map Revision projection for accepted research history."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from industry_alpha.chain_map_models import (
    IndustryMap,
    IndustryMapNode,
    IndustryMapNodeRevision,
    IndustryMapObservation,
    IndustryMapObservationRevision,
    IndustryMapRelationship,
    IndustryMapRelationshipRevision,
    IndustryMapRevision,
    IndustryMapRevisionMembership,
)
from industry_alpha.industry_research_result_rules import (
    IndustryResearchResultError,
    stored_utc,
)


def _visible(
    cutoff: date,
    recorded_at: datetime,
    boundary_cutoff: date,
    boundary_recorded: datetime,
) -> bool:
    return cutoff <= boundary_cutoff and stored_utc(recorded_at) <= boundary_recorded


class ExactIndustryMapRevisionReader:
    def __init__(self, session: Session) -> None:
        self._session = session

    def read(
        self,
        map_revision_id: UUID,
        *,
        expected_map_id: UUID,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        revision = self._session.get(IndustryMapRevision, map_revision_id)
        if revision is None or revision.map_id != expected_map_id or not _visible(
            revision.information_cutoff_date,
            revision.recorded_at_utc,
            as_of_cutoff,
            as_of_recorded_at_utc,
        ):
            raise IndustryResearchResultError(
                "industry_research_result_map_revision_not_visible",
                "exact accepted Industry Map revision is missing or outside the boundary",
            )
        industry_map = self._session.get(IndustryMap, revision.map_id)
        if industry_map is None:
            raise IndustryResearchResultError(
                "industry_research_result_map_graph_incomplete",
                "exact Industry Map identity is missing",
            )
        memberships = list(
            self._session.scalars(
                select(IndustryMapRevisionMembership)
                .where(IndustryMapRevisionMembership.map_revision_id == revision.id)
                .order_by(IndustryMapRevisionMembership.id)
            )
        )
        for membership in memberships:
            if (
                stored_utc(membership.recorded_at_utc) > as_of_recorded_at_utc
                or stored_utc(membership.recorded_at_utc)
                > stored_utc(revision.recorded_at_utc)
            ):
                raise IndustryResearchResultError(
                    "industry_research_result_map_graph_incomplete",
                    "map membership is outside the exact revision chronology",
                )

        node_revision_ids = [
            item.node_revision_id for item in memberships if item.node_revision_id
        ]
        relationship_revision_ids = [
            item.relationship_revision_id
            for item in memberships
            if item.relationship_revision_id
        ]
        observation_revision_ids = [
            item.observation_revision_id
            for item in memberships
            if item.observation_revision_id
        ]
        node_revisions = self._load_by_id(
            IndustryMapNodeRevision,
            node_revision_ids,
        )
        relationship_revisions = self._load_by_id(
            IndustryMapRelationshipRevision,
            relationship_revision_ids,
        )
        observation_revisions = self._load_by_id(
            IndustryMapObservationRevision,
            observation_revision_ids,
        )
        nodes = self._load_by_id(
            IndustryMapNode,
            [item.node_id for item in node_revisions.values()],
        )
        relationships = self._load_by_id(
            IndustryMapRelationship,
            [item.relationship_id for item in relationship_revisions.values()],
        )
        observations = self._load_by_id(
            IndustryMapObservation,
            [item.observation_id for item in observation_revisions.values()],
        )
        endpoint_ids = {
            node_id
            for item in relationships.values()
            for node_id in (item.source_node_id, item.target_node_id)
        }
        missing_endpoint_ids = endpoint_ids - set(nodes)
        if missing_endpoint_ids:
            nodes.update(self._load_by_id(IndustryMapNode, list(missing_endpoint_ids)))

        output_nodes = []
        for revision_id in node_revision_ids:
            item = node_revisions.get(revision_id)
            identity = None if item is None else nodes.get(item.node_id)
            if (
                item is None
                or identity is None
                or identity.map_id != revision.map_id
                or not _visible(
                    item.information_cutoff_date,
                    item.recorded_at_utc,
                    as_of_cutoff,
                    as_of_recorded_at_utc,
                )
            ):
                raise IndustryResearchResultError(
                    "industry_research_result_map_graph_incomplete",
                    "node revision is missing or outside exact map scope",
                )
            output_nodes.append(
                {
                    "node_id": str(identity.id),
                    "node_key": identity.node_key,
                    "node_revision_id": str(item.id),
                    "revision_no": item.revision_no,
                    "label": item.label,
                    "description": item.description,
                    "node_kind": item.node_kind,
                    "assertion_status": item.assertion_status,
                }
            )

        output_relationships = []
        for revision_id in relationship_revision_ids:
            item = relationship_revisions.get(revision_id)
            identity = None if item is None else relationships.get(
                item.relationship_id
            )
            if (
                item is None
                or identity is None
                or identity.map_id != revision.map_id
                or not _visible(
                    item.information_cutoff_date,
                    item.recorded_at_utc,
                    as_of_cutoff,
                    as_of_recorded_at_utc,
                )
            ):
                raise IndustryResearchResultError(
                    "industry_research_result_map_graph_incomplete",
                    "relationship revision is missing or outside exact map scope",
                )
            source = nodes.get(identity.source_node_id)
            target = nodes.get(identity.target_node_id)
            if source is None or target is None:
                raise IndustryResearchResultError(
                    "industry_research_result_map_graph_incomplete",
                    "relationship endpoints are missing",
                )
            output_relationships.append(
                {
                    "relationship_id": str(identity.id),
                    "relationship_key": identity.relationship_key,
                    "relationship_revision_id": str(item.id),
                    "revision_no": item.revision_no,
                    "source_node_id": str(source.id),
                    "source_node_key": source.node_key,
                    "target_node_id": str(target.id),
                    "target_node_key": target.node_key,
                    "relation_kind": item.relation_kind,
                    "description": item.description,
                    "assertion_status": item.assertion_status,
                }
            )

        output_observations = []
        for revision_id in observation_revision_ids:
            item = observation_revisions.get(revision_id)
            identity = None if item is None else observations.get(item.observation_id)
            if (
                item is None
                or identity is None
                or identity.map_id != revision.map_id
                or not _visible(
                    item.information_cutoff_date,
                    item.recorded_at_utc,
                    as_of_cutoff,
                    as_of_recorded_at_utc,
                )
            ):
                raise IndustryResearchResultError(
                    "industry_research_result_map_graph_incomplete",
                    "observation revision is missing or outside exact map scope",
                )
            output_observations.append(
                {
                    "observation_id": str(identity.id),
                    "observation_key": identity.observation_key,
                    "observation_revision_id": str(item.id),
                    "revision_no": item.revision_no,
                    "observation_kind": identity.observation_kind,
                    "title": item.title,
                    "description": item.description,
                    "assertion_status": item.assertion_status,
                }
            )

        output_nodes.sort(key=lambda item: (item["node_key"], item["node_revision_id"]))
        output_relationships.sort(
            key=lambda item: (
                item["relationship_key"],
                item["relationship_revision_id"],
            )
        )
        output_observations.sort(
            key=lambda item: (
                item["observation_kind"],
                item["observation_key"],
                item["observation_revision_id"],
            )
        )
        return {
            "map_id": str(industry_map.id),
            "case_id": str(industry_map.case_id),
            "map_key": industry_map.map_key,
            "map_revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "title": revision.title,
            "scope": revision.scope,
            "information_cutoff_date": revision.information_cutoff_date.isoformat(),
            "recorded_at_utc": stored_utc(revision.recorded_at_utc).isoformat(),
            "nodes": output_nodes,
            "relationships": output_relationships,
            "observations": output_observations,
            "counts": {
                "nodes": len(output_nodes),
                "relationships": len(output_relationships),
                "observations": len(output_observations),
            },
            "selector_mode": "exact_revision_id",
            "latest_fallback_used": False,
        }

    def _load_by_id(self, model, ids: list[UUID]) -> dict[UUID, Any]:
        if not ids:
            return {}
        return {
            item.id: item
            for item in self._session.scalars(
                select(model).where(model.id.in_(ids))
            )
        }
