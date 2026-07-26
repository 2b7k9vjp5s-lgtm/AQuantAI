from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from backend.database.models import IngestionRun, StockBasicRecord
from industry_alpha.stage1_commands import (
    MapAssertionRevisionInput,
    Stage1BeneficiaryCommandService,
)
from industry_alpha.stage1_fixtures import build_stage1_beneficiary_fixture
from industry_alpha.stage1_models import (
    Stage1BeneficiaryAssertionLink,
    Stage1BeneficiaryClaimLink,
    Stage1BeneficiaryRevision,
)
from scripts.run_industry_thesis_ordinary_user_acceptance_fixture import (
    BASE_TIME,
    CUTOFF,
    _map_header,
    new_database,
)


def _many_member_stocks(database, *, count: int) -> list[StockBasicRecord]:
    fixture = build_stage1_beneficiary_fixture(database.factory)
    with database.factory() as session:
        reference_revision = session.scalar(
            select(Stage1BeneficiaryRevision)
            .where(
                Stage1BeneficiaryRevision.beneficiary_id
                == fixture.direct_beneficiary_id
            )
            .order_by(Stage1BeneficiaryRevision.revision_no.desc())
        )
        assert reference_revision is not None
        assertion_link = session.scalar(
            select(Stage1BeneficiaryAssertionLink).where(
                Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                == reference_revision.id
            )
        )
        claim_link = session.scalar(
            select(Stage1BeneficiaryClaimLink).where(
                Stage1BeneficiaryClaimLink.beneficiary_revision_id
                == reference_revision.id
            )
        )
        assert assertion_link is not None
        assert claim_link is not None

    industry_map, map_revision = _map_header(
        database.factory, fixture.direct_beneficiary_id
    )
    if assertion_link.node_revision_id is not None:
        assertion = MapAssertionRevisionInput(
            "node", assertion_link.node_revision_id
        )
    elif assertion_link.relationship_revision_id is not None:
        assertion = MapAssertionRevisionInput(
            "relationship", assertion_link.relationship_revision_id
        )
    else:
        assert assertion_link.observation_revision_id is not None
        assertion = MapAssertionRevisionInput(
            "observation", assertion_link.observation_revision_id
        )

    with database.factory.begin() as session:
        run = IngestionRun(
            batch_identifier="ordinary-user-20-member-snapshot",
            series_key="8" * 64,
            series_identity={"fixture": "ordinary-user-20-member"},
            provider="fixture",
            dataset="stock_basic",
            imported_at=BASE_TIME - timedelta(hours=3),
            completed_at=BASE_TIME - timedelta(hours=2),
            requested_start_date=date(2026, 7, 1),
            requested_end_date=date(2026, 7, 9),
            information_cutoff_date=CUTOFF,
            requested_scope={"member_count": count},
            provider_request_metadata={"network_access": False},
            adapter_version="ordinary-user-20-member-v1",
            snapshot_mode="complete",
            contract_version="normalized-v1",
            status="succeeded",
            row_count_received=count,
            row_count_written=count,
            dataset_counts={"stock_basic": count},
        )
        session.add(run)
        session.flush()
        stock_ids: list[int] = []
        for index in range(count):
            stock = StockBasicRecord(
                ingestion_run_id=run.id,
                stock_code=f"9{index:05d}",
                stock_name=f"Fixture Scale Co {index + 1}",
                exchange="SZSE",
                industry="Fixture scale industry",
                listing_date=date(2020, 1, 1),
                status="listed",
                source="fixture-scale",
            )
            session.add(stock)
            session.flush()
            stock_ids.append(stock.id)

    commands = Stage1BeneficiaryCommandService(database.factory)
    for index, stock_id in enumerate(stock_ids):
        commands.create_beneficiary(
            industry_map.case_id,
            industry_map.id,
            source="fixture-scale",
            stock_code=f"9{index:05d}",
            selected_map_revision_id=map_revision.id,
            stock_basic_record_id=stock_id,
            beneficiary_kind="direct" if index % 2 == 0 else "secondary",
            assessment_status="supported" if index % 3 else "draft",
            rationale_summary="Exact scale fixture for bounded query verification.",
            information_cutoff_date=CUTOFF,
            assertion_revisions=(assertion,),
            claim_revision_ids=(claim_link.claim_revision_id,),
            recorded_at_utc=BASE_TIME - timedelta(minutes=30)
            + timedelta(seconds=index),
        )

    with database.factory() as session:
        stocks = [session.get(StockBasicRecord, stock_id) for stock_id in stock_ids]
        assert all(stock is not None for stock in stocks)
        return [stock for stock in stocks if stock is not None]


def test_twenty_member_stage1_fixture_is_complete() -> None:
    database = new_database()
    try:
        stocks = _many_member_stocks(database, count=20)
        assert len(stocks) == 20
    finally:
        database.engine.dispose()
