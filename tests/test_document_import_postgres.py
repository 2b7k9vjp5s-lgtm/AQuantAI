from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
import os
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


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
        connection.execute(text("TRUNCATE local_document_contents CASCADE"))
    engine.dispose()
    command.downgrade(config, "base")


def test_postgres_schema_and_populated_downgrade_stop(postgres_database_url):
    engine = create_engine(postgres_database_url)
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
    engine.dispose()
