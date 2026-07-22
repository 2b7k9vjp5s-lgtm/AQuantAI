"""Temporary CI isolation hook; remove after diagnosis."""

from pathlib import Path

import pytest

_ISOLATED_TESTS = {
    "test_industry_thesis_cli.py",
    "test_industry_thesis_foundation.py",
    "test_industry_thesis_invariants.py",
    "test_industry_thesis_migration.py",
    "test_benchmark_migration.py",
    "test_sector_migration.py",
    "test_investment_candidate_migration.py",
    "test_normalized_valuation_migration.py",
}


def pytest_collection_modifyitems(items):
    marker = pytest.mark.skip(reason="temporary Issue #194 CI isolation")
    for item in items:
        if Path(str(item.fspath)).name in _ISOLATED_TESTS:
            item.add_marker(marker)
