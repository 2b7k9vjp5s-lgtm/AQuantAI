"""Temporary CI diagnostic for Issue #236; remove before final validation."""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    skipped = pytest.mark.skip(reason="temporary Issue #236 migration diagnostic")
    target = "test_v1_output_rows_refuse_downgrade_before_any_loss"
    for item in items:
        if target not in item.nodeid:
            item.add_marker(skipped)
