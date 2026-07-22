from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import json
from uuid import UUID

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.database.canonical_price_models import (
    CanonicalPrice,
    CanonicalPriceRevision,
    CanonicalPriceSeries,
    CanonicalPriceSeriesRevision,
    ComparisonEligibilityAssessment,
    ComparisonEligibilityMember,
    ComparisonEligibilityRevision,
    ListedInstrument,
    ListedInstrumentRevision,
)
from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.investment_candidate_commands import InvestmentCandidateCommandService
from industry_alpha.investment_candidate_models import (
    COMPONENT_CODES,
    InvestmentCandidateComponentAssessment,
    InvestmentCandidateComponentInputLink,
    InvestmentCandidateComponentRevision,
    InvestmentCandidateSnapshotRevision,
)
from industry_alpha.investment_candidate_query import InvestmentCandidateQueryService
from industry_alpha.investment_candidate_rules import (
    InvestmentCandidateError,
    PRICE_PURPOSE_CODE,
    PURPOSE_CODE,
    RULE_VERSION,
)
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryRevision,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)
from industry_alpha.stage2_expectations_fixtures import (
    build_stage2_expectation_valuation_fixture,
)
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
    Stage2HandoffClaimLink,
    Stage2HandoffEvidenceLink,
)

UTC = timezone.utc
CUTOFF = date(2026, 7, 22)
RECORDED = datetime(2026, 7, 22, 18, tzinfo=UTC)


@pytest.fixture()
def database():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    try:
        yield factory
    finally:
        engine.dispose()


def _latest_research_revision(session: Session, research_id: UUID) -> Stage2CompanyResearchRevision:
    return session.scalars(
        select(Stage2CompanyResearchRevision)
        .where(Stage2CompanyResearchRevision.company_research_id == research_id)
        .order_by(Stage2CompanyResearchRevision.revision_no.desc())
    ).first()


def _add_third_membership(session: Session, pool_revision: Stage1CandidatePoolRevision) -> None:
    existing = {
        row.beneficiary_id
        for row in session.scalars(
            select(Stage1CandidatePoolMembership).where(
                Stage1CandidatePoolMembership.candidate_pool_revision_id == pool_revision.id
            )
        )
    }
    beneficiary = session.scalar(
        select(Stage1Beneficiary)
        .where(Stage1Beneficiary.id.not_in(existing))
        .order_by(Stage1Beneficiary.stock_code)
    )
    revision = session.scalars(
        select(Stage1BeneficiaryRevision)
        .where(Stage1BeneficiaryRevision.beneficiary_id == beneficiary.id)
        .order_by(Stage1BeneficiaryRevision.revision_no.desc())
    ).first()
    session.add(
        Stage1CandidatePoolMembership(
            candidate_pool_revision_id=pool_revision.id,
            beneficiary_id=beneficiary.id,
            beneficiary_revision_id=revision.id,
            recorded_at_utc=RECORDED,
        )
    )


