from __future__ import annotations

import json
import socket
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from backend.api.industry_alpha import get_industry_alpha_session_factory
from backend.database.engine import build_session_factory
from backend.database.models import Base, DailyPriceRecord
from backend.main import app
from industry_alpha.errors import (
    EvidenceLedgerImmutableError,
    EvidenceLedgerValidationError,
)
from industry_alpha.stage2_expectations_commands import Stage2ExpectationCommandService
from industry_alpha.stage2_expectations_fixtures import (
    build_stage2_expectation_valuation_fixture,
)
from industry_alpha.stage2_expectations_models import STAGE2_EXPECTATION_MODELS
from industry_alpha.stage2_expectations_query import (
    Stage2ExpectationQueryService,
    Stage2ValuationQueryService,
)
from industry_alpha.stage2_expectations_repository import Stage2ExpectationRepository
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
    Stage2HypothesisClaimLink,
    Stage2ResearchHypothesisLink,
)


def utc(day: int, hour: int = 10) -> datetime:
    return datetime(2026, 7, day, hour, tzinfo=timezone.utc)


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    yield factory
    engine.dispose()


@pytest.fixture
def built(session_factory):
    return build_stage2_expectation_valuation_fixture(session_factory)


def expectation_payload(session_factory, expectation_id, cutoff=None):
    with session_factory() as session:
        return Stage2ExpectationQueryService(
            Stage2ExpectationRepository(session)
        ).get_expectation(expectation_id, as_of_cutoff=cutoff).to_dict()


def valuation_payload(session_factory, valuation_id, cutoff=None):
    with session_factory() as session:
        return Stage2ValuationQueryService(
            Stage2ExpectationRepository(session)
        ).get_valuation(valuation_id, as_of_cutoff=cutoff).to_dict()


def snapshot_counts(session_factory):
    with session_factory() as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in STAGE2_EXPECTATION_MODELS
        )


def frozen_inputs(session_factory, research_id):
    with session_factory() as session:
        research = session.get(Stage2CompanyResearch, research_id)
        revision = session.scalar(
            select(Stage2CompanyResearchRevision)
            .where(Stage2CompanyResearchRevision.company_research_id == research.id)
            .order_by(Stage2CompanyResearchRevision.revision_no.desc())
        )
        hypothesis_revision_id = session.scalar(
            select(Stage2ResearchHypothesisLink.hypothesis_revision_id).where(
                Stage2ResearchHypothesisLink.company_research_revision_id == revision.id
            )
        )
        claim_revision_id = session.scalar(
            select(Stage2HypothesisClaimLink.claim_revision_id).where(
                Stage2HypothesisClaimLink.hypothesis_revision_id
                == hypothesis_revision_id
            )
        )
    return revision.id, hypothesis_revision_id, claim_revision_id


def test_fixture_outputs_are_strict_json_safe_and_bounded(session_factory, built):
    current = expectation_payload(session_factory, built.expectation_id)
    historical = expectation_payload(
        session_factory, built.expectation_id, date(2026, 7, 15)
    )
    assert current["latest_revision"]["revision_no"] == 2
    assert historical["latest_revision"]["revision_no"] == 1
    assert current["notices"]["no_target_price_fair_value_expected_return_or_upside"]
    assert current["latest_revision"]["evidence_grade_counts"]["A"] >= 1
    json.dumps(current, allow_nan=False, sort_keys=True)
    json.dumps(historical, allow_nan=False, sort_keys=True)


def test_valuation_freezes_price_provenance_without_target_price(session_factory, built):
    payload = valuation_payload(session_factory, built.valuation_id)
    latest = payload["latest_revision"]
    assert latest["valuation_method"] == "market_price_context"
    assert latest["observed_value"] == "10.2"
    assert latest["price_reference"]["daily_price_id"] == built.daily_price_id
    assert latest["price_reference"]["ingestion_run_id"] == built.ingestion_run_id
    assert latest["comparison_basis"].startswith("Single local daily_price row")
    assert payload["notices"]["no_scores_weights_rankings_or_recommendations"]
    json.dumps(payload, allow_nan=False, sort_keys=True)


