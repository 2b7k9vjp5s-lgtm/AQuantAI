"""Run the deterministic offline v0.6C catalyst/risk assessment demo."""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.stage2_assessments_fixtures import build_stage2_assessment_fixture
from industry_alpha.stage2_assessments_query import Stage2CatalystQueryService, Stage2RiskQueryService
from industry_alpha.stage2_assessments_repository import Stage2AssessmentRepository


def main() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    try:
        fixture = build_stage2_assessment_fixture(factory)
        with factory() as session:
            repository = Stage2AssessmentRepository(session)
            current = {
                "catalyst": Stage2CatalystQueryService(repository).get_catalyst(fixture.supported_catalyst_id).to_dict(),
                "risk": Stage2RiskQueryService(repository).get_risk(fixture.supported_risk_id).to_dict(),
            }
            historical = {
                "catalyst": Stage2CatalystQueryService(repository).get_catalyst(fixture.supported_catalyst_id, as_of_cutoff=date(2026, 7, 16)).to_dict(),
                "risk": Stage2RiskQueryService(repository).get_risk(fixture.supported_risk_id, as_of_cutoff=date(2026, 7, 16)).to_dict(),
            }
        print(json.dumps({"current": current, "historical": historical}, ensure_ascii=True, allow_nan=False, sort_keys=True))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
