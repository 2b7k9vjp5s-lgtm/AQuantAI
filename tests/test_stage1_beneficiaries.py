from __future__ import annotations

import json
import socket
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from backend.api.industry_alpha import get_industry_alpha_session_factory
from backend.database.engine import build_session_factory
from backend.database.models import Base, StockBasicRecord
from backend.main import app
from industry_alpha.commands import EvidenceLedgerCommandService, EvidenceLinkInput
from industry_alpha.errors import (
    EvidenceLedgerImmutableError,
    EvidenceLedgerValidationError,
)
from industry_alpha.models import Claim, ClaimRevision
from industry_alpha.stage1_commands import Stage1BeneficiaryCommandService
from industry_alpha.stage1_fixtures import build_stage1_beneficiary_fixture
from industry_alpha.stage1_models import (
    STAGE1_MODELS,
    Stage1Beneficiary,
    Stage1BeneficiaryAssertionLink,
    Stage1BeneficiaryClaimLink,
    Stage1BeneficiaryRevision,
    Stage1CandidatePool,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)
from industry_alpha.stage1_query import Stage1BeneficiaryQueryService
from industry_alpha.stage1_repository import Stage1BeneficiaryRepository


def utc(day: int, hour: int = 10) -> datetime:
    return datetime(2026, 7, day, hour, tzinfo=timezone.utc)


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    yield factory
    engine.dispose()


@pytest.fixture
def built(session_factory):
    return build_stage1_beneficiary_fixture(session_factory)


def latest_revision(session_factory, beneficiary_id):
    with session_factory() as session:
        return session.scalar(
            select(Stage1BeneficiaryRevision)
            .where(Stage1BeneficiaryRevision.beneficiary_id == beneficiary_id)
            .order_by(Stage1BeneficiaryRevision.revision_no.desc())
        )


def revision_inputs(session_factory, beneficiary_id, revision_no=1):
    with session_factory() as session:
        revision = session.scalar(
            select(Stage1BeneficiaryRevision).where(
                Stage1BeneficiaryRevision.beneficiary_id == beneficiary_id,
                Stage1BeneficiaryRevision.revision_no == revision_no,
            )
        )
        assertion_links = list(
            session.scalars(
                select(Stage1BeneficiaryAssertionLink).where(
                    Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                    == revision.id
                )
            )
        )
        claim_ids = tuple(
            session.scalars(
                select(Stage1BeneficiaryClaimLink.claim_revision_id).where(
                    Stage1BeneficiaryClaimLink.beneficiary_revision_id == revision.id
                )
            )
        )
    from industry_alpha.stage1_commands import MapAssertionRevisionInput

    assertions = []
    for link in assertion_links:
        for kind in ("node", "relationship", "observation"):
            revision_id = getattr(link, f"{kind}_revision_id")
            if revision_id is not None:
                assertions.append(MapAssertionRevisionInput(kind, revision_id))
    return revision, tuple(assertions), claim_ids


def stage1_counts(session_factory):
    with session_factory() as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in STAGE1_MODELS
        )


def test_fixture_has_exact_classifications_pool_and_cutoff_isolation(
    session_factory, built
):
    with session_factory() as session:
        query = Stage1BeneficiaryQueryService(Stage1BeneficiaryRepository(session))
        current = query.list_beneficiaries(built.map_id).to_dict()
        historical = query.list_beneficiaries(
            built.map_id, as_of_cutoff=date(2026, 7, 8)
        ).to_dict()
        pool = query.get_candidate_pool(built.candidate_pool_id).to_dict()
    assert len(current["beneficiaries"]) == 4
    statuses = sorted(
        item["latest_revision"]["assessment_status"]
        for item in current["beneficiaries"]
    )
    assert statuses == ["disputed", "draft", "supported", "supported"]
    current_direct = next(
        item
        for item in current["beneficiaries"]
        if item["beneficiary_id"] == str(built.direct_beneficiary_id)
    )
    historical_direct = next(
        item
        for item in historical["beneficiaries"]
        if item["beneficiary_id"] == str(built.direct_beneficiary_id)
    )
    assert current_direct["latest_revision"]["beneficiary_kind"] == "potential"
    assert historical_direct["latest_revision"]["beneficiary_kind"] == "direct"
    assert pool["latest_revision"]["candidate_count"] == 2
    assert [
        item["beneficiary"]["stock_code"] for item in pool["frozen_candidates"]
    ] == ["000001", "000002"]
    assert all(
        item["frozen_beneficiary_revision"]["assessment_status"] == "supported"
        for item in pool["frozen_candidates"]
    )
    json.dumps(current, allow_nan=False)
    json.dumps(pool, allow_nan=False)


