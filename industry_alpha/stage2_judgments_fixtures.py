"""Deterministic offline fixture for v0.6D quality judgments."""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from threading import RLock
from typing import Iterator
from uuid import UUID, UUID as UUIDValue, uuid5

from sqlalchemy import event, select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.models import Base
from industry_alpha.stage2_assessments_fixtures import Stage2AssessmentFixtureIds, build_stage2_assessment_fixture
from industry_alpha.stage2_assessments_models import (
    Stage2CatalystAssessmentRevision, Stage2CatalystClaimLink,
    Stage2CatalystExpectationLink, Stage2CatalystHypothesisLink,
    Stage2CatalystValuationLink, Stage2RiskAssessmentRevision,
)
from industry_alpha.stage2_judgments_commands import Stage2JudgmentCommandService
from industry_alpha.stage2_judgments_models import Stage2CompanyJudgmentRevision, Stage2IndustryJudgmentRevision


FIXTURE_ID_NAMESPACE = UUIDValue("52feff38-3d22-5a25-a44e-5d0a723a551c")
_FIXTURE_ID_LOCK = RLock()


@dataclass(frozen=True)
class Stage2JudgmentFixtureIds:
    v06c: Stage2AssessmentFixtureIds
    affirmed_industry_id: UUID
    uncertain_industry_id: UUID
    affirmed_company_id: UUID
    uncertain_company_id: UUID
    affirmed_industry_revision_id: UUID
    affirmed_company_revision_id: UUID
    later_industry_revision_id: UUID
    later_company_revision_id: UUID


def _recorded(day: int, hour: int) -> datetime:
    return datetime(2026, 7, day, hour, tzinfo=timezone.utc)


def _boundary(session: Session, catalyst_revision_id: UUID, risk_revision_id: UUID) -> dict:
    catalyst = session.get(Stage2CatalystAssessmentRevision, catalyst_revision_id)
    risk = session.get(Stage2RiskAssessmentRevision, risk_revision_id)
    return {
        "company_research_revision_id": catalyst.company_research_revision_id,
        "hypothesis_revision_ids": tuple(session.scalars(select(Stage2CatalystHypothesisLink.hypothesis_revision_id).where(Stage2CatalystHypothesisLink.catalyst_revision_id == catalyst.id).order_by(Stage2CatalystHypothesisLink.hypothesis_revision_id))),
        "expectation_revision_ids": tuple(session.scalars(select(Stage2CatalystExpectationLink.expectation_revision_id).where(Stage2CatalystExpectationLink.catalyst_revision_id == catalyst.id).order_by(Stage2CatalystExpectationLink.expectation_revision_id))),
        "valuation_revision_ids": tuple(session.scalars(select(Stage2CatalystValuationLink.valuation_revision_id).where(Stage2CatalystValuationLink.catalyst_revision_id == catalyst.id).order_by(Stage2CatalystValuationLink.valuation_revision_id))),
        "claim_revision_ids": tuple(session.scalars(select(Stage2CatalystClaimLink.claim_revision_id).where(Stage2CatalystClaimLink.catalyst_revision_id == catalyst.id).order_by(Stage2CatalystClaimLink.claim_revision_id))),
        "catalyst_revision_ids": (catalyst.id,),
        "risk_revision_ids": (risk.id,),
    }


def _common(boundary: dict, *, outcome: str, evidence_state: str, confidence: str, cutoff: date, recorded: datetime) -> dict:
    return {
        **boundary,
        "outcome": outcome,
        "evidence_state": evidence_state,
        "confidence": confidence,
        "decision_criteria": "Use only the exact frozen research, expectation, valuation, catalyst, risk, claim, and evidence boundary.",
        "rationale": "The manual judgment is bounded by attributable frozen evidence and does not imply a recommendation.",
        "uncertainty": "Magnitude, timing, and investment implications remain outside this record.",
        "follow_up_verification": "后续验证清单：检查下一份可归因的一手披露是否改变当前证据边界。",
        "information_cutoff_date": cutoff,
        "recorded_at_utc": recorded,
    }


@contextmanager
def _deterministic_fixture_uuid_defaults() -> Iterator[None]:
    """Assign deterministic UUID PKs while this fixture is being inserted."""
    counters: Counter[str] = Counter()

    def assign_uuid(mapper, _connection, target) -> None:
        for column in mapper.primary_key:
            if column.type.python_type is UUID and getattr(target, column.key) is None:
                table_name = column.table.name
                counters[table_name] += 1
                setattr(
                    target,
                    column.key,
                    uuid5(FIXTURE_ID_NAMESPACE, f"{table_name}:{counters[table_name]}"),
                )

    with _FIXTURE_ID_LOCK:
        event.listen(Base, "before_insert", assign_uuid, propagate=True)
        try:
            yield
        finally:
            event.remove(Base, "before_insert", assign_uuid)


def build_stage2_judgment_fixture(session_factory: sessionmaker[Session]) -> Stage2JudgmentFixtureIds:
    with _deterministic_fixture_uuid_defaults():
        return _build_stage2_judgment_fixture(session_factory)


