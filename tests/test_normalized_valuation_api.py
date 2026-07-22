from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.api.normalized_valuation import _boundary
from backend.main import app


EXPECTED_PATHS = {
    "/normalized-valuation/financial-observation-revisions/{revision_id}",
    "/normalized-valuation/metric-revisions/{revision_id}",
    "/normalized-valuation/comparison-set-revisions/{revision_id}",
    "/normalized-valuation/expectation-gap-revisions/{revision_id}",
}


def test_openapi_exposes_exact_four_read_only_paths() -> None:
    paths = set(app.openapi()["paths"])
    assert EXPECTED_PATHS.issubset(paths)
    for path in EXPECTED_PATHS:
        assert set(app.openapi()["paths"][path]) == {"get"}


def test_missing_read_boundaries_fail_before_database_connection(monkeypatch) -> None:
    def forbidden_engine():
        raise AssertionError("database connection must not be attempted")

    monkeypatch.setattr("backend.api.normalized_valuation.build_engine", forbidden_engine)
    client = TestClient(app)
    response = client.get(
        f"/normalized-valuation/metric-revisions/{uuid4()}"
    )
    assert response.status_code == 422


def test_boundary_requires_explicit_utc_and_ordered_dates() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _boundary(date(2026, 6, 30), datetime(2026, 7, 1, 0, 0))
    assert exc_info.value.status_code == 422

    with pytest.raises(HTTPException) as exc_info:
        _boundary(
            date(2026, 7, 2),
            datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc),
        )
    assert exc_info.value.status_code == 422

    value = datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)
    assert _boundary(date(2026, 6, 30), value) == value
