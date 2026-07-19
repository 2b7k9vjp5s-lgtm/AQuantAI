from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.errors import EvidenceLedgerValidationError
from industry_alpha import stage2_assessments_commands, stage2_judgments_commands
from industry_alpha.stage2_assessments_fixtures import build_stage2_assessment_fixture
from industry_alpha.stage2_assessments_models import (
    Stage2CatalystAssessment,
    Stage2CatalystAssessmentRevision,
    Stage2CatalystClaimLink,
    Stage2CatalystExpectationLink,
    Stage2CatalystHypothesisLink,
    Stage2CatalystValuationLink,
)
from industry_alpha.stage2_boundary import (
    Stage2BaseBoundary,
    build_stage2_base_boundary,
    load_unique,
)
from industry_alpha.stage2_models import Stage2CompanyResearch


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


def test_v06c_and_v06d_share_the_neutral_boundary_contract():
    assert stage2_assessments_commands._Boundary is Stage2BaseBoundary
    assert stage2_judgments_commands._Boundary is Stage2BaseBoundary
    assert stage2_assessments_commands._frozen_boundary is build_stage2_base_boundary
    assert stage2_judgments_commands._frozen_boundary is build_stage2_base_boundary
    assert "stage2_assessments_commands import" not in inspect.getsource(
        stage2_judgments_commands
    )


def test_boundary_value_is_frozen():
    boundary = Stage2BaseBoundary(None, (), (), (), (), ())
    with pytest.raises(FrozenInstanceError):
        boundary.claims = ()


def test_duplicate_identifier_validation_message_is_preserved():
    duplicate = uuid4()
    with pytest.raises(
        EvidenceLedgerValidationError,
        match="hypothesis_revision_ids must be a tuple of non-empty and unique identifiers",
    ):
        load_unique(
            None,
            object,
            (duplicate, duplicate),
            "hypothesis_revision_ids",
            required=True,
        )


def test_build_neutral_boundary_from_existing_stage2_fixture(session_factory):
    built = build_stage2_assessment_fixture(session_factory)
    with session_factory.begin() as session:
        revision = session.get(
            Stage2CatalystAssessmentRevision, built.later_catalyst_revision_id
        )
        catalyst = session.get(Stage2CatalystAssessment, revision.catalyst_id)
        research = session.get(Stage2CompanyResearch, catalyst.company_research_id)
        hypothesis_ids = tuple(
            session.scalars(
                select(Stage2CatalystHypothesisLink.hypothesis_revision_id).where(
                    Stage2CatalystHypothesisLink.catalyst_revision_id == revision.id
                )
            )
        )
        expectation_ids = tuple(
            session.scalars(
                select(Stage2CatalystExpectationLink.expectation_revision_id).where(
                    Stage2CatalystExpectationLink.catalyst_revision_id == revision.id
                )
            )
        )
        valuation_ids = tuple(
            session.scalars(
                select(Stage2CatalystValuationLink.valuation_revision_id).where(
                    Stage2CatalystValuationLink.catalyst_revision_id == revision.id
                )
            )
        )
        claim_ids = tuple(
            session.scalars(
                select(Stage2CatalystClaimLink.claim_revision_id).where(
                    Stage2CatalystClaimLink.catalyst_revision_id == revision.id
                )
            )
        )

        boundary = build_stage2_base_boundary(
            session,
            research,
            company_research_revision_id=revision.company_research_revision_id,
            hypothesis_revision_ids=hypothesis_ids,
            expectation_revision_ids=expectation_ids,
            valuation_revision_ids=valuation_ids,
            claim_revision_ids=claim_ids,
            cutoff=date(2026, 7, 20),
            recorded=datetime(2026, 7, 20, 12, tzinfo=timezone.utc),
        )

    assert isinstance(boundary, Stage2BaseBoundary)
    assert {item.id for item in boundary.hypotheses} == set(hypothesis_ids)
    assert {item.id for item in boundary.expectations} == set(expectation_ids)
    assert {item.id for item in boundary.valuations} == set(valuation_ids)
    assert {item.id for item in boundary.claims} == set(claim_ids)
    assert boundary.evidence
