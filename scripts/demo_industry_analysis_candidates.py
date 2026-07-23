"""Offline three-path demo for Personal Research Workbench UI Phase 1C."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

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
from industry_alpha.industry_thesis_models import IndustryThesisCandidateRevision
from industry_alpha.industry_thesis_query import IndustryThesisQueryService
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
BASE = datetime(2026, 7, 23, 2, 0, tzinfo=UTC)
CUTOFF = date(2026, 7, 23)


class SequenceClock:
    def __init__(self, *values: datetime) -> None:
        self._values = iter(values)

    def __call__(self) -> datetime:
        return next(self._values)


def _ingestion() -> IngestionRun:
    return IngestionRun(
        batch_identifier="phase1c-demo",
        series_key="c" * 64,
        series_identity={"kind": "stock_basic", "demo": "phase1c"},
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
        row_count_received=2,
        row_count_written=2,
        dataset_counts={"stock_basic": 2},
    )


def _session_payload(seed: StockBasicRecord, map_revision: IndustryMapRevision) -> dict:
    return {
        "thesis_text_original": "AI 数据中心扩张带动电子特气需求",
        "thesis_title_reviewed": "电子特气需求与认证",
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
                "exact_id": str(seed.id),
                "stock_basic_record_id": seed.id,
                "listed_instrument_id": None,
                "label": seed.stock_name,
                "code": seed.stock_code,
            }
        ],
        "seed_products": ["高纯电子气体"],
        "seed_technologies": ["气体纯化"],
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
        "workflow_state": "candidate_build_ready",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "Phase 1C offline demo scope",
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
        with factory.begin() as session:
            run = _ingestion()
            session.add(run)
            session.flush()
            stocks = [
                StockBasicRecord(
                    ingestion_run_id=run.id,
                    stock_code="688001.SH",
                    stock_name="示例公司A",
                    exchange="SSE",
                    industry="电子特气",
                    listing_date=date(2020, 1, 1),
                    status="active",
                    source="fixture",
                ),
                StockBasicRecord(
                    ingestion_run_id=run.id,
                    stock_code="688002.SH",
                    stock_name="示例公司B",
                    exchange="SSE",
                    industry="电子特气",
                    listing_date=date(2020, 1, 2),
                    status="active",
                    source="fixture",
                ),
            ]
            session.add_all(stocks)
            session.flush()
            case = ResearchCase(
                case_key="phase1c-demo-electronic-gases",
                created_at_utc=BASE,
                origin="fixture",
            )
            session.add(case)
            session.flush()
            industry_map = IndustryMap(
                case_id=case.id,
                map_key="phase1c-demo-map",
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
            beneficiary_rows = []
            for index, (stock, kind) in enumerate(zip(stocks, ("direct", "secondary")), start=1):
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
                    rationale_summary=f"{stock.stock_name} 冻结在本地 Stage 1 候选池。",
                    information_cutoff_date=CUTOFF,
                    recorded_at_utc=BASE + timedelta(seconds=index),
                    supersedes_revision_id=None,
                )
                session.add(revision)
                session.flush()
                beneficiary_rows.append((beneficiary, revision))
            pool = Stage1CandidatePool(
                case_id=case.id,
                map_id=industry_map.id,
                pool_key="phase1c-demo-complete-pool",
                created_at_utc=BASE + timedelta(seconds=3),
            )
            session.add(pool)
            session.flush()
            pool_revision = Stage1CandidatePoolRevision(
                candidate_pool_id=pool.id,
                revision_no=1,
                selected_map_revision_id=map_revision.id,
                title="电子特气冻结候选池",
                scope="两个受益公司",
                information_cutoff_date=CUTOFF,
                recorded_at_utc=BASE + timedelta(seconds=4),
                supersedes_revision_id=None,
            )
            session.add(pool_revision)
            session.flush()
            for index, (beneficiary, revision) in enumerate(beneficiary_rows, start=1):
                session.add(
                    Stage1CandidatePoolMembership(
                        candidate_pool_revision_id=pool_revision.id,
                        beneficiary_id=beneficiary.id,
                        beneficiary_revision_id=revision.id,
                        recorded_at_utc=BASE + timedelta(seconds=4 + index),
                    )
                )
            session.flush()
            seed_id = stocks[0].id
            map_revision_id = map_revision.id
            pool_revision_id = pool_revision.id

        with factory() as session:
            seed = session.get(StockBasicRecord, seed_id)
            map_revision = session.get(IndustryMapRevision, map_revision_id)
            payload = _session_payload(seed, map_revision)
        created = IndustryThesisCommandService(
            factory,
            clock=SequenceClock(BASE + timedelta(minutes=1)),
        ).create_session(payload)

        with factory() as session:
            source_options = IndustryThesisCandidateWorkbenchService(session).candidate_source_options(
                session_id=UUID(created["session_id"]),
                session_revision_id=UUID(created["session_revision_id"]),
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=BASE + timedelta(minutes=2),
            )
            command, composition = IndustryThesisCandidateWorkbenchService(session).compose_candidate_build(
                session_id=UUID(created["session_id"]),
                session_revision_id=UUID(created["session_revision_id"]),
                expected_session_latest_revision_number=1,
                selected_candidate_pool_revision_ids=[pool_revision_id],
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=BASE + timedelta(minutes=2),
            )
        assert source_options["company_seed_count"] == 1
        assert source_options["maps"][0]["eligible_candidate_pools"][0]["selected"] is False
        assert composition["proposal_count"] == 3

        dry_run = IndustryThesisWorkbenchCandidateCommandService(
            factory,
            clock=SequenceClock(BASE + timedelta(minutes=3)),
        ).build_candidates(command, dry_run=True)
        assert dry_run["candidate_count"] == 3
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(IndustryThesisCandidateRevision)) == 0

        committed = IndustryThesisWorkbenchCandidateCommandService(
            factory,
            clock=SequenceClock(BASE + timedelta(minutes=4)),
        ).build_candidates(command)
        with factory() as session:
            universe = IndustryThesisQueryService(session).list_candidate_revisions(
                UUID(created["session_revision_id"]),
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=BASE + timedelta(minutes=5),
            )
        assert committed["candidate_count"] == 3
        assert universe["candidate_count"] == 3
        assert all(row["review_state"] == "proposed" for row in universe["candidates"])
        return {
            "source_options": source_options,
            "composition": composition,
            "dry_run": dry_run,
            "committed": committed,
            "universe": universe,
        }
    finally:
        engine.dispose()


def main() -> None:
    print(json.dumps(run_demo(), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
