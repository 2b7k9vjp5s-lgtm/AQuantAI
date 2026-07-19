"""Run the deterministic offline v0.6A company-research demo."""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.stage2_fixtures import build_stage2_company_research_fixture
from industry_alpha.stage2_query import Stage2CompanyResearchQueryService
from industry_alpha.stage2_repository import Stage2CompanyResearchRepository


def main() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)
    try:
        fixture = build_stage2_company_research_fixture(session_factory)
        with session_factory() as session:
            query = Stage2CompanyResearchQueryService(
                Stage2CompanyResearchRepository(session)
            )
            current = query.get_research(fixture.supported_research_id).to_dict()
            historical = query.get_research(
                fixture.supported_research_id,
                as_of_cutoff=date(2026, 7, 12),
            ).to_dict()
            draft = query.get_research(fixture.draft_research_id).to_dict()
        payload = {
            "demo": "AQuantAI v0.6A offline Stage 2 company research",
            "supported_research_id": str(fixture.supported_research_id),
            "frozen_membership_id": current["frozen_stage1_handoff"]
            ["candidate_pool"]["candidate_pool_membership_id"],
            "current_research_revision_no": current["latest_revision"]["revision_no"],
            "historical_research_revision_no": historical["latest_revision"]["revision_no"],
            "historical_hypothesis_revision_no": historical["hypotheses"][0]
            ["latest_revision"]["revision_no"],
            "completed_checklist_count": len(
                historical["latest_revision"]["后续验证清单"]
            ),
            "draft_missing_evidence_count": len(draft["missing_evidence"]),
            "boundaries": [
                "fixture-only and no network",
                "exact frozen Stage 1 membership and evidence boundary",
                "append-only financial-transmission hypotheses",
                "no valuation, scores, rankings, recommendations, or trading",
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
