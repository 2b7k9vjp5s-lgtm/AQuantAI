"""Run the deterministic offline v0.6B expectation and valuation demo."""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.stage2_expectations_fixtures import (
    build_stage2_expectation_valuation_fixture,
)
from industry_alpha.stage2_expectations_query import (
    Stage2ExpectationQueryService,
    Stage2ValuationQueryService,
)
from industry_alpha.stage2_expectations_repository import Stage2ExpectationRepository


def main() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)
    try:
        fixture = build_stage2_expectation_valuation_fixture(session_factory)
        with session_factory() as session:
            repository = Stage2ExpectationRepository(session)
            expectations = Stage2ExpectationQueryService(repository)
            valuations = Stage2ValuationQueryService(repository)
            current_expectation = expectations.get_expectation(
                fixture.expectation_id
            ).to_dict()
            historical_expectation = expectations.get_expectation(
                fixture.expectation_id,
                as_of_cutoff=date(2026, 7, 15),
            ).to_dict()
            valuation = valuations.get_valuation(fixture.valuation_id).to_dict()
        payload = {
            "demo": "AQuantAI v0.6B offline expectation and valuation snapshots",
            "expectation_id": str(fixture.expectation_id),
            "valuation_id": str(fixture.valuation_id),
            "current_expectation_revision_no": current_expectation[
                "latest_revision"
            ]["revision_no"],
            "historical_expectation_revision_no": historical_expectation[
                "latest_revision"
            ]["revision_no"],
            "valuation_method": valuation["latest_revision"]["valuation_method"],
            "price_reference": valuation["latest_revision"]["price_reference"],
            "boundaries": [
                "fixture-only and no network",
                "append-only market expectation and valuation observations",
                "exact Stage 2 research, hypothesis, claim, and evidence boundary",
                "optional exact local daily_price row and successful ingestion provenance",
                "no target price, fair value, expected return, score, ranking, recommendation, or trading",
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
