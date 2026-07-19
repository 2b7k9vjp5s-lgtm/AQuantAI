from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_engine, build_session_factory
from backend.database.models import Base
from industry_alpha.stage2_judgments_commands import Stage2JudgmentCommandService
from industry_alpha.stage2_judgments_fixtures import (
    _boundary,
    build_stage2_judgment_fixture,
    build_stage2_judgment_fixture_payload,
)
from industry_alpha.stage2_judgments_models import Stage2CompanyJudgmentRevision, Stage2IndustryJudgmentRevision


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
def clean_database(postgres_database_url: str) -> Iterator[None]:
    engine = build_engine(postgres_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE research_cases, ingestion_runs CASCADE"))
        yield
    finally:
        engine.dispose()


def _append_data(factory, fixture, kind: str, index: int) -> dict:
    with factory() as session:
        boundary = _boundary(session, fixture.v06c.later_catalyst_revision_id, fixture.v06c.later_risk_revision_id)
    common = {
        **boundary,
        "outcome": "uncertain", "evidence_state": "disputed", "confidence": "low",
        "decision_criteria": f"Concurrent exact boundary {index}.",
        "rationale": "Contradictory evidence remains visible.",
        "uncertainty": "The result remains uncertain.",
        "follow_up_verification": "后续验证清单：检查新的可归因一手资料。",
        "information_cutoff_date": date(2026, 7, 20),
        "recorded_at_utc": datetime(2026, 7, 20, 12, tzinfo=timezone.utc),
    }
    if kind == "industry":
        common.update(driver_durability="Uncertain.", value_pool_direction="Not affirmed.", chain_bottleneck_support="Disputed boundary retained.")
    else:
        common.update(beneficiary_credibility="Uncertain.", financial_transmission_credibility="Not affirmed.", execution_risks="Disputed boundary retained.")
    return common


def test_postgres_v06d_migration_round_trip(postgres_database_url: str):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", postgres_database_url)
    engine = build_engine(postgres_database_url)
    try:
        assert "stage2_industry_judgments" in inspect(engine).get_table_names()
        assert "stage2_company_judgments" in inspect(engine).get_table_names()
        command.downgrade(config, "20260719_0010")
        assert "stage2_industry_judgments" not in inspect(engine).get_table_names()
        assert "stage2_catalyst_assessments" in inspect(engine).get_table_names()
        command.upgrade(config, "20260719_0011")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260719_0011"
    finally:
        engine.dispose()


@pytest.mark.parametrize("kind", ["industry", "company"])
def test_postgres_concurrent_revision_numbers(postgres_database_url: str, kind: str):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    fixture = build_stage2_judgment_fixture(factory)
    identity = fixture.affirmed_industry_id if kind == "industry" else fixture.affirmed_company_id

    def append(index: int):
        service = Stage2JudgmentCommandService(factory)
        method = service.append_industry_judgment_revision if kind == "industry" else service.append_company_judgment_revision
        return method(identity, **_append_data(factory, fixture, kind, index))

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(append, (1, 2)))
    assert sorted(item.revision_no for item in results) == [3, 4]
    model = Stage2IndustryJudgmentRevision if kind == "industry" else Stage2CompanyJudgmentRevision
    with factory() as session:
        rows = list(session.scalars(select(model).where(model.judgment_id == identity).order_by(model.revision_no)))
    assert [item.revision_no for item in rows] == [1, 2, 3, 4]
    assert rows[-1].supersedes_revision_id == rows[-2].id
    engine.dispose()


def test_postgres_fixture_semantics_repeat_on_clean_database(postgres_database_url: str):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    payloads = []
    try:
        for _ in range(2):
            with engine.begin() as connection:
                connection.execute(text("TRUNCATE research_cases, ingestion_runs CASCADE"))
            fixture = build_stage2_judgment_fixture(factory)
            payloads.append(build_stage2_judgment_fixture_payload(factory, fixture))
    finally:
        engine.dispose()
    sqlite_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        Base.metadata.create_all(sqlite_engine)
        sqlite_factory = build_session_factory(sqlite_engine)
        sqlite_fixture = build_stage2_judgment_fixture(sqlite_factory)
        sqlite_payload = build_stage2_judgment_fixture_payload(sqlite_factory, sqlite_fixture)
    finally:
        sqlite_engine.dispose()
    assert payloads[0] == payloads[1]
    assert payloads[0] == sqlite_payload
