from __future__ import annotations

import json
import socket
from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from backend.api.industry_alpha import get_industry_alpha_session_factory
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
from industry_alpha.errors import EvidenceLedgerImmutableError, EvidenceLedgerValidationError
from industry_alpha.stage2_assessments_commands import _Boundary
from industry_alpha.stage2_judgments_commands import Stage2JudgmentCommandService, _validate_outcome
from industry_alpha.stage2_judgments_fixtures import (
    build_stage2_judgment_fixture,
    build_stage2_judgment_fixture_payload,
)
from industry_alpha.stage2_judgments_models import (
    STAGE2_JUDGMENT_MODELS, Stage2CompanyJudgmentRevision,
    Stage2IndustryJudgment, Stage2IndustryJudgmentRevision,
)
from industry_alpha.stage2_judgments_query import Stage2CompanyJudgmentQueryService, Stage2IndustryJudgmentQueryService
from industry_alpha.stage2_judgments_repository import Stage2JudgmentRepository


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
    return build_stage2_judgment_fixture(session_factory)


def _payload(factory, kind, identity, cutoff=None):
    with factory() as session:
        service = Stage2IndustryJudgmentQueryService(Stage2JudgmentRepository(session)) if kind == "industry" else Stage2CompanyJudgmentQueryService(Stage2JudgmentRepository(session))
        return service.get_judgment(identity, as_of_cutoff=cutoff).to_dict()


def _links(factory, built, later=True):
    catalyst_id = built.v06c.later_catalyst_revision_id if later else built.v06c.supported_catalyst_revision_id
    risk_id = built.v06c.later_risk_revision_id if later else built.v06c.supported_risk_revision_id
    from industry_alpha.stage2_judgments_fixtures import _boundary
    with factory() as session:
        return _boundary(session, catalyst_id, risk_id)


def _append(factory, built, **changes):
    data = {
        **_links(factory, built),
        "outcome": "uncertain", "evidence_state": "disputed", "confidence": "low",
        "decision_criteria": "Use the exact frozen boundary.",
        "rationale": "Contradictory evidence remains visible.",
        "uncertainty": "The result remains uncertain.",
        "follow_up_verification": "后续验证清单：检查新的可归因一手资料。",
        "driver_durability": "Durability is uncertain.",
        "value_pool_direction": "Direction is not affirmed.",
        "chain_bottleneck_support": "The disputed boundary remains explicit.",
        "information_cutoff_date": date(2026, 7, 20), "recorded_at_utc": utc(20),
    }
    data.update(changes)
    return data


def _counts(factory):
    with factory() as session:
        return tuple(session.scalar(select(func.count()).select_from(model)) for model in STAGE2_JUDGMENT_MODELS)


def _returned_ids(value, key=""):
    if isinstance(value, dict):
        result = []
        for item_key, item_value in value.items():
            result.extend(_returned_ids(item_value, item_key))
        return result
    if isinstance(value, (list, tuple)):
        if key.endswith("_ids"):
            return [str(item) for item in value]
        result = []
        for item in value:
            result.extend(_returned_ids(item, key))
        return result
    return [str(value)] if key.endswith("_id") and value is not None else []


def test_fixture_current_historical_handoff_provenance_and_strict_json(session_factory, built):
    current = _payload(session_factory, "industry", built.affirmed_industry_id)
    historical = _payload(session_factory, "industry", built.affirmed_industry_id, date(2026, 7, 16))
    company = _payload(session_factory, "company", built.affirmed_company_id, date(2026, 7, 16))
    assert current["latest_revision"]["revision_no"] == 2
    assert current["latest_revision"]["outcome"] == "uncertain"
    assert historical["latest_revision"]["revision_no"] == 1
    assert historical["latest_revision"]["outcome"] == "affirmed"
    assert historical["latest_revision"]["evidence_state"] == "supported"
    assert len(historical["latest_revision"]["frozen_hypothesis_revision_ids"]) == 1
    assert len(historical["latest_revision"]["frozen_expectation_revision_ids"]) == 1
    assert len(historical["latest_revision"]["frozen_valuation_revision_ids"]) == 1
    assert len(historical["latest_revision"]["frozen_catalyst_revision_ids"]) == 1
    assert len(historical["latest_revision"]["frozen_risk_revision_ids"]) == 1
    fact = historical["latest_revision"]["claims"][0]
    inference = current["latest_revision"]["claims"][0]
    assert fact["claim_kind"] == "fact"
    assert fact["inference_confidence"] is None
    assert fact["inference_basis"] is None
    assert inference["claim_kind"] == "inference"
    assert inference["inference_confidence"] == "low"
    assert inference["inference_basis"]
    assert company["latest_revision"]["beneficiary_credibility"]
    json.dumps({"current": current, "historical": historical, "company": company}, allow_nan=False, sort_keys=True)


