"""Transactional commands for append-only evidence-backed chain maps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from threading import Lock, RLock
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.chain_map_models import (
    IndustryMap,
    IndustryMapAssertionClaimLink,
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
from industry_alpha.validation import (
    utc_timestamp,
    validate_recorded_cutoff,
    validate_utc_chronology,
)

ASSERTION_STATUSES = frozenset({"draft", "supported", "disputed", "rejected"})
NODE_KINDS = frozenset(
    {
        "upstream_input",
        "equipment",
        "component",
        "manufacturing",
        "distribution",
        "service",
        "customer_end_market",
        "regulation_infrastructure",
        "other",
    }
)
RELATION_KINDS = frozenset(
    {
        "supplies",
        "enables",
        "depends_on",
        "substitutes",
        "competes_with",
        "distributes_to",
        "regulates",
        "other",
    }
)
OBSERVATION_KINDS = frozenset({"driver", "bottleneck", "value_pool_shift"})

_LOCKS_GUARD = Lock()
_LOCKS: dict[tuple[str, UUID], RLock] = {}


def _revision_lock(kind: str, identity: UUID) -> RLock:
    key = (kind, identity)
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, RLock())


@dataclass(frozen=True)
class ClaimRevisionInput:
    claim_revision_id: UUID


@dataclass(frozen=True)
class _AssertionRef:
    kind: str
    revision: Any
    map_id: UUID
    status: str
    information_cutoff_date: date
    recorded_at_utc: datetime


class IndustryChainMapCommandService:
    """Create only new map identities, revisions, links, and memberships."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_map(
        self,
        case_id: UUID,
        *,
        map_key: str,
        title: str,
        scope: str,
        information_cutoff_date: date,
        recorded_at_utc: datetime | None = None,
    ) -> IndustryMap:
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        key = _required_text(map_key, "map_key", 96)
        with self._translate_integrity("map_key already exists in this research case"):
            with self._session_factory.begin() as session:
                case = session.get(ResearchCase, case_id)
                if case is None:
                    raise EvidenceLedgerNotFound(
                        f"Research case {case_id} was not found."
                    )
                validate_utc_chronology(
                    recorded,
                    ("research case creation timestamp", _stored_utc(case.created_at_utc)),
                )
                industry_map = IndustryMap(
                    case_id=case_id,
                    map_key=key,
                    created_at_utc=recorded,
                )
                session.add(industry_map)
                session.flush()
                self._insert_map_revision(
                    session,
                    industry_map=industry_map,
                    title=title,
                    scope=scope,
                    information_cutoff_date=information_cutoff_date,
                    recorded_at_utc=recorded,
                    node_revision_ids=(),
                    relationship_revision_ids=(),
                    observation_revision_ids=(),
                )
            return industry_map

    def append_map_revision(
        self,
        map_id: UUID,
        *,
        title: str,
        scope: str,
        information_cutoff_date: date,
        node_revision_ids: tuple[UUID, ...] = (),
        relationship_revision_ids: tuple[UUID, ...] = (),
        observation_revision_ids: tuple[UUID, ...] = (),
        recorded_at_utc: datetime | None = None,
    ) -> IndustryMapRevision:
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        with _revision_lock("map", map_id):
            with self._translate_integrity(
                "map revision conflicts with accepted history"
            ):
                with self._session_factory.begin() as session:
                    industry_map = self._locked_map(session, map_id)
                    revision = self._insert_map_revision(
                        session,
                        industry_map=industry_map,
                        title=title,
                        scope=scope,
                        information_cutoff_date=information_cutoff_date,
                        recorded_at_utc=recorded,
                        node_revision_ids=node_revision_ids,
                        relationship_revision_ids=relationship_revision_ids,
                        observation_revision_ids=observation_revision_ids,
                    )
            return revision

    def create_node(
        self,
        map_id: UUID,
        *,
        node_key: str,
        label: str,
        node_kind: str,
        assertion_status: str,
        information_cutoff_date: date,
        claim_revision_ids: tuple[UUID, ...],
        description: str | None = None,
        recorded_at_utc: datetime | None = None,
    ) -> IndustryMapNode:
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        key = _required_text(node_key, "node_key", 96)
        with self._translate_integrity("node_key already exists in this map"):
            with self._session_factory.begin() as session:
                industry_map = self._require_map(session, map_id)
                validate_utc_chronology(
                    recorded,
                    ("industry map creation timestamp", _stored_utc(industry_map.created_at_utc)),
                )
                node = IndustryMapNode(
                    map_id=map_id, node_key=key, created_at_utc=recorded
                )
                session.add(node)
                session.flush()
                self._insert_node_revision(
                    session,
                    node=node,
                    label=label,
                    description=description,
                    node_kind=node_kind,
                    assertion_status=assertion_status,
                    information_cutoff_date=information_cutoff_date,
                    claim_revision_ids=claim_revision_ids,
                    recorded_at_utc=recorded,
                )
            return node

    def append_node_revision(
        self,
        node_id: UUID,
        *,
        label: str,
        node_kind: str,
        assertion_status: str,
        information_cutoff_date: date,
        claim_revision_ids: tuple[UUID, ...],
        description: str | None = None,
        recorded_at_utc: datetime | None = None,
    ) -> IndustryMapNodeRevision:
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        with _revision_lock("node", node_id):
            with self._translate_integrity(
                "node revision conflicts with accepted history"
            ):
                with self._session_factory.begin() as session:
                    node = self._locked_node(session, node_id)
                    revision = self._insert_node_revision(
                        session,
                        node=node,
                        label=label,
                        description=description,
                        node_kind=node_kind,
                        assertion_status=assertion_status,
                        information_cutoff_date=information_cutoff_date,
                        claim_revision_ids=claim_revision_ids,
                        recorded_at_utc=recorded,
                    )
            return revision

    def create_relationship(
        self,
        map_id: UUID,
        *,
        relationship_key: str,
        source_node_id: UUID,
        target_node_id: UUID,
        relation_kind: str,
        assertion_status: str,
        information_cutoff_date: date,
        claim_revision_ids: tuple[UUID, ...],
        description: str | None = None,
        recorded_at_utc: datetime | None = None,
    ) -> IndustryMapRelationship:
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        key = _required_text(relationship_key, "relationship_key", 96)
        if source_node_id == target_node_id:
            raise EvidenceLedgerValidationError(
                "source_node_id and target_node_id must be different."
            )
        with self._translate_integrity(
            "relationship_key already exists in this map"
        ):
            with self._session_factory.begin() as session:
                industry_map = self._require_map(session, map_id)
                source = session.get(IndustryMapNode, source_node_id)
                target = session.get(IndustryMapNode, target_node_id)
                if source is None or target is None:
                    raise EvidenceLedgerNotFound(
                        "source or target industry-map node was not found."
                    )
                if source.map_id != map_id or target.map_id != map_id:
                    raise EvidenceLedgerValidationError(
                        "relationship endpoints must belong to the same industry map."
                    )
                validate_utc_chronology(
                    recorded,
                    ("industry map creation timestamp", _stored_utc(industry_map.created_at_utc)),
                    ("source node creation timestamp", _stored_utc(source.created_at_utc)),
                    ("target node creation timestamp", _stored_utc(target.created_at_utc)),
                )
                relationship = IndustryMapRelationship(
                    map_id=map_id,
                    relationship_key=key,
                    source_node_id=source_node_id,
                    target_node_id=target_node_id,
                    created_at_utc=recorded,
                )
                session.add(relationship)
                session.flush()
                self._insert_relationship_revision(
                    session,
                    relationship=relationship,
                    relation_kind=relation_kind,
                    description=description,
                    assertion_status=assertion_status,
                    information_cutoff_date=information_cutoff_date,
                    claim_revision_ids=claim_revision_ids,
                    recorded_at_utc=recorded,
                )
            return relationship

    def append_relationship_revision(
        self,
        relationship_id: UUID,
        *,
        relation_kind: str,
        assertion_status: str,
        information_cutoff_date: date,
        claim_revision_ids: tuple[UUID, ...],
        description: str | None = None,
        recorded_at_utc: datetime | None = None,
    ) -> IndustryMapRelationshipRevision:
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        with _revision_lock("relationship", relationship_id):
            with self._translate_integrity(
                "relationship revision conflicts with accepted history"
            ):
                with self._session_factory.begin() as session:
                    relationship = self._locked_relationship(session, relationship_id)
                    revision = self._insert_relationship_revision(
                        session,
                        relationship=relationship,
                        relation_kind=relation_kind,
                        description=description,
                        assertion_status=assertion_status,
                        information_cutoff_date=information_cutoff_date,
                        claim_revision_ids=claim_revision_ids,
                        recorded_at_utc=recorded,
                    )
            return revision

    def create_observation(
        self,
        map_id: UUID,
        *,
        observation_key: str,
        observation_kind: str,
        title: str,
        assertion_status: str,
        information_cutoff_date: date,
        claim_revision_ids: tuple[UUID, ...],
        description: str | None = None,
        recorded_at_utc: datetime | None = None,
    ) -> IndustryMapObservation:
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        key = _required_text(observation_key, "observation_key", 96)
        kind = _reviewed_value(
            observation_kind, "observation_kind", OBSERVATION_KINDS
        )
        with self._translate_integrity(
            "observation_key already exists in this map"
        ):
            with self._session_factory.begin() as session:
                industry_map = self._require_map(session, map_id)
                validate_utc_chronology(
                    recorded,
                    ("industry map creation timestamp", _stored_utc(industry_map.created_at_utc)),
                )
                observation = IndustryMapObservation(
                    map_id=map_id,
                    observation_key=key,
                    observation_kind=kind,
                    created_at_utc=recorded,
                )
                session.add(observation)
                session.flush()
                self._insert_observation_revision(
                    session,
                    observation=observation,
                    title=title,
                    description=description,
                    assertion_status=assertion_status,
                    information_cutoff_date=information_cutoff_date,
                    claim_revision_ids=claim_revision_ids,
                    recorded_at_utc=recorded,
                )
            return observation

    def append_observation_revision(
        self,
        observation_id: UUID,
        *,
        title: str,
        assertion_status: str,
        information_cutoff_date: date,
        claim_revision_ids: tuple[UUID, ...],
        description: str | None = None,
        recorded_at_utc: datetime | None = None,
    ) -> IndustryMapObservationRevision:
        recorded = utc_timestamp(recorded_at_utc)
        validate_recorded_cutoff(information_cutoff_date, recorded)
        with _revision_lock("observation", observation_id):
            with self._translate_integrity(
                "observation revision conflicts with accepted history"
            ):
                with self._session_factory.begin() as session:
                    observation = self._locked_observation(session, observation_id)
                    revision = self._insert_observation_revision(
                        session,
                        observation=observation,
                        title=title,
                        description=description,
                        assertion_status=assertion_status,
                        information_cutoff_date=information_cutoff_date,
                        claim_revision_ids=claim_revision_ids,
                        recorded_at_utc=recorded,
                    )
            return revision

    def link_claim_revision(
        self,
        assertion_kind: str,
        assertion_revision_id: UUID,
        claim_revision_id: UUID,
        *,
        recorded_at_utc: datetime | None = None,
    ) -> IndustryMapAssertionClaimLink:
        recorded = utc_timestamp(recorded_at_utc)
        with self._translate_integrity(
            "assertion and claim revision are already linked"
        ):
            with self._session_factory.begin() as session:
                assertion = self._assertion_ref(
                    session, assertion_kind, assertion_revision_id, for_update=True
                )
                industry_map = self._require_map(session, assertion.map_id)
                _validate_post_freeze_timestamp(session, assertion, recorded)
                existing_links = self._claim_links_for_ref(session, assertion)
                if existing_links:
                    validate_utc_chronology(
                        recorded,
                        (
                            "latest assertion claim-link timestamp",
                            max(_stored_utc(link.recorded_at_utc) for link in existing_links),
                        ),
                    )
                claim_revision = self._resolve_claim_revision(
                    session,
                    industry_map,
                    claim_revision_id,
                    assertion.information_cutoff_date,
                    recorded,
                )
                validate_utc_chronology(
                    recorded,
                    ("assertion revision timestamp", assertion.recorded_at_utc),
                    ("claim revision timestamp", _stored_utc(claim_revision.recorded_at_utc)),
                )
                linked = self._linked_claim_revisions(session, assertion)
                if any(item.claim_id == claim_revision.claim_id for item in linked):
                    raise EvidenceLedgerValidationError(
                        "an assertion cannot bind multiple revisions of the same claim identity."
                    )
                self._validate_assertion_status(
                    session,
                    assertion.status,
                    [*linked, claim_revision],
                    recorded,
                )
                link = self._claim_link(assertion, claim_revision_id, recorded)
                session.add(link)
                session.flush()
            return link

    def _insert_map_revision(
        self,
        session: Session,
        *,
        industry_map: IndustryMap,
        title: str,
        scope: str,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
        node_revision_ids: tuple[UUID, ...],
        relationship_revision_ids: tuple[UUID, ...],
        observation_revision_ids: tuple[UUID, ...],
    ) -> IndustryMapRevision:
        prior = session.scalar(
            select(IndustryMapRevision)
            .where(IndustryMapRevision.map_id == industry_map.id)
            .order_by(IndustryMapRevision.revision_no.desc())
            .limit(1)
        )
        chronology = [
            ("industry map creation timestamp", _stored_utc(industry_map.created_at_utc))
        ]
        if prior is not None:
            chronology.append(
                ("previous map revision timestamp", _stored_utc(prior.recorded_at_utc))
            )
        validate_utc_chronology(recorded_at_utc, *chronology)
        node_refs = self._membership_refs(
            session, "node", node_revision_ids, industry_map.id
        )
        relationship_refs = self._membership_refs(
            session,
            "relationship",
            relationship_revision_ids,
            industry_map.id,
        )
        observation_refs = self._membership_refs(
            session,
            "observation",
            observation_revision_ids,
            industry_map.id,
        )
        node_ids = {ref.revision.node_id for ref in node_refs}
        for ref in relationship_refs:
            relationship = session.get(
                IndustryMapRelationship, ref.revision.relationship_id
            )
            if relationship is None:
                raise EvidenceLedgerNotFound("relationship identity was not found.")
            if not {relationship.source_node_id, relationship.target_node_id} <= node_ids:
                raise EvidenceLedgerValidationError(
                    "frozen relationships require exact source and target node revisions."
                )
        for ref in [*node_refs, *relationship_refs, *observation_refs]:
            if ref.information_cutoff_date > information_cutoff_date:
                raise EvidenceLedgerValidationError(
                    "assertion revision cutoff exceeds the map revision cutoff."
                )
            validate_utc_chronology(
                recorded_at_utc,
                ("frozen assertion revision timestamp", ref.recorded_at_utc),
            )
            claims = self._linked_claim_revisions(session, ref, for_update=True)
            self._validate_assertion_status(
                session, ref.status, claims, recorded_at_utc
            )
            for link in self._claim_links_for_ref(session, ref):
                validate_utc_chronology(
                    recorded_at_utc,
                    ("assertion claim-link timestamp", _stored_utc(link.recorded_at_utc)),
                )
        revision = IndustryMapRevision(
            map_id=industry_map.id,
            revision_no=1 if prior is None else prior.revision_no + 1,
            title=_required_text(title, "title", 300),
            scope=_required_text(scope, "scope", 4000),
            information_cutoff_date=information_cutoff_date,
            recorded_at_utc=recorded_at_utc,
            supersedes_revision_id=None if prior is None else prior.id,
        )
        session.add(revision)
        session.flush()
        for ref in [*node_refs, *relationship_refs, *observation_refs]:
            membership = IndustryMapRevisionMembership(
                map_revision_id=revision.id,
                recorded_at_utc=recorded_at_utc,
            )
            setattr(membership, f"{ref.kind}_revision_id", ref.revision.id)
            session.add(membership)
        session.flush()
        return revision

    def _insert_node_revision(
        self,
        session: Session,
        *,
        node: IndustryMapNode,
        label: str,
        description: str | None,
        node_kind: str,
        assertion_status: str,
        information_cutoff_date: date,
        claim_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime,
    ) -> IndustryMapNodeRevision:
        prior = self._latest_revision(
            session, IndustryMapNodeRevision, "node_id", node.id
        )
        validate_utc_chronology(
            recorded_at_utc,
            ("node identity timestamp", _stored_utc(node.created_at_utc)),
            *(() if prior is None else (("previous node revision timestamp", _stored_utc(prior.recorded_at_utc)),)),
        )
        status = _reviewed_value(
            assertion_status, "assertion_status", ASSERTION_STATUSES
        )
        kind = _reviewed_value(node_kind, "node_kind", NODE_KINDS)
        industry_map = self._require_map(session, node.map_id)
        claims = self._resolve_claim_revisions(
            session,
            industry_map,
            claim_revision_ids,
            information_cutoff_date,
            recorded_at_utc,
        )
        self._validate_assertion_status(session, status, claims, recorded_at_utc)
        revision = IndustryMapNodeRevision(
            node_id=node.id,
            revision_no=1 if prior is None else prior.revision_no + 1,
            label=_required_text(label, "label", 300),
            description=_optional_text(description, "description", 4000),
            node_kind=kind,
            assertion_status=status,
            information_cutoff_date=information_cutoff_date,
            recorded_at_utc=recorded_at_utc,
            supersedes_revision_id=None if prior is None else prior.id,
        )
        session.add(revision)
        session.flush()
        ref = _AssertionRef(
            "node", revision, node.map_id, status, information_cutoff_date, recorded_at_utc
        )
        self._add_claim_links(session, ref, claims, recorded_at_utc)
        return revision

    def _insert_relationship_revision(
        self,
        session: Session,
        *,
        relationship: IndustryMapRelationship,
        relation_kind: str,
        description: str | None,
        assertion_status: str,
        information_cutoff_date: date,
        claim_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime,
    ) -> IndustryMapRelationshipRevision:
        prior = self._latest_revision(
            session,
            IndustryMapRelationshipRevision,
            "relationship_id",
            relationship.id,
        )
        validate_utc_chronology(
            recorded_at_utc,
            ("relationship identity timestamp", _stored_utc(relationship.created_at_utc)),
            *(() if prior is None else (("previous relationship revision timestamp", _stored_utc(prior.recorded_at_utc)),)),
        )
        status = _reviewed_value(
            assertion_status, "assertion_status", ASSERTION_STATUSES
        )
        kind = _reviewed_value(relation_kind, "relation_kind", RELATION_KINDS)
        industry_map = self._require_map(session, relationship.map_id)
        claims = self._resolve_claim_revisions(
            session,
            industry_map,
            claim_revision_ids,
            information_cutoff_date,
            recorded_at_utc,
        )
        self._validate_assertion_status(session, status, claims, recorded_at_utc)
        revision = IndustryMapRelationshipRevision(
            relationship_id=relationship.id,
            revision_no=1 if prior is None else prior.revision_no + 1,
            relation_kind=kind,
            description=_optional_text(description, "description", 4000),
            assertion_status=status,
            information_cutoff_date=information_cutoff_date,
            recorded_at_utc=recorded_at_utc,
            supersedes_revision_id=None if prior is None else prior.id,
        )
        session.add(revision)
        session.flush()
        ref = _AssertionRef(
            "relationship",
            revision,
            relationship.map_id,
            status,
            information_cutoff_date,
            recorded_at_utc,
        )
        self._add_claim_links(session, ref, claims, recorded_at_utc)
        return revision

    def _insert_observation_revision(
        self,
        session: Session,
        *,
        observation: IndustryMapObservation,
        title: str,
        description: str | None,
        assertion_status: str,
        information_cutoff_date: date,
        claim_revision_ids: tuple[UUID, ...],
        recorded_at_utc: datetime,
    ) -> IndustryMapObservationRevision:
        prior = self._latest_revision(
            session,
            IndustryMapObservationRevision,
            "observation_id",
            observation.id,
        )
        validate_utc_chronology(
            recorded_at_utc,
            ("observation identity timestamp", _stored_utc(observation.created_at_utc)),
            *(() if prior is None else (("previous observation revision timestamp", _stored_utc(prior.recorded_at_utc)),)),
        )
        status = _reviewed_value(
            assertion_status, "assertion_status", ASSERTION_STATUSES
        )
        industry_map = self._require_map(session, observation.map_id)
        claims = self._resolve_claim_revisions(
            session,
            industry_map,
            claim_revision_ids,
            information_cutoff_date,
            recorded_at_utc,
        )
        self._validate_assertion_status(session, status, claims, recorded_at_utc)
        revision = IndustryMapObservationRevision(
            observation_id=observation.id,
            revision_no=1 if prior is None else prior.revision_no + 1,
            title=_required_text(title, "title", 300),
            description=_optional_text(description, "description", 4000),
            assertion_status=status,
            information_cutoff_date=information_cutoff_date,
            recorded_at_utc=recorded_at_utc,
            supersedes_revision_id=None if prior is None else prior.id,
        )
        session.add(revision)
        session.flush()
        ref = _AssertionRef(
            "observation",
            revision,
            observation.map_id,
            status,
            information_cutoff_date,
            recorded_at_utc,
        )
        self._add_claim_links(session, ref, claims, recorded_at_utc)
        return revision

    def _resolve_claim_revisions(
        self,
        session: Session,
        industry_map: IndustryMap,
        claim_revision_ids: tuple[UUID, ...],
        information_cutoff_date: date,
        recorded_at_utc: datetime,
    ) -> list[ClaimRevision]:
        if not claim_revision_ids:
            raise EvidenceLedgerValidationError(
                "every map assertion revision requires at least one claim revision."
            )
        if len(set(claim_revision_ids)) != len(claim_revision_ids):
            raise EvidenceLedgerValidationError(
                "claim_revision_ids must not contain duplicates."
            )
        revisions = [
            self._resolve_claim_revision(
                session,
                industry_map,
                claim_revision_id,
                information_cutoff_date,
                recorded_at_utc,
            )
            for claim_revision_id in claim_revision_ids
        ]
        if len({revision.claim_id for revision in revisions}) != len(revisions):
            raise EvidenceLedgerValidationError(
                "an assertion cannot bind multiple revisions of the same claim identity."
            )
        return revisions

    @staticmethod
    def _resolve_claim_revision(
        session: Session,
        industry_map: IndustryMap,
        claim_revision_id: UUID,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
    ) -> ClaimRevision:
        revision = session.get(ClaimRevision, claim_revision_id)
        if revision is None:
            raise EvidenceLedgerNotFound(
                f"Claim revision {claim_revision_id} was not found."
            )
        claim = session.get(Claim, revision.claim_id)
        if claim is None or claim.case_id != industry_map.case_id:
            raise EvidenceLedgerValidationError(
                "map assertions and linked claim revisions must share one research case."
            )
        if revision.information_cutoff_date > information_cutoff_date:
            raise EvidenceLedgerValidationError(
                "claim revision cutoff exceeds the assertion cutoff."
            )
        validate_utc_chronology(
            recorded_at_utc,
            ("claim revision timestamp", _stored_utc(revision.recorded_at_utc)),
        )
        return revision

    @staticmethod
    def _validate_assertion_status(
        session: Session,
        status: str,
        claims: list[ClaimRevision],
        effective_at_utc: datetime,
    ) -> None:
        if not claims:
            raise EvidenceLedgerValidationError(
                "every map assertion revision requires at least one claim revision."
            )
        summaries = [
            _claim_evidence_state(session, claim, effective_at_utc) for claim in claims
        ]
        if status == "supported":
            if any(summary["has_conflict"] for summary in summaries):
                raise EvidenceLedgerValidationError(
                    "supported map assertions cannot have visible contradictory evidence."
                )
            if not any(
                claim.claim_status == "supported" and summary["has_abc_support"]
                for claim, summary in zip(claims, summaries, strict=True)
            ):
                raise EvidenceLedgerValidationError(
                    "supported map assertions require a supported A/B/C-backed claim revision."
                )
        if status == "disputed" and not any(
            claim.claim_status == "disputed" or summary["has_conflict"]
            for claim, summary in zip(claims, summaries, strict=True)
        ):
            raise EvidenceLedgerValidationError(
                "disputed map assertions require a disputed claim or visible contradiction."
            )

    @staticmethod
    def _add_claim_links(
        session: Session,
        assertion: _AssertionRef,
        claims: list[ClaimRevision],
        recorded_at_utc: datetime,
    ) -> None:
        for claim in claims:
            session.add(
                IndustryChainMapCommandService._claim_link(
                    assertion, claim.id, recorded_at_utc
                )
            )
        session.flush()

    @staticmethod
    def _claim_link(
        assertion: _AssertionRef,
        claim_revision_id: UUID,
        recorded_at_utc: datetime,
    ) -> IndustryMapAssertionClaimLink:
        link = IndustryMapAssertionClaimLink(
            claim_revision_id=claim_revision_id,
            recorded_at_utc=recorded_at_utc,
        )
        setattr(link, f"{assertion.kind}_revision_id", assertion.revision.id)
        return link

    def _membership_refs(
        self,
        session: Session,
        kind: str,
        revision_ids: tuple[UUID, ...],
        map_id: UUID,
    ) -> list[_AssertionRef]:
        if len(set(revision_ids)) != len(revision_ids):
            raise EvidenceLedgerValidationError(
                f"{kind}_revision_ids must not contain duplicates."
            )
        refs = [
            self._assertion_ref(session, kind, item, for_update=True)
            for item in sorted(revision_ids, key=str)
        ]
        if any(ref.map_id != map_id for ref in refs):
            raise EvidenceLedgerValidationError(
                "map revision memberships must belong to the same industry map."
            )
        identity_field = {
            "node": "node_id",
            "relationship": "relationship_id",
            "observation": "observation_id",
        }[kind]
        identity_ids = [getattr(ref.revision, identity_field) for ref in refs]
        if len(set(identity_ids)) != len(identity_ids):
            raise EvidenceLedgerValidationError(
                f"a map revision cannot freeze multiple revisions of one {kind} identity."
            )
        return refs

    def _assertion_ref(
        self,
        session: Session,
        kind: str,
        revision_id: UUID,
        *,
        for_update: bool = False,
    ) -> _AssertionRef:
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
        if kind not in models:
            raise EvidenceLedgerValidationError(
                "assertion_kind must be node, relationship, or observation."
            )
        revision_model, identity_model, identity_field = models[kind]
        if for_update:
            revision = session.scalar(
                select(revision_model)
                .where(revision_model.id == revision_id)
                .with_for_update()
            )
        else:
            revision = session.get(revision_model, revision_id)
        if revision is None:
            raise EvidenceLedgerNotFound(
                f"{kind} revision {revision_id} was not found."
            )
        identity = session.get(identity_model, getattr(revision, identity_field))
        if identity is None:
            raise EvidenceLedgerNotFound(f"{kind} identity was not found.")
        return _AssertionRef(
            kind=kind,
            revision=revision,
            map_id=identity.map_id,
            status=revision.assertion_status,
            information_cutoff_date=revision.information_cutoff_date,
            recorded_at_utc=_stored_utc(revision.recorded_at_utc),
        )

    @staticmethod
    def _claim_links_for_ref(
        session: Session, assertion: _AssertionRef
    ) -> list[IndustryMapAssertionClaimLink]:
        column = getattr(
            IndustryMapAssertionClaimLink, f"{assertion.kind}_revision_id"
        )
        return list(
            session.scalars(
                select(IndustryMapAssertionClaimLink)
                .where(column == assertion.revision.id)
                .order_by(IndustryMapAssertionClaimLink.claim_revision_id)
            )
        )

    def _linked_claim_revisions(
        self,
        session: Session,
        assertion: _AssertionRef,
        *,
        for_update: bool = False,
    ) -> list[ClaimRevision]:
        links = self._claim_links_for_ref(session, assertion)
        claim_ids = sorted({link.claim_revision_id for link in links}, key=str)
        if for_update and claim_ids:
            claims = list(
                session.scalars(
                    select(ClaimRevision)
                    .where(ClaimRevision.id.in_(claim_ids))
                    .order_by(ClaimRevision.id)
                    .with_for_update()
                )
            )
        else:
            claims = [session.get(ClaimRevision, item) for item in claim_ids]
        if any(claim is None for claim in claims):
            raise EvidenceLedgerNotFound("linked claim revision was not found.")
        return [claim for claim in claims if claim is not None]

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
    def _locked_map(session: Session, map_id: UUID) -> IndustryMap:
        industry_map = session.scalar(
            select(IndustryMap).where(IndustryMap.id == map_id).with_for_update()
        )
        if industry_map is None:
            raise EvidenceLedgerNotFound(f"Industry map {map_id} was not found.")
        return industry_map

    @staticmethod
    def _locked_node(session: Session, node_id: UUID) -> IndustryMapNode:
        node = session.scalar(
            select(IndustryMapNode)
            .where(IndustryMapNode.id == node_id)
            .with_for_update()
        )
        if node is None:
            raise EvidenceLedgerNotFound(f"Industry map node {node_id} was not found.")
        return node

    @staticmethod
    def _locked_relationship(
        session: Session, relationship_id: UUID
    ) -> IndustryMapRelationship:
        relationship = session.scalar(
            select(IndustryMapRelationship)
            .where(IndustryMapRelationship.id == relationship_id)
            .with_for_update()
        )
        if relationship is None:
            raise EvidenceLedgerNotFound(
                f"Industry map relationship {relationship_id} was not found."
            )
        return relationship

    @staticmethod
    def _locked_observation(
        session: Session, observation_id: UUID
    ) -> IndustryMapObservation:
        observation = session.scalar(
            select(IndustryMapObservation)
            .where(IndustryMapObservation.id == observation_id)
            .with_for_update()
        )
        if observation is None:
            raise EvidenceLedgerNotFound(
                f"Industry map observation {observation_id} was not found."
            )
        return observation

    @staticmethod
    def _require_map(session: Session, map_id: UUID) -> IndustryMap:
        industry_map = session.get(IndustryMap, map_id)
        if industry_map is None:
            raise EvidenceLedgerNotFound(f"Industry map {map_id} was not found.")
        return industry_map

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


