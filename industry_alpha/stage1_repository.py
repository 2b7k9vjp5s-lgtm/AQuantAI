"""Read-only repository for complete Stage 1 beneficiary map rows."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import IngestionRun, StockBasicRecord
from industry_alpha.chain_map_models import (
    IndustryMap,
    IndustryMapNode,
    IndustryMapNodeRevision,
    IndustryMapObservation,
    IndustryMapObservationRevision,
    IndustryMapRelationship,
    IndustryMapRelationshipRevision,
    IndustryMapRevision,
)
from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryAssertionLink,
    Stage1BeneficiaryClaimLink,
    Stage1BeneficiaryRevision,
    Stage1CandidatePool,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)


@dataclass(frozen=True)
class Stage1MapRows:
    industry_map: IndustryMap
    beneficiaries: tuple[Stage1Beneficiary, ...]
    beneficiary_revisions: tuple[Stage1BeneficiaryRevision, ...]
    assertion_links: tuple[Stage1BeneficiaryAssertionLink, ...]
    claim_links: tuple[Stage1BeneficiaryClaimLink, ...]
    candidate_pools: tuple[Stage1CandidatePool, ...]
    candidate_pool_revisions: tuple[Stage1CandidatePoolRevision, ...]
    memberships: tuple[Stage1CandidatePoolMembership, ...]
    map_revisions: tuple[IndustryMapRevision, ...]
    nodes: tuple[IndustryMapNode, ...]
    node_revisions: tuple[IndustryMapNodeRevision, ...]
    relationships: tuple[IndustryMapRelationship, ...]
    relationship_revisions: tuple[IndustryMapRelationshipRevision, ...]
    observations: tuple[IndustryMapObservation, ...]
    observation_revisions: tuple[IndustryMapObservationRevision, ...]
    claims: tuple[Claim, ...]
    claim_revisions: tuple[ClaimRevision, ...]
    claim_evidence_links: tuple[ClaimEvidenceLink, ...]
    evidence_items: tuple[EvidenceItem, ...]
    stock_records: tuple[StockBasicRecord, ...]
    ingestion_runs: tuple[IngestionRun, ...]


class Stage1BeneficiaryRepository:
    """Load immutable rows without exposing mutation methods."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def load_map(self, map_id: UUID) -> Stage1MapRows | None:
        industry_map = self._session.get(IndustryMap, map_id)
        if industry_map is None:
            return None
        beneficiaries = tuple(
            self._session.scalars(
                select(Stage1Beneficiary)
                .where(Stage1Beneficiary.map_id == map_id)
                .order_by(
                    Stage1Beneficiary.source,
                    Stage1Beneficiary.stock_code,
                    Stage1Beneficiary.id,
                )
            )
        )
        beneficiary_ids = [item.id for item in beneficiaries]
        beneficiary_revisions = self._rows_for_ids(
            Stage1BeneficiaryRevision,
            Stage1BeneficiaryRevision.beneficiary_id,
            beneficiary_ids,
            Stage1BeneficiaryRevision.beneficiary_id,
            Stage1BeneficiaryRevision.revision_no,
        )
        beneficiary_revision_ids = [item.id for item in beneficiary_revisions]
        assertion_links = self._rows_for_ids(
            Stage1BeneficiaryAssertionLink,
            Stage1BeneficiaryAssertionLink.beneficiary_revision_id,
            beneficiary_revision_ids,
            Stage1BeneficiaryAssertionLink.beneficiary_revision_id,
            Stage1BeneficiaryAssertionLink.id,
        )
        claim_links = self._rows_for_ids(
            Stage1BeneficiaryClaimLink,
            Stage1BeneficiaryClaimLink.beneficiary_revision_id,
            beneficiary_revision_ids,
            Stage1BeneficiaryClaimLink.beneficiary_revision_id,
            Stage1BeneficiaryClaimLink.claim_revision_id,
        )
        candidate_pools = tuple(
            self._session.scalars(
                select(Stage1CandidatePool)
                .where(Stage1CandidatePool.map_id == map_id)
                .order_by(Stage1CandidatePool.pool_key, Stage1CandidatePool.id)
            )
        )
        pool_ids = [item.id for item in candidate_pools]
        candidate_pool_revisions = self._rows_for_ids(
            Stage1CandidatePoolRevision,
            Stage1CandidatePoolRevision.candidate_pool_id,
            pool_ids,
            Stage1CandidatePoolRevision.candidate_pool_id,
            Stage1CandidatePoolRevision.revision_no,
        )
        pool_revision_ids = [item.id for item in candidate_pool_revisions]
        memberships = self._rows_for_ids(
            Stage1CandidatePoolMembership,
            Stage1CandidatePoolMembership.candidate_pool_revision_id,
            pool_revision_ids,
            Stage1CandidatePoolMembership.candidate_pool_revision_id,
            Stage1CandidatePoolMembership.beneficiary_id,
        )
        map_revision_ids = {
            item.selected_map_revision_id for item in beneficiary_revisions
        } | {
            item.selected_map_revision_id for item in candidate_pool_revisions
        }
        map_revisions = self._rows_for_ids(
            IndustryMapRevision,
            IndustryMapRevision.id,
            sorted(map_revision_ids, key=str),
            IndustryMapRevision.revision_no,
        )
        node_revision_ids = sorted(
            {
                item.node_revision_id
                for item in assertion_links
                if item.node_revision_id is not None
            },
            key=str,
        )
        relationship_revision_ids = sorted(
            {
                item.relationship_revision_id
                for item in assertion_links
                if item.relationship_revision_id is not None
            },
            key=str,
        )
        observation_revision_ids = sorted(
            {
                item.observation_revision_id
                for item in assertion_links
                if item.observation_revision_id is not None
            },
            key=str,
        )
        node_revisions = self._rows_for_ids(
            IndustryMapNodeRevision,
            IndustryMapNodeRevision.id,
            node_revision_ids,
            IndustryMapNodeRevision.node_id,
            IndustryMapNodeRevision.revision_no,
        )
        relationship_revisions = self._rows_for_ids(
            IndustryMapRelationshipRevision,
            IndustryMapRelationshipRevision.id,
            relationship_revision_ids,
            IndustryMapRelationshipRevision.relationship_id,
            IndustryMapRelationshipRevision.revision_no,
        )
        observation_revisions = self._rows_for_ids(
            IndustryMapObservationRevision,
            IndustryMapObservationRevision.id,
            observation_revision_ids,
            IndustryMapObservationRevision.observation_id,
            IndustryMapObservationRevision.revision_no,
        )
        nodes = self._identities(
            IndustryMapNode,
            [item.node_id for item in node_revisions],
            IndustryMapNode.node_key,
        )
        relationships = self._identities(
            IndustryMapRelationship,
            [item.relationship_id for item in relationship_revisions],
            IndustryMapRelationship.relationship_key,
        )
        observations = self._identities(
            IndustryMapObservation,
            [item.observation_id for item in observation_revisions],
            IndustryMapObservation.observation_kind,
            IndustryMapObservation.observation_key,
        )
        claim_revision_ids = sorted(
            {item.claim_revision_id for item in claim_links}, key=str
        )
        claim_revisions = self._rows_for_ids(
            ClaimRevision,
            ClaimRevision.id,
            claim_revision_ids,
            ClaimRevision.claim_id,
            ClaimRevision.revision_no,
        )
        claims = self._identities(
            Claim,
            [item.claim_id for item in claim_revisions],
            Claim.claim_key,
            Claim.id,
        )
        claim_evidence_links = self._rows_for_ids(
            ClaimEvidenceLink,
            ClaimEvidenceLink.claim_revision_id,
            claim_revision_ids,
            ClaimEvidenceLink.claim_revision_id,
            ClaimEvidenceLink.relation,
            ClaimEvidenceLink.evidence_id,
        )
        evidence_ids = sorted(
            {item.evidence_id for item in claim_evidence_links}, key=str
        )
        evidence_items = self._rows_for_ids(
            EvidenceItem,
            EvidenceItem.id,
            evidence_ids,
            EvidenceItem.information_date,
            EvidenceItem.recorded_at_utc,
            EvidenceItem.id,
        )
        stock_record_ids = sorted(
            {item.stock_basic_record_id for item in beneficiary_revisions}
        )
        stock_records = self._rows_for_ids(
            StockBasicRecord,
            StockBasicRecord.id,
            stock_record_ids,
            StockBasicRecord.source,
            StockBasicRecord.stock_code,
            StockBasicRecord.id,
        )
        ingestion_runs = self._rows_for_ids(
            IngestionRun,
            IngestionRun.id,
            sorted({item.ingestion_run_id for item in stock_records}),
            IngestionRun.id,
        )
        return Stage1MapRows(
            industry_map=industry_map,
            beneficiaries=beneficiaries,
            beneficiary_revisions=beneficiary_revisions,
            assertion_links=assertion_links,
            claim_links=claim_links,
            candidate_pools=candidate_pools,
            candidate_pool_revisions=candidate_pool_revisions,
            memberships=memberships,
            map_revisions=map_revisions,
            nodes=nodes,
            node_revisions=node_revisions,
            relationships=relationships,
            relationship_revisions=relationship_revisions,
            observations=observations,
            observation_revisions=observation_revisions,
            claims=claims,
            claim_revisions=claim_revisions,
            claim_evidence_links=claim_evidence_links,
            evidence_items=evidence_items,
            stock_records=stock_records,
            ingestion_runs=ingestion_runs,
        )

    def find_beneficiary_map_id(self, beneficiary_id: UUID) -> UUID | None:
        return self._session.scalar(
            select(Stage1Beneficiary.map_id).where(
                Stage1Beneficiary.id == beneficiary_id
            )
        )

    def find_candidate_pool_map_id(self, pool_id: UUID) -> UUID | None:
        return self._session.scalar(
            select(Stage1CandidatePool.map_id).where(
                Stage1CandidatePool.id == pool_id
            )
        )

    def _rows_for_ids(self, model, column, ids, *order_by):
        if not ids:
            return ()
        return tuple(
            self._session.scalars(
                select(model).where(column.in_(ids)).order_by(*order_by)
            )
        )

    def _identities(self, model, ids, *order_by):
        return self._rows_for_ids(
            model, model.id, sorted(set(ids), key=str), *order_by
        )
