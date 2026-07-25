"""Temporary Issue #236 migration diagnostic; remove before final validation."""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_issue236_upgrade_phase(tmp_path) -> None:
    database = tmp_path / "industry-thesis-upgrade-only.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.stamp(config, "20260722_0015")
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database}")
    try:
        columns = {
            item["name"]: item
            for item in inspect(engine).get_columns(
                "industry_thesis_output_link_revisions"
            )
        }
        assert columns["accepted_candidate_pool_revision_id"]["nullable"] is True
        assert {
            "accepted_session_revision_id",
            "reviewed_session_revision_id",
            "research_case_id",
            "output_contract_version",
            "reviewed_plan_fingerprint_sha256",
            "ordered_owner_output_bindings_json",
        }.issubset(columns)
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == "20260725_0017"
            )
    finally:
        engine.dispose()
