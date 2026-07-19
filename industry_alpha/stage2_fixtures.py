"""Deterministic offline fixture for Stage 2 company research."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.commands import EvidenceLedgerCommandService
from industry_alpha.models import ClaimRevision
from industry_alpha.stage1_fixtures import build_stage1_beneficiary_fixture
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryAssertionLink,
    Stage1BeneficiaryClaimLink,
    Stage1CandidatePool,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)
from industry_alpha.stage2_commands import (
    Stage2CompanyResearchCommandService,
    Stage2VerificationInput,
)
from industry_alpha.stage2_models import Stage2FinancialHypothesisRevision


@dataclass(frozen=True)
class Stage2FixtureIds:
    map_id: UUID
    candidate_pool_id: UUID
    candidate_pool_revision_id: UUID
    supported_research_id: UUID
    draft_research_id: UUID
    supported_hypothesis_id: UUID
    draft_hypothesis_id: UUID


def _recorded(day: int, hour: int = 10) -> datetime:
    return datetime(2026, 7, day, hour, tzinfo=timezone.utc)


def build_stage2_company_research_fixture(
    session_factory: sessionmaker[Session],
) -> Stage2FixtureIds:
    stage1 = build_stage1_beneficiary_fixture(session_factory)
    with session_factory() as session:
        pool = session.get(Stage1CandidatePool, stage1.candidate_pool_id)
        pool_revision = session.scalar(
            select(Stage1CandidatePoolRevision).where(
                Stage1CandidatePoolRevision.candidate_pool_id == pool.id
            )
        )
        memberships = list(
            session.scalars(
                select(Stage1CandidatePoolMembership)
                .where(
                    Stage1CandidatePoolMembership.candidate_pool_revision_id
                    == pool_revision.id
                )
                .join(
                    Stage1Beneficiary,
                    Stage1Beneficiary.id
                    == Stage1CandidatePoolMembership.beneficiary_id,
                )
                .order_by(Stage1Beneficiary.stock_code)
            )
        )
        beneficiary_claims = {
            membership.id: session.scalar(
                select(Stage1BeneficiaryClaimLink.claim_revision_id).where(
                    Stage1BeneficiaryClaimLink.beneficiary_revision_id
                    == membership.beneficiary_revision_id
                )
            )
            for membership in memberships
        }
        assertions = {
            membership.id: session.scalar(
                select(Stage1BeneficiaryAssertionLink.id).where(
                    Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                    == membership.beneficiary_revision_id
                )
            )
            for membership in memberships
        }
        case_id = pool.case_id

    ledger = EvidenceLedgerCommandService(session_factory)
    missing_claim = ledger.create_claim(
        case_id,
        claim_key="stage2-fixture-unverified-transmission",
        statement="The draft financial-transmission path remains unverified.",
        claim_kind="inference",
        claim_status="draft",
        inference_confidence="low",
        inference_basis="No attributable evidence is available at the fixture cutoff.",
        information_cutoff_date=date(2026, 7, 9),
        evidence_links=(),
        recorded_at_utc=_recorded(9),
    )
    with session_factory() as session:
        missing_claim_revision = session.scalar(
            select(ClaimRevision).where(ClaimRevision.claim_id == missing_claim.id)
        )

    commands = Stage2CompanyResearchCommandService(session_factory)
    supported_research = commands.create_company_research(
        pool_revision.id,
        memberships[0].id,
        workflow_state="open",
        conclusion_status="unassessed",
        research_question="How could the frozen Stage 1 relationship affect operating and financial lines?",
        summary="Initial Stage 2 file created from an exact frozen membership.",
        information_cutoff_date=date(2026, 7, 10),
        recorded_at_utc=_recorded(10),
    )
    draft_research = commands.create_company_research(
        pool_revision.id,
        memberships[1].id,
        workflow_state="open",
        conclusion_status="insufficient_evidence",
        research_question="Is the secondary relationship attributable to an operating metric?",
        summary="The current evidence boundary is explicitly incomplete.",
        information_cutoff_date=date(2026, 7, 10),
        recorded_at_utc=_recorded(10, 11),
    )
    supported_hypothesis = commands.create_hypothesis(
        supported_research.id,
        hypothesis_key="input-demand-to-revenue",
        stage1_assertion_link_id=assertions[memberships[0].id],
        hypothesis_status="supported",
        mechanism="Higher attributable input demand may increase shipped units before recognition.",
        direction="positive",
        operating_metric="shipped units",
        financial_statement_line="revenue",
        expected_lag_horizon="one to two reporting periods",
        confidence="medium",
        basis="A-grade fixture evidence supports the exact company relationship; magnitude is not estimated.",
        information_cutoff_date=date(2026, 7, 11),
        claim_revision_ids=(beneficiary_claims[memberships[0].id],),
        recorded_at_utc=_recorded(11),
    )
    draft_hypothesis = commands.create_hypothesis(
        draft_research.id,
        hypothesis_key="unverified-throughput-path",
        stage1_assertion_link_id=assertions[memberships[1].id],
        hypothesis_status="draft",
        mechanism="A possible throughput effect is retained only as an unsupported assumption.",
        direction="uncertain",
        operating_metric="throughput",
        financial_statement_line="revenue",
        expected_lag_horizon="unknown",
        confidence="low",
        basis="The exact claim has no evidence at this boundary and is not promoted.",
        information_cutoff_date=date(2026, 7, 11),
        claim_revision_ids=(missing_claim_revision.id,),
        recorded_at_utc=_recorded(11, 11),
    )
    with session_factory() as session:
        supported_revision = session.scalar(
            select(Stage2FinancialHypothesisRevision).where(
                Stage2FinancialHypothesisRevision.hypothesis_id
                == supported_hypothesis.id
            )
        )
    commands.append_research_revision(
        supported_research.id,
        workflow_state="completed",
        conclusion_status="supported",
        research_question="How could the frozen Stage 1 relationship affect operating and financial lines?",
        summary="One bounded positive transmission hypothesis is supported without quantifying impact.",
        information_cutoff_date=date(2026, 7, 12),
        hypothesis_revision_ids=(supported_revision.id,),
        verification_items=(
            Stage2VerificationInput("Verify shipped-unit disclosure in the next filing."),
        ),
        recorded_at_utc=_recorded(12),
    )
    later_hypothesis_revision = commands.append_hypothesis_revision(
        supported_hypothesis.id,
        hypothesis_status="supported",
        mechanism="Later evidence preserves the direction while extending the stated lag.",
        direction="positive",
        operating_metric="shipped units",
        financial_statement_line="revenue",
        expected_lag_horizon="two reporting periods",
        confidence="medium",
        basis="The same frozen A-grade claim supports this later append-only revision.",
        information_cutoff_date=date(2026, 7, 14),
        claim_revision_ids=(beneficiary_claims[memberships[0].id],),
        recorded_at_utc=_recorded(14),
    )
    commands.append_research_revision(
        supported_research.id,
        workflow_state="completed",
        conclusion_status="supported",
        research_question="How could the frozen Stage 1 relationship affect operating and financial lines?",
        summary="A later append-only revision updates the lag, not the frozen handoff.",
        information_cutoff_date=date(2026, 7, 15),
        hypothesis_revision_ids=(later_hypothesis_revision.id,),
        verification_items=(
            Stage2VerificationInput("Recheck the revised lag against the next two filings."),
        ),
        recorded_at_utc=_recorded(15),
    )
    return Stage2FixtureIds(
        map_id=stage1.map_id,
        candidate_pool_id=pool.id,
        candidate_pool_revision_id=pool_revision.id,
        supported_research_id=supported_research.id,
        draft_research_id=draft_research.id,
        supported_hypothesis_id=supported_hypothesis.id,
        draft_hypothesis_id=draft_hypothesis.id,
    )
