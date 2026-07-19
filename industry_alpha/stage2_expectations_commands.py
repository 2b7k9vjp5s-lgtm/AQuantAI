"""Transactional v0.6B expectation and valuation snapshot commands."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from threading import Lock, RLock
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.models import DailyPriceRecord, IngestionRun
from industry_alpha.errors import (
    EvidenceLedgerNotFound,
    EvidenceLedgerValidationError,
)
from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
    Stage2FinancialHypothesis,
    Stage2FinancialHypothesisRevision,
    Stage2HypothesisClaimLink,
    Stage2ResearchHypothesisLink,
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
from industry_alpha.stage2_integrity import translate_integrity as _translate_integrity
from industry_alpha.validation import (
    INFERENCE_CONFIDENCES,
    reviewed_value,
    utc_timestamp,
    validate_recorded_cutoff,
    validate_utc_chronology,
)

EXPECTATION_KINDS = frozenset(
    {"consensus", "guidance", "market_implied", "research_assumption", "unknown"}
)
DIRECTIONS = frozenset({"positive", "negative", "mixed", "uncertain"})
SNAPSHOT_STATUSES = frozenset({"draft", "supported", "disputed", "rejected"})
VALUATION_METHODS = frozenset(
    {
        "multiple_observation",
        "asset_reference",
        "historical_range",
        "market_price_context",
        "missing_data",
    }
)
_LOCKS_GUARD = Lock()
_LOCKS: dict[tuple[str, UUID], RLock] = {}


def _revision_lock(kind: str, identity: UUID) -> RLock:
    key = (kind, identity)
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, RLock())


class Stage2ExpectationCommandService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_expectation(
        self,
        company_research_id: UUID,
        *,
        expectation_key: str,
        company_research_revision_id: UUID,
        hypothesis_revision_ids: tuple[UUID, ...],
        claim_revision_ids: tuple[UUID, ...],
        subject: str,
        period_horizon: str,
        expectation_kind: str,
        direction: str,
        status: str,
        confidence: str,
        basis: str,
        information_cutoff_date: date,
        recorded_at_utc: datetime | None = None,
    ) -> Stage2MarketExpectation:
        recorded = utc_timestamp(recorded_at_utc)
        cutoff = _required_date(information_cutoff_date, "information_cutoff_date")
        validate_recorded_cutoff(cutoff, recorded)
        key = _required_text(expectation_key, "expectation_key", 96)
        with _translate_integrity("expectation key already exists"):
            with self._session_factory.begin() as session:
                research = _locked_research(session, company_research_id)
                identity = Stage2MarketExpectation(
                    company_research_id=research.id,
                    expectation_key=key,
                    created_at_utc=recorded,
                )
                session.add(identity)
                session.flush()
                self._insert_expectation_revision(
                    session,
                    research,
                    identity,
                    company_research_revision_id=company_research_revision_id,
                    hypothesis_revision_ids=hypothesis_revision_ids,
                    claim_revision_ids=claim_revision_ids,
                    subject=subject,
                    period_horizon=period_horizon,
                    expectation_kind=expectation_kind,
                    direction=direction,
                    status=status,
                    confidence=confidence,
                    basis=basis,
                    information_cutoff_date=cutoff,
                    recorded_at_utc=recorded,
                )
            return identity

    def append_expectation_revision(
        self,
        expectation_id: UUID,
        *,
        company_research_revision_id: UUID,
        hypothesis_revision_ids: tuple[UUID, ...],
        claim_revision_ids: tuple[UUID, ...],
        subject: str,
        period_horizon: str,
        expectation_kind: str,
        direction: str,
        status: str,
        confidence: str,
        basis: str,
        information_cutoff_date: date,
        recorded_at_utc: datetime | None = None,
    ) -> Stage2MarketExpectationRevision:
        recorded = utc_timestamp(recorded_at_utc)
        cutoff = _required_date(information_cutoff_date, "information_cutoff_date")
        validate_recorded_cutoff(cutoff, recorded)
        with _revision_lock("expectation", expectation_id):
            with _translate_integrity("expectation revision conflicts with history"):
                with self._session_factory.begin() as session:
                    identity = _locked_expectation(session, expectation_id)
                    research = _locked_research(session, identity.company_research_id)
                    return self._insert_expectation_revision(
                        session,
                        research,
                        identity,
                        company_research_revision_id=company_research_revision_id,
                        hypothesis_revision_ids=hypothesis_revision_ids,
                        claim_revision_ids=claim_revision_ids,
                        subject=subject,
                        period_horizon=period_horizon,
                        expectation_kind=expectation_kind,
                        direction=direction,
                        status=status,
                        confidence=confidence,
                        basis=basis,
                        information_cutoff_date=cutoff,
                        recorded_at_utc=recorded,
                    )

    def create_valuation_snapshot(
        self,
        company_research_id: UUID,
        *,
        valuation_key: str,
        company_research_revision_id: UUID,
        hypothesis_revision_ids: tuple[UUID, ...],
        claim_revision_ids: tuple[UUID, ...],
        valuation_method: str,
        metric_context: str,
        observed_value: str | Decimal | None,
        missing_data_reason: str | None,
        unit: str | None,
        currency: str | None,
        comparison_basis: str,
        assumptions: str,
        status: str,
        confidence: str,
        information_cutoff_date: date,
        daily_price_id: int | None = None,
        recorded_at_utc: datetime | None = None,
    ) -> Stage2ValuationSnapshot:
        recorded = utc_timestamp(recorded_at_utc)
        cutoff = _required_date(information_cutoff_date, "information_cutoff_date")
        validate_recorded_cutoff(cutoff, recorded)
        key = _required_text(valuation_key, "valuation_key", 96)
        method = reviewed_value(valuation_method, "valuation_method", VALUATION_METHODS)
        observed, missing = _valuation_value_state(
            method, observed_value, missing_data_reason
        )
        with _translate_integrity("valuation key already exists"):
            with self._session_factory.begin() as session:
                research = _locked_research(session, company_research_id)
                identity = Stage2ValuationSnapshot(
                    company_research_id=research.id,
                    valuation_key=key,
                    created_at_utc=recorded,
                )
                session.add(identity)
                session.flush()
                self._insert_valuation_revision(
                    session,
                    research,
                    identity,
                    company_research_revision_id=company_research_revision_id,
                    hypothesis_revision_ids=hypothesis_revision_ids,
                    claim_revision_ids=claim_revision_ids,
                    valuation_method=method,
                    metric_context=metric_context,
                    observed_value=observed,
                    missing_data_reason=missing,
                    unit=unit,
                    currency=currency,
                    comparison_basis=comparison_basis,
                    assumptions=assumptions,
                    status=status,
                    confidence=confidence,
                    information_cutoff_date=cutoff,
                    daily_price_id=daily_price_id,
                    recorded_at_utc=recorded,
                )
            return identity

    def append_valuation_revision(
        self,
        valuation_id: UUID,
        *,
        company_research_revision_id: UUID,
        hypothesis_revision_ids: tuple[UUID, ...],
        claim_revision_ids: tuple[UUID, ...],
        valuation_method: str,
        metric_context: str,
        observed_value: str | Decimal | None,
        missing_data_reason: str | None,
        unit: str | None,
        currency: str | None,
        comparison_basis: str,
        assumptions: str,
        status: str,
        confidence: str,
        information_cutoff_date: date,
        daily_price_id: int | None = None,
        recorded_at_utc: datetime | None = None,
    ) -> Stage2ValuationSnapshotRevision:
        recorded = utc_timestamp(recorded_at_utc)
        cutoff = _required_date(information_cutoff_date, "information_cutoff_date")
        validate_recorded_cutoff(cutoff, recorded)
        method = reviewed_value(valuation_method, "valuation_method", VALUATION_METHODS)
        observed, missing = _valuation_value_state(
            method, observed_value, missing_data_reason
        )
        with _revision_lock("valuation", valuation_id):
            with _translate_integrity("valuation revision conflicts with history"):
                with self._session_factory.begin() as session:
                    identity = _locked_valuation(session, valuation_id)
                    research = _locked_research(session, identity.company_research_id)
                    return self._insert_valuation_revision(
                        session,
                        research,
                        identity,
                        company_research_revision_id=company_research_revision_id,
                        hypothesis_revision_ids=hypothesis_revision_ids,
                        claim_revision_ids=claim_revision_ids,
                        valuation_method=method,
                        metric_context=metric_context,
                        observed_value=observed,
                        missing_data_reason=missing,
                        unit=unit,
                        currency=currency,
                        comparison_basis=comparison_basis,
                        assumptions=assumptions,
                        status=status,
                        confidence=confidence,
                        information_cutoff_date=cutoff,
                        daily_price_id=daily_price_id,
                        recorded_at_utc=recorded,
                    )

    def _insert_expectation_revision(self, session: Session, research: Stage2CompanyResearch, identity: Stage2MarketExpectation, **data) -> Stage2MarketExpectationRevision:
        boundary, hypotheses = _boundary(session, research, data["company_research_revision_id"], data["hypothesis_revision_ids"], data["information_cutoff_date"], data["recorded_at_utc"])
        claims, evidence = _claims_and_evidence(session, research.case_id, data["claim_revision_ids"], data["information_cutoff_date"], data["recorded_at_utc"])
        _require_claims_frozen_by_hypotheses(session, hypotheses, claims)
        status = reviewed_value(data["status"], "status", SNAPSHOT_STATUSES)
        _validate_status(status, claims, evidence)
        prior = _latest(session, Stage2MarketExpectationRevision, "expectation_id", identity.id)
        chronology = [("expectation identity timestamp", _stored_utc(identity.created_at_utc)), ("company-research revision timestamp", _stored_utc(boundary.recorded_at_utc))]
        chronology.extend(("hypothesis revision timestamp", _stored_utc(item.recorded_at_utc)) for item in hypotheses)
        chronology.extend(("claim revision timestamp", _stored_utc(item.recorded_at_utc)) for item in claims)
        chronology.extend(("evidence/link timestamp", max(_stored_utc(link.recorded_at_utc), _stored_utc(item.recorded_at_utc))) for _claim, link, item in evidence)
        if prior is not None:
            chronology.append(("previous expectation revision timestamp", _stored_utc(prior.recorded_at_utc)))
        validate_utc_chronology(data["recorded_at_utc"], *chronology)
        revision = Stage2MarketExpectationRevision(
            expectation_id=identity.id,
            company_research_revision_id=boundary.id,
            revision_no=1 if prior is None else prior.revision_no + 1,
            subject=_required_text(data["subject"], "subject", 500),
            period_horizon=_required_text(data["period_horizon"], "period_horizon", 300),
            expectation_kind=reviewed_value(data["expectation_kind"], "expectation_kind", EXPECTATION_KINDS),
            direction=reviewed_value(data["direction"], "direction", DIRECTIONS),
            status=status,
            confidence=reviewed_value(data["confidence"], "confidence", INFERENCE_CONFIDENCES),
            basis=_required_text(data["basis"], "basis", 4000),
            information_cutoff_date=data["information_cutoff_date"],
            recorded_at_utc=data["recorded_at_utc"],
            supersedes_revision_id=None if prior is None else prior.id,
        )
        session.add(revision)
        session.flush()
        for item in hypotheses:
            session.add(Stage2ExpectationHypothesisLink(expectation_revision_id=revision.id, hypothesis_revision_id=item.id, recorded_at_utc=data["recorded_at_utc"]))
        for claim in claims:
            session.add(Stage2ExpectationClaimLink(expectation_revision_id=revision.id, claim_revision_id=claim.id, recorded_at_utc=data["recorded_at_utc"]))
        for claim, link, item in evidence:
            session.add(Stage2ExpectationEvidenceLink(expectation_revision_id=revision.id, claim_revision_id=claim.id, claim_evidence_link_id=link.id, evidence_id=item.id, recorded_at_utc=data["recorded_at_utc"]))
        session.flush()
        return revision

    def _insert_valuation_revision(self, session: Session, research: Stage2CompanyResearch, identity: Stage2ValuationSnapshot, **data) -> Stage2ValuationSnapshotRevision:
        boundary, hypotheses = _boundary(session, research, data["company_research_revision_id"], data["hypothesis_revision_ids"], data["information_cutoff_date"], data["recorded_at_utc"])
        claims, evidence = _claims_and_evidence(session, research.case_id, data["claim_revision_ids"], data["information_cutoff_date"], data["recorded_at_utc"])
        _require_claims_frozen_by_hypotheses(session, hypotheses, claims)
        status = reviewed_value(data["status"], "status", SNAPSHOT_STATUSES)
        _validate_status(status, claims, evidence)
        price = _price(session, research, data["daily_price_id"], data["information_cutoff_date"], data["recorded_at_utc"])
        prior = _latest(session, Stage2ValuationSnapshotRevision, "valuation_id", identity.id)
        chronology = [("valuation identity timestamp", _stored_utc(identity.created_at_utc)), ("company-research revision timestamp", _stored_utc(boundary.recorded_at_utc))]
        chronology.extend(("hypothesis revision timestamp", _stored_utc(item.recorded_at_utc)) for item in hypotheses)
        chronology.extend(("claim revision timestamp", _stored_utc(item.recorded_at_utc)) for item in claims)
        chronology.extend(("evidence/link timestamp", max(_stored_utc(link.recorded_at_utc), _stored_utc(item.recorded_at_utc))) for _claim, link, item in evidence)
        if price is not None:
            _row, run = price
            chronology.extend((("price import timestamp", _stored_utc(run.imported_at)), ("price completion timestamp", _stored_utc(run.completed_at))))
        if prior is not None:
            chronology.append(("previous valuation revision timestamp", _stored_utc(prior.recorded_at_utc)))
        validate_utc_chronology(data["recorded_at_utc"], *chronology)
        method, observed, missing = _validated_valuation_values(
            data["valuation_method"],
            data["observed_value"],
            data["missing_data_reason"],
        )
        revision = Stage2ValuationSnapshotRevision(
            valuation_id=identity.id,
            company_research_revision_id=boundary.id,
            revision_no=1 if prior is None else prior.revision_no + 1,
            valuation_method=method,
            metric_context=_required_text(data["metric_context"], "metric_context", 1000),
            observed_value=observed,
            missing_data_reason=missing,
            unit=_optional_text(data["unit"], "unit", 64),
            currency=_optional_text(data["currency"], "currency", 16),
            comparison_basis=_required_text(data["comparison_basis"], "comparison_basis", 1000),
            assumptions=_required_text(data["assumptions"], "assumptions", 4000),
            status=status,
            confidence=reviewed_value(data["confidence"], "confidence", INFERENCE_CONFIDENCES),
            information_cutoff_date=data["information_cutoff_date"],
            recorded_at_utc=data["recorded_at_utc"],
            daily_price_id=None if price is None else price[0].id,
            supersedes_revision_id=None if prior is None else prior.id,
        )
        session.add(revision)
        session.flush()
        for item in hypotheses:
            session.add(Stage2ValuationHypothesisLink(valuation_revision_id=revision.id, hypothesis_revision_id=item.id, recorded_at_utc=data["recorded_at_utc"]))
        for claim in claims:
            session.add(Stage2ValuationClaimLink(valuation_revision_id=revision.id, claim_revision_id=claim.id, recorded_at_utc=data["recorded_at_utc"]))
        for claim, link, item in evidence:
            session.add(Stage2ValuationEvidenceLink(valuation_revision_id=revision.id, claim_revision_id=claim.id, claim_evidence_link_id=link.id, evidence_id=item.id, recorded_at_utc=data["recorded_at_utc"]))
        session.flush()
        return revision

def _boundary(session: Session, research: Stage2CompanyResearch, revision_id: UUID, hypothesis_ids: tuple[UUID, ...], cutoff: date, recorded: datetime) -> tuple[Stage2CompanyResearchRevision, list[Stage2FinancialHypothesisRevision]]:
    boundary = session.get(Stage2CompanyResearchRevision, revision_id)
    if boundary is None or boundary.company_research_id != research.id:
        raise EvidenceLedgerValidationError("company_research_revision_id must belong to this company research file.")
    if boundary.information_cutoff_date > cutoff:
        raise EvidenceLedgerValidationError("company-research revision cutoff exceeds snapshot cutoff.")
    validate_utc_chronology(recorded, ("company research identity timestamp", _stored_utc(research.created_at_utc)), ("company research revision timestamp", _stored_utc(boundary.recorded_at_utc)))
    if len(hypothesis_ids) != len(set(hypothesis_ids)) or not hypothesis_ids:
        raise EvidenceLedgerValidationError("hypothesis_revision_ids must be non-empty and unique.")
    frozen = set(session.scalars(select(Stage2ResearchHypothesisLink.hypothesis_revision_id).where(Stage2ResearchHypothesisLink.company_research_revision_id == boundary.id)))
    rows = list(session.scalars(select(Stage2FinancialHypothesisRevision).where(Stage2FinancialHypothesisRevision.id.in_(hypothesis_ids)).order_by(Stage2FinancialHypothesisRevision.id).with_for_update()))
    if len(rows) != len(hypothesis_ids):
        raise EvidenceLedgerNotFound("one or more hypothesis revisions were not found.")
    for row in rows:
        identity = session.get(Stage2FinancialHypothesis, row.hypothesis_id)
        if identity is None or identity.company_research_id != research.id or row.id not in frozen:
            raise EvidenceLedgerValidationError("hypothesis revisions must be frozen by the exact company-research revision.")
        if row.hypothesis_status not in {"supported", "disputed"}:
            raise EvidenceLedgerValidationError("snapshot hypotheses must be accepted supported or disputed revisions.")
        if row.information_cutoff_date > cutoff:
            raise EvidenceLedgerValidationError("hypothesis cutoff exceeds snapshot cutoff.")
    return boundary, rows


def _claims_and_evidence(session: Session, case_id: UUID, ids: tuple[UUID, ...], cutoff: date, recorded: datetime) -> tuple[list[ClaimRevision], list[tuple[ClaimRevision, ClaimEvidenceLink, EvidenceItem]]]:
    if len(ids) != len(set(ids)) or not ids:
        raise EvidenceLedgerValidationError("claim_revision_ids must be non-empty and unique.")
    claims = list(session.scalars(select(ClaimRevision).where(ClaimRevision.id.in_(ids)).order_by(ClaimRevision.id).with_for_update()))
    if len(claims) != len(ids):
        raise EvidenceLedgerNotFound("one or more claim revisions were not found.")
    evidence_rows: list[tuple[ClaimRevision, ClaimEvidenceLink, EvidenceItem]] = []
    for claim in claims:
        identity = session.get(Claim, claim.claim_id)
        if identity is None or identity.case_id != case_id:
            raise EvidenceLedgerValidationError("claim revisions must belong to the same research case.")
        if claim.information_cutoff_date > cutoff:
            raise EvidenceLedgerValidationError("claim revision cutoff exceeds snapshot cutoff.")
        validate_utc_chronology(recorded, ("claim revision timestamp", _stored_utc(claim.recorded_at_utc)))
        for link in session.scalars(select(ClaimEvidenceLink).where(ClaimEvidenceLink.claim_revision_id == claim.id)):
            item = session.get(EvidenceItem, link.evidence_id)
            if item is not None and item.information_date <= cutoff and item.information_date <= claim.information_cutoff_date and _stored_utc(link.recorded_at_utc) <= recorded and _stored_utc(item.recorded_at_utc) <= recorded:
                evidence_rows.append((claim, link, item))
    return claims, evidence_rows


def _validate_status(status: str, claims: list[ClaimRevision], evidence: list[tuple[ClaimRevision, ClaimEvidenceLink, EvidenceItem]]) -> None:
    has_supported_abc = any(claim.claim_status == "supported" and link.relation == "supports" and item.evidence_grade in {"A", "B", "C"} for claim, link, item in evidence)
    has_conflict = any(link.relation == "contradicts" for _claim, link, _item in evidence)
    if status == "supported" and (not has_supported_abc or has_conflict):
        raise EvidenceLedgerValidationError("supported snapshots require visible supported A/B/C-backed claims and no contradiction.")
    if status == "disputed" and not (has_conflict or any(claim.claim_status == "disputed" for claim in claims)):
        raise EvidenceLedgerValidationError("disputed snapshots require a disputed claim or visible contradiction.")


def _require_claims_frozen_by_hypotheses(
    session: Session,
    hypotheses: list[Stage2FinancialHypothesisRevision],
    claims: list[ClaimRevision],
) -> None:
    allowed = set(
        session.scalars(
            select(Stage2HypothesisClaimLink.claim_revision_id).where(
                Stage2HypothesisClaimLink.hypothesis_revision_id.in_(
                    [item.id for item in hypotheses]
                )
            )
        )
    )
    if any(item.id not in allowed for item in claims):
        raise EvidenceLedgerValidationError(
            "claim revisions must be frozen by the selected Stage 2 hypothesis revisions."
        )


def _price(session: Session, research: Stage2CompanyResearch, price_id: int | None, cutoff: date, recorded: datetime) -> tuple[DailyPriceRecord, IngestionRun] | None:
    if price_id is None:
        return None
    row = session.get(DailyPriceRecord, price_id)
    if row is None:
        raise EvidenceLedgerNotFound("daily_price row was not found.")
    run = session.get(IngestionRun, row.ingestion_run_id)
    if run is None or run.status != "succeeded" or run.completed_at is None:
        raise EvidenceLedgerValidationError("price reference must belong to a successful ingestion run.")
    imported_at = _stored_utc(run.imported_at)
    completed_at = _stored_utc(run.completed_at)
    if completed_at < imported_at:
        raise EvidenceLedgerValidationError(
            "price ingestion completion timestamp must not precede import timestamp."
        )
    if row.source != research.source or row.stock_code != research.stock_code:
        raise EvidenceLedgerValidationError("price reference must match the frozen Stage 2 company identity.")
    if row.trade_date > cutoff or run.information_cutoff_date > cutoff:
        raise EvidenceLedgerValidationError("price reference is after the valuation cutoff.")
    validate_utc_chronology(
        recorded,
        ("price import timestamp", imported_at),
        ("price completion timestamp", completed_at),
    )
    return row, run


def _locked_research(session: Session, identity: UUID) -> Stage2CompanyResearch:
    row = session.scalar(select(Stage2CompanyResearch).where(Stage2CompanyResearch.id == identity).with_for_update())
    if row is None:
        raise EvidenceLedgerNotFound(f"Stage 2 company research {identity} was not found.")
    return row


def _locked_expectation(session: Session, identity: UUID) -> Stage2MarketExpectation:
    row = session.scalar(select(Stage2MarketExpectation).where(Stage2MarketExpectation.id == identity).with_for_update())
    if row is None:
        raise EvidenceLedgerNotFound(f"Stage 2 expectation {identity} was not found.")
    return row


def _locked_valuation(session: Session, identity: UUID) -> Stage2ValuationSnapshot:
    row = session.scalar(select(Stage2ValuationSnapshot).where(Stage2ValuationSnapshot.id == identity).with_for_update())
    if row is None:
        raise EvidenceLedgerNotFound(f"Stage 2 valuation snapshot {identity} was not found.")
    return row


def _latest(session: Session, model: type[Any], field: str, identity: UUID) -> Any | None:
    return session.scalar(select(model).where(getattr(model, field) == identity).order_by(model.revision_no.desc()).limit(1))


def _decimal_text(value: str | Decimal | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, (str, Decimal)):
        raise EvidenceLedgerValidationError("observed_value must be a decimal string or Decimal.")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise EvidenceLedgerValidationError("observed_value must be finite decimal text.") from exc
    if not parsed.is_finite():
        raise EvidenceLedgerValidationError("observed_value must be finite.")
    if parsed.is_zero():
        return "0"
    sign, digit_values, exponent = parsed.as_tuple()
    digits = "".join(str(item) for item in digit_values)
    while digits.endswith("0"):
        digits = digits[:-1]
        exponent += 1
    prefix = "-" if sign else ""
    if exponent >= 0:
        canonical_length = len(prefix) + len(digits) + exponent
        if canonical_length > 64:
            raise EvidenceLedgerValidationError(
                "observed_value canonical decimal must not exceed 64 characters."
            )
        return prefix + digits + ("0" * exponent)
    decimal_position = len(digits) + exponent
    if decimal_position > 0:
        canonical_length = len(prefix) + len(digits) + 1
        if canonical_length > 64:
            raise EvidenceLedgerValidationError(
                "observed_value canonical decimal must not exceed 64 characters."
            )
        return prefix + digits[:decimal_position] + "." + digits[decimal_position:]
    canonical_length = len(prefix) + 2 + (-decimal_position) + len(digits)
    if canonical_length > 64:
        raise EvidenceLedgerValidationError(
            "observed_value canonical decimal must not exceed 64 characters."
        )
    return prefix + "0." + ("0" * (-decimal_position)) + digits


def _valuation_value_state(
    method: str,
    observed_value: str | Decimal | None,
    missing_data_reason: str | None,
) -> tuple[str | None, str | None]:
    observed = _decimal_text(observed_value)
    missing = _optional_text(missing_data_reason, "missing_data_reason", 500)
    if method == "missing_data":
        if observed is not None:
            raise EvidenceLedgerValidationError(
                "missing_data valuation_method requires observed_value to be None."
            )
        if missing is None:
            raise EvidenceLedgerValidationError(
                "missing_data valuation_method requires a nonblank missing_data_reason."
            )
    else:
        if observed is None:
            raise EvidenceLedgerValidationError(
                "non-missing valuation methods require an observed_value."
            )
        if missing is not None:
            raise EvidenceLedgerValidationError(
                "non-missing valuation methods must not include missing_data_reason."
            )
    return observed, missing


def _validated_valuation_values(
    valuation_method: str,
    observed_value: str | Decimal | None,
    missing_data_reason: str | None,
) -> tuple[str, str | None, str | None]:
    method = reviewed_value(valuation_method, "valuation_method", VALUATION_METHODS)
    observed, missing = _valuation_value_state(
        method, observed_value, missing_data_reason
    )
    return method, observed, missing


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


def _required_date(value: date, field: str) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise EvidenceLedgerValidationError(f"{field} must be a date.")
    return value


def _stored_utc(value: datetime | None) -> datetime:
    if value is None:
        raise EvidenceLedgerValidationError("required UTC timestamp is missing.")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
