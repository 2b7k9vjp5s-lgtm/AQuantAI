import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import re

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


def test_dashboard_page_and_local_assets_are_available() -> None:
    client = TestClient(app)

    page = client.get("/dashboard")
    stylesheet = client.get("/dashboard/static/dashboard.css")
    script = client.get("/dashboard/static/dashboard.js")

    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert "AQuantAI Dashboard" in page.text
    assert "Local fixture/sample research data" in page.text
    assert "Research disclaimer" in page.text
    assert "<form" not in page.text.lower()
    assert "<button" not in page.text.lower()
    assert stylesheet.status_code == 200
    assert script.status_code == 200


def test_dashboard_page_uses_only_existing_safe_json_endpoints() -> None:
    script = (Path(__file__).resolve().parents[1] / "dashboard" / "static" / "dashboard.js").read_text(encoding="utf-8")

    assert set(re.findall(r'fetchJson\("(/dashboard/[^\"]+)"\)', script)) == {
        "/dashboard/overview",
        "/dashboard/report",
    }
    assert "innerHTML" not in script
    assert "eval(" not in script
    assert "new Function" not in script
    assert "`" not in script
    assert "textContent" in script
    assert "No local fixture rows are available" in script


def test_dashboard_page_preserves_existing_endpoint_contracts() -> None:
    client = TestClient(app)

    root = client.get("/")
    health = client.get("/health")
    overview = client.get("/dashboard/overview")
    report = client.get("/dashboard/report")

    assert root.json()["status"] == "v0.1 research-only baseline"
    assert health.json() == {"status": "ok"}
    assert overview.json()["page_id"] == "dashboard_overview"
    assert report.json()["page_id"] == "dashboard_report"
    assert overview.json()["read_only"] is True
    assert report.json()["read_only"] is True


def test_dashboard_preserves_explicit_empty_inputs() -> None:
    overview = build_dashboard_overview([], {}, [], {}, []).to_dict()
    report = build_dashboard_report({}).to_dict()

    assert overview["sections"]["factor_summary"]["rows"] == []
    assert overview["sections"]["backtest_summary"]["metrics"] == []
    assert overview["sections"]["ml_summary"]["rows"] == []
    assert overview["source_refs"] == []
    assert overview["sections"]["research_report_summary"]["title"] == ""
    assert report["title"] == ""
    assert report["source_refs"] == []
    assert report["read_only"] is True
