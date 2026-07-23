"""Offline production-boundary demo for the Personal Research Workbench UI Phase 1A."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
import industry_alpha.stage1_models  # noqa: F401 - register output-link FK targets
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_workbench import IndustryThesisWorkbenchQueryService

UTC = timezone.utc
BASE_TIME = datetime(2026, 7, 23, 2, 0, tzinfo=UTC)
CUTOFF = date(2026, 7, 23)


def _input(title: str, thesis: str, workflow_state: str) -> dict:
    return {
        "thesis_text_original": thesis,
        "thesis_title_reviewed": title,
        "driver_type": "demand_expansion",
        "analysis_horizon_kind": "medium_term",
        "market_scope": [
            {
                "market_namespace": "CN_A",
                "exchange_namespace": None,
                "security_type": "common_equity",
                "include_status": "active",
                "listed_instrument_ids": [],
            }
        ],
        "chain_boundary": {"included": ["materials", "processing"]},
        "exclusions": [],
        "seed_companies": [],
        "seed_products": [],
        "seed_technologies": [],
        "seed_bottlenecks": [],
        "draft_graph": {"nodes": [], "relationships": []},
        "coverage_state": "partial_local_coverage",
        "workflow_state": workflow_state,
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "offline workbench demo",
    }


def run_demo() -> dict:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    try:
        IndustryThesisCommandService(
            factory,
            clock=lambda: BASE_TIME,
        ).create_session(
            _input(
                "先进材料产业链",
                "先进材料需求扩张与关键纯化工艺瓶颈",
                "draft",
            )
        )
        IndustryThesisCommandService(
            factory,
            clock=lambda: BASE_TIME + timedelta(minutes=1),
        ).create_session(
            _input(
                "高纯电子气体",
                "AI 数据中心与半导体扩产是否提升高纯电子气体需求",
                "candidate_build_ready",
            )
        )
        with factory() as session:
            payload = IndustryThesisWorkbenchQueryService(session).list_sessions(
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=BASE_TIME + timedelta(minutes=2),
                limit=20,
            )
        assert payload["session_count"] == 2
        assert payload["sessions"][0]["thesis_title"] == "高纯电子气体"
        assert payload["notices"]["accepted_outputs_not_inferred"] is True
        return payload
    finally:
        engine.dispose()


def main() -> None:
    print(json.dumps(run_demo(), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
