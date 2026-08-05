from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.commands import EvidenceLedgerCommandService
from industry_alpha.document_import_commands import DocumentImportCommandService
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
    LocalDocumentContent,
    LocalDocumentImportAttempt,
    LocalDocumentPage,
    LocalDocumentReviewCandidateDecision,
    LocalDocumentReviewRevision,
)
from industry_alpha.document_import_query import DocumentImportQueryService
from industry_alpha.document_import_rules import sha256_hex
from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem


def utc(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


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
def extracted(monkeypatch):
    text = "本地官方文档显示收益增长。"
    raw = b"%PDF-1.7 synthetic fixture"
    result = ExtractionResult(
        content_sha256=sha256_hex(raw),
        byte_size=len(raw),
        pages=(ExtractedPage(1, text, sha256_hex(text.encode("utf-8")), len(text)),),
        embedded_text_page_count=1,
        total_text_char_count=len(text),
        extractor_package="pypdf",
        extractor_version="6.14.2",
    )
    monkeypatch.setattr(
        "industry_alpha.document_import_commands.extract_pdf", lambda *_a, **_k: result
    )
    return raw, text


def build_review(session_factory, extracted, *, selected_fact: bool = True):
    raw, text = extracted
    ledger = EvidenceLedgerCommandService(session_factory)
    case = ledger.create_case(
        case_key="document-case",
        title="文档证据审核",
        research_question="文档说了什么？",
        information_cutoff_date=date(2026, 8, 1),
        recorded_at_utc=utc(1),
    )
    commands = DocumentImportCommandService(session_factory)
    imported = commands.import_pdf(
        pdf_bytes=raw,
        original_filename="公告.pdf",
        imported_at_utc=utc(2),
    )
    review = commands.create_review_session(
        import_attempt_id=imported.import_attempt_id,
        target_research_case_id=case.id,
        created_at_utc=utc(2),
    )
    document = commands.add_candidate(
        review.id,
        CandidateInput(
            candidate_kind="document_identity",
            payload={
                "identity_namespace": "user_defined_document",
                "identity_key": "issuer-report-2026-08",
                "document_title": "八月官方公告",
                "publisher_or_author": "示例发行人",
                "document_date": "2026-08-03",
                "document_kind": "announcement",
            },
            recorded_at_utc=utc(2),
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
            recorded_at_utc=utc(2),
        ),
    )
    quote = "收益增长"
    start = text.encode("utf-8").index(quote.encode("utf-8"))
    fact = commands.add_candidate(
        review.id,
        CandidateInput(
            candidate_kind="fact",
            payload={},
            page_number=1,
            start_utf8_byte=start,
            end_utf8_byte=start + len(quote.encode("utf-8")),
            quote_text=quote,
            quote_sha256=sha256_hex(quote.encode("utf-8")),
            statement="该文档明确披露收益增长。",
            recorded_at_utc=utc(2),
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
            information_date=date(2026, 8, 3),
            decisions=(
                DecisionInput(document.id, "selected"),
                DecisionInput(subject.id, "selected"),
                DecisionInput(
                    fact.id,
                    "selected" if selected_fact else "rejected",
                    claim_status="supported" if selected_fact else None,
                    evidence_relation="supports" if selected_fact else None,
                ),
            ),
            recorded_at_utc=utc(3),
        ),
    )
    return ledger, commands, case, imported, review, fact, revision


def acceptance_input(case, fact, revision) -> AcceptanceInput:
    with_placeholder = AcceptanceInput(
        source_review_revision_id=revision.id,
        expected_source_review_revision_number=revision.revision_number,
        expected_source_review_fingerprint_sha256=revision.review_fingerprint_sha256,
        expected_session_latest_revision_number=revision.revision_number,
        target_research_case_id=case.id,
        selected_candidate_ids=(fact.id,),
        selected_decision_fingerprints=(),
        recorded_at_utc=utc(4),
        acceptance_plan_fingerprint_sha256="0" * 64,
    )
    return with_placeholder


def ready_acceptance(session_factory, ledger, case, fact, revision):
    draft = acceptance_input(case, fact, revision)
    with session_factory() as session:
        decision_fingerprint = session.scalar(
            select(
                LocalDocumentReviewCandidateDecision.decision_fingerprint_sha256
            ).where(
                LocalDocumentReviewCandidateDecision.review_revision_id
                == revision.id,
                LocalDocumentReviewCandidateDecision.candidate_id == fact.id,
            )
        )
    draft = replace(
        draft, selected_decision_fingerprints=(decision_fingerprint,)
    )
    preview = ledger.preview_reviewed_local_document(draft)
    return replace(
        draft,
        acceptance_plan_fingerprint_sha256=(
            preview.acceptance_plan_fingerprint_sha256
        ),
    )


def test_import_persists_exact_content_pages_and_duplicate_alias(
    session_factory, extracted
):
    raw, _ = extracted
    commands = DocumentImportCommandService(session_factory)
    first = commands.import_pdf(
        pdf_bytes=raw, original_filename="a.pdf", imported_at_utc=utc(1)
    )
    second = commands.import_pdf(
        pdf_bytes=raw, original_filename="别名.pdf", imported_at_utc=utc(2)
    )
    assert first.admission_state == "admitted"
    assert second.admission_state == "exact_content_duplicate"
    assert first.content_id == second.content_id
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(LocalDocumentContent)) == 1
        assert session.scalar(select(func.count()).select_from(LocalDocumentPage)) == 1
        assert session.scalar(select(func.count()).select_from(LocalDocumentImportAttempt)) == 2


