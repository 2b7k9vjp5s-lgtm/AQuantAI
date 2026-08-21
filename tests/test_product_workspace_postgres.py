from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import os
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url

from backend.database.engine import build_session_factory
from industry_alpha.models import ResearchCaseRevision
from industry_alpha.product_workspace import ProductWorkspaceError, ProductWorkspaceService


@pytest.fixture
def postgres_factory():
    database_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    if "test" not in (make_url(database_url).database or "").lower():
        pytest.fail("TEST_DATABASE_URL must target a database whose name contains 'test'.")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260821_0020"
    try:
        yield build_session_factory(engine), engine
    finally:
        engine.dispose()


def test_postgres_competing_product_revisions_have_one_stable_winner(
    postgres_factory,
) -> None:
    factory, engine = postgres_factory
    key = f"postgres-product-{uuid4()}"
    service = ProductWorkspaceService(factory)
    created = service.create_case(
        case_key=key,
        case_type="industry",
        title="PostgreSQL product case",
        research_question="Which concurrent revision is accepted?",
        created_by="postgres-test",
        information_cutoff_date=date(2026, 8, 21),
        content={},
        industry_theme="Concurrency",
        recorded_at_utc=datetime(2026, 8, 21, 10, tzinfo=timezone.utc),
    )
    case_id = UUID(created["case"]["case_id"])
    try:
        def append(label: str):
            try:
                return ProductWorkspaceService(factory).append_revision(
                    case_id,
                    expected_latest_revision_no=1,
                    title=f"Concurrent revision {label}",
                    research_question="Which concurrent revision is accepted?",
                    created_by="postgres-test",
                    information_cutoff_date=date(2026, 8, 21),
                    workflow_state="open",
                    conclusion_status="unassessed",
                    content={"watch_items": label},
                    evidence_ids=[],
                    recorded_at_utc=datetime(2026, 8, 21, 11, tzinfo=timezone.utc),
                )
            except ProductWorkspaceError as exc:
                return exc

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = tuple(executor.map(append, ("A", "B")))

        assert sum(isinstance(item, dict) for item in outcomes) == 1
        errors = [item for item in outcomes if isinstance(item, ProductWorkspaceError)]
        assert len(errors) == 1
        assert errors[0].code == "stale_revision"
        with factory() as session:
            assert list(
                session.scalars(
                    select(ResearchCaseRevision.revision_no)
                    .where(ResearchCaseRevision.case_id == case_id)
                    .order_by(ResearchCaseRevision.revision_no)
                )
            ) == [1, 2]
    finally:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "DELETE FROM product_research_revision_contents "
                    "WHERE revision_id IN (SELECT id FROM research_case_revisions WHERE case_id = :case_id)"
                ),
                {"case_id": case_id},
            )
            connection.execute(
                text("DELETE FROM research_case_revisions WHERE case_id = :case_id"),
                {"case_id": case_id},
            )
            connection.execute(
                text("DELETE FROM product_research_case_profiles WHERE case_id = :case_id"),
                {"case_id": case_id},
            )
            connection.execute(
                text("DELETE FROM research_cases WHERE id = :case_id"),
                {"case_id": case_id},
            )
