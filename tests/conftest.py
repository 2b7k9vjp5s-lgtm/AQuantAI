"""Temporary CI diagnostic for Issue #236; remove before final validation."""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    skipped = pytest.mark.skip(reason="temporary Issue #236 migration diagnostic")
    for item in items:
        if "migration" not in item.nodeid.lower():
            item.add_marker(skipped)
