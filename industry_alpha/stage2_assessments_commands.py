"""Transactional commands for v0.6C catalyst and risk assessments."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from threading import Lock, RLock
from typing import Any, Iterator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.errors import EvidenceLedgerConflictError, EvidenceLedgerNotFound, EvidenceLedgerValidationError
from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem
from industry_alpha.stage2_models import Stage2CompanyResearch, Stage2CompanyResearchRevision, Stage2FinancialHypothesis, Stage2FinancialHypothesisRevision, Stage2ResearchHypothesisLink
from industry_alpha.stage2_expectations_models import (
    Stage2ExpectationClaimLink, Stage2ExpectationEvidenceLink,
    Stage2ExpectationHypothesisLink, Stage2MarketExpectation,
    Stage2MarketExpectationRevision, Stage2ValuationClaimLink,
    Stage2ValuationEvidenceLink, Stage2ValuationHypothesisLink,
    Stage2ValuationSnapshot, Stage2ValuationSnapshotRevision,
)
from industry_alpha.stage2_assessments_models import (
    Stage2CatalystAssessment, Stage2CatalystAssessmentRevision, Stage2CatalystClaimLink,
    Stage2CatalystEvidenceLink, Stage2CatalystExpectationLink, Stage2CatalystHypothesisLink,
    Stage2CatalystValuationLink, Stage2RiskAssessment, Stage2RiskAssessmentRevision,
    Stage2RiskClaimLink, Stage2RiskEvidenceLink, Stage2RiskExpectationLink,
    Stage2RiskHypothesisLink, Stage2RiskValuationLink,
)
from industry_alpha.validation import INFERENCE_CONFIDENCES, reviewed_value, utc_timestamp, validate_recorded_cutoff, validate_utc_chronology


CATALYST_CATEGORIES = frozenset({"demand", "supply", "product", "customer", "certification", "capacity", "policy", "financial", "operational", "other"})
RISK_CATEGORIES = frozenset({"demand", "supply", "execution", "competition", "customer", "policy", "financial", "governance", "operational", "other"})
ASSESSMENT_STATUSES = frozenset({"draft", "supported", "disputed", "rejected"})
_LOCKS_GUARD = Lock()
_LOCKS: dict[tuple[str, UUID], RLock] = {}


@dataclass(frozen=True)
class _Boundary:
    research_revision: Stage2CompanyResearchRevision
    hypotheses: tuple[Stage2FinancialHypothesisRevision, ...]
    expectations: tuple[Stage2MarketExpectationRevision, ...]
    valuations: tuple[Stage2ValuationSnapshotRevision, ...]
    claims: tuple[ClaimRevision, ...]
    evidence: tuple[tuple[ClaimRevision, ClaimEvidenceLink, EvidenceItem], ...]


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


def _frozen_boundary(session: Session, research: Stage2CompanyResearch, *, company_research_revision_id: UUID, hypothesis_revision_ids: tuple[UUID, ...], expectation_revision_ids: tuple[UUID, ...] = (), valuation_revision_ids: tuple[UUID, ...] = (), claim_revision_ids: tuple[UUID, ...], cutoff: date, recorded: datetime, **_data: Any) -> _Boundary:
    research_revision = session.get(Stage2CompanyResearchRevision, company_research_revision_id)
    if research_revision is None or research_revision.company_research_id != research.id:
        raise EvidenceLedgerValidationError("company_research_revision_id must belong to this company research file.")
    _visible_upstream(research_revision, cutoff, recorded, "company-research revision")

    hypotheses = _load_unique(session, Stage2FinancialHypothesisRevision, hypothesis_revision_ids, "hypothesis_revision_ids", required=True)
    frozen_hypotheses = set(session.scalars(select(Stage2ResearchHypothesisLink.hypothesis_revision_id).where(Stage2ResearchHypothesisLink.company_research_revision_id == research_revision.id)))
    for item in hypotheses:
        identity = session.get(Stage2FinancialHypothesis, item.hypothesis_id)
        if identity is None or identity.company_research_id != research.id or item.id not in frozen_hypotheses:
            raise EvidenceLedgerValidationError("hypothesis revisions must be frozen by the exact company-research revision.")
        if item.hypothesis_status not in {"supported", "disputed"}:
            raise EvidenceLedgerValidationError("assessment hypotheses must be accepted supported or disputed revisions.")
        _visible_upstream(item, cutoff, recorded, "hypothesis revision")

    expectations = _load_unique(session, Stage2MarketExpectationRevision, expectation_revision_ids, "expectation_revision_ids")
    valuations = _load_unique(session, Stage2ValuationSnapshotRevision, valuation_revision_ids, "valuation_revision_ids")
    if not expectations and not valuations:
        raise EvidenceLedgerValidationError("at least one exact v0.6B expectation or valuation revision is required.")
    for item in expectations:
        identity = session.get(Stage2MarketExpectation, item.expectation_id)
        if identity is None or identity.company_research_id != research.id:
            raise EvidenceLedgerValidationError("expectation revisions must belong to the same company research file.")
        if item.company_research_revision_id != research_revision.id or item.status not in {"supported", "disputed"}:
            raise EvidenceLedgerValidationError("expectation revisions must be accepted by the exact company-research boundary.")
        _visible_upstream(item, cutoff, recorded, "expectation revision")
    for item in valuations:
        identity = session.get(Stage2ValuationSnapshot, item.valuation_id)
        if identity is None or identity.company_research_id != research.id:
            raise EvidenceLedgerValidationError("valuation revisions must belong to the same company research file.")
        if item.company_research_revision_id != research_revision.id or item.status not in {"supported", "disputed"}:
            raise EvidenceLedgerValidationError("valuation revisions must be accepted by the exact company-research boundary.")
        _visible_upstream(item, cutoff, recorded, "valuation revision")

    claims = _load_unique(session, ClaimRevision, claim_revision_ids, "claim_revision_ids", required=True)
    upstream_claim_links = list(session.scalars(select(Stage2ExpectationClaimLink).where(Stage2ExpectationClaimLink.expectation_revision_id.in_([item.id for item in expectations])))) if expectations else []
    if valuations:
        upstream_claim_links.extend(session.scalars(select(Stage2ValuationClaimLink).where(Stage2ValuationClaimLink.valuation_revision_id.in_([item.id for item in valuations]))))
    for link in upstream_claim_links:
        validate_utc_chronology(recorded, ("v0.6B claim boundary timestamp", _stored_utc(link.recorded_at_utc)))
    upstream_claim_ids = {link.claim_revision_id for link in upstream_claim_links}
    evidence_boundaries = []
    if expectations:
        evidence_boundaries.extend(session.scalars(select(Stage2ExpectationEvidenceLink).where(Stage2ExpectationEvidenceLink.expectation_revision_id.in_([item.id for item in expectations]))))
    if valuations:
        evidence_boundaries.extend(session.scalars(select(Stage2ValuationEvidenceLink).where(Stage2ValuationEvidenceLink.valuation_revision_id.in_([item.id for item in valuations]))))
    for boundary in evidence_boundaries:
        validate_utc_chronology(recorded, ("v0.6B evidence boundary timestamp", _stored_utc(boundary.recorded_at_utc)))
    evidence: list[tuple[ClaimRevision, ClaimEvidenceLink, EvidenceItem]] = []
    for claim in claims:
        identity = session.get(Claim, claim.claim_id)
        if identity is None or identity.case_id != research.case_id or claim.id not in upstream_claim_ids:
            raise EvidenceLedgerValidationError("claim revisions must belong to the research case and exact frozen v0.6B boundary.")
        _visible_upstream(claim, cutoff, recorded, "claim revision")
        for boundary in evidence_boundaries:
            if boundary.claim_revision_id != claim.id:
                continue
            link = session.get(ClaimEvidenceLink, boundary.claim_evidence_link_id)
            item = session.get(EvidenceItem, boundary.evidence_id)
            if link is None or item is None or link.claim_revision_id != claim.id or link.evidence_id != item.id:
                raise EvidenceLedgerValidationError("frozen evidence link is inconsistent.")
            if item.information_date <= cutoff and _stored_utc(link.recorded_at_utc) <= recorded and _stored_utc(item.recorded_at_utc) <= recorded:
                evidence.append((claim, link, item))
    hypothesis_ids = {item.id for item in hypotheses}
    upstream_hypothesis_ids = set()
    upstream_hypothesis_links = []
    if expectations:
        upstream_hypothesis_links.extend(session.scalars(select(Stage2ExpectationHypothesisLink).where(Stage2ExpectationHypothesisLink.expectation_revision_id.in_([item.id for item in expectations]))))
    if valuations:
        upstream_hypothesis_links.extend(session.scalars(select(Stage2ValuationHypothesisLink).where(Stage2ValuationHypothesisLink.valuation_revision_id.in_([item.id for item in valuations]))))
    for link in upstream_hypothesis_links:
        validate_utc_chronology(recorded, ("v0.6B hypothesis boundary timestamp", _stored_utc(link.recorded_at_utc)))
    upstream_hypothesis_ids.update(link.hypothesis_revision_id for link in upstream_hypothesis_links)
    if hypothesis_ids != upstream_hypothesis_ids:
        raise EvidenceLedgerValidationError("assessment hypotheses must exactly match the selected v0.6B frozen boundary.")
    unique_evidence = {row[1].id: row for row in evidence}
    return _Boundary(
        research_revision,
        tuple(hypotheses),
        tuple(expectations),
        tuple(valuations),
        tuple(claims),
        tuple(unique_evidence[key] for key in sorted(unique_evidence, key=str)),
    )


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


def _load_unique(session: Session, model: type[Any], ids: tuple[UUID, ...], field: str, *, required: bool = False) -> list[Any]:
    if not isinstance(ids, tuple) or len(ids) != len(set(ids)) or (required and not ids):
        suffix = "non-empty and unique" if required else "unique"
        raise EvidenceLedgerValidationError(f"{field} must be a tuple of {suffix} identifiers.")
    if not ids:
        return []
    rows = list(session.scalars(select(model).where(model.id.in_(ids)).order_by(model.id).with_for_update()))
    if len(rows) != len(ids):
        raise EvidenceLedgerNotFound(f"one or more {field} were not found.")
    return rows


def _visible_upstream(row: Any, cutoff: date, recorded: datetime, label: str) -> None:
    if row.information_cutoff_date > cutoff:
        raise EvidenceLedgerValidationError(f"{label} cutoff exceeds assessment cutoff.")
    validate_utc_chronology(recorded, (f"{label} timestamp", _stored_utc(row.recorded_at_utc)))


def _time_boundary(data: dict[str, Any]) -> tuple[datetime, date]:
    cutoff = data.get("information_cutoff_date")
    if not isinstance(cutoff, date) or isinstance(cutoff, datetime):
        raise EvidenceLedgerValidationError("information_cutoff_date must be a date.")
    recorded = utc_timestamp(data.get("recorded_at_utc"))
    validate_recorded_cutoff(cutoff, recorded)
    return recorded, cutoff


def _locked_research(session: Session, identity: UUID) -> Stage2CompanyResearch:
    row = session.scalar(select(Stage2CompanyResearch).where(Stage2CompanyResearch.id == identity).with_for_update())
    if row is None:
        raise EvidenceLedgerNotFound(f"Stage 2 company research {identity} was not found.")
    return row


def _locked_identity(session: Session, model: type[Any], identity: UUID, label: str) -> Any:
    row = session.scalar(select(model).where(model.id == identity).with_for_update())
    if row is None:
        raise EvidenceLedgerNotFound(f"Stage 2 {label} assessment {identity} was not found.")
    return row


def _latest(session: Session, model: type[Any], field: str, identity: UUID) -> Any | None:
    return session.scalar(select(model).where(getattr(model, field) == identity).order_by(model.revision_no.desc()).limit(1))


def _required_text(value: str, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise EvidenceLedgerValidationError(f"{field} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise EvidenceLedgerValidationError(f"{field} must not be blank.")
    if len(normalized) > maximum:
        raise EvidenceLedgerValidationError(f"{field} must not exceed {maximum} characters.")
    return normalized


def _stored_utc(value: datetime | None) -> datetime:
    if value is None:
        raise EvidenceLedgerValidationError("required UTC timestamp is missing.")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
