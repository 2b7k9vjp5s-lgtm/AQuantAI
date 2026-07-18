"""Read adapter for complete append-only industry-map rows."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from industry_alpha.chain_map_models import (
    IndustryMap,
    IndustryMapAssertionClaimLink,
    IndustryMapNode,
    IndustryMapNodeRevision,
    IndustryMapObservation,
    IndustryMapObservationRevision,
    IndustryMapRelationship,
    IndustryMapRelationshipRevision,
    IndustryMapRevision,
    IndustryMapRevisionMembership,
)
from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem


@dataclass(frozen=True)
class IndustryMapRows:
    industry_map: IndustryMap
    map_revisions: tuple[IndustryMapRevision, ...]
    nodes: tuple[IndustryMapNode, ...]
    node_revisions: tuple[IndustryMapNodeRevision, ...]
    relationships: tuple[IndustryMapRelationship, ...]
    relationship_revisions: tuple[IndustryMapRelationshipRevision, ...]
    observations: tuple[IndustryMapObservation, ...]
    observation_revisions: tuple[IndustryMapObservationRevision, ...]
    assertion_claim_links: tuple[IndustryMapAssertionClaimLink, ...]
    memberships: tuple[IndustryMapRevisionMembership, ...]
    claims: tuple[Claim, ...]
    claim_revisions: tuple[ClaimRevision, ...]
    claim_evidence_links: tuple[ClaimEvidenceLink, ...]
    evidence_items: tuple[EvidenceItem, ...]


class IndustryChainMapRepository:
    """Load immutable map and evidence rows without mutation methods."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_maps(self) -> tuple[IndustryMap, ...]:
        return tuple(
            self._session.scalars(
                select(IndustryMap).order_by(
                    IndustryMap.case_id, IndustryMap.map_key, IndustryMap.id
                )
            )
        )

    def load_map(self, map_id: UUID) -> IndustryMapRows | None:
        industry_map = self._session.get(IndustryMap, map_id)
        if industry_map is None:
            return None
        map_revisions = tuple(
            self._session.scalars(
                select(IndustryMapRevision)
                .where(IndustryMapRevision.map_id == map_id)
                .order_by(IndustryMapRevision.revision_no)
            )
        )
        nodes = tuple(
            self._session.scalars(
                select(IndustryMapNode)
                .where(IndustryMapNode.map_id == map_id)
                .order_by(IndustryMapNode.node_key, IndustryMapNode.id)
            )
        )
        node_ids = [item.id for item in nodes]
        node_revisions = self._rows_for_ids(
            IndustryMapNodeRevision,
            IndustryMapNodeRevision.node_id,
            node_ids,
            IndustryMapNodeRevision.node_id,
            IndustryMapNodeRevision.revision_no,
        )
        relationships = tuple(
            self._session.scalars(
                select(IndustryMapRelationship)
                .where(IndustryMapRelationship.map_id == map_id)
                .order_by(
                    IndustryMapRelationship.relationship_key,
                    IndustryMapRelationship.id,
                )
            )
        )
        relationship_ids = [item.id for item in relationships]
        relationship_revisions = self._rows_for_ids(
            IndustryMapRelationshipRevision,
            IndustryMapRelationshipRevision.relationship_id,
            relationship_ids,
            IndustryMapRelationshipRevision.relationship_id,
            IndustryMapRelationshipRevision.revision_no,
        )
        observations = tuple(
            self._session.scalars(
                select(IndustryMapObservation)
                .where(IndustryMapObservation.map_id == map_id)
                .order_by(
                    IndustryMapObservation.observation_kind,
                    IndustryMapObservation.observation_key,
                    IndustryMapObservation.id,
                )
            )
        )
        observation_ids = [item.id for item in observations]
        observation_revisions = self._rows_for_ids(
            IndustryMapObservationRevision,
            IndustryMapObservationRevision.observation_id,
            observation_ids,
            IndustryMapObservationRevision.observation_id,
            IndustryMapObservationRevision.revision_no,
        )
        node_revision_ids = [item.id for item in node_revisions]
        relationship_revision_ids = [item.id for item in relationship_revisions]
        observation_revision_ids = [item.id for item in observation_revisions]
        assertion_claim_links = tuple(
            self._session.scalars(
                select(IndustryMapAssertionClaimLink)
                .where(
                    IndustryMapAssertionClaimLink.node_revision_id.in_(node_revision_ids)
                    | IndustryMapAssertionClaimLink.relationship_revision_id.in_(
                        relationship_revision_ids
                    )
                    | IndustryMapAssertionClaimLink.observation_revision_id.in_(
                        observation_revision_ids
                    )
                )
                .order_by(
                    IndustryMapAssertionClaimLink.recorded_at_utc,
                    IndustryMapAssertionClaimLink.claim_revision_id,
                    IndustryMapAssertionClaimLink.id,
                )
            )
        ) if (node_revision_ids or relationship_revision_ids or observation_revision_ids) else ()
        map_revision_ids = [item.id for item in map_revisions]
        memberships = tuple(
            self._session.scalars(
                select(IndustryMapRevisionMembership)
                .where(
                    IndustryMapRevisionMembership.map_revision_id.in_(map_revision_ids)
                )
                .order_by(
                    IndustryMapRevisionMembership.map_revision_id,
                    IndustryMapRevisionMembership.id,
                )
            )
        ) if map_revision_ids else ()
        claim_revision_ids = sorted(
            {link.claim_revision_id for link in assertion_claim_links}, key=str
        )
        claim_revisions = tuple(
            self._session.scalars(
                select(ClaimRevision)
                .where(ClaimRevision.id.in_(claim_revision_ids))
                .order_by(ClaimRevision.claim_id, ClaimRevision.revision_no)
            )
        ) if claim_revision_ids else ()
        claim_ids = sorted({item.claim_id for item in claim_revisions}, key=str)
        claims = tuple(
            self._session.scalars(
                select(Claim)
                .where(Claim.id.in_(claim_ids))
                .order_by(Claim.claim_key, Claim.id)
            )
        ) if claim_ids else ()
        claim_evidence_links = tuple(
            self._session.scalars(
                select(ClaimEvidenceLink)
                .where(ClaimEvidenceLink.claim_revision_id.in_(claim_revision_ids))
                .order_by(
                    ClaimEvidenceLink.claim_revision_id,
                    ClaimEvidenceLink.relation,
                    ClaimEvidenceLink.evidence_id,
                )
            )
        ) if claim_revision_ids else ()
        evidence_ids = sorted(
            {link.evidence_id for link in claim_evidence_links}, key=str
        )
        evidence_items = tuple(
            self._session.scalars(
                select(EvidenceItem)
                .where(EvidenceItem.id.in_(evidence_ids))
                .order_by(
                    EvidenceItem.information_date,
                    EvidenceItem.recorded_at_utc,
                    EvidenceItem.id,
                )
            )
        ) if evidence_ids else ()
        return IndustryMapRows(
            industry_map=industry_map,
            map_revisions=map_revisions,
            nodes=nodes,
            node_revisions=node_revisions,
            relationships=relationships,
            relationship_revisions=relationship_revisions,
            observations=observations,
            observation_revisions=observation_revisions,
            assertion_claim_links=assertion_claim_links,
            memberships=memberships,
            claims=claims,
            claim_revisions=claim_revisions,
            claim_evidence_links=claim_evidence_links,
            evidence_items=evidence_items,
        )

    def _rows_for_ids(self, model, column, ids, *order_by):
        if not ids:
            return ()
        return tuple(
            self._session.scalars(
                select(model).where(column.in_(ids)).order_by(*order_by)
            )
        )
