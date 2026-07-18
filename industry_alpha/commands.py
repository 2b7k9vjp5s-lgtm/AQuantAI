"""Transactional commands for the append-only evidence ledger."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from threading import Lock, RLock
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.errors import (
    EvidenceLedgerConflictError,
    EvidenceLedgerNotFound,
    EvidenceLedgerValidationError,
)
from industry_alpha.models import (
    CaseRevisionClaimLink,
    Claim,
    ClaimEvidenceLink,
    ClaimRevision,
    EvidenceItem,
    ResearchCase,
    ResearchCaseRevision,
    VerificationItem,
)
from industry_alpha.validation import (
    CLAIM_KINDS,
    CLAIM_ROLES,
    CLAIM_STATUSES,
    CONCLUSION_STATUSES,
    EVIDENCE_GRADES,
    EVIDENCE_RELATIONS,
    ORIGINS,
    SOURCE_KINDS,
    VERIFICATION_STATUSES,
    WORKFLOW_STATES,
    optional_text,
    required_text,
    reviewed_value,
    utc_timestamp,
    validate_claim_fields,
    validate_recorded_cutoff,
    validate_utc_chronology,
)

_REVISION_LOCKS_GUARD = Lock()
_REVISION_LOCKS: dict[tuple[str, UUID], RLock] = {}


def _revision_lock(kind: str, identity: UUID) -> RLock:
    key = (kind, identity)
    with _REVISION_LOCKS_GUARD:
        return _REVISION_LOCKS.setdefault(key, RLock())


@dataclass(frozen=True)
class EvidenceLinkInput:
    evidence_id: UUID
    relation: str
    link_note: str | None = None


@dataclass(frozen=True)
class CaseClaimInput:
    claim_revision_id: UUID
    role: str


@dataclass(frozen=True)
class VerificationInput:
    description: str
    status: str = "open"
    due_date: date | None = None


class EvidenceLedgerCommandService:
    """Run each accepted ledger mutation as one database transaction."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_case(
        self,
        *,
        case_key: str,
        title: str,
        research_question: str,
        information_cutoff_date: date,
        summary: str | None = None,
        workflow_state: str = "open",
        conclusion_status: str = "unassessed",
        origin: str = "manual",
        recorded_at_utc: datetime | None = None,
        verification_items: tuple[VerificationInput, ...] = (),
    ) -> ResearchCase:
        case_key = required_text(case_key, "case_key")
        origin = reviewed_value(origin, "origin", ORIGINS)
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        with self._translate_integrity("case_key already exists"):
            with self._session_factory.begin() as session:
                case = ResearchCase(case_key=case_key, created_at_utc=recorded, origin=origin)
                session.add(case)
                session.flush()
                self._insert_case_revision(
                    session,
                    case=case,
                    title=title,
                    research_question=research_question,
                    summary=summary,
                    workflow_state=workflow_state,
                    conclusion_status=conclusion_status,
                    information_cutoff_date=information_cutoff_date,
                    recorded_at_utc=recorded,
                    claim_links=(),
                    verification_items=verification_items,
                )
            return case

    def append_case_revision(
        self,
        case_id: UUID,
        *,
        title: str,
        research_question: str,
        information_cutoff_date: date,
        summary: str | None = None,
        workflow_state: str = "open",
        conclusion_status: str = "unassessed",
        claim_links: tuple[CaseClaimInput, ...] = (),
        verification_items: tuple[VerificationInput, ...] = (),
        recorded_at_utc: datetime | None = None,
    ) -> ResearchCaseRevision:
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        with _revision_lock("case", case_id):
            with self._translate_integrity("case revision conflicts with accepted history"):
                with self._session_factory.begin() as session:
                    case = self._locked_case(session, case_id)
                    revision = self._insert_case_revision(
                        session,
                        case=case,
                        title=title,
                        research_question=research_question,
                        summary=summary,
                        workflow_state=workflow_state,
                        conclusion_status=conclusion_status,
                        information_cutoff_date=information_cutoff_date,
                        recorded_at_utc=recorded,
                        claim_links=claim_links,
                        verification_items=verification_items,
                    )
            return revision

    def add_evidence(
        self,
        case_id: UUID,
        *,
        evidence_grade: str,
        source_kind: str,
        source_title: str,
        information_date: date,
        summary: str,
        publisher_or_author: str | None = None,
        source_locator: str | None = None,
        content_fingerprint: str | None = None,
        supersedes_evidence_id: UUID | None = None,
        recorded_at_utc: datetime | None = None,
    ) -> EvidenceItem:
        grade = reviewed_value(evidence_grade, "evidence_grade", EVIDENCE_GRADES)
        kind = reviewed_value(source_kind, "source_kind", SOURCE_KINDS)
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_date, recorded)
        with self._translate_integrity("evidence fingerprint already exists in this case"):
            with self._session_factory.begin() as session:
                case = self._require_case(session, case_id)
                validate_utc_chronology(
                    recorded, ("case creation timestamp", _stored_utc(case.created_at_utc))
                )
                if supersedes_evidence_id is not None:
                    previous = session.get(EvidenceItem, supersedes_evidence_id)
                    if previous is None or previous.case_id != case_id:
                        raise EvidenceLedgerValidationError(
                            "supersedes_evidence_id must identify evidence in the same case."
                        )
                    validate_utc_chronology(
                        recorded,
                        ("superseded evidence timestamp", _stored_utc(previous.recorded_at_utc)),
                    )
                item = EvidenceItem(
                    case_id=case_id,
                    evidence_grade=grade,
                    source_kind=kind,
                    source_title=required_text(source_title, "source_title"),
                    publisher_or_author=optional_text(publisher_or_author, "publisher_or_author"),
                    source_locator=optional_text(source_locator, "source_locator"),
                    information_date=information_date,
                    recorded_at_utc=recorded,
                    summary=required_text(summary, "summary"),
                    content_fingerprint=optional_text(content_fingerprint, "content_fingerprint"),
                    supersedes_evidence_id=supersedes_evidence_id,
                )
                session.add(item)
                session.flush()
            return item

    def create_claim(
        self,
        case_id: UUID,
        *,
        claim_key: str,
        statement: str,
        claim_kind: str,
        claim_status: str,
        information_cutoff_date: date,
        inference_confidence: str | None = None,
        inference_basis: str | None = None,
        evidence_links: tuple[EvidenceLinkInput, ...] = (),
        recorded_at_utc: datetime | None = None,
    ) -> Claim:
        key = required_text(claim_key, "claim_key")
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        with self._translate_integrity("claim_key already exists in this case"):
            with self._session_factory.begin() as session:
                case = self._require_case(session, case_id)
                validate_utc_chronology(
                    recorded, ("case creation timestamp", _stored_utc(case.created_at_utc))
                )
                claim = Claim(case_id=case_id, claim_key=key, created_at_utc=recorded)
                session.add(claim)
                session.flush()
                self._insert_claim_revision(
                    session,
                    claim=claim,
                    statement=statement,
                    claim_kind=claim_kind,
                    claim_status=claim_status,
                    information_cutoff_date=information_cutoff_date,
                    inference_confidence=inference_confidence,
                    inference_basis=inference_basis,
                    evidence_links=evidence_links,
                    recorded_at_utc=recorded,
                )
            return claim

    def append_claim_revision(
        self,
        claim_id: UUID,
        *,
        statement: str,
        claim_kind: str,
        claim_status: str,
        information_cutoff_date: date,
        inference_confidence: str | None = None,
        inference_basis: str | None = None,
        evidence_links: tuple[EvidenceLinkInput, ...] = (),
        recorded_at_utc: datetime | None = None,
    ) -> ClaimRevision:
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        with _revision_lock("claim", claim_id):
            with self._translate_integrity("claim revision conflicts with accepted history"):
                with self._session_factory.begin() as session:
                    claim = self._locked_claim(session, claim_id)
                    revision = self._insert_claim_revision(
                        session,
                        claim=claim,
                        statement=statement,
                        claim_kind=claim_kind,
                        claim_status=claim_status,
                        information_cutoff_date=information_cutoff_date,
                        inference_confidence=inference_confidence,
                        inference_basis=inference_basis,
                        evidence_links=evidence_links,
                        recorded_at_utc=recorded,
                    )
            return revision

    def link_evidence(
        self,
        claim_revision_id: UUID,
        evidence_id: UUID,
        *,
        relation: str,
        link_note: str | None = None,
        recorded_at_utc: datetime | None = None,
    ) -> ClaimEvidenceLink:
        relation = reviewed_value(relation, "relation", EVIDENCE_RELATIONS)
        recorded = utc_timestamp(recorded_at_utc)
        with self._translate_integrity("claim/evidence relation already exists"):
            with self._session_factory.begin() as session:
                revision, evidence = self._same_case_endpoints(
                    session, claim_revision_id, evidence_id
                )
                if evidence.information_date > revision.information_cutoff_date:
                    raise EvidenceLedgerValidationError(
                        "linked evidence information_date exceeds the claim revision cutoff."
                    )
                validate_utc_chronology(
                    recorded,
                    ("claim revision timestamp", _stored_utc(revision.recorded_at_utc)),
                    ("evidence timestamp", _stored_utc(evidence.recorded_at_utc)),
                )
                existing = list(
                    session.scalars(
                        select(ClaimEvidenceLink).where(
                            ClaimEvidenceLink.claim_revision_id == claim_revision_id
                        )
                    )
                )
                candidate = EvidenceLinkInput(evidence_id, relation, link_note)
                self._validate_claim_status_links(
                    revision.claim_status,
                    [(link.relation, session.get(EvidenceItem, link.evidence_id)) for link in existing]
                    + [(candidate.relation, evidence)],
                )
                link = ClaimEvidenceLink(
                    claim_revision_id=claim_revision_id,
                    evidence_id=evidence_id,
                    relation=relation,
                    link_note=optional_text(link_note, "link_note"),
                    recorded_at_utc=recorded,
                )
                session.add(link)
                session.flush()
            return link

    def add_verification_item(
        self,
        case_revision_id: UUID,
        *,
        description: str,
        status: str = "open",
        due_date: date | None = None,
        recorded_at_utc: datetime | None = None,
    ) -> VerificationItem:
        """Append one checklist item without modifying the frozen case revision."""
        recorded = utc_timestamp(recorded_at_utc)
        with _revision_lock("verification", case_revision_id):
            with self._translate_integrity(
                "verification item number conflicts with accepted history"
            ):
                with self._session_factory.begin() as session:
                    case_revision = session.scalar(
                        select(ResearchCaseRevision)
                        .where(ResearchCaseRevision.id == case_revision_id)
                        .with_for_update()
                    )
                    if case_revision is None:
                        raise EvidenceLedgerNotFound(
                            f"Case revision {case_revision_id} was not found."
                        )
                    latest_item = session.scalar(
                        select(VerificationItem)
                        .where(VerificationItem.case_revision_id == case_revision_id)
                        .order_by(VerificationItem.item_no.desc())
                        .limit(1)
                    )
                    chronology = [
                        ("case revision timestamp", _stored_utc(case_revision.recorded_at_utc))
                    ]
                    if latest_item is not None:
                        chronology.append(
                            ("latest verification item timestamp", _stored_utc(latest_item.recorded_at_utc))
                        )
                    validate_utc_chronology(recorded, *chronology)
                    latest_no = session.scalar(
                        select(func.max(VerificationItem.item_no)).where(
                            VerificationItem.case_revision_id == case_revision_id
                        )
                    )
                    item = VerificationItem(
                        case_revision_id=case_revision_id,
                        item_no=(latest_no or 0) + 1,
                        description=required_text(description, "description"),
                        status=reviewed_value(
                            status, "status", VERIFICATION_STATUSES
                        ),
                        due_date=due_date,
                        recorded_at_utc=recorded,
                    )
                    session.add(item)
                    session.flush()
            return item

    def _insert_case_revision(
        self,
        session: Session,
        *,
        case: ResearchCase,
        title: str,
        research_question: str,
        summary: str | None,
        workflow_state: str,
        conclusion_status: str,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
        claim_links: tuple[CaseClaimInput, ...],
        verification_items: tuple[VerificationInput, ...],
    ) -> ResearchCaseRevision:
        workflow = reviewed_value(workflow_state, "workflow_state", WORKFLOW_STATES)
        conclusion = reviewed_value(
            conclusion_status, "conclusion_status", CONCLUSION_STATUSES
        )
        if workflow == "completed" and not verification_items:
            raise EvidenceLedgerValidationError(
                "completed case revisions require at least one 后续验证清单 item."
            )
        prior = session.scalar(
            select(ResearchCaseRevision)
            .where(ResearchCaseRevision.case_id == case.id)
            .order_by(ResearchCaseRevision.revision_no.desc())
            .limit(1)
        )
        chronology = [("case creation timestamp", _stored_utc(case.created_at_utc))]
        if prior is not None:
            chronology.append(
                ("previous case revision timestamp", _stored_utc(prior.recorded_at_utc))
            )
        validate_utc_chronology(recorded_at_utc, *chronology)
        memberships: list[tuple[str, ClaimRevision]] = []
        for spec in claim_links:
            role = reviewed_value(spec.role, "role", CLAIM_ROLES)
            claim_revision = session.get(ClaimRevision, spec.claim_revision_id)
            if claim_revision is None:
                raise EvidenceLedgerNotFound(f"Claim revision {spec.claim_revision_id} was not found.")
            claim = session.get(Claim, claim_revision.claim_id)
            if claim is None or claim.case_id != case.id:
                raise EvidenceLedgerValidationError(
                    "case revision and linked claim revision must belong to the same case."
                )
            if claim_revision.information_cutoff_date > information_cutoff_date:
                raise EvidenceLedgerValidationError(
                    "linked claim revision cutoff exceeds the case revision cutoff."
                )
            validate_utc_chronology(
                recorded_at_utc,
                ("linked claim revision timestamp", _stored_utc(claim_revision.recorded_at_utc)),
            )
            memberships.append((role, claim_revision))
        self._validate_case_conclusion(
            session, conclusion, memberships, recorded_at_utc=recorded_at_utc
        )
        revision = ResearchCaseRevision(
            case_id=case.id,
            revision_no=1 if prior is None else prior.revision_no + 1,
            title=required_text(title, "title"),
            research_question=required_text(research_question, "research_question"),
            summary=optional_text(summary, "summary"),
            workflow_state=workflow,
            conclusion_status=conclusion,
            information_cutoff_date=information_cutoff_date,
            recorded_at_utc=recorded_at_utc,
            supersedes_revision_id=None if prior is None else prior.id,
        )
        session.add(revision)
        session.flush()
        for role, claim_revision in memberships:
            session.add(
                CaseRevisionClaimLink(
                    case_revision_id=revision.id,
                    claim_revision_id=claim_revision.id,
                    role=role,
                    recorded_at_utc=recorded_at_utc,
                )
            )
        for item_no, spec in enumerate(verification_items, start=1):
            session.add(
                VerificationItem(
                    case_revision_id=revision.id,
                    item_no=item_no,
                    description=required_text(spec.description, "description"),
                    status=reviewed_value(spec.status, "status", VERIFICATION_STATUSES),
                    due_date=spec.due_date,
                    recorded_at_utc=recorded_at_utc,
                )
            )
        session.flush()
        return revision

    def _insert_claim_revision(
        self,
        session: Session,
        *,
        claim: Claim,
        statement: str,
        claim_kind: str,
        claim_status: str,
        information_cutoff_date: date,
        inference_confidence: str | None,
        inference_basis: str | None,
        evidence_links: tuple[EvidenceLinkInput, ...],
        recorded_at_utc: datetime,
    ) -> ClaimRevision:
        kind = reviewed_value(claim_kind, "claim_kind", CLAIM_KINDS)
        status = reviewed_value(claim_status, "claim_status", CLAIM_STATUSES)
        confidence, basis = validate_claim_fields(kind, inference_confidence, inference_basis)
        prior = session.scalar(
            select(ClaimRevision)
            .where(ClaimRevision.claim_id == claim.id)
            .order_by(ClaimRevision.revision_no.desc())
            .limit(1)
        )
        case = session.get(ResearchCase, claim.case_id)
        if case is None:
            raise EvidenceLedgerNotFound(f"Research case {claim.case_id} was not found.")
        chronology = [
            ("case creation timestamp", _stored_utc(case.created_at_utc)),
            ("claim creation timestamp", _stored_utc(claim.created_at_utc)),
        ]
        if prior is not None:
            chronology.append(
                ("previous claim revision timestamp", _stored_utc(prior.recorded_at_utc))
            )
        validate_utc_chronology(recorded_at_utc, *chronology)
        resolved: list[tuple[EvidenceLinkInput, EvidenceItem]] = []
        seen: set[tuple[UUID, str]] = set()
        for spec in evidence_links:
            relation = reviewed_value(spec.relation, "relation", EVIDENCE_RELATIONS)
            evidence = session.get(EvidenceItem, spec.evidence_id)
            if evidence is None:
                raise EvidenceLedgerNotFound(f"Evidence {spec.evidence_id} was not found.")
            if evidence.case_id != claim.case_id:
                raise EvidenceLedgerValidationError(
                    "claim revision and evidence must belong to the same case."
                )
            validate_utc_chronology(
                recorded_at_utc,
                ("linked evidence timestamp", _stored_utc(evidence.recorded_at_utc)),
            )
            key = (evidence.id, relation)
            if key in seen:
                raise EvidenceLedgerValidationError("duplicate claim/evidence relation in command.")
            seen.add(key)
            resolved.append((EvidenceLinkInput(evidence.id, relation, spec.link_note), evidence))
        self._validate_claim_status_links(status, [(spec.relation, item) for spec, item in resolved])
        revision = ClaimRevision(
            claim_id=claim.id,
            revision_no=1 if prior is None else prior.revision_no + 1,
            statement=required_text(statement, "statement"),
            claim_kind=kind,
            claim_status=status,
            inference_confidence=confidence,
            inference_basis=basis,
            information_cutoff_date=information_cutoff_date,
            recorded_at_utc=recorded_at_utc,
            supersedes_revision_id=None if prior is None else prior.id,
        )
        session.add(revision)
        session.flush()
        for spec, evidence in resolved:
            if evidence.information_date > information_cutoff_date:
                raise EvidenceLedgerValidationError(
                    "linked evidence information_date exceeds the claim revision cutoff."
                )
            session.add(
                ClaimEvidenceLink(
                    claim_revision_id=revision.id,
                    evidence_id=evidence.id,
                    relation=spec.relation,
                    link_note=optional_text(spec.link_note, "link_note"),
                    recorded_at_utc=recorded_at_utc,
                )
            )
        session.flush()
        return revision

    @staticmethod
    def _validate_claim_status_links(
        status: str, relations: list[tuple[str, EvidenceItem | None]]
    ) -> None:
        supports = [item for relation, item in relations if relation == "supports" and item is not None]
        contradictions = [item for relation, item in relations if relation == "contradicts" and item is not None]
        if status == "supported":
            if contradictions:
                raise EvidenceLedgerValidationError(
                    "supported claim revisions cannot contain contradictory evidence."
                )
            if not any(item.evidence_grade in {"A", "B", "C"} for item in supports):
                raise EvidenceLedgerValidationError(
                    "supported claim revisions require A/B/C supporting evidence; D-only support is insufficient."
                )
        if status == "disputed" and not contradictions:
            raise EvidenceLedgerValidationError(
                "disputed claim revisions require contradictory evidence."
            )

    @staticmethod
    def _validate_case_conclusion(
        session: Session,
        conclusion: str,
        memberships: list[tuple[str, ClaimRevision]],
        *,
        recorded_at_utc: datetime,
    ) -> None:
        conclusion_claims = [revision for role, revision in memberships if role == "conclusion"]
        if conclusion == "supported":
            if not conclusion_claims:
                raise EvidenceLedgerValidationError(
                    "supported case conclusions require at least one conclusion claim."
                )
            for revision in conclusion_claims:
                links = list(
                    session.scalars(
                        select(ClaimEvidenceLink).where(
                            ClaimEvidenceLink.claim_revision_id == revision.id
                        )
                    )
                )
                evidence = [session.get(EvidenceItem, link.evidence_id) for link in links]
                visible_pairs = [
                    (link, item)
                    for link, item in zip(links, evidence, strict=True)
                    if item is not None
                    and _stored_utc(link.recorded_at_utc) <= recorded_at_utc
                    and _stored_utc(item.recorded_at_utc) <= recorded_at_utc
                ]
                if revision.claim_status != "supported":
                    raise EvidenceLedgerValidationError(
                        "every supported conclusion membership must freeze a supported claim revision."
                    )
                if any(link.relation == "contradicts" for link, _item in visible_pairs):
                    raise EvidenceLedgerValidationError(
                        "supported case conclusions cannot freeze contradictory conclusion claims."
                    )
                if not any(
                    link.relation == "supports" and item is not None and item.evidence_grade in {"A", "B", "C"}
                    for link, item in visible_pairs
                ):
                    raise EvidenceLedgerValidationError(
                        "supported conclusion claims require A/B/C supporting evidence."
                    )
        if conclusion == "disputed":
            if not conclusion_claims:
                raise EvidenceLedgerValidationError(
                    "disputed case conclusions require at least one conclusion claim."
                )
            valid = False
            for revision in conclusion_claims:
                conflict_links = list(
                    session.scalars(
                        select(ClaimEvidenceLink).where(
                            ClaimEvidenceLink.claim_revision_id == revision.id,
                            ClaimEvidenceLink.relation == "contradicts",
                        )
                    )
                )
                has_visible_conflict = any(
                    _stored_utc(link.recorded_at_utc) <= recorded_at_utc
                    and (item := session.get(EvidenceItem, link.evidence_id)) is not None
                    and _stored_utc(item.recorded_at_utc) <= recorded_at_utc
                    for link in conflict_links
                )
                valid = valid or has_visible_conflict
            if not valid:
                raise EvidenceLedgerValidationError(
                    "disputed case conclusions require a disputed or contradicted conclusion claim."
                )

    @staticmethod
    def _locked_case(session: Session, case_id: UUID) -> ResearchCase:
        case = session.scalar(
            select(ResearchCase).where(ResearchCase.id == case_id).with_for_update()
        )
        if case is None:
            raise EvidenceLedgerNotFound(f"Research case {case_id} was not found.")
        return case

    @staticmethod
    def _locked_claim(session: Session, claim_id: UUID) -> Claim:
        claim = session.scalar(select(Claim).where(Claim.id == claim_id).with_for_update())
        if claim is None:
            raise EvidenceLedgerNotFound(f"Claim {claim_id} was not found.")
        return claim

    @staticmethod
    def _require_case(session: Session, case_id: UUID) -> ResearchCase:
        case = session.get(ResearchCase, case_id)
        if case is None:
            raise EvidenceLedgerNotFound(f"Research case {case_id} was not found.")
        return case

    @staticmethod
    def _same_case_endpoints(
        session: Session, claim_revision_id: UUID, evidence_id: UUID
    ) -> tuple[ClaimRevision, EvidenceItem]:
        revision = session.get(ClaimRevision, claim_revision_id)
        evidence = session.get(EvidenceItem, evidence_id)
        if revision is None or evidence is None:
            raise EvidenceLedgerNotFound("claim revision or evidence was not found.")
        claim = session.get(Claim, revision.claim_id)
        if claim is None or claim.case_id != evidence.case_id:
            raise EvidenceLedgerValidationError(
                "claim revision and evidence must belong to the same case."
            )
        return revision, evidence

    class _IntegrityTranslation:
        def __init__(self, message: str) -> None:
            self.message = message

        def __enter__(self) -> None:
            return None

        def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, _tb: object) -> bool:
            if isinstance(exc, IntegrityError):
                raise EvidenceLedgerConflictError(self.message) from exc
            return False

    @classmethod
    def _translate_integrity(cls, message: str) -> _IntegrityTranslation:
        return cls._IntegrityTranslation(message)


def _stored_utc(value: datetime) -> datetime:
    """Restore UTC tzinfo lost by SQLite while keeping comparisons aware."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
