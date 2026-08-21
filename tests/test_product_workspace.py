from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
import json
from uuid import UUID

import pytest
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
    ExtractedPage,
    ExtractionResult,
    ReviewRevisionInput,
)
from industry_alpha.document_import_models import (
    LocalDocumentAcceptanceLink,
    LocalDocumentReviewCandidateDecision,
)
from industry_alpha.document_import_rules import sha256_hex
from industry_alpha.product_workspace import ProductWorkspaceError, ProductWorkspaceService
from industry_alpha.product_workspace_ai import ProductWorkspaceAIService
from industry_alpha.guarded_ai_adapter import GuardedAIProviderConfig
from industry_alpha.guarded_ai_contracts import (
    ALLOWED_SECTION_NAMES,
    DRAFT_SCHEMA_VERSION,
    GuardedAIAdapterResult,
    GuardedAIProviderError,
    GuardedAIResponseValidationError,
)
import industry_alpha.product_workspace_models  # noqa: F401


NOW = datetime(2026, 8, 21, 10, tzinfo=timezone.utc)


@pytest.fixture
def factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield build_session_factory(engine)
    engine.dispose()


def create_product_case(factory):
    return ProductWorkspaceService(factory).create_case(
        case_key="v1-industry-semiconductor",
        case_type="industry",
        title="Semiconductor equipment",
        research_question="What changes the domestic equipment opportunity?",
        created_by="reviewer-a",
        information_cutoff_date=date(2026, 8, 20),
        content={"driver_type": "Localization"},
        industry_theme="Semiconductor",
        recorded_at_utc=NOW,
    )


def accept_document_evidence(factory, monkeypatch, case_id):
    case_id = UUID(str(case_id))
    raw = b"%PDF-1.7 product workspace fixture"
    page_text = "Official filing reports completed customer certification."
    result = ExtractionResult(
        content_sha256=sha256_hex(raw),
        byte_size=len(raw),
        pages=(ExtractedPage(1, page_text, sha256_hex(page_text.encode()), len(page_text)),),
        embedded_text_page_count=1,
        total_text_char_count=len(page_text),
        extractor_package="pypdf",
        extractor_version="6.14.2",
    )
    monkeypatch.setattr("industry_alpha.document_import_commands.extract_pdf", lambda *_a, **_k: result)
    commands = DocumentImportCommandService(factory)
    imported = commands.import_pdf(pdf_bytes=raw, original_filename="official.pdf", imported_at_utc=NOW)
    review = commands.create_review_session(
        import_attempt_id=imported.import_attempt_id,
        target_research_case_id=case_id,
        created_at_utc=NOW,
    )
    document = commands.add_candidate(
        review.id,
        CandidateInput(
            "document_identity",
            {
                "identity_namespace": "user_defined_document",
                "identity_key": "official-2026",
                "document_title": "Official annual filing",
                "publisher_or_author": "Example issuer",
                "document_date": "2026-08-20",
                "document_kind": "announcement",
                "source_url": "https://example.invalid/official.pdf",
            },
            recorded_at_utc=NOW,
        ),
    )
    subject = commands.add_candidate(
        review.id,
        CandidateInput(
            "company_identity",
            {"subject_kind": "not_company_specific", "display_label": "Industry"},
            recorded_at_utc=NOW,
        ),
    )
    quote = "completed customer certification"
    start = page_text.encode().index(quote.encode())
    fact = commands.add_candidate(
        review.id,
        CandidateInput(
            "fact",
            {},
            page_number=1,
            start_utf8_byte=start,
            end_utf8_byte=start + len(quote.encode()),
            quote_text=quote,
            quote_sha256=sha256_hex(quote.encode()),
            statement="Customer certification was completed.",
            recorded_at_utc=NOW,
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
            information_date=date(2026, 8, 20),
            decisions=(
                DecisionInput(document.id, "selected"),
                DecisionInput(subject.id, "selected"),
                DecisionInput(fact.id, "selected", "supported", "supports"),
            ),
            reviewer_identity="reviewer-a",
            recorded_at_utc=NOW,
        ),
    )
    with factory() as session:
        decision = session.scalar(
            select(LocalDocumentReviewCandidateDecision).where(
                LocalDocumentReviewCandidateDecision.review_revision_id == revision.id,
                LocalDocumentReviewCandidateDecision.candidate_id == fact.id,
            )
        )
    assert decision is not None
    request = AcceptanceInput(
        source_review_revision_id=revision.id,
        expected_source_review_revision_number=1,
        expected_source_review_fingerprint_sha256=revision.review_fingerprint_sha256,
        expected_session_latest_revision_number=1,
        target_research_case_id=case_id,
        selected_candidate_ids=(fact.id,),
        selected_decision_fingerprints=(decision.decision_fingerprint_sha256,),
        recorded_at_utc=NOW,
        acceptance_plan_fingerprint_sha256="0" * 64,
    )
    ledger = EvidenceLedgerCommandService(factory)
    preview = ledger.preview_reviewed_local_document(request)
    accepted = ledger.accept_reviewed_local_document(
        replace(request, acceptance_plan_fingerprint_sha256=preview.acceptance_plan_fingerprint_sha256)
    )
    with factory() as session:
        link = session.scalar(
            select(LocalDocumentAcceptanceLink).where(
                LocalDocumentAcceptanceLink.receipt_id == accepted.receipt_id
            )
        )
    assert link is not None
    return link.evidence_item_id


