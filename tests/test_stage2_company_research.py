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
from backend.database.models import Base
from backend.main import app
from industry_alpha.errors import (
    EvidenceLedgerImmutableError,
    EvidenceLedgerValidationError,
)
from industry_alpha.chain_map_models import IndustryMapRelationshipRevision
from industry_alpha.commands import EvidenceLedgerCommandService
from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem
from industry_alpha.stage1_fixtures import build_stage1_beneficiary_fixture
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1CandidatePool,
    Stage1BeneficiaryAssertionLink,
    Stage1BeneficiaryClaimLink,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)
from industry_alpha.stage2_commands import (
    Stage2CompanyResearchCommandService,
    Stage2VerificationInput,
)
from industry_alpha.stage2_fixtures import build_stage2_company_research_fixture
from industry_alpha.stage2_models import (
    STAGE2_MODELS,
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
    Stage2FinancialHypothesis,
    Stage2FinancialHypothesisRevision,
    Stage2HypothesisClaimLink,
    Stage2HypothesisEvidenceLink,
)
from industry_alpha.stage2_query import Stage2CompanyResearchQueryService
from industry_alpha.stage2_repository import Stage2CompanyResearchRepository


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
    return build_stage2_company_research_fixture(session_factory)


def query(session_factory, research_id, cutoff=None):
    with session_factory() as session:
        return Stage2CompanyResearchQueryService(
            Stage2CompanyResearchRepository(session)
        ).get_research(research_id, as_of_cutoff=cutoff).to_dict()


def stage2_counts(session_factory):
    with session_factory() as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in STAGE2_MODELS
        )


def hypothesis_inputs(session_factory, hypothesis_id, revision_no=1):
    with session_factory() as session:
        revision = session.scalar(
            select(Stage2FinancialHypothesisRevision).where(
                Stage2FinancialHypothesisRevision.hypothesis_id == hypothesis_id,
                Stage2FinancialHypothesisRevision.revision_no == revision_no,
            )
        )
        claims = tuple(
            session.scalars(
                select(ClaimRevision.id)
                .join(
                    Stage2HypothesisClaimLink,
                    Stage2HypothesisClaimLink.claim_revision_id == ClaimRevision.id,
                )
                .where(
                    Stage2HypothesisClaimLink.hypothesis_revision_id == revision.id
                )
            )
        )
    return revision, claims


def add_stage2_test_claim(
    session_factory,
    case_id,
    *,
    claim_key,
    claim_status,
    relation="supports",
    evidence_grade="A",
    information_date=date(2026, 7, 15),
    recorded_at_utc=utc(15),
):
    with session_factory.begin() as session:
        evidence = EvidenceItem(
            case_id=case_id,
            evidence_grade=evidence_grade,
            source_kind="official",
            source_title=f"Fixture evidence for {claim_key}",
            information_date=information_date,
            recorded_at_utc=recorded_at_utc,
            summary=f"Bounded fixture evidence for {claim_key}.",
            content_fingerprint=f"{claim_key}-evidence",
        )
        claim = Claim(
            case_id=case_id,
            claim_key=claim_key,
            created_at_utc=recorded_at_utc,
        )
        session.add_all([evidence, claim])
        session.flush()
        revision = ClaimRevision(
            claim_id=claim.id,
            revision_no=1,
            statement=f"Fixture claim {claim_key}.",
            claim_kind="inference",
            claim_status=claim_status,
            inference_confidence="low",
            inference_basis="Fixture basis.",
            information_cutoff_date=information_date,
            recorded_at_utc=recorded_at_utc,
        )
        session.add(revision)
        session.flush()
        session.add(
            ClaimEvidenceLink(
                claim_revision_id=revision.id,
                evidence_id=evidence.id,
                relation=relation,
                recorded_at_utc=recorded_at_utc,
            )
        )
        session.flush()
        return revision.id


