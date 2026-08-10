from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timezone
import os

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.engine import make_url

from backend.database.engine import build_session_factory
from industry_alpha.commands import EvidenceLedgerCommandService
from industry_alpha.models import ResearchCaseRevision
from industry_alpha.research_evidence_pack_contracts import EvidencePackRequest
from industry_alpha.research_evidence_pack_query import ResearchEvidencePackQueryService


INFO_DATE = date(2026, 8, 5)


def _utc(hour: int) -> datetime:
    return datetime(2026, 8, 5, hour, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def postgres_database_url() -> Iterator[str]:
    database_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    if "test" not in (make_url(database_url).database or "").lower():
        pytest.fail("TEST_DATABASE_URL must target a database whose name contains 'test'.")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield database_url
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE local_document_contents, research_cases CASCADE"))
    engine.dispose()
    command.downgrade(config, "base")


@pytest.fixture
def postgres_session_factory(postgres_database_url):
    engine = create_engine(postgres_database_url)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE local_document_contents, research_cases CASCADE"))
    factory = build_session_factory(engine)
    yield factory
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE local_document_contents, research_cases CASCADE"))
    engine.dispose()


def test_postgres_keyset_and_minimal_supersession_target_load_stay_within_ceiling(
    postgres_session_factory,
):
    ledger = EvidenceLedgerCommandService(postgres_session_factory)
    case = ledger.create_case(
        case_key="research-evidence-pack-postgres",
        title="PostgreSQL 证据包",
        research_question="跨数据库语义是否一致？",
        information_cutoff_date=INFO_DATE,
        recorded_at_utc=_utc(8),
    )
    first = ledger.add_evidence(
        case.id,
        evidence_grade="B",
        source_kind="research",
        source_title="旧证据",
        information_date=INFO_DATE,
        summary="旧证据内容",
        content_fingerprint="research-evidence-pack-pg-old",
        recorded_at_utc=_utc(9),
    )
    second = ledger.add_evidence(
        case.id,
        evidence_grade="B",
        source_kind="research",
        source_title="新证据",
        information_date=INFO_DATE,
        summary="新证据内容",
        content_fingerprint="research-evidence-pack-pg-new",
        supersedes_evidence_id=first.id,
        recorded_at_utc=_utc(9),
    )
    with postgres_session_factory() as session:
        revision_id = session.scalar(
            select(ResearchCaseRevision.id).where(
                ResearchCaseRevision.case_id == case.id,
                ResearchCaseRevision.revision_no == 1,
            )
        )

    request = EvidencePackRequest(
        research_case_id=case.id,
        research_case_revision_id=revision_id,
        information_cutoff_date=INFO_DATE,
        recorded_at_utc=_utc(10),
        limit=1,
    )
    engine = postgres_session_factory.kw["bind"]
    statements: list[str] = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        first_page = ResearchEvidencePackQueryService(
            postgres_session_factory
        ).get_pack(request).to_dict()
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert 1 <= len(statements) <= 8
    assert first_page["visible_evidence_count"] == 2
    assert len(first_page["entries"]) == 1
    assert first_page["entries"][0]["evidence"]["evidence_id"] == str(second.id)
    assert first_page["entries"][0]["evidence"]["supersession_reference"] == {
        "evidence_id": str(first.id),
        "visibility_state": "visible_as_of",
    }
    assert first_page["next_cursor"] is not None

    second_page = ResearchEvidencePackQueryService(postgres_session_factory).get_pack(
        EvidencePackRequest(
            research_case_id=case.id,
            research_case_revision_id=revision_id,
            information_cutoff_date=INFO_DATE,
            recorded_at_utc=_utc(10),
            limit=1,
            cursor=first_page["next_cursor"],
        )
    ).to_dict()
    assert second_page["entries"][0]["evidence"]["evidence_id"] == str(first.id)
    assert second_page["next_cursor"] is None
