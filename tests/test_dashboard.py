import pytest
from fastapi.testclient import TestClient

from agent import RESEARCH_DISCLAIMER
from backend.main import app
from dashboard import build_dashboard_overview, build_dashboard_report
from dashboard.schemas import DashboardPage


def test_dashboard_overview_payload_contains_required_sections() -> None:
    payload = build_dashboard_overview().to_dict()

    assert payload["read_only"] is True
    assert payload["disclaimer"] == RESEARCH_DISCLAIMER
    assert payload["sections"]["project_overview"]["metrics"][0]["value"] == "v0.1 baseline"
    assert set(payload["sections"]) == {
        "project_overview",
        "factor_summary",
        "backtest_summary",
        "ml_summary",
        "research_report_summary",
        "risk_and_disclaimer",
    }
    assert payload["source_refs"]


def test_dashboard_report_preserves_source_references_and_disclaimer() -> None:
    payload = build_dashboard_report().to_dict()

    assert payload["disclaimer"] == RESEARCH_DISCLAIMER
    assert "docs/agent.md" in payload["source_refs"]
    assert payload["sections"]["research_report_summary"]["source_refs"]


def test_dashboard_payload_exposes_no_trading_actions() -> None:
    payload = build_dashboard_overview().to_dict()
    actions = {action.lower() for action in payload["allowed_actions"]}

    assert actions == {"view", "inspect", "export_research"}
    assert not {"trade", "order", "buy", "sell", "hold"} & actions


def test_dashboard_rejects_disallowed_actions() -> None:
    page = DashboardPage(page_id="bad", title="Bad", sections={}, allowed_actions=["view", "trade"])

    with pytest.raises(ValueError, match="disallowed actions"):
        page.to_dict()


def test_dashboard_fastapi_endpoints_are_read_only() -> None:
    client = TestClient(app)

    overview = client.get("/dashboard/overview")
    report = client.get("/dashboard/report")

    assert overview.status_code == 200
    assert report.status_code == 200
    assert overview.json()["read_only"] is True
    assert report.json()["read_only"] is True
    assert overview.json()["disclaimer"] == RESEARCH_DISCLAIMER
    assert report.json()["disclaimer"] == RESEARCH_DISCLAIMER
