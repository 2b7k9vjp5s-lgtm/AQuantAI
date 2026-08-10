from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timezone
import os

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, event, select, text, update
from sqlalchemy.engine import make_url

from backend.database.engine import build_session_factory
from industry_alpha.commands import EvidenceLedgerCommandService
from industry_alpha.document_import_models import (
    LocalDocumentCandidate,
    LocalDocumentReviewSession,
)
from industry_alpha.models import ResearchCaseRevision
from industry_alpha.research_evidence_pack_contracts import (
    EvidencePackRequest,
    ResearchEvidencePackError,
)
from industry_alpha.research_evidence_pack_query import ResearchEvidencePackQueryService
from scripts.demo_research_evidence_pack import run_demo
from tests.test_research_evidence_pack_query import _build_golden_graph, _request


INFO_DATE = date(2026, 8, 5)


def _utc(hour: int) -> datetime:
    return datetime(2026, 8, 5, hour, tzinfo=timezone.utc)


def test_zero_network_demo_is_executable_from_full_pytest():
    payload = run_demo()
    assert payload["contract_version"] == "aquantai.research-evidence-pack.v1"
    assert payload["visible_evidence_count"] == 1
    assert payload["entries"][0]["integrity_state"] == "ledger_only"
    assert payload["notices"]["writes_per_get"] == 0
    assert payload["notices"]["network_calls"] == 0
    assert payload["notices"]["ocr_calls"] == 0
    assert payload["notices"]["ai_calls"] == 0


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


def test_postgres_local_document_receipt_replay_stays_within_eight_statements(
    postgres_session_factory, monkeypatch
):
    graph = _build_golden_graph(postgres_session_factory, monkeypatch)
    engine = postgres_session_factory.kw["bind"]
    statements: list[str] = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        payload = ResearchEvidencePackQueryService(postgres_session_factory).get_pack(
            _request(graph, limit=100)
        ).to_dict()
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert 1 <= len(statements) <= 8
    entries = {row["evidence"]["evidence_id"]: row for row in payload["entries"]}
    local = entries[str(graph["local_evidence_id"])]
    assert local["integrity_state"] == "validated_local_document"
    assert local["membership_summary"] == "mixed_linked_and_unlinked_bindings"
    assert local["local_document_provenance"]["candidate_id"] == str(graph["candidate_id"])


def test_postgres_receipt_chronology_corruption_fails_closed(
    postgres_session_factory, monkeypatch
):
    graph = _build_golden_graph(postgres_session_factory, monkeypatch)
    with postgres_session_factory.begin() as session:
        review_session_id = session.scalar(
            select(LocalDocumentCandidate.review_session_id).where(
                LocalDocumentCandidate.id == graph["candidate_id"]
            )
        )
        session.execute(
            update(LocalDocumentReviewSession)
            .where(LocalDocumentReviewSession.id == review_session_id)
            .values(created_at_utc=datetime(2026, 8, 5, 11, 30))
        )
    with pytest.raises(ResearchEvidencePackError) as error:
        ResearchEvidencePackQueryService(postgres_session_factory).get_pack(_request(graph))
    assert error.value.code == "evidence_pack_integrity_error"


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
        information_date=date(2026, 8, 4),
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
