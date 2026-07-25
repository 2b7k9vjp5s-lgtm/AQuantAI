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
    """Test the 0015 -> current Industry Thesis delta without legacy SQLite DDL."""
    command.stamp(config, "20260722_0015")


def _insert_output_identity(connection, *, session_id: str, output_id: str) -> None:
    connection.execute(
        text(
            "INSERT INTO industry_thesis_output_link_identities "
            "(id, session_id, output_key, created_recorded_utc, latest_revision_number) "
            "VALUES (:id, :session_id, :output_key, "
            "'2026-07-22 16:00:00', 1)"
        ),
        {"id": output_id, "session_id": session_id, "output_key": "b" * 64},
    )


def _legacy_output_values() -> dict[str, str | int]:
    return {
        "id": str(uuid4()),
        "output_link_id": str(uuid4()),
        "session_id": str(uuid4()),
        "session_revision_id": str(uuid4()),
        "map_id": str(uuid4()),
        "map_revision_id": str(uuid4()),
        "pool_revision_id": str(uuid4()),
        "transaction_id": str(uuid4()),
    }


def test_migration_creates_exact_six_tables_and_empty_round_trip(tmp_path) -> None:
    database = tmp_path / "industry-thesis.db"
    config = config_for(database)
    prepare_prior_head(config)
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database}")
    try:
        assert EXPECTED_TABLES.issubset(inspect(engine).get_table_names())
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

    command.downgrade(config, "20260722_0015")
    engine = create_engine(f"sqlite:///{database}")
    try:
        assert EXPECTED_TABLES.isdisjoint(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_legacy_output_rows_refuse_upgrade_before_schema_mutation(tmp_path) -> None:
    database = tmp_path / "industry-thesis-legacy-output.db"
    config = config_for(database)
    prepare_prior_head(config)
    command.upgrade(config, "20260722_0016")
    engine = create_engine(f"sqlite:///{database}")
    values = _legacy_output_values()
    try:
        with engine.begin() as connection:
            _insert_output_identity(
                connection,
                session_id=values["session_id"],
                output_id=values["output_link_id"],
            )
            connection.execute(
                text(
                    "INSERT INTO industry_thesis_output_link_revisions "
                    "(id, output_link_id, revision_number, session_revision_id, "
                    "accepted_industry_map_identity_id, accepted_industry_map_revision_id, "
                    "accepted_candidate_pool_revision_id, "
                    "ordered_beneficiary_revision_ids_json, coverage_state, "
                    "acceptance_plan_fingerprint_sha256, owner_transaction_id, "
                    "information_cutoff_date, recorded_at_utc, "
                    "supersedes_output_link_revision_id) "
                    "VALUES (:id, :output_link_id, 1, :session_revision_id, "
                    ":map_id, :map_revision_id, :pool_revision_id, "
                    "'[\"legacy\"]', 'partial_local_coverage', :fingerprint, "
                    ":transaction_id, '2026-07-22', '2026-07-22 16:00:00', NULL)"
                ),
                {**values, "fingerprint": "a" * 64},
            )
        with pytest.raises(RuntimeError, match="cannot be derived without guessing"):
            command.upgrade(config, "head")
        columns = {
            item["name"]
            for item in inspect(engine).get_columns(
                "industry_thesis_output_link_revisions"
            )
        }
        assert "accepted_session_revision_id" not in columns
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == "20260722_0016"
            )
    finally:
        engine.dispose()


def test_v1_output_rows_refuse_downgrade_before_any_loss(tmp_path) -> None:
    database = tmp_path / "industry-thesis-v1-output.db"
    config = config_for(database)
    prepare_prior_head(config)
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database}")
    values = _legacy_output_values()
    accepted_session_id = str(uuid4())
    reviewed_session_id = str(uuid4())
    research_case_id = str(uuid4())
    try:
        with engine.begin() as connection:
            _insert_output_identity(
                connection,
                session_id=values["session_id"],
                output_id=values["output_link_id"],
            )
            connection.execute(
                text(
                    "INSERT INTO industry_thesis_output_link_revisions "
                    "(id, output_link_id, revision_number, session_revision_id, "
                    "accepted_session_revision_id, reviewed_session_revision_id, "
                    "research_case_id, accepted_industry_map_identity_id, "
                    "accepted_industry_map_revision_id, "
                    "accepted_candidate_pool_revision_id, output_contract_version, "
                    "reviewed_plan_fingerprint_sha256, "
                    "ordered_beneficiary_revision_ids_json, "
                    "ordered_owner_output_bindings_json, coverage_state, "
                    "acceptance_plan_fingerprint_sha256, owner_transaction_id, "
                    "information_cutoff_date, recorded_at_utc, "
                    "supersedes_output_link_revision_id) "
                    "VALUES (:id, :output_link_id, 1, :accepted_session_id, "
                    ":accepted_session_id, :reviewed_session_id, :research_case_id, "
                    ":map_id, :map_revision_id, NULL, :contract_version, "
                    ":reviewed_fingerprint, '[\"accepted\"]', "
                    "'[{\"sequence\":0}]', 'partial_local_coverage', "
                    ":fingerprint, :transaction_id, '2026-07-22', "
                    "'2026-07-22 16:00:00', NULL)"
                ),
                {
                    **values,
                    "accepted_session_id": accepted_session_id,
                    "reviewed_session_id": reviewed_session_id,
                    "research_case_id": research_case_id,
                    "contract_version": "aquantai.industry-thesis-output-links.v1",
                    "reviewed_fingerprint": "c" * 64,
                    "fingerprint": "a" * 64,
                },
            )
        with pytest.raises(
            RuntimeError,
            match="Cannot downgrade Industry Thesis owner acceptance",
        ):
            command.downgrade(config, "20260722_0016")
        columns = {
            item["name"]
            for item in inspect(engine).get_columns(
                "industry_thesis_output_link_revisions"
            )
        }
        assert "accepted_session_revision_id" in columns
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == "20260725_0017"
            )
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
