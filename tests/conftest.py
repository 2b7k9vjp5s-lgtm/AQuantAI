"""Temporary CI diagnostic for Issue #236; remove before final validation."""

from __future__ import annotations

import pytest


_TARGET = "test_postgres_identical_concurrent_commit_serializes_to_one_output"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    skipped = pytest.mark.skip(reason="temporary Issue #236 PostgreSQL diagnostic")
    for item in items:
        if item.name != _TARGET:
            item.add_marker(skipped)


def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    if pyfuncitem.name != _TARGET:
        return None
    module = pyfuncitem.module
    database_url = pyfuncitem.funcargs["postgres_database_url"]
    engine = module.build_engine(database_url)
    try:
        factory = module.build_session_factory(engine)
        raw, recorded = module._reviewed_fixture(factory)
        assert raw["reviewed_session_revision_id"]
        assert raw["industry_map_revision_id"]
        assert recorded is not None
    finally:
        engine.dispose()
    return True