def test_detail_freezes_exact_company_assertion_claim_and_evidence(
    session_factory, built
):
    with session_factory() as session:
        payload = Stage1BeneficiaryQueryService(
            Stage1BeneficiaryRepository(session)
        ).get_beneficiary(built.direct_beneficiary_id).to_dict()
    latest = payload["latest_revision"]
    assert latest["company_snapshot"]["stock_basic_record_id"] > 0
    assert latest["company_snapshot"]["stock_code"] == "000001"
    assert latest["company_snapshot"]["stock_name"] == "Fixture Direct Co"
    assert latest["company_snapshot"]["series_key"] == "1" * 64
    assert [item["assertion_kind"] for item in latest["map_assertions"]] == [
        "node"
    ]
    assert [item["claim_key"] for item in latest["claims"]] == [
        "stage1-fixture-direct"
    ]
    assert latest["evidence_summary"]["grade_counts"] == {
        "A": 1,
        "B": 0,
        "C": 0,
        "D": 0,
    }
    assert latest["conflicts"] == []
    assert latest["missing_evidence"] == []


def test_disputed_conflict_and_d_only_draft_remain_explicit(session_factory, built):
    with session_factory() as session:
        query = Stage1BeneficiaryQueryService(Stage1BeneficiaryRepository(session))
        disputed = query.get_beneficiary(built.disputed_beneficiary_id).to_dict()
        draft = query.get_beneficiary(built.draft_beneficiary_id).to_dict()
    assert disputed["latest_revision"]["assessment_status"] == "disputed"
    assert disputed["latest_revision"]["evidence_summary"]["conflict_count"] == 1
    assert len(disputed["latest_revision"]["conflicts"]) == 1
    assert draft["latest_revision"]["assessment_status"] == "draft"
    assert draft["latest_revision"]["evidence_summary"]["grade_counts"]["D"] == 1


def test_revision_numbers_and_supersedes_chain_are_deterministic(
    session_factory, built
):
    with session_factory() as session:
        revisions = list(
            session.scalars(
                select(Stage1BeneficiaryRevision)
                .where(
                    Stage1BeneficiaryRevision.beneficiary_id
                    == built.direct_beneficiary_id
                )
                .order_by(Stage1BeneficiaryRevision.revision_no)
            )
        )
    assert [item.revision_no for item in revisions] == [1, 2]
    assert revisions[0].supersedes_revision_id is None
    assert revisions[1].supersedes_revision_id == revisions[0].id


def test_candidate_pool_revision_numbers_and_supersedes_are_deterministic(
    session_factory, built
):
    direct, _, _ = revision_inputs(session_factory, built.direct_beneficiary_id, 1)
    secondary, _, _ = revision_inputs(
        session_factory, built.secondary_beneficiary_id, 1
    )
    revision = Stage1BeneficiaryCommandService(
        session_factory
    ).append_candidate_pool_revision(
        built.candidate_pool_id,
        selected_map_revision_id=direct.selected_map_revision_id,
        title="Second unranked handoff revision",
        scope="Exact supported revisions only.",
        information_cutoff_date=date(2026, 7, 10),
        beneficiary_revision_ids=(direct.id, secondary.id),
        recorded_at_utc=utc(10),
    )
    assert revision.revision_no == 2
    with session_factory() as session:
        first = session.scalar(
            select(Stage1CandidatePoolRevision).where(
                Stage1CandidatePoolRevision.candidate_pool_id
                == built.candidate_pool_id,
                Stage1CandidatePoolRevision.revision_no == 1,
            )
        )
    assert revision.supersedes_revision_id == first.id