def test_fixture_freezes_exact_handoff_and_cutoff_history(session_factory, built):
    current = query(session_factory, built.supported_research_id)
    historical = query(
        session_factory, built.supported_research_id, date(2026, 7, 12)
    )
    handoff = current["frozen_stage1_handoff"]
    assert handoff["candidate_pool"]["candidate_pool_revision_id"] == str(
        built.candidate_pool_revision_id
    )
    assert handoff["beneficiary"]["assessment_status"] == "supported"
    assert handoff["company_snapshot"]["provider"] == "fixture"
    assert handoff["map_assertions"]
    assert handoff["frozen_claims"][0]["evidence"][0]["evidence_grade"] in {
        "A",
        "B",
        "C",
    }
    assert current["latest_revision"]["revision_no"] == 3
    assert historical["latest_revision"]["revision_no"] == 2
    assert historical["hypotheses"][0]["latest_revision"]["revision_no"] == 1
    assert len(historical["latest_revision"]["后续验证清单"]) == 1


def test_draft_missing_evidence_is_explicit_and_json_safe(session_factory, built):
    payload = query(session_factory, built.draft_research_id)
    assert payload["latest_revision"]["conclusion_status"] == "insufficient_evidence"
    assert len(payload["missing_evidence"]) == 1
    assert payload["hypotheses"][0]["latest_revision"]["evidence_grade_counts"] == {
        "A": 0,
        "B": 0,
        "C": 0,
        "D": 0,
    }
    json.dumps(payload, allow_nan=False, sort_keys=True)


def test_list_is_scoped_deterministic_and_read_only(session_factory, built):
    with session_factory() as session:
        service = Stage2CompanyResearchQueryService(
            Stage2CompanyResearchRepository(session)
        )
        first = service.list_research(
            candidate_pool_revision_id=built.candidate_pool_revision_id
        ).to_dict()
        second = service.list_research(
            candidate_pool_revision_id=built.candidate_pool_revision_id
        ).to_dict()
    assert first == second
    assert [item["stock_code"] for item in first["company_research"]] == [
        "000001",
        "000002",
    ]
    assert first["notices"]["read_only"] is True
    assert first["notices"]["no_scores_weights_or_rankings"] is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("hypothesis_status", "scored"),
        ("direction", "bullish"),
        ("confidence", "certain"),
        ("mechanism", 123),
        ("basis", None),
    ],
)
def test_strict_hypothesis_fields_reject_and_rollback(
    session_factory, built, field, value
):
    before = stage2_counts(session_factory)
    with session_factory() as session:
        research = session.get(Stage2CompanyResearch, built.draft_research_id)
        assertion = session.scalar(
            select(Stage1BeneficiaryAssertionLink).where(
                Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                == research.beneficiary_revision_id
            )
        )
        claim = session.scalar(
            select(ClaimRevision)
            .join(Claim, Claim.id == ClaimRevision.claim_id)
            .where(Claim.case_id == research.case_id)
        )
    values = {
        "hypothesis_status": "draft",
        "mechanism": "Bounded mechanism.",
        "direction": "uncertain",
        "operating_metric": "throughput",
        "financial_statement_line": "revenue",
        "expected_lag_horizon": "unknown",
        "confidence": "low",
        "basis": "Evidence remains incomplete.",
    }
    values[field] = value
    with pytest.raises(EvidenceLedgerValidationError):
        Stage2CompanyResearchCommandService(session_factory).create_hypothesis(
            research.id,
            hypothesis_key=f"invalid-{field}",
            stage1_assertion_link_id=assertion.id,
            information_cutoff_date=date(2026, 7, 16),
            claim_revision_ids=(claim.id,),
            recorded_at_utc=utc(16),
            **values,
        )
    assert stage2_counts(session_factory) == before


