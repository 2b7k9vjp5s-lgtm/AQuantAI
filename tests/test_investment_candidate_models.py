from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.main import app
import industry_alpha.investment_candidate_commands as commands
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


def test_price_manifest_requires_exact_pair_and_validation(monkeypatch) -> None:
    manifest = {
        "canonical_price_revision_id": uuid4(),
        "comparison_eligibility_revision_id": None,
    }
    with pytest.raises(InvestmentCandidateError, match="one exact pair"):
        commands._validate_member_price_manifest(
            object(), manifest, date(2026, 7, 22), datetime(2026, 7, 22, tzinfo=timezone.utc)
        )

    calls = []
    monkeypatch.setattr(commands, "_price_graph", lambda *args: calls.append(args))
    manifest["comparison_eligibility_revision_id"] = uuid4()
    commands._validate_member_price_manifest(
        object(), manifest, date(2026, 7, 22), datetime(2026, 7, 22, tzinfo=timezone.utc)
    )
    assert len(calls) == 1


class _ScalarSession:
    def __init__(self, scalar_value):
        self.scalar_value = scalar_value

    def scalar(self, _statement):
        return self.scalar_value


def test_claim_and_evidence_require_exact_research_handoff() -> None:
    with pytest.raises(InvestmentCandidateError, match="exact company research handoff"):
        commands._require_exact_research_provenance(
            _ScalarSession(None), kind="claim", target_id=uuid4(), company_research_id=uuid4()
        )
    commands._require_exact_research_provenance(
        _ScalarSession(object()), kind="evidence", target_id=uuid4(), company_research_id=uuid4()
    )


class _ScalarsSession:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self, _statement):
        return self.rows


def test_supported_evidence_quality_reuses_other_component_provenance() -> None:
    quality_id = uuid4()
    other_id = uuid4()
    claim_id = uuid4()
    evidence_id = uuid4()
    components = {
        "evidence_quality": SimpleNamespace(id=quality_id, assessment_state="supported"),
        "industry_opportunity": SimpleNamespace(id=other_id, assessment_state="supported"),
    }
    rows = [
        SimpleNamespace(component_revision_id=quality_id, claim_revision_id=claim_id, evidence_id=None),
        SimpleNamespace(component_revision_id=quality_id, claim_revision_id=None, evidence_id=evidence_id),
        SimpleNamespace(component_revision_id=other_id, claim_revision_id=claim_id, evidence_id=None),
        SimpleNamespace(component_revision_id=other_id, claim_revision_id=None, evidence_id=evidence_id),
    ]
    commands._validate_evidence_quality_overlap(_ScalarsSession(rows), components)
    with pytest.raises(InvestmentCandidateError, match="reuse exact claim and evidence"):
        commands._validate_evidence_quality_overlap(_ScalarsSession(rows[:2]), components)
    components["industry_opportunity"].assessment_state = "missing"
    with pytest.raises(InvestmentCandidateError, match="reuse exact claim and evidence"):
        commands._validate_evidence_quality_overlap(_ScalarsSession(rows), components)
