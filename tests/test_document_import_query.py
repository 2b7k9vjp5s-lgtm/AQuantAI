from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.document_import_models import LocalDocumentContent, LocalDocumentPage
from industry_alpha.document_import_query import DocumentImportQueryService


def test_metadata_and_page_reads_do_not_materialize_raw_pdf_bytes():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    with factory.begin() as session:
        content = LocalDocumentContent(
            content_sha256="b" * 64,
            media_type="application/pdf",
            byte_size=4,
            raw_pdf_bytes=b"blob",
            page_count=1,
            embedded_text_page_count=1,
            total_text_char_count=4,
            extractor_contract_version="aquantai.local-pdf-embedded-text.v1",
            extractor_package="pypdf",
            extractor_version="6.14.2",
            created_at_utc=datetime(2026, 8, 4, tzinfo=timezone.utc),
        )
        session.add(content)
        session.flush()
        session.add(
            LocalDocumentPage(
                content_id=content.id,
                page_number=1,
                text_state="embedded_text_present",
                extracted_text="text",
                text_sha256="c" * 64,
                text_char_count=4,
            )
        )
        content_id = content.id
    statements: list[str] = []

    def record(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.lower())

    event.listen(engine, "before_cursor_execute", record)
    result = DocumentImportQueryService(factory).page_batch(content_id)
    event.remove(engine, "before_cursor_execute", record)
    assert result["pages"][0]["extracted_text"] == "text"
    assert len(statements) == 2
    assert all("raw_pdf_bytes" not in statement for statement in statements)
    assert DocumentImportQueryService(factory).attachment(content_id) == b"blob"
    engine.dispose()


def test_page_batches_are_capped_and_expose_a_stable_next_cursor():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    with factory.begin() as session:
        content = LocalDocumentContent(
            content_sha256="d" * 64,
            media_type="application/pdf",
            byte_size=4,
            raw_pdf_bytes=b"blob",
            page_count=31,
            embedded_text_page_count=31,
            total_text_char_count=62,
            extractor_contract_version="aquantai.local-pdf-embedded-text.v1",
            extractor_package="pypdf",
            extractor_version="6.14.2",
            created_at_utc=datetime(2026, 8, 4, tzinfo=timezone.utc),
        )
        session.add(content)
        session.flush()
        session.add_all(
            LocalDocumentPage(
                content_id=content.id,
                page_number=number,
                text_state="embedded_text_present",
                extracted_text=f"p{number}",
                text_sha256=f"{number:064x}",
                text_char_count=len(f"p{number}"),
            )
            for number in range(1, 32)
        )
        content_id = content.id
    first = DocumentImportQueryService(factory).page_batch(
        content_id, limit=100
    )
    assert len(first["pages"]) == 30
    assert first["next_after_page"] == 30
    final = DocumentImportQueryService(factory).page_batch(
        content_id, after_page=30, limit=30
    )
    assert [row["page_number"] for row in final["pages"]] == [31]
    assert final["next_after_page"] is None
    engine.dispose()
