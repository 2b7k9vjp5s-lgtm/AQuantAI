"""Run the deterministic offline v0.5C Stage 1 beneficiary demo."""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.stage1_fixtures import build_stage1_beneficiary_fixture
from industry_alpha.stage1_query import Stage1BeneficiaryQueryService
from industry_alpha.stage1_repository import Stage1BeneficiaryRepository


def main() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)
    try:
        fixture = build_stage1_beneficiary_fixture(session_factory)
        with session_factory() as session:
            query = Stage1BeneficiaryQueryService(
                Stage1BeneficiaryRepository(session)
            )
            current = query.list_beneficiaries(fixture.map_id).to_dict()
            historical = query.list_beneficiaries(
                fixture.map_id, as_of_cutoff=date(2026, 7, 8)
            ).to_dict()
            pool = query.get_candidate_pool(fixture.candidate_pool_id).to_dict()
        direct_current = next(
            item
            for item in current["beneficiaries"]
            if item["beneficiary_id"] == str(fixture.direct_beneficiary_id)
        )
        direct_historical = next(
            item
            for item in historical["beneficiaries"]
            if item["beneficiary_id"] == str(fixture.direct_beneficiary_id)
        )
        payload = {
            "demo": "AQuantAI v0.5C offline Stage 1 beneficiary classifications",
            "map_id": str(fixture.map_id),
            "current_beneficiary_count": len(current["beneficiaries"]),
            "current_statuses": sorted(
                item["latest_revision"]["assessment_status"]
                for item in current["beneficiaries"]
            ),
            "direct_current_kind": direct_current["latest_revision"][
                "beneficiary_kind"
            ],
            "direct_historical_kind": direct_historical["latest_revision"][
                "beneficiary_kind"
            ],
            "candidate_pool_count": pool["latest_revision"]["candidate_count"],
            "candidate_stock_codes": [
                item["beneficiary"]["stock_code"]
                for item in pool["frozen_candidates"]
            ],
            "boundaries": [
                "fixture-only and no network",
                "exact stock/map-assertion/claim revision bindings",
                "unranked Stage 2 handoff only",
                "no scores, recommendations, or trading",
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