def test_duplicate_assertion_and_claim_ids_are_rejected(session_factory, built):
    revision, assertions, claims = revision_inputs(
        session_factory, built.secondary_beneficiary_id
    )
    commands = Stage1BeneficiaryCommandService(session_factory)
    for duplicated_assertions, duplicated_claims in (
        (assertions + assertions, claims),
        (assertions, claims + claims),
    ):
        before = stage1_counts(session_factory)
        with pytest.raises(EvidenceLedgerValidationError, match="duplicates"):
            commands.append_beneficiary_revision(
                built.secondary_beneficiary_id,
                selected_map_revision_id=revision.selected_map_revision_id,
                stock_basic_record_id=revision.stock_basic_record_id,
                beneficiary_kind="secondary",
                assessment_status="supported",
                rationale_summary="Duplicate exact references must fail.",
                information_cutoff_date=date(2026, 7, 10),
                assertion_revisions=duplicated_assertions,
                claim_revision_ids=duplicated_claims,
                recorded_at_utc=utc(10),
            )
        assert stage1_counts(session_factory) == before


@pytest.mark.parametrize("kind", ["", "primary", 1])
def test_beneficiary_kind_is_strict_and_failure_rolls_back(
    session_factory, built, kind
):
    revision, assertions, claims = revision_inputs(
        session_factory, built.secondary_beneficiary_id
    )
    before = stage1_counts(session_factory)
    with pytest.raises(EvidenceLedgerValidationError):
        Stage1BeneficiaryCommandService(session_factory).append_beneficiary_revision(
            built.secondary_beneficiary_id,
            selected_map_revision_id=revision.selected_map_revision_id,
            stock_basic_record_id=revision.stock_basic_record_id,
            beneficiary_kind=kind,
            assessment_status="supported",
            rationale_summary="Invalid kind must rollback.",
            information_cutoff_date=date(2026, 7, 10),
            assertion_revisions=assertions,
            claim_revision_ids=claims,
            recorded_at_utc=utc(10),
        )
    assert stage1_counts(session_factory) == before


@pytest.mark.parametrize("status", ["", "eligible", 3])
def test_assessment_status_is_strict(session_factory, built, status):
    revision, assertions, claims = revision_inputs(
        session_factory, built.secondary_beneficiary_id
    )
    with pytest.raises(EvidenceLedgerValidationError):
        Stage1BeneficiaryCommandService(session_factory).append_beneficiary_revision(
            built.secondary_beneficiary_id,
            selected_map_revision_id=revision.selected_map_revision_id,
            stock_basic_record_id=revision.stock_basic_record_id,
            beneficiary_kind="secondary",
            assessment_status=status,
            rationale_summary="Invalid status.",
            information_cutoff_date=date(2026, 7, 10),
            assertion_revisions=assertions,
            claim_revision_ids=claims,
            recorded_at_utc=utc(10),
        )


def test_text_bounds_and_non_string_values_are_rejected(session_factory, built):
    revision, assertions, claims = revision_inputs(
        session_factory, built.secondary_beneficiary_id
    )
    commands = Stage1BeneficiaryCommandService(session_factory)
    for rationale in (" ", "x" * 4001, 17):
        with pytest.raises(EvidenceLedgerValidationError):
            commands.append_beneficiary_revision(
                built.secondary_beneficiary_id,
                selected_map_revision_id=revision.selected_map_revision_id,
                stock_basic_record_id=revision.stock_basic_record_id,
                beneficiary_kind="secondary",
                assessment_status="supported",
                rationale_summary=rationale,
                information_cutoff_date=date(2026, 7, 10),
                assertion_revisions=assertions,
                claim_revision_ids=claims,
                recorded_at_utc=utc(10),
            )