def test_list_api_is_read_only_deterministic_and_strict_json(session_factory, built):
    app.dependency_overrides[get_industry_alpha_session_factory] = lambda: session_factory
    try:
        with TestClient(app) as client:
            expectations = client.get(
                "/industry-alpha/market-expectations",
                params={"company_research_id": str(built.stage2.supported_research_id)},
            )
            valuations = client.get("/industry-alpha/valuation-snapshots")
            assert expectations.status_code == valuations.status_code == 200
            assert expectations.json() == client.get(expectations.request.url).json()
            assert valuations.json()["valuations"][0]["valuation_id"] == str(
                built.valuation_id
            )
            json.dumps(expectations.json(), allow_nan=False)
            json.dumps(valuations.json(), allow_nan=False)
            for route in (
                f"/industry-alpha/market-expectations/{built.expectation_id}",
                f"/industry-alpha/valuation-snapshots/{built.valuation_id}",
            ):
                assert client.get(route).status_code == 200
                for method in (client.post, client.put, client.patch, client.delete):
                    assert method(route).status_code == 405
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("status", ["supported", "disputed"])
def test_snapshot_status_requires_visible_evidence_and_rolls_back(
    session_factory, built, status
):
    before = snapshot_counts(session_factory)
    revision_id, hypothesis_revision_id, _claim_revision_id = frozen_inputs(
        session_factory, built.stage2.supported_research_id
    )
    with pytest.raises(EvidenceLedgerValidationError):
        Stage2ExpectationCommandService(session_factory).create_expectation(
            built.stage2.supported_research_id,
            expectation_key=f"invalid-{status}",
            company_research_revision_id=revision_id,
            hypothesis_revision_ids=(hypothesis_revision_id,),
            claim_revision_ids=(),
            subject="Invalid snapshot",
            period_horizon="unknown",
            expectation_kind="unknown",
            direction="uncertain",
            status=status,
            confidence="low",
            basis="Missing evidence should reject atomically.",
            information_cutoff_date=date(2026, 7, 16),
            recorded_at_utc=utc(16),
        )
    assert snapshot_counts(session_factory) == before


def test_claim_must_be_frozen_by_selected_hypothesis(session_factory, built):
    before = snapshot_counts(session_factory)
    revision_id, hypothesis_revision_id, _claim_revision_id = frozen_inputs(
        session_factory, built.stage2.supported_research_id
    )
    with session_factory() as session:
        draft_claim = session.scalar(
            select(Stage2HypothesisClaimLink.claim_revision_id)
            .join(
                Stage2ResearchHypothesisLink,
                Stage2ResearchHypothesisLink.hypothesis_revision_id
                == Stage2HypothesisClaimLink.hypothesis_revision_id,
                isouter=True,
            )
            .where(Stage2ResearchHypothesisLink.id.is_(None))
            .order_by(Stage2HypothesisClaimLink.claim_revision_id)
        )
    with pytest.raises(EvidenceLedgerValidationError, match="frozen"):
        Stage2ExpectationCommandService(session_factory).create_expectation(
            built.stage2.supported_research_id,
            expectation_key="wrong-claim-boundary",
            company_research_revision_id=revision_id,
            hypothesis_revision_ids=(hypothesis_revision_id,),
            claim_revision_ids=(draft_claim,),
            subject="Wrong claim boundary",
            period_horizon="unknown",
            expectation_kind="unknown",
            direction="uncertain",
            status="draft",
            confidence="low",
            basis="Claim belongs to another frozen hypothesis boundary.",
            information_cutoff_date=date(2026, 7, 16),
            recorded_at_utc=utc(16),
        )
    assert snapshot_counts(session_factory) == before


def test_price_reference_must_match_research_identity_and_cutoff(
    session_factory, built
):
    before = snapshot_counts(session_factory)
    revision_id, hypothesis_revision_id, claim_revision_id = frozen_inputs(
        session_factory, built.stage2.supported_research_id
    )
    with session_factory.begin() as session:
        original = session.get(DailyPriceRecord, built.daily_price_id)
        bad_price = DailyPriceRecord(
            ingestion_run_id=original.ingestion_run_id,
            trade_date=date(2026, 7, 15),
            stock_code="999999",
            open=10.0,
            high=10.0,
            low=10.0,
            close=10.0,
            volume=1.0,
            amount=10.0,
            adjust_type="qfq",
            source=original.source,
        )
        session.add(bad_price)
        session.flush()
        bad_price_id = bad_price.id
    with pytest.raises(EvidenceLedgerValidationError, match="match"):
        Stage2ExpectationCommandService(session_factory).create_valuation_snapshot(
            built.stage2.supported_research_id,
            valuation_key="bad-price",
            company_research_revision_id=revision_id,
            hypothesis_revision_ids=(hypothesis_revision_id,),
            claim_revision_ids=(claim_revision_id,),
            valuation_method="market_price_context",
            metric_context="Bad price",
            observed_value="10",
            missing_data_reason=None,
            unit="close",
            currency="CNY",
            comparison_basis="Invalid.",
            assumptions="Invalid.",
            status="draft",
            confidence="low",
            information_cutoff_date=date(2026, 7, 16),
            daily_price_id=bad_price_id,
            recorded_at_utc=utc(16),
        )
    assert snapshot_counts(session_factory) == before


def test_append_only_guard_applies_to_all_v06b_models(session_factory, built):
    with session_factory() as session:
        for model in STAGE2_EXPECTATION_MODELS:
            row = session.scalar(select(model))
            assert row is not None, model.__name__
            session.delete(row)
            with pytest.raises(EvidenceLedgerImmutableError):
                session.flush()
            session.rollback()


def test_import_fixture_demo_and_routes_do_not_use_network(monkeypatch, session_factory):
    def reject_network(*_args, **_kwargs):
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    fixture = build_stage2_expectation_valuation_fixture(session_factory)
    assert expectation_payload(session_factory, fixture.expectation_id)["notices"]["read_only"]
