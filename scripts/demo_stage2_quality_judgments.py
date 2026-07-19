"""Run the deterministic offline v0.6D quality-judgment demo."""

from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.stage2_judgments_fixtures import build_stage2_judgment_fixture
from industry_alpha.stage2_judgments_query import Stage2CompanyJudgmentQueryService, Stage2IndustryJudgmentQueryService
from industry_alpha.stage2_judgments_repository import Stage2JudgmentRepository


def build_demo() -> dict:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    fixture = build_stage2_judgment_fixture(factory)
    with factory() as session:
        repository = Stage2JudgmentRepository(session)
        result = {
            "industry": Stage2IndustryJudgmentQueryService(repository).get_judgment(fixture.affirmed_industry_id).to_dict(),
            "company": Stage2CompanyJudgmentQueryService(repository).get_judgment(fixture.affirmed_company_id).to_dict(),
        }
    engine.dispose()
    return result


def main() -> None:
    print(json.dumps(build_demo(), indent=2, ensure_ascii=True, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
