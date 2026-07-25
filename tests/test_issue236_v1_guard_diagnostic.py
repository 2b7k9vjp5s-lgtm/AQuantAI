"""Temporary Issue #236 diagnostic; remove before final validation."""

from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def test_issue236_v1_guard_fixture_insert(tmp_path) -> None:
    database = tmp_path / "industry-thesis-v1-identity-insert.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.stamp(config, "20260722_0015")
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database}")
    output_link_id = str(uuid4())
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO industry_thesis_output_link_identities "
                    "(id, session_id, output_key, created_recorded_utc, latest_revision_number) "
                    "VALUES (:id, :session_id, :output_key, "
                    "'2026-07-22 16:00:00', 1)"
                ),
                {
                    "id": output_link_id,
                    "session_id": str(uuid4()),
                    "output_key": "b" * 64,
                },
            )
        with engine.connect() as connection:
            assert connection.scalar(
                text("SELECT count(*) FROM industry_thesis_output_link_identities")
            ) == 1
    finally:
        engine.dispose()
