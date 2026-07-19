"""Transactional commands for evidence-backed Stage 1 beneficiary records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from threading import Lock, RLock
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.database.models import IngestionRun, StockBasicRecord
from industry_alpha.chain_map_models import (
    IndustryMap,
    IndustryMapNode,
    IndustryMapNodeRevision,
    IndustryMapObservation,
    IndustryMapObservationRevision,
    IndustryMapRelationship,
    IndustryMapRelationshipRevision,
    IndustryMapRevision,
    IndustryMapRevisionMembership,
)
from industry_alpha.errors import (
    EvidenceLedgerConflictError,
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
from industry_alpha.validation import (
    utc_timestamp,
    validate_recorded_cutoff,
    validate_utc_chronology,
)

BENEFICIARY_KINDS = frozenset({"direct", "secondary", "potential"})
ASSESSMENT_STATUSES = frozenset({"draft", "supported", "disputed", "rejected"})
ASSERTION_KINDS = frozenset({"node", "relationship", "observation"})

_LOCKS_GUARD = Lock()
_LOCKS: dict[tuple[str, UUID], RLock] = {}


def _revision_lock(kind: str, identity: UUID) -> RLock:
    key = (kind, identity)
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, RLock())


@dataclass(frozen=True)
class MapAssertionRevisionInput:
    assertion_kind: str
    assertion_revision_id: UUID


@dataclass(frozen=True)
class _AssertionRef:
    kind: str
    revision: Any
    map_id: UUID
    assertion_status: str
    information_cutoff_date: date
    recorded_at_utc: datetime


class Stage1BeneficiaryCommandService:
    """Append identities, immutable revisions, links, pools, and memberships."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_beneficiary(
        self,
        case_id: UUID,
        map_id: UUID,
        *,
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
        recorded_at_utc: datetime | None = None,
    ) -> Stage1Beneficiary:
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        normalized_source = _required_text(source, "source", 64)
        normalized_code = _required_text(stock_code, "stock_code", 16)
        with self._translate_integrity(
            "beneficiary source and stock_code already exist in this map"
        ):
            with self._session_factory.begin() as session:
                case, industry_map = self._case_and_map(session, case_id, map_id)
                validate_utc_chronology(
                    recorded,
                    ("research case creation timestamp", _stored_utc(case.created_at_utc)),
                    ("industry map creation timestamp", _stored_utc(industry_map.created_at_utc)),
                )
                beneficiary = Stage1Beneficiary(
                    case_id=case_id,
                    map_id=map_id,
                    source=normalized_source,
                    stock_code=normalized_code,
                    created_at_utc=recorded,
                )
                session.add(beneficiary)
                session.flush()
                self._insert_beneficiary_revision(
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
                    recorded_at_utc=recorded,
                )
            return beneficiary

    def append_beneficiary_revision(
        self,
        beneficiary_id: UUID,
        *,
        selected_map_revision_id: UUID,
        stock_basic_record_id: int,
        beneficiary_kind: str,
        assessment_status: str,
        rationale_summary: str,
        information_cutoff_date: date,
        assertion_revisions: tuple[MapAssertionRevisionInput, ...],
        claim_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime | None = None,
    ) -> Stage1BeneficiaryRevision:
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        with _revision_lock("beneficiary", beneficiary_id):
            with self._translate_integrity(
                "beneficiary revision conflicts with accepted history"
            ):
                with self._session_factory.begin() as session:
                    beneficiary = self._locked_beneficiary(session, beneficiary_id)
                    revision = self._insert_beneficiary_revision(
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
                        recorded_at_utc=recorded,
                    )
            return revision

    def create_candidate_pool(
        self,
        case_id: UUID,
        map_id: UUID,
        *,
        pool_key: str,
        selected_map_revision_id: UUID,
        title: str,
        scope: str,
        information_cutoff_date: date,
        beneficiary_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime | None = None,
    ) -> Stage1CandidatePool:
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        key = _required_text(pool_key, "pool_key", 96)
        with self._translate_integrity(
            "candidate-pool key already exists in this map"
        ):
            with self._session_factory.begin() as session:
                case, industry_map = self._case_and_map(session, case_id, map_id)
                validate_utc_chronology(
                    recorded,
                    ("research case creation timestamp", _stored_utc(case.created_at_utc)),
                    ("industry map creation timestamp", _stored_utc(industry_map.created_at_utc)),
                )
                pool = Stage1CandidatePool(
                    case_id=case_id,
                    map_id=map_id,
                    pool_key=key,
                    created_at_utc=recorded,
                )
                session.add(pool)
                session.flush()
                self._insert_candidate_pool_revision(
                    session,
                    pool=pool,
                    selected_map_revision_id=selected_map_revision_id,
                    title=title,
                    scope=scope,
                    information_cutoff_date=information_cutoff_date,
                    beneficiary_revision_ids=beneficiary_revision_ids,
                    recorded_at_utc=recorded,
                )
            return pool

    def append_candidate_pool_revision(
        self,
        candidate_pool_id: UUID,
        *,
        selected_map_revision_id: UUID,
        title: str,
        scope: str,
        information_cutoff_date: date,
        beneficiary_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime | None = None,
    ) -> Stage1CandidatePoolRevision:
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        with _revision_lock("candidate_pool", candidate_pool_id):
            with self._translate_integrity(
                "candidate-pool revision conflicts with accepted history"
            ):
                with self._session_factory.begin() as session:
                    pool = self._locked_candidate_pool(session, candidate_pool_id)
                    revision = self._insert_candidate_pool_revision(
                        session,
                        pool=pool,
                        selected_map_revision_id=selected_map_revision_id,
                        title=title,
                        scope=scope,
                        information_cutoff_date=information_cutoff_date,
                        beneficiary_revision_ids=beneficiary_revision_ids,
                        recorded_at_utc=recorded,
                    )
            return revision

    def _insert_beneficiary_revision(
        self,
        session: Session,
        *,
        beneficiary: Stage1Beneficiary,
        selected_map_revision_id: UUID,
        stock_basic_record_id: int,
        beneficiary_kind: str,
        assessment_status: str,
        rationale_summary: str,
        information_cutoff_date: date,
        assertion_revisions: tuple[MapAssertionRevisionInput, ...],
        claim_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime,
    ) -> Stage1BeneficiaryRevision:
        prior = self._latest_revision(
            session,
            Stage1BeneficiaryRevision,
            "beneficiary_id",
            beneficiary.id,
        )
        chronology = [
            ("beneficiary identity timestamp", _stored_utc(beneficiary.created_at_utc))
        ]
        if prior is not None:
            chronology.append(
                ("previous beneficiary revision timestamp", _stored_utc(prior.recorded_at_utc))
            )
        validate_utc_chronology(recorded_at_utc, *chronology)
        status = _reviewed_value(
            assessment_status, "assessment_status", ASSESSMENT_STATUSES
        )
        kind = _reviewed_value(
            beneficiary_kind, "beneficiary_kind", BENEFICIARY_KINDS
        )
        selected_map_revision = self._selected_map_revision(
            session,
            selected_map_revision_id,
            beneficiary.map_id,
            information_cutoff_date,
            recorded_at_utc,
        )
        stock_record, ingestion_run = self._stock_snapshot(
            session,
            stock_basic_record_id,
            beneficiary,
            information_cutoff_date,
            recorded_at_utc,
        )
        assertions = self._assertion_refs(
            session,
            assertion_revisions,
            selected_map_revision,
            information_cutoff_date,
            recorded_at_utc,
        )
        claims = self._claim_revisions(
            session,
            claim_revision_ids,
            beneficiary.case_id,
            information_cutoff_date,
            recorded_at_utc,
        )
        self._validate_assessment_status(session, status, claims, recorded_at_utc)
        validate_utc_chronology(
            recorded_at_utc,
            ("company snapshot import timestamp", _stored_utc(ingestion_run.imported_at)),
            ("company snapshot completion timestamp", _stored_utc(ingestion_run.completed_at)),
            ("selected map revision timestamp", _stored_utc(selected_map_revision.recorded_at_utc)),
            *((f"{item.kind} assertion revision timestamp", item.recorded_at_utc) for item in assertions),
            *(("claim revision timestamp", _stored_utc(item.recorded_at_utc)) for item in claims),
        )
        revision = Stage1BeneficiaryRevision(
            beneficiary_id=beneficiary.id,
            revision_no=1 if prior is None else prior.revision_no + 1,
            selected_map_revision_id=selected_map_revision.id,
            stock_basic_record_id=stock_record.id,
            beneficiary_kind=kind,
            assessment_status=status,
            rationale_summary=_required_text(
                rationale_summary, "rationale_summary", 4000
            ),
            information_cutoff_date=information_cutoff_date,
            recorded_at_utc=recorded_at_utc,
            supersedes_revision_id=None if prior is None else prior.id,
        )
        session.add(revision)
        session.flush()
        for assertion in assertions:
            link = Stage1BeneficiaryAssertionLink(
                beneficiary_revision_id=revision.id,
                recorded_at_utc=recorded_at_utc,
            )
            setattr(link, f"{assertion.kind}_revision_id", assertion.revision.id)
            session.add(link)
        for claim in claims:
            session.add(
                Stage1BeneficiaryClaimLink(
                    beneficiary_revision_id=revision.id,
                    claim_revision_id=claim.id,
                    recorded_at_utc=recorded_at_utc,
                )
            )
        session.flush()
        return revision

    def _insert_candidate_pool_revision(
        self,
        session: Session,
        *,
        pool: Stage1CandidatePool,
        selected_map_revision_id: UUID,
        title: str,
        scope: str,
        information_cutoff_date: date,
        beneficiary_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime,
    ) -> Stage1CandidatePoolRevision:
        prior = self._latest_revision(
            session,
            Stage1CandidatePoolRevision,
            "candidate_pool_id",
            pool.id,
        )
        chronology = [
            ("candidate-pool identity timestamp", _stored_utc(pool.created_at_utc))
        ]
        if prior is not None:
            chronology.append(
                ("previous candidate-pool revision timestamp", _stored_utc(prior.recorded_at_utc))
            )
        validate_utc_chronology(recorded_at_utc, *chronology)
        selected_map_revision = self._selected_map_revision(
            session,
            selected_map_revision_id,
            pool.map_id,
            information_cutoff_date,
            recorded_at_utc,
        )
        beneficiaries = self._eligible_beneficiary_revisions(
            session,
            beneficiary_revision_ids,
            pool,
            selected_map_revision,
            information_cutoff_date,
            recorded_at_utc,
        )
        revision = Stage1CandidatePoolRevision(
            candidate_pool_id=pool.id,
            revision_no=1 if prior is None else prior.revision_no + 1,
            selected_map_revision_id=selected_map_revision.id,
            title=_required_text(title, "title", 300),
            scope=_required_text(scope, "scope", 4000),
            information_cutoff_date=information_cutoff_date,
            recorded_at_utc=recorded_at_utc,
            supersedes_revision_id=None if prior is None else prior.id,
        )
        session.add(revision)
        session.flush()
        for beneficiary_revision, beneficiary in beneficiaries:
            session.add(
                Stage1CandidatePoolMembership(
                    candidate_pool_revision_id=revision.id,
                    beneficiary_id=beneficiary.id,
                    beneficiary_revision_id=beneficiary_revision.id,
                    recorded_at_utc=recorded_at_utc,
                )
            )
        session.flush()
        return revision

    @staticmethod
    def _case_and_map(
        session: Session, case_id: UUID, map_id: UUID
    ) -> tuple[ResearchCase, IndustryMap]:
        case = session.get(ResearchCase, case_id)
        industry_map = session.get(IndustryMap, map_id)
        if case is None or industry_map is None:
            raise EvidenceLedgerNotFound("research case or industry map was not found.")
        if industry_map.case_id != case_id:
            raise EvidenceLedgerValidationError(
                "beneficiary records and industry map must share one research case."
            )
        return case, industry_map

    @staticmethod
    def _selected_map_revision(
        session: Session,
        revision_id: UUID,
        map_id: UUID,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
    ) -> IndustryMapRevision:
        revision = session.get(IndustryMapRevision, revision_id)
        if revision is None:
            raise EvidenceLedgerNotFound(
                f"Industry map revision {revision_id} was not found."
            )
        if revision.map_id != map_id:
            raise EvidenceLedgerValidationError(
                "selected map revision must belong to the beneficiary industry map."
            )
        if revision.information_cutoff_date > information_cutoff_date:
            raise EvidenceLedgerValidationError(
                "selected map revision cutoff exceeds the Stage 1 cutoff."
            )
        validate_utc_chronology(
            recorded_at_utc,
            ("selected map revision timestamp", _stored_utc(revision.recorded_at_utc)),
        )
        return revision

    @staticmethod
    def _stock_snapshot(
        session: Session,
        stock_basic_record_id: int,
        beneficiary: Stage1Beneficiary,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
    ) -> tuple[StockBasicRecord, IngestionRun]:
        if not isinstance(stock_basic_record_id, int) or isinstance(
            stock_basic_record_id, bool
        ):
            raise EvidenceLedgerValidationError(
                "stock_basic_record_id must be an integer."
            )
        record = session.scalar(
            select(StockBasicRecord)
            .where(StockBasicRecord.id == stock_basic_record_id)
            .with_for_update()
        )
        if record is None:
            raise EvidenceLedgerNotFound(
                f"Stock basic record {stock_basic_record_id} was not found."
            )
        run = session.scalar(
            select(IngestionRun)
            .where(IngestionRun.id == record.ingestion_run_id)
            .with_for_update()
        )
        if run is None or run.status != "succeeded" or run.completed_at is None:
            raise EvidenceLedgerValidationError(
                "stock_basic_record_id must belong to a completed successful ingestion run."
            )
        if record.source != beneficiary.source or record.stock_code != beneficiary.stock_code:
            raise EvidenceLedgerValidationError(
                "stock_basic_record_id must exactly match beneficiary source and stock_code."
            )
        if run.provider != record.source:
            raise EvidenceLedgerValidationError(
                "company snapshot provider must exactly match stock_basic source."
            )
        if run.information_cutoff_date > information_cutoff_date:
            raise EvidenceLedgerValidationError(
                "company snapshot cutoff exceeds the beneficiary revision cutoff."
            )
        validate_utc_chronology(
            recorded_at_utc,
            ("company snapshot import timestamp", _stored_utc(run.imported_at)),
            ("company snapshot completion timestamp", _stored_utc(run.completed_at)),
        )
        return record, run

    def _assertion_refs(
        self,
        session: Session,
        inputs: tuple[MapAssertionRevisionInput, ...],
        selected_map_revision: IndustryMapRevision,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
    ) -> list[_AssertionRef]:
        if not inputs:
            raise EvidenceLedgerValidationError(
                "every beneficiary revision requires at least one map assertion revision."
            )
        keys = [(item.assertion_kind, item.assertion_revision_id) for item in inputs]
        if len(set(keys)) != len(keys):
            raise EvidenceLedgerValidationError(
                "assertion_revisions must not contain duplicates."
            )
        members = list(
            session.scalars(
                select(IndustryMapRevisionMembership).where(
                    IndustryMapRevisionMembership.map_revision_id
                    == selected_map_revision.id
                )
            )
        )
        membership_ids = {
            kind: {
                getattr(item, f"{kind}_revision_id")
                for item in members
                if getattr(item, f"{kind}_revision_id") is not None
            }
            for kind in ASSERTION_KINDS
        }
        refs = [
            self._assertion_ref(session, item.assertion_kind, item.assertion_revision_id)
            for item in inputs
        ]
        for ref in refs:
            if ref.map_id != selected_map_revision.map_id:
                raise EvidenceLedgerValidationError(
                    "beneficiary assertion links must belong to the selected industry map."
                )
            if ref.revision.id not in membership_ids[ref.kind]:
                raise EvidenceLedgerValidationError(
                    "beneficiary assertion revision is not frozen in the selected map revision."
                )
            if ref.information_cutoff_date > information_cutoff_date:
                raise EvidenceLedgerValidationError(
                    "map assertion cutoff exceeds the beneficiary revision cutoff."
                )
            validate_utc_chronology(
                recorded_at_utc,
                (f"{ref.kind} assertion revision timestamp", ref.recorded_at_utc),
            )
        refs.sort(key=lambda item: (item.kind, str(item.revision.id)))
        return refs

    @staticmethod
    def _assertion_ref(
        session: Session, kind: str, revision_id: UUID
    ) -> _AssertionRef:
        normalized_kind = _reviewed_value(kind, "assertion_kind", ASSERTION_KINDS)
        models: dict[str, tuple[type[Any], type[Any], str]] = {
            "node": (IndustryMapNodeRevision, IndustryMapNode, "node_id"),
            "relationship": (
                IndustryMapRelationshipRevision,
                IndustryMapRelationship,
                "relationship_id",
            ),
            "observation": (
                IndustryMapObservationRevision,
                IndustryMapObservation,
                "observation_id",
            ),
        }
        revision_model, identity_model, identity_field = models[normalized_kind]
        revision = session.get(revision_model, revision_id)
        if revision is None:
            raise EvidenceLedgerNotFound(
                f"{normalized_kind} revision {revision_id} was not found."
            )
        identity = session.get(identity_model, getattr(revision, identity_field))
        if identity is None:
            raise EvidenceLedgerNotFound(
                f"{normalized_kind} assertion identity was not found."
            )
        return _AssertionRef(
            kind=normalized_kind,
            revision=revision,
            map_id=identity.map_id,
            assertion_status=revision.assertion_status,
            information_cutoff_date=revision.information_cutoff_date,
            recorded_at_utc=_stored_utc(revision.recorded_at_utc),
        )

    def _claim_revisions(
        self,
        session: Session,
        revision_ids: tuple[UUID, ...],
        case_id: UUID,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
    ) -> list[ClaimRevision]:
        if not revision_ids:
            raise EvidenceLedgerValidationError(
                "every beneficiary revision requires at least one claim revision."
            )
        if len(set(revision_ids)) != len(revision_ids):
            raise EvidenceLedgerValidationError(
                "claim_revision_ids must not contain duplicates."
            )
        ordered_ids = sorted(revision_ids, key=str)
        revisions = list(
            session.scalars(
                select(ClaimRevision)
                .where(ClaimRevision.id.in_(ordered_ids))
                .order_by(ClaimRevision.id)
                .with_for_update()
            )
        )
        if len(revisions) != len(ordered_ids):
            missing = sorted(set(ordered_ids) - {item.id for item in revisions}, key=str)
            raise EvidenceLedgerNotFound(
                f"Claim revision {missing[0]} was not found."
            )
        claim_ids: set[UUID] = set()
        for revision in revisions:
            claim = session.get(Claim, revision.claim_id)
            if claim is None or claim.case_id != case_id:
                raise EvidenceLedgerValidationError(
                    "beneficiary and linked claim revisions must share one research case."
                )
            if revision.claim_id in claim_ids:
                raise EvidenceLedgerValidationError(
                    "a beneficiary revision cannot bind multiple revisions of one claim identity."
                )
            if revision.information_cutoff_date > information_cutoff_date:
                raise EvidenceLedgerValidationError(
                    "claim revision cutoff exceeds the beneficiary revision cutoff."
                )
            validate_utc_chronology(
                recorded_at_utc,
                ("claim revision timestamp", _stored_utc(revision.recorded_at_utc)),
            )
            claim_ids.add(revision.claim_id)
        revisions.sort(key=lambda item: (str(item.claim_id), item.revision_no))
        return revisions

    @staticmethod
    def _validate_assessment_status(
        session: Session,
        status: str,
        claims: list[ClaimRevision],
        effective_at_utc: datetime,
    ) -> None:
        summaries = [
            _claim_evidence_state(session, claim, effective_at_utc)
            for claim in claims
        ]
        if status == "supported":
            if any(item["has_conflict"] for item in summaries):
                raise EvidenceLedgerValidationError(
                    "supported beneficiary revisions cannot have visible contradictory evidence."
                )
            if not any(
                claim.claim_status == "supported" and summary["has_abc_support"]
                for claim, summary in zip(claims, summaries, strict=True)
            ):
                raise EvidenceLedgerValidationError(
                    "supported beneficiary revisions require a supported A/B/C-backed claim revision."
                )
        if status == "disputed" and not any(
            claim.claim_status == "disputed" or summary["has_conflict"]
            for claim, summary in zip(claims, summaries, strict=True)
        ):
            raise EvidenceLedgerValidationError(
                "disputed beneficiary revisions require a disputed claim or visible contradiction."
            )

    @staticmethod
    def _eligible_beneficiary_revisions(
        session: Session,
        revision_ids: tuple[UUID, ...],
        pool: Stage1CandidatePool,
        selected_map_revision: IndustryMapRevision,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
    ) -> list[tuple[Stage1BeneficiaryRevision, Stage1Beneficiary]]:
        if not revision_ids:
            raise EvidenceLedgerValidationError(
                "candidate-pool revisions require at least one supported beneficiary revision."
            )
        if len(set(revision_ids)) != len(revision_ids):
            raise EvidenceLedgerValidationError(
                "beneficiary_revision_ids must not contain duplicates."
            )
        rows: list[tuple[Stage1BeneficiaryRevision, Stage1Beneficiary]] = []
        identities: set[UUID] = set()
        for revision_id in sorted(revision_ids, key=str):
            revision = session.get(Stage1BeneficiaryRevision, revision_id)
            if revision is None:
                raise EvidenceLedgerNotFound(
                    f"Beneficiary revision {revision_id} was not found."
                )
            beneficiary = session.get(Stage1Beneficiary, revision.beneficiary_id)
            if beneficiary is None:
                raise EvidenceLedgerNotFound("beneficiary identity was not found.")
            if beneficiary.case_id != pool.case_id or beneficiary.map_id != pool.map_id:
                raise EvidenceLedgerValidationError(
                    "candidate-pool members must share the pool research case and map."
                )
            if revision.selected_map_revision_id != selected_map_revision.id:
                raise EvidenceLedgerValidationError(
                    "candidate-pool members must share the selected map revision boundary."
                )
            if revision.assessment_status != "supported":
                raise EvidenceLedgerValidationError(
                    "candidate-pool members must be supported beneficiary revisions."
                )
            if revision.beneficiary_kind not in BENEFICIARY_KINDS:
                raise EvidenceLedgerValidationError(
                    "candidate-pool member has an invalid beneficiary kind."
                )
            if revision.information_cutoff_date > information_cutoff_date:
                raise EvidenceLedgerValidationError(
                    "beneficiary revision cutoff exceeds the candidate-pool cutoff."
                )
            if beneficiary.id in identities:
                raise EvidenceLedgerValidationError(
                    "a candidate-pool revision may freeze only one revision per beneficiary identity."
                )
            validate_utc_chronology(
                recorded_at_utc,
                ("beneficiary revision timestamp", _stored_utc(revision.recorded_at_utc)),
            )
            assertion_links = list(
                session.scalars(
                    select(Stage1BeneficiaryAssertionLink).where(
                        Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                        == revision.id
                    )
                )
            )
            claim_links = list(
                session.scalars(
                    select(Stage1BeneficiaryClaimLink).where(
                        Stage1BeneficiaryClaimLink.beneficiary_revision_id
                        == revision.id
                    )
                )
            )
            if not assertion_links or not claim_links:
                raise EvidenceLedgerValidationError(
                    "candidate-pool members require complete assertion and claim bindings."
                )
            validate_utc_chronology(
                recorded_at_utc,
                *(
                    ("beneficiary assertion-link timestamp", _stored_utc(link.recorded_at_utc))
                    for link in assertion_links
                ),
                *(
                    ("beneficiary claim-link timestamp", _stored_utc(link.recorded_at_utc))
                    for link in claim_links
                ),
            )
            identities.add(beneficiary.id)
            rows.append((revision, beneficiary))
        rows.sort(
            key=lambda item: (
                item[0].beneficiary_kind,
                item[1].source,
                item[1].stock_code,
                str(item[1].id),
            )
        )
        return rows

    @staticmethod
    def _latest_revision(
        session: Session, model: type[Any], identity_field: str, identity_id: UUID
    ) -> Any | None:
        return session.scalar(
            select(model)
            .where(getattr(model, identity_field) == identity_id)
            .order_by(model.revision_no.desc())
            .limit(1)
        )

    @staticmethod
    def _locked_beneficiary(
        session: Session, beneficiary_id: UUID
    ) -> Stage1Beneficiary:
        beneficiary = session.scalar(
            select(Stage1Beneficiary)
            .where(Stage1Beneficiary.id == beneficiary_id)
            .with_for_update()
        )
        if beneficiary is None:
            raise EvidenceLedgerNotFound(
                f"Stage 1 beneficiary {beneficiary_id} was not found."
            )
        return beneficiary

    @staticmethod
    def _locked_candidate_pool(
        session: Session, pool_id: UUID
    ) -> Stage1CandidatePool:
        pool = session.scalar(
            select(Stage1CandidatePool)
            .where(Stage1CandidatePool.id == pool_id)
            .with_for_update()
        )
        if pool is None:
            raise EvidenceLedgerNotFound(
                f"Stage 1 candidate pool {pool_id} was not found."
            )
        return pool

    class _IntegrityTranslation:
        def __init__(self, message: str) -> None:
            self.message = message

        def __enter__(self) -> None:
            return None

        def __exit__(
            self,
            _exc_type: type[BaseException] | None,
            exc: BaseException | None,
            _tb: object,
        ) -> bool:
            if isinstance(exc, IntegrityError):
                raise EvidenceLedgerConflictError(self.message) from exc
            return False

    @classmethod
    def _translate_integrity(cls, message: str) -> _IntegrityTranslation:
        return cls._IntegrityTranslation(message)


