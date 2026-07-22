from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from backend.database.models import Base
from backend.main import app
from industry_alpha.errors import EvidenceLedgerImmutableError
from industry_alpha.normalized_valuation_models import (
    NormalizedValuationMetric,
    NormalizedValuationMetricInputLink,
    NormalizedValuationMetricRevision,
)
from industry_alpha.normalized_valuation_query import NormalizedValuationQueryService

UTC = timezone.utc


@pytest.fixture()
def database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    try:
        yield engine, factory
    finally:
        engine.dispose()


def seed_metric(factory):
    metric_id = uuid4()
    revision_id = uuid4()
    instrument_id = uuid4()
    instrument_revision_id = uuid4()
    recorded = datetime(2026, 7, 22, 10, tzinfo=UTC)
    with factory.begin() as session:
        session.add(
            NormalizedValuationMetric(
                id=metric_id,
                metric_key="query-count-pe-2026-06-30",
                instrument_id=instrument_id,
                metric_code="pe",
                valuation_as_of_date=date(2026, 6, 30),
                target_period_key="TTM-2026-06-20",
                period_basis="ttm",
                accounting_scope="consolidated_attributable",
                formula_version="aquantai.normalized-valuation.v1",
                created_at_utc=recorded,
            )
        )
        session.add(
            NormalizedValuationMetricRevision(
                id=revision_id,
                metric_id=metric_id,
                revision_no=1,
                instrument_revision_id=instrument_revision_id,
                calculation_state="calculated",
                normalized_value="10.0000",
                equity_value="20000000000.000000",
                enterprise_value=None,
                currency_code="CNY",
                output_unit_code="multiple",
                price_trade_date=date(2026, 6, 30),
                financial_period_end_date=date(2026, 6, 20),
                reason_codes=[],
                information_cutoff_date=date(2026, 7, 22),
                recorded_at_utc=recorded,
                recorded_by="query-test",
                supersedes_revision_id=None,
            )
        )
        session.add_all(
            [
                NormalizedValuationMetricInputLink(
                    metric_revision_id=revision_id,
                    position=0,
                    input_role="canonical_price",
                    canonical_price_revision_id=uuid4(),
                    recorded_at_utc=recorded,
                ),
                NormalizedValuationMetricInputLink(
                    metric_revision_id=revision_id,
                    position=1,
                    input_role="price_eligibility",
                    comparison_eligibility_revision_id=uuid4(),
                    recorded_at_utc=recorded,
                ),
                NormalizedValuationMetricInputLink(
                    metric_revision_id=revision_id,
                    position=2,
                    input_role="diluted_shares",
                    financial_observation_revision_id=uuid4(),
                    recorded_at_utc=recorded,
                ),
                NormalizedValuationMetricInputLink(
                    metric_revision_id=revision_id,
                    position=3,
                    input_role="financial_denominator",
                    financial_observation_revision_id=uuid4(),
                    recorded_at_utc=recorded,
                ),
            ]
        )
    return metric_id, revision_id


def test_exact_metric_read_is_bounded_and_exposes_formula_inputs(database) -> None:
    engine, factory = database
    _metric_id, revision_id = seed_metric(factory)
    statements = 0

    def count_statement(*_args):
        nonlocal statements
        statements += 1

    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        with factory() as session:
            payload = NormalizedValuationQueryService(session).get_metric_revision(
                revision_id,
                as_of_cutoff=date(2026, 7, 22),
                as_of_recorded_at_utc=datetime(2026, 7, 22, 10, tzinfo=UTC),
            )
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)

    assert statements == 3
    assert statements <= 18
    assert payload["normalized_value_text"] == "10.0000"
    assert payload["formula_version"] == "aquantai.normalized-valuation.v1"
    assert [item["input_role"] for item in payload["inputs"]] == [
        "canonical_price",
        "price_eligibility",
        "diluted_shares",
        "financial_denominator",
    ]


def test_normalized_metric_histories_are_append_only(database) -> None:
    _engine, factory = database
    metric_id, _revision_id = seed_metric(factory)
    with pytest.raises(EvidenceLedgerImmutableError):
        with factory.begin() as session:
            row = session.get(NormalizedValuationMetric, metric_id)
            row.metric_key = "changed"


def test_chinese_context_page_is_read_only_safe_and_non_advisory() -> None:
    response = TestClient(app).get("/company-research/valuation-context")
    assert response.status_code == 200
    assert "标准化估值与预期上下文" in response.text
    assert "不代表合理价值、目标价、预期收益、买卖建议" in response.text
    assert "交易" in response.text

    script = Path("company_research/static/valuation_context.js").read_text(
        encoding="utf-8"
    )
    assert "innerHTML" not in script
    assert "encodeURIComponent" in script
    assert "自动回退" in script
