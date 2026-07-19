"""Read-only repository for Stage 2 company-research rows."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import IngestionRun, StockBasicRecord
from industry_alpha.chain_map_models import (
    IndustryMapNodeRevision,
    IndustryMapObservationRevision,
    IndustryMapRelationshipRevision,
    IndustryMapRevision,
)
from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryAssertionLink,
    Stage1BeneficiaryRevision,
    Stage1CandidatePool,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
    Stage2FinancialHypothesis,
    Stage2FinancialHypothesisRevision,
    Stage2HandoffAssertionLink,
    Stage2HandoffClaimLink,
    Stage2HandoffEvidenceLink,
    Stage2HypothesisClaimLink,
    Stage2HypothesisEvidenceLink,
    Stage2ResearchHypothesisLink,
    Stage2VerificationItem,
)
from industry_alpha.stage2_repository_rows import load_ordered_rows


@dataclass(frozen=True)
class Stage2Rows:
    research: Stage2CompanyResearch
    research_revisions: tuple[Stage2CompanyResearchRevision, ...]
    hypotheses: tuple[Stage2FinancialHypothesis, ...]
    hypothesis_revisions: tuple[Stage2FinancialHypothesisRevision, ...]
    hypothesis_claim_links: tuple[Stage2HypothesisClaimLink, ...]
    hypothesis_evidence_links: tuple[Stage2HypothesisEvidenceLink, ...]
    research_hypothesis_links: tuple[Stage2ResearchHypothesisLink, ...]
    verification_items: tuple[Stage2VerificationItem, ...]
    handoff_assertion_links: tuple[Stage2HandoffAssertionLink, ...]
    handoff_evidence_links: tuple[Stage2HandoffEvidenceLink, ...]
    handoff_claim_links: tuple[Stage2HandoffClaimLink, ...]
    pool: Stage1CandidatePool
    pool_revision: Stage1CandidatePoolRevision
    membership: Stage1CandidatePoolMembership
    beneficiary: Stage1Beneficiary
    beneficiary_revision: Stage1BeneficiaryRevision
    assertion_links: tuple[Stage1BeneficiaryAssertionLink, ...]
    map_revision: IndustryMapRevision
    stock: StockBasicRecord
    ingestion_run: IngestionRun
    claims: tuple[Claim, ...]
    claim_revisions: tuple[ClaimRevision, ...]
    claim_evidence_links: tuple[ClaimEvidenceLink, ...]
    evidence_items: tuple[EvidenceItem, ...]
    node_revisions: tuple[IndustryMapNodeRevision, ...]
    relationship_revisions: tuple[IndustryMapRelationshipRevision, ...]
    observation_revisions: tuple[IndustryMapObservationRevision, ...]


class Stage2CompanyResearchRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_research(
        self,
        *,
        candidate_pool_revision_id: UUID | None = None,
        map_id: UUID | None = None,
    ) -> tuple[Stage2CompanyResearch, ...]:
        statement = select(Stage2CompanyResearch)
        if candidate_pool_revision_id is not None:
            statement = statement.where(
                Stage2CompanyResearch.candidate_pool_revision_id
                == candidate_pool_revision_id
            )
        if map_id is not None:
            statement = statement.where(Stage2CompanyResearch.map_id == map_id)
        return tuple(
            self._session.scalars(
                statement.order_by(
                    Stage2CompanyResearch.source,
                    Stage2CompanyResearch.stock_code,
                    Stage2CompanyResearch.id,
                )
            )
        )

    def load(self, research_id: UUID) -> Stage2Rows | None:
        research = self._session.get(Stage2CompanyResearch, research_id)
        if research is None:
            return None
        research_revisions = self._rows(
            Stage2CompanyResearchRevision,
            Stage2CompanyResearchRevision.company_research_id,
            [research.id],
            Stage2CompanyResearchRevision.revision_no,
        )
        hypotheses = self._rows(
            Stage2FinancialHypothesis,
            Stage2FinancialHypothesis.company_research_id,
            [research.id],
            Stage2FinancialHypothesis.hypothesis_key,
        )
        hypothesis_revisions = self._rows(
            Stage2FinancialHypothesisRevision,
            Stage2FinancialHypothesisRevision.hypothesis_id,
            [item.id for item in hypotheses],
            Stage2FinancialHypothesisRevision.hypothesis_id,
            Stage2FinancialHypothesisRevision.revision_no,
        )
        hypothesis_revision_ids = [item.id for item in hypothesis_revisions]
        research_revision_ids = [item.id for item in research_revisions]
        hypothesis_claim_links = self._rows(
            Stage2HypothesisClaimLink,
            Stage2HypothesisClaimLink.hypothesis_revision_id,
            hypothesis_revision_ids,
            Stage2HypothesisClaimLink.hypothesis_revision_id,
            Stage2HypothesisClaimLink.claim_revision_id,
        )
        hypothesis_evidence_links = self._rows(
            Stage2HypothesisEvidenceLink,
            Stage2HypothesisEvidenceLink.hypothesis_revision_id,
            hypothesis_revision_ids,
            Stage2HypothesisEvidenceLink.hypothesis_revision_id,
            Stage2HypothesisEvidenceLink.claim_revision_id,
            Stage2HypothesisEvidenceLink.evidence_id,
        )
        research_hypothesis_links = self._rows(
            Stage2ResearchHypothesisLink,
            Stage2ResearchHypothesisLink.company_research_revision_id,
            research_revision_ids,
            Stage2ResearchHypothesisLink.company_research_revision_id,
            Stage2ResearchHypothesisLink.hypothesis_id,
        )
        verification_items = self._rows(
            Stage2VerificationItem,
            Stage2VerificationItem.company_research_revision_id,
            research_revision_ids,
            Stage2VerificationItem.company_research_revision_id,
            Stage2VerificationItem.item_no,
        )
        handoff_assertion_links = self._rows(
            Stage2HandoffAssertionLink,
            Stage2HandoffAssertionLink.company_research_id,
            [research.id],
            Stage2HandoffAssertionLink.stage1_beneficiary_assertion_link_id,
        )
        handoff_evidence_links = self._rows(
            Stage2HandoffEvidenceLink,
            Stage2HandoffEvidenceLink.company_research_id,
            [research.id],
            Stage2HandoffEvidenceLink.claim_revision_id,
            Stage2HandoffEvidenceLink.evidence_id,
        )
        handoff_claim_links = self._rows(
            Stage2HandoffClaimLink,
            Stage2HandoffClaimLink.company_research_id,
            [research.id],
            Stage2HandoffClaimLink.claim_revision_id,
        )
        pool = self._session.get(Stage1CandidatePool, research.candidate_pool_id)
        pool_revision = self._session.get(
            Stage1CandidatePoolRevision, research.candidate_pool_revision_id
        )
        membership = self._session.get(
            Stage1CandidatePoolMembership, research.candidate_pool_membership_id
        )
        beneficiary = self._session.get(Stage1Beneficiary, research.beneficiary_id)
        beneficiary_revision = self._session.get(
            Stage1BeneficiaryRevision, research.beneficiary_revision_id
        )
        map_revision = self._session.get(
            IndustryMapRevision, research.selected_map_revision_id
        )
        stock = self._session.get(StockBasicRecord, research.stock_basic_record_id)
        ingestion_run = self._session.get(IngestionRun, stock.ingestion_run_id)
        assertion_links = self._rows(
            Stage1BeneficiaryAssertionLink,
            Stage1BeneficiaryAssertionLink.id,
            [
                item.stage1_beneficiary_assertion_link_id
                for item in handoff_assertion_links
            ],
            Stage1BeneficiaryAssertionLink.id,
        )
        claim_revision_ids = sorted(
            {
                *(item.claim_revision_id for item in handoff_claim_links),
                *(item.claim_revision_id for item in hypothesis_claim_links),
            },
            key=str,
        )
        claim_revisions = self._rows(
            ClaimRevision,
            ClaimRevision.id,
            claim_revision_ids,
            ClaimRevision.claim_id,
            ClaimRevision.revision_no,
        )
        claims = self._rows(
            Claim,
            Claim.id,
            [item.claim_id for item in claim_revisions],
            Claim.claim_key,
        )
        evidence_link_ids = sorted(
            {
                *(item.claim_evidence_link_id for item in handoff_evidence_links),
                *(item.claim_evidence_link_id for item in hypothesis_evidence_links),
            },
            key=str,
        )
        claim_evidence_links = self._rows(
            ClaimEvidenceLink,
            ClaimEvidenceLink.id,
            evidence_link_ids,
            ClaimEvidenceLink.claim_revision_id,
            ClaimEvidenceLink.relation,
            ClaimEvidenceLink.evidence_id,
        )
        evidence_items = self._rows(
            EvidenceItem,
            EvidenceItem.id,
            sorted(
                {
                    *(item.evidence_id for item in handoff_evidence_links),
                    *(item.evidence_id for item in hypothesis_evidence_links),
                },
                key=str,
            ),
            EvidenceItem.information_date,
            EvidenceItem.id,
        )
        node_revisions = self._rows(
            IndustryMapNodeRevision,
            IndustryMapNodeRevision.id,
            [item.node_revision_id for item in assertion_links if item.node_revision_id],
            IndustryMapNodeRevision.id,
        )
        relationship_revisions = self._rows(
            IndustryMapRelationshipRevision,
            IndustryMapRelationshipRevision.id,
            [item.relationship_revision_id for item in assertion_links if item.relationship_revision_id],
            IndustryMapRelationshipRevision.id,
        )
        observation_revisions = self._rows(
            IndustryMapObservationRevision,
            IndustryMapObservationRevision.id,
            [item.observation_revision_id for item in assertion_links if item.observation_revision_id],
            IndustryMapObservationRevision.id,
        )
        required = (
            pool,
            pool_revision,
            membership,
            beneficiary,
            beneficiary_revision,
            map_revision,
            stock,
            ingestion_run,
        )
        if any(item is None for item in required):
            return None
        return Stage2Rows(
            research,
            research_revisions,
            hypotheses,
            hypothesis_revisions,
            hypothesis_claim_links,
            hypothesis_evidence_links,
            research_hypothesis_links,
            verification_items,
            handoff_assertion_links,
            handoff_evidence_links,
            handoff_claim_links,
            pool,
            pool_revision,
            membership,
            beneficiary,
            beneficiary_revision,
            assertion_links,
            map_revision,
            stock,
            ingestion_run,
            claims,
            claim_revisions,
            claim_evidence_links,
            evidence_items,
            node_revisions,
            relationship_revisions,
            observation_revisions,
        )

    def _rows(self, model, field, ids, *order) -> tuple:
        return load_ordered_rows(self._session, model, field, ids, *order)