def test_non_member_and_mismatched_membership_are_atomic(session_factory, built):
    before = stage2_counts(session_factory)
    with session_factory() as session:
        membership = session.scalar(select(Stage1CandidatePoolMembership))
        other_revision = Stage1CandidatePoolRevision(
            candidate_pool_id=built.candidate_pool_id,
            revision_no=99,
            selected_map_revision_id=session.get(
                Stage1CandidatePoolRevision, built.candidate_pool_revision_id
            ).selected_map_revision_id,
            title="Mismatch probe",
            scope="Test-only mismatch.",
            information_cutoff_date=date(2026, 7, 16),
            recorded_at_utc=utc(16),
            supersedes_revision_id=built.candidate_pool_revision_id,
        )
        session.add(other_revision)
        session.commit()
        other_id = other_revision.id
    with pytest.raises(EvidenceLedgerValidationError):
        Stage2CompanyResearchCommandService(session_factory).create_company_research(
            other_id,
            membership.id,
            workflow_state="open",
            conclusion_status="unassessed",
            research_question="Should fail exact membership validation?",
            summary=None,
            information_cutoff_date=date(2026, 7, 16),
            recorded_at_utc=utc(16),
        )
    counts = stage2_counts(session_factory)
    assert counts[0] == before[0]


def test_completed_revision_requires_hypothesis_and_checklist(session_factory, built):
    before = stage2_counts(session_factory)
    with pytest.raises(EvidenceLedgerValidationError, match="accepted hypothesis"):
        Stage2CompanyResearchCommandService(session_factory).append_research_revision(
            built.draft_research_id,
            workflow_state="completed",
            conclusion_status="insufficient_evidence",
            research_question="Can this be completed without a hypothesis?",
            summary="No.",
            information_cutoff_date=date(2026, 7, 16),
            recorded_at_utc=utc(16),
        )
    assert stage2_counts(session_factory) == before


def test_completed_revision_rejects_missing_checklist(session_factory, built):
    revision, _claims = hypothesis_inputs(
        session_factory, built.supported_hypothesis_id, revision_no=2
    )
    with pytest.raises(EvidenceLedgerValidationError, match="后续验证清单"):
        Stage2CompanyResearchCommandService(session_factory).append_research_revision(
            built.supported_research_id,
            workflow_state="completed",
            conclusion_status="supported",
            research_question="Missing checklist should fail?",
            summary=None,
            information_cutoff_date=date(2026, 7, 16),
            hypothesis_revision_ids=(revision.id,),
            recorded_at_utc=utc(16),
        )


def test_later_verification_items_are_current_visible_without_cutoff_leakage(
    session_factory, built
):
    with session_factory() as session:
        latest_revision = session.scalar(
            select(Stage2CompanyResearchRevision)
            .where(
                Stage2CompanyResearchRevision.company_research_id
                == built.supported_research_id
            )
            .order_by(Stage2CompanyResearchRevision.revision_no.desc())
        )
    Stage2CompanyResearchCommandService(session_factory).add_verification_item(
        latest_revision.id,
        description="Later append-only checklist item visible only after its own timestamp.",
        status="open",
        recorded_at_utc=utc(16),
    )
    current = query(session_factory, built.supported_research_id)
    historical = query(
        session_factory, built.supported_research_id, date(2026, 7, 15)
    )
    current_items = current["latest_revision"]["后续验证清单"]
    historical_items = historical["latest_revision"]["后续验证清单"]
    assert [item["item_no"] for item in current_items] == [1, 2]
    assert current_items[1]["description"].startswith("Later append-only")
    assert [item["item_no"] for item in historical_items] == [1]
    assert current_items[1]["recorded_at_utc"] > current_items[0]["recorded_at_utc"]
    json.dumps(current, allow_nan=False, sort_keys=True)


