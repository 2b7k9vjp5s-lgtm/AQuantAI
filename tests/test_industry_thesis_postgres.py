from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import os
from uuid import UUID

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import make_url

from backend.database import build_engine, build_session_factory
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_models import (
    INDUSTRY_THESIS_MODELS,
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_rules import IndustryThesisError

UTC = timezone.utc
BASE_TIME = datetime(2026, 7, 22, 17, 30, tzinfo=UTC)
EXPECTED_TABLES = {model.__tablename__ for model in INDUSTRY_THESIS_MODELS}


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self._value = value

    def __call__(self) -> datetime:
        return self._value


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
    engine = build_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("TRUNCATE industry_thesis_session_identities CASCADE")
            )
    finally:
        engine.dispose()
    command.downgrade(config, "base")


@pytest.fixture(autouse=True)
def clean_industry_thesis(postgres_database_url: str) -> Iterator[None]:
    engine = build_engine(postgres_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("TRUNCATE industry_thesis_session_identities CASCADE")
            )
        yield
    finally:
        with engine.begin() as connection:
            connection.execute(
                text("TRUNCATE industry_thesis_session_identities CASCADE")
            )
        engine.dispose()


def _config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _input(*, workflow_state: str = "draft") -> dict:
    return {
        "thesis_text_original": "PostgreSQL offline industry thesis",
        "thesis_title_reviewed": None,
        "driver_type": "unknown",
        "analysis_horizon_kind": "unknown",
        "market_scope": [
            {
                "market_namespace": "CN_A",
                "exchange_namespace": None,
                "security_type": "common_equity",
                "include_status": "active",
                "listed_instrument_ids": [],
            }
        ],
        "chain_boundary": {},
        "exclusions": [],
        "seed_companies": [],
        "seed_products": [],
        "seed_technologies": [],
        "seed_bottlenecks": [],
        "draft_graph": {},
        "coverage_state": "coverage_unknown",
        "workflow_state": workflow_state,
        "information_cutoff_date": date(2026, 7, 22).isoformat(),
        "revision_note": "PostgreSQL contract fixture",
    }


def test_postgres_0015_to_0016_and_empty_round_trip(
    postgres_database_url: str,
) -> None:
    config = _config(postgres_database_url)
    engine = build_engine(postgres_database_url)
    try:
        command.downgrade(config, "20260722_0015")
        assert EXPECTED_TABLES.isdisjoint(inspect(engine).get_table_names())
        command.upgrade(config, "head")
        assert EXPECTED_TABLES.issubset(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert connection.scalar(
                text("SELECT version_num FROM alembic_version")
            ) == "20260722_0016"
    finally:
        engine.dispose()


def test_postgres_concurrent_session_revision_is_expected_latest_protected(
    postgres_database_url: str,
) -> None:
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    created = IndustryThesisCommandService(
        factory,
        clock=FixedClock(BASE_TIME),
    ).create_session(_input())
    session_id = created["session_id"]

    def revise(index: int):
        service = IndustryThesisCommandService(
            factory,
            clock=FixedClock(BASE_TIME + timedelta(seconds=index)),
        )
        try:
            return service.revise_session(
                {
                    "session_id": session_id,
                    "expected_latest_revision_number": 1,
                    "changes": {
                        "workflow_state": "candidate_build_ready",
                        "thesis_title_reviewed": f"Reviewed thesis {index}",
                    },
                    "revision_note": f"Concurrent revision {index}",
                }
            )
        except IndustryThesisError as exc:
            return exc.code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(revise, (1, 2)))
        assert sum(isinstance(item, dict) for item in results) == 1
        assert "industry_thesis_revision_conflict" in results
        with factory() as session:
            identity = session.get(
                IndustryThesisSessionIdentity,
                UUID(session_id),
            )
            assert identity.latest_revision_number == 2
            assert session.scalar(
                select(func.count()).select_from(IndustryThesisSessionRevision)
            ) == 2
    finally:
        engine.dispose()


def test_postgres_populated_downgrade_refuses_before_any_drop(
    postgres_database_url: str,
) -> None:
    config = _config(postgres_database_url)
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    try:
        IndustryThesisCommandService(
            factory,
            clock=FixedClock(BASE_TIME),
        ).create_session(_input())
        with pytest.raises(
            RuntimeError,
            match="Cannot downgrade Industry Thesis Orchestration",
        ):
            command.downgrade(config, "20260722_0015")
        assert EXPECTED_TABLES.issubset(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert connection.scalar(
                text("SELECT version_num FROM alembic_version")
            ) == "20260722_0016"
    finally:
        engine.dispose()
