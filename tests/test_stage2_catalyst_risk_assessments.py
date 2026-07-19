from __future__ import annotations

import json
import socket
from types import SimpleNamespace
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.pool import StaticPool

from backend.api.industry_alpha import get_industry_alpha_session_factory
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
from industry_alpha.errors import EvidenceLedgerImmutableError, EvidenceLedgerValidationError
from industry_alpha.stage2_assessments_commands import (
    Stage2AssessmentCommandService,
    _Boundary,
    _validate_status,
)
from industry_alpha.stage2_assessments_fixtures import build_stage2_assessment_fixture
from industry_alpha.stage2_assessments_models import (
    STAGE2_ASSESSMENT_MODELS, Stage2CatalystAssessment, Stage2CatalystAssessmentRevision,
    Stage2CatalystClaimLink, Stage2CatalystExpectationLink, Stage2CatalystHypothesisLink,
    Stage2CatalystValuationLink, Stage2RiskAssessmentRevision,
)
from industry_alpha.stage2_assessments_query import Stage2CatalystQueryService, Stage2RiskQueryService
from industry_alpha.stage2_assessments_repository import Stage2AssessmentRepository
from industry_alpha.stage2_expectations_models import Stage2ExpectationClaimLink


def utc(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 7, day, hour, tzinfo=timezone.utc)


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    yield factory
    engine.dispose()


@pytest.fixture
def built(session_factory):
    return build_stage2_assessment_fixture(session_factory)


def catalyst_payload(factory, identity, cutoff=None):
    with factory() as session:
        return Stage2CatalystQueryService(Stage2AssessmentRepository(session)).get_catalyst(identity, as_of_cutoff=cutoff).to_dict()


def risk_payload(factory, identity, cutoff=None):
    with factory() as session:
        return Stage2RiskQueryService(Stage2AssessmentRepository(session)).get_risk(identity, as_of_cutoff=cutoff).to_dict()


def frozen_inputs(factory, revision_id):
    with factory() as session:
        revision = session.get(Stage2CatalystAssessmentRevision, revision_id)
        hypothesis = session.scalar(select(Stage2CatalystHypothesisLink.hypothesis_revision_id).where(Stage2CatalystHypothesisLink.catalyst_revision_id == revision.id))
        expectation = session.scalar(select(Stage2CatalystExpectationLink.expectation_revision_id).where(Stage2CatalystExpectationLink.catalyst_revision_id == revision.id))
        valuation = session.scalar(select(Stage2CatalystValuationLink.valuation_revision_id).where(Stage2CatalystValuationLink.catalyst_revision_id == revision.id))
        claim = session.scalar(select(Stage2CatalystClaimLink.claim_revision_id).where(Stage2CatalystClaimLink.catalyst_revision_id == revision.id))
    return revision.company_research_revision_id, hypothesis, expectation, valuation, claim


def counts(factory):
    with factory() as session:
        return tuple(session.scalar(select(func.count()).select_from(model)) for model in STAGE2_ASSESSMENT_MODELS)


def append_kwargs(factory, built, *, recorded=utc(20), cutoff=date(2026, 7, 20)):
    research, hypothesis, expectation, valuation, claim = frozen_inputs(factory, built.later_catalyst_revision_id)
    return dict(
        company_research_revision_id=research,
        hypothesis_revision_ids=(hypothesis,), expectation_revision_ids=(expectation,),
        valuation_revision_ids=(valuation,), claim_revision_ids=(claim,),
        catalyst_category="demand", subject="Bounded append-only revision",
        expected_observation_window="尚未获得可靠公开证据", status="disputed", confidence="low",
        trigger_observation_criteria="Primary attributable evidence must resolve the conflict.",
        basis="The exact disputed upstream boundary is preserved.", uncertainty="No outcome is fabricated.",
        information_cutoff_date=cutoff, recorded_at_utc=recorded,
    )


