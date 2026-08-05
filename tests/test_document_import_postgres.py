from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime, timezone
import os
from threading import Barrier
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url

from backend.database.engine import build_session_factory
from industry_alpha.commands import EvidenceLedgerCommandService
from industry_alpha.document_import_commands import (
    DocumentImportCommandService,
    accept_local_document_in_session,
)
from industry_alpha.document_import_contracts import (
    AcceptanceInput,
    CandidateInput,
    DecisionInput,
    DocumentImportError,
    ExtractedPage,
    ExtractionResult,
    ReviewRevisionInput,
)
from industry_alpha.document_import_models import (
    LocalDocumentAcceptanceLink,
    LocalDocumentAcceptanceReceipt,
    LocalDocumentReviewCandidateDecision,
    LocalDocumentReviewRevision,
)
from industry_alpha.document_import_rules import sha256_hex
from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem


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
        _truncate_document_graph(connection)
    engine.dispose()
    command.downgrade(config, "base")


@pytest.fixture
def postgres_session_factory(postgres_database_url):
    engine = create_engine(postgres_database_url)
    with engine.begin() as connection:
        _truncate_document_graph(connection)
    factory = build_session_factory(engine)
    yield factory
    with engine.begin() as connection:
        _truncate_document_graph(connection)
    engine.dispose()


def _truncate_document_graph(connection) -> None:
    connection.execute(
        text("TRUNCATE local_document_contents, research_cases CASCADE")
    )


def _utc(hour: int) -> datetime:
    return datetime(2026, 8, 5, hour, tzinfo=timezone.utc)


def _ready_acceptance(postgres_session_factory, monkeypatch, suffix: str):
    raw = f"%PDF-1.7 PostgreSQL fixture {suffix}".encode()
    page_text = f"PostgreSQL 并发回执 {suffix}"
    extracted = ExtractionResult(
        content_sha256=sha256_hex(raw),
        byte_size=len(raw),
        pages=(
            ExtractedPage(
                1,
                page_text,
                sha256_hex(page_text.encode("utf-8")),
                len(page_text),
            ),
        ),
        embedded_text_page_count=1,
        total_text_char_count=len(page_text),
        extractor_package="pypdf",
        extractor_version="6.14.2",
    )
    monkeypatch.setattr(
        "industry_alpha.document_import_commands.extract_pdf",
        lambda *_args, **_kwargs: extracted,
    )
    ledger = EvidenceLedgerCommandService(postgres_session_factory)
    commands = DocumentImportCommandService(postgres_session_factory)
    case = ledger.create_case(
        case_key=f"document-postgres-{suffix}",
        title="PostgreSQL 文档接受测试",
        research_question="并发请求是否收敛？",
        information_cutoff_date=date(2026, 8, 5),
        recorded_at_utc=_utc(8),
    )
    imported = commands.import_pdf(
        pdf_bytes=raw,
        original_filename=f"postgres-{suffix}.pdf",
        imported_at_utc=_utc(9),
    )
    review = commands.create_review_session(
        import_attempt_id=imported.import_attempt_id,
        target_research_case_id=case.id,
        created_at_utc=_utc(9),
    )
    document = commands.add_candidate(
        review.id,
        CandidateInput(
            candidate_kind="document_identity",
            payload={
                "identity_namespace": "user_defined_document",
                "identity_key": f"postgres-{suffix}",
                "document_title": "PostgreSQL 并发文档",
                "publisher_or_author": "本地测试",
                "document_date": "2026-08-05",
                "document_kind": "announcement",
            },
            recorded_at_utc=_utc(9),
        ),
    )
    subject = commands.add_candidate(
        review.id,
        CandidateInput(
            candidate_kind="company_identity",
            payload={
                "subject_kind": "not_company_specific",
                "display_label": "非特定公司",
            },
            recorded_at_utc=_utc(9),
        ),
    )
    quote = suffix
    quote_bytes = quote.encode("utf-8")
    start = page_text.encode("utf-8").index(quote_bytes)
    fact = commands.add_candidate(
        review.id,
        CandidateInput(
            candidate_kind="fact",
            payload={},
            page_number=1,
            start_utf8_byte=start,
            end_utf8_byte=start + len(quote_bytes),
            quote_text=quote,
            quote_sha256=sha256_hex(quote_bytes),
            statement=f"PostgreSQL 接受事实 {suffix}",
            recorded_at_utc=_utc(9),
        ),
    )
    revision = commands.append_review_revision(
        review.id,
        ReviewRevisionInput(
            expected_previous_revision_number=0,
            review_state="draft",
            source_kind="official",
            evidence_grade="A",
            document_identity_candidate_id=document.id,
            subject_candidate_id=subject.id,
            information_date=date(2026, 8, 5),
            decisions=(
                DecisionInput(document.id, "selected"),
                DecisionInput(subject.id, "selected"),
                DecisionInput(
                    fact.id,
                    "selected",
                    claim_status="supported",
                    evidence_relation="supports",
                ),
            ),
            recorded_at_utc=_utc(10),
        ),
    )
    with postgres_session_factory() as session:
        decision_fingerprint = session.scalar(
            select(
                LocalDocumentReviewCandidateDecision.decision_fingerprint_sha256
            ).where(
                LocalDocumentReviewCandidateDecision.review_revision_id == revision.id,
                LocalDocumentReviewCandidateDecision.candidate_id == fact.id,
            )
        )
    draft = AcceptanceInput(
        source_review_revision_id=revision.id,
        expected_source_review_revision_number=revision.revision_number,
        expected_source_review_fingerprint_sha256=revision.review_fingerprint_sha256,
        expected_session_latest_revision_number=revision.revision_number,
        target_research_case_id=case.id,
        selected_candidate_ids=(fact.id,),
        selected_decision_fingerprints=(decision_fingerprint,),
        recorded_at_utc=_utc(11),
        acceptance_plan_fingerprint_sha256="0" * 64,
    )
    preview = ledger.preview_reviewed_local_document(draft)
    return ledger, replace(
        draft,
        acceptance_plan_fingerprint_sha256=(
            preview.acceptance_plan_fingerprint_sha256
        ),
    )


