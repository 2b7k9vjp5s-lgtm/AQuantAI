from __future__ import annotations

import json
import socket
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from backend.api.industry_alpha import get_industry_alpha_session_factory
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
from industry_alpha.chain_map_commands import IndustryChainMapCommandService
from industry_alpha.chain_map_fixtures import build_industry_chain_map_fixture
from industry_alpha.chain_map_models import (
    CHAIN_MAP_MODELS,
    IndustryMapAssertionClaimLink,
    IndustryMapNode,
    IndustryMapNodeRevision,
    IndustryMapObservationRevision,
    IndustryMapRelationshipRevision,
    IndustryMapRevision,
)
from industry_alpha.chain_map_query import IndustryChainMapQueryService
from industry_alpha.chain_map_repository import IndustryChainMapRepository
from industry_alpha.commands import EvidenceLedgerCommandService, EvidenceLinkInput
from industry_alpha.errors import (
    EvidenceLedgerImmutableError,
    EvidenceLedgerValidationError,
)
from industry_alpha.models import ClaimRevision


def utc(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 3, day, hour, tzinfo=timezone.utc)


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    yield factory
    engine.dispose()


def revision_for(session_factory, model, identity_field: str, identity_id: UUID):
    with session_factory() as session:
        return session.scalar(
            select(model)
            .where(getattr(model, identity_field) == identity_id)
            .order_by(model.revision_no.desc())
        )


def chain_counts(session_factory) -> tuple[int, ...]:
    with session_factory() as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in CHAIN_MAP_MODELS
        )


def build_case_claims(session_factory, key: str = "map-case") -> dict[str, object]:
    ledger = EvidenceLedgerCommandService(session_factory)
    case = ledger.create_case(
        case_key=key,
        title="Industry chain case",
        research_question="What does the evidence establish?",
        information_cutoff_date=date(2026, 3, 1),
        recorded_at_utc=utc(1),
    )
    primary = ledger.add_evidence(
        case.id,
        evidence_grade="A",
        source_kind="official",
        source_title="Official source",
        information_date=date(2026, 3, 2),
        summary="Primary attributable evidence.",
        recorded_at_utc=utc(2),
    )
    d_lead = ledger.add_evidence(
        case.id,
        evidence_grade="D",
        source_kind="community",
        source_title="Unverified lead",
        information_date=date(2026, 3, 2),
        summary="D-grade context only.",
        recorded_at_utc=utc(2),
    )
    supported = ledger.create_claim(
        case.id,
        claim_key="supported-structure",
        statement="A bounded structure is supported.",
        claim_kind="fact",
        claim_status="supported",
        information_cutoff_date=date(2026, 3, 2),
        evidence_links=(EvidenceLinkInput(primary.id, "supports"),),
        recorded_at_utc=utc(2),
    )
    lead = ledger.create_claim(
        case.id,
        claim_key="d-lead",
        statement="An unverified lead remains contextual.",
        claim_kind="inference",
        claim_status="draft",
        inference_confidence="low",
        inference_basis="D-grade context only.",
        information_cutoff_date=date(2026, 3, 2),
        evidence_links=(EvidenceLinkInput(d_lead.id, "context"),),
        recorded_at_utc=utc(2),
    )
    supported_revision = revision_for(
        session_factory, ClaimRevision, "claim_id", supported.id
    )
    lead_revision = revision_for(session_factory, ClaimRevision, "claim_id", lead.id)
    return {
        "ledger": ledger,
        "case": case,
        "primary": primary,
        "d_lead": d_lead,
        "supported_claim": supported,
        "supported_revision": supported_revision,
        "lead_claim": lead,
        "lead_revision": lead_revision,
    }


def create_map(session_factory, context, key: str = "chain-map"):
    return IndustryChainMapCommandService(session_factory).create_map(
        context["case"].id,
        map_key=key,
        title="Evidence-backed map",
        scope="Bounded fixture scope.",
        information_cutoff_date=date(2026, 3, 2),
        recorded_at_utc=utc(2),
    )


