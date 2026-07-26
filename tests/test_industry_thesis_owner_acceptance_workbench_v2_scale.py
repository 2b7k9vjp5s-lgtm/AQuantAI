from __future__ import annotations

from contextlib import contextmanager
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import create_engine, event, select
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base, IngestionRun, StockBasicRecord
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.industry_thesis_owner_acceptance_workbench import (
    IndustryThesisOwnerAcceptanceWorkbenchQueryService,
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
from tests import test_industry_thesis_owner_acceptance as owner_fixture


@contextmanager
def statement_counter(engine):
    statements: list[str] = []

    def before_cursor_execute(
        _connection,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def test_twenty_member_context_bound_view_has_fixed_query_ceiling() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    database = build_session_factory(engine)
    try:
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
                    Stage1BeneficiaryClaimLink.beneficiary_revision_id
                    == reference.id
                )
            )
            beneficiary = session.get(Stage1Beneficiary, fixture.direct_beneficiary_id)
            industry_map = session.get(IndustryMap, beneficiary.map_id)
            map_revision = session.scalar(
                select(IndustryMapRevision)
                .where(IndustryMapRevision.map_id == industry_map.id)
                .order_by(IndustryMapRevision.revision_no.desc())
            )
        assert reference is not None
        assert assertion_link is not None
        assert claim_link is not None
        assert industry_map is not None
        assert map_revision is not None
        if assertion_link.node_revision_id is not None:
            assertion = MapAssertionRevisionInput(
                "node", assertion_link.node_revision_id
            )
        elif assertion_link.relationship_revision_id is not None:
            assertion = MapAssertionRevisionInput(
                "relationship", assertion_link.relationship_revision_id
            )
        else:
            assertion = MapAssertionRevisionInput(
                "observation", assertion_link.observation_revision_id
            )

        with database.begin() as session:
            run = IngestionRun(
                batch_identifier="owner-context-v2-scale",
                series_key="8" * 64,
                series_identity={"fixture": "owner-context-v2-scale"},
                provider="fixture-scale",
                dataset="stock_basic",
                imported_at=owner_fixture.BASE_TIME - timedelta(hours=3),
                completed_at=owner_fixture.BASE_TIME - timedelta(hours=2),
                requested_start_date=date(2026, 7, 1),
                requested_end_date=owner_fixture.CUTOFF,
                information_cutoff_date=owner_fixture.CUTOFF,
                requested_scope={"member_count": 20},
                provider_request_metadata={"network_access": False},
                adapter_version="owner-context-v2-scale-v1",
                snapshot_mode="complete",
                contract_version="normalized-v1",
                status="succeeded",
                row_count_received=20,
                row_count_written=20,
                dataset_counts={"stock_basic": 20},
            )
            session.add(run)
            session.flush()
            stock_refs: list[tuple[int, str]] = []
            for index in range(20):
                stock_code = f"9{index:05d}"
                stock = StockBasicRecord(
                    ingestion_run_id=run.id,
                    stock_code=stock_code,
                    stock_name=f"Fixture Scale Co {index + 1}",
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
                rationale_summary="Exact scale fixture for bounded query verification.",
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

        review, _map, _revision, _rows = owner_fixture._build_reviewed(
            database,
            beneficiary_ids=tuple(beneficiary_ids),
        )
        with database() as session:
            with statement_counter(engine) as statements:
                view = IndustryThesisOwnerAcceptanceWorkbenchQueryService(
                    session
                ).get_acceptance_view(
                    session_id=UUID(review["acceptance_plan"]["session_id"]),
                    reviewed_session_revision_id=UUID(
                        review["reviewed_session_revision_id"]
                    ),
                    as_of_cutoff=owner_fixture.CUTOFF,
                    as_of_recorded_at_utc=(
                        owner_fixture.BASE_TIME + timedelta(seconds=3)
                    ),
                )
        assert len(view["members"]) == 20
        assert view["commit_possible"] is True
        assert len(statements) <= 14
    finally:
        engine.dispose()
