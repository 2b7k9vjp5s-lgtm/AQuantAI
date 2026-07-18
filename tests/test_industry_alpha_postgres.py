from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import make_url

from backend.database.engine import build_engine, build_session_factory
from industry_alpha.commands import EvidenceLedgerCommandService, EvidenceLinkInput
from industry_alpha.errors import (
    EvidenceLedgerImmutableError,
    EvidenceLedgerValidationError,
)
from industry_alpha.models import (
    Claim,
    ClaimEvidenceLink,
    ClaimRevision,
    EvidenceItem,
    ResearchCase,
    ResearchCaseRevision,
    VerificationItem,
)


@pytest.fixture(scope="module")
def postgres_database_url() -> Iterator[str]:
    database_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    database_name = make_url(database_url).database or ""
    if "test" not in database_name.lower():
        pytest.fail("TEST_DATABASE_URL must target a database whose name contains 'test'.")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield database_url
    command.downgrade(config, "base")


@pytest.fixture(autouse=True)
def clean_ledger(postgres_database_url: str) -> Iterator[None]:
    engine = build_engine(postgres_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE verification_items, case_revision_claim_links, claim_evidence_links, "
                    "claim_revisions, claims, evidence_items, research_case_revisions, research_cases CASCADE"
                )
            )
        yield
    finally:
        engine.dispose()


def _recorded(day: int) -> datetime:
    return datetime(2026, 2, day, 12, tzinfo=timezone.utc)


def test_postgres_migration_current_head_round_trip_and_check(postgres_database_url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", postgres_database_url)
    command.downgrade(config, "20260718_0004")
    engine = build_engine(postgres_database_url)
    try:
        assert "research_cases" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()
    command.upgrade(config, "head")
    command.check(config)
    engine = build_engine(postgres_database_url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert {
        "research_cases",
        "research_case_revisions",
        "evidence_items",
        "claims",
        "claim_revisions",
        "claim_evidence_links",
        "case_revision_claim_links",
        "verification_items",
    } <= tables


def test_postgres_concurrent_case_and_claim_revision_numbering(postgres_database_url):
    factory = build_session_factory(build_engine(postgres_database_url))
    service = EvidenceLedgerCommandService(factory)
    case = service.create_case(
        case_key="postgres-concurrent",
        title="Initial",
        research_question="Can revisions remain deterministic?",
        information_cutoff_date=date(2026, 2, 1),
        recorded_at_utc=_recorded(1),
    )

    def append_case(index: int) -> int:
        local_service = EvidenceLedgerCommandService(factory)
        return local_service.append_case_revision(
            case.id,
            title=f"Case revision {index}",
            research_question="Can revisions remain deterministic?",
            information_cutoff_date=date(2026, 2, 2),
            recorded_at_utc=_recorded(2),
        ).revision_no

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(append_case, [1, 2])) == [2, 3]

    claim = service.create_claim(
        case.id,
        claim_key="postgres-claim",
        statement="Initial draft.",
        claim_kind="fact",
        claim_status="draft",
        information_cutoff_date=date(2026, 2, 2),
        recorded_at_utc=_recorded(2),
    )

    def append_claim(index: int) -> int:
        local_service = EvidenceLedgerCommandService(factory)
        return local_service.append_claim_revision(
            claim.id,
            statement=f"Draft revision {index}.",
            claim_kind="fact",
            claim_status="draft",
            information_cutoff_date=date(2026, 2, 3),
            recorded_at_utc=_recorded(3),
        ).revision_no

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(append_claim, [1, 2])) == [2, 3]
    with factory() as session:
        assert [
            row.revision_no
            for row in session.scalars(
                select(ResearchCaseRevision)
                .where(ResearchCaseRevision.case_id == case.id)
                .order_by(ResearchCaseRevision.revision_no)
            )
        ] == [1, 2, 3]
        assert [
            row.revision_no
            for row in session.scalars(
                select(ClaimRevision)
                .where(ClaimRevision.claim_id == claim.id)
                .order_by(ClaimRevision.revision_no)
            )
        ] == [1, 2, 3]


def test_postgres_immutable_guard_rolls_back(postgres_database_url):
    factory = build_session_factory(build_engine(postgres_database_url))
    case = EvidenceLedgerCommandService(factory).create_case(
        case_key="postgres-immutable",
        title="Immutable",
        research_question="Does rejected mutation roll back?",
        information_cutoff_date=date(2026, 2, 1),
        recorded_at_utc=_recorded(1),
    )
    with factory() as session:
        row = session.get(ResearchCase, case.id)
        row.case_key = "forbidden"
        with pytest.raises(EvidenceLedgerImmutableError):
            session.commit()
        session.rollback()
    with factory() as session:
        assert session.get(ResearchCase, case.id).case_key == "postgres-immutable"


def test_postgres_chronology_failures_roll_back_without_history_leak(
    postgres_database_url,
):
    factory = build_session_factory(build_engine(postgres_database_url))
    service = EvidenceLedgerCommandService(factory)
    case = service.create_case(
        case_key="postgres-chronology",
        title="Chronology",
        research_question="Can later operations rewrite history?",
        information_cutoff_date=date(2026, 2, 2),
        recorded_at_utc=datetime(2026, 2, 2, 12, tzinfo=timezone.utc),
    )

    def counts() -> tuple[int, ...]:
        with factory() as session:
            return tuple(
                session.scalar(select(func.count()).select_from(model))
                for model in (
                    ResearchCase,
                    ResearchCaseRevision,
                    EvidenceItem,
                    Claim,
                    ClaimRevision,
                    ClaimEvidenceLink,
                    VerificationItem,
                )
            )

    initial = counts()
    with pytest.raises(EvidenceLedgerValidationError, match="case creation"):
        service.append_case_revision(
            case.id,
            title="Backdated",
            research_question="Must roll back",
            information_cutoff_date=date(2026, 2, 2),
            recorded_at_utc=datetime(2026, 2, 2, 11, tzinfo=timezone.utc),
        )
    assert counts() == initial

    evidence = service.add_evidence(
        case.id,
        evidence_grade="A",
        source_kind="official",
        source_title="PostgreSQL chronology evidence",
        information_date=date(2026, 2, 3),
        summary="Recorded at noon.",
        recorded_at_utc=datetime(2026, 2, 3, 12, tzinfo=timezone.utc),
    )
    before_claim = counts()
    with pytest.raises(EvidenceLedgerValidationError, match="linked evidence"):
        service.create_claim(
            case.id,
            claim_key="postgres-backdated-claim",
            statement="Must not use later evidence.",
            claim_kind="fact",
            claim_status="supported",
            information_cutoff_date=date(2026, 2, 3),
            evidence_links=(EvidenceLinkInput(evidence.id, "supports"),),
            recorded_at_utc=datetime(2026, 2, 3, 11, tzinfo=timezone.utc),
        )
    assert counts() == before_claim

    with factory() as session:
        first_revision = session.scalar(
            select(ResearchCaseRevision).where(
                ResearchCaseRevision.case_id == case.id,
                ResearchCaseRevision.revision_no == 1,
            )
        )
    service.add_verification_item(
        first_revision.id,
        description="Accepted PostgreSQL verification item.",
        recorded_at_utc=datetime(2026, 2, 3, 13, tzinfo=timezone.utc),
    )
    accepted = counts()
    with pytest.raises(EvidenceLedgerValidationError, match="latest verification"):
        service.add_verification_item(
            first_revision.id,
            description="Backdated PostgreSQL verification item.",
            recorded_at_utc=datetime(2026, 2, 3, 12, tzinfo=timezone.utc),
        )
    assert counts() == accepted
