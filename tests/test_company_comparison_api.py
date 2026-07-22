from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

import backend.api.company_comparison as comparison_api
from backend.main import app
from industry_alpha.company_comparison_query import CompanyComparisonSelectorError
from industry_alpha.company_comparison_repository import CompanyComparisonDataError


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
    def __init__(self):
        self.calls = []

    def get_comparison(
        self,
        candidate_pool_revision_id,
        *,
        as_of_cutoff,
        as_of_recorded_at_utc,
    ):
        self.calls.append(
            (
                candidate_pool_revision_id,
                as_of_cutoff,
                as_of_recorded_at_utc,
            )
        )
        return DictContract(
            {
                "selector": {
                    "candidate_pool_revision_id": str(candidate_pool_revision_id),
                    "as_of_cutoff": as_of_cutoff.isoformat(),
                    "as_of_recorded_at_utc": as_of_recorded_at_utc.isoformat(),
                },
                "universe": {
                    "title": "Fixture Pool",
                    "member_count": 1,
                },
                "rows": [
                    {
                        "identity": {"stock_code": "000001.SZ"},
                        "legacy_stage1": {},
                        "typed_semantics": {"state": "missing"},
                        "company_research": {"state": "missing"},
                        "detail_routes": {},
                    }
                ],
                "notices": {
                    "not_investment_advice": True,
                    "no_scores_rankings_or_priority_labels": True,
                },
                "query_count": 13,
            }
        )


class InvalidSelectorService(FakeService):
    def get_comparison(self, *args, **kwargs):
        raise CompanyComparisonSelectorError("explicit UTC boundary is invalid")


class IntegrityFailureService(FakeService):
    def get_comparison(self, *args, **kwargs):
        raise CompanyComparisonDataError("private frozen-boundary diagnostic")


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _endpoint(pool_revision_id=UUID(int=1)) -> str:
    return (
        f"/company-comparison/candidate-pool-revisions/{pool_revision_id}"
        "?as_of_cutoff=2026-07-22"
        "&as_of_recorded_at_utc=2026-07-22T00%3A00%3A00Z"
    )


def test_company_comparison_page_is_served() -> None:
    response = TestClient(app).get("/company-comparison")

    assert response.status_code == 200
    assert "公司研究组件对比" in response.text
    assert "不会默认选择第一条记录" in response.text
    assert "中性标识顺序" in response.text
    assert "完整保留一个候选池修订中的全部公司" in response.text
    assert "估值区域只展示方法与状态是否存在" in response.text


def test_page_script_uses_safe_dom_and_requires_explicit_submit() -> None:
    script = (
        Path(__file__).resolve().parents[1]
        / "company_comparison"
        / "static"
        / "company_comparison.js"
    ).read_text(encoding="utf-8")

    assert "innerHTML" not in script
    assert "textContent" in script
    assert "replaceChildren" in script
    assert 'form.addEventListener("submit"' in script
    assert "fetch(" in script
    assert "as_of_cutoff" in script
    assert "as_of_recorded_at_utc" in script
    assert "candidate_pool_revision_id" in script
    assert "sort(" not in script or "rows.sort" not in script
    assert "score" not in script.lower()
    assert "rank" not in script.lower()


def test_read_only_api_passes_all_explicit_selector_values(monkeypatch) -> None:
    _clear_overrides()
    fake = FakeService()
    monkeypatch.setattr(comparison_api, "_service", lambda _session: fake)
    app.dependency_overrides[
        comparison_api.get_company_comparison_session_factory
    ] = _override_session_dependency

    try:
        response = TestClient(app).get(_endpoint())
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["rows"][0]["identity"]["stock_code"] == "000001.SZ"
    assert response.json()["notices"]["not_investment_advice"] is True
    assert len(fake.calls) == 1
    pool_id, cutoff, recorded = fake.calls[0]
    assert pool_id == UUID(int=1)
    assert cutoff == date(2026, 7, 22)
    assert recorded == datetime(2026, 7, 22, tzinfo=timezone.utc)


def test_missing_selector_values_and_mutating_method_are_rejected(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.setattr(comparison_api, "_service", lambda _session: FakeService())
    app.dependency_overrides[
        comparison_api.get_company_comparison_session_factory
    ] = _override_session_dependency
    client = TestClient(app)

    try:
        missing_cutoff = client.get(
            f"/company-comparison/candidate-pool-revisions/{UUID(int=1)}"
            "?as_of_recorded_at_utc=2026-07-22T00%3A00%3A00Z"
        )
        missing_recorded = client.get(
            f"/company-comparison/candidate-pool-revisions/{UUID(int=1)}"
            "?as_of_cutoff=2026-07-22"
        )
        post_response = client.post(_endpoint())
    finally:
        _clear_overrides()

    assert missing_cutoff.status_code == 422
    assert missing_recorded.status_code == 422
    assert post_response.status_code == 405


def test_invalid_selector_returns_typed_422(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.setattr(
        comparison_api, "_service", lambda _session: InvalidSelectorService()
    )
    app.dependency_overrides[
        comparison_api.get_company_comparison_session_factory
    ] = _override_session_dependency

    try:
        response = TestClient(app).get(_endpoint())
    finally:
        _clear_overrides()

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_comparison_selector"


def test_integrity_failure_is_redacted_as_409(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.setattr(
        comparison_api, "_service", lambda _session: IntegrityFailureService()
    )
    app.dependency_overrides[
        comparison_api.get_company_comparison_session_factory
    ] = _override_session_dependency

    try:
        response = TestClient(app).get(_endpoint())
    finally:
        _clear_overrides()

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "company_comparison_integrity_failure"
    assert "private frozen-boundary diagnostic" not in response.text


def test_missing_database_configuration_returns_503(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.delenv("DATABASE_URL", raising=False)

    response = TestClient(app).get(_endpoint())

    assert response.status_code == 503
    assert "database configuration" in response.json()["detail"]
