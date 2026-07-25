"""Session-bound write port for authoritative Stage 1 owner operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.errors import (
    EvidenceLedgerConflictError,
    EvidenceLedgerNotFound,
    EvidenceLedgerValidationError,
)
from industry_alpha.stage1_commands import (
    MapAssertionRevisionInput,
    Stage1BeneficiaryCommandService,
    _required_text,
    _stored_utc,
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
from industry_alpha.validation import validate_recorded_cutoff, validate_utc_chronology


@dataclass(frozen=True)
class Stage1BeneficiaryOwnerResult:
    beneficiary: Stage1Beneficiary
    revision: Stage1BeneficiaryRevision


@dataclass(frozen=True)
class Stage1CandidatePoolOwnerResult:
    candidate_pool: Stage1CandidatePool
    revision: Stage1CandidatePoolRevision


class Stage1OwnerWritePort:
    """Apply Stage 1 writes inside a caller-owned SQLAlchemy transaction.

    The port delegates all revision validation and insertion to the existing
    Stage1BeneficiaryCommandService internals. It never commits, rolls back, or
    opens a transaction.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._owner = Stage1BeneficiaryCommandService(session_factory)

    def lock_identities(
        self,
        session: Session,
        *,
        beneficiary_ids: tuple[UUID, ...] = (),
        candidate_pool_id: UUID | None = None,
    ) -> None:
        """Acquire owner locks in deterministic UUID order."""

        for beneficiary_id in sorted(set(beneficiary_ids), key=str):
            self._owner._locked_beneficiary(session, beneficiary_id)
        if candidate_pool_id is not None:
            self._owner._locked_candidate_pool(session, candidate_pool_id)

    def reuse_beneficiary_revision(
        self,
        session: Session,
        *,
        beneficiary_id: UUID,
        beneficiary_revision_id: UUID,
        case_id: UUID,
        map_id: UUID,
        selected_map_revision_id: UUID,
        stock_basic_record_id: int,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
    ) -> Stage1BeneficiaryOwnerResult:
        beneficiary = self._owner._locked_beneficiary(session, beneficiary_id)
        revision = session.get(Stage1BeneficiaryRevision, beneficiary_revision_id)
        if revision is None or revision.beneficiary_id != beneficiary.id:
            raise EvidenceLedgerNotFound(
                "exact Stage 1 beneficiary revision was not found"
            )
        if beneficiary.case_id != case_id or beneficiary.map_id != map_id:
            raise EvidenceLedgerValidationError(
                "reused beneficiary revision must share the exact research case and map"
            )
        if revision.selected_map_revision_id != selected_map_revision_id:
            raise EvidenceLedgerValidationError(
                "reused beneficiary revision must freeze the exact selected map revision"
            )
        if revision.stock_basic_record_id != stock_basic_record_id:
            raise EvidenceLedgerValidationError(
                "reused beneficiary revision must freeze the exact stock_basic record"
            )
        if revision.assessment_status == "rejected":
            raise EvidenceLedgerValidationError(
                "rejected Stage 1 beneficiary revisions are not acceptance-eligible"
            )
        if revision.information_cutoff_date > information_cutoff_date:
            raise EvidenceLedgerValidationError(
                "reused beneficiary revision exceeds the owner-acceptance cutoff"
            )
        if _stored_utc(revision.recorded_at_utc) > _stored_utc(recorded_at_utc):
            raise EvidenceLedgerValidationError(
                "reused beneficiary revision exceeds the owner-acceptance recorded boundary"
            )
        assertion_count = session.scalar(
            select(Stage1BeneficiaryAssertionLink.id)
            .where(
                Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                == revision.id
            )
            .limit(1)
        )
        claim_count = session.scalar(
            select(Stage1BeneficiaryClaimLink.id)
            .where(
                Stage1BeneficiaryClaimLink.beneficiary_revision_id
                == revision.id
            )
            .limit(1)
        )
        if assertion_count is None or claim_count is None:
            raise EvidenceLedgerValidationError(
                "reused beneficiary revision lacks complete assertion or claim bindings"
            )
        return Stage1BeneficiaryOwnerResult(beneficiary=beneficiary, revision=revision)

    def create_beneficiary(
        self,
        session: Session,
        *,
        case_id: UUID,
        map_id: UUID,
        source: str,
        stock_code: str,
        selected_map_revision_id: UUID,
        stock_basic_record_id: int,
        beneficiary_kind: str,
        assessment_status: str,
        rationale_summary: str,
        information_cutoff_date: date,
        assertion_revisions: tuple[MapAssertionRevisionInput, ...],
        claim_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime,
    ) -> Stage1BeneficiaryOwnerResult:
        validate_recorded_cutoff(information_cutoff_date, recorded_at_utc)
        normalized_source = _required_text(source, "source", 64)
        normalized_code = _required_text(stock_code, "stock_code", 16)
        case, industry_map = self._owner._case_and_map(session, case_id, map_id)
        validate_utc_chronology(
            recorded_at_utc,
            ("research case creation timestamp", _stored_utc(case.created_at_utc)),
            ("industry map creation timestamp", _stored_utc(industry_map.created_at_utc)),
        )
        existing = session.scalar(
            select(Stage1Beneficiary)
            .where(
                Stage1Beneficiary.case_id == case_id,
                Stage1Beneficiary.map_id == map_id,
                Stage1Beneficiary.source == normalized_source,
                Stage1Beneficiary.stock_code == normalized_code,
            )
            .with_for_update()
        )
        if existing is not None:
            raise EvidenceLedgerConflictError(
                "beneficiary source and stock_code already exist in this map"
            )
        beneficiary = Stage1Beneficiary(
            case_id=case_id,
            map_id=map_id,
            source=normalized_source,
            stock_code=normalized_code,
            created_at_utc=recorded_at_utc,
        )
        session.add(beneficiary)
        session.flush()
        revision = self._owner._insert_beneficiary_revision(
            session,
            beneficiary=beneficiary,
            selected_map_revision_id=selected_map_revision_id,
            stock_basic_record_id=stock_basic_record_id,
            beneficiary_kind=beneficiary_kind,
            assessment_status=assessment_status,
            rationale_summary=rationale_summary,
            information_cutoff_date=information_cutoff_date,
            assertion_revisions=assertion_revisions,
            claim_revision_ids=claim_revision_ids,
            recorded_at_utc=recorded_at_utc,
        )
        return Stage1BeneficiaryOwnerResult(beneficiary=beneficiary, revision=revision)

    def append_beneficiary_revision(
        self,
        session: Session,
        *,
        beneficiary_id: UUID,
        expected_latest_revision_id: UUID,
        selected_map_revision_id: UUID,
        stock_basic_record_id: int,
        beneficiary_kind: str,
        assessment_status: str,
        rationale_summary: str,
        information_cutoff_date: date,
        assertion_revisions: tuple[MapAssertionRevisionInput, ...],
        claim_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime,
    ) -> Stage1BeneficiaryOwnerResult:
        validate_recorded_cutoff(information_cutoff_date, recorded_at_utc)
        beneficiary = self._owner._locked_beneficiary(session, beneficiary_id)
        latest = self._owner._latest_revision(
            session,
            Stage1BeneficiaryRevision,
            "beneficiary_id",
            beneficiary.id,
        )
        if latest is None or latest.id != expected_latest_revision_id:
            raise EvidenceLedgerConflictError(
                "expected latest beneficiary revision does not match accepted history"
            )
        revision = self._owner._insert_beneficiary_revision(
            session,
            beneficiary=beneficiary,
            selected_map_revision_id=selected_map_revision_id,
            stock_basic_record_id=stock_basic_record_id,
            beneficiary_kind=beneficiary_kind,
            assessment_status=assessment_status,
            rationale_summary=rationale_summary,
            information_cutoff_date=information_cutoff_date,
            assertion_revisions=assertion_revisions,
            claim_revision_ids=claim_revision_ids,
            recorded_at_utc=recorded_at_utc,
        )
        return Stage1BeneficiaryOwnerResult(beneficiary=beneficiary, revision=revision)

    def create_candidate_pool(
        self,
        session: Session,
        *,
        case_id: UUID,
        map_id: UUID,
        pool_key: str,
        selected_map_revision_id: UUID,
        title: str,
        scope: str,
        information_cutoff_date: date,
        beneficiary_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime,
    ) -> Stage1CandidatePoolOwnerResult:
        validate_recorded_cutoff(information_cutoff_date, recorded_at_utc)
        normalized_key = _required_text(pool_key, "pool_key", 96)
        case, industry_map = self._owner._case_and_map(session, case_id, map_id)
        validate_utc_chronology(
            recorded_at_utc,
            ("research case creation timestamp", _stored_utc(case.created_at_utc)),
            ("industry map creation timestamp", _stored_utc(industry_map.created_at_utc)),
        )
        existing = session.scalar(
            select(Stage1CandidatePool)
            .where(
                Stage1CandidatePool.case_id == case_id,
                Stage1CandidatePool.map_id == map_id,
                Stage1CandidatePool.pool_key == normalized_key,
            )
            .with_for_update()
        )
        if existing is not None:
            raise EvidenceLedgerConflictError(
                "candidate-pool key already exists in this map"
            )
        pool = Stage1CandidatePool(
            case_id=case_id,
            map_id=map_id,
            pool_key=normalized_key,
            created_at_utc=recorded_at_utc,
        )
        session.add(pool)
        session.flush()
        revision = self._owner._insert_candidate_pool_revision(
            session,
            pool=pool,
            selected_map_revision_id=selected_map_revision_id,
            title=title,
            scope=scope,
            information_cutoff_date=information_cutoff_date,
            beneficiary_revision_ids=beneficiary_revision_ids,
            recorded_at_utc=recorded_at_utc,
        )
        return Stage1CandidatePoolOwnerResult(candidate_pool=pool, revision=revision)

    def append_candidate_pool_revision(
        self,
        session: Session,
        *,
        candidate_pool_id: UUID,
        expected_latest_revision_id: UUID,
        selected_map_revision_id: UUID,
        title: str,
        scope: str,
        information_cutoff_date: date,
        beneficiary_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime,
    ) -> Stage1CandidatePoolOwnerResult:
        validate_recorded_cutoff(information_cutoff_date, recorded_at_utc)
        pool = self._owner._locked_candidate_pool(session, candidate_pool_id)
        latest = self._owner._latest_revision(
            session,
            Stage1CandidatePoolRevision,
            "candidate_pool_id",
            pool.id,
        )
        if latest is None or latest.id != expected_latest_revision_id:
            raise EvidenceLedgerConflictError(
                "expected latest candidate-pool revision does not match accepted history"
            )
        revision = self._owner._insert_candidate_pool_revision(
            session,
            pool=pool,
            selected_map_revision_id=selected_map_revision_id,
            title=title,
            scope=scope,
            information_cutoff_date=information_cutoff_date,
            beneficiary_revision_ids=beneficiary_revision_ids,
            recorded_at_utc=recorded_at_utc,
        )
        return Stage1CandidatePoolOwnerResult(candidate_pool=pool, revision=revision)

    def reuse_candidate_pool_revision(
        self,
        session: Session,
        *,
        candidate_pool_id: UUID,
        candidate_pool_revision_id: UUID,
        case_id: UUID,
        map_id: UUID,
        selected_map_revision_id: UUID,
        beneficiary_revision_ids: tuple[UUID, ...],
        information_cutoff_date: date,
        recorded_at_utc: datetime,
    ) -> Stage1CandidatePoolOwnerResult:
        pool = self._owner._locked_candidate_pool(session, candidate_pool_id)
        revision = session.get(Stage1CandidatePoolRevision, candidate_pool_revision_id)
        if revision is None or revision.candidate_pool_id != pool.id:
            raise EvidenceLedgerNotFound(
                "exact Stage 1 candidate-pool revision was not found"
            )
        if pool.case_id != case_id or pool.map_id != map_id:
            raise EvidenceLedgerValidationError(
                "reused candidate pool must share the exact research case and map"
            )
        if revision.selected_map_revision_id != selected_map_revision_id:
            raise EvidenceLedgerValidationError(
                "reused candidate pool must freeze the exact selected map revision"
            )
        if revision.information_cutoff_date > information_cutoff_date:
            raise EvidenceLedgerValidationError(
                "reused candidate-pool revision exceeds the owner-acceptance cutoff"
            )
        if _stored_utc(revision.recorded_at_utc) > _stored_utc(recorded_at_utc):
            raise EvidenceLedgerValidationError(
                "reused candidate-pool revision exceeds the owner-acceptance recorded boundary"
            )
        actual = tuple(
            session.scalars(
                select(Stage1CandidatePoolMembership.beneficiary_revision_id)
                .where(
                    Stage1CandidatePoolMembership.candidate_pool_revision_id
                    == revision.id
                )
                .order_by(Stage1CandidatePoolMembership.beneficiary_revision_id)
            )
        )
        expected = tuple(sorted(set(beneficiary_revision_ids), key=str))
        if actual != expected:
            raise EvidenceLedgerValidationError(
                "reused candidate-pool membership does not equal the supported accepted subset"
            )
        return Stage1CandidatePoolOwnerResult(candidate_pool=pool, revision=revision)