def test_create_case_revision_history_search_feed_and_reports(factory, monkeypatch):
    created = create_product_case(factory)
    case_id = created["case"]["case_id"]
    evidence_id = accept_document_evidence(factory, monkeypatch, case_id)
    service = ProductWorkspaceService(factory)
    updated = service.append_revision(
        UUID(case_id),
        expected_latest_revision_no=1,
        title="Semiconductor equipment evidence review",
        research_question="What changes the domestic equipment opportunity?",
        created_by="reviewer-a",
        information_cutoff_date=date(2026, 8, 20),
        workflow_state="completed",
        conclusion_status="supported",
        content={
            "driver_type": "Localization",
            "research_conclusion": "Certification evidence supports the recorded observation.",
            "risks": "Evidence covers one issuer only.",
        },
        evidence_ids=[evidence_id],
        change_summary="Bound the accepted filing evidence.",
        recorded_at_utc=NOW,
    )
    assert updated["current_revision"]["revision_no"] == 2
    assert updated["authoritative_revision"]["revision_no"] == 2
    citation = updated["current_revision"]["evidence_references"][0]
    assert citation["page"] == 1
    assert citation["source"] == "Official annual filing"
    assert citation["source_url"] == "https://example.invalid/official.pdf"
    ledger_item = service.evidence_ledger(status="accepted")["items"][0]
    assert ledger_item["reviewer"] == "reviewer-a"
    assert ledger_item["reviewed_at_utc"] == "2026-08-21T10:00:00Z"
    assert ledger_item["page"] == 1
    assert service.evidence_ledger(status="pending_review") == {
        "items": [],
        "count": 0,
        "statuses": ["imported", "pending_review", "accepted", "rejected"],
    }
    assert service.dashboard()["accepted_evidence_count"] == 1
    assert service.search("Semiconductor")["count"] >= 1
    assert {item["event_type"] for item in service.change_feed()["items"]} >= {
        "research_revision", "accepted_evidence", "document_import"
    }
    markdown, media_type = service.report(UUID(case_id))
    assert "Evidence citations" in markdown
    assert str(evidence_id) in markdown
    assert "not investment advice" in markdown
    assert media_type.startswith("text/markdown")
    html, html_type = service.report(UUID(case_id), format="html")
    assert "<!doctype html>" in html
    assert html_type.startswith("text/html")


def test_authoritative_revision_requires_accepted_evidence_and_rolls_back(factory):
    created = create_product_case(factory)
    service = ProductWorkspaceService(factory)
    with pytest.raises(ProductWorkspaceError, match="must cite accepted evidence"):
        service.append_revision(
            UUID(created["case"]["case_id"]),
            expected_latest_revision_no=1,
            title="Unsupported conclusion",
            research_question="Why?",
            created_by="reviewer-a",
            information_cutoff_date=date(2026, 8, 20),
            workflow_state="completed",
            conclusion_status="supported",
            content={"research_conclusion": "Unsupported"},
            evidence_ids=[],
            recorded_at_utc=NOW,
        )
    assert service.get_case(UUID(created["case"]["case_id"]))["current_revision"]["revision_no"] == 1


def test_stale_revision_and_cross_case_evidence_fail_closed(factory, monkeypatch):
    first = create_product_case(factory)
    evidence_id = accept_document_evidence(factory, monkeypatch, first["case"]["case_id"])
    second = ProductWorkspaceService(factory).create_case(
        case_key="v1-company-other",
        case_type="company",
        title="Other company",
        research_question="What is known?",
        created_by="reviewer-b",
        information_cutoff_date=date(2026, 8, 20),
        content={},
        company_name="Other",
        stock_code="000001",
        recorded_at_utc=NOW,
    )
    service = ProductWorkspaceService(factory)
    with pytest.raises(ProductWorkspaceError) as error:
        service.append_revision(
            UUID(second["case"]["case_id"]),
            expected_latest_revision_no=1,
            title="Other company",
            research_question="What is known?",
            created_by="reviewer-b",
            information_cutoff_date=date(2026, 8, 20),
            workflow_state="open",
            conclusion_status="unassessed",
            content={},
            evidence_ids=[evidence_id],
            recorded_at_utc=NOW,
        )
    assert error.value.code == "evidence_not_accepted"


