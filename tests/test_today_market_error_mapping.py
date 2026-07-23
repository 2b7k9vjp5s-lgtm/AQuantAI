from fastapi.testclient import TestClient

import backend.api.today_market as today_market_api
from backend.api.today_market import get_today_market_session_factory
from backend.database.series import SnapshotSeriesError
from backend.main import app
from market_cockpit.repository import MarketCockpitSelectionError


class _DummySession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class _DummySessionFactory:
    def __call__(self):
        return _DummySession()


def _snapshot_url() -> str:
    return (
        "/today-market/api/snapshot"
        "?as_of_cutoff=2026-04-05"
        "&as_of_recorded_at_utc=2026-04-06T12:00:00Z"
        f"&equity_series_key={'0' * 64}"
    )


def _request_with_service_failure(monkeypatch, error: Exception):
    def reject_snapshot(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(
        today_market_api.MarketCockpitService,
        "build_snapshot",
        reject_snapshot,
    )
    app.dependency_overrides[get_today_market_session_factory] = (
        lambda: _DummySessionFactory()
    )
    try:
        return TestClient(app).get(_snapshot_url())
    finally:
        app.dependency_overrides.clear()


def test_snapshot_identity_conflict_maps_to_stable_409(monkeypatch) -> None:
    response = _request_with_service_failure(
        monkeypatch,
        SnapshotSeriesError("persisted identity mismatch"),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "today_market_snapshot_identity_conflict",
        "message": "所选本地数据身份发生冲突，请重新读取数据列表。",
    }


def test_incompatible_exact_selection_maps_to_stable_422(monkeypatch) -> None:
    response = _request_with_service_failure(
        monkeypatch,
        MarketCockpitSelectionError("incompatible exact graph"),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "today_market_selection_incompatible",
        "message": "所选本地数据无法在当前边界下组合，请调整明确选择。",
    }