def test_import_classifies_exact_filename_conflict_without_merging_content(
    session_factory, extracted, monkeypatch
):
    first_raw, text = extracted
    second_raw = b"%PDF-1.7 second synthetic fixture"

    def extract(value):
        return ExtractionResult(
            content_sha256=sha256_hex(value),
            byte_size=len(value),
            pages=(
                ExtractedPage(
                    1,
                    text,
                    sha256_hex(text.encode("utf-8")),
                    len(text),
                ),
            ),
            embedded_text_page_count=1,
            total_text_char_count=len(text),
            extractor_package="pypdf",
            extractor_version="6.14.2",
        )

    monkeypatch.setattr(
        "industry_alpha.document_import_commands.extract_pdf", extract
    )
    commands = DocumentImportCommandService(session_factory)
    first = commands.import_pdf(
        pdf_bytes=first_raw,
        original_filename=" exact-name.pdf ",
        imported_at_utc=utc(1),
    )
    conflict = commands.import_pdf(
        pdf_bytes=second_raw,
        original_filename=" exact-name.pdf ",
        imported_at_utc=utc(2),
    )
    assert first.admission_state == "admitted"
    assert conflict.admission_state == "filename_content_conflict"
    assert first.content_id != conflict.content_id
    with session_factory() as session:
        attempts = list(
            session.scalars(
                select(LocalDocumentImportAttempt).order_by(
                    LocalDocumentImportAttempt.imported_at_utc
                )
            )
        )
        assert [row.original_filename for row in attempts] == [
            " exact-name.pdf ",
            " exact-name.pdf ",
        ]


def test_invalid_media_records_safe_rejection_without_extraction(
    session_factory, monkeypatch
):
    monkeypatch.setattr(
        "industry_alpha.document_import_commands.extract_pdf",
        lambda *_a, **_k: pytest.fail("invalid media must not reach extraction"),
    )
    result = DocumentImportCommandService(session_factory).import_pdf(
        pdf_bytes=b"not parsed",
        original_filename="bad.pdf",
        observed_media_type="",
        imported_at_utc=utc(1),
    )
    assert result.admission_state == "rejected"
    assert result.admission_reason == "invalid_media_type"
    with session_factory() as session:
        attempt = session.get(LocalDocumentImportAttempt, result.import_attempt_id)
        assert attempt.observed_media_type == "invalid"


def test_acceptance_is_atomic_exact_and_replay_is_zero_write(session_factory, extracted):
    ledger, _, case, _, _, fact, revision = build_review(session_factory, extracted)
    draft = acceptance_input(case, fact, revision)
    with session_factory() as session:
        decision_fingerprint = session.scalar(
            select(LocalDocumentReviewCandidateDecision.decision_fingerprint_sha256).where(
                LocalDocumentReviewCandidateDecision.review_revision_id == revision.id,
                LocalDocumentReviewCandidateDecision.candidate_id == fact.id,
            )
        )
    draft = replace(draft, selected_decision_fingerprints=(decision_fingerprint,))
    preview = ledger.preview_reviewed_local_document(draft)
    request = replace(
        draft,
        acceptance_plan_fingerprint_sha256=preview.acceptance_plan_fingerprint_sha256,
    )
    result = ledger.accept_reviewed_local_document(request)
    with session_factory() as session:
        models = (
            EvidenceItem,
            Claim,
            ClaimRevision,
            ClaimEvidenceLink,
            LocalDocumentAcceptanceReceipt,
            LocalDocumentAcceptanceLink,
            LocalDocumentReviewRevision,
        )
        counts = tuple(
            session.scalar(select(func.count()).select_from(model)) for model in models
        )
        accepted = session.get(LocalDocumentReviewRevision, result.accepted_review_revision_id)
        assert accepted.review_state == "accepted"
    replay = ledger.accept_reviewed_local_document(request)
    assert replay.replayed is True
    assert replay.receipt_id == result.receipt_id
    with session_factory() as session:
        assert tuple(
            session.scalar(select(func.count()).select_from(model)) for model in models
        ) == counts


def test_nonempty_acceptance_fails_closed_with_zero_ledger_writes(
    session_factory, extracted
):
    ledger, _, case, _, _, fact, revision = build_review(
        session_factory, extracted, selected_fact=False
    )
    with pytest.raises(DocumentImportError, match="nonempty_acceptance_required"):
        ledger.preview_reviewed_local_document(acceptance_input(case, fact, revision))
    with session_factory() as session:
        for model in (EvidenceItem, Claim, ClaimRevision, ClaimEvidenceLink):
            assert session.scalar(select(func.count()).select_from(model)) == 0