def _canonical_pair(session: Session, *, key: str, source_daily_price_id: int, source_run_id: int):
    instrument = ListedInstrument(instrument_key=f"fixture-{key}", created_at_utc=RECORDED)
    session.add(instrument)
    session.flush()
    instrument_revision = ListedInstrumentRevision(
        instrument_id=instrument.id,
        revision_no=1,
        canonical_symbol=key,
        security_type="common_equity",
        market_code="CN_A",
        exchange_code_namespace="ISO_MIC",
        exchange_code="XSHE",
        currency_code="CNY",
        listing_date=date(2020, 1, 1),
        delisting_date=None,
        listing_status="active",
        recorded_by="fixture",
        information_cutoff_date=CUTOFF,
        recorded_at_utc=RECORDED,
        supersedes_revision_id=None,
    )
    session.add(instrument_revision)
    session.flush()
    series = CanonicalPriceSeries(
        series_contract_key=f"fixture-{key}-series",
        instrument_id=instrument.id,
        created_at_utc=RECORDED,
    )
    session.add(series)
    session.flush()
    series_revision = CanonicalPriceSeriesRevision(
        series_id=series.id,
        revision_no=1,
        instrument_revision_id=instrument_revision.id,
        provider="fixture",
        dataset="daily_price",
        series_key=f"fixture-{key}-series-key",
        source_stock_code=key,
        source_adjust_type="",
        price_kind="official_close",
        adjustment_basis="unadjusted",
        unit_code="currency_per_share",
        currency_code="CNY",
        decimal_scale=2,
        decimal_rule_code="float_repr_decimal_v1",
        rounding_mode="ROUND_HALF_EVEN",
        status="accepted",
        recorded_by="fixture",
        information_cutoff_date=CUTOFF,
        recorded_at_utc=RECORDED,
        supersedes_revision_id=None,
    )
    session.add(series_revision)
    session.flush()
    price = CanonicalPrice(
        series_id=series.id,
        trade_date=CUTOFF,
        price_kind="official_close",
        adjustment_basis="unadjusted",
        created_at_utc=RECORDED,
    )
    session.add(price)
    session.flush()
    price_revision = CanonicalPriceRevision(
        canonical_price_id=price.id,
        revision_no=1,
        series_revision_id=series_revision.id,
        instrument_revision_id=instrument_revision.id,
        source_daily_price_id=source_daily_price_id,
        source_ingestion_run_id=source_run_id,
        source_value_text="10.2",
        standardized_value_text="10.20",
        value_decimal=Decimal("10.20"),
        numeric_fidelity="binary_float_normalized",
        currency_code="CNY",
        unit_code="currency_per_share",
        trade_date=CUTOFF,
        canonical_status="accepted",
        conflict_summary=None,
        recorded_by="fixture",
        information_cutoff_date=CUTOFF,
        recorded_at_utc=RECORDED,
        supersedes_revision_id=None,
    )
    session.add(price_revision)
    session.flush()
    assessment = ComparisonEligibilityAssessment(
        assessment_key=f"fixture-{key}-eligibility",
        purpose_code=PRICE_PURPOSE_CODE,
        created_at_utc=RECORDED,
    )
    session.add(assessment)
    session.flush()
    eligibility = ComparisonEligibilityRevision(
        assessment_id=assessment.id,
        revision_no=1,
        rule_version="aquantai.company-research-price-context-eligibility.v1",
        state="eligible",
        reason_codes=["canonical_price_accepted"],
        requested_trade_date=CUTOFF,
        recorded_by="fixture",
        information_cutoff_date=CUTOFF,
        recorded_at_utc=RECORDED,
        supersedes_revision_id=None,
    )
    session.add(eligibility)
    session.flush()
    session.add(
        ComparisonEligibilityMember(
            eligibility_revision_id=eligibility.id,
            position=0,
            canonical_price_revision_id=price_revision.id,
            recorded_at_utc=RECORDED,
        )
    )
    return price_revision.id, eligibility.id


