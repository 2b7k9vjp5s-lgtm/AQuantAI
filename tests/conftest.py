"""Temporary CI diagnostic for Issue #236; remove before final validation."""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    skipped = pytest.mark.skip(reason="temporary Issue #236 migration diagnostic")
    module = "tests/test_industry_thesis_migration.py"
    passed_target = "test_migration_creates_exact_six_tables_and_empty_round_trip"
    for item in items:
        nodeid = item.nodeid.replace("\\", "/")
        if module not in nodeid or passed_target in nodeid:
            item.add_marker(skipped)
