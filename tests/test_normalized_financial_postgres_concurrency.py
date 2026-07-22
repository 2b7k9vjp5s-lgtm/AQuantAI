from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import os

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url

from backend.database import build_engine, build_session_factory
from backend.database.canonical_price import CanonicalPriceCommandService
from industry_alpha.normalized_financial_rules import NormalizedMetricError
from industry_alpha.normalized_valuation_models import (
    StructuredFinancialObservation,
    StructuredFinancialObservationRevision,
)
from industry_alpha.normalized_valuation_service import NormalizedValuationCommandService
from industry_alpha.stage2_expectations_fixtures import (
    build_stage2_expectation_valuation_fixture,
)
from industry_alpha.stage2_models import Stage2CompanyResearch, Stage2CompanyResearchRevision


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
    command.downgrade(config, "base")


@pytest.fixture(autouse=True)
def clean_database(postgres_database_url: str) -> Iterator[None]:
    engine = build_engine(postgres_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("TRUNCATE research_cases, listed_instruments RESTART IDENTITY CASCADE")
            )
        yield
    finally:
        engine.dispose()


def test_same_identity_concurrent_first_observation_has_one_winner(
    postgres_database_url: str,
) -> None:
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    try:
        fixture = build_stage2_expectation_valuation_fixture(factory)
        with factory() as session:
            research = session.get(
                Stage2CompanyResearch, fixture.stage2.supported_research_id
            )
            research_revision = session.scalar(
                select(Stage2CompanyResearchRevision).where(
                    Stage2CompanyResearchRevision.company_research_id == research.id,
                    Stage2CompanyResearchRevision.revision_no == 3,
                )
            )
        assert research is not None
        assert research_revision is not None

        instrument = CanonicalPriceCommandService(factory).record_listed_instrument(
            {
                "instrument_key": "normalized-concurrency-instrument",
                "expected_latest_revision_id": None,
                "canonical_symbol": research.stock_code,
                "security_type": "common_equity",
                "market_code": "CN_A",
                "exchange_code_namespace": "ISO_MIC",
                "exchange_code": "XSHE",
                "currency_code": "CNY",
                "listing_date": "2000-01-01",
                "delisting_date": None,
                "listing_status": "active",
                "recorded_by": "concurrency-test",
                "information_cutoff_date": "2026-07-22",
                "recorded_at_utc": "2026-07-22T20:00:00Z",
            }
        )
        payload = {
            "observation_key": "concurrent-first-revenue-fy2027",
            "company_research_id": str(research.id),
            "company_research_revision_id": str(research_revision.id),
            "instrument_id": instrument["instrument_id"],
            "instrument_revision_id": instrument["instrument_revision_id"],
            "metric_code": "revenue",
            "source_kind": "research_assumption",
            "observation_state": "supported",
            "value_text": "12000000000",
            "currency_code": "CNY",
            "unit_code": "currency_amount",
            "period_basis": "forward_fy1",
            "target_period_key": "FY2027",
            "accounting_scope": "consolidated",
            "observation_as_of_date": "2026-07-22",
            "period_start_date": "2027-01-01",
            "period_end_date": "2027-12-31",
            "fiscal_year": 2027,
            "effective_start_date": None,
            "effective_end_date": None,
            "rationale": "Explicit concurrent analyst assumption.",
            "falsification_condition": "Reported FY2027 revenue differs materially.",
            "information_cutoff_date": "2026-07-22",
            "recorded_at_utc": "2026-07-22T21:00:00Z",
            "recorded_by": "concurrency-test",
            "expected_latest_revision_id": None,
            "claim_revision_ids": [],
            "evidence_links": [],
        }

        barrier = Barrier(2)

        def record() -> tuple[str, str | None]:
            barrier.wait()
            try:
                result = NormalizedValuationCommandService(factory).record_observation(
                    dict(payload)
                )
                return "success", result["revision_id"]
            except NormalizedMetricError as exc:
                return exc.code, None

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _index: record(), range(2)))

        assert sorted(code for code, _revision in outcomes) == [
            "normalized_metric_revision_conflict",
            "success",
        ]
        with factory() as session:
            assert session.scalar(
                select(func.count()).select_from(StructuredFinancialObservation)
            ) == 1
            assert session.scalar(
                select(func.count()).select_from(StructuredFinancialObservationRevision)
            ) == 1
    finally:
        engine.dispose()
