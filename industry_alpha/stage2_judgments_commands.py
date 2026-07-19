"""Transactional commands for v0.6D evidence-backed quality judgments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerValidationError
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
from industry_alpha.stage2_integrity import translate_integrity as _integrity
from industry_alpha.stage2_models import Stage2CompanyResearch
from industry_alpha.stage2_revision_locks import revision_lock as _revision_lock
from industry_alpha.validation import INFERENCE_CONFIDENCES, reviewed_value, validate_utc_chronology


OUTCOMES = frozenset({"affirmed", "not_affirmed", "uncertain", "not_assessed"})
EVIDENCE_STATES = frozenset({"supported", "disputed", "insufficient_evidence"})


@dataclass(frozen=True)
class _JudgmentBoundary:
    base: _Boundary
    catalysts: tuple[Stage2CatalystAssessmentRevision, ...]
    risks: tuple[Stage2RiskAssessmentRevision, ...]


class Stage2JudgmentCommandService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_industry_judgment(self, company_research_id: UUID, *, judgment_key: str, **data: Any) -> Stage2IndustryJudgment:
        return self._create("industry", company_research_id, judgment_key, data)

    def append_industry_judgment_revision(self, judgment_id: UUID, **data: Any) -> Stage2IndustryJudgmentRevision:
        return self._append("industry", judgment_id, data)

    def create_company_judgment(self, company_research_id: UUID, *, judgment_key: str, **data: Any) -> Stage2CompanyJudgment:
        return self._create("company", company_research_id, judgment_key, data)

    def append_company_judgment_revision(self, judgment_id: UUID, **data: Any) -> Stage2CompanyJudgmentRevision:
        return self._append("company", judgment_id, data)

    def _create(self, kind: str, company_research_id: UUID, key: str, data: dict[str, Any]) -> Any:
        recorded, cutoff = _time_boundary(data)
        identity_model = Stage2IndustryJudgment if kind == "industry" else Stage2CompanyJudgment
        with _integrity(f"{kind} judgment key already exists"):
            with self._session_factory.begin() as session:
                research = _locked_research(session, company_research_id)
                identity = identity_model(
                    company_research_id=research.id,
                    judgment_key=_required_text(key, "judgment_key", 96),
                    created_at_utc=recorded,
                )
                session.add(identity)
                session.flush()
                self._insert(session, kind, research, identity, recorded, cutoff, data)
            return identity

    def _append(self, kind: str, judgment_id: UUID, data: dict[str, Any]) -> Any:
        recorded, cutoff = _time_boundary(data)
        identity_model = Stage2IndustryJudgment if kind == "industry" else Stage2CompanyJudgment
        with _revision_lock(kind, judgment_id), _integrity(f"{kind} judgment revision conflicts with history"):
            with self._session_factory.begin() as session:
                identity = session.scalar(select(identity_model).where(identity_model.id == judgment_id).with_for_update())
                if identity is None:
                    raise EvidenceLedgerNotFound(f"Stage 2 {kind} judgment {judgment_id} was not found.")
                research = _locked_research(session, identity.company_research_id)
                return self._insert(session, kind, research, identity, recorded, cutoff, data)

    def _insert(self, session: Session, kind: str, research: Stage2CompanyResearch, identity: Any, recorded: datetime, cutoff: date, data: dict[str, Any]) -> Any:
        boundary = _judgment_boundary(session, research, cutoff=cutoff, recorded=recorded, **data)
        outcome = reviewed_value(data.get("outcome"), "outcome", OUTCOMES)
        evidence_state = reviewed_value(data.get("evidence_state"), "evidence_state", EVIDENCE_STATES)
        confidence = reviewed_value(data.get("confidence"), "confidence", INFERENCE_CONFIDENCES)
        rationale = _required_text(data.get("rationale"), "rationale", 4000)
        uncertainty = _required_text(data.get("uncertainty"), "uncertainty", 2000)
        follow_up = _required_text(data.get("follow_up_verification"), "follow_up_verification", 3000)
        _validate_outcome(outcome, evidence_state, confidence, rationale, uncertainty, follow_up, boundary.base)
        revision_model = Stage2IndustryJudgmentRevision if kind == "industry" else Stage2CompanyJudgmentRevision
        prior = session.scalar(select(revision_model).where(revision_model.judgment_id == identity.id).order_by(revision_model.revision_no.desc()).limit(1))
        _validate_chronology(identity.created_at_utc, prior, boundary, recorded, kind)
        common = dict(
            judgment_id=identity.id,
            company_research_revision_id=boundary.base.research_revision.id,
            revision_no=1 if prior is None else prior.revision_no + 1,
            outcome=outcome,
            evidence_state=evidence_state,
            confidence=confidence,
            decision_criteria=_required_text(data.get("decision_criteria"), "decision_criteria", 2000),
            rationale=rationale,
            uncertainty=uncertainty,
            follow_up_verification=follow_up,
            information_cutoff_date=cutoff,
            recorded_at_utc=recorded,
            supersedes_revision_id=None if prior is None else prior.id,
        )
        if kind == "industry":
            revision = Stage2IndustryJudgmentRevision(
                **common,
                driver_durability=_required_text(data.get("driver_durability"), "driver_durability", 2000),
                value_pool_direction=_required_text(data.get("value_pool_direction"), "value_pool_direction", 2000),
                chain_bottleneck_support=_required_text(data.get("chain_bottleneck_support"), "chain_bottleneck_support", 2000),
            )
        else:
            revision = Stage2CompanyJudgmentRevision(
                **common,
                beneficiary_credibility=_required_text(data.get("beneficiary_credibility"), "beneficiary_credibility", 2000),
                financial_transmission_credibility=_required_text(data.get("financial_transmission_credibility"), "financial_transmission_credibility", 2000),
                execution_risks=_required_text(data.get("execution_risks"), "execution_risks", 2000),
            )
        session.add(revision)
        session.flush()
        _insert_links(session, kind, revision.id, boundary, recorded)
        session.flush()
        return revision

def _judgment_boundary(session: Session, research: Stage2CompanyResearch, *, catalyst_revision_ids: tuple[UUID, ...] = (), risk_revision_ids: tuple[UUID, ...] = (), cutoff: date, recorded: datetime, **data: Any) -> _JudgmentBoundary:
    base = _frozen_boundary(session, research, cutoff=cutoff, recorded=recorded, **data)
    catalysts = tuple(_load_unique(session, Stage2CatalystAssessmentRevision, catalyst_revision_ids, "catalyst_revision_ids"))
    risks = tuple(_load_unique(session, Stage2RiskAssessmentRevision, risk_revision_ids, "risk_revision_ids"))
    if not catalysts and not risks:
        raise EvidenceLedgerValidationError("at least one exact v0.6C catalyst or risk revision is required.")
    _validate_v06c(session, research, base, catalysts, risks, cutoff, recorded)
    return _JudgmentBoundary(base, catalysts, risks)


def _validate_v06c(session: Session, research: Stage2CompanyResearch, base: _Boundary, catalysts: tuple[Any, ...], risks: tuple[Any, ...], cutoff: date, recorded: datetime) -> None:
    expected = (
        {item.id for item in base.hypotheses}, {item.id for item in base.expectations},
        {item.id for item in base.valuations}, {item.id for item in base.claims},
        {link.id for _claim, link, _item in base.evidence},
    )
    for kind, revisions in (("catalyst", catalysts), ("risk", risks)):
        identity_model = Stage2CatalystAssessment if kind == "catalyst" else Stage2RiskAssessment
        models = _assessment_link_models(kind)
        field = f"{kind}_revision_id"
        for revision in revisions:
            identity = session.get(identity_model, getattr(revision, f"{kind}_id"))
            if identity is None or identity.company_research_id != research.id or revision.company_research_revision_id != base.research_revision.id:
                raise EvidenceLedgerValidationError("v0.6C revisions must belong to the exact company-research boundary.")
            if revision.status not in {"supported", "disputed"}:
                raise EvidenceLedgerValidationError("v0.6C revisions must be accepted supported or disputed revisions.")
            _visible_upstream(revision, cutoff, recorded, f"{kind} revision")
            selected = tuple(set() for _ in range(5))
            for model, target in zip(models[:4], selected[:4], strict=True):
                rows = tuple(session.scalars(select(model).where(getattr(model, field) == revision.id)))
                for row in rows:
                    validate_utc_chronology(recorded, (f"v0.6C {kind} link timestamp", _stored_utc(row.recorded_at_utc)))
                    upstream = next(name for name in ("hypothesis", "expectation", "valuation", "claim") if hasattr(row, f"{name}_revision_id"))
                    target.add(getattr(row, f"{upstream}_revision_id"))
            evidence_rows = tuple(session.scalars(select(models[4]).where(getattr(models[4], field) == revision.id)))
            for row in evidence_rows:
                validate_utc_chronology(recorded, (f"v0.6C {kind} evidence timestamp", _stored_utc(row.recorded_at_utc)))
                selected[4].add(row.claim_evidence_link_id)
            if selected != expected:
                raise EvidenceLedgerValidationError("each v0.6C revision must exactly match the frozen v0.6A/v0.6B claim and evidence boundary.")


def _assessment_link_models(kind: str) -> tuple[type[Any], ...]:
    if kind == "catalyst":
        return (Stage2CatalystHypothesisLink, Stage2CatalystExpectationLink, Stage2CatalystValuationLink, Stage2CatalystClaimLink, Stage2CatalystEvidenceLink)
    return (Stage2RiskHypothesisLink, Stage2RiskExpectationLink, Stage2RiskValuationLink, Stage2RiskClaimLink, Stage2RiskEvidenceLink)


def _validate_outcome(outcome: str, evidence_state: str, confidence: str, rationale: str, uncertainty: str, follow_up: str, boundary: _Boundary) -> None:
    supported_abc = any(claim.claim_status == "supported" and link.relation == "supports" and item.evidence_grade in {"A", "B", "C"} for claim, link, item in boundary.evidence)
    conflict = any(link.relation == "contradicts" for _claim, link, _item in boundary.evidence)
    disputed_claim = any(claim.claim_status == "disputed" for claim in boundary.claims)
    if evidence_state == "supported" and (not supported_abc or conflict):
        raise EvidenceLedgerValidationError("supported evidence requires a visible supported A/B/C claim and no contradiction.")
    if evidence_state == "disputed" and not (conflict or disputed_claim):
        raise EvidenceLedgerValidationError("disputed evidence requires a disputed claim or visible contradiction.")
    if evidence_state == "insufficient_evidence" and supported_abc:
        raise EvidenceLedgerValidationError("insufficient evidence cannot hide a visible supported A/B/C boundary.")
    if outcome == "affirmed" and evidence_state != "supported":
        raise EvidenceLedgerValidationError("affirmed judgments require supported evidence.")
    if outcome == "uncertain" and evidence_state not in {"disputed", "insufficient_evidence"}:
        raise EvidenceLedgerValidationError("uncertain judgments require disputed or insufficient evidence.")
    if outcome == "not_assessed":
        if evidence_state != "insufficient_evidence" or "尚未获得可靠公开证据" not in f"{rationale} {uncertainty} {follow_up}":
            raise EvidenceLedgerValidationError("not_assessed judgments require insufficient evidence and explicit missing-evidence wording.")
    if evidence_state != "supported" and confidence != "low":
        raise EvidenceLedgerValidationError("disputed or insufficient evidence cannot use medium or high confidence.")


def _validate_chronology(created: datetime, prior: Any | None, boundary: _JudgmentBoundary, recorded: datetime, kind: str) -> None:
    rows = [(f"{kind} judgment identity timestamp", _stored_utc(created)), ("company-research revision timestamp", _stored_utc(boundary.base.research_revision.recorded_at_utc))]
    for label, values in (("hypothesis", boundary.base.hypotheses), ("expectation", boundary.base.expectations), ("valuation", boundary.base.valuations), ("claim", boundary.base.claims), ("catalyst", boundary.catalysts), ("risk", boundary.risks)):
        rows.extend((f"{label} revision timestamp", _stored_utc(item.recorded_at_utc)) for item in values)
    rows.extend(("evidence/link timestamp", max(_stored_utc(link.recorded_at_utc), _stored_utc(item.recorded_at_utc))) for _claim, link, item in boundary.base.evidence)
    if prior is not None:
        rows.append(("previous judgment revision timestamp", _stored_utc(prior.recorded_at_utc)))
    validate_utc_chronology(recorded, *rows)


def _insert_links(session: Session, kind: str, revision_id: UUID, boundary: _JudgmentBoundary, recorded: datetime) -> None:
    prefix = "Industry" if kind == "industry" else "Company"
    models = {
        "hypothesis": globals()[f"Stage2{prefix}JudgmentHypothesisLink"],
        "expectation": globals()[f"Stage2{prefix}JudgmentExpectationLink"],
        "valuation": globals()[f"Stage2{prefix}JudgmentValuationLink"],
        "catalyst": globals()[f"Stage2{prefix}JudgmentCatalystLink"],
        "risk": globals()[f"Stage2{prefix}JudgmentRiskLink"],
        "claim": globals()[f"Stage2{prefix}JudgmentClaimLink"],
        "evidence": globals()[f"Stage2{prefix}JudgmentEvidenceLink"],
    }
    common = {"judgment_revision_id": revision_id, "recorded_at_utc": recorded}
    for name, rows in (("hypothesis", boundary.base.hypotheses), ("expectation", boundary.base.expectations), ("valuation", boundary.base.valuations), ("catalyst", boundary.catalysts), ("risk", boundary.risks), ("claim", boundary.base.claims)):
        session.add_all(models[name](**common, **{f"{name}_revision_id": item.id}) for item in rows)
    session.add_all(models["evidence"](**common, claim_revision_id=claim.id, claim_evidence_link_id=link.id, evidence_id=item.id) for claim, link, item in boundary.base.evidence)
