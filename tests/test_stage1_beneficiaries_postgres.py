from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from backend.database.engine import build_engine, build_session_factory
from industry_alpha.errors import EvidenceLedgerImmutableError
from industry_alpha.stage1_commands import (
    MapAssertionRevisionInput,
    Stage1BeneficiaryCommandService,
)
from industry_alpha.stage1_fixtures import build_stage1_beneficiary_fixture
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryAssertionLink,
    Stage1BeneficiaryClaimLink,
    Stage1BeneficiaryRevision,
    Stage1CandidatePool,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)


@pytest.fixture(scope="module")
def postgres_database_url() -> Iterator[str]:
    database_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    if "test" not in (make_url(database_url).database or "").lower():
        pytest.fail("TEST_DATABASE_URL must target a database whose name contains 'test'.")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield database_url
    command.downgrade(config, "base")


@pytest.fixture(autouse=True)
def clean_stage1(postgres_database_url: str) -> Iterator[None]:
    engine = build_engine(postgres_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE research_cases, ingestion_runs CASCADE"))
        yield
    finally:
        engine.dispose()


def utc(day: int, hour: int = 10) -> datetime:
    return datetime(2026, 7, day, hour, tzinfo=timezone.utc)


def revision_inputs(factory, beneficiary_id, revision_no=1):
    with factory() as session:
        revision = session.scalar(
            select(Stage1BeneficiaryRevision).where(
                Stage1BeneficiaryRevision.beneficiary_id == beneficiary_id,
                Stage1BeneficiaryRevision.revision_no == revision_no,
            )
        )
        links = list(
            session.scalars(
                select(Stage1BeneficiaryAssertionLink).where(
                    Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                    == revision.id
                )
            )
        )
        claims = tuple(
            session.scalars(
                select(Stage1BeneficiaryClaimLink.claim_revision_id).where(
                    Stage1BeneficiaryClaimLink.beneficiary_revision_id == revision.id
                )
            )
        )
    assertions = []
    for link in links:
        for kind in ("node", "relationship", "observation"):
            item = getattr(link, f"{kind}_revision_id")
            if item is not None:
                assertions.append(MapAssertionRevisionInput(kind, item))
    return revision, tuple(assertions), claims


def test_migration_head_and_v05b_round_trip_preserve_prior_schema(
    postgres_database_url: str,
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", postgres_database_url)
    engine = build_engine(postgres_database_url)
    try:
        assert "stage1_beneficiaries" in inspect(engine).get_table_names()
        command.downgrade(config, "20260719_0006")
        tables = inspect(engine).get_table_names()
        assert "stage1_beneficiaries" not in tables
        assert "industry_maps" in tables
        assert "research_cases" in tables
        command.upgrade(config, "head")
        assert "stage1_candidate_pool_memberships" in inspect(engine).get_table_names()
        with engine.connect() as connection:
            assert connection.scalar(
                text("SELECT version_num FROM alembic_version")
            ) == "20260719_0011"
    finally:
        engine.dispose()


def test_postgres_concurrent_beneficiary_revision_numbers_are_sequential(
    postgres_database_url: str,
):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    fixture = build_stage1_beneficiary_fixture(factory)
    revision, assertions, claims = revision_inputs(
        factory, fixture.secondary_beneficiary_id
    )

    def append(index: int):
        return Stage1BeneficiaryCommandService(factory).append_beneficiary_revision(
            fixture.secondary_beneficiary_id,
            selected_map_revision_id=revision.selected_map_revision_id,
            stock_basic_record_id=revision.stock_basic_record_id,
            beneficiary_kind="secondary",
            assessment_status="supported",
            rationale_summary=f"Concurrent append {index}.",
            information_cutoff_date=date(2026, 7, 10),
            assertion_revisions=assertions,
            claim_revision_ids=claims,
            recorded_at_utc=utc(10),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(append, (1, 2)))
    assert sorted(item.revision_no for item in results) == [2, 3]
    with factory() as session:
        numbers = list(
            session.scalars(
                select(Stage1BeneficiaryRevision.revision_no)
                .where(
                    Stage1BeneficiaryRevision.beneficiary_id
                    == fixture.secondary_beneficiary_id
                )
                .order_by(Stage1BeneficiaryRevision.revision_no)
            )
        )
    assert numbers == [1, 2, 3]
    engine.dispose()


def test_postgres_concurrent_candidate_pool_revision_numbers_are_sequential(
    postgres_database_url: str,
):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    fixture = build_stage1_beneficiary_fixture(factory)
    direct, _, _ = revision_inputs(factory, fixture.direct_beneficiary_id, 1)
    secondary, _, _ = revision_inputs(factory, fixture.secondary_beneficiary_id, 1)

    def append(index: int):
        return Stage1BeneficiaryCommandService(factory).append_candidate_pool_revision(
            fixture.candidate_pool_id,
            selected_map_revision_id=direct.selected_map_revision_id,
            title=f"Concurrent candidate pool {index}",
            scope="Exact supported revisions without ranking.",
            information_cutoff_date=date(2026, 7, 10),
            beneficiary_revision_ids=(direct.id, secondary.id),
            recorded_at_utc=utc(10),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(append, (1, 2)))
    assert sorted(item.revision_no for item in results) == [2, 3]
    engine.dispose()


def test_postgres_exact_membership_fk_and_append_only_guards(
    postgres_database_url: str,
):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    fixture = build_stage1_beneficiary_fixture(factory)
    direct, _, _ = revision_inputs(factory, fixture.direct_beneficiary_id, 1)
    secondary, _, _ = revision_inputs(factory, fixture.secondary_beneficiary_id, 1)
    with factory() as session:
        pool_revision = session.scalar(
            select(Stage1CandidatePoolRevision).where(
                Stage1CandidatePoolRevision.candidate_pool_id
                == fixture.candidate_pool_id
            )
        )
        isolated_pool_revision = Stage1CandidatePoolRevision(
            candidate_pool_id=fixture.candidate_pool_id,
            revision_no=99,
            selected_map_revision_id=direct.selected_map_revision_id,
            title="Constraint probe",
            scope="Test-only exact identity constraint probe.",
            information_cutoff_date=date(2026, 7, 10),
            recorded_at_utc=utc(10),
            supersedes_revision_id=pool_revision.id,
        )
        session.add(isolated_pool_revision)
        session.flush()
        session.add(
            Stage1CandidatePoolMembership(
                candidate_pool_revision_id=isolated_pool_revision.id,
                beneficiary_id=fixture.secondary_beneficiary_id,
                beneficiary_revision_id=direct.id,
                recorded_at_utc=utc(10),
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
    with factory() as session:
        beneficiary = session.get(Stage1Beneficiary, fixture.direct_beneficiary_id)
        beneficiary.stock_code = "999999"
        with pytest.raises(EvidenceLedgerImmutableError):
            session.flush()
    engine.dispose()
