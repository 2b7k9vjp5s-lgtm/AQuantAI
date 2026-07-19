"""Deterministic offline fixture for v0.6B expectation and valuation snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.models import DailyPriceRecord, IngestionRun
from industry_alpha.commands import EvidenceLedgerCommandService, EvidenceLinkInput
from industry_alpha.models import ClaimEvidenceLink, ClaimRevision
from industry_alpha.stage2_commands import (
    Stage2CompanyResearchCommandService,
    Stage2VerificationInput,
)
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
    disputed_expectation_id: UUID
    missing_valuation_id: UUID
    later_valuation_revision_id: UUID
    later_research_revision_id: UUID
    later_hypothesis_revision_id: UUID
    later_claim_revision_id: UUID
    contradiction_evidence_id: UUID
    later_daily_price_id: int
    later_ingestion_run_id: int


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
            completed_at=_recorded(15, 11),
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
        initial_claim = session.get(ClaimRevision, claim_revision_id)
        support_evidence_id = session.scalar(
            select(ClaimEvidenceLink.evidence_id)
            .where(
                ClaimEvidenceLink.claim_revision_id == claim_revision_id,
                ClaimEvidenceLink.relation == "supports",
            )
            .order_by(ClaimEvidenceLink.id)
        )

    ledger = EvidenceLedgerCommandService(session_factory)
    contradiction = ledger.add_evidence(
        research.case_id,
        evidence_grade="C",
        source_kind="research",
        source_title="Later fixture contradiction",
        publisher_or_author="Fixture research publisher",
        source_locator="fixture://stage2-v06b/later-contradiction",
        information_date=date(2026, 7, 17),
        summary="Later attributable evidence disputes the earlier bounded inference.",
        content_fingerprint="stage2-v06b-later-contradiction-v1",
        recorded_at_utc=_recorded(17),
    )
    disputed_claim = ledger.append_claim_revision(
        initial_claim.claim_id,
        statement="Later attributable evidence leaves the financial-transmission claim disputed.",
        claim_kind="inference",
        claim_status="disputed",
        inference_confidence="low",
        inference_basis="The original supporting evidence and a later contradiction coexist.",
        information_cutoff_date=date(2026, 7, 17),
        evidence_links=(
            EvidenceLinkInput(support_evidence_id, "supports"),
            EvidenceLinkInput(contradiction.id, "contradicts"),
        ),
        recorded_at_utc=_recorded(17, 11),
    )

    stage2_commands = Stage2CompanyResearchCommandService(session_factory)
    disputed_hypothesis = stage2_commands.append_hypothesis_revision(
        stage2.supported_hypothesis_id,
        hypothesis_status="disputed",
        mechanism="Later evidence disputes whether attributable demand reaches recognized revenue.",
        direction="uncertain",
        operating_metric="shipped units",
        financial_statement_line="revenue",
        expected_lag_horizon="requires further verification",
        confidence="low",
        basis="A later C-grade contradiction is frozen alongside the earlier support.",
        information_cutoff_date=date(2026, 7, 17),
        claim_revision_ids=(disputed_claim.id,),
        recorded_at_utc=_recorded(17, 12),
    )
    later_research = stage2_commands.append_research_revision(
        stage2.supported_research_id,
        workflow_state="completed",
        conclusion_status="disputed",
        research_question="How could the frozen Stage 1 relationship affect operating and financial lines?",
        summary="Later evidence creates an explicit dispute without rewriting earlier research revisions.",
        information_cutoff_date=date(2026, 7, 17),
        hypothesis_revision_ids=(disputed_hypothesis.id,),
        verification_items=(
            Stage2VerificationInput("Resolve the later contradictory evidence with primary disclosure."),
        ),
        recorded_at_utc=_recorded(17, 13),
    )

    with session_factory.begin() as session:
        later_run = IngestionRun(
            batch_identifier="stage2-v06b-fixture-later-price",
            series_key="f" * 64,
            series_identity={
                "provider": "fixture",
                "dataset": "daily_price",
                "scope": {"stock_codes": [research.stock_code]},
            },
            provider="fixture",
            dataset="daily_price",
            imported_at=_recorded(18, 8),
            completed_at=_recorded(18, 9),
            requested_start_date=date(2026, 7, 18),
            requested_end_date=date(2026, 7, 18),
            information_cutoff_date=date(2026, 7, 18),
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
        session.add(later_run)
        session.flush()
        later_price = DailyPriceRecord(
            ingestion_run_id=later_run.id,
            trade_date=date(2026, 7, 18),
            stock_code=research.stock_code,
            open=10.3,
            high=10.7,
            low=10.1,
            close=10.5,
            volume=1100.0,
            amount=11550.0,
            adjust_type="qfq",
            source=research.source,
        )
        session.add(later_price)
        session.flush()
        later_price_id = later_price.id
        later_run_id = later_run.id

    disputed_expectation = commands.create_expectation(
        stage2.supported_research_id,
        expectation_key="fixture-disputed-expectation",
        company_research_revision_id=later_research.id,
        hypothesis_revision_ids=(disputed_hypothesis.id,),
        claim_revision_ids=(disputed_claim.id,),
        subject="Later disputed market expectation",
        period_horizon="future reporting period",
        expectation_kind="research_assumption",
        direction="uncertain",
        status="disputed",
        confidence="low",
        basis="The frozen evidence boundary contains an explicit contradiction.",
        information_cutoff_date=date(2026, 7, 18),
        recorded_at_utc=_recorded(18, 10),
    )
    missing_valuation = commands.create_valuation_snapshot(
        stage2.supported_research_id,
        valuation_key="fixture-missing-valuation",
        company_research_revision_id=later_research.id,
        hypothesis_revision_ids=(disputed_hypothesis.id,),
        claim_revision_ids=(disputed_claim.id,),
        valuation_method="missing_data",
        metric_context="Public valuation metric unavailable at the frozen boundary",
        observed_value=None,
        missing_data_reason="尚未获得可靠公开证据，未构造估值输入。",
        unit=None,
        currency=None,
        comparison_basis="No comparison is performed without attributable data.",
        assumptions="Missing data remains explicit and no value is fabricated.",
        status="disputed",
        confidence="low",
        information_cutoff_date=date(2026, 7, 18),
        recorded_at_utc=_recorded(18, 11),
    )
    later_price_revision = commands.append_valuation_revision(
        valuation.id,
        company_research_revision_id=later_research.id,
        hypothesis_revision_ids=(disputed_hypothesis.id,),
        claim_revision_ids=(disputed_claim.id,),
        valuation_method="market_price_context",
        metric_context="Later observed local fixture close price context only",
        observed_value="10.5",
        missing_data_reason=None,
        unit="close",
        currency="CNY",
        comparison_basis="A later exact daily_price row; no fair value or expected return is derived.",
        assumptions="The later price is visible only when this snapshot explicitly binds it.",
        status="disputed",
        confidence="low",
        information_cutoff_date=date(2026, 7, 18),
        daily_price_id=later_price_id,
        recorded_at_utc=_recorded(18, 12),
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
        disputed_expectation_id=disputed_expectation.id,
        missing_valuation_id=missing_valuation.id,
        later_valuation_revision_id=later_price_revision.id,
        later_research_revision_id=later_research.id,
        later_hypothesis_revision_id=disputed_hypothesis.id,
        later_claim_revision_id=disputed_claim.id,
        contradiction_evidence_id=contradiction.id,
        later_daily_price_id=later_price_id,
        later_ingestion_run_id=later_run_id,
    )
