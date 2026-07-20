from datetime import date, datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient

import backend.api.evidence_intelligence as evidence_api
from backend.main import app
from industry_alpha.evidence_intelligence_repository import (
    EVENT_TYPE_EVIDENCE,
    EvidenceIntelligenceRow,
)

UTC = timezone.utc
NOW = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)


class DummySession:
    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        return False


class FakeRepository:
    def __init__(self, _session) -> None:
        pass

    def list_events(self, **_kwargs):
        return (
            EvidenceIntelligenceRow(
                event_type=EVENT_TYPE_EVIDENCE,
                event_id=UUID(int=1),
                object_id=UUID(int=2),
                revision_no=None,
                primary_text="Official evidence",
                primary_text_source_field="source_title",
                summary="Evidence summary.",
                information_date=date(2026, 7, 19),
                information_cutoff_date=None,
                recorded_at_utc=NOW,
                source_kind="official",
                evidence_grade="A",
                source_locator="https://example.com/source",
                supersedes_id=None,
                detail_path=f"/industry-alpha/cases/{UUID(int=2)}",
            ),
        )


def _fake_session_factory():
    return DummySession()


def _override_session_dependency():
    yield _fake_session_factory


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_evidence_intelligence_page_is_served() -> None:
    client = TestClient(app)

    response = client.get("/evidence-intelligence")

    assert response.status_code == 200
    assert "研究变化" in response.text
    assert "不是投资吸引力排序" in response.text


def test_feed_api_returns_neutral_read_only_contract(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.setattr(evidence_api, "EvidenceIntelligenceRepository", FakeRepository)
    app.dependency_overrides[
        evidence_api.get_evidence_intelligence_session_factory
    ] = _override_session_dependency
    app.dependency_overrides[evidence_api.get_evaluated_at_utc] = lambda: NOW
    client = TestClient(app)

    try:
        response = client.get("/evidence-intelligence/feed?limit=25")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["events"][0]["event_type"] == EVENT_TYPE_EVIDENCE
    assert payload["events"][0]["primary_text"] == "Official evidence"
    assert payload["notices"]["not_investment_advice"] is True
    assert payload["recorded_from"] == "2026-07-13T12:00:00Z"
    assert payload["recorded_to"] == "2026-07-20T12:00:00Z"


def test_invalid_cursor_fails_before_database_construction(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    app.dependency_overrides[evidence_api.get_evaluated_at_utc] = lambda: NOW
    client = TestClient(app)

    try:
        response = client.get("/evidence-intelligence/feed?cursor=invalid")
    finally:
        _clear_overrides()

    assert response.status_code == 422
    assert "cursor" in response.json()["detail"]


def test_missing_database_configuration_returns_503(monkeypatch) -> None:
    _clear_overrides()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    app.dependency_overrides[evidence_api.get_evaluated_at_utc] = lambda: NOW
    client = TestClient(app)

    try:
        response = client.get("/evidence-intelligence/feed")
    finally:
        _clear_overrides()

    assert response.status_code == 503
    assert "database configuration" in response.json()["detail"]


def test_naive_recorded_time_is_rejected() -> None:
    _clear_overrides()
    app.dependency_overrides[evidence_api.get_evaluated_at_utc] = lambda: NOW
    client = TestClient(app)

    try:
        response = client.get(
            "/evidence-intelligence/feed?recorded_from=2026-07-19T12:00:00"
        )
    finally:
        _clear_overrides()

    assert response.status_code == 422
    assert "UTC offset" in response.json()["detail"]
