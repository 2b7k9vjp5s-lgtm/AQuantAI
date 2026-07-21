from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

import backend.api.industry_research as industry_api
from backend.main import app
from industry_alpha.beneficiary_workspace_repository import (
    IndustryBeneficiaryWorkspaceDataError,
)
from industry_alpha.errors import EvidenceLedgerNotFound


class DummySession:
    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        return False


def _fake_session_factory():
    return DummySession()


def _override_session_dependency():
    yield _fake_session_factory


class DictContract:
    def __init__(self, payload):
        self.payload = payload

    def to_dict(self):
        return self.payload


class FakeService:
    def list_maps(self, *, as_of_cutoff=None):
        return DictContract(
            {
                "as_of_cutoff": None if as_of_cutoff is None else as_of_cutoff.isoformat(),
                "maps": [
                    {
                        "map_id": str(UUID(int=1)),
                        "map_key": "memory",
                        "latest_revision": {
                            "revision_id": str(UUID(int=2)),
                            "revision_no": 1,
                            "title": "Memory chain",
                            "scope": "Scope",
                            "information_cutoff_date": "2026-07-20",
                            "recorded_at_utc": "2026-07-21T01:00:00Z",
                        },
                    }
                ],
                "notices": {"not_investment_advice": True},
            }
        )

    def get_workspace(self, map_id, *, as_of_cutoff=None):
        if map_id == UUID(int=999):
            raise EvidenceLedgerNotFound("map not found")
        return DictContract(
            {
                "as_of_cutoff": None if as_of_cutoff is None else as_of_cutoff.isoformat(),
                "industry_map": {
                    "map_id": str(map_id),
                    "map_key": "memory",
                },
                "latest_revision": {
                    "revision_id": str(UUID(int=2)),
                    "revision_no": 1,
                },
                "frozen_snapshot": {"observations": []},
                "map_evidence_summary": {},
                "beneficiaries": [],
                "detail_routes": {},
                "notices": {"not_investment_advice": True},
            }
        )


class FailingService:
    def list_maps(self, *, as_of_cutoff=None):
        raise IndustryBeneficiaryWorkspaceDataError("raw database detail")


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_industry_research_page_is_served() -> None:
    client = TestClient(app)

    response = client.get("/industry-research")

    assert response.status_code == 200
    assert "产业受益公司研究" in response.text
    assert "已录入受益公司全量" in response.text
    assert "不是全市场排名" in response.text


def test_page_script_uses_safe_dom_and_explicit_map_selection() -> None:
    script = (
        Path(__file__).resolve().parents[1]
        / "industry_research"
        / "static"
        / "industry_research.js"
    ).read_text(encoding="utf-8")

    assert "innerHTML" not in script
    assert 'mapSelect.value = preferred' in script
    assert '请选择产业地图' in script
    assert 'firstElementChild.value = ""' in script
    assert "/industry-alpha/beneficiaries/" not in script
    assert "beneficiary_detail_path" in script


def test_selector_and_workspace_api_return_read_only_contract(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.setattr(industry_api, "_service", lambda _session: FakeService())
    app.dependency_overrides[
        industry_api.get_industry_research_session_factory
    ] = _override_session_dependency
    client = TestClient(app)

    try:
        maps_response = client.get(
            "/industry-research/maps?as_of_cutoff=2026-07-21"
        )
        workspace_response = client.get(
            f"/industry-research/maps/{UUID(int=1)}/workspace"
            "?as_of_cutoff=2026-07-21"
        )
    finally:
        _clear_overrides()

    assert maps_response.status_code == 200
    assert maps_response.json()["maps"][0]["map_key"] == "memory"
    assert workspace_response.status_code == 200
    assert workspace_response.json()["beneficiaries"] == []
    assert workspace_response.json()["notices"]["not_investment_advice"] is True


def test_missing_map_returns_404(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.setattr(industry_api, "_service", lambda _session: FakeService())
    app.dependency_overrides[
        industry_api.get_industry_research_session_factory
    ] = _override_session_dependency
    client = TestClient(app)

    try:
        response = client.get(
            f"/industry-research/maps/{UUID(int=999)}/workspace"
        )
    finally:
        _clear_overrides()

    assert response.status_code == 404
    assert response.json()["detail"] == "map not found"


def test_malformed_uuid_and_date_return_422_before_query(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.setattr(industry_api, "_service", lambda _session: FakeService())
    app.dependency_overrides[
        industry_api.get_industry_research_session_factory
    ] = _override_session_dependency
    client = TestClient(app)

    try:
        uuid_response = client.get(
            "/industry-research/maps/not-a-uuid/workspace"
        )
        date_response = client.get(
            "/industry-research/maps?as_of_cutoff=not-a-date"
        )
    finally:
        _clear_overrides()

    assert uuid_response.status_code == 422
    assert date_response.status_code == 422


def test_missing_database_configuration_returns_503(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    client = TestClient(app)

    response = client.get("/industry-research/maps")

    assert response.status_code == 503
    assert "database configuration" in response.json()["detail"]


def test_data_integrity_failure_is_redacted_as_503(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.setattr(industry_api, "_service", lambda _session: FailingService())
    app.dependency_overrides[
        industry_api.get_industry_research_session_factory
    ] = _override_session_dependency
    client = TestClient(app)

    try:
        response = client.get("/industry-research/maps")
    finally:
        _clear_overrides()

    assert response.status_code == 503
    assert "raw database detail" not in response.json()["detail"]
    assert "database query failed" in response.json()["detail"]
