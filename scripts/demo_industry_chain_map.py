"""Run the deterministic, offline v0.5B industry-chain-map demo."""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.chain_map_fixtures import build_industry_chain_map_fixture
from industry_alpha.chain_map_query import IndustryChainMapQueryService
from industry_alpha.chain_map_repository import IndustryChainMapRepository


def main() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)
    try:
        map_id = build_industry_chain_map_fixture(session_factory)
        with session_factory() as session:
            query = IndustryChainMapQueryService(
                IndustryChainMapRepository(session)
            )
            current = query.get_map(map_id).to_dict()
            historical = query.get_map(
                map_id, as_of_cutoff=date(2026, 7, 3)
            ).to_dict()
        result = {
            "demo": "AQuantAI v0.5B offline evidence-backed industry chain map",
            "map_key": current["industry_map"]["map_key"],
            "current": {
                "revision_no": current["latest_revision"]["revision_no"],
                "counts": current["frozen_snapshot"]["counts"],
                "evidence_grade_summary": current["evidence_grade_summary"],
                "conflict_count": len(current["conflicts"]),
                "missing_evidence_count": len(current["missing_evidence"]),
            },
            "historical_cutoff_2026_07_03": {
                "revision_no": historical["latest_revision"]["revision_no"],
                "counts": historical["frozen_snapshot"]["counts"],
                "conflict_count": len(historical["conflicts"]),
            },
            "boundaries": [
                "fixture-only",
                "read-only HTTP API",
                "exact v0.5A claim-revision binding",
                "no network or LLM execution",
                "no scoring, company beneficiaries, recommendations, or trading",
            ],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
