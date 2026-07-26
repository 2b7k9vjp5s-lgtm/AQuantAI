from __future__ import annotations

from contextlib import contextmanager
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import event, select

from backend.database.models import IngestionRun, StockBasicRecord
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.industry_research_result_query import (
    IndustryResearchResultQueryService,
)
from industry_alpha.industry_thesis_owner_acceptance import (
    IndustryThesisOwnerAcceptanceService,
)
from industry_alpha.stage1_commands import (
    MapAssertionRevisionInput,
    Stage1BeneficiaryCommandService,
)
from industry_alpha.stage1_fixtures import build_stage1_beneficiary_fixture
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryAssertionLink,
    Stage1BeneficiaryClaimLink,
    Stage1BeneficiaryRevision,
)
from scripts.demo_industry_research_result_assembly import (
    seed_industry_research_result_demo,
)
from tests import test_industry_thesis_owner_acceptance as owner_fixture
from tests.test_industry_research_result_query import database


@contextmanager
def statement_counter(engine):
    statements: list[str] = []

    def before_cursor_execute(
        _connection, _cursor, statement, _parameters, _context, _executemany
    ) -> None:
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def _twenty_member_accepted_output(database) -> str:
    fixture = build_stage1_beneficiary_fixture(database)
    with database() as session:
        reference = session.scalar(
            select(Stage1BeneficiaryRevision)
            .where(
                Stage1BeneficiaryRevision.beneficiary_id
                == fixture.direct_beneficiary_id
            )
            .order_by(Stage1BeneficiaryRevision.revision_no.desc())
        )
        assertion_link = session.scalar(
            select(Stage1BeneficiaryAssertionLink).where(
                Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                == reference.id
            )
        )
        claim_link = session.scalar(
            select(Stage1BeneficiaryClaimLink).where(
                Stage1BeneficiaryClaimLink.beneficiary_revision_id == reference.id
            )
        )
        beneficiary = session.get(
            Stage1Beneficiary,
            fixture.direct_beneficiary_id,
        )
        industry_map = session.get(IndustryMap, beneficiary.map_id)
        map_revision = session.scalar(
            select(IndustryMapRevision)
            .where(IndustryMapRevision.map_id == industry_map.id)
            .order_by(IndustryMapRevision.revision_no.desc())
        )
    if assertion_link.node_revision_id is not None:
        assertion = MapAssertionRevisionInput(
            "node",
            assertion_link.node_revision_id,
        )
    elif assertion_link.relationship_revision_id is not None:
        assertion = MapAssertionRevisionInput(
            "relationship",
            assertion_link.relationship_revision_id,
        )
    else:
        assertion = MapAssertionRevisionInput(
            "observation",
            assertion_link.observation_revision_id,
        )

    with database.begin() as session:
        run = IngestionRun(
            batch_identifier="industry-result-scale",
            series_key="7" * 64,
            series_identity={"fixture": "industry-result-scale"},
            provider="fixture-scale",
            dataset="stock_basic",
            imported_at=owner_fixture.BASE_TIME - timedelta(hours=3),
            completed_at=owner_fixture.BASE_TIME - timedelta(hours=2),
            requested_start_date=date(2026, 7, 1),
            requested_end_date=owner_fixture.CUTOFF,
            information_cutoff_date=owner_fixture.CUTOFF,
            requested_scope={"member_count": 20},
            provider_request_metadata={"network_access": False},
            adapter_version="industry-result-scale-v1",
            snapshot_mode="complete",
            contract_version="normalized-v1",
            status="succeeded",
            row_count_received=20,
            row_count_written=20,
            dataset_counts={"stock_basic": 20},
        )
        session.add(run)
        session.flush()
        stock_refs = []
        for index in range(20):
            stock_code = f"8{index:05d}"
            stock = StockBasicRecord(
                ingestion_run_id=run.id,
                stock_code=stock_code,
                stock_name=f"Result Scale Co {index + 1}",
                exchange="SZSE",
                industry="Fixture scale industry",
                listing_date=date(2020, 1, 1),
                status="listed",
                source="fixture-scale",
            )
            session.add(stock)
            session.flush()
            stock_refs.append((stock.id, stock_code))

    commands = Stage1BeneficiaryCommandService(database)
    beneficiary_ids = []
    for index, (stock_id, stock_code) in enumerate(stock_refs):
        created = commands.create_beneficiary(
            industry_map.case_id,
            industry_map.id,
            source="fixture-scale",
            stock_code=stock_code,
            selected_map_revision_id=map_revision.id,
            stock_basic_record_id=stock_id,
            beneficiary_kind="direct" if index % 2 == 0 else "secondary",
            assessment_status="supported" if index % 3 else "draft",
            rationale_summary="Exact scale fixture for assembled-result query ceiling.",
            information_cutoff_date=owner_fixture.CUTOFF,
            assertion_revisions=(assertion,),
            claim_revision_ids=(claim_link.claim_revision_id,),
            recorded_at_utc=(
                owner_fixture.BASE_TIME
                - timedelta(minutes=30)
                + timedelta(seconds=index)
            ),
        )
        beneficiary_ids.append(created.id)

    reviewed, reviewed_map, reviewed_map_revision, owner_rows = (
        owner_fixture._build_reviewed(
            database,
            beneficiary_ids=tuple(beneficiary_ids),
        )
    )
    payload = owner_fixture._acceptance_input(
        reviewed,
        reviewed_map,
        reviewed_map_revision,
        owner_rows,
        pool_mode="create_supported_handoff",
    )
    service = IndustryThesisOwnerAcceptanceService(
        database,
        clock=lambda: owner_fixture.BASE_TIME + timedelta(seconds=4),
    )
    preview = service.preview(payload)
    assert preview["commit_ready"] is True
    committed = service.commit(
        {
            **payload,
            "preview_fingerprint_sha256": preview[
                "preview_fingerprint_sha256"
            ],
        }
    )
    return committed["output_link_revision_id"]


def _query_count(database, output_link_revision_id: str) -> tuple[int, dict]:
    engine = database.kw["bind"]
    with database() as session:
        with statement_counter(engine) as statements:
            result = IndustryResearchResultQueryService(
                session
            ).get_assembled_result(
                UUID(output_link_revision_id),
                as_of_cutoff=owner_fixture.CUTOFF,
                as_of_recorded_at_utc=owner_fixture.BASE_TIME
                + timedelta(seconds=6),
            )
    return len(statements), result


def test_twenty_member_assembled_result_has_fixed_query_ceiling(database) -> None:
    three_member = seed_industry_research_result_demo(database)
    three_count, three_result = _query_count(
        database,
        three_member["output_link_revision_id"],
    )
    twenty_member_output = _twenty_member_accepted_output(database)
    twenty_count, twenty_result = _query_count(database, twenty_member_output)

    assert three_result["accepted_snapshot"]["complete_member_count"] == 3
    assert twenty_result["accepted_snapshot"]["complete_member_count"] == 20
    assert twenty_count <= 40
    assert twenty_count <= three_count + 2
