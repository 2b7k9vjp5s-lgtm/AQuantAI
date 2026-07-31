from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from industry_alpha.beneficiary_semantics_models import (
    Stage1BeneficiarySemanticAssertion,
    Stage1BeneficiarySemanticProfile,
    Stage1BeneficiarySemanticProfileRevision,
)
from industry_alpha.industry_research_result_company import (
    ExplainedCompanyProjectionReader,
)
from industry_alpha.industry_research_result_query import (
    IndustryResearchResultQueryService,
)
from industry_alpha.investment_candidate_models import (
    InvestmentCandidateComponentAssessment,
    InvestmentCandidateComponentInputLink,
    InvestmentCandidateComponentRevision,
)
from industry_alpha.stage2_assessments_models import (
    Stage2CatalystAssessmentRevision,
)
from industry_alpha.stage2_expectations_models import (
    Stage2MarketExpectationRevision,
)
from industry_alpha.stage2_judgments_fixtures import build_stage2_judgment_fixture
from industry_alpha.stage2_models import Stage2CompanyResearch
from industry_alpha.stage2_assessments_fixtures import Stage2AssessmentFixtureIds
from scripts.demo_industry_research_result_assembly import (
    CUTOFF as RESULT_CUTOFF,
    seed_industry_research_result_demo,
)
from tests.test_industry_research_result_query import database

UTC = timezone.utc
EXPLAINED_CUTOFF = date(2026, 7, 16)
EXPLAINED_RECORDED = datetime(2026, 7, 16, 20, tzinfo=UTC)


def _component(
    session,
    *,
    beneficiary_id: UUID,
    beneficiary_revision_id: UUID,
    company_research_revision_id: UUID,
    code: str,
    targets: tuple[tuple[str, UUID], ...],
) -> UUID:
    assessment = InvestmentCandidateComponentAssessment(
        beneficiary_id=beneficiary_id,
        component_code=code,
        assessment_key=f"explained-result-{code}",
        created_at_utc=EXPLAINED_RECORDED,
    )
    session.add(assessment)
    session.flush()
    revision = InvestmentCandidateComponentRevision(
        component_assessment_id=assessment.id,
        revision_no=1,
        beneficiary_revision_id=beneficiary_revision_id,
        company_research_revision_id=company_research_revision_id,
        assessment_state="supported",
        verification_state="verified",
        verification_material=False,
        verification_item_code=None,
        verification_question=None,
        source_score_text="80.00",
        score_value=Decimal("80.00"),
        missing_reason=None,
        rationale=f"Exact persisted rationale for {code}.",
        falsification_condition=f"Exact persisted falsification for {code}.",
        falsification_state="inactive",
        information_cutoff_date=EXPLAINED_CUTOFF,
        recorded_at_utc=EXPLAINED_RECORDED,
        recorded_by="explained-result-test",
        supersedes_revision_id=None,
    )
    session.add(revision)
    session.flush()
    field_by_kind = {
        "financial_hypothesis": "financial_hypothesis_revision_id",
        "market_expectation": "market_expectation_revision_id",
        "valuation": "valuation_revision_id",
        "catalyst": "catalyst_revision_id",
        "risk": "risk_revision_id",
        "industry_judgment": "industry_judgment_revision_id",
        "company_judgment": "company_judgment_revision_id",
    }
    for position, (kind, target_id) in enumerate(targets):
        payload = {
            "component_revision_id": revision.id,
            "position": position,
            "recorded_at_utc": EXPLAINED_RECORDED,
            field_by_kind[kind]: target_id,
        }
        session.add(InvestmentCandidateComponentInputLink(**payload))
    return revision.id


