from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price_models import ListedInstrument, ListedInstrumentRevision
from backend.database.models import Base
from industry_alpha.normalized_financial_rules import NormalizedMetricError
from industry_alpha.normalized_valuation_models import (
    NormalizedValuationMetric,
    NormalizedValuationMetricRevision,
)
from industry_alpha.normalized_valuation_service import NormalizedValuationCommandService

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


def test_comparison_rejects_same_identity_different_instrument_revision(database) -> None:
    instrument_id = uuid4()
    first_revision_id = uuid4()
    second_revision_id = uuid4()
    metric_id = uuid4()
    metric_revision_id = uuid4()
    with database.begin() as session:
        session.add(
            ListedInstrument(
                id=instrument_id,
                instrument_key="exact-revision-instrument",
                created_at_utc=RECORDED,
            )
        )
        session.add_all(
            [
                ListedInstrumentRevision(
                    id=first_revision_id,
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
                    information_cutoff_date=date(2026, 6, 1),
                    recorded_at_utc=datetime(2026, 6, 1, 10, tzinfo=UTC),
                    supersedes_revision_id=None,
                ),
                ListedInstrumentRevision(
                    id=second_revision_id,
                    instrument_id=instrument_id,
                    revision_no=2,
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
                    supersedes_revision_id=first_revision_id,
                ),
            ]
        )
        session.add(
            NormalizedValuationMetric(
                id=metric_id,
                metric_key="exact-revision-pe",
                instrument_id=instrument_id,
                metric_code="pe",
                valuation_as_of_date=CUTOFF,
                target_period_key="TTM-HISTORICAL",
                period_basis="ttm",
                accounting_scope="consolidated_attributable",
                formula_version="aquantai.normalized-valuation.v1",
                created_at_utc=RECORDED,
            )
        )
        session.add(
            NormalizedValuationMetricRevision(
                id=metric_revision_id,
                metric_id=metric_id,
                revision_no=1,
                instrument_revision_id=first_revision_id,
                calculation_state="calculated",
                normalized_value=Decimal("10.0000"),
                equity_value=Decimal("1000000000.000000"),
                enterprise_value=None,
                currency_code="CNY",
                output_unit_code="multiple",
                price_trade_date=CUTOFF,
                financial_period_end_date=date(2025, 12, 31),
                reason_codes=[],
                information_cutoff_date=CUTOFF,
                recorded_at_utc=RECORDED,
                recorded_by="test",
                supersedes_revision_id=None,
            )
        )

    with pytest.raises(NormalizedMetricError) as exc_info:
        NormalizedValuationCommandService(database).record_comparison_set(
            {
                "comparison_key": "exact-revision-substitution",
                "comparison_kind": "historical",
                "subject_company_research_id": str(uuid4()),
                "subject_instrument_id": str(instrument_id),
                "metric_code": "pe",
                "target_period_key": "TTM-HISTORICAL",
                "period_basis": "ttm",
                "accounting_scope": "consolidated_attributable",
                "formula_version": "aquantai.normalized-valuation.v1",
                "purpose_code": "normalized_valuation_historical_context_v1",
                "rule_version": "aquantai.normalized-comparison-context.v1",
                "rationale": "Exact revision substitution must fail closed.",
                "subject_metric_revision_id": str(metric_revision_id),
                "information_cutoff_date": "2026-06-30",
                "recorded_at_utc": "2026-07-01T10:00:00Z",
                "recorded_by": "test",
                "expected_latest_revision_id": None,
                "members": [
                    {
                        "member_key": "subject",
                        "company_research_revision_id": None,
                        "instrument_revision_id": str(second_revision_id),
                        "metric_revision_id": str(metric_revision_id),
                        "is_subject": True,
                        "missing_reason_codes": [],
                    }
                ],
            }
        )
    assert exc_info.value.code == "normalized_comparison_universe_mismatch"
