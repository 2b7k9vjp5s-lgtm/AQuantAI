"""Temporary CI diagnostic for Issue #236; remove before final validation."""

from __future__ import annotations

import pytest


_TARGETS = {
    "tests/test_industry_thesis_owner_acceptance_cli.py",
    "tests/test_industry_thesis_owner_acceptance_demo.py",
    "tests/test_industry_thesis_owner_acceptance_readiness.py",
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    skipped = pytest.mark.skip(reason="temporary Issue #236 adapter diagnostic")
    for item in items:
        nodeid = item.nodeid.replace("\\", "/")
        if not any(target in nodeid for target in _TARGETS):
            item.add_marker(skipped)
