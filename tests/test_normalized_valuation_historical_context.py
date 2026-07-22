from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price_models import ListedInstrument, ListedInstrumentRevision
from backend.database.models import Base
from industry_alpha.normalized_valuation_models import (
    NormalizedValuationMetric,
    NormalizedValuationMetricRevision,
)
from industry_alpha.normalized_valuation_service import (
    NormalizedValuationCommandService,
    NormalizedValuationQueryService,
)
from industry_alpha.stage2_models import Stage2CompanyResearch

UTC = timezone.utc
RECORDED = datetime(2026, 7, 1, 10, tzinfo=UTC)
CUTOFF = date(2026, 6, 30)


@pytest.fixture()
def database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


def test_persisted_eight_period_historical_context_round_trip(database) -> None:
    research_id = uuid4()
    instrument_id = uuid4()
    instrument_revision_id = uuid4()
    valuation_dates = (
        date(2023, 1, 1),
        date(2023, 5, 1),
        date(2023, 9, 1),
        date(2024, 1, 1),
        date(2024, 5, 1),
        date(2024, 9, 1),
        date(2025, 1, 1),
        date(2025, 5, 5),
    )
    period_ends = (
        date(2022, 12, 31),
        date(2022, 12, 31),
        date(2023, 12, 31),
        date(2023, 12, 31),
        date(2024, 12, 31),
        date(2024, 12, 31),
        date(2025, 12, 31),
        date(2025, 12, 31),
    )
    values = ("10", "5", "10", "15", "20", "25", "30", "35")
    members = []

    with database.begin() as session:
        session.add(
            Stage2CompanyResearch(
                id=research_id,
                case_id=uuid4(),
                map_id=uuid4(),
                candidate_pool_id=uuid4(),
                candidate_pool_revision_id=uuid4(),
                candidate_pool_membership_id=uuid4(),
                beneficiary_id=uuid4(),
                beneficiary_revision_id=uuid4(),
                selected_map_revision_id=uuid4(),
                stock_basic_record_id=1,
                source="fixture",
                stock_code="000001",
                created_at_utc=RECORDED,
            )
        )
        session.add(
            ListedInstrument(
                id=instrument_id,
                instrument_key="historical-000001",
                created_at_utc=RECORDED,
            )
        )
        session.add(
            ListedInstrumentRevision(
                id=instrument_revision_id,
                instrument_id=instrument_id,
                revision_no=1,
                canonical_symbol="000001",
                security_type="common_equity",
                market_code="CN_A",
                exchange_code_namespace="ISO_MIC",
                exchange_code="XSHE",
                currency_code="CNY",
                listing_date=date(2000, 1, 1),
                delisting_date=None,
                listing_status="active",
                recorded_by="test",
                information_cutoff_date=CUTOFF,
                recorded_at_utc=RECORDED,
                supersedes_revision_id=None,
            )
        )
        for index, (valuation_date, period_end, value) in enumerate(
            zip(valuation_dates, period_ends, values, strict=True)
        ):
            metric_id = uuid4()
            revision_id = uuid4()
            session.add(
                NormalizedValuationMetric(
                    id=metric_id,
                    metric_key=f"historical-pe-{index}",
                    instrument_id=instrument_id,
                    metric_code="pe",
                    valuation_as_of_date=valuation_date,
                    target_period_key="TTM-HISTORICAL",
                    period_basis="ttm",
                    accounting_scope="consolidated_attributable",
                    formula_version="aquantai.normalized-valuation.v1",
                    created_at_utc=RECORDED,
                )
            )
            session.add(
                NormalizedValuationMetricRevision(
                    id=revision_id,
                    metric_id=metric_id,
                    revision_no=1,
                    instrument_revision_id=instrument_revision_id,
                    calculation_state="calculated",
                    normalized_value=Decimal(value),
                    equity_value=Decimal("1000000000.000000"),
                    enterprise_value=None,
                    currency_code="CNY",
                    output_unit_code="multiple",
                    price_trade_date=valuation_date,
                    financial_period_end_date=period_end,
                    reason_codes=[],
                    information_cutoff_date=valuation_date,
                    recorded_at_utc=RECORDED,
                    recorded_by="test",
                    supersedes_revision_id=None,
                )
            )
            members.append(
                {
                    "member_key": f"history-{index}",
                    "company_research_revision_id": None,
                    "instrument_revision_id": str(instrument_revision_id),
                    "metric_revision_id": str(revision_id),
                    "is_subject": index == 2,
                    "missing_reason_codes": [],
                }
            )

    result = NormalizedValuationCommandService(database).record_comparison_set(
        {
            "comparison_key": "historical-pe-eight-periods",
            "comparison_kind": "historical",
            "subject_company_research_id": str(research_id),
            "subject_instrument_id": str(instrument_id),
            "metric_code": "pe",
            "target_period_key": "TTM-HISTORICAL",
            "period_basis": "ttm",
            "accounting_scope": "consolidated_attributable",
            "formula_version": "aquantai.normalized-valuation.v1",
            "purpose_code": "normalized_valuation_historical_context_v1",
            "rule_version": "aquantai.normalized-comparison-context.v1",
            "rationale": "Eight eligible observations across more than two years.",
            "subject_metric_revision_id": members[2]["metric_revision_id"],
            "information_cutoff_date": "2026-06-30",
            "recorded_at_utc": "2026-07-01T10:00:00Z",
            "recorded_by": "test",
            "expected_latest_revision_id": None,
            "members": members,
        }
    )

    assert result["comparison_state"] == "calculated"
    assert result["eligible_member_count"] == 8
    assert result["minimum_value_text"] == "5.0000"
    assert result["maximum_value_text"] == "35.0000"
    assert result["median_value_text"] == "17.5000"
    assert result["subject_percentile_text"] == "25.00"

    with database() as session:
        payload = NormalizedValuationQueryService(session).get_comparison_set_revision(
            UUID(result["revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=RECORDED,
        )
    assert payload["comparison_state"] == "calculated"
    assert len(payload["members"]) == 8
    assert payload["subject_percentile_text"] == "25.00"
