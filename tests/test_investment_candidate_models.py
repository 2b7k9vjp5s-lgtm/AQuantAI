from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from industry_alpha.investment_candidate_commands import (
    InvestmentCandidateError,
    _parse_component,
)
from industry_alpha.investment_candidate_models import (
    COMPONENT_CODES,
    INVESTMENT_CANDIDATE_MODELS,
    VERIFICATION_ITEM_CODES,
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
    assert VERIFICATION_ITEM_CODES == (
        "certification",
        "order",
        "capacity",
        "production",
        "financial_confirmation",
        "customer_confirmation",
        "other_explicit",
    )


def test_read_routes_are_get_only_and_page_is_non_advisory() -> None:
    paths = app.openapi()["paths"]
    assert set(paths["/investment-candidates/component-revisions/{component_revision_id}"]) == {"get"}
    assert set(paths["/investment-candidates/snapshot-revisions/{snapshot_revision_id}"]) == {"get"}
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


def _component_input(**overrides):
    raw = {
        "assessment_key": "verification-contract",
        "beneficiary_id": str(uuid4()),
        "beneficiary_revision_id": str(uuid4()),
        "company_research_revision_id": str(uuid4()),
        "component_code": "catalyst_readiness",
        "assessment_state": "missing",
        "verification_state": "verified",
        "verification_material": False,
        "missing_reason": "not yet assessed",
        "rationale": "bounded rationale",
        "falsification_condition": "bounded falsification condition",
        "falsification_state": "inactive",
        "information_cutoff_date": "2026-07-22",
        "recorded_at_utc": "2026-07-22T06:00:00+00:00",
        "recorded_by": "test",
        "inputs": [],
    }
    raw.update(overrides)
    return raw


def test_verification_item_contract_is_closed_and_explicit() -> None:
    parsed = _parse_component(
        _component_input(
            verification_state="pending",
            verification_material=True,
            verification_item_code="certification",
            verification_question="Has the customer certification completed?",
        )
    )
    assert parsed["verification_item_code"] == "certification"
    assert parsed["verification_question"].startswith("Has the customer")

    with pytest.raises(InvestmentCandidateError, match="closed item code"):
        _parse_component(
            _component_input(
                verification_state="pending",
                verification_material=True,
                verification_item_code="social_buzz",
                verification_question="Is attention rising?",
            )
        )
    with pytest.raises(InvestmentCandidateError, match="forbids"):
        _parse_component(
            _component_input(
                verification_state="verified",
                verification_material=False,
                verification_item_code="certification",
                verification_question="This must not be stored for verified state",
            )
        )
