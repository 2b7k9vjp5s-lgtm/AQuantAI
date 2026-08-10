from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select, update
from sqlalchemy.pool import StaticPool

from backend.api.industry_alpha import get_industry_alpha_session_factory
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
from industry_alpha.commands import (
    CaseClaimInput,
    EvidenceLedgerCommandService,
    EvidenceLinkInput,
)
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
    LocalDocumentCandidate,
    LocalDocumentReviewCandidateDecision,
)
from industry_alpha.document_import_rules import sha256_hex
from industry_alpha.models import ClaimRevision, EvidenceItem
from industry_alpha.research_evidence_pack_contracts import (
    EvidencePackRequest,
    ResearchEvidencePackError,
)
from industry_alpha.research_evidence_pack_query import ResearchEvidencePackQueryService


INFO_DATE = date(2026, 8, 5)


def _utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 5, hour, minute, tzinfo=timezone.utc)


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


def _claim_revision_id(factory, claim_id: UUID) -> UUID:
    with factory() as session:
        return session.scalar(
            select(ClaimRevision.id).where(
                ClaimRevision.claim_id == claim_id,
                ClaimRevision.revision_no == 1,
            )
        )


def _build_golden_graph(factory, monkeypatch):
    ledger = EvidenceLedgerCommandService(factory)
    documents = DocumentImportCommandService(factory)
    case = ledger.create_case(
        case_key=f"research-evidence-pack-{uuid4()}",
        title="研究证据包",
        research_question="哪些证据属于精确历史研究快照？",
        information_cutoff_date=INFO_DATE,
        recorded_at_utc=_utc(8),
    )

    raw = b"%PDF-1.7 research evidence pack fixture"
    page_text = "第一页包含本地文档事实与精确引用。"
    monkeypatch.setattr(
        "industry_alpha.document_import_commands.extract_pdf",
        lambda *_args, **_kwargs: ExtractionResult(
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
        ),
    )
    imported = documents.import_pdf(
        pdf_bytes=raw,
        original_filename="evidence-pack.pdf",
        imported_at_utc=_utc(9),
    )
    review = documents.create_review_session(
        import_attempt_id=imported.import_attempt_id,
        target_research_case_id=case.id,
        created_at_utc=_utc(9),
    )
    document = documents.add_candidate(
        review.id,
        CandidateInput(
            candidate_kind="document_identity",
            payload={
                "identity_namespace": "user_defined_document",
                "identity_key": "evidence-pack-official",
                "document_title": "证据包官方文档",
                "publisher_or_author": "测试发布者",
                "document_date": INFO_DATE.isoformat(),
                "document_kind": "announcement",
            },
            recorded_at_utc=_utc(9),
        ),
    )
    subject = documents.add_candidate(
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
    quote = "本地文档事实"
    quote_bytes = quote.encode("utf-8")
    start = page_text.encode("utf-8").index(quote_bytes)
    fact = documents.add_candidate(
        review.id,
        CandidateInput(
            candidate_kind="fact",
            payload={},
            page_number=1,
            start_utf8_byte=start,
            end_utf8_byte=start + len(quote_bytes),
            quote_text=quote,
            quote_sha256=sha256_hex(quote_bytes),
            statement="该本地文档事实经过人工审核并接受。",
            recorded_at_utc=_utc(9),
        ),
    )
    decisions = (
        DecisionInput(document.id, "selected"),
        DecisionInput(subject.id, "selected"),
        DecisionInput(
            fact.id,
            "selected",
            claim_status="supported",
            evidence_relation="supports",
        ),
    )
    first_review = documents.append_review_revision(
        review.id,
        ReviewRevisionInput(
            expected_previous_revision_number=0,
            review_state="draft",
            source_kind="official",
            evidence_grade="A",
            document_identity_candidate_id=document.id,
            subject_candidate_id=subject.id,
            information_date=INFO_DATE,
            decisions=decisions,
            reviewer_note="第一轮审核",
            recorded_at_utc=_utc(10),
        ),
    )
    source_review = documents.append_review_revision(
        review.id,
        ReviewRevisionInput(
            expected_previous_revision_number=first_review.revision_number,
            review_state="deferred",
            source_kind="official",
            evidence_grade="A",
            document_identity_candidate_id=document.id,
            subject_candidate_id=subject.id,
            information_date=INFO_DATE,
            decisions=decisions,
            reviewer_note="第二轮审核",
            recorded_at_utc=_utc(10, 15),
        ),
    )
    with factory() as session:
        decision_fingerprint = session.scalar(
            select(LocalDocumentReviewCandidateDecision.decision_fingerprint_sha256).where(
                LocalDocumentReviewCandidateDecision.review_revision_id == source_review.id,
                LocalDocumentReviewCandidateDecision.candidate_id == fact.id,
            )
        )
    draft = AcceptanceInput(
        source_review_revision_id=source_review.id,
        expected_source_review_revision_number=source_review.revision_number,
        expected_source_review_fingerprint_sha256=source_review.review_fingerprint_sha256,
        expected_session_latest_revision_number=source_review.revision_number,
        target_research_case_id=case.id,
        selected_candidate_ids=(fact.id,),
        selected_decision_fingerprints=(decision_fingerprint,),
        recorded_at_utc=_utc(11),
        acceptance_plan_fingerprint_sha256="0" * 64,
    )
    preview = ledger.preview_reviewed_local_document(draft)
    accepted = ledger.accept_reviewed_local_document(
        replace(
            draft,
            acceptance_plan_fingerprint_sha256=preview.acceptance_plan_fingerprint_sha256,
        )
    )
    with factory() as session:
        acceptance_link = session.scalar(
            select(LocalDocumentAcceptanceLink).where(
                LocalDocumentAcceptanceLink.receipt_id == accepted.receipt_id
            )
        )
    local_evidence_id = acceptance_link.evidence_item_id
    local_claim_revision_id = acceptance_link.claim_revision_id

    unlinked_claim = ledger.create_claim(
        case.id,
        claim_key="mixed-unlinked-binding",
        statement="同一证据的另一个尚未进入所选研究快照的 Claim。",
        claim_kind="fact",
        claim_status="draft",
        information_cutoff_date=INFO_DATE,
        evidence_links=(EvidenceLinkInput(local_evidence_id, "context"),),
        recorded_at_utc=_utc(11, 10),
    )
    unlinked_claim_revision_id = _claim_revision_id(factory, unlinked_claim.id)

    ledger_only_evidence = ledger.add_evidence(
        case.id,
        evidence_grade="B",
        source_kind="research",
        source_title="普通 Ledger 证据",
        information_date=INFO_DATE,
        summary="这条证据没有本地文档接受链接。",
        source_locator="local-document:looks-similar-but-is-not-authority",
        content_fingerprint=f"ledger-only-{uuid4()}",
        recorded_at_utc=_utc(11, 20),
    )
    ledger_only_claim = ledger.create_claim(
        case.id,
        claim_key="ledger-only-supported",
        statement="普通 Ledger Claim。",
        claim_kind="fact",
        claim_status="supported",
        information_cutoff_date=INFO_DATE,
        evidence_links=(EvidenceLinkInput(ledger_only_evidence.id, "supports"),),
        recorded_at_utc=_utc(11, 30),
    )
    ledger_only_claim_revision_id = _claim_revision_id(factory, ledger_only_claim.id)

    selected_revision = ledger.append_case_revision(
        case.id,
        title="冻结研究快照",
        research_question="精确证据包如何重开？",
        summary="只链接部分 ClaimRevision。",
        workflow_state="open",
        conclusion_status="unassessed",
        information_cutoff_date=INFO_DATE,
        claim_links=(
            CaseClaimInput(local_claim_revision_id, "conclusion"),
            CaseClaimInput(ledger_only_claim_revision_id, "context"),
        ),
        recorded_at_utc=_utc(12),
    )
    return {
        "case_id": case.id,
        "case_revision_id": selected_revision.id,
        "local_evidence_id": local_evidence_id,
        "ledger_only_evidence_id": ledger_only_evidence.id,
        "unlinked_claim_revision_id": unlinked_claim_revision_id,
        "candidate_id": fact.id,
    }


def _request(graph, *, limit: int = 50, cursor: str | None = None):
    return EvidencePackRequest(
        research_case_id=graph["case_id"],
        research_case_revision_id=graph["case_revision_id"],
        information_cutoff_date=INFO_DATE,
        recorded_at_utc=_utc(12),
        limit=limit,
        cursor=cursor,
    )


def test_golden_pack_preserves_mixed_membership_and_exact_provenance(
    session_factory, monkeypatch
):
    graph = _build_golden_graph(session_factory, monkeypatch)
    before = None
    with session_factory() as session:
        before = (
            session.scalar(select(func.count()).select_from(EvidenceItem)),
            session.scalar(select(func.count()).select_from(ClaimRevision)),
        )
    payload = ResearchEvidencePackQueryService(session_factory).get_pack(
        _request(graph)
    ).to_dict()
    with session_factory() as session:
        after = (
            session.scalar(select(func.count()).select_from(EvidenceItem)),
            session.scalar(select(func.count()).select_from(ClaimRevision)),
        )
    assert before == after
    assert payload["contract_version"] == "aquantai.research-evidence-pack.v1"
    assert payload["visible_evidence_count"] == 2
    assert payload["notices"]["writes_per_get"] == 0
    assert payload["notices"]["network_calls"] == 0
    assert payload["notices"]["ocr_calls"] == 0
    assert payload["notices"]["ai_calls"] == 0

    entries = {UUID(row["evidence"]["evidence_id"]): row for row in payload["entries"]}
    local = entries[graph["local_evidence_id"]]
    assert "research_membership_state" not in local
    assert local["membership_summary"] == "mixed_linked_and_unlinked_bindings"
    assert {
        row["research_membership_state"] for row in local["claim_bindings"]
    } == {
        "linked_to_selected_case_revision",
        "accepted_unlinked_to_selected_case_revision",
    }
    assert local["integrity_state"] == "validated_local_document"
    provenance = local["local_document_provenance"]
    assert provenance["candidate_id"] == str(graph["candidate_id"])
    assert provenance["quote_text"] == "本地文档事实"
    assert "extracted_text" not in provenance
    assert "raw_pdf_bytes" not in provenance

    ledger_only = entries[graph["ledger_only_evidence_id"]]
    assert ledger_only["local_document_provenance"] is None
    assert ledger_only["integrity_state"] == "ledger_only"
    assert ledger_only["membership_summary"] == "all_bindings_linked"


def test_cursor_is_request_bound_stable_and_duplicate_free(session_factory, monkeypatch):
    graph = _build_golden_graph(session_factory, monkeypatch)
    service = ResearchEvidencePackQueryService(session_factory)
    first = service.get_pack(_request(graph, limit=1)).to_dict()
    assert len(first["entries"]) == 1
    assert first["next_cursor"] is not None
    first_id = first["entries"][0]["evidence"]["evidence_id"]
    second = service.get_pack(
        _request(graph, limit=1, cursor=first["next_cursor"])
    ).to_dict()
    assert len(second["entries"]) == 1
    assert second["entries"][0]["evidence"]["evidence_id"] != first_id
    assert second["next_cursor"] is None

    with pytest.raises(ResearchEvidencePackError) as error:
        service.get_pack(_request(graph, limit=2, cursor=first["next_cursor"]))
    assert error.value.code == "invalid_evidence_pack_cursor"
    with pytest.raises(ResearchEvidencePackError) as error:
        service.get_pack(_request(graph, limit=1, cursor=first["next_cursor"] + "x"))
    assert error.value.code == "invalid_evidence_pack_cursor"


@pytest.mark.parametrize("limit", [1, 50, 100])
def test_sql_statement_ceiling_is_at_most_eight(
    session_factory, monkeypatch, limit
):
    graph = _build_golden_graph(session_factory, monkeypatch)
    engine = session_factory.kw["bind"]
    statements: list[str] = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        ResearchEvidencePackQueryService(session_factory).get_pack(
            _request(graph, limit=limit)
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert 1 <= len(statements) <= 8


def test_candidate_fingerprint_corruption_fails_entire_pack(session_factory, monkeypatch):
    graph = _build_golden_graph(session_factory, monkeypatch)
    with session_factory.begin() as session:
        session.execute(
            update(LocalDocumentCandidate)
            .where(LocalDocumentCandidate.id == graph["candidate_id"])
            .values(candidate_fingerprint_sha256="0" * 64)
        )
    with pytest.raises(ResearchEvidencePackError) as error:
        ResearchEvidencePackQueryService(session_factory).get_pack(_request(graph))
    assert error.value.code == "evidence_pack_integrity_error"


def test_anchor_mismatch_and_visibility_fail_without_fallback(session_factory, monkeypatch):
    graph = _build_golden_graph(session_factory, monkeypatch)
    other = EvidenceLedgerCommandService(session_factory).create_case(
        case_key=f"other-{uuid4()}",
        title="其他 Case",
        research_question="不得推断替代 revision",
        information_cutoff_date=INFO_DATE,
        recorded_at_utc=_utc(8),
    )
    service = ResearchEvidencePackQueryService(session_factory)
    mismatch = replace(_request(graph), research_case_id=other.id)
    with pytest.raises(ResearchEvidencePackError) as error:
        service.get_pack(mismatch)
    assert error.value.code == "research_case_revision_mismatch"
    invisible = replace(_request(graph), recorded_at_utc=_utc(11, 59))
    with pytest.raises(ResearchEvidencePackError) as error:
        service.get_pack(invisible)
    assert error.value.code == "research_case_revision_not_visible_as_of"


def test_http_adapter_is_local_only_and_returns_stable_contract(session_factory, monkeypatch):
    graph = _build_golden_graph(session_factory, monkeypatch)
    app.dependency_overrides[get_industry_alpha_session_factory] = lambda: session_factory
    path = (
        f"/research-evidence-pack/api/cases/{graph['case_id']}"
        f"/revisions/{graph['case_revision_id']}"
    )
    try:
        with TestClient(app) as client:
            blocked = client.get(
                path,
                headers={"host": "192.168.1.20"},
                params={
                    "information_cutoff_date": INFO_DATE.isoformat(),
                    "recorded_at_utc": "2026-08-05T12:00:00Z",
                },
            )
            assert blocked.status_code == 403
            response = client.get(
                path,
                params={
                    "information_cutoff_date": INFO_DATE.isoformat(),
                    "recorded_at_utc": "2026-08-05T12:00:00Z",
                    "limit": 100,
                },
            )
            assert response.status_code == 200
            assert response.json()["contract_version"] == "aquantai.research-evidence-pack.v1"
    finally:
        app.dependency_overrides.clear()