def test_wrong_stock_snapshot_is_rejected_atomically(session_factory, built):
    revision, assertions, claims = revision_inputs(
        session_factory, built.secondary_beneficiary_id
    )
    with session_factory() as session:
        wrong_stock = session.scalar(
            select(StockBasicRecord).where(StockBasicRecord.stock_code == "000001")
        )
    before = stage1_counts(session_factory)
    with pytest.raises(EvidenceLedgerValidationError, match="exactly match"):
        Stage1BeneficiaryCommandService(session_factory).append_beneficiary_revision(
            built.secondary_beneficiary_id,
            selected_map_revision_id=revision.selected_map_revision_id,
            stock_basic_record_id=wrong_stock.id,
            beneficiary_kind="secondary",
            assessment_status="supported",
            rationale_summary="Wrong exact company row.",
            information_cutoff_date=date(2026, 7, 10),
            assertion_revisions=assertions,
            claim_revision_ids=claims,
            recorded_at_utc=utc(10),
        )
    assert stage1_counts(session_factory) == before


def test_company_snapshot_after_cutoff_is_rejected(session_factory, built):
    revision, assertions, claims = revision_inputs(
        session_factory, built.secondary_beneficiary_id
    )
    before = stage1_counts(session_factory)
    with pytest.raises(EvidenceLedgerValidationError, match="company snapshot cutoff"):
        Stage1BeneficiaryCommandService(session_factory).append_beneficiary_revision(
            built.secondary_beneficiary_id,
            selected_map_revision_id=revision.selected_map_revision_id,
            stock_basic_record_id=revision.stock_basic_record_id,
            beneficiary_kind="secondary",
            assessment_status="supported",
            rationale_summary="Company snapshot is not visible at this cutoff.",
            information_cutoff_date=date(2026, 7, 5),
            assertion_revisions=assertions,
            claim_revision_ids=claims,
            recorded_at_utc=utc(10),
        )
    assert stage1_counts(session_factory) == before


def test_assertion_must_be_in_selected_map_revision(session_factory, built):
    revision, assertions, claims = revision_inputs(
        session_factory, built.secondary_beneficiary_id
    )
    with session_factory() as session:
        from industry_alpha.chain_map_models import IndustryMapRevision

        empty_map_revision_id = session.scalar(
            select(IndustryMapRevision.id)
            .where(IndustryMapRevision.map_id == built.map_id)
            .order_by(IndustryMapRevision.revision_no)
            .limit(1)
        )
    with pytest.raises(EvidenceLedgerValidationError, match="not frozen"):
        Stage1BeneficiaryCommandService(session_factory).append_beneficiary_revision(
            built.secondary_beneficiary_id,
            selected_map_revision_id=empty_map_revision_id,
            stock_basic_record_id=revision.stock_basic_record_id,
            beneficiary_kind="secondary",
            assessment_status="supported",
            rationale_summary="Assertion is not in this map snapshot.",
            information_cutoff_date=date(2026, 7, 10),
            assertion_revisions=assertions,
            claim_revision_ids=claims,
            recorded_at_utc=utc(10),
        )


def test_d_only_claim_cannot_be_promoted_to_supported(session_factory, built):
    revision, assertions, claims = revision_inputs(
        session_factory, built.draft_beneficiary_id
    )
    with pytest.raises(EvidenceLedgerValidationError, match="A/B/C"):
        Stage1BeneficiaryCommandService(session_factory).append_beneficiary_revision(
            built.draft_beneficiary_id,
            selected_map_revision_id=revision.selected_map_revision_id,
            stock_basic_record_id=revision.stock_basic_record_id,
            beneficiary_kind="potential",
            assessment_status="supported",
            rationale_summary="D-only must not become supported.",
            information_cutoff_date=date(2026, 7, 10),
            assertion_revisions=assertions,
            claim_revision_ids=claims,
            recorded_at_utc=utc(10),
        )


