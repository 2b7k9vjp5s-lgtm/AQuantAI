from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
import industry_alpha.stage1_models  # noqa: F401 - register output-link FK targets
from industry_alpha.industry_thesis_models import (
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_workbench import (
    IndustryThesisWorkbenchError,
    IndustryThesisWorkbenchQueryService,
    validate_workbench_boundary,
)

UTC = timezone.utc
BASE_TIME = datetime(2026, 7, 23, 1, 0, tzinfo=UTC)


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


def _revision(
    *,
    revision_id: UUID,
    session_id: UUID,
    revision_number: int,
    title: str | None,
    text: str,
    recorded_at: datetime,
    cutoff: date,
    workflow_state: str = "draft",
    coverage_state: str = "partial_local_coverage",
) -> IndustryThesisSessionRevision:
    return IndustryThesisSessionRevision(
        id=revision_id,
        session_id=session_id,
        revision_number=revision_number,
        thesis_text_original=text,
        thesis_title_reviewed=title,
        driver_type="demand_expansion",
        analysis_horizon_kind="medium_term",
        analysis_start_date=None,
        analysis_end_date=None,
        market_scope_json='[{"market_namespace":"CN_A"}]',
        chain_boundary_json='{"included":["materials"]}',
        exclusions_json="[]",
        seed_companies_json="[]",
        seed_products_json="[]",
        seed_technologies_json="[]",
        seed_bottlenecks_json="[]",
        draft_graph_json='{"nodes":[],"relationships":[]}',
        coverage_state=coverage_state,
        workflow_state=workflow_state,
        information_cutoff_date=cutoff,
        recorded_at_utc=recorded_at,
        input_fingerprint_sha256=(f"{revision_number:x}" * 64)[:64],
        supersedes_revision_id=None,
        revision_note=f"revision {revision_number}",
    )


def _seed(database) -> dict[str, UUID]:
    session_a = UUID(int=10)
    session_b = UUID(int=20)
    revision_a1 = UUID(int=101)
    revision_a2 = UUID(int=102)
    revision_b1 = UUID(int=201)
    with database.begin() as db:
        db.add_all(
            [
                IndustryThesisSessionIdentity(
                    id=session_a,
                    created_recorded_utc=BASE_TIME,
                    created_by_kind="local_user",
                    state="active",
                    latest_revision_number=2,
                ),
                IndustryThesisSessionIdentity(
                    id=session_b,
                    created_recorded_utc=BASE_TIME + timedelta(minutes=5),
                    created_by_kind="local_user",
                    state="active",
                    latest_revision_number=1,
                ),
            ]
        )
        db.add_all(
            [
                _revision(
                    revision_id=revision_a1,
                    session_id=session_a,
                    revision_number=1,
                    title=None,
                    text="先进材料需求扩张\n第二行说明",
                    recorded_at=BASE_TIME + timedelta(minutes=10),
                    cutoff=date(2026, 7, 22),
                ),
                _revision(
                    revision_id=revision_b1,
                    session_id=session_b,
                    revision_number=1,
                    title="高纯电子气体",
                    text="高纯电子气体本地研究",
                    recorded_at=BASE_TIME + timedelta(minutes=20),
                    cutoff=date(2026, 7, 22),
                    workflow_state="awaiting_review",
                ),
                _revision(
                    revision_id=revision_a2,
                    session_id=session_a,
                    revision_number=2,
                    title="先进材料产业链",
                    text="先进材料需求扩张与纯化瓶颈",
                    recorded_at=BASE_TIME + timedelta(minutes=30),
                    cutoff=date(2026, 7, 23),
                    workflow_state="reviewed_plan_ready",
                    coverage_state="reviewed_local_scope",
                ),
            ]
        )
    return {
        "session_a": session_a,
        "session_b": session_b,
        "revision_a1": revision_a1,
        "revision_a2": revision_a2,
        "revision_b1": revision_b1,
    }


def test_empty_history_is_explicit(database) -> None:
    with database() as session:
        result = IndustryThesisWorkbenchQueryService(session).list_sessions(
            as_of_cutoff=date(2026, 7, 23),
            as_of_recorded_at_utc=BASE_TIME,
            limit=20,
        )

    assert result["sessions"] == []
    assert result["session_count"] == 0
    assert result["has_more"] is False
    assert result["notices"]["accepted_outputs_not_inferred"] is True


def test_history_uses_exact_visible_latest_revision_and_deterministic_order(database) -> None:
    ids = _seed(database)
    boundary = BASE_TIME + timedelta(minutes=25)

    with database() as session:
        result = IndustryThesisWorkbenchQueryService(session).list_sessions(
            as_of_cutoff=date(2026, 7, 22),
            as_of_recorded_at_utc=boundary,
            limit=20,
        )

    assert [item["session_id"] for item in result["sessions"]] == [
        str(ids["session_b"]),
        str(ids["session_a"]),
    ]
    assert result["sessions"][0]["visible_latest_revision_id"] == str(
        ids["revision_b1"]
    )
    assert result["sessions"][1]["visible_latest_revision_id"] == str(
        ids["revision_a1"]
    )
    assert result["sessions"][1]["visible_revision_count"] == 1
    assert result["sessions"][1]["thesis_title"] == "先进材料需求扩张"


def test_later_boundary_reveals_later_revision_without_rewriting_history(database) -> None:
    ids = _seed(database)

    with database() as session:
        result = IndustryThesisWorkbenchQueryService(session).list_sessions(
            as_of_cutoff=date(2026, 7, 23),
            as_of_recorded_at_utc=BASE_TIME + timedelta(minutes=35),
            limit=20,
        )

    first = result["sessions"][0]
    assert first["session_id"] == str(ids["session_a"])
    assert first["visible_latest_revision_id"] == str(ids["revision_a2"])
    assert first["visible_latest_revision_number"] == 2
    assert first["visible_revision_count"] == 2
    assert first["next_surface"] == "result"
    assert first["coverage_state"] == "reviewed_local_scope"


def test_limit_is_bounded_and_reports_more(database) -> None:
    _seed(database)
    with database() as session:
        result = IndustryThesisWorkbenchQueryService(session).list_sessions(
            as_of_cutoff=date(2026, 7, 23),
            as_of_recorded_at_utc=BASE_TIME + timedelta(minutes=35),
            limit=1,
        )

    assert result["session_count"] == 1
    assert result["has_more"] is True


@pytest.mark.parametrize(
    ("cutoff", "recorded_at"),
    [
        (date(2026, 7, 23), datetime(2026, 7, 23, 1, 0)),
        (date(2026, 7, 24), BASE_TIME),
    ],
)
def test_invalid_boundaries_fail_closed(cutoff, recorded_at) -> None:
    with pytest.raises(IndustryThesisWorkbenchError):
        validate_workbench_boundary(cutoff, recorded_at)


def test_limit_outside_contract_fails_closed(database) -> None:
    with database() as session, pytest.raises(IndustryThesisWorkbenchError):
        IndustryThesisWorkbenchQueryService(session).list_sessions(
            as_of_cutoff=date(2026, 7, 23),
            as_of_recorded_at_utc=BASE_TIME,
            limit=101,
        )