def test_fixture_has_frozen_structure_conflict_d_lead_and_no_cutoff_leakage(
    session_factory,
):
    map_id = build_industry_chain_map_fixture(session_factory)
    with session_factory() as session:
        query = IndustryChainMapQueryService(IndustryChainMapRepository(session))
        current = query.get_map(map_id).to_dict()
        historical = query.get_map(
            map_id, as_of_cutoff=date(2026, 7, 3)
        ).to_dict()
    assert current["latest_revision"]["revision_no"] == 3
    assert current["frozen_snapshot"]["counts"] == {
        "nodes": 2,
        "relationships": 1,
        "drivers": 1,
        "bottlenecks": 1,
        "value_pool_shifts": 1,
    }
    assert current["evidence_grade_summary"] == {"A": 1, "B": 1, "C": 1, "D": 1}
    assert len(current["conflicts"]) == 1
    value_pool = next(
        item
        for item in current["frozen_snapshot"]["observations"]
        if item["observation_kind"] == "value_pool_shift"
    )
    assert value_pool["revision"]["assertion_status"] == "draft"
    assert value_pool["revision"]["evidence_summary"]["grade_counts"]["D"] == 1
    assert historical["latest_revision"]["revision_no"] == 2
    assert historical["frozen_snapshot"]["counts"]["bottlenecks"] == 0
    assert historical["conflicts"] == []
    json.dumps(current, allow_nan=False)


def test_stable_node_identity_revision_number_and_supersedes(session_factory):
    context = build_case_claims(session_factory)
    industry_map = create_map(session_factory, context)
    commands = IndustryChainMapCommandService(session_factory)
    node = commands.create_node(
        industry_map.id,
        node_key="input",
        label="Input",
        node_kind="upstream_input",
        assertion_status="supported",
        information_cutoff_date=date(2026, 3, 3),
        claim_revision_ids=(context["supported_revision"].id,),
        recorded_at_utc=utc(3),
    )
    second = commands.append_node_revision(
        node.id,
        label="Reviewed input",
        node_kind="component",
        assertion_status="supported",
        information_cutoff_date=date(2026, 3, 4),
        claim_revision_ids=(context["supported_revision"].id,),
        recorded_at_utc=utc(4),
    )
    with session_factory() as session:
        first = session.scalar(
            select(IndustryMapNodeRevision).where(
                IndustryMapNodeRevision.node_id == node.id,
                IndustryMapNodeRevision.revision_no == 1,
            )
        )
    assert second.revision_no == 2
    assert second.supersedes_revision_id == first.id
    assert node.node_key == "input"


@pytest.mark.parametrize("node_kind", ["bad", "manufacturer", "customer"])
def test_node_kind_enum_is_strict_and_rolls_back(session_factory, node_kind):
    context = build_case_claims(session_factory)
    industry_map = create_map(session_factory, context)
    before = chain_counts(session_factory)
    with pytest.raises(EvidenceLedgerValidationError, match="node_kind"):
        IndustryChainMapCommandService(session_factory).create_node(
            industry_map.id,
            node_key="bad-node",
            label="Bad",
            node_kind=node_kind,
            assertion_status="draft",
            information_cutoff_date=date(2026, 3, 3),
            claim_revision_ids=(context["supported_revision"].id,),
            recorded_at_utc=utc(3),
        )
    assert chain_counts(session_factory) == before


@pytest.mark.parametrize("status", ["unknown", "qualified", "recommended"])
def test_assertion_status_enum_is_strict(session_factory, status):
    context = build_case_claims(session_factory)
    industry_map = create_map(session_factory, context)
    with pytest.raises(EvidenceLedgerValidationError, match="assertion_status"):
        IndustryChainMapCommandService(session_factory).create_observation(
            industry_map.id,
            observation_key="bad-status",
            observation_kind="driver",
            title="Bad status",
            assertion_status=status,
            information_cutoff_date=date(2026, 3, 3),
            claim_revision_ids=(context["supported_revision"].id,),
            recorded_at_utc=utc(3),
        )


