from __future__ import annotations

from datetime import datetime, timezone
import importlib

import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.document_import_models import LocalDocumentContent
from industry_alpha.errors import EvidenceLedgerImmutableError


migration = importlib.import_module(
    "migrations.versions.20260803_0018_manual_official_pdf_import"
)


class _Result:
    def __init__(self, populated: bool) -> None:
        self.populated = populated

    def first(self):
        return object() if self.populated else None


class _Operation:
    def __init__(self, populated: bool) -> None:
        self.populated = populated
        self.drops: list[str] = []

    def get_bind(self):
        return self

    def execute(self, _statement):
        return _Result(self.populated)

    def drop_table(self, name: str) -> None:
        self.drops.append(name)


def test_document_schema_contains_only_reviewed_tables_and_deferred_blob():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    names = set(inspect(engine).get_table_names())
    assert {
        "local_document_contents",
        "local_document_import_attempts",
        "local_document_pages",
        "local_document_review_sessions",
        "local_document_candidates",
        "local_document_review_revisions",
        "local_document_review_candidate_decisions",
        "local_document_acceptance_receipts",
        "local_document_acceptance_links",
    } <= names
    assert LocalDocumentContent.raw_pdf_bytes.property.deferred is True
    engine.dispose()


def test_document_rows_are_append_only():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    with factory.begin() as session:
        content = LocalDocumentContent(
            content_sha256="a" * 64,
            media_type="application/pdf",
            byte_size=1,
            raw_pdf_bytes=b"x",
            page_count=1,
            embedded_text_page_count=1,
            total_text_char_count=1,
            extractor_contract_version="contract",
            extractor_package="pypdf",
            extractor_version="6.14.2",
            created_at_utc=datetime(2026, 8, 4, tzinfo=timezone.utc),
        )
        session.add(content)
    with factory() as session:
        row = session.scalar(select(LocalDocumentContent))
        row.extractor_version = "changed"
        with pytest.raises(EvidenceLedgerImmutableError):
            session.flush()
        session.rollback()
    with factory() as session:
        row = session.scalar(select(LocalDocumentContent))
        session.delete(row)
        with pytest.raises(EvidenceLedgerImmutableError):
            session.flush()
    engine.dispose()


def test_populated_migration_downgrade_refuses_before_any_drop(monkeypatch):
    operation = _Operation(populated=True)
    monkeypatch.setattr(migration, "op", operation)
    with pytest.raises(RuntimeError, match="Cannot downgrade local document import"):
        migration.downgrade()
    assert operation.drops == []


def test_empty_migration_downgrade_drops_exact_nine_tables(monkeypatch):
    operation = _Operation(populated=False)
    monkeypatch.setattr(migration, "op", operation)
    migration.downgrade()
    assert operation.drops == list(migration._TABLES)
    assert len(operation.drops) == 9
