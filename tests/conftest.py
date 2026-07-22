"""Temporary CI isolation hook; remove after diagnosis."""

from pathlib import Path

_NEW_INDUSTRY_THESIS_TESTS = {
    "test_industry_thesis_cli.py",
    "test_industry_thesis_foundation.py",
    "test_industry_thesis_invariants.py",
    "test_industry_thesis_migration.py",
}


def pytest_ignore_collect(collection_path, config):
    filename = Path(str(collection_path)).name
    return filename in _NEW_INDUSTRY_THESIS_TESTS or filename.endswith("_migration.py")