def test_cross_case_claim_is_rejected_and_rolls_back(session_factory, built):
    revision, assertions, _ = revision_inputs(
        session_factory, built.secondary_beneficiary_id
    )
    ledger = EvidenceLedgerCommandService(session_factory)
    other_case = ledger.create_case(
        case_key="other-stage1-case",
        title="Other case",
        research_question="Must cross-case links fail?",
        information_cutoff_date=date(2026, 7, 6),
        recorded_at_utc=utc(6),
    )
    evidence = ledger.add_evidence(
        other_case.id,
        evidence_grade="A",
        source_kind="official",
        source_title="Other-case evidence",
        information_date=date(2026, 7, 6),
        summary="This evidence belongs to another research case.",
        recorded_at_utc=utc(6),
    )
    claim = ledger.create_claim(
        other_case.id,
        claim_key="other-case-claim",
        statement="This claim must not cross the case boundary.",
        claim_kind="fact",
        claim_status="supported",
        information_cutoff_date=date(2026, 7, 6),
        evidence_links=(EvidenceLinkInput(evidence.id, "supports"),),
        recorded_at_utc=utc(6),
    )
    with session_factory() as session:
        claim_revision = session.scalar(
            select(ClaimRevision).where(ClaimRevision.claim_id == claim.id)
        )
    before = stage1_counts(session_factory)
    with pytest.raises(EvidenceLedgerValidationError, match="share one research case"):
        Stage1BeneficiaryCommandService(session_factory).append_beneficiary_revision(
            built.secondary_beneficiary_id,
            selected_map_revision_id=revision.selected_map_revision_id,
            stock_basic_record_id=revision.stock_basic_record_id,
            beneficiary_kind="secondary",
            assessment_status="supported",
            rationale_summary="Cross-case claim must fail.",
            information_cutoff_date=date(2026, 7, 10),
            assertion_revisions=assertions,
            claim_revision_ids=(claim_revision.id,),
            recorded_at_utc=utc(10),
        )
    assert stage1_counts(session_factory) == before


def test_missing_evidence_is_explicit_in_read_contract(session_factory, built):
    revision, assertions, _ = revision_inputs(
        session_factory, built.secondary_beneficiary_id
    )
    with session_factory() as session:
        beneficiary = session.get(
            Stage1Beneficiary, built.secondary_beneficiary_id
        )
        stock = session.get(StockBasicRecord, revision.stock_basic_record_id)
        case_id = beneficiary.case_id
        map_id = beneficiary.map_id
    ledger = EvidenceLedgerCommandService(session_factory)
    claim = ledger.create_claim(
        case_id,
        claim_key="stage1-missing-evidence",
        statement="This draft claim intentionally has no evidence.",
        claim_kind="fact",
        claim_status="draft",
        information_cutoff_date=date(2026, 7, 6),
        evidence_links=(),
        recorded_at_utc=utc(6),
    )
    with session_factory.begin() as session:
        new_stock = StockBasicRecord(
            ingestion_run_id=stock.ingestion_run_id,
            stock_code="000005",
            stock_name="Fixture Missing Evidence Co",
            exchange="SZSE",
            industry="Fixture industry",
            listing_date=date(2020, 1, 1),
            status="listed",
            source="fixture",
        )
        session.add(new_stock)
        session.flush()
        stock_id = new_stock.id
        claim_revision = session.scalar(
            select(ClaimRevision).where(ClaimRevision.claim_id == claim.id)
        )
    created = Stage1BeneficiaryCommandService(session_factory).create_beneficiary(
        case_id,
        map_id,
        source="fixture",
        stock_code="000005",
        selected_map_revision_id=revision.selected_map_revision_id,
        stock_basic_record_id=stock_id,
        beneficiary_kind="potential",
        assessment_status="draft",
        rationale_summary="Missing evidence remains explicit.",
        information_cutoff_date=date(2026, 7, 7),
        assertion_revisions=assertions,
        claim_revision_ids=(claim_revision.id,),
        recorded_at_utc=utc(7),
    )
    with session_factory() as session:
        payload = Stage1BeneficiaryQueryService(
            Stage1BeneficiaryRepository(session)
        ).get_beneficiary(created.id).to_dict()
    assert payload["latest_revision"]["evidence_summary"][
        "missing_evidence_claim_count"
    ] == 1
    assert payload["latest_revision"]["missing_evidence"][0]["claim_key"] == (
        "stage1-missing-evidence"
    )


