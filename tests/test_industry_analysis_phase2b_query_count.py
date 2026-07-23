from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

import backend.api.industry_analysis as industry_api
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
import industry_alpha.stage1_models  # noqa: F401 - register output-link FK targets
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService


CUTOFF = date(2026, 7, 23)
RECORDED = datetime(2026, 7, 23, 14, 0, tzinfo=timezone.utc)
SCOPE_CONTRACT = "aquantai.personal-research-workbench.scope.v1"


def _input() -> dict:
    return {
        "thesis_text_original": "Phase 2B 查询上限验证",
        "thesis_title_reviewed": "查询上限",
        "driver_type": "other",
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
        "chain_boundary": {"kind": "user_confirmed_text", "text": "本地范围"},
        "exclusions": [],
        "seed_companies": [],
        "seed_products": [],
        "seed_technologies": [],
        "seed_bottlenecks": [],
        "draft_graph": {
            "workbench_contract": SCOPE_CONTRACT,
            "exact_industry_map_references": [],
            "nodes": [],
            "relationships": [],
        },
        "coverage_state": "coverage_unknown",
        "workflow_state": "draft",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "query ceiling fixture",
    }


def test_sessions_projection_keeps_one_statement_independent_of_card_projection() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    IndustryThesisCommandService(factory, clock=lambda: RECORDED).create_session(_input())

    statements: list[str] = []

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture)

    def override_factory():
        yield factory

    app.dependency_overrides[
        industry_api.get_industry_analysis_session_factory
    ] = override_factory
    try:
        response = TestClient(app).get(
            "/industry-analysis/api/sessions",
            params={
                "as_of_cutoff": CUTOFF.isoformat(),
                "as_of_recorded_at_utc": RECORDED.isoformat(),
                "limit": 20,
            },
        )
    finally:
        app.dependency_overrides.clear()
        event.remove(engine, "before_cursor_execute", capture)
        engine.dispose()

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_count"] == 1
    assert payload["sessions"][0]["continuation"]["kind"] == "scope"
    assert len(statements) == 1
    assert statements[0].lstrip().upper().startswith("SELECT")
