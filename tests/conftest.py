"""Temporary CI diagnostic for Issue #236; remove before final validation."""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Run only the fresh Industry Thesis migration round-trip test."""

    skipped = pytest.mark.skip(reason="temporary Issue #236 migration diagnostic")
    target = "test_migration_creates_exact_six_tables_and_empty_round_trip"
    for item in items:
        if target not in item.nodeid:
            item.add_marker(skipped)
