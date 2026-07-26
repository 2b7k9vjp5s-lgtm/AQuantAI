from __future__ import annotations

from datetime import date, timedelta
import json
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from sqlalchemy import select, update

from backend.database.models import IngestionRun, StockBasicRecord
from industry_alpha.industry_thesis_models import IndustryThesisSessionRevision
from industry_alpha.industry_thesis_owner_acceptance_workbench import (
    IndustryThesisOwnerAcceptanceWorkbenchQueryService,
)
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
    READ_BOUNDARY,
    _accepted_result,
    _build_reviewed,
    _commit,
    _map_header,
    _preview,
    _view,
    api_client,
    build_golden_fixture,
    golden_plan,
    new_database,
    run_demo,
    statement_counter,
)


def test_offline_demo_proves_golden_zero_supported_and_query_ceilings() -> None:
    result = run_demo()
    golden = result["golden_path"]
    zero = result["zero_supported_path"]

    assert golden["complete_universe_count"] == 3
    assert golden["supported_handoff_count"] == 2
    assert golden["candidate_pool_mode"] == "create_supported_handoff"
    assert golden["assessment_statuses"] == ["supported", "draft", "supported"]
    assert golden["semantic_covered_count"] == 1
    assert golden["preview_zero_writes"] is True
    assert golden["acceptance_view_sql_statements"] <= 14
    assert golden["accepted_result_sql_statements"] <= 10
    assert golden["company_research_created"] is False

    assert zero["complete_universe_count"] == 2
    assert zero["supported_handoff_count"] == 0
    assert zero["candidate_pool_mode"] == "none_no_supported_members"
    assert zero["accepted_candidate_pool_revision_id"] is None
    assert zero["zero_supported_notice"]
    assert result["notices"]["external_network"] is False
    assert result["notices"]["provider_or_ai"] is False
    assert result["notices"]["recommendation_or_trading"] is False


def test_accepted_result_respects_recorded_boundary_and_fails_closed_on_corruption() -> None:
    fixture = build_golden_fixture()
    try:
        with api_client(fixture.database) as client:
            view = _view(client, fixture.reviewed)
            plan = golden_plan(view)
            preview = _preview(client, fixture.reviewed, plan)
            committed = _commit(
                client,
                fixture.reviewed,
                plan,
                preview["preview_fingerprint_sha256"],
            )

            early = client.get(
                f"/industry-analysis/api/session-revisions/"
                f"{committed['accepted_session_revision_id']}/accepted-result-view",
                params={
                    "session_id": str(fixture.reviewed.session_id),
                    "as_of_cutoff": CUTOFF.isoformat(),
                    "as_of_recorded_at_utc": (
                        BASE_TIME + timedelta(seconds=2)
                    ).isoformat(),
                },
            )
            assert early.status_code == 422
            assert early.json()["detail"]["code"] == (
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )

            with fixture.database.factory.begin() as session:
                session.execute(
                    update(IndustryThesisSessionRevision)
                    .where(
                        IndustryThesisSessionRevision.id
                        == UUID(committed["accepted_session_revision_id"])
                    )
                    .values(draft_graph_json=json.dumps({"corrupt": True}))
                )

            parsed = urlparse(committed["accepted_result_path"])
            boundary = {
                key: values[-1] for key, values in parse_qs(parsed.query).items()
            }
            corrupt = client.get(
                f"/industry-analysis/api/session-revisions/"
                f"{committed['accepted_session_revision_id']}/accepted-result-view",
                params={"session_id": str(fixture.reviewed.session_id), **boundary},
            )
            assert corrupt.status_code == 422
            assert corrupt.json()["detail"]["code"] == (
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )
    finally:
        fixture.database.engine.dispose()


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
            code = f"9{index:05d}"
            stock = StockBasicRecord(
                ingestion_run_id=run.id,
                stock_code=code,
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
            recorded_at_utc=BASE_TIME - timedelta(minutes=30) + timedelta(
                seconds=index
            ),
        )

    with database.factory() as session:
        return [session.get(StockBasicRecord, stock_id) for stock_id in stock_ids]


def test_twenty_member_acceptance_view_stays_within_fixed_sql_ceiling() -> None:
    database = new_database()
    try:
        stocks = _many_member_stocks(database, count=20)
        assert all(stock is not None for stock in stocks)
        reviewed = _build_reviewed(
            database.factory,
            [stock for stock in stocks if stock is not None],
            title="普通用户二十公司查询上限",
        )
        with database.factory() as session:
            with statement_counter(database.engine) as statements:
                view = IndustryThesisOwnerAcceptanceWorkbenchQueryService(
                    session
                ).get_acceptance_view(
                    session_id=reviewed.session_id,
                    reviewed_session_revision_id=reviewed.reviewed_session_revision_id,
                    as_of_cutoff=CUTOFF,
                    as_of_recorded_at_utc=READ_BOUNDARY,
                )
        assert len(view["members"]) == 20
        assert view["commit_possible"] is True
        assert len(statements) <= 14
    finally:
        database.engine.dispose()