def _component_graph(
    session: Session,
    *,
    research: Stage2CompanyResearch,
    research_revision: Stage2CompanyResearchRevision,
    scores: dict[str, Decimal],
    price_revision_id: UUID,
    eligibility_revision_id: UUID,
) -> dict[str, UUID]:
    claim = session.scalar(
        select(Stage2HandoffClaimLink).where(
            Stage2HandoffClaimLink.company_research_id == research.id
        )
    )
    evidence = session.scalar(
        select(Stage2HandoffEvidenceLink).where(
            Stage2HandoffEvidenceLink.company_research_id == research.id,
            Stage2HandoffEvidenceLink.claim_revision_id == claim.claim_revision_id,
        )
    )
    revisions: dict[str, UUID] = {}
    for code in COMPONENT_CODES:
        assessment = InvestmentCandidateComponentAssessment(
            beneficiary_id=research.beneficiary_id,
            component_code=code,
            assessment_key=f"fixture-{research.stock_code}-{code}",
            created_at_utc=RECORDED,
        )
        session.add(assessment)
        session.flush()
        revision = InvestmentCandidateComponentRevision(
            component_assessment_id=assessment.id,
            revision_no=1,
            beneficiary_revision_id=research.beneficiary_revision_id,
            company_research_revision_id=research_revision.id,
            assessment_state="supported",
            verification_state="verified",
            verification_material=False,
            verification_item_code=None,
            verification_question=None,
            source_score_text=format(scores[code], ".2f"),
            score_value=scores[code],
            missing_reason=None,
            rationale=f"Deterministic fixture rationale for {code}.",
            falsification_condition=f"Deterministic fixture falsification for {code}.",
            falsification_state="inactive",
            information_cutoff_date=CUTOFF,
            recorded_at_utc=RECORDED,
            recorded_by="fixture",
            supersedes_revision_id=None,
        )
        session.add(revision)
        session.flush()
        revisions[code] = revision.id
        if code in {"industry_opportunity", "evidence_quality"}:
            session.add_all(
                [
                    InvestmentCandidateComponentInputLink(
                        component_revision_id=revision.id,
                        position=0,
                        claim_revision_id=claim.claim_revision_id,
                        recorded_at_utc=RECORDED,
                    ),
                    InvestmentCandidateComponentInputLink(
                        component_revision_id=revision.id,
                        position=1,
                        evidence_id=evidence.evidence_id,
                        recorded_at_utc=RECORDED,
                    ),
                ]
            )
        if code == "valuation_context":
            session.add_all(
                [
                    InvestmentCandidateComponentInputLink(
                        component_revision_id=revision.id,
                        position=0,
                        canonical_price_revision_id=price_revision_id,
                        recorded_at_utc=RECORDED,
                    ),
                    InvestmentCandidateComponentInputLink(
                        component_revision_id=revision.id,
                        position=1,
                        comparison_eligibility_revision_id=eligibility_revision_id,
                        recorded_at_utc=RECORDED,
                    ),
                ]
            )
    return revisions


def _seed_three_member_graph(factory):
    fixture = build_stage2_expectation_valuation_fixture(factory)
    with factory.begin() as session:
        pool_revision = session.get(
            Stage1CandidatePoolRevision, fixture.stage2.candidate_pool_revision_id
        )
        _add_third_membership(session, pool_revision)
        session.flush()
        memberships = list(
            session.scalars(
                select(Stage1CandidatePoolMembership)
                .where(
                    Stage1CandidatePoolMembership.candidate_pool_revision_id
                    == pool_revision.id
                )
                .order_by(Stage1CandidatePoolMembership.id)
            )
        )
        research_by_membership = {
            row.candidate_pool_membership_id: row
            for row in session.scalars(
                select(Stage2CompanyResearch).where(
                    Stage2CompanyResearch.candidate_pool_revision_id == pool_revision.id
                )
            )
        }
        scored_memberships = [
            row for row in memberships if row.id in research_by_membership
        ]
        score_sets = [
            {
                "industry_opportunity": Decimal("92.00"),
                "beneficiary_strength": Decimal("90.00"),
                "earnings_conversion": Decimal("86.00"),
                "expectation_gap": Decimal("82.00"),
                "valuation_context": Decimal("70.00"),
                "catalyst_readiness": Decimal("80.00"),
                "evidence_quality": Decimal("90.00"),
                "risk_penalty": Decimal("20.00"),
            },
            {
                "industry_opportunity": Decimal("88.00"),
                "beneficiary_strength": Decimal("82.00"),
                "earnings_conversion": Decimal("78.00"),
                "expectation_gap": Decimal("35.00"),
                "valuation_context": Decimal("35.00"),
                "catalyst_readiness": Decimal("75.00"),
                "evidence_quality": Decimal("80.00"),
                "risk_penalty": Decimal("25.00"),
            },
        ]
        component_ids: dict[UUID, dict[str, UUID]] = {}
        price_pairs: dict[UUID, tuple[UUID, UUID]] = {}
        for membership, scores in zip(scored_memberships, score_sets, strict=True):
            research = research_by_membership[membership.id]
            research_revision = _latest_research_revision(session, research.id)
            price_pair = _canonical_pair(
                session,
                key=research.stock_code,
                source_daily_price_id=fixture.daily_price_id,
                source_run_id=fixture.ingestion_run_id,
            )
            price_pairs[membership.id] = price_pair
            component_ids[membership.id] = _component_graph(
                session,
                research=research,
                research_revision=research_revision,
                scores=scores,
                price_revision_id=price_pair[0],
                eligibility_revision_id=price_pair[1],
            )
        session.flush()
        members = []
        for membership in memberships:
            research = research_by_membership.get(membership.id)
            if research is None:
                members.append(
                    {
                        "candidate_pool_membership_id": str(membership.id),
                        "beneficiary_id": str(membership.beneficiary_id),
                        "beneficiary_revision_id": str(membership.beneficiary_revision_id),
                        "company_research_revision_id": None,
                        "typed_beneficiary_revision_id": None,
                        "canonical_price_revision_id": None,
                        "comparison_eligibility_revision_id": None,
                        "component_revision_ids": {},
                    }
                )
                continue
            research_revision = _latest_research_revision(session, research.id)
            price_pair = price_pairs[membership.id]
            members.append(
                {
                    "candidate_pool_membership_id": str(membership.id),
                    "beneficiary_id": str(membership.beneficiary_id),
                    "beneficiary_revision_id": str(membership.beneficiary_revision_id),
                    "company_research_revision_id": str(research_revision.id),
                    "typed_beneficiary_revision_id": None,
                    "canonical_price_revision_id": str(price_pair[0]),
                    "comparison_eligibility_revision_id": str(price_pair[1]),
                    "component_revision_ids": {
                        code: str(revision_id)
                        for code, revision_id in component_ids[membership.id].items()
                    },
                }
            )
        return fixture.stage2.candidate_pool_id, pool_revision.id, members


