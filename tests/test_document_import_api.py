from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from backend.api.industry_alpha import get_industry_alpha_session_factory
from backend.api.document_import import _origin
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
from industry_alpha.commands import EvidenceLedgerCommandService
from industry_alpha.document_import_contracts import ExtractedPage, ExtractionResult
from industry_alpha.document_import_models import LocalDocumentImportAttempt
from industry_alpha.document_import_rules import sha256_hex


@pytest.fixture
def api(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    raw = b"%PDF-1.7 API fixture"
    text = "本地逐页文本"
    monkeypatch.setattr(
        "industry_alpha.document_import_commands.extract_pdf",
        lambda *_a, **_k: ExtractionResult(
            content_sha256=sha256_hex(raw),
            byte_size=len(raw),
            pages=(ExtractedPage(1, text, sha256_hex(text.encode()), len(text)),),
            embedded_text_page_count=1,
            total_text_char_count=len(text),
            extractor_package="pypdf",
            extractor_version="6.14.2",
        ),
    )
    app.dependency_overrides[get_industry_alpha_session_factory] = lambda: factory
    with TestClient(app) as client:
        yield client, factory, raw
    app.dependency_overrides.clear()
    engine.dispose()


def test_mutation_rejects_missing_origin_and_csrf_before_import(api):
    client, factory, raw = api
    response = client.post(
        "/api/document-imports?original_filename=a.pdf",
        content=raw,
        headers={"content-type": "application/pdf"},
    )
    assert response.status_code == 403
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(LocalDocumentImportAttempt)) == 0


def test_ipv6_loopback_is_a_valid_local_origin():
    request = Request(
        {
            "type": "http",
            "scheme": "http",
            "server": ("::1", 8000),
            "path": "/api/document-import/csrf",
            "query_string": b"",
            "headers": [(b"host", b"[::1]:8000")],
        }
    )
    assert _origin(request) == "http://[::1]:8000"


def test_csrf_guard_runs_before_json_body_parsing(api):
    client, _, _ = api
    blocked = client.post(
        "/api/document-reviews",
        content=b"{not-json",
        headers={"content-type": "application/json"},
    )
    assert blocked.status_code == 403

    token = client.get("/api/document-import/csrf").json()["csrf_token"]
    parsed = client.post(
        "/api/document-reviews",
        content=b"{not-json",
        headers={
            "content-type": "application/json",
            "origin": "http://testserver",
            "x-aquantai-csrf": token,
        },
    )
    assert parsed.status_code == 422


def test_local_upload_pages_and_attachment_are_exact(api):
    client, _, raw = api
    token_response = client.get("/api/document-import/csrf")
    assert token_response.status_code == 200
    token = token_response.json()["csrf_token"]
    response = client.post(
        "/api/document-imports?original_filename=%E5%85%AC%E5%91%8A.pdf",
        content=raw,
        headers={
            "content-type": "application/pdf",
            "origin": "http://testserver",
            "x-aquantai-csrf": token,
        },
    )
    assert response.status_code == 200
    imported = response.json()
    detail = client.get(f"/api/document-imports/{imported['import_attempt_id']}")
    assert detail.json()["page_count"] == 1
    pages = client.get(f"/api/document-contents/{imported['content_id']}/pages")
    assert pages.json()["pages"][0]["extracted_text"] == "本地逐页文本"
    attachment = client.get(f"/api/document-contents/{imported['content_id']}/pdf")
    assert attachment.content == raw
    assert attachment.headers["content-disposition"] == 'attachment; filename="document.pdf"'
    assert attachment.headers["x-content-type-options"] == "nosniff"


