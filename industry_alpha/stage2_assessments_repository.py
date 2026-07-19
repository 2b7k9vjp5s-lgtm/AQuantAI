"""Repository helpers for v0.6C catalyst and risk assessment reads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem
from industry_alpha.stage2_assessments_models import (
    Stage2CatalystAssessment, Stage2CatalystAssessmentRevision, Stage2CatalystClaimLink,
    Stage2CatalystEvidenceLink, Stage2CatalystExpectationLink, Stage2CatalystHypothesisLink,
    Stage2CatalystValuationLink, Stage2RiskAssessment, Stage2RiskAssessmentRevision,
    Stage2RiskClaimLink, Stage2RiskEvidenceLink, Stage2RiskExpectationLink,
    Stage2RiskHypothesisLink, Stage2RiskValuationLink,
)


@dataclass(frozen=True)
class Stage2AssessmentRows:
    identity: Any
    revisions: tuple[Any, ...]
    hypothesis_links: tuple[Any, ...]
    expectation_links: tuple[Any, ...]
    valuation_links: tuple[Any, ...]
    claim_links: tuple[Any, ...]
    evidence_links: tuple[Any, ...]
    claims: tuple[Claim, ...]
    claim_revisions: tuple[ClaimRevision, ...]
    source_evidence_links: tuple[ClaimEvidenceLink, ...]
    evidence: tuple[EvidenceItem, ...]


class Stage2AssessmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_catalysts(self, company_research_id: UUID | None = None) -> tuple[Stage2CatalystAssessment, ...]:
        return self._list(Stage2CatalystAssessment, Stage2CatalystAssessment.catalyst_key, company_research_id)

    def list_risks(self, company_research_id: UUID | None = None) -> tuple[Stage2RiskAssessment, ...]:
        return self._list(Stage2RiskAssessment, Stage2RiskAssessment.risk_key, company_research_id)

    def load_catalyst(self, identity: UUID) -> Stage2AssessmentRows | None:
        return self._load(
            Stage2CatalystAssessment, Stage2CatalystAssessmentRevision,
            Stage2CatalystHypothesisLink, Stage2CatalystExpectationLink,
            Stage2CatalystValuationLink, Stage2CatalystClaimLink,
            Stage2CatalystEvidenceLink, "catalyst_id", "catalyst_revision_id", identity,
        )

    def load_risk(self, identity: UUID) -> Stage2AssessmentRows | None:
        return self._load(
            Stage2RiskAssessment, Stage2RiskAssessmentRevision,
            Stage2RiskHypothesisLink, Stage2RiskExpectationLink,
            Stage2RiskValuationLink, Stage2RiskClaimLink,
            Stage2RiskEvidenceLink, "risk_id", "risk_revision_id", identity,
        )

    def _list(self, model: type[Any], key: Any, company_research_id: UUID | None) -> tuple[Any, ...]:
        statement = select(model)
        if company_research_id is not None:
            statement = statement.where(model.company_research_id == company_research_id)
        return tuple(self._session.scalars(statement.order_by(key, model.id)))

    def _load(self, identity_model: type[Any], revision_model: type[Any], hypothesis_model: type[Any], expectation_model: type[Any], valuation_model: type[Any], claim_model: type[Any], evidence_model: type[Any], identity_field: str, revision_field: str, identity: UUID) -> Stage2AssessmentRows | None:
        row = self._session.get(identity_model, identity)
        if row is None:
            return None
        revisions = tuple(self._session.scalars(select(revision_model).where(getattr(revision_model, identity_field) == identity).order_by(revision_model.revision_no)))
        revision_ids = [item.id for item in revisions]
        hypothesis_links = self._linked(hypothesis_model, revision_field, revision_ids)
        expectation_links = self._linked(expectation_model, revision_field, revision_ids)
        valuation_links = self._linked(valuation_model, revision_field, revision_ids)
        claim_links = self._linked(claim_model, revision_field, revision_ids)
        evidence_links = self._linked(evidence_model, revision_field, revision_ids)
        claim_revision_ids = [item.claim_revision_id for item in claim_links]
        claim_revisions = self._rows(ClaimRevision, ClaimRevision.id, claim_revision_ids, ClaimRevision.claim_id, ClaimRevision.revision_no)
        claims = self._rows(Claim, Claim.id, [item.claim_id for item in claim_revisions], Claim.claim_key, Claim.id)
        source_evidence_links = self._rows(ClaimEvidenceLink, ClaimEvidenceLink.id, [item.claim_evidence_link_id for item in evidence_links], ClaimEvidenceLink.id)
        evidence = self._rows(EvidenceItem, EvidenceItem.id, [item.evidence_id for item in evidence_links], EvidenceItem.id)
        return Stage2AssessmentRows(row, revisions, hypothesis_links, expectation_links, valuation_links, claim_links, evidence_links, claims, claim_revisions, source_evidence_links, evidence)

    def _linked(self, model: type[Any], field: str, ids: list[UUID]) -> tuple[Any, ...]:
        if not ids:
            return ()
        return tuple(self._session.scalars(select(model).where(getattr(model, field).in_(ids)).order_by(getattr(model, field), model.id)))

    def _rows(self, model: type[Any], field: Any, ids: list[Any], *order: Any) -> tuple[Any, ...]:
        if not ids:
            return ()
        return tuple(self._session.scalars(select(model).where(field.in_(ids)).order_by(*order)))