def test_d_only_claim_cannot_support_hypothesis(session_factory, built):
    with session_factory() as session:
        research = session.get(Stage2CompanyResearch, built.supported_research_id)
        assertion = session.scalar(
            select(Stage1BeneficiaryAssertionLink).where(
                Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                == research.beneficiary_revision_id
            )
        )
        d_claim = session.scalar(
            select(ClaimRevision)
            .join(Claim, Claim.id == ClaimRevision.claim_id)
            .where(Claim.claim_key == "stage1-fixture-draft")
        )
    with pytest.raises(EvidenceLedgerValidationError, match="A/B/C"):
        Stage2CompanyResearchCommandService(session_factory).create_hypothesis(
            research.id,
            hypothesis_key="d-only-invalid",
            stage1_assertion_link_id=assertion.id,
            hypothesis_status="supported",
            mechanism="D-only mechanism must not be promoted.",
            direction="positive",
            operating_metric="units",
            financial_statement_line="revenue",
            expected_lag_horizon="unknown",
            confidence="low",
            basis="Only D-grade context exists.",
            information_cutoff_date=date(2026, 7, 16),
            claim_revision_ids=(d_claim.id,),
            recorded_at_utc=utc(16),
        )


@pytest.mark.parametrize("claim_status", ["draft", "disputed", "rejected"])
def test_supported_hypothesis_requires_supported_abc_claim_revision(
    session_factory, built, claim_status
):
    before = stage2_counts(session_factory)
    with session_factory() as session:
        research = session.get(Stage2CompanyResearch, built.supported_research_id)
        assertion = session.scalar(
            select(Stage1BeneficiaryAssertionLink).where(
                Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                == research.beneficiary_revision_id
            )
        )
        case_id = research.case_id
    claim_revision_id = add_stage2_test_claim(
        session_factory,
        case_id,
        claim_key=f"stage2-{claim_status}-abc-support",
        claim_status=claim_status,
    )
    with pytest.raises(
        EvidenceLedgerValidationError, match="supported A/B/C-backed claim"
    ):
        Stage2CompanyResearchCommandService(session_factory).create_hypothesis(
            research.id,
            hypothesis_key=f"{claim_status}-abc-invalid",
            stage1_assertion_link_id=assertion.id,
            hypothesis_status="supported",
            mechanism="A claim without supported status must not support Stage 2.",
            direction="positive",
            operating_metric="units",
            financial_statement_line="revenue",
            expected_lag_horizon="unknown",
            confidence="low",
            basis="The evidence is A-grade but the claim revision is not supported.",
            information_cutoff_date=date(2026, 7, 16),
            claim_revision_ids=(claim_revision_id,),
            recorded_at_utc=utc(16),
        )
    assert stage2_counts(session_factory) == before


def test_supported_hypothesis_accepts_supported_abc_claim_revision(
    session_factory, built
):
    with session_factory() as session:
        research = session.get(Stage2CompanyResearch, built.supported_research_id)
        assertion = session.scalar(
            select(Stage1BeneficiaryAssertionLink).where(
                Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                == research.beneficiary_revision_id
            )
        )
        case_id = research.case_id
    claim_revision_id = add_stage2_test_claim(
        session_factory,
        case_id,
        claim_key="stage2-supported-abc-support",
        claim_status="supported",
    )
    hypothesis = Stage2CompanyResearchCommandService(session_factory).create_hypothesis(
        research.id,
        hypothesis_key="supported-abc-valid",
        stage1_assertion_link_id=assertion.id,
        hypothesis_status="supported",
        mechanism="A supported A-backed claim may support a bounded hypothesis.",
        direction="positive",
        operating_metric="units",
        financial_statement_line="revenue",
        expected_lag_horizon="unknown",
        confidence="low",
        basis="The bound claim revision is supported and has A-grade support.",
        information_cutoff_date=date(2026, 7, 16),
        claim_revision_ids=(claim_revision_id,),
        recorded_at_utc=utc(16),
    )
    payload = query(session_factory, research.id)
    matched = [
        item
        for item in payload["hypotheses"]
        if item["hypothesis_id"] == str(hypothesis.id)
    ]
    assert matched[0]["latest_revision"]["hypothesis_status"] == "supported"
    json.dumps(payload, allow_nan=False, sort_keys=True)


