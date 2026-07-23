from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base, IngestionRun, StockBasicRecord
from industry_alpha.industry_thesis_candidate_workbench import (
    IndustryThesisCandidateWorkbenchService,
    IndustryThesisWorkbenchCandidateCommandService,
)
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateIdentity,
    IndustryThesisCandidateRevision,
    IndustryThesisOutputLinkIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_review import (
    ACCEPTANCE_PLAN_VERSION,
    IndustryThesisProposalReviewService,
)
from industry_alpha.industry_thesis_review_workbench import (
    IndustryThesisReviewWorkbenchQueryService,
)
from industry_alpha.industry_thesis_rules import IndustryThesisError, IndustryThesisNotFound
from industry_alpha.industry_thesis_workbench import IndustryThesisWorkbenchQueryService
import industry_alpha.stage1_models  # noqa: F401 - register exact FK targets

UTC = timezone.utc
BASE = datetime(2026, 7, 23, 6, 0, tzinfo=UTC)
CUTOFF = date(2026, 7, 23)


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self._value = value

    def __call__(self) -> datetime:
        return self._value


@pytest.fixture()
def database():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    try:
        yield factory
    finally:
        engine.dispose()


def _seed_stock_records(database) -> list[StockBasicRecord]:
    with database.begin() as session:
        run = IngestionRun(
            batch_identifier="phase1d-review-workbench",
            series_key="1" * 64,
            series_identity={"kind": "stock_basic", "fixture": "phase1d"},
            provider="fixture",
            dataset="stock_basic",
            imported_at=BASE,
            completed_at=BASE,
            requested_start_date=CUTOFF,
            requested_end_date=CUTOFF,
            information_cutoff_date=CUTOFF,
            requested_scope={"market": "CN_A"},
            provider_request_metadata={},
            adapter_version="fixture-v1",
            snapshot_mode="complete",
            contract_version="v1",
            status="succeeded",
            row_count_received=3,
            row_count_written=3,
            dataset_counts={"stock_basic": 3},
        )
        session.add(run)
        session.flush()
        rows = [
            StockBasicRecord(
                ingestion_run_id=run.id,
                stock_code=f"68800{index}.SH",
                stock_name=label,
                exchange="SSE",
                industry="电子特气",
                listing_date=date(2020, 1, index),
                status="active",
                source="fixture",
            )
            for index, label in enumerate(
                ("精确公司甲", "精确公司乙", "精确公司丙"),
                start=1,
            )
        ]
        session.add_all(rows)
        session.flush()
        ids = [row.id for row in rows]
    with database() as session:
        return [session.get(StockBasicRecord, value) for value in ids]


def _session_payload(rows: list[StockBasicRecord]) -> dict:
    return {
        "thesis_text_original": "AI 数据中心扩张带动电子特气需求",
        "thesis_title_reviewed": "电子特气需求",
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
        "chain_boundary": {"kind": "user_confirmed_text", "text": "纯化、供应与客户认证"},
        "exclusions": [],
        "seed_companies": [
            {
                "source_kind": "stock_basic_record",
                "exact_id": str(row.id),
                "stock_basic_record_id": row.id,
                "listed_instrument_id": None,
                "label": row.stock_name,
                "code": row.stock_code,
            }
            for row in rows
        ],
        "seed_products": ["高纯电子气体"],
        "seed_technologies": [],
        "seed_bottlenecks": ["客户认证"],
        "draft_graph": {
            "workbench_contract": "aquantai.personal-research-workbench.scope.v1",
            "exact_industry_map_references": [],
            "nodes": [],
            "relationships": [],
        },
        "coverage_state": "reviewed_local_scope",
        "workflow_state": "candidate_build_ready",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "Phase 1D exact three-seed scope",
    }


def _built_universe(database) -> tuple[dict, dict]:
    rows = _seed_stock_records(database)
    created = IndustryThesisCommandService(
        database,
        clock=FixedClock(BASE + timedelta(minutes=1)),
    ).create_session(_session_payload(rows))
    with database() as session:
        command, summary = IndustryThesisCandidateWorkbenchService(
            session
        ).compose_candidate_build(
            session_id=UUID(created["session_id"]),
            session_revision_id=UUID(created["session_revision_id"]),
            expected_session_latest_revision_number=1,
            selected_candidate_pool_revision_ids=[],
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BASE + timedelta(minutes=2),
        )
    assert summary["company_seed_proposal_count"] == 3
    assert summary["stage1_proposal_count"] == 0
    built = IndustryThesisWorkbenchCandidateCommandService(
        database,
        clock=FixedClock(BASE + timedelta(minutes=3)),
    ).build_candidates(command)
    assert built["candidate_count"] == 3
    return created, built


