"""Transactional commands for append-only Stage 2 company research."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from threading import Lock, RLock
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.models import IngestionRun, StockBasicRecord
from industry_alpha.errors import (
    EvidenceLedgerNotFound,
    EvidenceLedgerValidationError,
)
from industry_alpha.models import (
    Claim,
    ClaimEvidenceLink,
    ClaimRevision,
    EvidenceItem,
    ResearchCase,
)
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryAssertionLink,
    Stage1BeneficiaryClaimLink,
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
from industry_alpha.stage2_integrity import translate_integrity as _translate_integrity
from industry_alpha.validation import (
    CONCLUSION_STATUSES,
    INFERENCE_CONFIDENCES,
    VERIFICATION_STATUSES,
    WORKFLOW_STATES,
    reviewed_value,
    utc_timestamp,
    validate_recorded_cutoff,
    validate_utc_chronology,
)

HYPOTHESIS_STATUSES = frozenset({"draft", "supported", "disputed", "rejected"})
HYPOTHESIS_DIRECTIONS = frozenset({"positive", "negative", "mixed", "uncertain"})

_LOCKS_GUARD = Lock()
_LOCKS: dict[tuple[str, UUID], RLock] = {}


def _revision_lock(kind: str, identity: UUID) -> RLock:
    key = (kind, identity)
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, RLock())


@dataclass(frozen=True)
class Stage2VerificationInput:
    description: str
    status: str = "open"
    due_date: date | None = None


class Stage2CompanyResearchCommandService:
    """Create exact handoffs and append immutable research history."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_company_research(
        self,
        candidate_pool_revision_id: UUID,
        candidate_pool_membership_id: UUID,
        *,
        workflow_state: str,
        conclusion_status: str,
        research_question: str,
        summary: str | None,
        information_cutoff_date: date,
        recorded_at_utc: datetime | None = None,
    ) -> Stage2CompanyResearch:
        recorded = utc_timestamp(recorded_at_utc)
        information_cutoff_date = _required_date(
            information_cutoff_date, "information_cutoff_date"
        )
        validate_recorded_cutoff(information_cutoff_date, recorded)
        with _translate_integrity("this exact Stage 1 membership already has a Stage 2 research file"):
            with self._session_factory.begin() as session:
                handoff = self._exact_handoff(
                    session,
                    candidate_pool_revision_id,
                    candidate_pool_membership_id,
                    information_cutoff_date,
                    recorded,
                )
                pool, pool_revision, membership, beneficiary, beneficiary_revision, stock, _run = handoff
                research = Stage2CompanyResearch(
                    case_id=pool.case_id,
                    map_id=pool.map_id,
                    candidate_pool_id=pool.id,
                    candidate_pool_revision_id=pool_revision.id,
                    candidate_pool_membership_id=membership.id,
                    beneficiary_id=beneficiary.id,
                    beneficiary_revision_id=beneficiary_revision.id,
                    selected_map_revision_id=beneficiary_revision.selected_map_revision_id,
                    stock_basic_record_id=stock.id,
                    source=beneficiary.source,
                    stock_code=beneficiary.stock_code,
                    created_at_utc=recorded,
                )
                session.add(research)
                session.flush()
                self._freeze_handoff_boundary(
                    session, research, beneficiary_revision, information_cutoff_date, recorded
                )
                self._insert_research_revision(
                    session,
                    research,
                    workflow_state=workflow_state,
                    conclusion_status=conclusion_status,
                    research_question=research_question,
                    summary=summary,
                    information_cutoff_date=information_cutoff_date,
                    hypothesis_revision_ids=(),
                    verification_items=(),
                    recorded_at_utc=recorded,
                )
            return research

    def append_research_revision(
        self,
        company_research_id: UUID,
        *,
        workflow_state: str,
        conclusion_status: str,
        research_question: str,
        summary: str | None,
        information_cutoff_date: date,
        hypothesis_revision_ids: tuple[UUID, ...] = (),
        verification_items: tuple[Stage2VerificationInput, ...] = (),
        recorded_at_utc: datetime | None = None,
    ) -> Stage2CompanyResearchRevision:
        recorded = utc_timestamp(recorded_at_utc)
        information_cutoff_date = _required_date(
            information_cutoff_date, "information_cutoff_date"
        )
        validate_recorded_cutoff(information_cutoff_date, recorded)
        with _revision_lock("research", company_research_id):
            with _translate_integrity("company-research revision conflicts with accepted history"):
                with self._session_factory.begin() as session:
                    research = self._locked_research(session, company_research_id)
                    revision = self._insert_research_revision(
                        session,
                        research,
                        workflow_state=workflow_state,
                        conclusion_status=conclusion_status,
                        research_question=research_question,
                        summary=summary,
                        information_cutoff_date=information_cutoff_date,
                        hypothesis_revision_ids=hypothesis_revision_ids,
                        verification_items=verification_items,
                        recorded_at_utc=recorded,
                    )
            return revision

    def create_hypothesis(
        self,
        company_research_id: UUID,
        *,
        hypothesis_key: str,
        stage1_assertion_link_id: UUID,
        hypothesis_status: str,
        mechanism: str,
        direction: str,
        operating_metric: str,
        financial_statement_line: str,
        expected_lag_horizon: str,
        confidence: str,
        basis: str,
        information_cutoff_date: date,
        claim_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime | None = None,
    ) -> Stage2FinancialHypothesis:
        recorded = utc_timestamp(recorded_at_utc)
        information_cutoff_date = _required_date(
            information_cutoff_date, "information_cutoff_date"
        )
        validate_recorded_cutoff(information_cutoff_date, recorded)
        key = _required_text(hypothesis_key, "hypothesis_key", 96)
        with _translate_integrity("hypothesis key already exists in this company research file"):
            with self._session_factory.begin() as session:
                research = self._locked_research(session, company_research_id)
                assertion_link = session.get(Stage1BeneficiaryAssertionLink, stage1_assertion_link_id)
                if (
                    assertion_link is None
                    or assertion_link.beneficiary_revision_id != research.beneficiary_revision_id
                    or session.scalar(
                        select(Stage2HandoffAssertionLink.id).where(
                            Stage2HandoffAssertionLink.company_research_id
                            == research.id,
                            Stage2HandoffAssertionLink.stage1_beneficiary_assertion_link_id
                            == stage1_assertion_link_id,
                        )
                    )
                    is None
                ):
                    raise EvidenceLedgerValidationError(
                        "stage1_assertion_link_id must be frozen by the exact beneficiary revision."
                    )
                validate_utc_chronology(
                    recorded,
                    ("company-research identity timestamp", _stored_utc(research.created_at_utc)),
                    ("Stage 1 assertion-link timestamp", _stored_utc(assertion_link.recorded_at_utc)),
                )
                hypothesis = Stage2FinancialHypothesis(
                    company_research_id=research.id,
                    hypothesis_key=key,
                    stage1_assertion_link_id=assertion_link.id,
                    created_at_utc=recorded,
                )
                session.add(hypothesis)
                session.flush()
                self._insert_hypothesis_revision(
                    session,
                    research,
                    hypothesis,
                    hypothesis_status=hypothesis_status,
                    mechanism=mechanism,
                    direction=direction,
                    operating_metric=operating_metric,
                    financial_statement_line=financial_statement_line,
                    expected_lag_horizon=expected_lag_horizon,
                    confidence=confidence,
                    basis=basis,
                    information_cutoff_date=information_cutoff_date,
                    claim_revision_ids=claim_revision_ids,
                    recorded_at_utc=recorded,
                )
            return hypothesis

    def append_hypothesis_revision(
        self,
        hypothesis_id: UUID,
        *,
        hypothesis_status: str,
        mechanism: str,
        direction: str,
        operating_metric: str,
        financial_statement_line: str,
        expected_lag_horizon: str,
        confidence: str,
        basis: str,
        information_cutoff_date: date,
        claim_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime | None = None,
    ) -> Stage2FinancialHypothesisRevision:
        recorded = utc_timestamp(recorded_at_utc)
        information_cutoff_date = _required_date(
            information_cutoff_date, "information_cutoff_date"
        )
        validate_recorded_cutoff(information_cutoff_date, recorded)
        with _revision_lock("hypothesis", hypothesis_id):
            with _translate_integrity("hypothesis revision conflicts with accepted history"):
                with self._session_factory.begin() as session:
                    hypothesis = self._locked_hypothesis(session, hypothesis_id)
                    research = self._locked_research(session, hypothesis.company_research_id)
                    revision = self._insert_hypothesis_revision(
                        session,
                        research,
                        hypothesis,
                        hypothesis_status=hypothesis_status,
                        mechanism=mechanism,
                        direction=direction,
                        operating_metric=operating_metric,
                        financial_statement_line=financial_statement_line,
                        expected_lag_horizon=expected_lag_horizon,
                        confidence=confidence,
                        basis=basis,
                        information_cutoff_date=information_cutoff_date,
                        claim_revision_ids=claim_revision_ids,
                        recorded_at_utc=recorded,
                    )
            return revision

    def add_verification_item(
        self,
        company_research_revision_id: UUID,
        *,
        description: str,
        status: str = "open",
        due_date: date | None = None,
        recorded_at_utc: datetime | None = None,
    ) -> Stage2VerificationItem:
        recorded = utc_timestamp(recorded_at_utc)
        with _translate_integrity("verification item conflicts with accepted history"):
            with self._session_factory.begin() as session:
                revision = session.scalar(
                    select(Stage2CompanyResearchRevision)
                    .where(Stage2CompanyResearchRevision.id == company_research_revision_id)
                    .with_for_update()
                )
                if revision is None:
                    raise EvidenceLedgerNotFound("company-research revision was not found.")
                prior = list(
                    session.scalars(
                        select(Stage2VerificationItem)
                        .where(Stage2VerificationItem.company_research_revision_id == revision.id)
                        .order_by(Stage2VerificationItem.item_no)
                    )
                )
                chronology = [("company-research revision timestamp", _stored_utc(revision.recorded_at_utc))]
                if prior:
                    chronology.append(("previous verification timestamp", _stored_utc(prior[-1].recorded_at_utc)))
                validate_utc_chronology(recorded, *chronology)
                item = self._verification_row(revision.id, len(prior) + 1, Stage2VerificationInput(description, status, due_date), recorded)
                session.add(item)
                session.flush()
            return item

    def _insert_research_revision(
        self,
        session: Session,
        research: Stage2CompanyResearch,
        *,
        workflow_state: str,
        conclusion_status: str,
        research_question: str,
        summary: str | None,
        information_cutoff_date: date,
        hypothesis_revision_ids: tuple[UUID, ...],
        verification_items: tuple[Stage2VerificationInput, ...],
        recorded_at_utc: datetime,
    ) -> Stage2CompanyResearchRevision:
        prior = self._latest(session, Stage2CompanyResearchRevision, "company_research_id", research.id)
        chronology = [("company-research identity timestamp", _stored_utc(research.created_at_utc))]
        if prior is not None:
            chronology.append(("previous company-research revision timestamp", _stored_utc(prior.recorded_at_utc)))
        validate_utc_chronology(recorded_at_utc, *chronology)
        state = reviewed_value(workflow_state, "workflow_state", WORKFLOW_STATES)
        conclusion = reviewed_value(conclusion_status, "conclusion_status", CONCLUSION_STATUSES)
        hypotheses = self._hypothesis_revisions(
            session, research, hypothesis_revision_ids, information_cutoff_date, recorded_at_utc
        )
        if state == "completed":
            accepted = [item for item in hypotheses if item.hypothesis_status in {"supported", "disputed"}]
            if not accepted:
                raise EvidenceLedgerValidationError(
                    "completed research revisions require at least one accepted hypothesis revision."
                )
            if not verification_items:
                raise EvidenceLedgerValidationError(
                    "completed research revisions require a non-empty 后续验证清单."
                )
            if any(self._hypothesis_has_missing_evidence(session, item) for item in hypotheses):
                raise EvidenceLedgerValidationError(
                    "completed research revisions cannot hide missing hypothesis evidence."
                )
            if conclusion == "supported" and (
                not any(item.hypothesis_status == "supported" for item in hypotheses)
                or any(item.hypothesis_status == "disputed" for item in hypotheses)
            ):
                raise EvidenceLedgerValidationError(
                    "a supported completed conclusion requires supported hypotheses without an unresolved disputed hypothesis."
                )
            if conclusion == "disputed" and not any(
                item.hypothesis_status == "disputed" for item in hypotheses
            ):
                raise EvidenceLedgerValidationError(
                    "a disputed completed conclusion requires a disputed hypothesis."
                )
        if conclusion == "supported" and (
            not any(item.hypothesis_status == "supported" for item in hypotheses)
            or any(item.hypothesis_status == "disputed" for item in hypotheses)
            or any(
                self._hypothesis_has_missing_evidence(session, item)
                for item in hypotheses
            )
        ):
            raise EvidenceLedgerValidationError(
                "a supported conclusion requires supported hypotheses without disputes or missing evidence."
            )
        if conclusion == "disputed" and not any(
            item.hypothesis_status == "disputed" for item in hypotheses
        ):
            raise EvidenceLedgerValidationError(
                "a disputed conclusion requires a disputed hypothesis."
            )
        revision = Stage2CompanyResearchRevision(
            company_research_id=research.id,
            revision_no=1 if prior is None else prior.revision_no + 1,
            workflow_state=state,
            conclusion_status=conclusion,
            research_question=_required_text(research_question, "research_question", 2000),
            summary=_optional_text(summary, "summary", 4000),
            information_cutoff_date=information_cutoff_date,
            recorded_at_utc=recorded_at_utc,
            supersedes_revision_id=None if prior is None else prior.id,
        )
        session.add(revision)
        session.flush()
        for hypothesis_revision in hypotheses:
            session.add(
                Stage2ResearchHypothesisLink(
                    company_research_revision_id=revision.id,
                    hypothesis_id=hypothesis_revision.hypothesis_id,
                    hypothesis_revision_id=hypothesis_revision.id,
                    recorded_at_utc=recorded_at_utc,
                )
            )
        for number, item in enumerate(verification_items, 1):
            session.add(self._verification_row(revision.id, number, item, recorded_at_utc))
        session.flush()
        return revision

    def _insert_hypothesis_revision(
        self,
        session: Session,
        research: Stage2CompanyResearch,
        hypothesis: Stage2FinancialHypothesis,
        *,
        hypothesis_status: str,
        mechanism: str,
        direction: str,
        operating_metric: str,
        financial_statement_line: str,
        expected_lag_horizon: str,
        confidence: str,
        basis: str,
        information_cutoff_date: date,
        claim_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime,
    ) -> Stage2FinancialHypothesisRevision:
        prior = self._latest(session, Stage2FinancialHypothesisRevision, "hypothesis_id", hypothesis.id)
        chronology = [("hypothesis identity timestamp", _stored_utc(hypothesis.created_at_utc))]
        research_boundary = self._latest(
            session,
            Stage2CompanyResearchRevision,
            "company_research_id",
            research.id,
        )
        if research_boundary is not None:
            chronology.append(
                (
                    "latest company-research revision timestamp",
                    _stored_utc(research_boundary.recorded_at_utc),
                )
            )
        if prior is not None:
            chronology.append(("previous hypothesis revision timestamp", _stored_utc(prior.recorded_at_utc)))
        validate_utc_chronology(recorded_at_utc, *chronology)
        status = reviewed_value(hypothesis_status, "hypothesis_status", HYPOTHESIS_STATUSES)
        normalized_direction = reviewed_value(direction, "direction", HYPOTHESIS_DIRECTIONS)
        normalized_confidence = reviewed_value(confidence, "confidence", INFERENCE_CONFIDENCES)
        claims = self._claims(session, research.case_id, claim_revision_ids, information_cutoff_date, recorded_at_utc)
        boundaries = self._evidence_boundaries(session, claims, information_cutoff_date, recorded_at_utc)
        has_supported_abc_claim = any(
            claim.claim_status == "supported"
            and link.relation == "supports"
            and evidence.evidence_grade in {"A", "B", "C"}
            for claim, link, evidence in boundaries
        )
        has_conflict = any(link.relation == "contradicts" for _claim, link, _evidence in boundaries)
        if status == "supported" and (not has_supported_abc_claim or has_conflict):
            raise EvidenceLedgerValidationError(
                "supported hypotheses require a visible supported A/B/C-backed claim revision and no contradiction."
            )
        if status == "disputed" and not (
            has_conflict or any(claim.claim_status == "disputed" for claim in claims)
        ):
            raise EvidenceLedgerValidationError(
                "disputed hypotheses require a disputed claim or visible contradiction."
            )
        revision = Stage2FinancialHypothesisRevision(
            hypothesis_id=hypothesis.id,
            revision_no=1 if prior is None else prior.revision_no + 1,
            hypothesis_status=status,
            mechanism=_required_text(mechanism, "mechanism", 4000),
            direction=normalized_direction,
            operating_metric=_required_text(operating_metric, "operating_metric", 300),
            financial_statement_line=_required_text(financial_statement_line, "financial_statement_line", 300),
            expected_lag_horizon=_required_text(expected_lag_horizon, "expected_lag_horizon", 300),
            confidence=normalized_confidence,
            basis=_required_text(basis, "basis", 4000),
            information_cutoff_date=information_cutoff_date,
            recorded_at_utc=recorded_at_utc,
            supersedes_revision_id=None if prior is None else prior.id,
        )
        session.add(revision)
        session.flush()
        for claim in claims:
            session.add(Stage2HypothesisClaimLink(hypothesis_revision_id=revision.id, claim_revision_id=claim.id, recorded_at_utc=recorded_at_utc))
        for claim, link, evidence in boundaries:
            session.add(Stage2HypothesisEvidenceLink(hypothesis_revision_id=revision.id, claim_revision_id=claim.id, claim_evidence_link_id=link.id, evidence_id=evidence.id, recorded_at_utc=recorded_at_utc))
        session.flush()
        return revision

    def _exact_handoff(
        self,
        session: Session,
        pool_revision_id: UUID,
        membership_id: UUID,
        cutoff: date,
        recorded: datetime,
    ) -> tuple[Any, ...]:
        pool_revision = session.scalar(select(Stage1CandidatePoolRevision).where(Stage1CandidatePoolRevision.id == pool_revision_id).with_for_update())
        membership = session.scalar(select(Stage1CandidatePoolMembership).where(Stage1CandidatePoolMembership.id == membership_id).with_for_update())
        if pool_revision is None or membership is None:
            raise EvidenceLedgerNotFound("candidate-pool revision or membership was not found.")
        if membership.candidate_pool_revision_id != pool_revision.id:
            raise EvidenceLedgerValidationError("membership must belong to the exact candidate-pool revision.")
        pool = session.get(Stage1CandidatePool, pool_revision.candidate_pool_id)
        beneficiary = session.get(Stage1Beneficiary, membership.beneficiary_id)
        beneficiary_revision = session.get(Stage1BeneficiaryRevision, membership.beneficiary_revision_id)
        if pool is None or beneficiary is None or beneficiary_revision is None:
            raise EvidenceLedgerNotFound("frozen Stage 1 handoff rows were not found.")
        if (
            beneficiary_revision.beneficiary_id != beneficiary.id
            or beneficiary.case_id != pool.case_id
            or beneficiary.map_id != pool.map_id
            or beneficiary_revision.assessment_status != "supported"
            or beneficiary_revision.selected_map_revision_id != pool_revision.selected_map_revision_id
        ):
            raise EvidenceLedgerValidationError("candidate-pool handoff boundaries are inconsistent.")
        stock = session.get(StockBasicRecord, beneficiary_revision.stock_basic_record_id)
        run = None if stock is None else session.get(IngestionRun, stock.ingestion_run_id)
        case = session.get(ResearchCase, pool.case_id)
        if stock is None or run is None or case is None or run.status != "succeeded" or run.completed_at is None:
            raise EvidenceLedgerValidationError("the frozen company snapshot must belong to a successful ingestion run.")
        if stock.source != beneficiary.source or stock.stock_code != beneficiary.stock_code:
            raise EvidenceLedgerValidationError("the frozen company snapshot does not match the Stage 1 company identity.")
        dated = (pool_revision.information_cutoff_date, beneficiary_revision.information_cutoff_date, run.information_cutoff_date)
        if any(item > cutoff for item in dated):
            raise EvidenceLedgerValidationError("the Stage 1 handoff is not visible at the requested cutoff.")
        validate_utc_chronology(
            recorded,
            ("research case creation timestamp", _stored_utc(case.created_at_utc)),
            ("candidate-pool identity timestamp", _stored_utc(pool.created_at_utc)),
            ("candidate-pool revision timestamp", _stored_utc(pool_revision.recorded_at_utc)),
            ("candidate-pool membership timestamp", _stored_utc(membership.recorded_at_utc)),
            ("beneficiary identity timestamp", _stored_utc(beneficiary.created_at_utc)),
            ("beneficiary revision timestamp", _stored_utc(beneficiary_revision.recorded_at_utc)),
            ("company snapshot import timestamp", _stored_utc(run.imported_at)),
            ("company snapshot completion timestamp", _stored_utc(run.completed_at)),
        )
        return pool, pool_revision, membership, beneficiary, beneficiary_revision, stock, run

    @staticmethod
    def _freeze_handoff_boundary(session: Session, research: Stage2CompanyResearch, beneficiary_revision: Stage1BeneficiaryRevision, cutoff: date, recorded: datetime) -> None:
        assertion_links = list(
            session.scalars(
                select(Stage1BeneficiaryAssertionLink)
                .where(
                    Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                    == beneficiary_revision.id
                )
                .order_by(Stage1BeneficiaryAssertionLink.id)
            )
        )
        for link in assertion_links:
            if _stored_utc(link.recorded_at_utc) > _stored_utc(
                beneficiary_revision.recorded_at_utc
            ):
                raise EvidenceLedgerValidationError(
                    "Stage 1 assertion links added after the frozen beneficiary revision cannot enter the Stage 2 handoff."
                )
            session.add(
                Stage2HandoffAssertionLink(
                    company_research_id=research.id,
                    stage1_beneficiary_assertion_link_id=link.id,
                    recorded_at_utc=recorded,
                )
            )
        stage1_links = list(
            session.scalars(
                select(Stage1BeneficiaryClaimLink)
                .where(
                    Stage1BeneficiaryClaimLink.beneficiary_revision_id
                    == beneficiary_revision.id
                )
                .order_by(Stage1BeneficiaryClaimLink.claim_revision_id)
            )
        )
        for link in stage1_links:
            if _stored_utc(link.recorded_at_utc) > _stored_utc(
                beneficiary_revision.recorded_at_utc
            ):
                raise EvidenceLedgerValidationError(
                    "Stage 1 claim links added after the frozen beneficiary revision cannot enter the Stage 2 handoff."
                )
            session.add(
                Stage2HandoffClaimLink(
                    company_research_id=research.id,
                    stage1_beneficiary_claim_link_id=link.id,
                    claim_revision_id=link.claim_revision_id,
                    recorded_at_utc=recorded,
                )
            )
        claim_ids = [item.claim_revision_id for item in stage1_links]
        boundary_cutoff = beneficiary_revision.information_cutoff_date
        boundary_recorded = _stored_utc(beneficiary_revision.recorded_at_utc)
        claims = (
            Stage2CompanyResearchCommandService._claims(
                session,
                research.case_id,
                tuple(claim_ids),
                boundary_cutoff,
                boundary_recorded,
            )
            if claim_ids
            else []
        )
        for claim, link, evidence in Stage2CompanyResearchCommandService._evidence_boundaries(
            session,
            claims,
            boundary_cutoff,
            boundary_recorded,
        ):
            session.add(Stage2HandoffEvidenceLink(company_research_id=research.id, claim_revision_id=claim.id, claim_evidence_link_id=link.id, evidence_id=evidence.id, recorded_at_utc=recorded))
        session.flush()

    @staticmethod
    def _claims(session: Session, case_id: UUID, ids: tuple[UUID, ...], cutoff: date, recorded: datetime) -> list[ClaimRevision]:
        if not ids or len(ids) != len(set(ids)):
            raise EvidenceLedgerValidationError("claim_revision_ids must be non-empty and unique.")
        claims = list(session.scalars(select(ClaimRevision).where(ClaimRevision.id.in_(ids)).order_by(ClaimRevision.id).with_for_update()))
        if len(claims) != len(ids):
            raise EvidenceLedgerNotFound("one or more claim revisions were not found.")
        for revision in claims:
            identity = session.get(Claim, revision.claim_id)
            if identity is None or identity.case_id != case_id:
                raise EvidenceLedgerValidationError("hypothesis claims must belong to the same research case.")
            if revision.information_cutoff_date > cutoff:
                raise EvidenceLedgerValidationError("claim revision cutoff exceeds the hypothesis cutoff.")
            validate_utc_chronology(recorded, ("claim revision timestamp", _stored_utc(revision.recorded_at_utc)))
        return claims

    @staticmethod
    def _evidence_boundaries(session: Session, claims: list[ClaimRevision], cutoff: date, recorded: datetime) -> list[tuple[ClaimRevision, ClaimEvidenceLink, EvidenceItem]]:
        rows: list[tuple[ClaimRevision, ClaimEvidenceLink, EvidenceItem]] = []
        for claim in claims:
            links = session.scalars(select(ClaimEvidenceLink).where(ClaimEvidenceLink.claim_revision_id == claim.id).order_by(ClaimEvidenceLink.id))
            for link in links:
                evidence = session.get(EvidenceItem, link.evidence_id)
                if (
                    evidence is not None
                    and evidence.information_date <= cutoff
                    and evidence.information_date <= claim.information_cutoff_date
                    and _stored_utc(evidence.recorded_at_utc) <= recorded
                    and _stored_utc(link.recorded_at_utc) <= recorded
                ):
                    rows.append((claim, link, evidence))
        return rows

    @staticmethod
    def _hypothesis_revisions(session: Session, research: Stage2CompanyResearch, ids: tuple[UUID, ...], cutoff: date, recorded: datetime) -> list[Stage2FinancialHypothesisRevision]:
        if len(ids) != len(set(ids)):
            raise EvidenceLedgerValidationError("hypothesis_revision_ids must be unique.")
        revisions = list(session.scalars(select(Stage2FinancialHypothesisRevision).where(Stage2FinancialHypothesisRevision.id.in_(ids)).order_by(Stage2FinancialHypothesisRevision.id))) if ids else []
        if len(revisions) != len(ids):
            raise EvidenceLedgerNotFound("one or more hypothesis revisions were not found.")
        seen: set[UUID] = set()
        for revision in revisions:
            hypothesis = session.get(Stage2FinancialHypothesis, revision.hypothesis_id)
            if hypothesis is None or hypothesis.company_research_id != research.id:
                raise EvidenceLedgerValidationError("hypothesis revisions must belong to this company research file.")
            if hypothesis.id in seen:
                raise EvidenceLedgerValidationError("only one revision per hypothesis may be frozen in a research revision.")
            seen.add(hypothesis.id)
            if revision.information_cutoff_date > cutoff:
                raise EvidenceLedgerValidationError("hypothesis cutoff exceeds the research revision cutoff.")
            validate_utc_chronology(recorded, ("hypothesis revision timestamp", _stored_utc(revision.recorded_at_utc)))
        return revisions

    @staticmethod
    def _hypothesis_has_missing_evidence(session: Session, revision: Stage2FinancialHypothesisRevision) -> bool:
        claim_ids = list(session.scalars(select(Stage2HypothesisClaimLink.claim_revision_id).where(Stage2HypothesisClaimLink.hypothesis_revision_id == revision.id)))
        evidence_claim_ids = set(session.scalars(select(Stage2HypothesisEvidenceLink.claim_revision_id).where(Stage2HypothesisEvidenceLink.hypothesis_revision_id == revision.id)))
        return any(item not in evidence_claim_ids for item in claim_ids)

    @staticmethod
    def _verification_row(revision_id: UUID, number: int, item: Stage2VerificationInput, recorded: datetime) -> Stage2VerificationItem:
        if not isinstance(item, Stage2VerificationInput):
            raise EvidenceLedgerValidationError("verification_items must contain Stage2VerificationInput values.")
        due_date = (
            None
            if item.due_date is None
            else _required_date(item.due_date, "verification due_date")
        )
        return Stage2VerificationItem(
            company_research_revision_id=revision_id,
            item_no=number,
            description=_required_text(item.description, "verification description", 2000),
            status=reviewed_value(item.status, "verification status", VERIFICATION_STATUSES),
            due_date=due_date,
            recorded_at_utc=recorded,
        )

    @staticmethod
    def _latest(session: Session, model: type[Any], field: str, identity: UUID) -> Any | None:
        return session.scalar(select(model).where(getattr(model, field) == identity).order_by(model.revision_no.desc()).limit(1))

    @staticmethod
    def _locked_research(session: Session, identity: UUID) -> Stage2CompanyResearch:
        row = session.scalar(select(Stage2CompanyResearch).where(Stage2CompanyResearch.id == identity).with_for_update())
        if row is None:
            raise EvidenceLedgerNotFound(f"Stage 2 company research {identity} was not found.")
        return row

    @staticmethod
    def _locked_hypothesis(session: Session, identity: UUID) -> Stage2FinancialHypothesis:
        row = session.scalar(select(Stage2FinancialHypothesis).where(Stage2FinancialHypothesis.id == identity).with_for_update())
        if row is None:
            raise EvidenceLedgerNotFound(f"Stage 2 hypothesis {identity} was not found.")
        return row

def _required_text(value: str, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise EvidenceLedgerValidationError(f"{field} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise EvidenceLedgerValidationError(f"{field} must not be blank.")
    if len(normalized) > maximum:
        raise EvidenceLedgerValidationError(f"{field} must not exceed {maximum} characters.")
    return normalized


def _optional_text(value: str | None, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise EvidenceLedgerValidationError(f"{field} must be a string or None.")
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > maximum:
        raise EvidenceLedgerValidationError(f"{field} must not exceed {maximum} characters.")
    return normalized


def _stored_utc(value: datetime | None) -> datetime:
    if value is None:
        raise EvidenceLedgerValidationError("required UTC timestamp is missing.")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _required_date(value: date, field: str) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise EvidenceLedgerValidationError(f"{field} must be a date.")
    return value