def test_disputed_requires_conflict_or_disputed_claim(session_factory, built):
    revision, claims = hypothesis_inputs(
        session_factory, built.supported_hypothesis_id, revision_no=2
    )
    with pytest.raises(EvidenceLedgerValidationError, match="disputed claim"):
        Stage2CompanyResearchCommandService(session_factory).append_hypothesis_revision(
            built.supported_hypothesis_id,
            hypothesis_status="disputed",
            mechanism=revision.mechanism,
            direction="mixed",
            operating_metric=revision.operating_metric,
            financial_statement_line=revision.financial_statement_line,
            expected_lag_horizon=revision.expected_lag_horizon,
            confidence="low",
            basis="No actual contradiction exists.",
            information_cutoff_date=date(2026, 7, 16),
            claim_revision_ids=claims,
            recorded_at_utc=utc(16),
        )


def test_backdating_research_and_hypothesis_revisions_is_rejected(
    session_factory, built
):
    revision, claims = hypothesis_inputs(
        session_factory, built.draft_hypothesis_id
    )
    Stage2CompanyResearchCommandService(session_factory).append_hypothesis_revision(
        built.draft_hypothesis_id,
        hypothesis_status="draft",
        mechanism=revision.mechanism,
        direction=revision.direction,
        operating_metric=revision.operating_metric,
        financial_statement_line=revision.financial_statement_line,
        expected_lag_horizon=revision.expected_lag_horizon,
        confidence=revision.confidence,
        basis=revision.basis,
        information_cutoff_date=date(2026, 7, 12),
        claim_revision_ids=claims,
        recorded_at_utc=utc(12),
    )
    with pytest.raises(EvidenceLedgerValidationError, match="previous hypothesis"):
        Stage2CompanyResearchCommandService(session_factory).append_hypothesis_revision(
            built.draft_hypothesis_id,
            hypothesis_status="draft",
            mechanism=revision.mechanism,
            direction=revision.direction,
            operating_metric=revision.operating_metric,
            financial_statement_line=revision.financial_statement_line,
            expected_lag_horizon=revision.expected_lag_horizon,
            confidence=revision.confidence,
            basis=revision.basis,
            information_cutoff_date=date(2026, 7, 11),
            claim_revision_ids=claims,
            recorded_at_utc=utc(11, 12),
        )
    revision, claims = hypothesis_inputs(
        session_factory, built.supported_hypothesis_id, revision_no=2
    )
    with pytest.raises(
        EvidenceLedgerValidationError, match="latest company-research revision"
    ):
        Stage2CompanyResearchCommandService(session_factory).append_hypothesis_revision(
            built.supported_hypothesis_id,
            hypothesis_status="supported",
            mechanism=revision.mechanism,
            direction=revision.direction,
            operating_metric=revision.operating_metric,
            financial_statement_line=revision.financial_statement_line,
            expected_lag_horizon=revision.expected_lag_horizon,
            confidence=revision.confidence,
            basis=revision.basis,
            information_cutoff_date=date(2026, 7, 14),
            claim_revision_ids=claims,
            recorded_at_utc=utc(14, 11),
        )


def test_frozen_evidence_boundary_does_not_follow_later_links(session_factory, built):
    before = query(session_factory, built.draft_research_id)
    assert before["missing_evidence"]
    with session_factory() as session:
        count = session.scalar(select(func.count()).select_from(Stage2HypothesisEvidenceLink))
    after = query(session_factory, built.draft_research_id)
    assert after == before
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Stage2HypothesisEvidenceLink)) == count


def test_frozen_handoff_claim_set_does_not_follow_later_stage1_links(
    session_factory, built
):
    before = query(session_factory, built.supported_research_id)
    with session_factory.begin() as session:
        research = session.get(Stage2CompanyResearch, built.supported_research_id)
        later_claim = session.scalar(
            select(ClaimRevision)
            .join(Claim, Claim.id == ClaimRevision.claim_id)
            .where(Claim.claim_key == "stage2-fixture-unverified-transmission")
        )
        session.add(
            Stage1BeneficiaryClaimLink(
                beneficiary_revision_id=research.beneficiary_revision_id,
                claim_revision_id=later_claim.id,
                recorded_at_utc=utc(16),
            )
        )
    after = query(session_factory, built.supported_research_id)
    assert after["frozen_stage1_handoff"] == before["frozen_stage1_handoff"]