def _payload(pool_id: UUID, pool_revision_id: UUID, members: list[dict]) -> dict:
    return {
        "candidate_pool_id": str(pool_id),
        "candidate_pool_revision_id": str(pool_revision_id),
        "purpose_code": PURPOSE_CODE,
        "rule_version": RULE_VERSION,
        "snapshot_key": "fixture-three-member-golden-path",
        "expected_latest_revision_id": None,
        "information_cutoff_date": CUTOFF.isoformat(),
        "recorded_at_utc": RECORDED.isoformat(),
        "recorded_by": "fixture",
        "members": members,
    }


def test_three_member_offline_golden_path_and_exact_read(database):
    pool_id, pool_revision_id, members = _seed_three_member_graph(database)
    service = InvestmentCandidateCommandService(database)
    payload = _payload(pool_id, pool_revision_id, members)

    dry_run = service.record_snapshot(payload, dry_run=True)
    assert dry_run["dry_run"] is True
    assert dry_run["member_count"] == 3
    with database() as session:
        assert session.scalar(
            select(func.count()).select_from(InvestmentCandidateSnapshotRevision)
        ) == 0

    result = service.record_snapshot(payload)
    boundary = datetime(2026, 7, 22, 18, tzinfo=UTC)
    with database() as session:
        output = InvestmentCandidateQueryService(session).get_snapshot_revision(
            UUID(result["snapshot_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=boundary,
        )
    statuses = {row["candidate_status"] for row in output["members"]}
    assert statuses == {
        "priority_candidate",
        "pricing_demanding",
        "evidence_insufficient",
    }
    assert output["member_count"] == 3
    priority = next(
        row for row in output["members"] if row["candidate_status"] == "priority_candidate"
    )
    insufficient = next(
        row for row in output["members"] if row["candidate_status"] == "evidence_insufficient"
    )
    assert priority["priority_ordinal"] == 1
    assert insufficient["final_score"] is None
    assert len(insufficient["components"]) == 0
    json.dumps(output, allow_nan=False, sort_keys=True)


def test_universe_omission_rolls_back_before_snapshot_write(database):
    pool_id, pool_revision_id, members = _seed_three_member_graph(database)
    service = InvestmentCandidateCommandService(database)
    bad = _payload(pool_id, pool_revision_id, members[:-1])
    with pytest.raises(InvestmentCandidateError, match="set-equal"):
        service.record_snapshot(bad)
    with database() as session:
        assert session.scalar(
            select(func.count()).select_from(InvestmentCandidateSnapshotRevision)
        ) == 0