def test_relationship_and_observation_enums_are_strict(session_factory):
    context = build_case_claims(session_factory)
    industry_map = create_map(session_factory, context)
    commands = IndustryChainMapCommandService(session_factory)
    source = commands.create_node(
        industry_map.id,
        node_key="enum-source",
        label="Source",
        node_kind="component",
        assertion_status="draft",
        information_cutoff_date=date(2026, 3, 3),
        claim_revision_ids=(context["supported_revision"].id,),
        recorded_at_utc=utc(3),
    )
    target = commands.create_node(
        industry_map.id,
        node_key="enum-target",
        label="Target",
        node_kind="service",
        assertion_status="draft",
        information_cutoff_date=date(2026, 3, 3),
        claim_revision_ids=(context["supported_revision"].id,),
        recorded_at_utc=utc(3),
    )
    before = chain_counts(session_factory)
    with pytest.raises(EvidenceLedgerValidationError, match="relation_kind"):
        commands.create_relationship(
            industry_map.id,
            relationship_key="invalid-relation",
            source_node_id=source.id,
            target_node_id=target.id,
            relation_kind="benefits_from",
            assertion_status="draft",
            information_cutoff_date=date(2026, 3, 3),
            claim_revision_ids=(context["supported_revision"].id,),
            recorded_at_utc=utc(3),
        )
    with pytest.raises(EvidenceLedgerValidationError, match="observation_kind"):
        commands.create_observation(
            industry_map.id,
            observation_key="invalid-observation",
            observation_kind="recommendation",
            title="Invalid",
            assertion_status="draft",
            information_cutoff_date=date(2026, 3, 3),
            claim_revision_ids=(context["supported_revision"].id,),
            recorded_at_utc=utc(3),
        )
    assert chain_counts(session_factory) == before


@pytest.mark.parametrize(
    ("field", "value"),
    [("node_key", 123), ("label", None), ("description", object())],
)
def test_text_boundaries_reject_non_strings_atomically(
    session_factory, field, value
):
    context = build_case_claims(session_factory)
    industry_map = create_map(session_factory, context)
    kwargs = {
        "node_key": "strict-node",
        "label": "Strict node",
        "description": None,
        "node_kind": "component",
        "assertion_status": "draft",
        "information_cutoff_date": date(2026, 3, 3),
        "claim_revision_ids": (context["supported_revision"].id,),
        "recorded_at_utc": utc(3),
    }
    kwargs[field] = value
    before = chain_counts(session_factory)
    with pytest.raises(EvidenceLedgerValidationError, match=field):
        IndustryChainMapCommandService(session_factory).create_node(
            industry_map.id, **kwargs
        )
    assert chain_counts(session_factory) == before


def test_supported_d_only_and_disputed_rules(session_factory):
    context = build_case_claims(session_factory)
    industry_map = create_map(session_factory, context)
    commands = IndustryChainMapCommandService(session_factory)
    with pytest.raises(EvidenceLedgerValidationError, match="A/B/C"):
        commands.create_observation(
            industry_map.id,
            observation_key="d-only-supported",
            observation_kind="value_pool_shift",
            title="D-only cannot support",
            assertion_status="supported",
            information_cutoff_date=date(2026, 3, 3),
            claim_revision_ids=(context["lead_revision"].id,),
            recorded_at_utc=utc(3),
        )
    with pytest.raises(EvidenceLedgerValidationError, match="disputed claim"):
        commands.create_observation(
            industry_map.id,
            observation_key="not-disputed",
            observation_kind="bottleneck",
            title="No conflict",
            assertion_status="disputed",
            information_cutoff_date=date(2026, 3, 3),
            claim_revision_ids=(context["supported_revision"].id,),
            recorded_at_utc=utc(3),
        )
    contradiction = context["ledger"].add_evidence(
        context["case"].id,
        evidence_grade="C",
        source_kind="industry",
        source_title="Contradictory source",
        information_date=date(2026, 3, 4),
        summary="Visible contradiction.",
        recorded_at_utc=utc(4),
    )
    disputed_claim = context["ledger"].append_claim_revision(
        context["supported_claim"].id,
        statement="The structure is now disputed.",
        claim_kind="fact",
        claim_status="disputed",
        information_cutoff_date=date(2026, 3, 4),
        evidence_links=(EvidenceLinkInput(contradiction.id, "contradicts"),),
        recorded_at_utc=utc(4),
    )
    item = commands.create_observation(
        industry_map.id,
        observation_key="disputed-bottleneck",
        observation_kind="bottleneck",
        title="Disputed bottleneck",
        assertion_status="disputed",
        information_cutoff_date=date(2026, 3, 4),
        claim_revision_ids=(disputed_claim.id,),
        recorded_at_utc=utc(4),
    )
    assert item.observation_kind == "bottleneck"


