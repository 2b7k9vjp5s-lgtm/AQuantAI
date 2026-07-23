from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base, IngestionRun, StockBasicRecord
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.industry_thesis_candidate_workbench import (
    IndustryThesisCandidateWorkbenchService,
    IndustryThesisWorkbenchCandidateCommandService,
)
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateIdentity,
    IndustryThesisCandidateRevision,
)
from industry_alpha.industry_thesis_query import IndustryThesisQueryService
from industry_alpha.industry_thesis_rules import IndustryThesisError
from industry_alpha.models import ResearchCase
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryRevision,
    Stage1CandidatePool,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)
import industry_alpha.stage1_models  # noqa: F401 - register all exact FK targets

UTC = timezone.utc
BASE = datetime(2026, 7, 23, 1, 0, tzinfo=UTC)
CUTOFF = date(2026, 7, 23)


class SequenceClock:
    def __init__(self, *values: datetime) -> None:
        self._values = iter(values)

    def __call__(self) -> datetime:
        return next(self._values)


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


def _run(index: int, completed: datetime) -> IngestionRun:
    return IngestionRun(
        batch_identifier=f"phase1c-{index}",
        series_key=f"{index:064d}",
        series_identity={"kind": "stock_basic", "fixture": index},
        provider="fixture",
        dataset="stock_basic",
        imported_at=completed,
        completed_at=completed,
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


def _session_input(seed: StockBasicRecord, map_revision: IndustryMapRevision, *, workflow: str = "candidate_build_ready") -> dict:
    return {
        "thesis_text_original": "AI 数据中心扩张是否提升电子特气需求",
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
        "chain_boundary": {"kind": "user_confirmed_text", "text": "纯化与客户认证"},
        "exclusions": [],
        "seed_companies": [
            {
                "source_kind": "stock_basic_record",
                "exact_id": str(seed.id),
                "stock_basic_record_id": seed.id,
                "listed_instrument_id": None,
                "label": seed.stock_name,
                "code": seed.stock_code,
            }
        ],
        "seed_products": ["高纯电子气体"],
        "seed_technologies": [],
        "seed_bottlenecks": ["客户认证"],
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
        "workflow_state": workflow,
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "Phase 1C fixture scope",
    }


def _seed_graph(database):
    with database.begin() as session:
        run = _run(1, BASE)
        session.add(run)
        session.flush()
        stock_a = StockBasicRecord(
            ingestion_run_id=run.id,
            stock_code="688001.SH",
            stock_name="种子公司A",
            exchange="SSE",
            industry="电子特气",
            listing_date=date(2020, 1, 1),
            status="active",
            source="fixture",
        )
        stock_b = StockBasicRecord(
            ingestion_run_id=run.id,
            stock_code="688002.SH",
            stock_name="候选公司B",
            exchange="SSE",
            industry="电子特气",
            listing_date=date(2020, 1, 2),
            status="active",
            source="fixture",
        )
        session.add_all([stock_a, stock_b])
        session.flush()
        case = ResearchCase(case_key="phase1c-electronic-gases", created_at_utc=BASE, origin="fixture")
        session.add(case)
        session.flush()
        industry_map = IndustryMap(
            case_id=case.id,
            map_key="electronic-gases",
            created_at_utc=BASE,
        )
        session.add(industry_map)
        session.flush()
        map_revision = IndustryMapRevision(
            map_id=industry_map.id,
            revision_no=1,
            title="电子特气产业链",
            scope="纯化、供应与客户认证",
            information_cutoff_date=CUTOFF,
            recorded_at_utc=BASE,
            supersedes_revision_id=None,
        )
        session.add(map_revision)
        session.flush()
        beneficiaries = []
        revisions = []
        for index, (stock, kind) in enumerate(((stock_a, "direct"), (stock_b, "secondary")), start=1):
            beneficiary = Stage1Beneficiary(
                case_id=case.id,
                map_id=industry_map.id,
                source=stock.source,
                stock_code=stock.stock_code,
                created_at_utc=BASE + timedelta(seconds=index),
            )
            session.add(beneficiary)
            session.flush()
            revision = Stage1BeneficiaryRevision(
                beneficiary_id=beneficiary.id,
                revision_no=1,
                selected_map_revision_id=map_revision.id,
                stock_basic_record_id=stock.id,
                beneficiary_kind=kind,
                assessment_status="supported",
                rationale_summary=f"{stock.stock_name} 已冻结在 Stage 1 候选池中。",
                information_cutoff_date=CUTOFF,
                recorded_at_utc=BASE + timedelta(seconds=index),
                supersedes_revision_id=None,
            )
            session.add(revision)
            session.flush()
            beneficiaries.append(beneficiary)
            revisions.append(revision)
        pool = Stage1CandidatePool(
            case_id=case.id,
            map_id=industry_map.id,
            pool_key="phase1c-complete-local-pool",
            created_at_utc=BASE + timedelta(seconds=3),
        )
        session.add(pool)
        session.flush()
        pool_revision = Stage1CandidatePoolRevision(
            candidate_pool_id=pool.id,
            revision_no=1,
            selected_map_revision_id=map_revision.id,
            title="电子特气冻结候选池",
            scope="完整保留两个支持状态成员",
            information_cutoff_date=CUTOFF,
            recorded_at_utc=BASE + timedelta(seconds=4),
            supersedes_revision_id=None,
        )
        session.add(pool_revision)
        session.flush()
        for index, (beneficiary, revision) in enumerate(zip(beneficiaries, revisions), start=1):
            session.add(
                Stage1CandidatePoolMembership(
                    candidate_pool_revision_id=pool_revision.id,
                    beneficiary_id=beneficiary.id,
                    beneficiary_revision_id=revision.id,
                    recorded_at_utc=BASE + timedelta(seconds=4 + index),
                )
            )
        session.flush()
        values = {
            "stock_a_id": stock_a.id,
            "map_revision_id": map_revision.id,
            "pool_revision_id": pool_revision.id,
        }
    with database() as session:
        stock_a = session.get(StockBasicRecord, values["stock_a_id"])
        map_revision = session.get(IndustryMapRevision, values["map_revision_id"])
        return values, _session_input(stock_a, map_revision)


def _created_session(database, session_input: dict, *, workflow: str | None = None):
    if workflow is not None:
        session_input = dict(session_input)
        session_input["workflow_state"] = workflow
    return IndustryThesisCommandService(
        database,
        clock=SequenceClock(BASE + timedelta(minutes=1)),
    ).create_session(session_input)


def test_source_options_require_explicit_pool_selection_and_preserve_seed(database) -> None:
    values, session_input = _seed_graph(database)
    created = _created_session(database, session_input)
    with database() as session:
        options = IndustryThesisCandidateWorkbenchService(session).candidate_source_options(
            session_id=UUID(created["session_id"]),
            session_revision_id=UUID(created["session_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BASE + timedelta(minutes=2),
        )
    assert options["build_allowed"] is True
    assert options["company_seed_count"] == 1
    assert options["company_seeds"][0]["stock_basic_record_id"] == values["stock_a_id"]
    assert options["map_count"] == 1
    assert options["maps"][0]["eligible_candidate_pool_count"] == 1
    pool = options["maps"][0]["eligible_candidate_pools"][0]
    assert pool["candidate_pool_revision_id"] == str(values["pool_revision_id"])
    assert pool["selected"] is False
    assert options["notices"]["first_pool_not_selected"] is True


def test_draft_revision_cannot_compose_candidate_build(database) -> None:
    values, session_input = _seed_graph(database)
    created = _created_session(database, session_input, workflow="draft")
    with database() as session:
        service = IndustryThesisCandidateWorkbenchService(session)
        with pytest.raises(IndustryThesisError, match="candidate_build_ready"):
            service.compose_candidate_build(
                session_id=UUID(created["session_id"]),
                session_revision_id=UUID(created["session_revision_id"]),
                expected_session_latest_revision_number=1,
                selected_candidate_pool_revision_ids=[values["pool_revision_id"]],
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=BASE + timedelta(minutes=2),
            )


def test_three_path_build_preserves_same_company_from_two_exact_sources(database) -> None:
    values, session_input = _seed_graph(database)
    created = _created_session(database, session_input)
    with database() as session:
        command, summary = IndustryThesisCandidateWorkbenchService(session).compose_candidate_build(
            session_id=UUID(created["session_id"]),
            session_revision_id=UUID(created["session_revision_id"]),
            expected_session_latest_revision_number=1,
            selected_candidate_pool_revision_ids=[values["pool_revision_id"]],
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BASE + timedelta(minutes=2),
        )
    assert summary["proposal_count"] == 3
    assert summary["company_seed_proposal_count"] == 1
    assert summary["stage1_proposal_count"] == 2
    assert [item["source_kind"] for item in command["proposals"]].count("user_seed") == 1
    assert [item["source_kind"] for item in command["proposals"]].count("existing_industry_map_revision") == 2
    assert [item.get("proposed_stock_basic_record_id") for item in command["proposals"]].count(values["stock_a_id"]) == 2

    dry_run = IndustryThesisWorkbenchCandidateCommandService(
        database,
        clock=SequenceClock(BASE + timedelta(minutes=3)),
    ).build_candidates(command, dry_run=True)
    assert dry_run["candidate_count"] == 3
    with database() as session:
        assert session.scalar(select(func.count()).select_from(IndustryThesisCandidateIdentity)) == 0
        assert session.scalar(select(func.count()).select_from(IndustryThesisCandidateRevision)) == 0

    committed = IndustryThesisWorkbenchCandidateCommandService(
        database,
        clock=SequenceClock(BASE + timedelta(minutes=4)),
    ).build_candidates(command)
    assert committed["candidate_count"] == 3
    with database() as session:
        assert session.scalar(select(func.count()).select_from(IndustryThesisCandidateIdentity)) == 3
        assert session.scalar(select(func.count()).select_from(IndustryThesisCandidateRevision)) == 3
        universe = IndustryThesisQueryService(session).list_candidate_revisions(
            UUID(created["session_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BASE + timedelta(minutes=5),
        )
    assert universe["candidate_count"] == 3
    assert [row["proposed_exposure_type"] for row in universe["candidates"]] == ["unknown", "unknown", "unknown"]
    assert [row["review_state"] for row in universe["candidates"]] == ["proposed", "proposed", "proposed"]

    with pytest.raises(IndustryThesisError, match="exact latest revision"):
        IndustryThesisWorkbenchCandidateCommandService(
            database,
            clock=SequenceClock(BASE + timedelta(minutes=6)),
        ).build_candidates(command)
    with database() as session:
        assert session.scalar(select(func.count()).select_from(IndustryThesisCandidateRevision)) == 3
