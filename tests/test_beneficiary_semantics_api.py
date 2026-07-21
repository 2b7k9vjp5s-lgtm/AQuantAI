from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

import backend.api.beneficiary_semantics as semantics_api
from backend.main import app
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
    def __init__(self, _repository):
        pass

    def get_profile(self, beneficiary_id, *, as_of_cutoff=None):
        if beneficiary_id == UUID(int=999):
            raise EvidenceLedgerNotFound("semantic profile not found")
        return DictContract(
            {
                "beneficiary": {"beneficiary_id": str(beneficiary_id)},
                "profile": {"profile_id": str(UUID(int=2))},
                "as_of_cutoff": (
                    None if as_of_cutoff is None else as_of_cutoff.isoformat()
                ),
                "latest_revision": {
                    "taxonomy_version": "aquantai.typed-beneficiary-evidence-semantics.v1",
                    "overall_status": "supported",
                    "frozen_stage1": {"legacy_beneficiary_kind": "direct"},
                    "assertions": [],
                },
                "revision_history": [],
                "notices": {"read_only": True},
            }
        )


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_read_only_api_returns_explicit_profile(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.setattr(
        semantics_api, "BeneficiarySemanticQueryService", FakeService
    )
    app.dependency_overrides[
        semantics_api.get_industry_alpha_session_factory
    ] = _override_session_dependency
    client = TestClient(app)
    try:
        response = client.get(
            f"/industry-alpha/beneficiary-semantics/{UUID(int=1)}"
            "?as_of_cutoff=2026-07-21"
        )
    finally:
        _clear_overrides()
    assert response.status_code == 200
    assert response.json()["as_of_cutoff"] == "2026-07-21"
    assert response.json()["latest_revision"]["frozen_stage1"][
        "legacy_beneficiary_kind"
    ] == "direct"


def test_missing_profile_is_404_and_malformed_inputs_are_422(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.setattr(
        semantics_api, "BeneficiarySemanticQueryService", FakeService
    )
    app.dependency_overrides[
        semantics_api.get_industry_alpha_session_factory
    ] = _override_session_dependency
    client = TestClient(app)
    try:
        missing = client.get(
            f"/industry-alpha/beneficiary-semantics/{UUID(int=999)}"
        )
        bad_uuid = client.get(
            "/industry-alpha/beneficiary-semantics/not-a-uuid"
        )
        bad_date = client.get(
            f"/industry-alpha/beneficiary-semantics/{UUID(int=1)}"
            "?as_of_cutoff=not-a-date"
        )
    finally:
        _clear_overrides()
    assert missing.status_code == 404
    assert missing.json()["detail"] == "semantic profile not found"
    assert bad_uuid.status_code == 422
    assert bad_date.status_code == 422


def test_semantic_route_has_no_mutation_method() -> None:
    route_methods = {
        method
        for route in app.routes
        if getattr(route, "path", "").startswith(
            "/industry-alpha/beneficiary-semantics"
        )
        for method in getattr(route, "methods", set())
    }
    assert route_methods == {"GET"}


def test_industry_research_uses_explicit_safe_semantic_loading() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (
        root / "industry_research" / "static" / "industry_research.js"
    ).read_text(encoding="utf-8")
    page = (
        root / "industry_research" / "static" / "industry_research.html"
    ).read_text(encoding="utf-8")
    assert "innerHTML" not in script
    assert "openSemanticDetails" in script
    assert "查看类型化证据语义" in script
    assert "/industry-alpha/beneficiary-semantics/" in script
    assert "semanticDetail.textContent" in script
    assert "semantic-detail" in page
    assert "不会自动映射" in page
    assert "renderBeneficiaries" in script
    assert "openSemanticDetails(item)" in script