def test_cross_case_claim_and_cross_map_relationship_roll_back(session_factory):
    context = build_case_claims(session_factory)
    other = build_case_claims(session_factory, "other-case")
    industry_map = create_map(session_factory, context)
    commands = IndustryChainMapCommandService(session_factory)
    before = chain_counts(session_factory)
    with pytest.raises(EvidenceLedgerValidationError, match="share one research case"):
        commands.create_node(
            industry_map.id,
            node_key="cross-case",
            label="Cross case",
            node_kind="other",
            assertion_status="draft",
            information_cutoff_date=date(2026, 3, 3),
            claim_revision_ids=(other["supported_revision"].id,),
            recorded_at_utc=utc(3),
        )
    assert chain_counts(session_factory) == before
    other_map = create_map(session_factory, context, "other-map")
    source = commands.create_node(
        industry_map.id,
        node_key="source",
        label="Source",
        node_kind="component",
        assertion_status="supported",
        information_cutoff_date=date(2026, 3, 3),
        claim_revision_ids=(context["supported_revision"].id,),
        recorded_at_utc=utc(3),
    )
    target = commands.create_node(
        other_map.id,
        node_key="target",
        label="Target",
        node_kind="manufacturing",
        assertion_status="supported",
        information_cutoff_date=date(2026, 3, 3),
        claim_revision_ids=(context["supported_revision"].id,),
        recorded_at_utc=utc(3),
    )
    before_relationship = chain_counts(session_factory)
    with pytest.raises(EvidenceLedgerValidationError, match="same industry map"):
        commands.create_relationship(
            industry_map.id,
            relationship_key="cross-map",
            source_node_id=source.id,
            target_node_id=target.id,
            relation_kind="supplies",
            assertion_status="draft",
            information_cutoff_date=date(2026, 3, 3),
            claim_revision_ids=(context["supported_revision"].id,),
            recorded_at_utc=utc(3),
        )
    assert chain_counts(session_factory) == before_relationship


def test_map_membership_requires_endpoints_and_rejects_later_assertion(
    session_factory,
):
    context = build_case_claims(session_factory)
    industry_map = create_map(session_factory, context)
    commands = IndustryChainMapCommandService(session_factory)
    source = commands.create_node(
        industry_map.id,
        node_key="source",
        label="Source",
        node_kind="component",
        assertion_status="supported",
        information_cutoff_date=date(2026, 3, 3),
        claim_revision_ids=(context["supported_revision"].id,),
        recorded_at_utc=utc(3),
    )
    target = commands.create_node(
        industry_map.id,
        node_key="target",
        label="Target",
        node_kind="manufacturing",
        assertion_status="supported",
        information_cutoff_date=date(2026, 3, 3),
        claim_revision_ids=(context["supported_revision"].id,),
        recorded_at_utc=utc(3),
    )
    relation = commands.create_relationship(
        industry_map.id,
        relationship_key="source-target",
        source_node_id=source.id,
        target_node_id=target.id,
        relation_kind="supplies",
        assertion_status="supported",
        information_cutoff_date=date(2026, 3, 3),
        claim_revision_ids=(context["supported_revision"].id,),
        recorded_at_utc=utc(3),
    )
    source_revision = revision_for(
        session_factory, IndustryMapNodeRevision, "node_id", source.id
    )
    relation_revision = revision_for(
        session_factory,
        IndustryMapRelationshipRevision,
        "relationship_id",
        relation.id,
    )
    with pytest.raises(EvidenceLedgerValidationError, match="source and target"):
        commands.append_map_revision(
            industry_map.id,
            title="Incomplete relationship membership",
            scope="Missing target node revision.",
            information_cutoff_date=date(2026, 3, 4),
            node_revision_ids=(source_revision.id,),
            relationship_revision_ids=(relation_revision.id,),
            recorded_at_utc=utc(4),
        )
    target_revision = revision_for(
        session_factory, IndustryMapNodeRevision, "node_id", target.id
    )
    with pytest.raises(EvidenceLedgerValidationError, match="frozen assertion"):
        commands.append_map_revision(
            industry_map.id,
            title="Backdated freeze",
            scope="Must reject exact UTC backdating.",
            information_cutoff_date=date(2026, 3, 3),
            node_revision_ids=(source_revision.id, target_revision.id),
            relationship_revision_ids=(relation_revision.id,),
            recorded_at_utc=utc(3, 11),
        )