def _seed_exact_explanation(database) -> dict:
    fixture = build_stage2_judgment_fixture(database)
    assessment_fixture: Stage2AssessmentFixtureIds = fixture.v06c
    with database.begin() as session:
        research = session.get(
            Stage2CompanyResearch,
            assessment_fixture.v06b.stage2.supported_research_id,
        )
        catalyst = session.get(
            Stage2CatalystAssessmentRevision,
            assessment_fixture.supported_catalyst_revision_id,
        )
        company_research_revision_id = catalyst.company_research_revision_id
        hypothesis_revision_id = session.scalar(
            select(
                __import__(
                    "industry_alpha.stage2_assessments_models",
                    fromlist=["Stage2CatalystHypothesisLink"],
                ).Stage2CatalystHypothesisLink.hypothesis_revision_id
            ).where(
                __import__(
                    "industry_alpha.stage2_assessments_models",
                    fromlist=["Stage2CatalystHypothesisLink"],
                ).Stage2CatalystHypothesisLink.catalyst_revision_id
                == catalyst.id
            )
        )

        profile = Stage1BeneficiarySemanticProfile(
            beneficiary_id=research.beneficiary_id,
            created_at_utc=EXPLAINED_RECORDED,
        )
        session.add(profile)
        session.flush()
        semantic_revision = Stage1BeneficiarySemanticProfileRevision(
            profile_id=profile.id,
            revision_no=1,
            beneficiary_revision_id=research.beneficiary_revision_id,
            selected_map_revision_id=research.selected_map_revision_id,
            taxonomy_version="aquantai.typed-beneficiary-evidence-semantics.v1",
            overall_status="supported",
            summary="Exact accepted semantic profile for explained-result tests.",
            recorded_by="explained-result-test",
            information_cutoff_date=EXPLAINED_CUTOFF,
            recorded_at_utc=EXPLAINED_RECORDED,
            supersedes_revision_id=None,
        )
        session.add(semantic_revision)
        session.flush()
        semantic_values = (
            ("offering", "产品A", "supported"),
            ("customer", "客户A", "supported"),
            ("certification", "认证A", "supported"),
            ("capacity", "产能A", "supported"),
            ("production", "投产A", "supported"),
            ("order", "订单A", "supported"),
        )
        for position, (field_kind, subject, evidence_state) in enumerate(
            semantic_values
        ):
            session.add(
                Stage1BeneficiarySemanticAssertion(
                    profile_revision_id=semantic_revision.id,
                    assertion_key=f"explained-{field_kind}",
                    field_kind=field_kind,
                    state_code=f"{field_kind}_confirmed",
                    evidence_state=evidence_state,
                    subject_text=subject,
                    rationale=f"Exact persisted {field_kind} rationale.",
                    map_observation_revision_id=None,
                    position=position,
                )
            )

        component_ids = {
            "earnings_conversion": _component(
                session,
                beneficiary_id=research.beneficiary_id,
                beneficiary_revision_id=research.beneficiary_revision_id,
                company_research_revision_id=company_research_revision_id,
                code="earnings_conversion",
                targets=(("financial_hypothesis", hypothesis_revision_id),),
            ),
            "expectation_gap": _component(
                session,
                beneficiary_id=research.beneficiary_id,
                beneficiary_revision_id=research.beneficiary_revision_id,
                company_research_revision_id=company_research_revision_id,
                code="expectation_gap",
                targets=(("market_expectation", assessment_fixture.v06b.expectation_revision_id),),
            ),
            "valuation_context": _component(
                session,
                beneficiary_id=research.beneficiary_id,
                beneficiary_revision_id=research.beneficiary_revision_id,
                company_research_revision_id=company_research_revision_id,
                code="valuation_context",
                targets=(("valuation", assessment_fixture.v06b.valuation_revision_id),),
            ),
            "catalyst_readiness": _component(
                session,
                beneficiary_id=research.beneficiary_id,
                beneficiary_revision_id=research.beneficiary_revision_id,
                company_research_revision_id=company_research_revision_id,
                code="catalyst_readiness",
                targets=(("catalyst", assessment_fixture.supported_catalyst_revision_id),),
            ),
            "risk_penalty": _component(
                session,
                beneficiary_id=research.beneficiary_id,
                beneficiary_revision_id=research.beneficiary_revision_id,
                company_research_revision_id=company_research_revision_id,
                code="risk_penalty",
                targets=(("risk", assessment_fixture.supported_risk_revision_id),),
            ),
            "industry_opportunity": _component(
                session,
                beneficiary_id=research.beneficiary_id,
                beneficiary_revision_id=research.beneficiary_revision_id,
                company_research_revision_id=company_research_revision_id,
                code="industry_opportunity",
                targets=(
                    ("industry_judgment", fixture.affirmed_industry_revision_id),
                    ("company_judgment", fixture.affirmed_company_revision_id),
                ),
            ),
        }
        later_expectation = session.scalars(
            select(Stage2MarketExpectationRevision)
            .where(
                Stage2MarketExpectationRevision.expectation_id
                == assessment_fixture.v06b.disputed_expectation_id
            )
            .order_by(Stage2MarketExpectationRevision.revision_no.desc())
        ).first()
        return {
            "beneficiary_id": research.beneficiary_id,
            "beneficiary_revision_id": research.beneficiary_revision_id,
            "semantic_revision_id": semantic_revision.id,
            "company_research_revision_id": company_research_revision_id,
            "components": component_ids,
            "later_risk_revision_id": assessment_fixture.later_risk_revision_id,
            "later_expectation_revision_id": later_expectation.id,
        }


