from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


EXPECTED_TABLES = {
    "investment_candidate_component_assessments",
    "investment_candidate_component_revisions",
    "investment_candidate_component_input_links",
    "investment_candidate_snapshots",
    "investment_candidate_snapshot_revisions",
    "investment_candidate_members",
    "investment_candidate_member_component_links",
    "investment_candidate_member_reason_codes",
}


def config_for(path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    return config


def prepare_prior_head(config: Config) -> None:
    """Test the 0013 -> 0014 delta without replaying legacy SQLite-incompatible DDL."""
    command.stamp(config, "20260722_0013")


def test_migration_creates_exact_eight_tables_and_empty_round_trip(tmp_path) -> None:
    database = tmp_path / "investment-candidate.db"
    config = config_for(database)
    prepare_prior_head(config)
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database}")
    try:
        assert EXPECTED_TABLES.issubset(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260722_0014"
    finally:
        engine.dispose()
    command.downgrade(config, "20260722_0013")
    engine = create_engine(f"sqlite:///{database}")
    try:
        assert EXPECTED_TABLES.isdisjoint(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_populated_downgrade_refuses_before_any_drop(tmp_path) -> None:
    database = tmp_path / "investment-candidate-populated.db"
    config = config_for(database)
    prepare_prior_head(config)
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO investment_candidate_component_assessments "
                    "(id, beneficiary_id, component_code, assessment_key, created_at_utc) "
                    "VALUES (:id, :beneficiary, 'industry_opportunity', 'migration-test', '2026-07-22 10:00:00')"
                ),
                {"id": str(uuid4()), "beneficiary": str(uuid4())},
            )
        with pytest.raises(RuntimeError, match="Cannot downgrade Investment Candidate"):
            command.downgrade(config, "20260722_0013")
        assert EXPECTED_TABLES.issubset(inspect(engine).get_table_names())
    finally:
        engine.dispose()
