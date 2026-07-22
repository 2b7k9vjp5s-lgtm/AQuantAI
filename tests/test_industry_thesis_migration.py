from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


EXPECTED_TABLES = {
    "industry_thesis_session_identities",
    "industry_thesis_session_revisions",
    "industry_thesis_candidate_identities",
    "industry_thesis_candidate_revisions",
    "industry_thesis_output_link_identities",
    "industry_thesis_output_link_revisions",
}


def config_for(path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    return config


def prepare_prior_head(config: Config) -> None:
    """Test the 0015 -> 0016 delta without replaying legacy SQLite-incompatible DDL."""
    command.stamp(config, "20260722_0015")


def test_migration_creates_exact_six_tables_and_empty_round_trip(tmp_path) -> None:
    database = tmp_path / "industry-thesis.db"
    config = config_for(database)
    prepare_prior_head(config)
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database}")
    try:
        assert EXPECTED_TABLES.issubset(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260722_0016"
    finally:
        engine.dispose()

    command.downgrade(config, "20260722_0015")
    engine = create_engine(f"sqlite:///{database}")
    try:
        assert EXPECTED_TABLES.isdisjoint(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_populated_downgrade_refuses_before_any_drop(tmp_path) -> None:
    database = tmp_path / "industry-thesis-populated.db"
    config = config_for(database)
    prepare_prior_head(config)
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO industry_thesis_session_identities "
                    "(id, created_recorded_utc, created_by_kind, state, latest_revision_number) "
                    "VALUES (:id, '2026-07-22 16:00:00', 'local_user', 'active', 0)"
                ),
                {"id": str(uuid4())},
            )
        with pytest.raises(RuntimeError, match="Cannot downgrade Industry Thesis Orchestration"):
            command.downgrade(config, "20260722_0015")
        assert EXPECTED_TABLES.issubset(inspect(engine).get_table_names())
    finally:
        engine.dispose()
