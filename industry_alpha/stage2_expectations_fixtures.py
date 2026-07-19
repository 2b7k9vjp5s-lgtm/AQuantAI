"""Deterministic offline fixture for v0.6B expectation and valuation snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.models import DailyPriceRecord, IngestionRun
from industry_alpha.stage2_expectations_commands import Stage2ExpectationCommandService
from industry_alpha.stage2_expectations_models import (
    Stage2MarketExpectationRevision,
    Stage2ValuationSnapshotRevision,
)
from industry_alpha.stage2_fixtures import (
    Stage2FixtureIds,
    build_stage2_company_research_fixture,
)
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
    Stage2HypothesisClaimLink,
    Stage2ResearchHypothesisLink,
)


@dataclass(frozen=True)
class Stage2ExpectationFixtureIds:
    stage2: Stage2FixtureIds
    expectation_id: UUID
    valuation_id: UUID
    expectation_revision_id: UUID
    valuation_revision_id: UUID
    daily_price_id: int
    ingestion_run_id: int


def _recorded(day: int, hour: int = 10) -> datetime:
    return datetime(2026, 7, day, hour, tzinfo=timezone.utc)


def build_stage2_expectation_valuation_fixture(
    session_factory: sessionmaker[Session],
) -> Stage2ExpectationFixtureIds:
    stage2 = build_stage2_company_research_fixture(session_factory)
    with session_factory.begin() as session:
        research = session.get(Stage2CompanyResearch, stage2.supported_research_id)
        research_revision = session.scalar(
            select(Stage2CompanyResearchRevision)
            .where(
                Stage2CompanyResearchRevision.company_research_id
                == research.id,
                Stage2CompanyResearchRevision.revision_no == 3,
            )
        )
        hypothesis_revision_id = session.scalar(
            select(Stage2ResearchHypothesisLink.hypothesis_revision_id).where(
                Stage2ResearchHypothesisLink.company_research_revision_id
                == research_revision.id
            )
        )
        claim_revision_id = session.scalar(
            select(Stage2HypothesisClaimLink.claim_revision_id).where(
                Stage2HypothesisClaimLink.hypothesis_revision_id
                == hypothesis_revision_id
            )
        )
        run = IngestionRun(
            batch_identifier="stage2-v06b-fixture-price",
            series_key="f" * 64,
            series_identity={
                "provider": "fixture",
                "dataset": "daily_price",
                "scope": {"stock_codes": [research.stock_code]},
            },
            provider="fixture",
            dataset="daily_price",
            imported_at=_recorded(15),
            completed_at=_recorded(15, 1),
            requested_start_date=date(2026, 7, 15),
            requested_end_date=date(2026, 7, 15),
            information_cutoff_date=date(2026, 7, 15),
            requested_scope={"stock_codes": [research.stock_code]},
            provider_request_metadata={"offline_fixture": True},
            adapter_version="fixture-v06b",
            snapshot_mode="complete",
            contract_version="v0.3",
            status="succeeded",
            row_count_received=1,
            row_count_written=1,
            dataset_counts={"daily_price": 1},
            error_summary=None,
        )
        session.add(run)
        session.flush()
        price = DailyPriceRecord(
            ingestion_run_id=run.id,
            trade_date=date(2026, 7, 15),
            stock_code=research.stock_code,
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            volume=1000.0,
            amount=10200.0,
            adjust_type="qfq",
            source=research.source,
        )
        session.add(price)
        session.flush()
        price_id = price.id
        run_id = run.id

    commands = Stage2ExpectationCommandService(session_factory)
    expectation = commands.create_expectation(
        stage2.supported_research_id,
        expectation_key="fixture-demand-expectation",
        company_research_revision_id=research_revision.id,
        hypothesis_revision_ids=(hypothesis_revision_id,),
        claim_revision_ids=(claim_revision_id,),
        subject="Market expectation around attributable input demand",
        period_horizon="next reporting period",
        expectation_kind="research_assumption",
        direction="positive",
        status="supported",
        confidence="medium",
        basis="Bound to the supported Stage 2 hypothesis and frozen A/B/C claim evidence.",
        information_cutoff_date=date(2026, 7, 15),
        recorded_at_utc=_recorded(15, 12),
    )
    valuation = commands.create_valuation_snapshot(
        stage2.supported_research_id,
        valuation_key="fixture-price-context",
        company_research_revision_id=research_revision.id,
        hypothesis_revision_ids=(hypothesis_revision_id,),
        claim_revision_ids=(claim_revision_id,),
        valuation_method="market_price_context",
        metric_context="Observed local fixture close price context only",
        observed_value="10.2",
        missing_data_reason=None,
        unit="close",
        currency="CNY",
        comparison_basis="Single local daily_price row; no fair value or expected return is derived.",
        assumptions="The value is a persisted fixture observation, not a valuation model output.",
        status="supported",
        confidence="low",
        information_cutoff_date=date(2026, 7, 15),
        daily_price_id=price_id,
        recorded_at_utc=_recorded(15, 13),
    )
    later = commands.append_expectation_revision(
        expectation.id,
        company_research_revision_id=research_revision.id,
        hypothesis_revision_ids=(hypothesis_revision_id,),
        claim_revision_ids=(claim_revision_id,),
        subject="Later expectation revision hidden from earlier cutoffs",
        period_horizon="subsequent reporting period",
        expectation_kind="research_assumption",
        direction="mixed",
        status="supported",
        confidence="medium",
        basis="Later append-only revision for cutoff regression tests.",
        information_cutoff_date=date(2026, 7, 16),
        recorded_at_utc=_recorded(16),
    )
    with session_factory() as session:
        valuation_revision = session.scalar(
            select(Stage2ValuationSnapshotRevision).where(
                Stage2ValuationSnapshotRevision.valuation_id == valuation.id
            )
        )
    return Stage2ExpectationFixtureIds(
        stage2=stage2,
        expectation_id=expectation.id,
        valuation_id=valuation.id,
        expectation_revision_id=later.id,
        valuation_revision_id=valuation_revision.id,
        daily_price_id=price_id,
        ingestion_run_id=run_id,
    )
