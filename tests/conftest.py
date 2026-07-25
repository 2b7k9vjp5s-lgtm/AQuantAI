"""Temporary CI diagnostic for Issue #236; remove before final validation."""

from __future__ import annotations

import pytest


_TARGET = "test_postgres_identical_concurrent_commit_serializes_to_one_output"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    skipped = pytest.mark.skip(reason="temporary Issue #236 PostgreSQL diagnostic")
    for item in items:
        if item.name != _TARGET:
            item.add_marker(skipped)