def test_invalid_quote_span_is_rejected(session_factory, extracted):
    _, commands, _, _, review, _, _ = build_review(session_factory, extracted)
    with pytest.raises(DocumentImportError, match="citation_quote_mismatch"):
        commands.add_candidate(
            review.id,
            CandidateInput(
                candidate_kind="fact",
                payload={},
                page_number=1,
                start_utf8_byte=0,
                end_utf8_byte=3,
                quote_text="错误",
                quote_sha256=sha256_hex("错误".encode("utf-8")),
                statement="不得写入",
                recorded_at_utc=utc(4),
            ),
        )


def test_acceptance_conflicting_replay_and_terminal_history_fail_closed(
    session_factory, extracted
):
    ledger, commands, case, _, review, fact, revision = build_review(
        session_factory, extracted
    )
    request = ready_acceptance(
        session_factory, ledger, case, fact, revision
    )
    accepted = ledger.accept_reviewed_local_document(request)
    with pytest.raises(DocumentImportError, match="acceptance_replay_conflict"):
        ledger.accept_reviewed_local_document(
            replace(request, recorded_at_utc=utc(5))
        )
    with pytest.raises(DocumentImportError, match="review_terminal"):
        commands.add_candidate(
            review.id,
            CandidateInput(
                "fact",
                {},
                page_number=1,
                start_utf8_byte=0,
                end_utf8_byte=3,
                quote_text="本",
                quote_sha256=sha256_hex("本".encode("utf-8")),
                statement="终态后不得新增。",
                recorded_at_utc=utc(5),
            ),
        )
    exact = DocumentImportQueryService(session_factory).acceptance_detail(
        accepted.receipt_id,
        information_cutoff_date=date(2026, 8, 3),
        recorded_at_utc=utc(4),
    )
    assert exact["accepted_review_revision_id"] == str(
        accepted.accepted_review_revision_id
    )
    with pytest.raises(DocumentImportError, match="acceptance_not_visible_as_of"):
        DocumentImportQueryService(session_factory).acceptance_detail(
            accepted.receipt_id,
            information_cutoff_date=date(2026, 8, 2),
            recorded_at_utc=utc(4),
        )


def test_acceptance_rolls_back_every_owner_on_injected_failure(
    session_factory, extracted
):
    ledger, _, case, _, _, fact, revision = build_review(
        session_factory, extracted
    )
    request = ready_acceptance(
        session_factory, ledger, case, fact, revision
    )
    engine = session_factory.kw["bind"]

    def fail_on_acceptance_link(
        _connection, _cursor, statement, _parameters, _context, _many
    ):
        if statement.lstrip().upper().startswith(
            "INSERT INTO LOCAL_DOCUMENT_ACCEPTANCE_LINKS"
        ):
            raise RuntimeError("injected acceptance failure")

    event.listen(engine, "before_cursor_execute", fail_on_acceptance_link)
    try:
        with pytest.raises(RuntimeError, match="injected acceptance failure"):
            ledger.accept_reviewed_local_document(request)
    finally:
        event.remove(engine, "before_cursor_execute", fail_on_acceptance_link)
    with session_factory() as session:
        assert session.scalar(
            select(func.count()).select_from(LocalDocumentAcceptanceReceipt)
        ) == 0
        assert session.scalar(
            select(func.count()).select_from(LocalDocumentAcceptanceLink)
        ) == 0
        for model in (EvidenceItem, Claim, ClaimRevision, ClaimEvidenceLink):
            assert session.scalar(select(func.count()).select_from(model)) == 0
        assert session.scalar(
            select(func.count()).select_from(LocalDocumentReviewRevision)
        ) == 1


def test_acceptance_preview_and_commit_respect_sql_ceilings(
    session_factory, extracted
):
    ledger, _, case, _, _, fact, revision = build_review(
        session_factory, extracted
    )
    draft = acceptance_input(case, fact, revision)
    with session_factory() as session:
        decision_fingerprint = session.scalar(
            select(
                LocalDocumentReviewCandidateDecision.decision_fingerprint_sha256
            ).where(
                LocalDocumentReviewCandidateDecision.review_revision_id
                == revision.id,
                LocalDocumentReviewCandidateDecision.candidate_id == fact.id,
            )
        )
    draft = replace(
        draft, selected_decision_fingerprints=(decision_fingerprint,)
    )
    engine = session_factory.kw["bind"]
    statements = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.strip().splitlines()[0])

    event.listen(engine, "before_cursor_execute", capture)
    try:
        preview = ledger.preview_reviewed_local_document(draft)
        preview_count = len(statements)
        statements.clear()
        ledger.accept_reviewed_local_document(
            replace(
                draft,
                acceptance_plan_fingerprint_sha256=(
                    preview.acceptance_plan_fingerprint_sha256
                ),
            )
        )
        commit_count = len(statements)
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert preview_count <= 10
    assert commit_count <= 16, statements