def test_revision_cannot_bind_evidence_beyond_its_information_cutoff(factory, monkeypatch):
    created = create_product_case(factory)
    evidence_id = accept_document_evidence(factory, monkeypatch, created["case"]["case_id"])
    service = ProductWorkspaceService(factory)
    with pytest.raises(ProductWorkspaceError) as error:
        service.append_revision(
            UUID(created["case"]["case_id"]),
            expected_latest_revision_no=1,
            title="Historical boundary",
            research_question="What was known before the filing?",
            created_by="reviewer-a",
            information_cutoff_date=date(2026, 8, 19),
            workflow_state="open",
            conclusion_status="unassessed",
            content={},
            evidence_ids=[evidence_id],
            recorded_at_utc=NOW,
        )
    assert error.value.code == "evidence_not_accepted"


def test_imported_document_appears_before_review_session(factory, monkeypatch):
    raw = b"%PDF-1.7 imported only"
    page_text = "Local imported evidence awaiting review."
    result = ExtractionResult(
        content_sha256=sha256_hex(raw),
        byte_size=len(raw),
        pages=(ExtractedPage(1, page_text, sha256_hex(page_text.encode()), len(page_text)),),
        embedded_text_page_count=1,
        total_text_char_count=len(page_text),
        extractor_package="pypdf",
        extractor_version="6.14.2",
    )
    monkeypatch.setattr("industry_alpha.document_import_commands.extract_pdf", lambda *_a, **_k: result)
    imported = DocumentImportCommandService(factory).import_pdf(
        pdf_bytes=raw,
        original_filename="awaiting-review.pdf",
        imported_at_utc=NOW,
    )
    DocumentImportCommandService(factory).import_pdf(
        pdf_bytes=raw,
        original_filename="same-content-alias.pdf",
        imported_at_utc=NOW,
    )
    ledger = ProductWorkspaceService(factory).evidence_ledger(status="imported")
    assert ledger["count"] == 1
    item = ledger["items"][0]
    assert item["import_attempt_id"] == str(imported.import_attempt_id)
    assert item["content_fragment"] == "awaiting-review.pdf"


class FakeAIAdapter:
    adapter_version = "test-adapter"

    def __init__(self, *, invalid_citation: bool = False, fail: bool = False) -> None:
        self.invalid_citation = invalid_citation
        self.fail = fail

    def generate(self, **kwargs):
        if self.fail:
            raise GuardedAIProviderError()
        manifest = json.loads(kwargs["canonical_manifest"])
        citation = manifest["accepted_evidence"][0]["manifest_item_id"]
        if self.invalid_citation:
            citation = "evidence:invented"
        sections = {name: [] for name in ALLOWED_SECTION_NAMES}
        sections["evidence_grounded_summary"] = [
            {"text": "Evidence-bound draft.", "manifest_item_ids": [citation]}
        ]
        return GuardedAIAdapterResult(
            raw_content=json.dumps(
                {
                    "schema_version": DRAFT_SCHEMA_VERSION,
                    "manifest_fingerprint": kwargs["manifest_fingerprint"],
                    "sections": sections,
                    "validation_warnings": [],
                }
            )
        )


def ai_payload() -> dict:
    return {
        "case": {"case_id": "case-1", "case_type": "industry"},
        "current_revision": {
            "revision_id": "revision-1",
            "revision_no": 2,
            "title": "Evidence research",
            "research_question": "What is known?",
            "workflow_state": "open",
            "conclusion_status": "unassessed",
            "information_cutoff_date": "2026-08-20",
            "content": {"risks": "Limited coverage."},
            "evidence_references": [
                {
                    "evidence_id": "evidence-1",
                    "source": "Official filing",
                    "document_id": "document-1",
                    "page": 1,
                    "evidence_grade": "A",
                    "content_fragment": "Accepted fact.",
                }
            ],
        },
    }


def ai_config() -> GuardedAIProviderConfig:
    return GuardedAIProviderConfig(
        enabled=True,
        provider_id="local-test-provider",
        endpoint_url="https://example.invalid/v1/chat",
        model_id="test-model",
        api_credential="not-a-real-key",
        data_use_notice="Test fixture only.",
    )


def test_ai_is_evidence_limited_citation_bound_and_failure_is_ephemeral():
    service = ProductWorkspaceAIService(ai_config(), adapter=FakeAIAdapter())
    preview = service.preview(ai_payload())
    assert preview["evidence_reference_count"] == 1
    draft = service.generate(
        ai_payload(),
        expected_manifest_fingerprint=preview["manifest_fingerprint"],
        confirm_remote_transmission=True,
    )
    assert draft["ephemeral_only"] is True
    assert draft["sections"]["evidence_grounded_summary"][0]["manifest_item_ids"] == (
        "evidence:evidence-1",
    )
    with pytest.raises(GuardedAIResponseValidationError):
        ProductWorkspaceAIService(
            ai_config(), adapter=FakeAIAdapter(invalid_citation=True)
        ).generate(
            ai_payload(),
            expected_manifest_fingerprint=preview["manifest_fingerprint"],
            confirm_remote_transmission=True,
        )
    with pytest.raises(GuardedAIProviderError):
        ProductWorkspaceAIService(ai_config(), adapter=FakeAIAdapter(fail=True)).generate(
            ai_payload(),
            expected_manifest_fingerprint=preview["manifest_fingerprint"],
            confirm_remote_transmission=True,
        )
