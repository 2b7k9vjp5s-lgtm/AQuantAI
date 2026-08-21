"""Offline production-boundary golden path for the V1 research product."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import json
from uuid import UUID

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
from industry_alpha.document_import_models import (
    LocalDocumentAcceptanceLink,
    LocalDocumentReviewCandidateDecision,
)
from industry_alpha.document_import_query import DocumentImportQueryService
from industry_alpha.document_import_rules import sha256_hex
from industry_alpha.product_workspace import ProductWorkspaceService
import industry_alpha.product_workspace_models  # noqa: F401
from scripts.demo_manual_document_import import fixture_pdf, utc


def main() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    workspace = ProductWorkspaceService(factory)
    created = workspace.create_case(
        case_key="v1-product-golden-path",
        case_type="company",
        title="V1 Product Golden Path",
        research_question="What does the reviewed document support?",
        created_by="fixture-reviewer",
        information_cutoff_date=date(2026, 8, 20),
        content={"company_profile": "Draft awaiting reviewed evidence."},
        company_name="Fixture Company",
        stock_code="000001",
        recorded_at_utc=utc(20),
    )
    case_id = UUID(created["case"]["case_id"])
    documents = DocumentImportCommandService(factory)
    imported = documents.import_pdf(
        pdf_bytes=fixture_pdf(),
        original_filename="offline-official-fixture.pdf",
        imported_at_utc=utc(20),
    )
    review = documents.create_review_session(
        import_attempt_id=imported.import_attempt_id,
        target_research_case_id=case_id,
        created_at_utc=utc(20),
    )
    document = documents.add_candidate(
        review.id,
        CandidateInput(
            "document_identity",
            {
                "identity_namespace": "user_defined_document",
                "identity_key": "v1-official-fixture",
                "document_title": "Offline Official Fixture",
                "publisher_or_author": "AQuantAI Fixture Publisher",
                "document_date": "2026-08-20",
                "document_kind": "company_report",
            },
            recorded_at_utc=utc(20),
        ),
    )
    subject = documents.add_candidate(
        review.id,
        CandidateInput(
            "company_identity",
            {"subject_kind": "not_company_specific", "display_label": "Fixture Company"},
            recorded_at_utc=utc(20),
        ),
    )
    pages = DocumentImportQueryService(factory).page_batch(imported.content_id)
    extracted = pages["pages"][0]["extracted_text"]
    quote = "Revenue increased"
    start = extracted.encode().index(quote.encode())
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
            recorded_at_utc=utc(20),
        ),
    )
    source_revision = documents.append_review_revision(
        review.id,
        ReviewRevisionInput(
            expected_previous_revision_number=0,
            review_state="draft",
            source_kind="official",
            evidence_grade="A",
            document_identity_candidate_id=document.id,
            subject_candidate_id=subject.id,
            information_date=date(2026, 8, 20),
            decisions=(
                DecisionInput(document.id, "selected"),
                DecisionInput(subject.id, "selected"),
                DecisionInput(fact.id, "selected", "supported", "supports"),
            ),
            reviewer_identity="fixture-reviewer",
            recorded_at_utc=utc(20),
        ),
    )
    with factory() as session:
        decision_sha = session.scalar(
            select(LocalDocumentReviewCandidateDecision.decision_fingerprint_sha256).where(
                LocalDocumentReviewCandidateDecision.review_revision_id == source_revision.id,
                LocalDocumentReviewCandidateDecision.candidate_id == fact.id,
            )
        )
    acceptance = AcceptanceInput(
        source_revision.id,
        source_revision.revision_number,
        source_revision.review_fingerprint_sha256,
        source_revision.revision_number,
        case_id,
        (fact.id,),
        (decision_sha,),
        utc(20),
        "0" * 64,
    )
    ledger = EvidenceLedgerCommandService(factory)
    preview = ledger.preview_reviewed_local_document(acceptance)
    committed = ledger.accept_reviewed_local_document(
        replace(
            acceptance,
            acceptance_plan_fingerprint_sha256=preview.acceptance_plan_fingerprint_sha256,
        )
    )
    with factory() as session:
        evidence_id = session.scalar(
            select(LocalDocumentAcceptanceLink.evidence_item_id).where(
                LocalDocumentAcceptanceLink.receipt_id == committed.receipt_id
            )
        )
    final_case = workspace.append_revision(
        case_id,
        expected_latest_revision_no=1,
        title="V1 Product Golden Path",
        research_question="What does the reviewed document support?",
        created_by="fixture-reviewer",
        information_cutoff_date=date(2026, 8, 20),
        workflow_state="completed",
        conclusion_status="supported",
        content={
            "company_profile": "Fixture-only local company research.",
            "research_conclusion": "The accepted fixture supports the stated revenue observation.",
            "risks": "Fixture evidence is not real market research.",
            "watch_items": "Collect additional official evidence.",
        },
        evidence_ids=[evidence_id],
        change_summary="Accepted evidence was bound to the authoritative revision.",
        recorded_at_utc=utc(20),
    )
    markdown, _ = workspace.report(case_id)
    print(
        json.dumps(
            {
                "demo": "AQuantAI V1 product golden path",
                "network_calls": 0,
                "ai_calls": 0,
                "pdf_imported": True,
                "reviewer_identity": "fixture-reviewer",
                "evidence_accepted": True,
                "revision_no": final_case["current_revision"]["revision_no"],
                "authoritative_revision": final_case["authoritative_revision"]["revision_no"],
                "citation_count": len(final_case["current_revision"]["evidence_references"]),
                "markdown_exported": "Evidence citations" in markdown,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    engine.dispose()


if __name__ == "__main__":
    main()