def test_outcomes_evidence_states_and_missing_wording_fail_atomically(session_factory, built):
    before = _counts(session_factory)
    service = Stage2JudgmentCommandService(session_factory)
    for changes, match in (
        ({"outcome": "affirmed", "evidence_state": "disputed"}, "affirmed"),
        ({"outcome": "uncertain", "evidence_state": "supported"}, "supported evidence"),
        ({"outcome": "not_assessed", "evidence_state": "insufficient_evidence"}, "missing-evidence"),
        ({"evidence_state": "disputed", "confidence": "high"}, "confidence"),
        ({"outcome": "ranked"}, "outcome"),
    ):
        with pytest.raises(EvidenceLedgerValidationError, match=match):
            service.append_industry_judgment_revision(built.affirmed_industry_id, **_append(session_factory, built, **changes))
        assert _counts(session_factory) == before


def test_d_only_or_missing_boundary_cannot_affirm(session_factory, built):
    data = _append(session_factory, built)
    data["claim_revision_ids"] = ()
    with pytest.raises(EvidenceLedgerValidationError):
        Stage2JudgmentCommandService(session_factory).append_industry_judgment_revision(built.affirmed_industry_id, **data)


def test_d_only_cannot_affirm_and_explicit_not_assessed_is_valid():
    claim = SimpleNamespace(claim_status="supported")
    d_only = _Boundary(None, (), (), (), (claim,), ((claim, SimpleNamespace(relation="supports"), SimpleNamespace(evidence_grade="D")),))
    with pytest.raises(EvidenceLedgerValidationError, match="A/B/C"):
        _validate_outcome("affirmed", "supported", "low", "Manual rationale.", "Uncertain.", "后续验证清单：核验。", d_only)
    missing = _Boundary(None, (), (), (), (claim,), ())
    _validate_outcome(
        "not_assessed", "insufficient_evidence", "low",
        "尚未获得可靠公开证据。", "Evidence remains unavailable.", "后续验证清单：寻找一手资料。", missing,
    )


def test_exact_same_company_and_complete_v06c_boundary_fail_closed(session_factory, built):
    before = _counts(session_factory)
    data = _append(session_factory, built)
    data["risk_revision_ids"] = (built.v06c.supported_risk_revision_id,)
    with pytest.raises(EvidenceLedgerValidationError, match="exact"):
        Stage2JudgmentCommandService(session_factory).append_industry_judgment_revision(built.affirmed_industry_id, **data)
    data = _append(session_factory, built)
    from industry_alpha.stage2_models import Stage2CompanyResearchRevision
    with session_factory() as session:
        data["company_research_revision_id"] = session.scalar(
            select(Stage2CompanyResearchRevision.id).where(
                Stage2CompanyResearchRevision.company_research_id == built.v06c.v06b.stage2.draft_research_id
            )
        )
    with pytest.raises(EvidenceLedgerValidationError):
        Stage2JudgmentCommandService(session_factory).append_industry_judgment_revision(built.affirmed_industry_id, **data)
    assert _counts(session_factory) == before


