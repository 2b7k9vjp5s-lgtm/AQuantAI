"""Run the deterministic, offline Industry Alpha evidence-ledger demo."""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.fixtures import build_evidence_ledger_fixture
from industry_alpha.query import EvidenceLedgerQueryService
from industry_alpha.repository import EvidenceLedgerRepository


def main() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)
    try:
        case_id = build_evidence_ledger_fixture(session_factory)
        with session_factory() as session:
            query = EvidenceLedgerQueryService(EvidenceLedgerRepository(session))
            current = query.get_case(case_id).to_dict()
            historical = query.get_case(
                case_id, as_of_cutoff=date(2026, 6, 7)
            ).to_dict()
        result = {
            "demo": "AQuantAI v0.5A offline evidence ledger fixture",
            "case_key": current["case"]["case_key"],
            "current": {
                "latest_revision_no": current["latest_revision"]["revision_no"],
                "workflow_state": current["latest_revision"]["workflow_state"],
                "conclusion_status": current["latest_revision"]["conclusion_status"],
                "evidence_count": len(current["evidence_items"]),
                "conflict_count": len(current["conflicts"]),
                "verification_count": len(current["verification_items"]),
            },
            "historical_cutoff_2026_06_07": {
                "latest_revision_no": historical["latest_revision"]["revision_no"],
                "evidence_count": len(historical["evidence_items"]),
                "conflict_count": len(historical["conflicts"]),
                "verification_count": len(historical["verification_items"]),
            },
            "boundaries": [
                "fixture-only",
                "read-only HTTP API",
                "no network access",
                "research record-keeping only",
                "not investment advice",
            ],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