def _member(seeded: dict) -> dict:
    return {
        "beneficiary_revision_id": str(seeded["beneficiary_revision_id"]),
        "semantic_profile_revision_id": str(seeded["semantic_revision_id"]),
        "candidate_overlay": {
            "beneficiary_id": str(seeded["beneficiary_id"]),
            "beneficiary_revision_id": str(seeded["beneficiary_revision_id"]),
            "company_research_revision_id": str(
                seeded["company_research_revision_id"]
            ),
            "typed_beneficiary_revision_id": str(seeded["semantic_revision_id"]),
            "canonical_price_revision_id": None,
            "comparison_eligibility_revision_id": None,
            "base_score": "80.00",
            "business_quality_score": "80.00",
            "risk_penalty_points": "10.00",
            "final_score": "70.00",
            "candidate_status": "watch_candidate",
            "priority_ordinal": 1,
            "reason_codes": ["exact_fixture_reason"],
            "components": [
                {
                    "component_code": code,
                    "component_revision_id": str(revision_id),
                }
                for code, revision_id in seeded["components"].items()
            ],
        },
    }


def test_exact_frozen_downstream_revisions_build_readable_explanation(database) -> None:
    seeded = _seed_exact_explanation(database)
    with database() as session:
        result = ExplainedCompanyProjectionReader(session).explain(
            [_member(seeded)],
            as_of_cutoff=EXPLAINED_CUTOFF,
            as_of_recorded_at_utc=EXPLAINED_RECORDED,
        )
    item = result["members"][0]
    assert item["overall_state"] == "selected_exact_overlay"
    assert item["company_research"]["revision_id"] == str(
        seeded["company_research_revision_id"]
    )
    assert {row["subject_text"] for row in item["product_and_chain"]} == {
        "产品A"
    }
    assert {
        row["field_kind"]
        for row in item["customer_certification_capacity_order"]
    } == {"customer", "certification", "capacity", "production", "order"}
    assert "shipped units" in item["earnings_transmission"][0]["operating_metric"]
    assert item["expectation"][0]["kind"] == "market_expectation"
    assert item["valuation"][0]["kind"] == "valuation"
    assert item["catalysts"][0]["kind"] == "catalyst"
    assert item["risks"][0]["kind"] == "risk"
    assert item["industry_judgments"][0]["outcome"] == "affirmed"
    assert item["company_judgments"][0]["outcome"] == "affirmed"
    assert item["candidate_explanation"]["candidate_status"] == "watch_candidate"
    assert item["missing_inputs"] == []
    assert result["creates_owner_state"] is False
    assert result["recomputes_candidate"] is False
    assert result["uses_latest_fallback"] is False
    assert result["external_network"] is False


