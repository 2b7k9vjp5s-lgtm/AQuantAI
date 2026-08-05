"""Offline golden path for explicit local PDF review and atomic acceptance."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
from io import BytesIO
import json

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.commands import EvidenceLedgerCommandService
from industry_alpha.document_import_commands import DocumentImportCommandService
from industry_alpha.document_import_contracts import (
    AcceptanceInput,
    CandidateInput,
    DecisionInput,
    ReviewRevisionInput,
)
from industry_alpha.document_import_models import LocalDocumentReviewCandidateDecision
from industry_alpha.document_import_query import DocumentImportQueryService
from industry_alpha.document_import_rules import sha256_hex


def utc(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def fixture_pdf() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=200)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 100 Td (Revenue increased in the period.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def main() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    ledger = EvidenceLedgerCommandService(factory)
    documents = DocumentImportCommandService(factory)
    case = ledger.create_case(
        case_key="manual-pdf-demo",
        title="本地 PDF Evidence Ledger 演示",
        research_question="这份文档有哪些可引用事实？",
        information_cutoff_date=date(2026, 8, 1),
        recorded_at_utc=utc(1),
    )
    imported = documents.import_pdf(
        pdf_bytes=fixture_pdf(),
        original_filename="offline-official-fixture.pdf",
        imported_at_utc=utc(2),
    )
    review = documents.create_review_session(
        import_attempt_id=imported.import_attempt_id,
        target_research_case_id=case.id,
        created_at_utc=utc(2),
    )
    document = documents.add_candidate(
        review.id,
        CandidateInput(
            "document_identity",
            {
                "identity_namespace": "user_defined_document",
                "identity_key": "offline-official-fixture-2026",
                "document_title": "Offline Official Fixture",
                "publisher_or_author": "AQuantAI Fixture Publisher",
                "document_date": "2026-08-03",
                "document_kind": "company_report",
            },
            recorded_at_utc=utc(2),
        ),
    )
    subject = documents.add_candidate(
        review.id,
        CandidateInput(
            "company_identity",
            {"subject_kind": "not_company_specific", "display_label": "演示主体"},
            recorded_at_utc=utc(2),
        ),
    )
    pages = DocumentImportQueryService(factory).page_batch(imported.content_id)
    text = pages["pages"][0]["extracted_text"]
    quote = "Revenue increased"
    start = text.encode().index(quote.encode())
    fact = documents.add_candidate(
        review.id,
        CandidateInput(
            "fact",
            {},
            page_number=1,
            start_utf8_byte=start,
            end_utf8_byte=start + len(quote.encode()),
            quote_text=quote,
            quote_sha256=sha256_hex(quote.encode()),
            statement="The reviewed fixture states that revenue increased.",
            recorded_at_utc=utc(2),
        ),
    )
    source = documents.append_review_revision(
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
                DecisionInput(fact.id, "selected", "supported", "supports"),
            ),
            recorded_at_utc=utc(3),
        ),
    )
    with factory() as session:
        decision_sha = session.scalar(
            select(LocalDocumentReviewCandidateDecision.decision_fingerprint_sha256).where(
                LocalDocumentReviewCandidateDecision.review_revision_id == source.id,
                LocalDocumentReviewCandidateDecision.candidate_id == fact.id,
            )
        )
    request = AcceptanceInput(
        source.id,
        source.revision_number,
        source.review_fingerprint_sha256,
        source.revision_number,
        case.id,
        (fact.id,),
        (decision_sha,),
        utc(4),
        "0" * 64,
    )
    preview = ledger.preview_reviewed_local_document(request)
    result = ledger.accept_reviewed_local_document(
        replace(
            request,
            acceptance_plan_fingerprint_sha256=preview.acceptance_plan_fingerprint_sha256,
        )
    )
    history = DocumentImportQueryService(factory).acceptance_detail(
        result.receipt_id,
        information_cutoff_date=date(2026, 8, 3),
        recorded_at_utc=utc(4),
    )
    print(
        json.dumps(
            {
                "demo": "manual official PDF import and Evidence Ledger v1",
                "network_calls": 0,
                "ocr_calls": 0,
                "ai_calls": 0,
                "page_count": len(pages["pages"]),
                "accepted_candidate_count": len(history["links"]),
                "receipt_id": str(result.receipt_id),
                "exact_reopen": history["request_fingerprint_sha256"]
                == result.request_fingerprint_sha256,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    engine.dispose()


if __name__ == "__main__":
    main()
