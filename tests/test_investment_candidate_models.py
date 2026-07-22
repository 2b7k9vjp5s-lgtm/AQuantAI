from fastapi.testclient import TestClient

from backend.main import app
from industry_alpha.investment_candidate_models import (
    COMPONENT_CODES,
    INVESTMENT_CANDIDATE_MODELS,
)


EXPECTED_TABLES = {
    "investment_candidate_component_assessments",
    "investment_candidate_component_revisions",
    "investment_candidate_component_input_links",
    "investment_candidate_snapshots",
    "investment_candidate_snapshot_revisions",
    "investment_candidate_members",
    "investment_candidate_member_component_links",
    "investment_candidate_member_reason_codes",
}


def test_exact_eight_table_contract_and_component_vocabulary() -> None:
    assert {model.__tablename__ for model in INVESTMENT_CANDIDATE_MODELS} == EXPECTED_TABLES
    assert COMPONENT_CODES == (
        "industry_opportunity",
        "beneficiary_strength",
        "earnings_conversion",
        "expectation_gap",
        "valuation_context",
        "catalyst_readiness",
        "evidence_quality",
        "risk_penalty",
    )


def test_read_routes_are_get_only_and_page_is_non_advisory() -> None:
    routes = {
        route.path: route.methods
        for route in app.routes
        if route.path.startswith("/investment-candidates") and hasattr(route, "methods")
    }
    assert routes["/investment-candidates/component-revisions/{component_revision_id}"] == {"GET"}
    assert routes["/investment-candidates/snapshot-revisions/{snapshot_revision_id}"] == {"GET"}
    client = TestClient(app)
    page = client.get("/investment-candidates")
    assert page.status_code == 200
    assert "完整受益公司池" in page.text
    assert "不构成买入、卖出、持有" in page.text


def test_exact_id_api_requires_both_as_of_boundaries() -> None:
    client = TestClient(app)
    response = client.get(
        "/investment-candidates/snapshot-revisions/00000000-0000-0000-0000-000000000001"
    )
    assert response.status_code == 422