def test_handoff_evidence_freezes_at_beneficiary_revision_boundary(session_factory):
    stage1 = build_stage1_beneficiary_fixture(session_factory)
    with session_factory() as session:
        pool_revision = session.scalar(
            select(Stage1CandidatePoolRevision).where(
                Stage1CandidatePoolRevision.candidate_pool_id
                == stage1.candidate_pool_id
            )
        )
        membership = session.scalar(
            select(Stage1CandidatePoolMembership)
            .join(
                Stage1Beneficiary,
                Stage1Beneficiary.id
                == Stage1CandidatePoolMembership.beneficiary_id,
            )
            .where(
                Stage1CandidatePoolMembership.candidate_pool_revision_id
                == pool_revision.id,
                Stage1Beneficiary.stock_code == "000002",
            )
            .order_by(Stage1CandidatePoolMembership.recorded_at_utc)
        )
        claim_revision_id = session.scalar(
            select(Stage1BeneficiaryClaimLink.claim_revision_id).where(
                Stage1BeneficiaryClaimLink.beneficiary_revision_id
                == membership.beneficiary_revision_id
            )
        )
        case_id = session.get(Stage1CandidatePool, stage1.candidate_pool_id).case_id

    ledger = EvidenceLedgerCommandService(session_factory)
    late_evidence = ledger.add_evidence(
        case_id,
        evidence_grade="A",
        source_kind="official",
        source_title="Late Stage 1 evidence after beneficiary freeze",
        information_date=date(2026, 7, 6),
        summary="This evidence is visible by Stage 2 creation but not by the beneficiary revision.",
        content_fingerprint="stage2-late-handoff-evidence",
        recorded_at_utc=utc(9),
    )
    ledger.link_evidence(
        claim_revision_id,
        late_evidence.id,
        relation="supports",
        recorded_at_utc=utc(9, 11),
    )
    research = Stage2CompanyResearchCommandService(
        session_factory
    ).create_company_research(
        pool_revision.id,
        membership.id,
        workflow_state="open",
        conclusion_status="unassessed",
        research_question="Does a later Stage 1 evidence link leak into the handoff?",
        summary=None,
        information_cutoff_date=date(2026, 7, 10),
        recorded_at_utc=utc(10),
    )
    handoff = query(session_factory, research.id)["frozen_stage1_handoff"]
    titles = [
        evidence["source_title"]
        for claim in handoff["frozen_claims"]
        for evidence in claim["evidence"]
    ]
    assert "Late Stage 1 evidence after beneficiary freeze" not in titles
    json.dumps(handoff, allow_nan=False, sort_keys=True)


def test_frozen_handoff_assertion_set_does_not_follow_later_stage1_links(
    session_factory, built
):
    before = query(session_factory, built.supported_research_id)
    with session_factory.begin() as session:
        research = session.get(Stage2CompanyResearch, built.supported_research_id)
        linked_ids = {
            item
            for item in session.scalars(
                select(Stage1BeneficiaryAssertionLink.relationship_revision_id).where(
                    Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                    == research.beneficiary_revision_id
                )
            )
            if item is not None
        }
        relationship_revision_id = session.scalar(
            select(IndustryMapRelationshipRevision.id).where(
                IndustryMapRelationshipRevision.id.not_in(linked_ids)
            )
        )
        late_link = Stage1BeneficiaryAssertionLink(
            beneficiary_revision_id=research.beneficiary_revision_id,
            relationship_revision_id=relationship_revision_id,
            recorded_at_utc=utc(16),
        )
        session.add(late_link)
        session.flush()
        late_link_id = late_link.id
    after = query(session_factory, built.supported_research_id)
    assert after["frozen_stage1_handoff"] == before["frozen_stage1_handoff"]

    revision, claims = hypothesis_inputs(
        session_factory, built.supported_hypothesis_id
    )
    with pytest.raises(EvidenceLedgerValidationError, match="frozen"):
        Stage2CompanyResearchCommandService(session_factory).create_hypothesis(
            built.supported_research_id,
            hypothesis_key="late-stage1-assertion",
            stage1_assertion_link_id=late_link_id,
            hypothesis_status="draft",
            mechanism=revision.mechanism,
            direction=revision.direction,
            operating_metric=revision.operating_metric,
            financial_statement_line=revision.financial_statement_line,
            expected_lag_horizon=revision.expected_lag_horizon,
            confidence=revision.confidence,
            basis=revision.basis,
            information_cutoff_date=date(2026, 7, 16),
            claim_revision_ids=claims,
            recorded_at_utc=utc(16),
        )


