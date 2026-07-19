"""Deterministic offline fixture for v0.6C catalyst and risk assessments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.stage2_assessments_commands import Stage2AssessmentCommandService
from industry_alpha.stage2_assessments_models import Stage2CatalystAssessmentRevision, Stage2RiskAssessmentRevision
from industry_alpha.stage2_expectations_fixtures import Stage2ExpectationFixtureIds, build_stage2_expectation_valuation_fixture
from industry_alpha.stage2_expectations_models import (
    Stage2ExpectationClaimLink, Stage2ExpectationHypothesisLink, Stage2MarketExpectationRevision,
    Stage2ValuationClaimLink, Stage2ValuationHypothesisLink, Stage2ValuationSnapshotRevision,
)


@dataclass(frozen=True)
class Stage2AssessmentFixtureIds:
    v06b: Stage2ExpectationFixtureIds
    supported_catalyst_id: UUID
    disputed_catalyst_id: UUID
    supported_risk_id: UUID
    disputed_risk_id: UUID
    supported_catalyst_revision_id: UUID
    supported_risk_revision_id: UUID
    later_catalyst_revision_id: UUID
    later_risk_revision_id: UUID


def _recorded(day: int, hour: int) -> datetime:
    return datetime(2026, 7, day, hour, tzinfo=timezone.utc)


def _expectation_boundary(session: Session, revision_id: UUID) -> tuple[UUID, UUID, UUID]:
    revision = session.get(Stage2MarketExpectationRevision, revision_id)
    hypothesis_id = session.scalar(select(Stage2ExpectationHypothesisLink.hypothesis_revision_id).where(Stage2ExpectationHypothesisLink.expectation_revision_id == revision.id))
    claim_id = session.scalar(select(Stage2ExpectationClaimLink.claim_revision_id).where(Stage2ExpectationClaimLink.expectation_revision_id == revision.id))
    return revision.company_research_revision_id, hypothesis_id, claim_id


def _latest_expectation(session: Session, identity_id: UUID) -> Stage2MarketExpectationRevision:
    return session.scalars(select(Stage2MarketExpectationRevision).where(Stage2MarketExpectationRevision.expectation_id == identity_id).order_by(Stage2MarketExpectationRevision.revision_no.desc())).first()


def _latest_valuation(session: Session, identity_id: UUID) -> Stage2ValuationSnapshotRevision:
    return session.scalars(select(Stage2ValuationSnapshotRevision).where(Stage2ValuationSnapshotRevision.valuation_id == identity_id).order_by(Stage2ValuationSnapshotRevision.revision_no.desc())).first()


def build_stage2_assessment_fixture(session_factory: sessionmaker[Session]) -> Stage2AssessmentFixtureIds:
    v06b = build_stage2_expectation_valuation_fixture(session_factory)
    with session_factory() as session:
        research_revision_id, hypothesis_id, claim_id = _expectation_boundary(session, v06b.expectation_revision_id)
        disputed_expectation = _latest_expectation(session, v06b.disputed_expectation_id)
        disputed_valuation = _latest_valuation(session, v06b.missing_valuation_id)
        disputed_hypothesis_id = session.scalar(select(Stage2ExpectationHypothesisLink.hypothesis_revision_id).where(Stage2ExpectationHypothesisLink.expectation_revision_id == disputed_expectation.id))
        disputed_claim_id = session.scalar(select(Stage2ExpectationClaimLink.claim_revision_id).where(Stage2ExpectationClaimLink.expectation_revision_id == disputed_expectation.id))

    commands = Stage2AssessmentCommandService(session_factory)
    supported_catalyst = commands.create_catalyst(
        v06b.stage2.supported_research_id,
        catalyst_key="fixture-attributable-demand-observation",
        company_research_revision_id=research_revision_id,
        hypothesis_revision_ids=(hypothesis_id,),
        expectation_revision_ids=(v06b.expectation_revision_id,),
        valuation_revision_ids=(v06b.valuation_revision_id,),
        claim_revision_ids=(claim_id,),
        catalyst_category="demand",
        subject="Attributable input-demand disclosure may become observable",
        expected_observation_window="next two reporting periods",
        status="supported",
        confidence="medium",
        trigger_observation_criteria="A primary filing reports attributable shipped-unit demand using a comparable scope.",
        basis="The exact supported hypothesis and frozen A/B/C evidence establish a bounded observation path.",
        uncertainty="Magnitude and timing remain unquantified; this is not an alert or recommendation.",
        information_cutoff_date=date(2026, 7, 16),
        recorded_at_utc=_recorded(16, 14),
    )
    supported_risk = commands.create_risk(
        v06b.stage2.supported_research_id,
        risk_key="fixture-demand-transmission-risk",
        company_research_revision_id=research_revision_id,
        hypothesis_revision_ids=(hypothesis_id,),
        expectation_revision_ids=(v06b.expectation_revision_id,),
        valuation_revision_ids=(v06b.valuation_revision_id,),
        claim_revision_ids=(claim_id,),
        risk_category="execution",
        subject="Attributable demand may fail to reach recognized revenue",
        downside_path="Observed demand does not translate into shipped units or recognized revenue within the bounded lag.",
        thesis_invalidation_condition="Primary disclosures show no attributable shipment or revenue transmission across two reporting periods.",
        mitigants="尚未获得可靠公开证据证明存在可量化缓释因素。",
        status="supported",
        confidence="medium",
        basis="The frozen evidence supports the transmission mechanism while leaving execution uncertainty explicit.",
        uncertainty="No probability, loss estimate, score, or investment conclusion is produced.",
        information_cutoff_date=date(2026, 7, 16),
        recorded_at_utc=_recorded(16, 15),
    )
    disputed_catalyst = commands.create_catalyst(
        v06b.stage2.supported_research_id,
        catalyst_key="fixture-disputed-timing",
        company_research_revision_id=v06b.later_research_revision_id,
        hypothesis_revision_ids=(disputed_hypothesis_id,),
        expectation_revision_ids=(disputed_expectation.id,),
        valuation_revision_ids=(disputed_valuation.id,),
        claim_revision_ids=(disputed_claim_id,),
        catalyst_category="customer",
        subject="Possible timing remains disputed",
        expected_observation_window="尚未获得可靠公开证据",
        status="disputed",
        confidence="low",
        trigger_observation_criteria="Only a future attributable primary disclosure could resolve the contradiction.",
        basis="The frozen claim contains both support and contradiction.",
        uncertainty="No event date, customer order, or outcome is fabricated.",
        information_cutoff_date=date(2026, 7, 18),
        recorded_at_utc=_recorded(18, 13),
    )
    disputed_risk = commands.create_risk(
        v06b.stage2.supported_research_id,
        risk_key="fixture-disputed-revenue-risk",
        company_research_revision_id=v06b.later_research_revision_id,
        hypothesis_revision_ids=(disputed_hypothesis_id,),
        expectation_revision_ids=(disputed_expectation.id,),
        valuation_revision_ids=(disputed_valuation.id,),
        claim_revision_ids=(disputed_claim_id,),
        risk_category="demand",
        subject="Revenue transmission remains disputed",
        downside_path="The disputed demand signal may not translate into attributable revenue.",
        thesis_invalidation_condition="Primary evidence establishes that the asserted transmission did not occur.",
        mitigants="尚未获得可靠公开证据",
        status="disputed",
        confidence="low",
        basis="Visible contradictory evidence prevents a supported judgment.",
        uncertainty="The downside path is descriptive and unquantified.",
        information_cutoff_date=date(2026, 7, 18),
        recorded_at_utc=_recorded(18, 14),
    )
    later_catalyst = commands.append_catalyst_revision(
        supported_catalyst.id,
        company_research_revision_id=v06b.later_research_revision_id,
        hypothesis_revision_ids=(disputed_hypothesis_id,),
        expectation_revision_ids=(disputed_expectation.id,),
        valuation_revision_ids=(disputed_valuation.id,),
        claim_revision_ids=(disputed_claim_id,),
        catalyst_category="demand", subject="Later disputed catalyst revision",
        expected_observation_window="尚未获得可靠公开证据", status="disputed", confidence="low",
        trigger_observation_criteria="Primary evidence must resolve the later contradiction.",
        basis="Later upstream evidence is frozen only in this append-only revision.",
        uncertainty="Earlier cutoff views remain unchanged.", information_cutoff_date=date(2026, 7, 19),
        recorded_at_utc=_recorded(19, 10),
    )
    later_risk = commands.append_risk_revision(
        supported_risk.id,
        company_research_revision_id=v06b.later_research_revision_id,
        hypothesis_revision_ids=(disputed_hypothesis_id,),
        expectation_revision_ids=(disputed_expectation.id,),
        valuation_revision_ids=(disputed_valuation.id,),
        claim_revision_ids=(disputed_claim_id,),
        risk_category="execution", subject="Later disputed execution risk",
        downside_path="Later contradictory evidence weakens the earlier bounded mechanism.",
        thesis_invalidation_condition="Primary evidence resolves the asserted mechanism against the thesis.",
        mitigants="尚未获得可靠公开证据", status="disputed", confidence="low",
        basis="Later evidence is explicit and does not rewrite revision one.",
        uncertainty="No score or recommendation is produced.", information_cutoff_date=date(2026, 7, 19),
        recorded_at_utc=_recorded(19, 11),
    )
    with session_factory() as session:
        catalyst_v1 = session.scalar(select(Stage2CatalystAssessmentRevision).where(Stage2CatalystAssessmentRevision.catalyst_id == supported_catalyst.id, Stage2CatalystAssessmentRevision.revision_no == 1))
        risk_v1 = session.scalar(select(Stage2RiskAssessmentRevision).where(Stage2RiskAssessmentRevision.risk_id == supported_risk.id, Stage2RiskAssessmentRevision.revision_no == 1))
    return Stage2AssessmentFixtureIds(v06b, supported_catalyst.id, disputed_catalyst.id, supported_risk.id, disputed_risk.id, catalyst_v1.id, risk_v1.id, later_catalyst.id, later_risk.id)
