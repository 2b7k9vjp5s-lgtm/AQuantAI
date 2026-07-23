from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.industry_thesis_candidate_workbench import (
    IndustryThesisCandidateWorkbenchService,
)
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_rules import IndustryThesisError
from industry_alpha.models import ResearchCase
from industry_alpha.stage1_models import Stage1CandidatePool, Stage1CandidatePoolRevision
import industry_alpha.stage1_models  # noqa: F401 - register exact FK targets

UTC = timezone.utc
BASE = datetime(2026, 7, 23, 1, 0, tzinfo=UTC)
CUTOFF = date(2026, 7, 23)


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


def _payload(map_revision: IndustryMapRevision) -> dict:
    return {
        "thesis_text_original": "精确地图的候选来源边界测试",
        "thesis_title_reviewed": "候选来源边界",
        "driver_type": "unknown",
        "analysis_horizon_kind": "unknown",
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
        "chain_boundary": {"kind": "user_confirmed_text", "text": "边界测试"},
        "exclusions": [],
        "seed_companies": [],
        "seed_products": [],
        "seed_technologies": [],
        "seed_bottlenecks": [],
        "draft_graph": {
            "workbench_contract": "aquantai.personal-research-workbench.scope.v1",
            "exact_industry_map_references": [
                {
                    "source_kind": "industry_map_revision",
                    "map_id": str(map_revision.map_id),
                    "map_revision_id": str(map_revision.id),
                    "revision_number": map_revision.revision_no,
                    "title": map_revision.title,
                }
            ],
            "nodes": [],
            "relationships": [],
        },
        "coverage_state": "partial_local_coverage",
        "workflow_state": "candidate_build_ready",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "boundary fixture",
    }


def _seed(database):
    with database.begin() as session:
        case = ResearchCase(case_key="phase1c-boundary", created_at_utc=BASE, origin="fixture")
        session.add(case)
        session.flush()
        industry_map = IndustryMap(case_id=case.id, map_key="phase1c-boundary-map", created_at_utc=BASE)
        session.add(industry_map)
        session.flush()
        map_revision = IndustryMapRevision(
            map_id=industry_map.id,
            revision_no=1,
            title="边界测试地图",
            scope="只验证精确 pool 可见性",
            information_cutoff_date=CUTOFF,
            recorded_at_utc=BASE,
            supersedes_revision_id=None,
        )
        session.add(map_revision)
        session.flush()
        map_id = industry_map.id
        map_revision_id = map_revision.id
    with database() as session:
        map_revision = session.get(IndustryMapRevision, map_revision_id)
        payload = _payload(map_revision)
    created = IndustryThesisCommandService(
        database,
        clock=lambda: BASE + timedelta(minutes=1),
    ).create_session(payload)
    return created, map_id, map_revision_id


def _add_pool(database, *, map_id: UUID, map_revision_id: UUID, key: str, recorded_at: datetime):
    with database.begin() as session:
        case_id = session.get(IndustryMap, map_id).case_id
        pool = Stage1CandidatePool(
            case_id=case_id,
            map_id=map_id,
            pool_key=key,
            created_at_utc=recorded_at,
        )
        session.add(pool)
        session.flush()
        revision = Stage1CandidatePoolRevision(
            candidate_pool_id=pool.id,
            revision_no=1,
            selected_map_revision_id=map_revision_id,
            title=key,
            scope="empty frozen pool for option-boundary testing",
            information_cutoff_date=CUTOFF,
            recorded_at_utc=recorded_at,
            supersedes_revision_id=None,
        )
        session.add(revision)
        session.flush()
        return revision.id


def test_exact_route_ownership_is_enforced(database) -> None:
    created, _, _ = _seed(database)
    with database() as session:
        with pytest.raises(IndustryThesisError) as captured:
            IndustryThesisCandidateWorkbenchService(session).candidate_source_options(
                session_id=uuid4(),
                session_revision_id=UUID(created["session_revision_id"]),
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=BASE + timedelta(minutes=2),
            )
    assert captured.value.code == "industry_thesis_session_revision_not_found"


def test_map_without_pool_is_explicit_and_has_no_fallback(database) -> None:
    created, _, _ = _seed(database)
    with database() as session:
        options = IndustryThesisCandidateWorkbenchService(session).candidate_source_options(
            session_id=UUID(created["session_id"]),
            session_revision_id=UUID(created["session_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BASE + timedelta(minutes=2),
        )
    assert options["maps"][0]["availability_state"] == "no_exact_frozen_pool"
    assert options["maps"][0]["eligible_candidate_pools"] == []
    assert options["maps"][0]["selected_candidate_pool_revision_id"] is None


def test_later_pools_do_not_leak_and_multiple_visible_pools_are_not_preselected(database) -> None:
    created, map_id, map_revision_id = _seed(database)
    early = _add_pool(
        database,
        map_id=map_id,
        map_revision_id=map_revision_id,
        key="early-pool",
        recorded_at=BASE + timedelta(minutes=2),
    )
    late = _add_pool(
        database,
        map_id=map_id,
        map_revision_id=map_revision_id,
        key="late-pool",
        recorded_at=BASE + timedelta(minutes=4),
    )
    with database() as session:
        early_options = IndustryThesisCandidateWorkbenchService(session).candidate_source_options(
            session_id=UUID(created["session_id"]),
            session_revision_id=UUID(created["session_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BASE + timedelta(minutes=3),
        )
        later_options = IndustryThesisCandidateWorkbenchService(session).candidate_source_options(
            session_id=UUID(created["session_id"]),
            session_revision_id=UUID(created["session_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BASE + timedelta(minutes=5),
        )
    early_ids = {
        item["candidate_pool_revision_id"]
        for item in early_options["maps"][0]["eligible_candidate_pools"]
    }
    later_rows = later_options["maps"][0]["eligible_candidate_pools"]
    assert early_ids == {str(early)}
    assert {item["candidate_pool_revision_id"] for item in later_rows} == {str(early), str(late)}
    assert all(item["selected"] is False for item in later_rows)
    assert later_options["maps"][0]["selected_candidate_pool_revision_id"] is None
