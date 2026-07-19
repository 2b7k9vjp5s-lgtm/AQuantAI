"""Deterministic offline fixture for evidence-backed industry chain maps."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.chain_map_commands import IndustryChainMapCommandService
from industry_alpha.chain_map_models import (
    IndustryMapNodeRevision,
    IndustryMapObservationRevision,
    IndustryMapRelationshipRevision,
)
from industry_alpha.commands import EvidenceLedgerCommandService, EvidenceLinkInput
from industry_alpha.models import ClaimRevision

RevisionT = TypeVar("RevisionT")


def _recorded(day: int) -> datetime:
    return datetime(2026, 7, day, 9, tzinfo=timezone.utc)


def build_industry_chain_map_fixture(
    session_factory: sessionmaker[Session],
) -> UUID:
    ledger = EvidenceLedgerCommandService(session_factory)
    maps = IndustryChainMapCommandService(session_factory)
    case = ledger.create_case(
        case_key="fixture-industry-chain-map",
        title="Fixture industry chain research",
        research_question="What structure is supported by attributable fixture evidence?",
        information_cutoff_date=date(2026, 7, 1),
        recorded_at_utc=_recorded(1),
        origin="fixture",
    )
    primary = ledger.add_evidence(
        case.id,
        evidence_grade="A",
        source_kind="official",
        source_title="Fixture official industry publication",
        information_date=date(2026, 7, 2),
        summary="Official evidence for a bounded chain structure.",
        content_fingerprint="chain-map-primary-v1",
        recorded_at_utc=_recorded(2),
    )
    study = ledger.add_evidence(
        case.id,
        evidence_grade="B",
        source_kind="research",
        source_title="Fixture attributable industry study",
        information_date=date(2026, 7, 2),
        summary="Attributable evidence for a bounded causal driver.",
        content_fingerprint="chain-map-study-v1",
        recorded_at_utc=_recorded(2),
    )
    lead = ledger.add_evidence(
        case.id,
        evidence_grade="D",
        source_kind="community",
        source_title="Fixture unverified value-pool lead",
        information_date=date(2026, 7, 2),
        summary="Unverified context retained without factual promotion.",
        content_fingerprint="chain-map-lead-v1",
        recorded_at_utc=_recorded(2),
    )
    structure_claim = ledger.create_claim(
        case.id,
        claim_key="fixture-chain-structure",
        statement="The bounded fixture chain contains an input and manufacturing step.",
        claim_kind="fact",
        claim_status="supported",
        information_cutoff_date=date(2026, 7, 2),
        evidence_links=(EvidenceLinkInput(primary.id, "supports"),),
        recorded_at_utc=_recorded(2),
    )
    driver_claim = ledger.create_claim(
        case.id,
        claim_key="fixture-chain-driver",
        statement="The attributable study supports a bounded demand driver inference.",
        claim_kind="inference",
        claim_status="supported",
        inference_confidence="medium",
        inference_basis="One attributable study with a discernible method.",
        information_cutoff_date=date(2026, 7, 2),
        evidence_links=(EvidenceLinkInput(study.id, "supports"),),
        recorded_at_utc=_recorded(2),
    )
    lead_claim = ledger.create_claim(
        case.id,
        claim_key="fixture-value-pool-lead",
        statement="An unverified lead suggests a possible value-pool shift.",
        claim_kind="inference",
        claim_status="draft",
        inference_confidence="low",
        inference_basis="D-grade context only; primary verification is missing.",
        information_cutoff_date=date(2026, 7, 2),
        evidence_links=(EvidenceLinkInput(lead.id, "context"),),
        recorded_at_utc=_recorded(2),
    )
    structure_revision = _claim_revision(session_factory, structure_claim.id)
    driver_revision = _claim_revision(session_factory, driver_claim.id)
    lead_revision = _claim_revision(session_factory, lead_claim.id)

    industry_map = maps.create_map(
        case.id,
        map_key="fixture-chain-map",
        title="Fixture evidence-backed industry chain map",
        scope="Bounded fixture structure only; no company beneficiaries or scoring.",
        information_cutoff_date=date(2026, 7, 2),
        recorded_at_utc=_recorded(2),
    )
    upstream = maps.create_node(
        industry_map.id,
        node_key="upstream-input",
        label="Fixture upstream input",
        node_kind="upstream_input",
        assertion_status="supported",
        information_cutoff_date=date(2026, 7, 3),
        claim_revision_ids=(structure_revision.id,),
        recorded_at_utc=_recorded(3),
    )
    manufacturing = maps.create_node(
        industry_map.id,
        node_key="manufacturing",
        label="Fixture manufacturing step",
        node_kind="manufacturing",
        assertion_status="supported",
        information_cutoff_date=date(2026, 7, 3),
        claim_revision_ids=(structure_revision.id,),
        recorded_at_utc=_recorded(3),
    )
    relationship = maps.create_relationship(
        industry_map.id,
        relationship_key="input-supplies-manufacturing",
        source_node_id=upstream.id,
        target_node_id=manufacturing.id,
        relation_kind="supplies",
        assertion_status="supported",
        information_cutoff_date=date(2026, 7, 3),
        claim_revision_ids=(structure_revision.id,),
        recorded_at_utc=_recorded(3),
    )
    driver = maps.create_observation(
        industry_map.id,
        observation_key="bounded-demand-driver",
        observation_kind="driver",
        title="Fixture bounded demand driver",
        assertion_status="supported",
        information_cutoff_date=date(2026, 7, 3),
        claim_revision_ids=(driver_revision.id,),
        recorded_at_utc=_recorded(3),
    )
    value_pool = maps.create_observation(
        industry_map.id,
        observation_key="unverified-value-pool-lead",
        observation_kind="value_pool_shift",
        title="Unverified fixture value-pool lead",
        description="D-grade context remains draft and is not a supported finding.",
        assertion_status="draft",
        information_cutoff_date=date(2026, 7, 3),
        claim_revision_ids=(lead_revision.id,),
        recorded_at_utc=_recorded(3),
    )
    upstream_revision = _first_revision(
        session_factory, IndustryMapNodeRevision, "node_id", upstream.id
    )
    manufacturing_revision = _first_revision(
        session_factory, IndustryMapNodeRevision, "node_id", manufacturing.id
    )
    relationship_revision = _first_revision(
        session_factory,
        IndustryMapRelationshipRevision,
        "relationship_id",
        relationship.id,
    )
    driver_map_revision = _first_revision(
        session_factory,
        IndustryMapObservationRevision,
        "observation_id",
        driver.id,
    )
    value_pool_revision = _first_revision(
        session_factory,
        IndustryMapObservationRevision,
        "observation_id",
        value_pool.id,
    )
    maps.append_map_revision(
        industry_map.id,
        title="Early fixture chain map",
        scope="Supported structure plus one explicit D-grade value-pool lead.",
        information_cutoff_date=date(2026, 7, 3),
        node_revision_ids=(upstream_revision.id, manufacturing_revision.id),
        relationship_revision_ids=(relationship_revision.id,),
        observation_revision_ids=(driver_map_revision.id, value_pool_revision.id),
        recorded_at_utc=_recorded(3),
    )

    contradiction = ledger.add_evidence(
        case.id,
        evidence_grade="C",
        source_kind="industry",
        source_title="Fixture contradictory bottleneck context",
        information_date=date(2026, 7, 4),
        summary="Attributable context conflicts with the prior driver inference.",
        content_fingerprint="chain-map-conflict-v1",
        recorded_at_utc=_recorded(5),
    )
    disputed_driver = ledger.append_claim_revision(
        driver_claim.id,
        statement="The driver remains disputed because attributable conflict is visible.",
        claim_kind="inference",
        claim_status="disputed",
        inference_confidence="low",
        inference_basis="Attributable supporting and contradictory evidence coexist.",
        information_cutoff_date=date(2026, 7, 5),
        evidence_links=(
            EvidenceLinkInput(study.id, "supports"),
            EvidenceLinkInput(contradiction.id, "contradicts"),
        ),
        recorded_at_utc=_recorded(5),
    )
    bottleneck = maps.create_observation(
        industry_map.id,
        observation_key="disputed-bottleneck",
        observation_kind="bottleneck",
        title="Disputed fixture bottleneck",
        assertion_status="disputed",
        information_cutoff_date=date(2026, 7, 5),
        claim_revision_ids=(disputed_driver.id,),
        recorded_at_utc=_recorded(5),
    )
    bottleneck_revision = _first_revision(
        session_factory,
        IndustryMapObservationRevision,
        "observation_id",
        bottleneck.id,
    )
    maps.append_map_revision(
        industry_map.id,
        title="Current fixture chain map with explicit conflict",
        scope="Bounded structure, disputed bottleneck, and unverified D-grade lead.",
        information_cutoff_date=date(2026, 7, 5),
        node_revision_ids=(upstream_revision.id, manufacturing_revision.id),
        relationship_revision_ids=(relationship_revision.id,),
        observation_revision_ids=(
            driver_map_revision.id,
            bottleneck_revision.id,
            value_pool_revision.id,
        ),
        recorded_at_utc=_recorded(5),
    )
    return industry_map.id


def _claim_revision(
    session_factory: sessionmaker[Session], claim_id: UUID
) -> ClaimRevision:
    with session_factory() as session:
        return session.scalar(
            select(ClaimRevision).where(ClaimRevision.claim_id == claim_id)
        )


def _first_revision(
    session_factory: sessionmaker[Session],
    model: type[RevisionT],
    identity_field: str,
    identity_id: UUID,
) -> RevisionT:
    with session_factory() as session:
        return session.scalar(
            select(model).where(getattr(model, identity_field) == identity_id)
        )
