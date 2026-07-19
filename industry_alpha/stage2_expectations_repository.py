"""Repository helpers for v0.6B expectation and valuation reads."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import DailyPriceRecord, IngestionRun
from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
    Stage2FinancialHypothesisRevision,
)
from industry_alpha.stage2_expectations_models import (
    Stage2ExpectationClaimLink,
    Stage2ExpectationEvidenceLink,
    Stage2ExpectationHypothesisLink,
    Stage2MarketExpectation,
    Stage2MarketExpectationRevision,
    Stage2ValuationClaimLink,
    Stage2ValuationEvidenceLink,
    Stage2ValuationHypothesisLink,
    Stage2ValuationSnapshot,
    Stage2ValuationSnapshotRevision,
)


@dataclass(frozen=True)
class Stage2ExpectationRows:
    expectation: Stage2MarketExpectation
    research: Stage2CompanyResearch
    revisions: tuple[Stage2MarketExpectationRevision, ...]
    research_revisions: tuple[Stage2CompanyResearchRevision, ...]
    hypothesis_revisions: tuple[Stage2FinancialHypothesisRevision, ...]
    hypothesis_links: tuple[Stage2ExpectationHypothesisLink, ...]
    claim_links: tuple[Stage2ExpectationClaimLink, ...]
    evidence_links: tuple[Stage2ExpectationEvidenceLink, ...]
    claims: tuple[Claim, ...]
    claim_revisions: tuple[ClaimRevision, ...]
    claim_evidence_links: tuple[ClaimEvidenceLink, ...]
    evidence: tuple[EvidenceItem, ...]


@dataclass(frozen=True)
class Stage2ValuationRows:
    valuation: Stage2ValuationSnapshot
    research: Stage2CompanyResearch
    revisions: tuple[Stage2ValuationSnapshotRevision, ...]
    research_revisions: tuple[Stage2CompanyResearchRevision, ...]
    hypothesis_revisions: tuple[Stage2FinancialHypothesisRevision, ...]
    hypothesis_links: tuple[Stage2ValuationHypothesisLink, ...]
    claim_links: tuple[Stage2ValuationClaimLink, ...]
    evidence_links: tuple[Stage2ValuationEvidenceLink, ...]
    claims: tuple[Claim, ...]
    claim_revisions: tuple[ClaimRevision, ...]
    claim_evidence_links: tuple[ClaimEvidenceLink, ...]
    evidence: tuple[EvidenceItem, ...]
    prices: tuple[DailyPriceRecord, ...]
    ingestion_runs: tuple[IngestionRun, ...]


class Stage2ExpectationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_expectations(self, company_research_id: UUID | None = None) -> tuple[Stage2MarketExpectation, ...]:
        statement = select(Stage2MarketExpectation)
        if company_research_id is not None:
            statement = statement.where(Stage2MarketExpectation.company_research_id == company_research_id)
        return tuple(self._session.scalars(statement.order_by(Stage2MarketExpectation.expectation_key, Stage2MarketExpectation.id)))

    def list_valuations(self, company_research_id: UUID | None = None) -> tuple[Stage2ValuationSnapshot, ...]:
        statement = select(Stage2ValuationSnapshot)
        if company_research_id is not None:
            statement = statement.where(Stage2ValuationSnapshot.company_research_id == company_research_id)
        return tuple(self._session.scalars(statement.order_by(Stage2ValuationSnapshot.valuation_key, Stage2ValuationSnapshot.id)))

    def load_expectation(self, identity: UUID) -> Stage2ExpectationRows | None:
        expectation = self._session.get(Stage2MarketExpectation, identity)
        if expectation is None:
            return None
        research = self._session.get(Stage2CompanyResearch, expectation.company_research_id)
        revisions = self._rows(Stage2MarketExpectationRevision, Stage2MarketExpectationRevision.expectation_id, [expectation.id], Stage2MarketExpectationRevision.revision_no)
        research_revisions = self._rows(Stage2CompanyResearchRevision, Stage2CompanyResearchRevision.id, [item.company_research_revision_id for item in revisions], Stage2CompanyResearchRevision.revision_no)
        hypothesis_links = self._rows(Stage2ExpectationHypothesisLink, Stage2ExpectationHypothesisLink.expectation_revision_id, [item.id for item in revisions], Stage2ExpectationHypothesisLink.expectation_revision_id, Stage2ExpectationHypothesisLink.hypothesis_revision_id)
        claim_links = self._rows(Stage2ExpectationClaimLink, Stage2ExpectationClaimLink.expectation_revision_id, [item.id for item in revisions], Stage2ExpectationClaimLink.expectation_revision_id, Stage2ExpectationClaimLink.claim_revision_id)
        evidence_links = self._rows(Stage2ExpectationEvidenceLink, Stage2ExpectationEvidenceLink.expectation_revision_id, [item.id for item in revisions], Stage2ExpectationEvidenceLink.expectation_revision_id, Stage2ExpectationEvidenceLink.claim_revision_id)
        hypothesis_revisions = self._rows(Stage2FinancialHypothesisRevision, Stage2FinancialHypothesisRevision.id, [item.hypothesis_revision_id for item in hypothesis_links], Stage2FinancialHypothesisRevision.id)
        return self._expectation_rows(expectation, research, revisions, research_revisions, hypothesis_revisions, hypothesis_links, claim_links, evidence_links)

    def load_valuation(self, identity: UUID) -> Stage2ValuationRows | None:
        valuation = self._session.get(Stage2ValuationSnapshot, identity)
        if valuation is None:
            return None
        research = self._session.get(Stage2CompanyResearch, valuation.company_research_id)
        revisions = self._rows(Stage2ValuationSnapshotRevision, Stage2ValuationSnapshotRevision.valuation_id, [valuation.id], Stage2ValuationSnapshotRevision.revision_no)
        research_revisions = self._rows(Stage2CompanyResearchRevision, Stage2CompanyResearchRevision.id, [item.company_research_revision_id for item in revisions], Stage2CompanyResearchRevision.revision_no)
        hypothesis_links = self._rows(Stage2ValuationHypothesisLink, Stage2ValuationHypothesisLink.valuation_revision_id, [item.id for item in revisions], Stage2ValuationHypothesisLink.valuation_revision_id, Stage2ValuationHypothesisLink.hypothesis_revision_id)
        claim_links = self._rows(Stage2ValuationClaimLink, Stage2ValuationClaimLink.valuation_revision_id, [item.id for item in revisions], Stage2ValuationClaimLink.valuation_revision_id, Stage2ValuationClaimLink.claim_revision_id)
        evidence_links = self._rows(Stage2ValuationEvidenceLink, Stage2ValuationEvidenceLink.valuation_revision_id, [item.id for item in revisions], Stage2ValuationEvidenceLink.valuation_revision_id, Stage2ValuationEvidenceLink.claim_revision_id)
        hypothesis_revisions = self._rows(Stage2FinancialHypothesisRevision, Stage2FinancialHypothesisRevision.id, [item.hypothesis_revision_id for item in hypothesis_links], Stage2FinancialHypothesisRevision.id)
        claim_revisions, claims, claim_evidence_links, evidence = self._evidence_rows(claim_links, evidence_links)
        prices = self._rows(DailyPriceRecord, DailyPriceRecord.id, [item.daily_price_id for item in revisions if item.daily_price_id is not None], DailyPriceRecord.trade_date, DailyPriceRecord.id)
        runs = self._rows(IngestionRun, IngestionRun.id, [item.ingestion_run_id for item in prices], IngestionRun.id)
        if research is None:
            return None
        return Stage2ValuationRows(valuation, research, revisions, research_revisions, hypothesis_revisions, hypothesis_links, claim_links, evidence_links, claims, claim_revisions, claim_evidence_links, evidence, prices, runs)

    def _expectation_rows(self, expectation, research, revisions, research_revisions, hypothesis_revisions, hypothesis_links, claim_links, evidence_links):
        if research is None:
            return None
        claim_revisions, claims, claim_evidence_links, evidence = self._evidence_rows(claim_links, evidence_links)
        return Stage2ExpectationRows(expectation, research, revisions, research_revisions, hypothesis_revisions, hypothesis_links, claim_links, evidence_links, claims, claim_revisions, claim_evidence_links, evidence)

    def _evidence_rows(self, claim_links, evidence_links):
        claim_revisions = self._rows(ClaimRevision, ClaimRevision.id, [item.claim_revision_id for item in claim_links], ClaimRevision.claim_id, ClaimRevision.revision_no)
        claims = self._rows(Claim, Claim.id, [item.claim_id for item in claim_revisions], Claim.claim_key)
        claim_evidence_links = self._rows(ClaimEvidenceLink, ClaimEvidenceLink.id, [item.claim_evidence_link_id for item in evidence_links], ClaimEvidenceLink.claim_revision_id, ClaimEvidenceLink.relation)
        evidence = self._rows(EvidenceItem, EvidenceItem.id, [item.evidence_id for item in evidence_links], EvidenceItem.information_date, EvidenceItem.id)
        return claim_revisions, claims, claim_evidence_links, evidence

    def _rows(self, model, field, ids, *order) -> tuple:
        ids = [item for item in ids if item is not None]
        if not ids:
            return ()
        return tuple(self._session.scalars(select(model).where(field.in_(ids)).order_by(*order)))
