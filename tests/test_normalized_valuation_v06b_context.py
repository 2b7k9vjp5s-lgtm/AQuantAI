from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price import CanonicalPriceCommandService
from backend.database.models import Base
from industry_alpha.normalized_financial_rules import NormalizedMetricError
from industry_alpha.normalized_valuation_service import (
    NormalizedValuationCommandService,
    NormalizedValuationQueryService,
)
from industry_alpha.stage2_expectations_fixtures import (
    build_stage2_expectation_valuation_fixture,
)
from industry_alpha.stage2_models import Stage2CompanyResearch, Stage2CompanyResearchRevision

UTC = timezone.utc


@pytest.fixture()
def database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


def _research(factory, fixture):
    with factory() as session:
        research = session.get(Stage2CompanyResearch, fixture.stage2.supported_research_id)
        revision = session.scalar(
            select(Stage2CompanyResearchRevision).where(
                Stage2CompanyResearchRevision.company_research_id == research.id,
                Stage2CompanyResearchRevision.revision_no == 3,
            )
        )
    return research, revision


def _instrument(factory, symbol: str) -> dict:
    return CanonicalPriceCommandService(factory).record_listed_instrument(
        {
            "instrument_key": "v06b-context-instrument",
            "expected_latest_revision_id": None,
            "canonical_symbol": symbol,
            "security_type": "common_equity",
            "market_code": "CN_A",
            "exchange_code_namespace": "ISO_MIC",
            "exchange_code": "XSHE",
            "currency_code": "CNY",
            "listing_date": "2000-01-01",
            "delisting_date": None,
            "listing_status": "active",
            "recorded_by": "context-test",
            "information_cutoff_date": "2026-07-22",
            "recorded_at_utc": "2026-07-22T20:00:00Z",
        }
    )


def _observation(
    *,
    key: str,
    research,
    revision,
    instrument: dict,
    source_kind: str,
    state: str,
    period_basis: str,
    value_text: str | None,
    recorded_at: str,
    cutoff: str,
    **context,
) -> dict:
    return {
        "observation_key": key,
        "company_research_id": str(research.id),
        "company_research_revision_id": str(revision.id),
        "instrument_id": instrument["instrument_id"],
        "instrument_revision_id": instrument["instrument_revision_id"],
        "metric_code": "net_profit_attributable",
        "source_kind": source_kind,
        "observation_state": state,
        "value_text": value_text,
        "currency_code": "CNY",
        "unit_code": "currency_amount",
        "period_basis": period_basis,
        "target_period_key": "FY2026",
        "accounting_scope": "consolidated_attributable",
        "observation_as_of_date": "2026-07-22" if source_kind != "actual" else "2027-02-20",
        "period_start_date": "2026-01-01",
        "period_end_date": "2026-12-31",
        "fiscal_year": 2026,
        "effective_start_date": None,
        "effective_end_date": None,
        "rationale": "Explicit optional context fixture.",
        "falsification_condition": "A later exact revision may supersede this input.",
        "information_cutoff_date": cutoff,
        "recorded_at_utc": recorded_at,
        "recorded_by": "context-test",
        "expected_latest_revision_id": None,
        "claim_revision_ids": [],
        "evidence_links": [],
        **context,
    }


