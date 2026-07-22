"""Alembic environment for explicit AQuantAI schema migrations."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.database.models import Base
import backend.database.canonical_price_models  # noqa: F401 - register canonical price metadata
import industry_alpha.models  # noqa: F401 - register v0.5A metadata
import industry_alpha.chain_map_models  # noqa: F401 - register v0.5B metadata
import industry_alpha.stage1_models  # noqa: F401 - register v0.5C metadata
import industry_alpha.stage2_models  # noqa: F401 - register v0.6A metadata
import industry_alpha.stage2_expectations_models  # noqa: F401 - register v0.6B metadata
import industry_alpha.stage2_assessments_models  # noqa: F401 - register v0.6C metadata
import industry_alpha.stage2_judgments_models  # noqa: F401 - register v0.6D metadata
import industry_alpha.beneficiary_semantics_models  # noqa: F401 - register typed semantics
import industry_alpha.investment_candidate_models  # noqa: F401 - register investment candidate metadata
import industry_alpha.normalized_valuation_models  # noqa: F401 - register normalized valuation metadata
import industry_alpha.normalized_valuation_context  # noqa: F401 - register typed v0.6B context columns
import industry_alpha.industry_thesis_models  # noqa: F401 - register industry thesis metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.getenv("DATABASE_URL", "").strip()
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
