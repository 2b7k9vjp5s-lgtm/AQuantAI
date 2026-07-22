from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price import CanonicalPriceCommandService
from backend.database.models import Base, DailyPriceRecord, IngestionRun
from backend.database.normalized_valuation_eligibility import (
    NORMALIZED_VALUATION_PURPOSE,
    NORMALIZED_VALUATION_RULE_VERSION,
    NormalizedValuationEligibilityCommandService,
)
from industry_alpha.models import ClaimEvidenceLink
from industry_alpha.normalized_valuation_query import NormalizedValuationQueryService
from industry_alpha.normalized_valuation_service import NormalizedValuationCommandService
from industry_alpha.stage2_expectations_fixtures import (
    build_stage2_expectation_valuation_fixture,
)
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
    Stage2HypothesisClaimLink,
    Stage2ResearchHypothesisLink,
)

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


def research_graph(factory):
    fixture = build_stage2_expectation_valuation_fixture(factory)
    with factory() as session:
        research = session.get(Stage2CompanyResearch, fixture.stage2.supported_research_id)
        revision = session.scalar(
            select(Stage2CompanyResearchRevision).where(
                Stage2CompanyResearchRevision.company_research_id == research.id,
                Stage2CompanyResearchRevision.revision_no == 3,
            )
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
        evidence_link = session.scalar(
            select(ClaimEvidenceLink)
            .where(
                ClaimEvidenceLink.claim_revision_id == claim_revision_id,
                ClaimEvidenceLink.relation == "supports",
            )
            .order_by(ClaimEvidenceLink.id)
        )
    return research, revision, claim_revision_id, evidence_link


def canonical_graph(factory, stock_code: str):
    recorded = "2026-07-22T20:00:00Z"
    common = {
        "recorded_by": "golden-path",
        "information_cutoff_date": "2026-07-22",
        "recorded_at_utc": recorded,
    }
    with factory.begin() as session:
        run = IngestionRun(
            batch_identifier="normalized-valuation-golden-price",
            series_key="g" * 64,
            series_identity={},
            provider="fixture",
            dataset="daily_price",
            imported_at=datetime(2026, 7, 22, 18, tzinfo=UTC),
            completed_at=datetime(2026, 7, 22, 19, tzinfo=UTC),
            requested_start_date=date(2026, 6, 30),
            requested_end_date=date(2026, 6, 30),
            information_cutoff_date=date(2026, 6, 30),
            requested_scope={"stock_codes": [stock_code]},
            provider_request_metadata={"offline_fixture": True},
            adapter_version="golden.v1",
            snapshot_mode="complete",
            contract_version="v1",
            status="succeeded",
            row_count_received=1,
            row_count_written=1,
            dataset_counts={"daily_price": 1},
            error_summary=None,
        )
        session.add(run)
        session.flush()
        source = DailyPriceRecord(
            ingestion_run_id=run.id,
            trade_date=date(2026, 6, 30),
            stock_code=stock_code,
            open=20.0,
            high=20.0,
            low=20.0,
            close=20.0,
            volume=100.0,
            amount=2000.0,
            adjust_type="",
            source="fixture",
        )
        session.add(source)
        session.flush()
        run_id = run.id
        source_id = source.id

    canonical = CanonicalPriceCommandService(factory)
    instrument = canonical.record_listed_instrument(
        {
            **common,
            "instrument_key": f"golden-{stock_code}",
            "expected_latest_revision_id": None,
            "canonical_symbol": stock_code,
            "security_type": "common_equity",
            "market_code": "CN_A",
            "exchange_code_namespace": "ISO_MIC",
            "exchange_code": "XSHE",
            "currency_code": "CNY",
            "listing_date": "1991-04-03",
            "delisting_date": None,
            "listing_status": "active",
        }
    )
    series = canonical.record_series(
        {
            **common,
            "series_contract_key": f"golden-{stock_code}-close",
            "instrument_id": instrument["instrument_id"],
            "instrument_revision_id": instrument["instrument_revision_id"],
            "expected_latest_revision_id": None,
            "provider": "fixture",
            "dataset": "daily_price",
            "series_key": "g" * 64,
            "source_stock_code": stock_code,
            "source_adjust_type": "",
            "price_kind": "official_close",
            "adjustment_basis": "unadjusted",
            "unit_code": "currency_per_share",
            "currency_code": "CNY",
            "decimal_scale": 2,
            "decimal_rule_code": "float_repr_decimal_v1",
            "rounding_mode": "ROUND_HALF_EVEN",
            "status": "accepted",
        }
    )
    price = canonical.record_price(
        {
            **common,
            "series_id": series["series_id"],
            "series_revision_id": series["series_revision_id"],
            "instrument_revision_id": instrument["instrument_revision_id"],
            "source_daily_price_id": source_id,
            "source_ingestion_run_id": run_id,
            "trade_date": "2026-06-30",
            "expected_latest_revision_id": None,
            "canonical_status": "accepted",
            "conflict_summary": None,
        }
    )
    eligibility = NormalizedValuationEligibilityCommandService(factory).record_eligibility(
        {
            **common,
            "assessment_key": f"golden-{stock_code}-normalized-valuation",
            "purpose_code": NORMALIZED_VALUATION_PURPOSE,
            "expected_latest_revision_id": None,
            "rule_version": NORMALIZED_VALUATION_RULE_VERSION,
            "state": "eligible",
            "reason_codes": [
                "canonical_price_accepted",
                "source_numeric_fidelity_disclosed",
            ],
            "requested_trade_date": "2026-06-30",
            "canonical_price_revision_ids": [price["canonical_price_revision_id"]],
        }
    )
    return instrument, price, eligibility


def observation_payload(
    *,
    key: str,
    research,
    research_revision,
    instrument,
    claim_revision_id,
    evidence_link,
    metric_code: str,
    source_kind: str,
    value_text: str,
    period_basis: str,
    target_period_key: str,
    accounting_scope: str,
    observation_as_of_date: str,
    period_end_date: str,
    cutoff: str,
    recorded_at: str,
    period_start_date: str | None = None,
    fiscal_year: int | None = None,
    effective_start_date: str | None = None,
):
    currency_code = None if metric_code == "diluted_shares_outstanding" else "CNY"
    unit_code = "shares" if metric_code == "diluted_shares_outstanding" else "currency_amount"
    return {
        "observation_key": key,
        "company_research_id": str(research.id),
        "company_research_revision_id": str(research_revision.id),
        "instrument_id": instrument["instrument_id"],
        "instrument_revision_id": instrument["instrument_revision_id"],
        "metric_code": metric_code,
        "source_kind": source_kind,
        "observation_state": "supported",
        "value_text": value_text,
        "currency_code": currency_code,
        "unit_code": unit_code,
        "period_basis": period_basis,
        "target_period_key": target_period_key,
        "accounting_scope": accounting_scope,
        "observation_as_of_date": observation_as_of_date,
        "period_start_date": period_start_date,
        "period_end_date": period_end_date,
        "fiscal_year": fiscal_year,
        "effective_start_date": effective_start_date,
        "effective_end_date": None,
        "rationale": "Exact offline golden-path observation.",
        "falsification_condition": "A later attributable source may supersede this revision.",
        "information_cutoff_date": cutoff,
        "recorded_at_utc": recorded_at,
        "recorded_by": "golden-path",
        "expected_latest_revision_id": None,
        "claim_revision_ids": [str(claim_revision_id)],
        "evidence_links": [
            {
                "claim_revision_id": str(claim_revision_id),
                "claim_evidence_link_id": str(evidence_link.id),
                "evidence_id": str(evidence_link.evidence_id),
            }
        ],
    }


def test_production_boundary_golden_path_for_metrics_and_expectation_gap(database) -> None:
    research, research_revision, claim_revision_id, evidence_link = research_graph(database)
    instrument, price, eligibility = canonical_graph(database, research.stock_code)
    commands = NormalizedValuationCommandService(database)

    common = {
        "research": research,
        "research_revision": research_revision,
        "instrument": instrument,
        "claim_revision_id": claim_revision_id,
        "evidence_link": evidence_link,
        "cutoff": "2026-07-22",
        "recorded_at": "2026-07-22T21:00:00Z",
    }
    observations = {
        "shares": commands.record_observation(
            observation_payload(
                **common,
                key="golden-shares",
                metric_code="diluted_shares_outstanding",
                source_kind="actual",
                value_text="1000000000",
                period_basis="instant",
                target_period_key="SHARES-2026-06-30",
                accounting_scope="consolidated_attributable",
                observation_as_of_date="2026-06-20",
                period_end_date="2026-06-20",
                effective_start_date="2026-01-01",
            )
        ),
        "revenue": commands.record_observation(
            observation_payload(
                **common,
                key="golden-revenue-ttm",
                metric_code="revenue",
                source_kind="actual",
                value_text="10000000000",
                period_basis="ttm",
                target_period_key="TTM-2026-06-20",
                accounting_scope="consolidated",
                observation_as_of_date="2026-06-20",
                period_start_date="2025-06-21",
                period_end_date="2026-06-20",
            )
        ),
        "profit": commands.record_observation(
            observation_payload(
                **common,
                key="golden-profit-ttm",
                metric_code="net_profit_attributable",
                source_kind="actual",
                value_text="2000000000",
                period_basis="ttm",
                target_period_key="TTM-2026-06-20",
                accounting_scope="consolidated_attributable",
                observation_as_of_date="2026-06-20",
                period_start_date="2025-06-21",
                period_end_date="2026-06-20",
            )
        ),
        "ebitda": commands.record_observation(
            observation_payload(
                **common,
                key="golden-ebitda-ttm",
                metric_code="ebitda",
                source_kind="actual",
                value_text="3000000000",
                period_basis="ttm",
                target_period_key="TTM-2026-06-20",
                accounting_scope="consolidated",
                observation_as_of_date="2026-06-20",
                period_start_date="2025-06-21",
                period_end_date="2026-06-20",
            )
        ),
        "fcf": commands.record_observation(
            observation_payload(
                **common,
                key="golden-fcf-ttm",
                metric_code="free_cash_flow",
                source_kind="actual",
                value_text="1000000000",
                period_basis="ttm",
                target_period_key="TTM-2026-06-20",
                accounting_scope="consolidated",
                observation_as_of_date="2026-06-20",
                period_start_date="2025-06-21",
                period_end_date="2026-06-20",
            )
        ),
        "debt": commands.record_observation(
            observation_payload(
                **common,
                key="golden-net-debt",
                metric_code="net_debt",
                source_kind="actual",
                value_text="1000000000",
                period_basis="instant",
                target_period_key="NET-DEBT-2026-06-20",
                accounting_scope="consolidated",
                observation_as_of_date="2026-06-20",
                period_end_date="2026-06-20",
            )
        ),
    }

    metric_common = {
        "instrument_id": instrument["instrument_id"],
        "instrument_revision_id": instrument["instrument_revision_id"],
        "valuation_as_of_date": "2026-06-30",
        "target_period_key": "TTM-2026-06-20",
        "period_basis": "ttm",
        "formula_version": "aquantai.normalized-valuation.v1",
        "canonical_price_revision_id": price["canonical_price_revision_id"],
        "comparison_eligibility_revision_id": eligibility["eligibility_revision_id"],
        "diluted_shares_revision_id": observations["shares"]["revision_id"],
        "information_cutoff_date": "2026-07-22",
        "recorded_at_utc": "2026-07-22T22:00:00Z",
        "recorded_by": "golden-path",
        "expected_latest_revision_id": None,
    }
    metrics = {
        "pe": commands.record_metric(
            {
                **metric_common,
                "metric_key": "golden-pe",
                "metric_code": "pe",
                "accounting_scope": "consolidated_attributable",
                "denominator_revision_id": observations["profit"]["revision_id"],
            }
        ),
        "ps": commands.record_metric(
            {
                **metric_common,
                "metric_key": "golden-ps",
                "metric_code": "ps",
                "accounting_scope": "consolidated",
                "denominator_revision_id": observations["revenue"]["revision_id"],
            }
        ),
        "ev_ebitda": commands.record_metric(
            {
                **metric_common,
                "metric_key": "golden-ev-ebitda",
                "metric_code": "ev_ebitda",
                "accounting_scope": "consolidated",
                "denominator_revision_id": observations["ebitda"]["revision_id"],
                "net_debt_revision_id": observations["debt"]["revision_id"],
            }
        ),
        "fcf_yield": commands.record_metric(
            {
                **metric_common,
                "metric_key": "golden-fcf-yield",
                "metric_code": "fcf_yield",
                "accounting_scope": "consolidated",
                "denominator_revision_id": observations["fcf"]["revision_id"],
            }
        ),
    }
    assert metrics["pe"]["normalized_value_text"] == "10.0000"
    assert metrics["ps"]["normalized_value_text"] == "2.0000"
    assert metrics["ev_ebitda"]["normalized_value_text"] == "7.0000"
    assert metrics["fcf_yield"]["normalized_value_text"] == "5.0000"

    expected = commands.record_observation(
        observation_payload(
            research=research,
            research_revision=research_revision,
            instrument=instrument,
            claim_revision_id=claim_revision_id,
            evidence_link=evidence_link,
            key="golden-profit-consensus-fy2026",
            metric_code="net_profit_attributable",
            source_kind="consensus",
            value_text="2000000000",
            period_basis="forward_fy1",
            target_period_key="FY2026",
            accounting_scope="consolidated_attributable",
            observation_as_of_date="2026-07-15",
            period_start_date="2026-01-01",
            period_end_date="2026-12-31",
            fiscal_year=2026,
            cutoff="2026-07-22",
            recorded_at="2026-07-22T23:00:00Z",
        )
    )
    actual = commands.record_observation(
        observation_payload(
            research=research,
            research_revision=research_revision,
            instrument=instrument,
            claim_revision_id=claim_revision_id,
            evidence_link=evidence_link,
            key="golden-profit-actual-fy2026",
            metric_code="net_profit_attributable",
            source_kind="actual",
            value_text="2200000000",
            period_basis="fy_actual",
            target_period_key="FY2026",
            accounting_scope="consolidated_attributable",
            observation_as_of_date="2027-02-20",
            period_start_date="2026-01-01",
            period_end_date="2026-12-31",
            fiscal_year=2026,
            cutoff="2027-02-20",
            recorded_at="2027-02-21T10:00:00Z",
        )
    )
    gap = commands.record_expectation_gap(
        {
            "gap_key": "golden-profit-fy2026-gap",
            "company_research_id": str(research.id),
            "company_research_revision_id": str(research_revision.id),
            "instrument_id": instrument["instrument_id"],
            "instrument_revision_id": instrument["instrument_revision_id"],
            "metric_code": "net_profit_attributable",
            "target_period_key": "FY2026",
            "expected_source_kind": "consensus",
            "rule_version": "aquantai.normalized-expectation-gap.v1",
            "expected_observation_revision_id": expected["revision_id"],
            "actual_observation_revision_id": actual["revision_id"],
            "calculation_as_of_date": "2027-02-20",
            "information_cutoff_date": "2027-02-20",
            "recorded_at_utc": "2027-02-21T11:00:00Z",
            "recorded_by": "golden-path",
            "expected_latest_revision_id": None,
        }
    )
    assert gap["absolute_gap_text"] == "200000000.000000"
    assert gap["percentage_gap_text"] == "10.0000"
    assert gap["direction"] == "above_expected"

    with database() as session:
        query = NormalizedValuationQueryService(session)
        pe = query.get_metric_revision(
            UUID(metrics["pe"]["revision_id"]),
            as_of_cutoff=date(2026, 7, 22),
            as_of_recorded_at_utc=datetime(2026, 7, 22, 22, tzinfo=UTC),
        )
        gap_payload = query.get_expectation_gap_revision(
            UUID(gap["revision_id"]),
            as_of_cutoff=date(2027, 2, 20),
            as_of_recorded_at_utc=datetime(2027, 2, 21, 11, tzinfo=UTC),
        )
    assert pe["normalized_value_text"] == "10.0000"
    assert len(pe["inputs"]) == 4
    assert gap_payload["percentage_gap_text"] == "10.0000"