def _acceptance_counts(postgres_session_factory) -> tuple[int, ...]:
    models = (
        EvidenceItem,
        Claim,
        ClaimRevision,
        ClaimEvidenceLink,
        LocalDocumentAcceptanceReceipt,
        LocalDocumentAcceptanceLink,
    )
    with postgres_session_factory() as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model)) for model in models
        )


def _accept_without_process_lock(postgres_session_factory, request):
    """Exercise PostgreSQL's row lock and receipt convergence directly."""

    with postgres_session_factory.begin() as session:
        return accept_local_document_in_session(session, request)


def test_postgres_exact_concurrent_acceptance_converges_to_one_graph(
    postgres_session_factory, monkeypatch
):
    ledger, request = _ready_acceptance(
        postgres_session_factory, monkeypatch, "exact"
    )
    barrier = Barrier(2)

    def submit():
        barrier.wait()
        return _accept_without_process_lock(postgres_session_factory, request)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(lambda _index: submit(), range(2)))

    assert len({row.receipt_id for row in results}) == 1
    assert len({row.accepted_review_revision_id for row in results}) == 1
    assert sorted(row.replayed for row in results) == [False, True]
    assert _acceptance_counts(postgres_session_factory) == (1, 1, 1, 1, 1, 1)
    replay = ledger.accept_reviewed_local_document(request)
    assert replay.replayed is True
    assert replay.receipt_id == results[0].receipt_id
    assert _acceptance_counts(postgres_session_factory) == (1, 1, 1, 1, 1, 1)


def test_postgres_concurrent_conflicting_acceptance_has_one_winner(
    postgres_session_factory, monkeypatch
):
    ledger, request = _ready_acceptance(
        postgres_session_factory, monkeypatch, "conflict"
    )
    requests = (request, replace(request, recorded_at_utc=_utc(12)))
    barrier = Barrier(2)

    def submit(value):
        barrier.wait()
        try:
            return _accept_without_process_lock(postgres_session_factory, value)
        except DocumentImportError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(submit, requests))

    accepted = [row for row in outcomes if not isinstance(row, DocumentImportError)]
    rejected = [row for row in outcomes if isinstance(row, DocumentImportError)]
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected[0].code == "acceptance_replay_conflict"
    assert _acceptance_counts(postgres_session_factory) == (1, 1, 1, 1, 1, 1)
    with postgres_session_factory() as session:
        assert session.scalar(
            select(func.count()).select_from(LocalDocumentReviewRevision)
        ) == 2


def test_postgres_schema_and_populated_downgrade_stop(
    postgres_database_url, postgres_session_factory
):
    engine = postgres_session_factory.kw["bind"]
    assert "local_document_acceptance_receipts" in inspect(engine).get_table_names()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO local_document_contents "
                "(id, content_sha256, media_type, byte_size, raw_pdf_bytes, page_count, "
                "embedded_text_page_count, total_text_char_count, extractor_contract_version, "
                "extractor_package, extractor_version, created_at_utc) VALUES "
                "(:id, :sha, 'application/pdf', 1, :raw, 1, 1, 1, :contract, "
                "'pypdf', '6.14.2', :recorded)"
            ),
            {
                "id": uuid4(),
                "sha": "d" * 64,
                "raw": b"x",
                "contract": "aquantai.local-pdf-embedded-text.v1",
                "recorded": datetime(2026, 8, 4, tzinfo=timezone.utc),
            },
        )
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", postgres_database_url)
    with pytest.raises(RuntimeError, match="Cannot downgrade local document import"):
        command.downgrade(config, "20260725_0017")
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM local_document_contents"))
    command.downgrade(config, "20260725_0017")
    command.upgrade(config, "head")