def _claim_evidence_state(
    session: Session, claim: ClaimRevision, effective_at_utc: datetime
) -> dict[str, Any]:
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
            link.relation == "supports" and evidence.evidence_grade in {"A", "B", "C"}
            for link, evidence in visible
        ),
        "has_conflict": any(link.relation == "contradicts" for link, _ in visible),
        "has_evidence": bool(visible),
    }


def _validate_post_freeze_timestamp(
    session: Session, assertion: _AssertionRef, recorded_at_utc: datetime
) -> None:
    target_column = getattr(
        IndustryMapRevisionMembership, f"{assertion.kind}_revision_id"
    )
    memberships = list(
        session.scalars(
            select(IndustryMapRevisionMembership).where(
                target_column == assertion.revision.id
            )
        )
    )
    map_revisions = [
        session.get(IndustryMapRevision, item.map_revision_id) for item in memberships
    ]
    frozen_at = [
        _stored_utc(item.recorded_at_utc)
        for item in map_revisions
        if item is not None
    ]
    if frozen_at and recorded_at_utc <= max(frozen_at):
        raise EvidenceLedgerValidationError(
            "a later assertion claim link must be recorded after every map revision that already froze the assertion."
        )


def validate_claim_evidence_append_after_map_freeze(
    session: Session, claim_revision_id: UUID, recorded_at_utc: datetime
) -> None:
    """Prevent a later v0.5A evidence link from rewriting a frozen map."""
    assertion_links = list(
        session.scalars(
            select(IndustryMapAssertionClaimLink).where(
                IndustryMapAssertionClaimLink.claim_revision_id == claim_revision_id
            )
        )
    )
    frozen_at: list[datetime] = []
    for assertion_link in assertion_links:
        for kind in ("node", "relationship", "observation"):
            assertion_revision_id = getattr(
                assertion_link, f"{kind}_revision_id"
            )
            if assertion_revision_id is None:
                continue
            membership_column = getattr(
                IndustryMapRevisionMembership, f"{kind}_revision_id"
            )
            memberships = session.scalars(
                select(IndustryMapRevisionMembership).where(
                    membership_column == assertion_revision_id
                )
            )
            for membership in memberships:
                map_revision = session.get(
                    IndustryMapRevision, membership.map_revision_id
                )
                if (
                    map_revision is not None
                    and _stored_utc(assertion_link.recorded_at_utc)
                    <= _stored_utc(map_revision.recorded_at_utc)
                ):
                    frozen_at.append(_stored_utc(map_revision.recorded_at_utc))
    if frozen_at and recorded_at_utc <= max(frozen_at):
        raise EvidenceLedgerValidationError(
            "a later claim evidence link must be recorded after every map revision that already froze the claim binding."
        )


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


def _optional_text(value: str | None, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise EvidenceLedgerValidationError(f"{field} must be a string or None.")
    normalized = value.strip()
    if not normalized:
        return None
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


def _stored_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
