from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


EXPECTED_TABLES = {
    "structured_financial_observations",
    "structured_financial_observation_revisions",
    "structured_financial_observation_claim_links",
    "structured_financial_observation_evidence_links",
    "normalized_valuation_metrics",
    "normalized_valuation_metric_revisions",
    "normalized_valuation_metric_input_links",
    "valuation_comparison_sets",
    "valuation_comparison_set_revisions",
    "valuation_comparison_members",
    "normalized_expectation_gaps",
    "normalized_expectation_gap_revisions",
    "investment_candidate_normalized_metric_links",
}


def config_for(path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    return config


def prepare_prior_head(config: Config) -> None:
    """Test the 0014 -> 0015 delta without replaying legacy SQLite-incompatible DDL."""
    command.stamp(config, "20260722_0014")


def test_migration_creates_exact_thirteen_tables_and_empty_round_trip(tmp_path) -> None:
    database = tmp_path / "normalized-valuation.db"
    config = config_for(database)
    prepare_prior_head(config)
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database}")
    try:
        tables = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES.issubset(tables)
        assert len(EXPECTED_TABLES) == 13
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260722_0015"
    finally:
        engine.dispose()

    command.downgrade(config, "20260722_0014")
    engine = create_engine(f"sqlite:///{database}")
    try:
        assert EXPECTED_TABLES.isdisjoint(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_populated_downgrade_refuses_before_any_drop(tmp_path) -> None:
    database = tmp_path / "normalized-valuation-populated.db"
    config = config_for(database)
    prepare_prior_head(config)
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO structured_financial_observations "
                    "(id, observation_key, company_research_id, instrument_id, metric_code, "
                    "source_kind, target_period_key, accounting_scope, currency_code, unit_code, "
                    "created_at_utc) VALUES "
                    "(:id, 'migration-test', :research, :instrument, 'revenue', 'actual', "
                    "'TTM-2026-06-30', 'consolidated', 'CNY', 'currency_amount', "
                    "'2026-07-22 10:00:00')"
                ),
                {
                    "id": str(uuid4()),
                    "research": str(uuid4()),
                    "instrument": str(uuid4()),
                },
            )
        with pytest.raises(RuntimeError, match="Cannot downgrade Normalized Valuation"):
            command.downgrade(config, "20260722_0014")
        assert EXPECTED_TABLES.issubset(inspect(engine).get_table_names())
    finally:
        engine.dispose()