def test_fixture_freezes_exact_handoff_and_is_strict_json(session_factory, built):
    current = catalyst_payload(session_factory, built.supported_catalyst_id)
    historical = catalyst_payload(session_factory, built.supported_catalyst_id, date(2026, 7, 16))
    risk = risk_payload(session_factory, built.supported_risk_id, date(2026, 7, 16))
    assert current["latest_revision"]["revision_no"] == 2
    assert current["latest_revision"]["status"] == "disputed"
    assert historical["latest_revision"]["revision_no"] == 1
    assert historical["latest_revision"]["status"] == "supported"
    assert historical["latest_revision"]["conflicts"] == ()
    assert len(historical["latest_revision"]["frozen_hypothesis_revision_ids"]) == 1
    assert len(historical["latest_revision"]["frozen_expectation_revision_ids"]) == 1
    assert len(historical["latest_revision"]["frozen_valuation_revision_ids"]) == 1
    assert risk["latest_revision"]["thesis_invalidation_condition"]
    assert risk["notices"]["no_good_price_good_timing_or_final_conclusion"]
    json.dumps({"current": current, "historical": historical, "risk": risk}, allow_nan=False, sort_keys=True)


def test_disputed_and_missing_evidence_are_explicit(session_factory, built):
    disputed = catalyst_payload(session_factory, built.disputed_catalyst_id)
    risk = risk_payload(session_factory, built.disputed_risk_id)
    assert disputed["latest_revision"]["conflicts"]
    assert disputed["latest_revision"]["status"] == "disputed"
    assert "尚未获得可靠公开证据" in disputed["latest_revision"]["expected_observation_window"]
    assert "尚未获得可靠公开证据" in risk["latest_revision"]["mitigants"]


def test_d_only_and_missing_evidence_cannot_support_an_assessment():
    claim = SimpleNamespace(claim_status="supported")
    d_only = _Boundary(None, (), (), (), (claim,), ((claim, SimpleNamespace(relation="supports"), SimpleNamespace(evidence_grade="D")),))
    missing = _Boundary(None, (), (), (), (claim,), ())
    with pytest.raises(EvidenceLedgerValidationError, match="A/B/C"):
        _validate_status("supported", d_only)
    with pytest.raises(EvidenceLedgerValidationError, match="A/B/C"):
        _validate_status("supported", missing)


def test_api_is_read_only_deterministic_and_invalid_cutoff_is_422(session_factory, built):
    app.dependency_overrides[get_industry_alpha_session_factory] = lambda: session_factory
    try:
        with TestClient(app) as client:
            routes = (
                "/industry-alpha/catalyst-assessments",
                f"/industry-alpha/catalyst-assessments/{built.supported_catalyst_id}",
                "/industry-alpha/risk-assessments",
                f"/industry-alpha/risk-assessments/{built.supported_risk_id}",
            )
            for route in routes:
                response = client.get(route)
                assert response.status_code == 200
                assert response.json() == client.get(route).json()
                json.dumps(response.json(), allow_nan=False)
                for method in (client.post, client.put, client.patch, client.delete):
                    assert method(route).status_code == 405
            assert client.get("/industry-alpha/catalyst-assessments", params={"as_of_cutoff": "bad"}).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_append_is_sequential_and_supersedes_exact_prior(session_factory, built):
    revision = Stage2AssessmentCommandService(session_factory).append_catalyst_revision(
        built.supported_catalyst_id, **append_kwargs(session_factory, built)
    )
    assert revision.revision_no == 3
    assert revision.supersedes_revision_id == built.later_catalyst_revision_id


@pytest.mark.parametrize("field,value", [
    ("catalyst_category", "score"), ("status", "recommended"), ("confidence", "certain"),
    ("subject", 123), ("information_cutoff_date", "2026-07-20"),
])
def test_strict_types_enums_and_dates_roll_back(session_factory, built, field, value):
    before = counts(session_factory)
    data = append_kwargs(session_factory, built)
    data[field] = value
    with pytest.raises(EvidenceLedgerValidationError):
        Stage2AssessmentCommandService(session_factory).append_catalyst_revision(built.supported_catalyst_id, **data)
    assert counts(session_factory) == before