def test_sequential_revision_supersedes_and_backdating_rolls_back(session_factory, built):
    revision = Stage2JudgmentCommandService(session_factory).append_industry_judgment_revision(built.affirmed_industry_id, **_append(session_factory, built))
    assert revision.revision_no == 3
    assert revision.supersedes_revision_id == built.later_industry_revision_id
    assert revision.id.version == 4
    before = _counts(session_factory)
    with pytest.raises(EvidenceLedgerValidationError, match="must not be before"):
        Stage2JudgmentCommandService(session_factory).append_industry_judgment_revision(
            built.affirmed_industry_id, **_append(session_factory, built, information_cutoff_date=date(2026, 7, 19), recorded_at_utc=utc(19, 13))
        )
    assert _counts(session_factory) == before


@pytest.mark.parametrize("field,value", [
    ("decision_criteria", 123), ("information_cutoff_date", "2026-07-20"),
    ("confidence", "certain"), ("evidence_state", "unknown"),
    ("driver_durability", "x" * 2001),
])
def test_strict_types_enums_and_bounds_roll_back(session_factory, built, field, value):
    before = _counts(session_factory)
    with pytest.raises(EvidenceLedgerValidationError):
        Stage2JudgmentCommandService(session_factory).append_industry_judgment_revision(built.affirmed_industry_id, **_append(session_factory, built, **{field: value}))
    assert _counts(session_factory) == before


def test_append_only_update_and_delete_are_rejected(session_factory, built):
    with pytest.raises(EvidenceLedgerImmutableError):
        with session_factory.begin() as session:
            row = session.get(Stage2IndustryJudgment, built.affirmed_industry_id)
            row.judgment_key = "changed"
    with pytest.raises(EvidenceLedgerImmutableError):
        with session_factory.begin() as session:
            session.delete(session.get(Stage2CompanyJudgmentRevision, built.affirmed_company_revision_id))


def test_api_is_read_only_deterministic_cutoff_aware_and_strict_json(session_factory, built):
    app.dependency_overrides[get_industry_alpha_session_factory] = lambda: session_factory
    try:
        with TestClient(app) as client:
            routes = (
                "/industry-alpha/industry-judgments",
                f"/industry-alpha/industry-judgments/{built.affirmed_industry_id}",
                "/industry-alpha/company-judgments",
                f"/industry-alpha/company-judgments/{built.affirmed_company_id}",
            )
            for route in routes:
                response = client.get(route)
                assert response.status_code == 200
                assert response.json() == client.get(route).json()
                json.dumps(response.json(), allow_nan=False)
                for method in (client.post, client.put, client.patch, client.delete):
                    assert method(route).status_code == 405
            historical = client.get(routes[1], params={"as_of_cutoff": "2026-07-16"})
            assert historical.status_code == 200
            assert historical.json()["latest_revision"]["outcome"] == "affirmed"
            assert client.get(routes[0], params={"as_of_cutoff": "bad"}).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_fixture_semantics_and_order_repeat_on_clean_databases():
    payloads = []
    returned_ids = []
    for _ in range(2):
        engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        factory = build_session_factory(engine)
        fixture = build_stage2_judgment_fixture(factory)
        payload = build_stage2_judgment_fixture_payload(factory, fixture)
        json.dumps(payload, allow_nan=False, sort_keys=True, separators=(",", ":"))
        payloads.append(payload)
        returned_ids.append(_returned_ids(payload))
        engine.dispose()
    assert payloads[0] == payloads[1]
    assert returned_ids[0]
    assert returned_ids[0] == returned_ids[1]
    assert all(UUID(item).version == 5 for item in returned_ids[0])


def test_import_startup_fixture_and_demo_do_not_use_network(monkeypatch, session_factory):
    def reject(*_args, **_kwargs):
        raise AssertionError("network access is forbidden")
    monkeypatch.setattr(socket, "create_connection", reject)
    monkeypatch.setattr(socket.socket, "connect", reject)
    fixture = build_stage2_judgment_fixture(session_factory)
    assert _payload(session_factory, "company", fixture.affirmed_company_id)["notices"]["read_only"]
    from scripts.demo_stage2_quality_judgments import build_demo
    assert build_demo()["industry"]["notices"]["research_only"]
