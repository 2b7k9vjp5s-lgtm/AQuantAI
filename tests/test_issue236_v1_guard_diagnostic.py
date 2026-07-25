"""Temporary Issue #236 diagnostic; remove before final validation."""

from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def test_issue236_v1_guard_fixture_insert(tmp_path) -> None:
    database = tmp_path / "industry-thesis-v1-guard-insert.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.stamp(config, "20260722_0015")
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database}")
    values = {
        "id": str(uuid4()),
        "output_link_id": str(uuid4()),
        "session_id": str(uuid4()),
        "accepted_session_id": str(uuid4()),
        "reviewed_session_id": str(uuid4()),
        "research_case_id": str(uuid4()),
        "map_id": str(uuid4()),
        "map_revision_id": str(uuid4()),
        "transaction_id": str(uuid4()),
    }
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO industry_thesis_output_link_identities "
                    "(id, session_id, output_key, created_recorded_utc, latest_revision_number) "
                    "VALUES (:output_link_id, :session_id, :output_key, "
                    "'2026-07-22 16:00:00', 1)"
                ),
                {**values, "output_key": "b" * 64},
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
                    "contract_version": "aquantai.industry-thesis-output-links.v1",
                    "reviewed_fingerprint": "c" * 64,
                    "fingerprint": "a" * 64,
                },
            )
        with engine.connect() as connection:
            assert connection.scalar(
                text("SELECT count(*) FROM industry_thesis_output_link_revisions")
            ) == 1
    finally:
        engine.dispose()