def validate_claim_evidence_append_after_beneficiary_freeze(
    session: Session, claim_revision_id: UUID, recorded_at_utc: datetime
) -> None:
    """Reject evidence-link backfill into an already accepted beneficiary revision."""
    links = list(
        session.scalars(
            select(Stage1BeneficiaryClaimLink).where(
                Stage1BeneficiaryClaimLink.claim_revision_id == claim_revision_id
            )
        )
    )
    frozen_at: list[datetime] = []
    for link in links:
        revision = session.get(
            Stage1BeneficiaryRevision, link.beneficiary_revision_id
        )
        if (
            revision is not None
            and _stored_utc(link.recorded_at_utc)
            <= _stored_utc(revision.recorded_at_utc)
        ):
            frozen_at.append(_stored_utc(revision.recorded_at_utc))
    if frozen_at and recorded_at_utc <= max(frozen_at):
        raise EvidenceLedgerValidationError(
            "a later claim evidence link must be recorded after every beneficiary revision that already froze the claim binding."
        )


def _claim_evidence_state(
    session: Session, claim: ClaimRevision, effective_at_utc: datetime
) -> dict[str, bool]:
    visible: list[tuple[ClaimEvidenceLink, EvidenceItem]] = []
    for link in session.scalars(
        select(ClaimEvidenceLink).where(
            ClaimEvidenceLink.claim_revision_id == claim.id
        )
    ):
        evidence = session.get(EvidenceItem, link.evidence_id)
        if (
            evidence is not None
            and _stored_utc(link.recorded_at_utc) <= effective_at_utc
            and _stored_utc(evidence.recorded_at_utc) <= effective_at_utc
            and evidence.information_date <= claim.information_cutoff_date
        ):
            visible.append((link, evidence))
    return {
        "has_abc_support": any(
            link.relation == "supports"
            and evidence.evidence_grade in {"A", "B", "C"}
            for link, evidence in visible
        ),
        "has_conflict": any(
            link.relation == "contradicts" for link, _ in visible
        ),
        "has_evidence": bool(visible),
    }


def _required_text(value: str, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise EvidenceLedgerValidationError(f"{field} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise EvidenceLedgerValidationError(f"{field} must not be blank.")
    if len(normalized) > maximum:
        raise EvidenceLedgerValidationError(
            f"{field} exceeds the maximum length of {maximum}."
        )
    return normalized


def _reviewed_value(value: str, field: str, allowed: frozenset[str]) -> str:
    normalized = _required_text(value, field, 64)
    if normalized not in allowed:
        choices = ", ".join(sorted(allowed))
        raise EvidenceLedgerValidationError(f"{field} must be one of: {choices}.")
    return normalized


def _stored_utc(value: datetime | None) -> datetime:
    if value is None:
        raise EvidenceLedgerValidationError("required UTC timestamp is missing.")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