def _build_stage2_judgment_fixture(session_factory: sessionmaker[Session]) -> Stage2JudgmentFixtureIds:
    v06c = build_stage2_assessment_fixture(session_factory)
    with session_factory() as session:
        supported = _boundary(session, v06c.supported_catalyst_revision_id, v06c.supported_risk_revision_id)
        later = _boundary(session, v06c.later_catalyst_revision_id, v06c.later_risk_revision_id)
    research_id = v06c.v06b.stage2.supported_research_id
    commands = Stage2JudgmentCommandService(session_factory)
    affirmed_industry = commands.create_industry_judgment(
        research_id, judgment_key="fixture-industry-quality",
        **_common(supported, outcome="affirmed", evidence_state="supported", confidence="medium", cutoff=date(2026, 7, 16), recorded=_recorded(16, 16)),
        driver_durability="A bounded attributable mechanism supports durability at this cutoff.",
        value_pool_direction="The frozen chain evidence supports only a directional research observation.",
        chain_bottleneck_support="The exact Stage 1 map and beneficiary boundary remains traceable through v0.6A.",
    )
    affirmed_company = commands.create_company_judgment(
        research_id, judgment_key="fixture-company-quality",
        **_common(supported, outcome="affirmed", evidence_state="supported", confidence="medium", cutoff=date(2026, 7, 16), recorded=_recorded(16, 17)),
        beneficiary_credibility="The frozen beneficiary claim has attributable A/B/C support.",
        financial_transmission_credibility="The accepted hypothesis and expectation preserve a bounded transmission mechanism.",
        execution_risks="Execution remains uncertain and is explicitly preserved by the frozen risk assessment.",
    )
    uncertain_industry = commands.create_industry_judgment(
        research_id, judgment_key="fixture-industry-uncertain",
        **_common(later, outcome="uncertain", evidence_state="disputed", confidence="low", cutoff=date(2026, 7, 19), recorded=_recorded(19, 12)),
        driver_durability="Later contradictory evidence leaves durability uncertain.",
        value_pool_direction="No value-pool conclusion is inferred from disputed evidence.",
        chain_bottleneck_support="The frozen boundary preserves both support and contradiction.",
    )
    uncertain_company = commands.create_company_judgment(
        research_id, judgment_key="fixture-company-uncertain",
        **_common(later, outcome="uncertain", evidence_state="disputed", confidence="low", cutoff=date(2026, 7, 19), recorded=_recorded(19, 13)),
        beneficiary_credibility="Later evidence disputes the previously bounded beneficiary mechanism.",
        financial_transmission_credibility="Transmission remains unresolved at this cutoff.",
        execution_risks="Contradictory evidence is retained without an automatic adverse conclusion.",
    )
    later_industry = commands.append_industry_judgment_revision(
        affirmed_industry.id,
        **_common(later, outcome="uncertain", evidence_state="disputed", confidence="low", cutoff=date(2026, 7, 19), recorded=_recorded(19, 14)),
        driver_durability="Later evidence makes the durability judgment uncertain.",
        value_pool_direction="Later disputed evidence prevents affirmation.",
        chain_bottleneck_support="The earlier revision remains immutable and visible historically.",
    )
    later_company = commands.append_company_judgment_revision(
        affirmed_company.id,
        **_common(later, outcome="not_affirmed", evidence_state="disputed", confidence="low", cutoff=date(2026, 7, 19), recorded=_recorded(19, 15)),
        beneficiary_credibility="The manual judgment is not affirmed on the later disputed boundary.",
        financial_transmission_credibility="Contradiction prevents retaining the earlier affirmed judgment.",
        execution_risks="The exact disputed risk boundary is preserved without scoring.",
    )
    with session_factory() as session:
        industry_v1 = session.scalar(select(Stage2IndustryJudgmentRevision).where(Stage2IndustryJudgmentRevision.judgment_id == affirmed_industry.id, Stage2IndustryJudgmentRevision.revision_no == 1))
        company_v1 = session.scalar(select(Stage2CompanyJudgmentRevision).where(Stage2CompanyJudgmentRevision.judgment_id == affirmed_company.id, Stage2CompanyJudgmentRevision.revision_no == 1))
    return Stage2JudgmentFixtureIds(v06c, affirmed_industry.id, uncertain_industry.id, affirmed_company.id, uncertain_company.id, industry_v1.id, company_v1.id, later_industry.id, later_company.id)


def build_stage2_judgment_fixture_payload(
    session_factory: sessionmaker[Session], fixture: Stage2JudgmentFixtureIds
) -> dict:
    """Return the complete canonical list/detail payload for repeatability checks."""
    from industry_alpha.stage2_judgments_query import (
        Stage2CompanyJudgmentQueryService,
        Stage2IndustryJudgmentQueryService,
    )
    from industry_alpha.stage2_judgments_repository import Stage2JudgmentRepository

    with session_factory() as session:
        repository = Stage2JudgmentRepository(session)
        industry = Stage2IndustryJudgmentQueryService(repository)
        company = Stage2CompanyJudgmentQueryService(repository)
        return {
            "industry_list": industry.list_judgments().to_dict(),
            "company_list": company.list_judgments().to_dict(),
            "industry_details": tuple(
                industry.get_judgment(item).to_dict()
                for item in sorted(
                    (fixture.affirmed_industry_id, fixture.uncertain_industry_id), key=str
                )
            ),
            "company_details": tuple(
                company.get_judgment(item).to_dict()
                for item in sorted(
                    (fixture.affirmed_company_id, fixture.uncertain_company_id), key=str
                )
            ),
            "historical": {
                "industry": industry.get_judgment(
                    fixture.affirmed_industry_id, as_of_cutoff=date(2026, 7, 16)
                ).to_dict(),
                "company": company.get_judgment(
                    fixture.affirmed_company_id, as_of_cutoff=date(2026, 7, 16)
                ).to_dict(),
            },
        }