def test_optional_v06b_contexts_are_typed_validated_and_readable(database) -> None:
    fixture = build_stage2_expectation_valuation_fixture(database)
    research, revision = _research(database, fixture)
    instrument = _instrument(database, research.stock_code)
    commands = NormalizedValuationCommandService(database)

    expected = commands.record_observation(
        _observation(
            key="context-expected-profit",
            research=research,
            revision=revision,
            instrument=instrument,
            source_kind="research_assumption",
            state="supported",
            period_basis="forward_fy1",
            value_text="2000000000",
            cutoff="2026-07-22",
            recorded_at="2026-07-22T21:00:00Z",
            market_expectation_revision_id=str(fixture.expectation_revision_id),
        )
    )
    valuation_context = commands.record_observation(
        _observation(
            key="context-valuation-profit",
            research=research,
            revision=revision,
            instrument=instrument,
            source_kind="research_assumption",
            state="supported",
            period_basis="forward_fy1",
            value_text="2100000000",
            cutoff="2026-07-22",
            recorded_at="2026-07-22T21:01:00Z",
            valuation_snapshot_revision_id=str(fixture.valuation_revision_id),
        )
    )
    actual = commands.record_observation(
        _observation(
            key="context-actual-profit",
            research=research,
            revision=revision,
            instrument=instrument,
            source_kind="actual",
            state="missing",
            period_basis="fy_actual",
            value_text=None,
            cutoff="2027-02-20",
            recorded_at="2027-02-21T10:00:00Z",
        )
    )
    gap = commands.record_expectation_gap(
        {
            "gap_key": "context-profit-gap",
            "company_research_id": str(research.id),
            "company_research_revision_id": str(revision.id),
            "instrument_id": instrument["instrument_id"],
            "instrument_revision_id": instrument["instrument_revision_id"],
            "metric_code": "net_profit_attributable",
            "target_period_key": "FY2026",
            "expected_source_kind": "research_assumption",
            "rule_version": "aquantai.normalized-expectation-gap.v1",
            "expected_observation_revision_id": expected["revision_id"],
            "actual_observation_revision_id": actual["revision_id"],
            "calculation_as_of_date": "2027-02-20",
            "information_cutoff_date": "2027-02-20",
            "recorded_at_utc": "2027-02-21T11:00:00Z",
            "recorded_by": "context-test",
            "expected_latest_revision_id": None,
            "market_expectation_revision_id": str(fixture.expectation_revision_id),
        }
    )

    with database() as session:
        query = NormalizedValuationQueryService(session)
        expected_payload = query.get_financial_observation_revision(
            UUID(expected["revision_id"]),
            as_of_cutoff=date(2026, 7, 22),
            as_of_recorded_at_utc=datetime(2026, 7, 22, 21, tzinfo=UTC),
        )
        valuation_payload = query.get_financial_observation_revision(
            UUID(valuation_context["revision_id"]),
            as_of_cutoff=date(2026, 7, 22),
            as_of_recorded_at_utc=datetime(2026, 7, 22, 21, 1, tzinfo=UTC),
        )
        gap_payload = query.get_expectation_gap_revision(
            UUID(gap["revision_id"]),
            as_of_cutoff=date(2027, 2, 20),
            as_of_recorded_at_utc=datetime(2027, 2, 21, 11, tzinfo=UTC),
        )

    assert expected_payload["market_expectation_revision_id"] == str(
        fixture.expectation_revision_id
    )
    assert expected_payload["valuation_snapshot_revision_id"] is None
    assert valuation_payload["valuation_snapshot_revision_id"] == str(
        fixture.valuation_revision_id
    )
    assert gap_payload["market_expectation_revision_id"] == str(
        fixture.expectation_revision_id
    )


def test_optional_context_must_match_exact_company_research_revision(database) -> None:
    fixture = build_stage2_expectation_valuation_fixture(database)
    research, _revision = _research(database, fixture)
    instrument = _instrument(database, research.stock_code)
    with database() as session:
        later_revision = session.get(
            Stage2CompanyResearchRevision, fixture.later_research_revision_id
        )
    with pytest.raises(NormalizedMetricError) as exc_info:
        NormalizedValuationCommandService(database).record_observation(
            _observation(
                key="context-mismatch",
                research=research,
                revision=later_revision,
                instrument=instrument,
                source_kind="research_assumption",
                state="supported",
                period_basis="forward_fy1",
                value_text="2000000000",
                cutoff="2026-07-22",
                recorded_at="2026-07-22T21:00:00Z",
                market_expectation_revision_id=str(fixture.expectation_revision_id),
            )
        )
    assert exc_info.value.code == "normalized_financial_context_mismatch"
