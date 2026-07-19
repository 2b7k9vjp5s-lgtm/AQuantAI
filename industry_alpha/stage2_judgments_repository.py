"""Repository helpers for v0.6D judgment reads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem
from industry_alpha.stage2_judgments_models import (
    Stage2CompanyJudgment, Stage2CompanyJudgmentCatalystLink, Stage2CompanyJudgmentClaimLink,
    Stage2CompanyJudgmentEvidenceLink, Stage2CompanyJudgmentExpectationLink,
    Stage2CompanyJudgmentHypothesisLink, Stage2CompanyJudgmentRevision,
    Stage2CompanyJudgmentRiskLink, Stage2CompanyJudgmentValuationLink,
    Stage2IndustryJudgment, Stage2IndustryJudgmentCatalystLink,
    Stage2IndustryJudgmentClaimLink, Stage2IndustryJudgmentEvidenceLink,
    Stage2IndustryJudgmentExpectationLink, Stage2IndustryJudgmentHypothesisLink,
    Stage2IndustryJudgmentRevision, Stage2IndustryJudgmentRiskLink,
    Stage2IndustryJudgmentValuationLink,
)


@dataclass(frozen=True)
class Stage2JudgmentRows:
    identity: Any
    revisions: tuple[Any, ...]
    hypothesis_links: tuple[Any, ...]
    expectation_links: tuple[Any, ...]
    valuation_links: tuple[Any, ...]
    catalyst_links: tuple[Any, ...]
    risk_links: tuple[Any, ...]
    claim_links: tuple[Any, ...]
    evidence_links: tuple[Any, ...]
    claims: tuple[Claim, ...]
    claim_revisions: tuple[ClaimRevision, ...]
    source_evidence_links: tuple[ClaimEvidenceLink, ...]
    evidence: tuple[EvidenceItem, ...]


class Stage2JudgmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_industry(self, company_research_id: UUID | None = None) -> tuple[Stage2IndustryJudgment, ...]:
        return self._list(Stage2IndustryJudgment, company_research_id)

    def list_company(self, company_research_id: UUID | None = None) -> tuple[Stage2CompanyJudgment, ...]:
        return self._list(Stage2CompanyJudgment, company_research_id)

    def load_industry(self, identity: UUID) -> Stage2JudgmentRows | None:
        return self._load("industry", identity)

    def load_company(self, identity: UUID) -> Stage2JudgmentRows | None:
        return self._load("company", identity)

    def _list(self, model: type[Any], company_research_id: UUID | None) -> tuple[Any, ...]:
        statement = select(model)
        if company_research_id is not None:
            statement = statement.where(model.company_research_id == company_research_id)
        return tuple(self._session.scalars(statement.order_by(model.judgment_key, model.id)))

    def _load(self, kind: str, identity: UUID) -> Stage2JudgmentRows | None:
        prefix = "Industry" if kind == "industry" else "Company"
        identity_model = Stage2IndustryJudgment if kind == "industry" else Stage2CompanyJudgment
        revision_model = Stage2IndustryJudgmentRevision if kind == "industry" else Stage2CompanyJudgmentRevision
        row = self._session.get(identity_model, identity)
        if row is None:
            return None
        revisions = tuple(self._session.scalars(select(revision_model).where(revision_model.judgment_id == identity).order_by(revision_model.revision_no)))
        ids = [item.id for item in revisions]
        models = {name: globals()[f"Stage2{prefix}Judgment{name.title()}Link"] for name in ("hypothesis", "expectation", "valuation", "catalyst", "risk", "claim", "evidence")}
        links = {name: self._linked(model, ids) for name, model in models.items()}
        claim_revisions = self._rows(ClaimRevision, [item.claim_revision_id for item in links["claim"]], ClaimRevision.claim_id, ClaimRevision.revision_no)
        claims = self._rows(Claim, [item.claim_id for item in claim_revisions], Claim.claim_key, Claim.id)
        source_links = self._rows(ClaimEvidenceLink, [item.claim_evidence_link_id for item in links["evidence"]], ClaimEvidenceLink.id)
        evidence = self._rows(EvidenceItem, [item.evidence_id for item in links["evidence"]], EvidenceItem.id)
        return Stage2JudgmentRows(row, revisions, links["hypothesis"], links["expectation"], links["valuation"], links["catalyst"], links["risk"], links["claim"], links["evidence"], claims, claim_revisions, source_links, evidence)

    def _linked(self, model: type[Any], ids: list[UUID]) -> tuple[Any, ...]:
        if not ids:
            return ()
        return tuple(self._session.scalars(select(model).where(model.judgment_revision_id.in_(ids)).order_by(model.judgment_revision_id, model.id)))

    def _rows(self, model: type[Any], ids: list[UUID], *order: Any) -> tuple[Any, ...]:
        if not ids:
            return ()
        return tuple(self._session.scalars(select(model).where(model.id.in_(ids)).order_by(*order)))
