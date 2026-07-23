"""Offline production-service demo for Personal Research Workbench UI Phase 1B."""

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
WORKBENCH_SCOPE_CONTRACT = "aquantai.personal-research-workbench.scope.v1"


def _input() -> dict:
    return {
        "thesis_text_original": "AI 数据中心与半导体扩产是否提升高纯电子气体需求",
        "thesis_title_reviewed": "高纯电子气体",
        "driver_type": "demand_expansion",
        "analysis_horizon_kind": "medium_term",
        "analysis_start_date": None,
        "analysis_end_date": None,
        "market_scope": [
            {
                "market_namespace": "CN_A",
                "exchange_namespace": None,
                "security_type": "common_equity",
                "include_status": "active",
                "listed_instrument_ids": [],
            }
        ],
        "chain_boundary": {
            "kind": "user_confirmed_text",
            "text": "纯化、现场制气与客户认证",
        },
        "exclusions": ["仅有概念标签"],
        "seed_companies": [],
        "seed_products": ["高纯电子气体"],
        "seed_technologies": ["气体纯化"],
        "seed_bottlenecks": ["客户认证"],
        "draft_graph": {
            "workbench_contract": WORKBENCH_SCOPE_CONTRACT,
            "exact_industry_map_references": [],
            "nodes": [],
            "relationships": [],
        },
        "coverage_state": "coverage_unknown",
        "workflow_state": "draft",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "offline Phase 1B demo",
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
        with factory() as session:
            option_service = IndustryThesisWorkbenchQueryService(session)
            maps = option_service.list_map_options(
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=BASE_TIME,
                limit=20,
            )
            companies = option_service.list_company_options(
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=BASE_TIME,
                query="688001.SH",
                limit=20,
            )
        assert maps["option_count"] == 0
        assert companies["option_count"] == 0
        assert companies["notices"]["first_result_not_selected"] is True

        create_service = IndustryThesisCommandService(
            factory,
            clock=lambda: BASE_TIME + timedelta(minutes=1),
        )
        create_preview = create_service.create_session(_input(), dry_run=True)
        assert create_preview["dry_run"] is True
        assert create_preview["session_id"] is None

        created = IndustryThesisCommandService(
            factory,
            clock=lambda: BASE_TIME + timedelta(minutes=2),
        ).create_session(_input())
        assert created["revision_number"] == 1

        revision_preview = IndustryThesisCommandService(
            factory,
            clock=lambda: BASE_TIME + timedelta(minutes=3),
        ).revise_session(
            {
                "session_id": created["session_id"],
                "expected_latest_revision_number": 1,
                "changes": {
                    "thesis_title_reviewed": "高纯电子气体需求与认证",
                    "coverage_state": "partial_local_coverage",
                },
                "revision_note": "确认本地研究边界",
            },
            dry_run=True,
        )
        assert revision_preview["dry_run"] is True
        assert revision_preview["revision_number"] == 2

        revised = IndustryThesisCommandService(
            factory,
            clock=lambda: BASE_TIME + timedelta(minutes=4),
        ).revise_session(
            {
                "session_id": created["session_id"],
                "expected_latest_revision_number": 1,
                "changes": {
                    "thesis_title_reviewed": "高纯电子气体需求与认证",
                    "coverage_state": "partial_local_coverage",
                },
                "revision_note": "确认本地研究边界",
            }
        )
        assert revised["revision_number"] == 2

        with factory() as session:
            history = IndustryThesisWorkbenchQueryService(session).list_sessions(
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=BASE_TIME + timedelta(minutes=5),
                limit=20,
            )
        assert history["session_count"] == 1
        assert history["sessions"][0]["visible_revision_count"] == 2
        assert history["sessions"][0]["thesis_title"] == "高纯电子气体需求与认证"
        assert history["notices"]["accepted_outputs_not_inferred"] is True
        return {
            "options": {"maps": maps, "companies": companies},
            "create_preview": create_preview,
            "created": created,
            "revision_preview": revision_preview,
            "revised": revised,
            "history": history,
        }
    finally:
        engine.dispose()


def main() -> None:
    print(json.dumps(run_demo(), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
