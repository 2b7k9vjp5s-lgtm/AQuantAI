from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price_models import ListedInstrument, ListedInstrumentRevision
from backend.database.models import Base
from industry_alpha.normalized_valuation_models import (
    NormalizedValuationMetric,
    NormalizedValuationMetricRevision,
)
from industry_alpha.normalized_valuation_query import NormalizedValuationQueryService
from industry_alpha.normalized_valuation_rules import ComparisonMember
from industry_alpha.normalized_valuation_service import NormalizedValuationCommandService
from industry_alpha.normalized_valuation_comparison_service import (
    StrictValuationComparisonCommandService,
)
from industry_alpha.stage2_models import Stage2CompanyResearch, Stage2CompanyResearchRevision

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


def test_excluded_old_member_cannot_satisfy_eligible_history_span() -> None:
    eligible_dates = (
        date(2025, 7, 1),
        date(2025, 8, 1),
        date(2025, 9, 1),
        date(2025, 10, 1),
        date(2025, 11, 1),
        date(2025, 12, 1),
        date(2026, 1, 1),
        date(2026, 2, 1),
    )
    members = tuple(
        ComparisonMember(
            member_id=f"eligible-{index}",
            value=Decimal(str(index + 1)),
            valuation_date=value_date,
            period_end_date=date(2025 + index // 4, 3 * (index % 4 + 1), 1),
            eligible=True,
        )
        for index, value_date in enumerate(eligible_dates)
    ) + (
        ComparisonMember(
            member_id="excluded-old",
            value=None,
            valuation_date=date(2020, 1, 1),
            period_end_date=date(2019, 12, 31),
            eligible=False,
            reason_codes=("input_missing",),
        ),
    )

    result = StrictValuationComparisonCommandService._calculate_context(
        "historical", "eligible-0", members
    )

    assert result.comparison_state == "insufficient_history"
    assert result.eligible_member_count == 8
    assert result.excluded_member_count == 1
    assert result.subject_percentile is None


def _company_and_metric(
    session: Session,
    *,
    symbol: str,
    value: str,
    currency: str,
) -> dict[str, str]:
    research_id = uuid4()
    research_revision_id = uuid4()
    instrument_id = uuid4()
    instrument_revision_id = uuid4()
    metric_id = uuid4()
    metric_revision_id = uuid4()

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
            stock_code=symbol,
            created_at_utc=RECORDED,
        )
    )
    session.add(
        Stage2CompanyResearchRevision(
            id=research_revision_id,
            company_research_id=research_id,
            revision_no=1,
            workflow_state="open",
            conclusion_status="supported",
            research_question=f"Research {symbol}",
            summary="Strict comparison fixture.",
            information_cutoff_date=CUTOFF,
            recorded_at_utc=RECORDED,
            supersedes_revision_id=None,
        )
    )
    session.add(
        ListedInstrument(
            id=instrument_id,
            instrument_key=f"instrument-{symbol}",
            created_at_utc=RECORDED,
        )
    )
    session.add(
        ListedInstrumentRevision(
            id=instrument_revision_id,
            instrument_id=instrument_id,
            revision_no=1,
            canonical_symbol=symbol,
            security_type="common_equity",
            market_code="CN_A",
            exchange_code_namespace="ISO_MIC",
            exchange_code="XSHE",
            currency_code=currency,
            listing_date=date(2000, 1, 1),
            delisting_date=None,
            listing_status="active",
            recorded_by="test",
            information_cutoff_date=CUTOFF,
            recorded_at_utc=RECORDED,
            supersedes_revision_id=None,
        )
    )
    session.add(
        NormalizedValuationMetric(
            id=metric_id,
            metric_key=f"pe-{symbol}",
            instrument_id=instrument_id,
            metric_code="pe",
            valuation_as_of_date=CUTOFF,
            target_period_key="FY2026",
            period_basis="forward_fy1",
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
            instrument_revision_id=instrument_revision_id,
            calculation_state="calculated",
            normalized_value=Decimal(value),
            equity_value=Decimal("1000000000.000000"),
            enterprise_value=None,
            currency_code=currency,
            output_unit_code="multiple",
            price_trade_date=CUTOFF,
            financial_period_end_date=date(2026, 12, 31),
            reason_codes=[],
            information_cutoff_date=CUTOFF,
            recorded_at_utc=RECORDED,
            recorded_by="test",
            supersedes_revision_id=None,
        )
    )
    return {
        "research_id": str(research_id),
        "research_revision_id": str(research_revision_id),
        "instrument_id": str(instrument_id),
        "instrument_revision_id": str(instrument_revision_id),
        "metric_revision_id": str(metric_revision_id),
    }


def test_peer_context_preserves_but_excludes_currency_mismatch(database) -> None:
    with database.begin() as session:
        subject = _company_and_metric(
            session, symbol="000001", value="10.0000", currency="CNY"
        )
        peer_b = _company_and_metric(
            session, symbol="000002", value="15.0000", currency="CNY"
        )
        peer_c = _company_and_metric(
            session, symbol="000003", value="20.0000", currency="CNY"
        )
        peer_usd = _company_and_metric(
            session, symbol="000004", value="12.0000", currency="USD"
        )

    members = []
    for index, member in enumerate((subject, peer_b, peer_c, peer_usd)):
        members.append(
            {
                "member_key": f"member-{index}",
                "company_research_revision_id": member["research_revision_id"],
                "instrument_revision_id": member["instrument_revision_id"],
                "metric_revision_id": member["metric_revision_id"],
                "is_subject": index == 0,
                "missing_reason_codes": [],
            }
        )

    result = NormalizedValuationCommandService(database).record_comparison_set(
        {
            "comparison_key": "strict-peer-currency",
            "comparison_kind": "peer",
            "subject_company_research_id": subject["research_id"],
            "subject_instrument_id": subject["instrument_id"],
            "metric_code": "pe",
            "target_period_key": "FY2026",
            "period_basis": "forward_fy1",
            "accounting_scope": "consolidated_attributable",
            "formula_version": "aquantai.normalized-valuation.v1",
            "purpose_code": "normalized_valuation_peer_context_v1",
            "rule_version": "aquantai.normalized-comparison-context.v1",
            "rationale": "Explicit peers for currency compatibility test.",
            "subject_metric_revision_id": subject["metric_revision_id"],
            "information_cutoff_date": "2026-06-30",
            "recorded_at_utc": "2026-07-01T10:00:00Z",
            "recorded_by": "test",
            "expected_latest_revision_id": None,
            "members": members,
        }
    )

    assert result["comparison_state"] == "calculated"
    assert result["total_member_count"] == 4
    assert result["eligible_member_count"] == 3
    assert result["excluded_member_count"] == 1

    with database() as session:
        payload = NormalizedValuationQueryService(session).get_comparison_set_revision(
            uuid4() if False else __import__("uuid").UUID(result["revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=RECORDED,
        )
    usd_member = next(item for item in payload["members"] if item["member_key"] == "member-3")
    assert usd_member["eligibility_state"] == "excluded"
    assert usd_member["normalized_value_text"] is None
    assert "currency_mismatch" in usd_member["reason_codes"]
