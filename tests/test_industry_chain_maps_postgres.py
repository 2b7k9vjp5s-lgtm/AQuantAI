from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import make_url

from backend.database.engine import build_engine, build_session_factory
from industry_alpha.chain_map_commands import IndustryChainMapCommandService
from industry_alpha.chain_map_models import (
    CHAIN_MAP_MODELS,
    IndustryMap,
    IndustryMapNodeRevision,
    IndustryMapObservationRevision,
    IndustryMapRelationshipRevision,
    IndustryMapRevision,
)
from industry_alpha.commands import EvidenceLedgerCommandService, EvidenceLinkInput
from industry_alpha.errors import (
    EvidenceLedgerImmutableError,
    EvidenceLedgerValidationError,
)
from industry_alpha.models import ClaimRevision


@pytest.fixture(scope="module")
def postgres_database_url() -> Iterator[str]:
    database_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    database_name = make_url(database_url).database or ""
    if "test" not in database_name.lower():
        pytest.fail("TEST_DATABASE_URL must target a database whose name contains 'test'.")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield database_url
    command.downgrade(config, "base")


@pytest.fixture(autouse=True)
def clean_industry_maps(postgres_database_url: str) -> Iterator[None]:
    engine = build_engine(postgres_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE research_cases CASCADE"))
        yield
    finally:
        engine.dispose()


def recorded(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 4, day, hour, tzinfo=timezone.utc)


def build_context(database_url: str):
    factory = build_session_factory(build_engine(database_url))
    ledger = EvidenceLedgerCommandService(factory)
    case = ledger.create_case(
        case_key="postgres-industry-map",
        title="PostgreSQL chain map",
        research_question="Are revisions deterministic?",
        information_cutoff_date=date(2026, 4, 1),
        recorded_at_utc=recorded(1),
    )
    evidence = ledger.add_evidence(
        case.id,
        evidence_grade="A",
        source_kind="official",
        source_title="PostgreSQL evidence",
        information_date=date(2026, 4, 2),
        summary="Attributable evidence.",
        recorded_at_utc=recorded(2),
    )
    claim = ledger.create_claim(
        case.id,
        claim_key="postgres-map-claim",
        statement="A bounded map assertion is supported.",
        claim_kind="fact",
        claim_status="supported",
        information_cutoff_date=date(2026, 4, 2),
        evidence_links=(EvidenceLinkInput(evidence.id, "supports"),),
        recorded_at_utc=recorded(2),
    )
    with factory() as session:
        claim_revision = session.scalar(
            select(ClaimRevision).where(ClaimRevision.claim_id == claim.id)
        )
    maps = IndustryChainMapCommandService(factory)
    industry_map = maps.create_map(
        case.id,
        map_key="postgres-map",
        title="PostgreSQL map",
        scope="Bounded test scope.",
        information_cutoff_date=date(2026, 4, 2),
        recorded_at_utc=recorded(2),
    )
    source = maps.create_node(
        industry_map.id,
        node_key="source",
        label="Source",
        node_kind="component",
        assertion_status="supported",
        information_cutoff_date=date(2026, 4, 2),
        claim_revision_ids=(claim_revision.id,),
        recorded_at_utc=recorded(2),
    )
    target = maps.create_node(
        industry_map.id,
        node_key="target",
        label="Target",
        node_kind="manufacturing",
        assertion_status="supported",
        information_cutoff_date=date(2026, 4, 2),
        claim_revision_ids=(claim_revision.id,),
        recorded_at_utc=recorded(2),
    )
    relationship = maps.create_relationship(
        industry_map.id,
        relationship_key="source-target",
        source_node_id=source.id,
        target_node_id=target.id,
        relation_kind="supplies",
        assertion_status="supported",
        information_cutoff_date=date(2026, 4, 2),
        claim_revision_ids=(claim_revision.id,),
        recorded_at_utc=recorded(2),
    )
    observation = maps.create_observation(
        industry_map.id,
        observation_key="driver",
        observation_kind="driver",
        title="Driver",
        assertion_status="supported",
        information_cutoff_date=date(2026, 4, 2),
        claim_revision_ids=(claim_revision.id,),
        recorded_at_utc=recorded(2),
    )
    return factory, claim_revision, industry_map, source, relationship, observation


def test_postgres_migration_0005_to_head_round_trip_and_check(
    postgres_database_url,
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", postgres_database_url)
    command.downgrade(config, "20260718_0005")
    engine = build_engine(postgres_database_url)
    try:
        assert "industry_maps" not in inspect(engine).get_table_names()
        assert "research_cases" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
    command.upgrade(config, "head")
    command.check(config)
    engine = build_engine(postgres_database_url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert {model.__tablename__ for model in CHAIN_MAP_MODELS} <= tables


def test_postgres_concurrent_map_and_assertion_revision_numbering(
    postgres_database_url,
):
    factory, claim, industry_map, node, relationship, observation = build_context(
        postgres_database_url
    )

    def append_map(index: int) -> int:
        return IndustryChainMapCommandService(factory).append_map_revision(
            industry_map.id,
            title=f"Map revision {index}",
            scope="Concurrent map revision.",
            information_cutoff_date=date(2026, 4, 3),
            recorded_at_utc=recorded(3),
        ).revision_no

    def append_node(index: int) -> int:
        return IndustryChainMapCommandService(factory).append_node_revision(
            node.id,
            label=f"Node revision {index}",
            node_kind="component",
            assertion_status="supported",
            information_cutoff_date=date(2026, 4, 3),
            claim_revision_ids=(claim.id,),
            recorded_at_utc=recorded(3),
        ).revision_no

    def append_relationship(index: int) -> int:
        return IndustryChainMapCommandService(factory).append_relationship_revision(
            relationship.id,
            relation_kind="supplies",
            description=f"Relationship revision {index}",
            assertion_status="supported",
            information_cutoff_date=date(2026, 4, 3),
            claim_revision_ids=(claim.id,),
            recorded_at_utc=recorded(3),
        ).revision_no

    def append_observation(index: int) -> int:
        return IndustryChainMapCommandService(factory).append_observation_revision(
            observation.id,
            title=f"Observation revision {index}",
            assertion_status="supported",
            information_cutoff_date=date(2026, 4, 3),
            claim_revision_ids=(claim.id,),
            recorded_at_utc=recorded(3),
        ).revision_no

    for operation in (
        append_map,
        append_node,
        append_relationship,
        append_observation,
    ):
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(operation, [1, 2])) == [2, 3]
    with factory() as session:
        assert [
            item.revision_no
            for item in session.scalars(
                select(IndustryMapRevision)
                .where(IndustryMapRevision.map_id == industry_map.id)
                .order_by(IndustryMapRevision.revision_no)
            )
        ] == [1, 2, 3]
        assert [
            item.revision_no
            for item in session.scalars(
                select(IndustryMapNodeRevision)
                .where(IndustryMapNodeRevision.node_id == node.id)
                .order_by(IndustryMapNodeRevision.revision_no)
            )
        ] == [1, 2, 3]
        assert session.scalar(
            select(func.count()).select_from(IndustryMapRelationshipRevision)
        ) == 3
        assert session.scalar(
            select(func.count()).select_from(IndustryMapObservationRevision)
        ) == 3


def test_postgres_chronology_failure_rolls_back_and_history_is_immutable(
    postgres_database_url,
):
    factory, claim, industry_map, node, _relationship, _observation = build_context(
        postgres_database_url
    )
    commands = IndustryChainMapCommandService(factory)
    with factory() as session:
        before = tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in CHAIN_MAP_MODELS
        )
    with pytest.raises(EvidenceLedgerValidationError, match="node identity"):
        commands.append_node_revision(
            node.id,
            label="Backdated",
            node_kind="component",
            assertion_status="supported",
            information_cutoff_date=date(2026, 4, 2),
            claim_revision_ids=(claim.id,),
            recorded_at_utc=recorded(2, 11),
        )
    with factory() as session:
        after = tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in CHAIN_MAP_MODELS
        )
        stored = session.get(IndustryMap, industry_map.id)
        stored.map_key = "forbidden"
        with pytest.raises(EvidenceLedgerImmutableError):
            session.commit()
        session.rollback()
    assert after == before
    with factory() as session:
        assert session.get(IndustryMap, industry_map.id).map_key == "postgres-map"
