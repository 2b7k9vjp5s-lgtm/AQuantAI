"""Production-realistic zero-network demo for ordinary-user Industry Thesis acceptance."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
from typing import Any, Iterator
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import backend.api.industry_analysis_acceptance as acceptance_api
from backend.database.engine import build_session_factory
from backend.database.models import Base, IngestionRun, StockBasicRecord
from backend.main import app
from industry_alpha.beneficiary_semantics_contracts import TAXONOMY_VERSION
from industry_alpha.beneficiary_semantics_models import (
    Stage1BeneficiarySemanticProfile,
    Stage1BeneficiarySemanticProfileRevision,
)
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_models import (
    IndustryThesisOutputLinkIdentity,
    IndustryThesisOutputLinkRevision,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_owner_acceptance import IndustryThesisOwnerAcceptanceService
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    OWNER_ACCEPTANCE_PLAN_VERSION,
)
from industry_alpha.industry_thesis_review import (
    ACCEPTANCE_PLAN_VERSION,
    IndustryThesisProposalReviewService,
)
from industry_alpha.industry_thesis_rules import BUILDER_VERSION
from industry_alpha.stage1_fixtures import build_stage1_beneficiary_fixture
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryRevision,
    Stage1CandidatePool,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)
from industry_alpha.stage2_models import Stage2CompanyResearch

UTC = timezone.utc
CUTOFF = date(2026, 7, 9)
BASE_TIME = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
COMMIT_TIME = BASE_TIME + timedelta(seconds=3)
READ_BOUNDARY = COMMIT_TIME + timedelta(seconds=1)


@dataclass(frozen=True)
class LocalDatabase:
    engine: Engine
    factory: sessionmaker[Session]


@dataclass(frozen=True)
class ReviewedFixture:
    session_id: UUID
    reviewed_session_revision_id: UUID
    review: dict[str, Any]


@dataclass(frozen=True)
class GoldenFixture:
    database: LocalDatabase
    reviewed: ReviewedFixture
    semantic_profile_id: UUID
    semantic_profile_revision_id: UUID


def new_database() -> LocalDatabase:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return LocalDatabase(engine, build_session_factory(engine))


def _session_input(title: str) -> dict[str, Any]:
    return {
        "thesis_text_original": f"{title}：需求扩张、工艺瓶颈与客户认证",
        "thesis_title_reviewed": title,
        "driver_type": "demand_expansion",
        "analysis_horizon_kind": "medium_term",
        "market_scope": [
            {
                "market_namespace": "CN_A",
                "exchange_namespace": None,
                "security_type": "common_equity",
                "include_status": "active",
                "listed_instrument_ids": [],
            }
        ],
        "chain_boundary": {"included": ["materials", "processing", "certification"]},
        "exclusions": [],
        "seed_companies": [],
        "seed_products": ["fixture-product"],
        "seed_technologies": [],
        "seed_bottlenecks": ["fixture-bottleneck"],
        "draft_graph": {"nodes": [], "relationships": []},
        "coverage_state": "partial_local_coverage",
        "workflow_state": "candidate_build_ready",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "ordinary-user acceptance offline fixture",
    }


def _latest_owner_row(
    factory: sessionmaker[Session], beneficiary_id: UUID
) -> tuple[Stage1Beneficiary, Stage1BeneficiaryRevision, StockBasicRecord]:
    with factory() as session:
        beneficiary = session.get(Stage1Beneficiary, beneficiary_id)
        revision = session.scalar(
            select(Stage1BeneficiaryRevision)
            .where(Stage1BeneficiaryRevision.beneficiary_id == beneficiary_id)
            .order_by(Stage1BeneficiaryRevision.revision_no.desc())
        )
        if beneficiary is None or revision is None:
            raise AssertionError("fixture beneficiary graph is incomplete")
        stock = session.get(StockBasicRecord, revision.stock_basic_record_id)
        if stock is None:
            raise AssertionError("fixture stock identity is missing")
        return beneficiary, revision, stock


def _map_header(
    factory: sessionmaker[Session], beneficiary_id: UUID
) -> tuple[IndustryMap, IndustryMapRevision]:
    with factory() as session:
        beneficiary = session.get(Stage1Beneficiary, beneficiary_id)
        if beneficiary is None:
            raise AssertionError("fixture beneficiary is missing")
        industry_map = session.get(IndustryMap, beneficiary.map_id)
        revision = session.scalar(
            select(IndustryMapRevision)
            .where(IndustryMapRevision.map_id == beneficiary.map_id)
            .order_by(IndustryMapRevision.revision_no.desc())
        )
        if industry_map is None or revision is None:
            raise AssertionError("fixture map graph is incomplete")
        return industry_map, revision


def _create_stock_only(factory: sessionmaker[Session]) -> StockBasicRecord:
    code = "000099"
    with factory.begin() as session:
        run = IngestionRun(
            batch_identifier="ordinary-user-stock-only-000099",
            series_key="2" * 64,
            series_identity={"fixture": "ordinary-user-stock-only"},
            provider="fixture",
            dataset="stock_basic",
            imported_at=BASE_TIME - timedelta(days=2, hours=1),
            completed_at=BASE_TIME - timedelta(days=2),
            requested_start_date=date(2026, 7, 1),
            requested_end_date=date(2026, 7, 8),
            information_cutoff_date=date(2026, 7, 8),
            requested_scope={"stock_codes": [code]},
            provider_request_metadata={"network_access": False},
            adapter_version="ordinary-user-fixture-v1",
            snapshot_mode="complete",
            contract_version="normalized-v1",
            status="succeeded",
            row_count_received=1,
            row_count_written=1,
            dataset_counts={"stock_basic": 1},
        )
        session.add(run)
        session.flush()
        stock = StockBasicRecord(
            ingestion_run_id=run.id,
            stock_code=code,
            stock_name="Fixture Create Co",
            exchange="SZSE",
            industry="Fixture industry",
            listing_date=date(2020, 1, 1),
            status="listed",
            source="fixture",
        )
        session.add(stock)
        session.flush()
        stock_id = stock.id
    with factory() as session:
        result = session.get(StockBasicRecord, stock_id)
        if result is None:
            raise AssertionError("stock-only fixture was not persisted")
        return result


def _create_semantic_revision(
    factory: sessionmaker[Session],
    beneficiary: Stage1Beneficiary,
    revision: Stage1BeneficiaryRevision,
    map_revision: IndustryMapRevision,
) -> tuple[UUID, UUID]:
    with factory.begin() as session:
        profile = Stage1BeneficiarySemanticProfile(
            beneficiary_id=beneficiary.id,
            created_at_utc=BASE_TIME - timedelta(hours=2),
        )
        session.add(profile)
        session.flush()
        semantic_revision = Stage1BeneficiarySemanticProfileRevision(
            profile_id=profile.id,
            revision_no=1,
            beneficiary_revision_id=revision.id,
            selected_map_revision_id=map_revision.id,
            taxonomy_version=TAXONOMY_VERSION,
            overall_status="supported",
            summary="Fixture semantic profile freezes the exact supported revision.",
            recorded_by="offline_fixture",
            information_cutoff_date=CUTOFF,
            recorded_at_utc=BASE_TIME - timedelta(hours=1),
            supersedes_revision_id=None,
        )
        session.add(semantic_revision)
        session.flush()
        return profile.id, semantic_revision.id


def _build_reviewed(
    factory: sessionmaker[Session],
    stocks: list[StockBasicRecord],
    *,
    title: str,
) -> ReviewedFixture:
    created = IndustryThesisCommandService(factory, clock=lambda: BASE_TIME).create_session(
        _session_input(title)
    )
    exposures = ("direct", "conditional", "indirect")
    proposals = [
        {
            "source_kind": "accepted_local_mapping",
            "source_reference": {"fixture_binding": f"ordinary-owner-{index}"},
            "proposed_stock_basic_record_id": stock.id,
            "company_label_original": stock.stock_name,
            "product_or_service_fit": "Fixture product and service fit.",
            "industry_position": "Fixture industry-chain position.",
            "benefit_path_text": "Fixture evidence-backed benefit path.",
            "proposed_exposure_type": exposures[index % len(exposures)],
            "proposal_confidence": "medium",
            "identity_state": "exact_accepted_identity",
            "review_state": "proposed",
            "rationale": {"reason": "explicit local stock_basic identity"},
            "uncertainty": {"state": "review_required"},
        }
        for index, stock in enumerate(stocks)
    ]
    built = IndustryThesisCommandService(
        factory, clock=lambda: BASE_TIME + timedelta(seconds=1)
    ).build_candidates(
        {
            "session_revision_id": created["session_revision_id"],
            "expected_session_latest_revision_number": 1,
            "builder_version": BUILDER_VERSION,
            "allowed_source_kinds": ["accepted_local_mapping"],
            "proposals": proposals,
        }
    )
    review = IndustryThesisProposalReviewService(
        factory, clock=lambda: BASE_TIME + timedelta(seconds=2)
    ).review_candidates(
        {
            "session_revision_id": created["session_revision_id"],
            "expected_session_latest_revision_number": 1,
            "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
            "decisions": [
                {
                    "candidate_revision_id": item["candidate_revision_id"],
                    "expected_latest_revision_number": 1,
                    "decision": "selected_for_acceptance",
                    "final_proposed_exposure_type": item["proposed_exposure_type"],
                    "rationale": {"reason": "explicit ordinary-user fixture selection"},
                    "uncertainty": {"state": "reviewed_local_scope"},
                }
                for item in built["candidates"]
            ],
            "revision_note": "selected exact owner-bound candidates",
        }
    )
    reviewed_id = UUID(review["reviewed_session_revision_id"])
    with factory() as session:
        reviewed_row = session.get(IndustryThesisSessionRevision, reviewed_id)
        if reviewed_row is None:
            raise AssertionError("reviewed session revision was not persisted")
        session_id = reviewed_row.session_id
    return ReviewedFixture(session_id, reviewed_id, review)


def build_golden_fixture() -> GoldenFixture:
    database = new_database()
    fixture = build_stage1_beneficiary_fixture(database.factory)
    direct_beneficiary, direct_revision, direct_stock = _latest_owner_row(
        database.factory, fixture.direct_beneficiary_id
    )
    _draft_beneficiary, _draft_revision, draft_stock = _latest_owner_row(
        database.factory, fixture.draft_beneficiary_id
    )
    _industry_map, map_revision = _map_header(
        database.factory, fixture.direct_beneficiary_id
    )
    profile_id, semantic_revision_id = _create_semantic_revision(
        database.factory, direct_beneficiary, direct_revision, map_revision
    )
    reviewed = _build_reviewed(
        database.factory,
        [direct_stock, draft_stock, _create_stock_only(database.factory)],
        title="普通用户三公司研究成果",
    )
    return GoldenFixture(
        database, reviewed, profile_id, semantic_revision_id
    )


def build_zero_supported_fixture() -> tuple[LocalDatabase, ReviewedFixture]:
    database = new_database()
    fixture = build_stage1_beneficiary_fixture(database.factory)
    _draft, _draft_revision, draft_stock = _latest_owner_row(
        database.factory, fixture.draft_beneficiary_id
    )
    _disputed, _disputed_revision, disputed_stock = _latest_owner_row(
        database.factory, fixture.disputed_beneficiary_id
    )
    return database, _build_reviewed(
        database.factory,
        [draft_stock, disputed_stock],
        title="普通用户零 supported 研究成果",
    )


def query_params(reviewed: ReviewedFixture) -> dict[str, str]:
    return {
        "session_id": str(reviewed.session_id),
        "as_of_cutoff": CUTOFF.isoformat(),
        "as_of_recorded_at_utc": READ_BOUNDARY.isoformat(),
    }


def _reuse_binding(member: dict[str, Any], *, semantic: bool) -> dict[str, Any]:
    options = member["stage1_reuse_options"]
    if not options:
        raise AssertionError("expected an exact Stage 1 reuse option")
    if semantic:
        option = next(
            (item for item in options if item.get("semantic_reuse_options")),
            None,
        )
        if option is None:
            raise AssertionError("expected an exact semantic-compatible owner revision")
        semantic_option = option["semantic_reuse_options"][0]
    else:
        option = options[-1]
        semantic_option = None
    return {
        "reviewed_candidate_revision_id": member["reviewed_candidate_revision_id"],
        "sequence": member["sequence"],
        "stage1_operation": "reuse_exact_beneficiary_revision",
        "stage1": {
            "beneficiary_id": option["beneficiary_id"],
            "beneficiary_revision_id": option["beneficiary_revision_id"],
            "stock_basic_record_id": option["stock_basic_record_id"],
        },
        "semantic_operation": "reuse_exact_semantic_revision" if semantic else "none",
        "semantic": (
            {
                "profile_id": semantic_option["profile_id"],
                "profile_revision_id": semantic_option["profile_revision_id"],
            }
            if semantic_option is not None
            else None
        ),
        "readiness_note": "Fixture readiness remains explicit and owner-confirmed.",
    }


def _base_plan(view: dict[str, Any], bindings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "reviewed_session_revision_id": view["reviewed_session_revision_id"],
        "expected_session_latest_revision_number": view[
            "expected_session_latest_revision_number"
        ],
        "reviewed_plan_fingerprint_sha256": view[
            "reviewed_plan_fingerprint_sha256"
        ],
        "research_case_id": view["research_case"]["id"],
        "map_mode": view["map_mode"],
        "industry_map_id": view["industry_map"]["id"],
        "industry_map_revision_id": view["industry_map"]["revision_id"],
        "candidate_owner_bindings": bindings,
        "output_title": view["output_metadata_defaults"]["output_title"],
        "output_scope": view["output_metadata_defaults"]["output_scope"],
        "information_cutoff_date": view["information_cutoff_date"],
        "owner_acceptance_plan_version": OWNER_ACCEPTANCE_PLAN_VERSION,
    }


def golden_plan(view: dict[str, Any]) -> dict[str, Any]:
    members = view["members"]
    if len(members) != 3:
        raise AssertionError("golden acceptance view must contain three members")
    create_contract = members[2]["stage1_create_contract"]
    assertions = create_contract["map_assertion_options"]
    claims = create_contract["claim_revision_options"]
    if not create_contract["available"] or not assertions or not claims:
        raise AssertionError(create_contract.get("blocking_reason") or "create unavailable")
    bindings = [
        _reuse_binding(members[0], semantic=True),
        _reuse_binding(members[1], semantic=False),
        {
            "reviewed_candidate_revision_id": members[2][
                "reviewed_candidate_revision_id"
            ],
            "sequence": members[2]["sequence"],
            "stage1_operation": "create_beneficiary_identity_and_revision",
            "stage1": {
                "stock_basic_record_id": create_contract["stock_basic_record_id"],
                "source": create_contract["source"],
                "stock_code": create_contract["stock_code"],
                "legacy_beneficiary_kind": "direct",
                "assessment_status": "supported",
                "rationale_summary": "Exact fixture evidence supports this explicit created beneficiary.",
                "map_assertion_revisions": [
                    {
                        "assertion_kind": assertions[0]["assertion_kind"],
                        "assertion_revision_id": assertions[0]["assertion_revision_id"],
                    }
                ],
                "claim_revision_ids": [claims[0]["claim_revision_id"]],
            },
            "semantic_operation": "none",
            "semantic": None,
            "readiness_note": "No typed semantic revision is bound in this acceptance.",
        },
    ]
    pool = view["candidate_pool_operation_contract"]["create_contract"]
    return {
        **_base_plan(view, bindings),
        "candidate_pool_operation": {
            "mode": "create_supported_handoff",
            "pool_key": pool["pool_key"],
            "title": pool["title_default"],
            "scope": pool["scope_default"],
        },
        "revision_note": "Explicitly accept the ordinary-user golden fixture.",
    }


def zero_supported_plan(view: dict[str, Any]) -> dict[str, Any]:
    bindings = [_reuse_binding(member, semantic=False) for member in view["members"]]
    if any(
        option["assessment_status"] == "supported"
        for member in view["members"]
        for option in member["stage1_reuse_options"]
    ):
        raise AssertionError("zero-supported fixture unexpectedly exposes supported reuse")
    return {
        **_base_plan(view, bindings),
        "candidate_pool_operation": {"mode": "none_no_supported_members"},
        "revision_note": "Explicitly accept a valid zero-supported fixture.",
    }


def owner_counts(factory: sessionmaker[Session]) -> dict[str, int]:
    models = {
        "session_revisions": IndustryThesisSessionRevision,
        "output_identities": IndustryThesisOutputLinkIdentity,
        "output_revisions": IndustryThesisOutputLinkRevision,
        "beneficiaries": Stage1Beneficiary,
        "beneficiary_revisions": Stage1BeneficiaryRevision,
        "candidate_pools": Stage1CandidatePool,
        "candidate_pool_revisions": Stage1CandidatePoolRevision,
        "candidate_pool_memberships": Stage1CandidatePoolMembership,
        "company_research": Stage2CompanyResearch,
    }
    with factory() as session:
        return {
            name: int(session.scalar(select(func.count()).select_from(model)) or 0)
            for name, model in models.items()
        }


@contextmanager
def statement_counter(engine: Engine) -> Iterator[list[str]]:
    statements: list[str] = []

    def before_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


@contextmanager
def api_client(database: LocalDatabase) -> Iterator[TestClient]:
    original_service = acceptance_api.IndustryThesisOwnerAcceptanceService

    class FixedClockService:
        def __init__(self, factory: sessionmaker[Session]) -> None:
            self.delegate = IndustryThesisOwnerAcceptanceService(
                factory, clock=lambda: COMMIT_TIME
            )

        def preview(self, raw: dict[str, Any]) -> dict[str, Any]:
            return self.delegate.preview(raw)

        def commit(self, raw: dict[str, Any]) -> dict[str, Any]:
            return self.delegate.commit(raw)

    app.dependency_overrides[
        acceptance_api.get_industry_analysis_session_factory
    ] = lambda: database.factory
    app.dependency_overrides[
        acceptance_api.get_industry_analysis_write_factory
    ] = lambda: database.factory
    acceptance_api.IndustryThesisOwnerAcceptanceService = FixedClockService
    try:
        with TestClient(app) as client:
            yield client
    finally:
        acceptance_api.IndustryThesisOwnerAcceptanceService = original_service
        app.dependency_overrides.clear()


def _view(client: TestClient, reviewed: ReviewedFixture) -> dict[str, Any]:
    response = client.get(
        f"/industry-analysis/api/session-revisions/"
        f"{reviewed.reviewed_session_revision_id}/owner-acceptance-view",
        params=query_params(reviewed),
    )
    if response.status_code != 200:
        raise AssertionError(response.text)
    return response.json()


def _preview(
    client: TestClient, reviewed: ReviewedFixture, plan: dict[str, Any]
) -> dict[str, Any]:
    response = client.post(
        f"/industry-analysis/api/session-revisions/"
        f"{reviewed.reviewed_session_revision_id}/owner-acceptance/preview",
        params=query_params(reviewed),
        json=plan,
    )
    if response.status_code != 200:
        raise AssertionError(response.text)
    return response.json()


def _commit(
    client: TestClient,
    reviewed: ReviewedFixture,
    plan: dict[str, Any],
    preview_fingerprint: str,
) -> dict[str, Any]:
    response = client.post(
        f"/industry-analysis/api/session-revisions/"
        f"{reviewed.reviewed_session_revision_id}/owner-acceptance/commit",
        params=query_params(reviewed),
        json={**plan, "preview_fingerprint_sha256": preview_fingerprint},
    )
    if response.status_code != 200:
        raise AssertionError(response.text)
    return response.json()


def _accepted_result(
    client: TestClient, reviewed: ReviewedFixture, committed: dict[str, Any]
) -> dict[str, Any]:
    parsed = urlparse(committed["accepted_result_path"])
    query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
    response = client.get(
        f"/industry-analysis/api/session-revisions/"
        f"{committed['accepted_session_revision_id']}/accepted-result-view",
        params={"session_id": str(reviewed.session_id), **query},
    )
    if response.status_code != 200:
        raise AssertionError(response.text)
    return response.json()


def run_golden_path() -> dict[str, Any]:
    fixture = build_golden_fixture()
    try:
        with api_client(fixture.database) as client:
            with statement_counter(fixture.database.engine) as view_statements:
                view = _view(client, fixture.reviewed)
            plan = golden_plan(view)
            before = owner_counts(fixture.database.factory)
            preview = _preview(client, fixture.reviewed, plan)
            after_preview = owner_counts(fixture.database.factory)
            committed = _commit(
                client,
                fixture.reviewed,
                plan,
                preview["preview_fingerprint_sha256"],
            )
            with statement_counter(fixture.database.engine) as result_statements:
                result = _accepted_result(client, fixture.reviewed, committed)
        if before != after_preview:
            raise AssertionError("preview persisted owner state")
        if preview["complete_universe_count"] != 3 or preview["supported_handoff_count"] != 2:
            raise AssertionError("golden preview counts are incorrect")
        statuses = [item["assessment_status"] for item in result["members"]]
        if statuses != ["supported", "draft", "supported"]:
            raise AssertionError("accepted result frozen order is incorrect")
        if result["members"][0]["semantic"]["profile_revision_id"] != str(
            fixture.semantic_profile_revision_id
        ):
            raise AssertionError("exact semantic revision was not preserved")
        if owner_counts(fixture.database.factory)["company_research"] != 0:
            raise AssertionError("owner acceptance created Company Research")
        return {
            "complete_universe_count": result["complete_member_count"],
            "supported_handoff_count": result["supported_handoff_count"],
            "candidate_pool_mode": result["candidate_pool_mode"],
            "assessment_statuses": statuses,
            "semantic_covered_count": result["semantic_covered_count"],
            "preview_zero_writes": before == after_preview,
            "acceptance_view_sql_statements": len(view_statements),
            "accepted_result_sql_statements": len(result_statements),
            "company_research_created": False,
            "network_access": False,
        }
    finally:
        fixture.database.engine.dispose()


def run_zero_supported_path() -> dict[str, Any]:
    database, reviewed = build_zero_supported_fixture()
    try:
        with api_client(database) as client:
            view = _view(client, reviewed)
            plan = zero_supported_plan(view)
            preview = _preview(client, reviewed, plan)
            committed = _commit(
                client, reviewed, plan, preview["preview_fingerprint_sha256"]
            )
            result = _accepted_result(client, reviewed, committed)
        if preview["supported_handoff_count"] != 0:
            raise AssertionError("zero-supported preview created a supported handoff")
        if committed["accepted_candidate_pool_revision_id"] is not None:
            raise AssertionError("zero-supported commit created a candidate pool")
        if result["accepted_candidate_pool_revision_id"] is not None:
            raise AssertionError("zero-supported result exposes a candidate pool")
        if result["complete_member_count"] != 2 or result["zero_supported_notice"] is None:
            raise AssertionError("zero-supported complete result is incorrect")
        return {
            "complete_universe_count": result["complete_member_count"],
            "supported_handoff_count": result["supported_handoff_count"],
            "candidate_pool_mode": result["candidate_pool_mode"],
            "accepted_candidate_pool_revision_id": result[
                "accepted_candidate_pool_revision_id"
            ],
            "zero_supported_notice": result["zero_supported_notice"],
            "network_access": False,
        }
    finally:
        database.engine.dispose()


def run_demo() -> dict[str, Any]:
    return {
        "golden_path": run_golden_path(),
        "zero_supported_path": run_zero_supported_path(),
        "notices": {
            "local_first": True,
            "external_network": False,
            "provider_or_ai": False,
            "recommendation_or_trading": False,
            "automatic_company_research": False,
        },
    }


def main() -> None:
    print(json.dumps(run_demo(), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