def test_one_claim_and_assertion_revision_per_stable_identity(session_factory):
    context = build_case_claims(session_factory)
    industry_map = create_map(session_factory, context)
    second_claim_revision = context["ledger"].append_claim_revision(
        context["supported_claim"].id,
        statement="The same bounded structure remains supported.",
        claim_kind="fact",
        claim_status="supported",
        information_cutoff_date=date(2026, 3, 3),
        evidence_links=(EvidenceLinkInput(context["primary"].id, "supports"),),
        recorded_at_utc=utc(3),
    )
    commands = IndustryChainMapCommandService(session_factory)
    with pytest.raises(EvidenceLedgerValidationError, match="same claim identity"):
        commands.create_node(
            industry_map.id,
            node_key="ambiguous-claim-version",
            label="Ambiguous",
            node_kind="other",
            assertion_status="supported",
            information_cutoff_date=date(2026, 3, 3),
            claim_revision_ids=(
                context["supported_revision"].id,
                second_claim_revision.id,
            ),
            recorded_at_utc=utc(3),
        )
    node = commands.create_node(
        industry_map.id,
        node_key="single-node-version",
        label="Version one",
        node_kind="other",
        assertion_status="supported",
        information_cutoff_date=date(2026, 3, 3),
        claim_revision_ids=(second_claim_revision.id,),
        recorded_at_utc=utc(3),
    )
    first_node_revision = revision_for(
        session_factory, IndustryMapNodeRevision, "node_id", node.id
    )
    second_node_revision = commands.append_node_revision(
        node.id,
        label="Version two",
        node_kind="other",
        assertion_status="supported",
        information_cutoff_date=date(2026, 3, 4),
        claim_revision_ids=(second_claim_revision.id,),
        recorded_at_utc=utc(4),
    )
    with pytest.raises(EvidenceLedgerValidationError, match="one node identity"):
        commands.append_map_revision(
            industry_map.id,
            title="Ambiguous node snapshot",
            scope="Must freeze one exact version per identity.",
            information_cutoff_date=date(2026, 3, 4),
            node_revision_ids=(first_node_revision.id, second_node_revision.id),
            recorded_at_utc=utc(4),
        )


def test_revision_and_identity_chronology_roll_back(session_factory):
    context = build_case_claims(session_factory)
    industry_map = create_map(session_factory, context)
    commands = IndustryChainMapCommandService(session_factory)
    before = chain_counts(session_factory)
    with pytest.raises(EvidenceLedgerValidationError, match="map creation"):
        commands.create_node(
            industry_map.id,
            node_key="backdated",
            label="Backdated",
            node_kind="other",
            assertion_status="draft",
            information_cutoff_date=date(2026, 3, 2),
            claim_revision_ids=(context["supported_revision"].id,),
            recorded_at_utc=utc(2, 11),
        )
    assert chain_counts(session_factory) == before
    node = commands.create_node(
        industry_map.id,
        node_key="chronological",
        label="Chronological",
        node_kind="other",
        assertion_status="draft",
        information_cutoff_date=date(2026, 3, 3),
        claim_revision_ids=(context["supported_revision"].id,),
        recorded_at_utc=utc(3),
    )
    commands.append_node_revision(
        node.id,
        label="Second",
        node_kind="other",
        assertion_status="draft",
        information_cutoff_date=date(2026, 3, 4),
        claim_revision_ids=(context["supported_revision"].id,),
        recorded_at_utc=utc(4),
    )
    accepted = chain_counts(session_factory)
    with pytest.raises(EvidenceLedgerValidationError, match="previous node revision"):
        commands.append_node_revision(
            node.id,
            label="Backdated third",
            node_kind="other",
            assertion_status="draft",
            information_cutoff_date=date(2026, 3, 3),
            claim_revision_ids=(context["supported_revision"].id,),
            recorded_at_utc=utc(3),
        )
    assert chain_counts(session_factory) == accepted


