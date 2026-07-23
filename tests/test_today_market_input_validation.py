from fastapi.testclient import TestClient

import backend.api.today_market as today_market_api
from backend.main import app


def test_snapshot_selection_validation_precedes_database_construction(monkeypatch) -> None:
    def reject_engine(*_args, **_kwargs):
        raise AssertionError("database engine must not be created")

    monkeypatch.setattr(today_market_api, "build_engine", reject_engine)
    test_client = TestClient(app)
    boundaries = (
        "as_of_cutoff=2026-04-05"
        "&as_of_recorded_at_utc=2026-04-06T12:00:00Z"
    )

    missing = test_client.get(f"/today-market/api/snapshot?{boundaries}")
    invalid = test_client.get(
        f"/today-market/api/snapshot?{boundaries}&equity_series_key=not-an-exact-key"
    )

    assert missing.status_code == 422
    assert missing.json()["detail"]["code"] == "today_market_equity_selection_required"
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "today_market_series_key_invalid"
