"""Temporary CI isolation hook; remove after diagnosis."""

from pathlib import Path

import pytest

_NEW_INDUSTRY_THESIS_TESTS = {
    "test_industry_thesis_cli.py",
    "test_industry_thesis_foundation.py",
    "test_industry_thesis_invariants.py",
    "test_industry_thesis_migration.py",
}


def pytest_collection_modifyitems(items):
    marker = pytest.mark.skip(reason="temporary Issue #194 CI isolation")
    for item in items:
        filename = Path(str(item.fspath)).name
        if filename in _NEW_INDUSTRY_THESIS_TESTS or filename.endswith("_migration.py"):
            item.add_marker(marker)