def _decision_payload(view: dict) -> list[dict]:
    decisions = []
    states = (
        ("selected_for_acceptance", "direct", "需求与产品路径直接对应。", "limited_evidence", "仍需核对收入占比。"),
        ("rejected_by_user", None, "当前受益路径不足以进入后续研究。", "not_current_priority", "后续有新增客户证据再复核。"),
        ("unresolved", None, "受益方向存在但关键环节尚未验证。", "awaiting_verification", "等待客户认证与产能信息。"),
    )
    for candidate, values in zip(view["candidates"], states, strict=True):
        decision, exposure, rationale, uncertainty_state, uncertainty_note = values
        decisions.append(
            {
                "candidate_revision_id": candidate["candidate_revision_id"],
                "expected_latest_revision_number": candidate["revision_number"],
                "decision": decision,
                "final_proposed_exposure_type": exposure,
                "rationale": {"user_review_rationale": rationale},
                "uncertainty": {
                    "state": uncertainty_state,
                    "note": uncertainty_note,
                },
            }
        )
    return decisions


def test_exact_review_projection_dry_run_commit_and_result_reopen(database) -> None:
    created, built = _built_universe(database)
    session_id = UUID(created["session_id"])
    source_revision_id = UUID(created["session_revision_id"])
    boundary = datetime.fromisoformat(built["recorded_at_utc"])

    with database() as session:
        review_view = IndustryThesisReviewWorkbenchQueryService(session).get_review_view(
            session_id=session_id,
            session_revision_id=source_revision_id,
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=boundary,
        )
    assert review_view["candidate_count"] == 3
    assert review_view["undecided_count"] == 3
    assert all(item["review_state"] == "proposed" for item in review_view["candidates"])
    assert all(item["can_select_for_acceptance"] for item in review_view["candidates"])

    decisions = _decision_payload(review_view)
    command = {
        "session_revision_id": str(source_revision_id),
        "expected_session_latest_revision_number": 1,
        "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
        "decisions": list(reversed(decisions)),
        "revision_note": "完成三条精确候选路径审阅",
    }
    dry_run = IndustryThesisProposalReviewService(
        database,
        clock=FixedClock(BASE + timedelta(minutes=4)),
    ).review_candidates(command, dry_run=True)
    with database() as session:
        assert session.scalar(select(func.count()).select_from(IndustryThesisSessionRevision)) == 1
        assert session.scalar(select(func.count()).select_from(IndustryThesisCandidateRevision)) == 3

    command["decisions"] = decisions
    committed = IndustryThesisProposalReviewService(
        database,
        clock=FixedClock(BASE + timedelta(minutes=5)),
    ).review_candidates(command)
    assert committed["acceptance_plan"] == dry_run["acceptance_plan"]
    assert committed["acceptance_plan_fingerprint_sha256"] == dry_run[
        "acceptance_plan_fingerprint_sha256"
    ]
    assert committed["reviewed_session_revision_id"] == dry_run[
        "reviewed_session_revision_id"
    ]

    result_boundary = datetime.fromisoformat(committed["candidate_recorded_at_utc"])
    with database() as session:
        assert session.scalar(select(func.count()).select_from(IndustryThesisSessionRevision)) == 2
        assert session.scalar(select(func.count()).select_from(IndustryThesisCandidateIdentity)) == 3
        assert session.scalar(select(func.count()).select_from(IndustryThesisCandidateRevision)) == 6
        assert session.scalar(select(func.count()).select_from(IndustryThesisOutputLinkIdentity)) == 0
        result = IndustryThesisReviewWorkbenchQueryService(session).get_result_view(
            session_id=session_id,
            reviewed_session_revision_id=UUID(committed["reviewed_session_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=result_boundary,
        )
        history = IndustryThesisWorkbenchQueryService(session).list_sessions(
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=result_boundary,
            limit=20,
        )

    assert result["candidate_count"] == 3
    assert result["selected_count"] == 1
    assert result["rejected_count"] == 1
    assert result["unresolved_count"] == 1
    assert result["selected_candidates"][0]["rationale"] == {
        "user_review_rationale": "需求与产品路径直接对应。"
    }
    assert result["unresolved_candidates"][0]["uncertainty"] == {
        "state": "awaiting_verification",
        "note": "等待客户认证与产能信息。",
    }
    assert result["acceptance_plan_fingerprint_sha256"] == committed[
        "acceptance_plan_fingerprint_sha256"
    ]
    assert result["notices"]["owner_acceptance_not_performed"] is True
    assert history["sessions"][0]["next_surface"] == "result"
    assert history["sessions"][0]["visible_latest_revision_id"] == committed[
        "reviewed_session_revision_id"
    ]

    with database() as session:
        with pytest.raises(IndustryThesisNotFound):
            IndustryThesisReviewWorkbenchQueryService(session).get_result_view(
                session_id=uuid4(),
                reviewed_session_revision_id=UUID(committed["reviewed_session_revision_id"]),
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=result_boundary,
            )
        with pytest.raises(IndustryThesisError, match="exact latest"):
            IndustryThesisReviewWorkbenchQueryService(session).get_review_view(
                session_id=session_id,
                session_revision_id=source_revision_id,
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=result_boundary,
            )
