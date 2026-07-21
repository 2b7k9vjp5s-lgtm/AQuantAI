from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

import backend.api.company_research as company_api
from backend.main import app
from industry_alpha.company_research_workspace_repository import (
    CompanyResearchWorkspaceDataError,
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
    def list_research(self, *, as_of_cutoff=None):
        return DictContract({
            "as_of_cutoff": None if as_of_cutoff is None else as_of_cutoff.isoformat(),
            "research": [{
                "company_research_id": str(UUID(int=1)),
                "source": "fixture",
                "stock_code": "000001.SZ",
                "stock_name": "Fixture Company",
                "latest_revision": {"revision_no": 2},
            }],
            "notices": {"not_investment_advice": True},
        })

    def get_workspace(self, research_id, *, as_of_cutoff=None):
        if research_id == UUID(int=999):
            raise EvidenceLedgerNotFound("company research not found")
        return DictContract({
            "as_of_cutoff": None if as_of_cutoff is None else as_of_cutoff.isoformat(),
            "identity": {"company_research_id": str(research_id)},
            "frozen_stage1": {},
            "company_research": {},
            "hypotheses": [],
            "expectations": [],
            "valuation_observations": [],
            "catalysts": [],
            "risks": [],
            "industry_judgments": [],
            "company_judgments": [],
            "evidence_summary": {},
            "detail_routes": {},
            "notices": {"not_investment_advice": True},
        })


class FailingService:
    def list_research(self, *, as_of_cutoff=None):
        raise CompanyResearchWorkspaceDataError("private database diagnostic")


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_company_research_page_is_served() -> None:
    response = TestClient(app).get("/company-research")
    assert response.status_code == 200
    assert "公司研究工作台" in response.text
    assert "不会默认选择第一条" in response.text
    assert "估值观察" in response.text
    assert "不是全市场排名" in response.text


def test_page_script_uses_safe_dom_and_explicit_identity_selection() -> None:
    script = (Path(__file__).resolve().parents[1] / "company_research" / "static" / "company_research.js").read_text(encoding="utf-8")
    assert "innerHTML" not in script
    assert "textContent" in script
    assert "replaceChildren" in script
    assert 'researchSelect.value = ""' in script
    assert "请选择公司研究" in script
    assert 'searchParams.get("company_research_id")' in script
    assert "/company-research/research/${researchId}/workspace" in script
    assert "loadDetail" in script


def test_selector_and_workspace_api_return_read_only_contract(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.setattr(company_api, "_service", lambda _session: FakeService())
    app.dependency_overrides[company_api.get_company_research_session_factory] = _override_session_dependency
    client = TestClient(app)
    try:
        selector = client.get("/company-research/research?as_of_cutoff=2026-07-21")
        workspace = client.get(f"/company-research/research/{UUID(int=1)}/workspace?as_of_cutoff=2026-07-21")
    finally:
        _clear_overrides()
    assert selector.status_code == 200
    assert selector.json()["research"][0]["stock_code"] == "000001.SZ"
    assert workspace.status_code == 200
    assert workspace.json()["identity"]["company_research_id"] == str(UUID(int=1))
    assert workspace.json()["notices"]["not_investment_advice"] is True


def test_missing_identity_returns_404(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.setattr(company_api, "_service", lambda _session: FakeService())
    app.dependency_overrides[company_api.get_company_research_session_factory] = _override_session_dependency
    try:
        response = TestClient(app).get(f"/company-research/research/{UUID(int=999)}/workspace")
    finally:
        _clear_overrides()
    assert response.status_code == 404
    assert response.json()["detail"] == "company research not found"


def test_malformed_uuid_and_date_return_422_before_query(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.setattr(company_api, "_service", lambda _session: FakeService())
    app.dependency_overrides[company_api.get_company_research_session_factory] = _override_session_dependency
    client = TestClient(app)
    try:
        uuid_response = client.get("/company-research/research/not-a-uuid/workspace")
        date_response = client.get("/company-research/research?as_of_cutoff=not-a-date")
    finally:
        _clear_overrides()
    assert uuid_response.status_code == 422
    assert date_response.status_code == 422


def test_missing_database_configuration_returns_503(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    response = TestClient(app).get("/company-research/research")
    assert response.status_code == 503
    assert "database configuration" in response.json()["detail"]


def test_integrity_error_is_redacted_as_503(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.setattr(company_api, "_service", lambda _session: FailingService())
    app.dependency_overrides[company_api.get_company_research_session_factory] = _override_session_dependency
    try:
        response = TestClient(app).get("/company-research/research")
    finally:
        _clear_overrides()
    assert response.status_code == 503
    assert "private database diagnostic" not in response.json()["detail"]
    assert "database query failed" in response.json()["detail"]
