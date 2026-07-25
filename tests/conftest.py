"""Temporary CI diagnostic for Issue #236; remove before final validation."""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    skipped = pytest.mark.skip(reason="temporary Issue #236 PostgreSQL diagnostic")
    target = "tests/test_industry_thesis_owner_acceptance_postgres.py"
    for item in items:
        if target not in item.nodeid.replace("\\", "/"):
            item.add_marker(skipped)
