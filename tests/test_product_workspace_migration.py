from __future__ import annotations

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, text


REVISION = "20260821_0020"
TABLES = {
    "product_research_case_profiles",
    "product_research_revision_contents",
    "product_research_revision_evidence_references",
}


def config_for(path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{path.as_posix()}")
    return config


def prepare_prior_head(database, config) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{database.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE research_cases (id CHAR(32) PRIMARY KEY)"))
        connection.execute(
            text("CREATE TABLE research_case_revisions (id CHAR(32) PRIMARY KEY)")
        )
        connection.execute(text("CREATE TABLE evidence_items (id CHAR(32) PRIMARY KEY)"))
        connection.execute(
            text("CREATE TABLE local_document_review_revisions (id CHAR(32) PRIMARY KEY)")
        )
    engine.dispose()
    command.stamp(config, "20260803_0018")


def test_v1_workspace_migration_empty_upgrade_and_downgrade(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database = tmp_path / "v1-workspace.db"
    config = config_for(database)
    prepare_prior_head(database, config)
    command.upgrade(config, REVISION)
    engine = create_engine(f"sqlite+pysqlite:///{database.as_posix()}")
    try:
        assert TABLES <= set(inspect(engine).get_table_names())
        columns = {
            item["name"]
            for item in inspect(engine).get_columns("local_document_review_revisions")
        }
        assert "reviewer_identity" in columns
    finally:
        engine.dispose()
    command.downgrade(config, "20260803_0018")
    engine = create_engine(f"sqlite+pysqlite:///{database.as_posix()}")
    try:
        assert TABLES.isdisjoint(inspect(engine).get_table_names())
        columns = {
            item["name"]
            for item in inspect(engine).get_columns("local_document_review_revisions")
        }
        assert "reviewer_identity" not in columns
    finally:
        engine.dispose()


def test_populated_workspace_downgrade_fails_before_schema_loss(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database = tmp_path / "v1-workspace-populated.db"
    config = config_for(database)
    prepare_prior_head(database, config)
    command.upgrade(config, REVISION)
    engine = create_engine(f"sqlite+pysqlite:///{database.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO product_research_case_profiles "
                "(case_id, case_type, display_title, created_by, created_at_utc) "
                "VALUES (:id, 'industry', 'Fixture', 'tester', '2026-08-21 00:00:00')"
            ),
            {"id": "00000000000000000000000000000001"},
        )
    engine.dispose()
    with pytest.raises(RuntimeError, match="append-only research data exists"):
        command.downgrade(config, "20260803_0018")
    engine = create_engine(f"sqlite+pysqlite:///{database.as_posix()}")
    try:
        assert TABLES <= set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