def test_later_assertion_claim_link_does_not_rewrite_frozen_map(session_factory):
    context = build_case_claims(session_factory)
    industry_map = create_map(session_factory, context)
    commands = IndustryChainMapCommandService(session_factory)
    node = commands.create_node(
        industry_map.id,
        node_key="frozen-node",
        label="Frozen node",
        node_kind="other",
        assertion_status="draft",
        information_cutoff_date=date(2026, 3, 3),
        claim_revision_ids=(context["supported_revision"].id,),
        recorded_at_utc=utc(3),
    )
    node_revision = revision_for(
        session_factory, IndustryMapNodeRevision, "node_id", node.id
    )
    commands.append_map_revision(
        industry_map.id,
        title="Frozen at day three",
        scope="One exact claim revision.",
        information_cutoff_date=date(2026, 3, 3),
        node_revision_ids=(node_revision.id,),
        recorded_at_utc=utc(3),
    )
    with pytest.raises(EvidenceLedgerValidationError, match="already froze"):
        commands.link_claim_revision(
            "node",
            node_revision.id,
            context["lead_revision"].id,
            recorded_at_utc=utc(3),
        )
    commands.link_claim_revision(
        "node",
        node_revision.id,
        context["lead_revision"].id,
        recorded_at_utc=utc(4),
    )
    with session_factory() as session:
        payload = IndustryChainMapQueryService(
            IndustryChainMapRepository(session)
        ).get_map(industry_map.id).to_dict()
    linked = payload["frozen_snapshot"]["nodes"][0]["revision"][
        "linked_claim_revisions"
    ]
    assert [item["claim_key"] for item in linked] == ["supported-structure"]
    with pytest.raises(EvidenceLedgerValidationError, match="latest assertion claim-link"):
        commands.link_claim_revision(
            "node",
            node_revision.id,
            context["lead_revision"].id,
            recorded_at_utc=utc(3, 13),
        )


def test_later_claim_evidence_link_cannot_backfill_a_frozen_map(session_factory):
    context = build_case_claims(session_factory)
    industry_map = create_map(session_factory, context)
    commands = IndustryChainMapCommandService(session_factory)
    node = commands.create_node(
        industry_map.id,
        node_key="evidence-freeze",
        label="Evidence freeze",
        node_kind="other",
        assertion_status="supported",
        information_cutoff_date=date(2026, 3, 3),
        claim_revision_ids=(context["supported_revision"].id,),
        recorded_at_utc=utc(3),
    )
    node_revision = revision_for(
        session_factory, IndustryMapNodeRevision, "node_id", node.id
    )
    commands.append_map_revision(
        industry_map.id,
        title="Frozen evidence state",
        scope="Later links cannot rewrite this snapshot.",
        information_cutoff_date=date(2026, 3, 3),
        node_revision_ids=(node_revision.id,),
        recorded_at_utc=utc(3),
    )
    later_context = context["ledger"].add_evidence(
        context["case"].id,
        evidence_grade="B",
        source_kind="research",
        source_title="Later contextual evidence",
        information_date=date(2026, 3, 2),
        summary="Recorded after the map was physically frozen.",
        recorded_at_utc=utc(3),
    )
    with pytest.raises(EvidenceLedgerValidationError, match="already froze"):
        context["ledger"].link_evidence(
            context["supported_revision"].id,
            later_context.id,
            relation="context",
            recorded_at_utc=utc(3),
        )
    context["ledger"].link_evidence(
        context["supported_revision"].id,
        later_context.id,
        relation="context",
        recorded_at_utc=utc(4),
    )
    with session_factory() as session:
        payload = IndustryChainMapQueryService(
            IndustryChainMapRepository(session)
        ).get_map(industry_map.id).to_dict()
    evidence = payload["frozen_snapshot"]["nodes"][0]["revision"][
        "linked_claim_revisions"
    ][0]["evidence"]
    assert [item["source_title"] for item in evidence] == ["Official source"]


