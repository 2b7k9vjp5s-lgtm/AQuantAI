from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.api.industry_alpha import get_industry_alpha_session_factory
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
import industry_alpha.product_workspace_models  # noqa: F401


def factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, build_session_factory(engine)


def client_with_database():
    engine, session_factory = factory()
    app.dependency_overrides[get_industry_alpha_session_factory] = lambda: session_factory
    return engine, TestClient(app)


def mutation_headers(client: TestClient) -> dict[str, str]:
    token = client.get("/api/document-import/csrf").json()["csrf_token"]
    return {"Origin": "http://testserver", "X-AQuantAI-CSRF": token}


def case_body() -> dict:
    return {
        "case_key": "api-company-case",
        "case_type": "company",
        "title": "Example company",
        "research_question": "What is supported by accepted evidence?",
        "created_by": "local-reviewer",
        "information_cutoff_date": "2026-08-20",
        "content": {"company_profile": "Initial draft."},
        "company_name": "Example company",
        "stock_code": "000001",
    }


def test_workspace_page_and_api_golden_draft_path() -> None:
    engine, client = client_with_database()
    try:
        page = client.get("/research-workspace")
        assert page.status_code == 200
        assert "研究案例" in page.text
        assert "导入与审核队列" in page.text
        assert "新手操作指引" in page.text
        assert "Pending Review" not in page.text
        guide = client.get("/research-workspace/guide")
        assert guide.status_code == 200
        assert "从零开始完成一次研究闭环" in guide.text
        assert "明确接受并写入" in guide.text
        assert client.get("/research-workspace/static/workspace.css").status_code == 200
        script = client.get("/research-workspace/static/workspace.js")
        assert script.status_code == 200
        assert "innerHTML" not in script.text
        assert "待审核证据" in script.text
        assert "已接受证据" in script.text
        assert "rejectButton" in client.get("/document-import/static/document_import.js").text
        assert 'id="reviewer-note"' in client.get("/document-import").text

        response = client.post(
            "/api/v1/research-cases",
            json=case_body(),
            headers=mutation_headers(client),
        )
        assert response.status_code == 201
        created = response.json()
        case_id = created["case"]["case_id"]
        assert created["current_revision"]["revision_no"] == 1
        assert created["authoritative_revision"] is None

        listed = client.get("/api/v1/research-cases?case_type=company")
        assert listed.status_code == 200
        assert listed.json()["items"][0]["stock_code"] == "000001"
        dashboard = client.get("/api/v1/workspace/dashboard").json()
        assert dashboard["case_count"] == 1
        assert dashboard["company_case_count"] == 1

        report = client.get(f"/api/v1/research-cases/{case_id}/reports/markdown")
        assert report.status_code == 200
        assert "No accepted evidence is bound" in report.text
        assert "not investment advice" in report.text
        search = client.get("/api/v1/search?q=Example")
        assert search.status_code == 200
        assert search.json()["items"][0]["kind"] == "research_case"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_mutations_require_local_csrf_and_state_conflicts_are_typed() -> None:
    engine, client = client_with_database()
    try:
        assert client.post("/api/v1/research-cases", json=case_body()).status_code == 403
        created = client.post(
            "/api/v1/research-cases",
            json=case_body(),
            headers=mutation_headers(client),
        ).json()
        case_id = created["case"]["case_id"]
        response = client.post(
            f"/api/v1/research-cases/{case_id}/revisions",
            headers=mutation_headers(client),
            json={
                "expected_latest_revision_no": 1,
                "title": "Unsupported final",
                "research_question": "What is supported?",
                "created_by": "local-reviewer",
                "information_cutoff_date": "2026-08-20",
                "workflow_state": "completed",
                "conclusion_status": "supported",
                "content": {"research_conclusion": "Unsupported."},
                "evidence_ids": [],
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "authoritative_revision_requires_evidence"
        missing = client.get("/api/v1/research-cases/00000000-0000-0000-0000-000000000000")
        assert missing.status_code == 404
        assert missing.json()["detail"]["code"] == "case_not_found"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