def test_review_preview_commit_and_exact_receipt_reopen_over_http(api):
    client, factory, raw = api
    case = EvidenceLedgerCommandService(factory).create_case(
        case_key="document-api-golden-path",
        title="本地 PDF HTTP 审核",
        research_question="这份文档有哪些可引用事实？",
        information_cutoff_date=date(2026, 8, 5),
        recorded_at_utc=datetime(2026, 8, 5, 8, tzinfo=timezone.utc),
    )
    token = client.get("/api/document-import/csrf").json()["csrf_token"]
    headers = {
        "content-type": "application/json",
        "origin": "http://testserver",
        "x-aquantai-csrf": token,
    }
    imported = client.post(
        "/api/document-imports?original_filename=official.pdf",
        content=raw,
        headers={**headers, "content-type": "application/pdf"},
    ).json()
    recorded = "2026-08-05T09:00:00Z"
    review_response = client.post(
        "/api/document-reviews",
        headers=headers,
        json={
            "import_attempt_id": imported["import_attempt_id"],
            "target_research_case_id": str(case.id),
            "created_at_utc": recorded,
        },
    )
    assert review_response.status_code == 200
    review_id = review_response.json()["review_session_id"]

    def candidate(body):
        response = client.post(
            f"/api/document-reviews/{review_id}/candidates",
            headers=headers,
            json={**body, "recorded_at_utc": recorded},
        )
        assert response.status_code == 200
        return response.json()["candidate_id"]

    document_id = candidate(
        {
            "candidate_kind": "document_identity",
            "payload": {
                "identity_namespace": "user_defined_document",
                "identity_key": "api-official-2026-08",
                "document_title": "HTTP 官方文档",
                "publisher_or_author": "示例发布者",
                "document_date": "2026-08-05",
                "document_kind": "announcement",
            },
        }
    )
    subject_id = candidate(
        {
            "candidate_kind": "company_identity",
            "payload": {
                "subject_kind": "not_company_specific",
                "display_label": "非特定公司",
            },
        }
    )
    quote = "本地逐页文本"
    fact_id = candidate(
        {
            "candidate_kind": "fact",
            "payload": {},
            "page_number": 1,
            "start_utf8_byte": 0,
            "end_utf8_byte": len(quote.encode("utf-8")),
            "quote_text": quote,
            "quote_sha256": sha256_hex(quote.encode("utf-8")),
            "statement": "该文档包含经过人工选择的逐页事实。",
        }
    )
    revision_response = client.post(
        f"/api/document-reviews/{review_id}/revisions",
        headers=headers,
        json={
            "expected_previous_revision_number": 0,
            "review_state": "draft",
            "source_kind": "official",
            "evidence_grade": "A",
            "document_identity_candidate_id": document_id,
            "subject_candidate_id": subject_id,
            "information_date": "2026-08-05",
            "recorded_at_utc": recorded,
            "decisions": [
                {"candidate_id": document_id, "decision": "selected"},
                {"candidate_id": subject_id, "decision": "selected"},
                {
                    "candidate_id": fact_id,
                    "decision": "selected",
                    "claim_status": "supported",
                    "evidence_relation": "supports",
                },
            ],
        },
    )
    assert revision_response.status_code == 200
    revision = revision_response.json()
    exact = client.get(
        f"/api/document-reviews/{review_id}",
        params={"review_revision_id": revision["review_revision_id"]},
    ).json()
    decision = next(
        row
        for row in exact["revisions"][0]["candidate_decisions"]
        if row["candidate_id"] == fact_id
    )
    acceptance = {
        "source_review_revision_id": revision["review_revision_id"],
        "expected_source_review_revision_number": revision["revision_number"],
        "expected_source_review_fingerprint_sha256": revision[
            "review_fingerprint_sha256"
        ],
        "expected_session_latest_revision_number": revision["revision_number"],
        "target_research_case_id": str(case.id),
        "selected_candidate_ids": [fact_id],
        "selected_decision_fingerprints": [
            decision["decision_fingerprint_sha256"]
        ],
        "recorded_at_utc": "2026-08-05T10:00:00Z",
        "acceptance_plan_fingerprint_sha256": "0" * 64,
    }
    preview = client.post(
        f"/api/document-reviews/{review_id}/acceptance-preview",
        headers=headers,
        json=acceptance,
    )
    assert preview.status_code == 200
    assert preview.json()["receipt_id"] is None
    acceptance["acceptance_plan_fingerprint_sha256"] = preview.json()[
        "acceptance_plan_fingerprint_sha256"
    ]
    committed = client.post(
        f"/api/document-reviews/{review_id}/acceptance-commit",
        headers=headers,
        json=acceptance,
    )
    assert committed.status_code == 200
    receipt_id = committed.json()["receipt_id"]
    reopened = client.get(
        f"/api/document-acceptances/{receipt_id}",
        params={
            "information_cutoff_date": "2026-08-05",
            "recorded_at_utc": acceptance["recorded_at_utc"],
        },
    )
    assert reopened.status_code == 200
    assert reopened.json()["receipt_id"] == receipt_id
    assert reopened.json()["links"][0]["candidate_id"] == fact_id