def test_newer_downstream_records_are_not_selected_without_exact_frozen_link(database) -> None:
    seeded = _seed_exact_explanation(database)
    with database() as session:
        result = ExplainedCompanyProjectionReader(session).explain(
            [_member(seeded)],
            as_of_cutoff=date(2026, 7, 20),
            as_of_recorded_at_utc=datetime(2026, 7, 20, 20, tzinfo=UTC),
        )
    item = result["members"][0]
    assert item["risks"][0]["revision_id"] != str(seeded["later_risk_revision_id"])
    assert item["expectation"][0]["revision_id"] != str(
        seeded["later_expectation_revision_id"]
    )
    assert "Later" not in str(item)
    assert result["uses_latest_fallback"] is False


def test_exact_input_outside_boundary_is_unavailable_without_replacement(database) -> None:
    seeded = _seed_exact_explanation(database)
    risk_component_id = seeded["components"]["risk_penalty"]
    with database.begin() as session:
        session.add(
            InvestmentCandidateComponentInputLink(
                component_revision_id=risk_component_id,
                position=1,
                risk_revision_id=seeded["later_risk_revision_id"],
                recorded_at_utc=EXPLAINED_RECORDED,
            )
        )
    with database() as session:
        result = ExplainedCompanyProjectionReader(session).explain(
            [_member(seeded)],
            as_of_cutoff=EXPLAINED_CUTOFF,
            as_of_recorded_at_utc=EXPLAINED_RECORDED,
        )
    item = result["members"][0]
    assert "exact_input_not_visible:risk" in item["missing_inputs"]
    risk_component = next(
        row
        for row in item["candidate_explanation"]["components"]
        if row["component_code"] == "risk_penalty"
    )
    assert any(
        input_row["state"] == "unavailable"
        and input_row["reason"] == "exact_revision_not_visible"
        for input_row in risk_component["inputs"]
    )
    assert len(item["risks"]) == 1


def test_exact_input_company_research_mismatch_fails_affected_input_closed(database) -> None:
    seeded = _seed_exact_explanation(database)
    component_id = seeded["components"]["expectation_gap"]
    with database.begin() as session:
        session.add(
            InvestmentCandidateComponentInputLink(
                component_revision_id=component_id,
                position=1,
                market_expectation_revision_id=seeded[
                    "later_expectation_revision_id"
                ],
                recorded_at_utc=datetime(2026, 7, 20, 10, tzinfo=UTC),
            )
        )
    with database() as session:
        result = ExplainedCompanyProjectionReader(session).explain(
            [_member(seeded)],
            as_of_cutoff=date(2026, 7, 20),
            as_of_recorded_at_utc=datetime(2026, 7, 20, 20, tzinfo=UTC),
        )
    item = result["members"][0]
    assert "exact_input_company_research_mismatch:market_expectation" in item[
        "missing_inputs"
    ]
    assert len(item["expectation"]) == 1


def test_assembled_result_exposes_deterministic_explanation_contract_and_fingerprint(database) -> None:
    seeded = seed_industry_research_result_demo(database)
    with database() as session:
        service = IndustryResearchResultQueryService(session)
        first = service.get_assembled_result(
            UUID(seeded["output_link_revision_id"]),
            as_of_cutoff=RESULT_CUTOFF,
            as_of_recorded_at_utc=seeded["as_of_recorded_at_utc"],
        )
        second = service.get_assembled_result(
            UUID(seeded["output_link_revision_id"]),
            as_of_cutoff=RESULT_CUTOFF,
            as_of_recorded_at_utc=seeded["as_of_recorded_at_utc"],
        )
    assert first["explained_result"]["contract_version"] == (
        "aquantai.industry-research-explained-result.v1"
    )
    assert len(first["explained_result"]["content_sha256"]) == 64
    assert first["explained_result"] == second["explained_result"]
    assert first["explained_result"]["uses_latest_fallback"] is False
    assert first["explained_result"]["recomputes_candidate"] is False
    assert all(
        member["explained_research"] is not None
        for member in first["accepted_snapshot"]["members"]
    )