def test_supported_research_conclusion_requires_supported_hypothesis(
    session_factory, built
):
    with pytest.raises(EvidenceLedgerValidationError, match="supported conclusion"):
        Stage2CompanyResearchCommandService(session_factory).append_research_revision(
            built.draft_research_id,
            workflow_state="open",
            conclusion_status="supported",
            research_question="Can support be declared without a supported hypothesis?",
            summary=None,
            information_cutoff_date=date(2026, 7, 16),
            recorded_at_utc=utc(16),
        )


@pytest.mark.parametrize("model", STAGE2_MODELS)
def test_all_stage2_rows_are_append_only(session_factory, built, model):
    with session_factory() as session:
        row = session.scalar(select(model))
        if row is None:
            pytest.skip(f"fixture has no {model.__name__} row")
        session.delete(row)
        with pytest.raises(EvidenceLedgerImmutableError):
            session.flush()


def test_api_is_read_only_strict_json_and_deterministic(session_factory, built):
    app.dependency_overrides[get_industry_alpha_session_factory] = lambda: session_factory
    try:
        with TestClient(app) as client:
            detail = client.get(
                f"/industry-alpha/company-research/{built.supported_research_id}"
            )
            listing = client.get(
                "/industry-alpha/company-research",
                params={"candidate_pool_revision_id": str(built.candidate_pool_revision_id)},
            )
            assert detail.status_code == listing.status_code == 200
            assert detail.json() == client.get(detail.request.url).json()
            json.dumps(detail.json(), allow_nan=False)
            for method in (client.post, client.put, client.patch, client.delete):
                assert method(
                    f"/industry-alpha/company-research/{built.supported_research_id}"
                ).status_code == 405
    finally:
        app.dependency_overrides.clear()


def test_database_configuration_error_is_generic(monkeypatch):
    def fail_engine(*_args, **_kwargs):
        raise RuntimeError("postgresql://user:secret@private/path")

    monkeypatch.setattr("backend.api.industry_alpha.build_engine", fail_engine)
    with TestClient(app) as client:
        response = client.get("/industry-alpha/company-research")
    assert response.status_code == 503
    body = response.text
    assert "secret" not in body
    assert "private" not in body
    assert "configuration is unavailable" in body


def test_stage2_import_fixture_demo_and_api_startup_do_not_use_network(
    monkeypatch, session_factory
):
    def reject_network(*_args, **_kwargs):
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    fixture = build_stage2_company_research_fixture(session_factory)
    assert query(session_factory, fixture.supported_research_id)["notices"]["research_only"]


def test_version_and_existing_routes_remain_compatible(session_factory, built):
    app.dependency_overrides[get_industry_alpha_session_factory] = lambda: session_factory
    try:
        with TestClient(app) as client:
            assert client.get("/").json()["version"] == "0.2.0"
            assert client.get("/health").status_code == 200
            assert client.get("/dashboard/overview").status_code == 200
            assert client.get(
                f"/industry-alpha/candidate-pools/{built.candidate_pool_id}"
            ).status_code == 200
    finally:
        app.dependency_overrides.clear()