def test_disputed_requires_disputed_claim_or_visible_conflict(session_factory, built):
    revision, assertions, claims = revision_inputs(
        session_factory, built.secondary_beneficiary_id
    )
    with pytest.raises(EvidenceLedgerValidationError, match="disputed claim"):
        Stage1BeneficiaryCommandService(session_factory).append_beneficiary_revision(
            built.secondary_beneficiary_id,
            selected_map_revision_id=revision.selected_map_revision_id,
            stock_basic_record_id=revision.stock_basic_record_id,
            beneficiary_kind="secondary",
            assessment_status="disputed",
            rationale_summary="No conflict exists.",
            information_cutoff_date=date(2026, 7, 10),
            assertion_revisions=assertions,
            claim_revision_ids=claims,
            recorded_at_utc=utc(10),
        )


def test_candidate_pool_rejects_draft_and_duplicate_identity(session_factory, built):
    direct_v1, _, _ = revision_inputs(session_factory, built.direct_beneficiary_id, 1)
    direct_v2 = latest_revision(session_factory, built.direct_beneficiary_id)
    draft = latest_revision(session_factory, built.draft_beneficiary_id)
    commands = Stage1BeneficiaryCommandService(session_factory)
    with session_factory() as session:
        pool = session.get(Stage1CandidatePool, built.candidate_pool_id)
    with pytest.raises(EvidenceLedgerValidationError, match="supported"):
        commands.append_candidate_pool_revision(
            pool.id,
            selected_map_revision_id=direct_v1.selected_map_revision_id,
            title="Invalid draft member",
            scope="Must rollback.",
            information_cutoff_date=date(2026, 7, 10),
            beneficiary_revision_ids=(draft.id,),
            recorded_at_utc=utc(10),
        )
    with pytest.raises(EvidenceLedgerValidationError, match="only one revision"):
        commands.append_candidate_pool_revision(
            pool.id,
            selected_map_revision_id=direct_v1.selected_map_revision_id,
            title="Duplicate beneficiary identity",
            scope="Must rollback.",
            information_cutoff_date=date(2026, 7, 10),
            beneficiary_revision_ids=(direct_v1.id, direct_v2.id),
            recorded_at_utc=utc(10),
        )


def test_revision_chronology_rejects_backdating(session_factory, built):
    revision, assertions, claims = revision_inputs(
        session_factory, built.direct_beneficiary_id, 1
    )
    with pytest.raises(EvidenceLedgerValidationError, match="previous beneficiary"):
        Stage1BeneficiaryCommandService(session_factory).append_beneficiary_revision(
            built.direct_beneficiary_id,
            selected_map_revision_id=revision.selected_map_revision_id,
            stock_basic_record_id=revision.stock_basic_record_id,
            beneficiary_kind="direct",
            assessment_status="supported",
            rationale_summary="Backdated revision.",
            information_cutoff_date=date(2026, 7, 8),
            assertion_revisions=assertions,
            claim_revision_ids=claims,
            recorded_at_utc=utc(8),
        )