def test_missing_claim_evidence_is_explicit_in_frozen_read(session_factory):
    context = build_case_claims(session_factory)
    ledger = context["ledger"]
    claim = ledger.create_claim(
        context["case"].id,
        claim_key="missing-evidence",
        statement="This draft claim has no evidence yet.",
        claim_kind="fact",
        claim_status="draft",
        information_cutoff_date=date(2026, 3, 3),
        recorded_at_utc=utc(3),
    )
    claim_revision = revision_for(
        session_factory, ClaimRevision, "claim_id", claim.id
    )
    industry_map = create_map(session_factory, context)
    commands = IndustryChainMapCommandService(session_factory)
    observation = commands.create_observation(
        industry_map.id,
        observation_key="missing-evidence-observation",
        observation_kind="driver",
        title="Unresolved driver",
        assertion_status="draft",
        information_cutoff_date=date(2026, 3, 3),
        claim_revision_ids=(claim_revision.id,),
        recorded_at_utc=utc(3),
    )
    observation_revision = revision_for(
        session_factory,
        IndustryMapObservationRevision,
        "observation_id",
        observation.id,
    )
    commands.append_map_revision(
        industry_map.id,
        title="Map with explicit missing evidence",
        scope="Missing evidence must remain visible.",
        information_cutoff_date=date(2026, 3, 3),
        observation_revision_ids=(observation_revision.id,),
        recorded_at_utc=utc(3),
    )
    with session_factory() as session:
        payload = IndustryChainMapQueryService(
            IndustryChainMapRepository(session)
        ).get_map(industry_map.id).to_dict()
    assert len(payload["missing_evidence"]) == 1
    assert payload["missing_evidence"][0]["claim_key"] == "missing-evidence"
    assert payload["frozen_snapshot"]["observations"][0]["revision"][
        "evidence_summary"
    ]["missing_evidence_claim_count"] == 1


def test_append_only_guard_rejects_updates_and_deletes(session_factory):
    context = build_case_claims(session_factory)
    industry_map = create_map(session_factory, context)
    with session_factory() as session:
        row = session.get(IndustryMapNode, uuid4())
        assert row is None
        stored = session.get(type(industry_map), industry_map.id)
        stored.map_key = "mutated"
        with pytest.raises(EvidenceLedgerImmutableError):
            session.commit()
        session.rollback()
        stored = session.get(type(industry_map), industry_map.id)
        session.delete(stored)
        with pytest.raises(EvidenceLedgerImmutableError):
            session.commit()
        session.rollback()


def test_query_is_deterministic_strict_json_and_api_is_read_only(session_factory):
    map_id = build_industry_chain_map_fixture(session_factory)
    app.dependency_overrides[get_industry_alpha_session_factory] = lambda: session_factory
    try:
        client = TestClient(app)
        listed = client.get("/industry-alpha/maps")
        detail = client.get(f"/industry-alpha/maps/{map_id}")
        assert listed.status_code == 200
        assert listed.json()["map_count"] == 1
        assert detail.status_code == 200
        assert detail.json()["notices"]["read_only"] is True
        assert detail.json() == client.get(f"/industry-alpha/maps/{map_id}").json()
        json.dumps(detail.json(), allow_nan=False)
        assert client.get("/industry-alpha/maps?as_of_cutoff=bad").status_code == 422
        assert client.get(f"/industry-alpha/maps/{uuid4()}").status_code == 404
        assert client.get(
            f"/industry-alpha/maps/{map_id}?as_of_cutoff=2026-07-01"
        ).status_code == 404
        assert client.post("/industry-alpha/maps", json={}).status_code == 405
        for method in (client.put, client.patch, client.delete):
            assert method(f"/industry-alpha/maps/{map_id}").status_code == 405
    finally:
        app.dependency_overrides.clear()


def test_fixture_and_import_paths_do_not_access_network(session_factory, monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    map_id = build_industry_chain_map_fixture(session_factory)
    with session_factory() as session:
        result = IndustryChainMapQueryService(
            IndustryChainMapRepository(session)
        ).get_map(map_id).to_dict()
    assert result["notices"]["read_only"] is True