def test_missing_v06b_boundary_and_cross_research_fail_atomically(session_factory, built):
    before = counts(session_factory)
    data = append_kwargs(session_factory, built)
    data["expectation_revision_ids"] = ()
    data["valuation_revision_ids"] = ()
    with pytest.raises(EvidenceLedgerValidationError, match="at least one exact v0.6B"):
        Stage2AssessmentCommandService(session_factory).create_catalyst(
            built.v06b.stage2.supported_research_id, catalyst_key="missing-v06b", **data
        )
    data = append_kwargs(session_factory, built)
    with pytest.raises(EvidenceLedgerValidationError, match="belong to this company research"):
        Stage2AssessmentCommandService(session_factory).create_catalyst(
            built.v06b.stage2.draft_research_id, catalyst_key="cross-research", **data
        )
    assert counts(session_factory) == before


def test_backdated_revision_fails_and_history_does_not_leak(session_factory, built):
    before = counts(session_factory)
    data = append_kwargs(session_factory, built, recorded=utc(18, 9), cutoff=date(2026, 7, 18))
    with pytest.raises(EvidenceLedgerValidationError, match="must not be before"):
        Stage2AssessmentCommandService(session_factory).append_catalyst_revision(built.supported_catalyst_id, **data)
    assert counts(session_factory) == before
    historical = catalyst_payload(session_factory, built.supported_catalyst_id, date(2026, 7, 16))
    assert historical["latest_revision"]["revision_no"] == 1
    assert all(item["information_date"] <= "2026-07-16" for claim in historical["latest_revision"]["claims"] for item in claim["evidence"])


def test_later_v06b_boundary_link_cannot_be_backfilled(session_factory, built):
    before = counts(session_factory)
    data = append_kwargs(session_factory, built)
    expectation_id = data["expectation_revision_ids"][0]
    with session_factory.begin() as session:
        session.execute(
            update(Stage2ExpectationClaimLink)
            .where(Stage2ExpectationClaimLink.expectation_revision_id == expectation_id)
            .values(recorded_at_utc=utc(21))
        )
    with pytest.raises(EvidenceLedgerValidationError, match="v0.6B claim boundary"):
        Stage2AssessmentCommandService(session_factory).append_catalyst_revision(
            built.supported_catalyst_id, **data
        )
    assert counts(session_factory) == before


def test_append_only_guards_reject_update_and_delete(session_factory, built):
    with pytest.raises(EvidenceLedgerImmutableError):
        with session_factory.begin() as session:
            row = session.get(Stage2CatalystAssessment, built.supported_catalyst_id)
            row.catalyst_key = "changed"
    with pytest.raises(EvidenceLedgerImmutableError):
        with session_factory.begin() as session:
            session.delete(session.get(Stage2RiskAssessmentRevision, built.supported_risk_revision_id))


def test_fixture_order_and_revision_semantics_repeat_on_clean_databases():
    results = []
    for _ in range(2):
        engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        factory = build_session_factory(engine)
        fixture = build_stage2_assessment_fixture(factory)
        with factory() as session:
            catalysts = Stage2CatalystQueryService(Stage2AssessmentRepository(session)).list_catalysts().to_dict()["assessments"]
        results.append(([item["catalyst_key"] for item in catalysts], catalyst_payload(factory, fixture.supported_catalyst_id)["latest_revision"]["revision_no"]))
        engine.dispose()
    assert results[0] == results[1]


def test_import_fixture_demo_and_routes_do_not_use_network(monkeypatch, session_factory):
    def reject_network(*_args, **_kwargs):
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr(socket.socket, "connect", reject_network)
    fixture = build_stage2_assessment_fixture(session_factory)
    assert catalyst_payload(session_factory, fixture.supported_catalyst_id)["notices"]["read_only"]