def test_later_claim_evidence_link_cannot_backfill_frozen_beneficiary(
    session_factory, built
):
    revision, _, claims = revision_inputs(
        session_factory, built.direct_beneficiary_id, 1
    )
    ledger = EvidenceLedgerCommandService(session_factory)
    with session_factory() as session:
        claim = session.get(ClaimRevision, claims[0])
        beneficiary = session.get(Stage1Beneficiary, built.direct_beneficiary_id)
    evidence = ledger.add_evidence(
        beneficiary.case_id,
        evidence_grade="B",
        source_kind="research",
        source_title="Later physically inserted context",
        information_date=date(2026, 7, 6),
        summary="This record cannot be backfilled into an accepted classification.",
        content_fingerprint="stage1-later-context",
        recorded_at_utc=utc(7),
    )
    with pytest.raises(EvidenceLedgerValidationError, match="beneficiary revision"):
        ledger.link_evidence(
            claims[0],
            evidence.id,
            relation="context",
            recorded_at_utc=utc(7),
        )
    ledger.link_evidence(
        claims[0], evidence.id, relation="context", recorded_at_utc=utc(10)
    )
    with session_factory() as session:
        detail = Stage1BeneficiaryQueryService(
            Stage1BeneficiaryRepository(session)
        ).get_beneficiary(built.direct_beneficiary_id).to_dict()
    assert all(
        item["source_title"] != "Later physically inserted context"
        for claim_payload in detail["latest_revision"]["claims"]
        for item in claim_payload["evidence"]
    )


def test_append_only_update_and_delete_are_rejected(session_factory, built):
    with session_factory() as session:
        beneficiary = session.get(Stage1Beneficiary, built.direct_beneficiary_id)
        beneficiary.stock_code = "999999"
        with pytest.raises(EvidenceLedgerImmutableError):
            session.flush()
        session.rollback()
    for model in STAGE1_MODELS:
        with session_factory() as session:
            row = session.scalar(select(model).limit(1))
            session.delete(row)
            with pytest.raises(EvidenceLedgerImmutableError):
                session.flush()


def test_api_routes_are_read_only_strict_json_and_deterministic(
    session_factory, built
):
    app.dependency_overrides[get_industry_alpha_session_factory] = lambda: session_factory
    try:
        client = TestClient(app)
        paths = (
            f"/industry-alpha/maps/{built.map_id}/beneficiaries",
            f"/industry-alpha/beneficiaries/{built.direct_beneficiary_id}",
            f"/industry-alpha/maps/{built.map_id}/candidate-pools",
            f"/industry-alpha/candidate-pools/{built.candidate_pool_id}",
        )
        payloads = []
        for path in paths:
            first = client.get(path)
            second = client.get(path)
            assert first.status_code == 200
            assert first.json() == second.json()
            json.dumps(first.json(), allow_nan=False)
            payloads.append(first.json())
            for method in (client.post, client.put, client.patch, client.delete):
                assert method(path).status_code == 405
        assert payloads[0]["notices"]["read_only"] is True
        assert "rank" not in payloads[3]["latest_revision"]
        assert "score" not in payloads[3]["latest_revision"]
        assert "weight" not in payloads[3]["latest_revision"]
    finally:
        app.dependency_overrides.clear()


def test_fixture_import_and_demo_paths_never_access_network(
    session_factory, monkeypatch
):
    def reject_network(*_args, **_kwargs):
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr(socket.socket, "connect", reject_network)
    fixture = build_stage1_beneficiary_fixture(session_factory)
    assert fixture.map_id is not None


def test_version_and_existing_routes_remain_compatible(session_factory, built):
    from backend.main import app as fastapi_app

    assert fastapi_app.version == "0.2.0"
    app.dependency_overrides[get_industry_alpha_session_factory] = lambda: session_factory
    try:
        client = TestClient(app)
        assert client.get("/").status_code == 200
        assert client.get("/health").status_code == 200
        assert client.get(f"/industry-alpha/maps/{built.map_id}").status_code == 200
    finally:
        app.dependency_overrides.clear()
