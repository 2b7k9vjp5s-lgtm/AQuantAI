"""Transactional commands for v0.6C catalyst and risk assessments."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from threading import Lock, RLock
from typing import Any, Iterator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.errors import EvidenceLedgerConflictError, EvidenceLedgerNotFound, EvidenceLedgerValidationError
from industry_alpha.stage2_assessments_models import (
    Stage2CatalystAssessment, Stage2CatalystAssessmentRevision, Stage2CatalystClaimLink,
    Stage2CatalystEvidenceLink, Stage2CatalystExpectationLink, Stage2CatalystHypothesisLink,
    Stage2CatalystValuationLink, Stage2RiskAssessment, Stage2RiskAssessmentRevision,
    Stage2RiskClaimLink, Stage2RiskEvidenceLink, Stage2RiskExpectationLink,
    Stage2RiskHypothesisLink, Stage2RiskValuationLink,
)
from industry_alpha.stage2_boundary import (
    Stage2BaseBoundary as _Boundary,
    build_stage2_base_boundary as _frozen_boundary,
    load_unique as _load_unique,
    lock_company_research as _locked_research,
    required_text as _required_text,
    stored_utc as _stored_utc,
    time_boundary as _time_boundary,
    visible_upstream as _visible_upstream,
)
from industry_alpha.stage2_models import Stage2CompanyResearch
from industry_alpha.validation import INFERENCE_CONFIDENCES, reviewed_value, validate_utc_chronology


CATALYST_CATEGORIES = frozenset({"demand", "supply", "product", "customer", "certification", "capacity", "policy", "financial", "operational", "other"})
RISK_CATEGORIES = frozenset({"demand", "supply", "execution", "competition", "customer", "policy", "financial", "governance", "operational", "other"})
ASSESSMENT_STATUSES = frozenset({"draft", "supported", "disputed", "rejected"})
_LOCKS_GUARD = Lock()
_LOCKS: dict[tuple[str, UUID], RLock] = {}


def _revision_lock(kind: str, identity: UUID) -> RLock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault((kind, identity), RLock())


class Stage2AssessmentCommandService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_catalyst(self, company_research_id: UUID, *, catalyst_key: str, **data: Any) -> Stage2CatalystAssessment:
        recorded, cutoff = _time_boundary(data)
        with self._integrity("catalyst key already exists"):
            with self._session_factory.begin() as session:
                research = _locked_research(session, company_research_id)
                identity = Stage2CatalystAssessment(
                    company_research_id=research.id,
                    catalyst_key=_required_text(catalyst_key, "catalyst_key", 96),
                    created_at_utc=recorded,
                )
                session.add(identity)
                session.flush()
                self._insert_catalyst(session, research, identity, recorded=recorded, cutoff=cutoff, **data)
            return identity

    def append_catalyst_revision(self, catalyst_id: UUID, **data: Any) -> Stage2CatalystAssessmentRevision:
        recorded, cutoff = _time_boundary(data)
        with _revision_lock("catalyst", catalyst_id), self._integrity("catalyst revision conflicts with history"):
            with self._session_factory.begin() as session:
                identity = _locked_identity(session, Stage2CatalystAssessment, catalyst_id, "catalyst")
                research = _locked_research(session, identity.company_research_id)
                return self._insert_catalyst(session, research, identity, recorded=recorded, cutoff=cutoff, **data)

    def create_risk(self, company_research_id: UUID, *, risk_key: str, **data: Any) -> Stage2RiskAssessment:
        recorded, cutoff = _time_boundary(data)
        with self._integrity("risk key already exists"):
            with self._session_factory.begin() as session:
                research = _locked_research(session, company_research_id)
                identity = Stage2RiskAssessment(
                    company_research_id=research.id,
                    risk_key=_required_text(risk_key, "risk_key", 96),
                    created_at_utc=recorded,
                )
                session.add(identity)
                session.flush()
                self._insert_risk(session, research, identity, recorded=recorded, cutoff=cutoff, **data)
            return identity

    def append_risk_revision(self, risk_id: UUID, **data: Any) -> Stage2RiskAssessmentRevision:
        recorded, cutoff = _time_boundary(data)
        with _revision_lock("risk", risk_id), self._integrity("risk revision conflicts with history"):
            with self._session_factory.begin() as session:
                identity = _locked_identity(session, Stage2RiskAssessment, risk_id, "risk")
                research = _locked_research(session, identity.company_research_id)
                return self._insert_risk(session, research, identity, recorded=recorded, cutoff=cutoff, **data)

    def _insert_catalyst(self, session: Session, research: Stage2CompanyResearch, identity: Stage2CatalystAssessment, *, recorded: datetime, cutoff: date, **data: Any) -> Stage2CatalystAssessmentRevision:
        boundary = _frozen_boundary(session, research, cutoff=cutoff, recorded=recorded, **data)
        status = reviewed_value(data["status"], "status", ASSESSMENT_STATUSES)
        _validate_status(status, boundary)
        prior = _latest(session, Stage2CatalystAssessmentRevision, "catalyst_id", identity.id)
        _validate_chronology(identity.created_at_utc, prior, boundary, recorded, "catalyst")
        revision = Stage2CatalystAssessmentRevision(
            catalyst_id=identity.id,
            company_research_revision_id=boundary.research_revision.id,
            revision_no=1 if prior is None else prior.revision_no + 1,
            catalyst_category=reviewed_value(data["catalyst_category"], "catalyst_category", CATALYST_CATEGORIES),
            subject=_required_text(data["subject"], "subject", 500),
            expected_observation_window=_required_text(data["expected_observation_window"], "expected_observation_window", 300),
            status=status,
            confidence=reviewed_value(data["confidence"], "confidence", INFERENCE_CONFIDENCES),
            trigger_observation_criteria=_required_text(data["trigger_observation_criteria"], "trigger_observation_criteria", 2000),
            basis=_required_text(data["basis"], "basis", 4000),
            uncertainty=_required_text(data["uncertainty"], "uncertainty", 2000),
            information_cutoff_date=cutoff,
            recorded_at_utc=recorded,
            supersedes_revision_id=None if prior is None else prior.id,
        )
        session.add(revision)
        session.flush()
        _insert_links(session, "catalyst", revision.id, boundary, recorded)
        session.flush()
        return revision

    def _insert_risk(self, session: Session, research: Stage2CompanyResearch, identity: Stage2RiskAssessment, *, recorded: datetime, cutoff: date, **data: Any) -> Stage2RiskAssessmentRevision:
        boundary = _frozen_boundary(session, research, cutoff=cutoff, recorded=recorded, **data)
        status = reviewed_value(data["status"], "status", ASSESSMENT_STATUSES)
        _validate_status(status, boundary)
        prior = _latest(session, Stage2RiskAssessmentRevision, "risk_id", identity.id)
        _validate_chronology(identity.created_at_utc, prior, boundary, recorded, "risk")
        revision = Stage2RiskAssessmentRevision(
            risk_id=identity.id,
            company_research_revision_id=boundary.research_revision.id,
            revision_no=1 if prior is None else prior.revision_no + 1,
            risk_category=reviewed_value(data["risk_category"], "risk_category", RISK_CATEGORIES),
            subject=_required_text(data["subject"], "subject", 500),
            downside_path=_required_text(data["downside_path"], "downside_path", 2000),
            thesis_invalidation_condition=_required_text(data["thesis_invalidation_condition"], "thesis_invalidation_condition", 2000),
            mitigants=_required_text(data["mitigants"], "mitigants", 2000),
            status=status,
            confidence=reviewed_value(data["confidence"], "confidence", INFERENCE_CONFIDENCES),
            basis=_required_text(data["basis"], "basis", 4000),
            uncertainty=_required_text(data["uncertainty"], "uncertainty", 2000),
            information_cutoff_date=cutoff,
            recorded_at_utc=recorded,
            supersedes_revision_id=None if prior is None else prior.id,
        )
        session.add(revision)
        session.flush()
        _insert_links(session, "risk", revision.id, boundary, recorded)
        session.flush()
        return revision

    @contextmanager
    def _integrity(self, message: str) -> Iterator[None]:
        try:
            yield
        except IntegrityError as exc:
            raise EvidenceLedgerConflictError(message) from exc


def _validate_status(status: str, boundary: _Boundary) -> None:
    has_supported_abc = any(claim.claim_status == "supported" and link.relation == "supports" and item.evidence_grade in {"A", "B", "C"} for claim, link, item in boundary.evidence)
    has_conflict = any(link.relation == "contradicts" for _claim, link, _item in boundary.evidence)
    if status == "supported" and (not has_supported_abc or has_conflict):
        raise EvidenceLedgerValidationError("supported assessments require a visible supported A/B/C-backed claim and no contradiction.")
    if status == "disputed" and not (has_conflict or any(item.claim_status == "disputed" for item in boundary.claims)):
        raise EvidenceLedgerValidationError("disputed assessments require a disputed claim or visible contradiction.")


def _validate_chronology(created: datetime, prior: Any | None, boundary: _Boundary, recorded: datetime, kind: str) -> None:
    rows = [(f"{kind} identity timestamp", _stored_utc(created)), ("company-research revision timestamp", _stored_utc(boundary.research_revision.recorded_at_utc))]
    rows.extend(("hypothesis revision timestamp", _stored_utc(item.recorded_at_utc)) for item in boundary.hypotheses)
    rows.extend(("expectation revision timestamp", _stored_utc(item.recorded_at_utc)) for item in boundary.expectations)
    rows.extend(("valuation revision timestamp", _stored_utc(item.recorded_at_utc)) for item in boundary.valuations)
    rows.extend(("claim revision timestamp", _stored_utc(item.recorded_at_utc)) for item in boundary.claims)
    rows.extend(("evidence/link timestamp", max(_stored_utc(link.recorded_at_utc), _stored_utc(item.recorded_at_utc))) for _claim, link, item in boundary.evidence)
    if prior is not None:
        rows.append((f"previous {kind} revision timestamp", _stored_utc(prior.recorded_at_utc)))
    validate_utc_chronology(recorded, *rows)


def _insert_links(session: Session, kind: str, revision_id: UUID, boundary: _Boundary, recorded: datetime) -> None:
    if kind == "catalyst":
        hypothesis_model, expectation_model, valuation_model, claim_model, evidence_model = Stage2CatalystHypothesisLink, Stage2CatalystExpectationLink, Stage2CatalystValuationLink, Stage2CatalystClaimLink, Stage2CatalystEvidenceLink
        revision_field = "catalyst_revision_id"
    else:
        hypothesis_model, expectation_model, valuation_model, claim_model, evidence_model = Stage2RiskHypothesisLink, Stage2RiskExpectationLink, Stage2RiskValuationLink, Stage2RiskClaimLink, Stage2RiskEvidenceLink
        revision_field = "risk_revision_id"
    common = {revision_field: revision_id, "recorded_at_utc": recorded}
    session.add_all(hypothesis_model(**common, hypothesis_revision_id=item.id) for item in boundary.hypotheses)
    session.add_all(expectation_model(**common, expectation_revision_id=item.id) for item in boundary.expectations)
    session.add_all(valuation_model(**common, valuation_revision_id=item.id) for item in boundary.valuations)
    session.add_all(claim_model(**common, claim_revision_id=item.id) for item in boundary.claims)
    session.add_all(evidence_model(**common, claim_revision_id=claim.id, claim_evidence_link_id=link.id, evidence_id=item.id) for claim, link, item in boundary.evidence)


def _locked_identity(session: Session, model: type[Any], identity: UUID, label: str) -> Any:
    row = session.scalar(select(model).where(model.id == identity).with_for_update())
    if row is None:
        raise EvidenceLedgerNotFound(f"Stage 2 {label} assessment {identity} was not found.")
    return row


def _latest(session: Session, model: type[Any], field: str, identity: UUID) -> Any | None:
    return session.scalar(select(model).where(getattr(model, field) == identity).order_by(model.revision_no.desc()).limit(1))
