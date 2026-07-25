from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.beneficiary_semantics_commands import (
    BeneficiarySemanticCommandService,
)
from industry_alpha.beneficiary_semantics_contracts import TAXONOMY_VERSION
from industry_alpha.beneficiary_semantics_models import (
    Stage1BeneficiarySemanticAssertion,
    Stage1BeneficiarySemanticAssertionClaimLink,
    Stage1BeneficiarySemanticProfile,
    Stage1BeneficiarySemanticProfileRevision,
    Stage1BeneficiarySemanticVerificationItem,
)
from industry_alpha.chain_map_models import (
    IndustryMapObservation,
    IndustryMapObservationRevision,
    IndustryMapRevision,
)
from industry_alpha.industry_thesis_models import (
    IndustryThesisOutputLinkIdentity,
    IndustryThesisOutputLinkRevision,
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_owner_acceptance import (
    IndustryThesisOwnerAcceptanceService,
)
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    IndustryThesisOwnerAcceptanceError,
    normalize_owner_acceptance_plan,
)
from industry_alpha.industry_thesis_owner_acceptance_query import (
    IndustryThesisAcceptedOutputQueryService,
)
from industry_alpha.industry_thesis_rules import (
    canonical_json_text,
    json_value,
    stored_utc,
)
from industry_alpha.models import Claim, ClaimRevision
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
    Stage1CandidatePool,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)

UTC = timezone.utc


def _load_test_helpers(filename: str, module_name: str) -> ModuleType:
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load test helpers from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_OWNER = _load_test_helpers(
    "test_industry_thesis_owner_acceptance.py",
    "_aquantai_owner_acceptance_test_helpers",
)
_SEMANTICS = _load_test_helpers(
    "test_beneficiary_semantics.py",
    "_aquantai_semantic_test_helpers",
)


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


def _state_snapshot(database) -> dict[str, object]:
    models = (
        Stage1Beneficiary,
        Stage1BeneficiaryRevision,
        Stage1BeneficiaryAssertionLink,
        Stage1BeneficiaryClaimLink,
        Stage1BeneficiarySemanticProfile,
        Stage1BeneficiarySemanticProfileRevision,
        Stage1BeneficiarySemanticAssertion,
        Stage1BeneficiarySemanticAssertionClaimLink,
        Stage1BeneficiarySemanticVerificationItem,
        Stage1CandidatePool,
        Stage1CandidatePoolRevision,
        Stage1CandidatePoolMembership,
        IndustryThesisSessionRevision,
        IndustryThesisOutputLinkIdentity,
        IndustryThesisOutputLinkRevision,
    )
    with database() as session:
        counts = {
            model.__tablename__: session.scalar(
                select(func.count()).select_from(model)
            )
            for model in models
        }
        latest = tuple(
            (str(row.id), row.latest_revision_number)
            for row in session.scalars(
                select(IndustryThesisSessionIdentity).order_by(
                    IndustryThesisSessionIdentity.id
                )
            )
        )
    return {"counts": counts, "session_latest": latest}


def _commit_input(raw: dict) -> dict:
    normalized = normalize_owner_acceptance_plan(raw)
    return {
        **raw,
        "preview_fingerprint_sha256": normalized[
            "owner_acceptance_plan_fingerprint_sha256"
        ],
    }


def _commit_success(database, raw: dict) -> dict:
    service = IndustryThesisOwnerAcceptanceService(
        database,
        clock=lambda: _OWNER.BASE_TIME + timedelta(seconds=3),
    )
    preview = service.preview(raw)
    assert preview["commit_ready"] is True
    return service.commit(
        {
            **raw,
            "preview_fingerprint_sha256": preview[
                "preview_fingerprint_sha256"
            ],
        }
    )


def _one_member_raw(database):
    fixture = build_stage1_beneficiary_fixture(database)
    review, industry_map, map_revision, rows = _OWNER._build_reviewed(
        database,
        beneficiary_ids=(fixture.direct_beneficiary_id,),
    )
    raw = _OWNER._acceptance_input(
        review,
        industry_map,
        map_revision,
        rows,
        pool_mode="create_supported_handoff",
    )
    return fixture, review, industry_map, map_revision, rows, raw


def _set_append_stage1(
    database,
    binding: dict,
    *,
    beneficiary_id: UUID,
    revision_id: UUID,
    expected_latest_revision_id: UUID,
    rationale: str,
) -> None:
    with database() as session:
        beneficiary = session.get(Stage1Beneficiary, beneficiary_id)
        revision = session.get(Stage1BeneficiaryRevision, revision_id)
        assert beneficiary is not None and revision is not None
        assertion_links = list(
            session.scalars(
                select(Stage1BeneficiaryAssertionLink).where(
                    Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                    == revision.id
                )
            )
        )
        claim_ids = list(
            session.scalars(
                select(Stage1BeneficiaryClaimLink.claim_revision_id).where(
                    Stage1BeneficiaryClaimLink.beneficiary_revision_id
                    == revision.id
                )
            )
        )
        source = beneficiary.source
        stock_code = beneficiary.stock_code
        stock_basic_record_id = revision.stock_basic_record_id
        beneficiary_kind = revision.beneficiary_kind
        assessment_status = revision.assessment_status

    assertions: list[dict[str, str]] = []
    for link in assertion_links:
        for kind in ("node", "relationship", "observation"):
            assertion_revision_id = getattr(link, f"{kind}_revision_id")
            if assertion_revision_id is not None:
                assertions.append(
                    {
                        "assertion_kind": kind,
                        "assertion_revision_id": str(assertion_revision_id),
                    }
                )

    binding["stage1_operation"] = "append_beneficiary_revision"
    binding["stage1"] = {
        "beneficiary_id": str(beneficiary_id),
        "expected_latest_revision_id": str(expected_latest_revision_id),
        "stock_basic_record_id": stock_basic_record_id,
        "source": source,
        "stock_code": stock_code,
        "legacy_beneficiary_kind": beneficiary_kind,
        "assessment_status": assessment_status,
        "rationale_summary": rationale,
        "map_assertion_revisions": assertions,
        "claim_revision_ids": [str(value) for value in claim_ids],
    }


def _track_successful_stage1_appends(service, monkeypatch):
    original = service._stage1.append_beneficiary_revision
    appended_revision_ids: list[UUID] = []

    def tracked(*args, **kwargs):
        result = original(*args, **kwargs)
        appended_revision_ids.append(result.revision.id)
        return result

    monkeypatch.setattr(service._stage1, "append_beneficiary_revision", tracked)
    return appended_revision_ids


def _semantic_owner_fixture(database):
    fixture = build_stage1_beneficiary_fixture(database)
    with database() as session:
        prior = session.scalar(
            select(Stage1BeneficiaryRevision)
            .where(
                Stage1BeneficiaryRevision.beneficiary_id
                == fixture.direct_beneficiary_id
            )
            .order_by(Stage1BeneficiaryRevision.revision_no.desc())
        )
        map_revision = session.scalar(
            select(IndustryMapRevision)
            .where(IndustryMapRevision.map_id == fixture.map_id)
            .order_by(IndustryMapRevision.revision_no.desc())
        )
        driver_revision = session.scalar(
            select(IndustryMapObservationRevision)
            .join(
                IndustryMapObservation,
                IndustryMapObservation.id
                == IndustryMapObservationRevision.observation_id,
            )
            .where(
                IndustryMapObservation.map_id == fixture.map_id,
                IndustryMapObservation.observation_key == "bounded-demand-driver",
            )
        )
        direct_claim = session.scalar(
            select(ClaimRevision)
            .join(Claim, Claim.id == ClaimRevision.claim_id)
            .where(Claim.claim_key == "stage1-fixture-direct")
        )
        driver_claim = session.scalar(
            select(ClaimRevision)
            .join(Claim, Claim.id == ClaimRevision.claim_id)
            .where(
                Claim.claim_key == "fixture-chain-driver",
                ClaimRevision.revision_no == 1,
            )
        )
        assert all(
            value is not None
            for value in (
                prior,
                map_revision,
                driver_revision,
                direct_claim,
                driver_claim,
            )
        )
        latest_recorded = max(
            stored_utc(prior.recorded_at_utc),
            stored_utc(map_revision.recorded_at_utc),
            stored_utc(driver_revision.recorded_at_utc),
            stored_utc(direct_claim.recorded_at_utc),
            stored_utc(driver_claim.recorded_at_utc),
        )

    appended_recorded = max(
        latest_recorded + timedelta(microseconds=1),
        _OWNER.BASE_TIME - timedelta(seconds=1),
    )
    assert appended_recorded < _OWNER.BASE_TIME
    beneficiary_revision = Stage1BeneficiaryCommandService(
        database
    ).append_beneficiary_revision(
        fixture.direct_beneficiary_id,
        selected_map_revision_id=map_revision.id,
        stock_basic_record_id=prior.stock_basic_record_id,
        beneficiary_kind="direct",
        assessment_status="supported",
        rationale_summary=(
            "Fixture revision freezes one exact driver and two attributable claims "
            "for owner-acceptance semantic stale testing."
        ),
        information_cutoff_date=_OWNER.CUTOFF,
        assertion_revisions=(
            MapAssertionRevisionInput("observation", driver_revision.id),
        ),
        claim_revision_ids=(direct_claim.id, driver_claim.id),
        recorded_at_utc=appended_recorded,
    )

    review, industry_map, selected_map_revision, rows = _OWNER._build_reviewed(
        database,
        beneficiary_ids=(fixture.direct_beneficiary_id,),
    )
    raw = _OWNER._acceptance_input(
        review,
        industry_map,
        selected_map_revision,
        rows,
        pool_mode="create_supported_handoff",
    )

    semantic_context = {
        "beneficiary_id": fixture.direct_beneficiary_id,
        "beneficiary_revision_id": beneficiary_revision.id,
        "map_revision_id": selected_map_revision.id,
        "driver_revision_id": driver_revision.id,
        "direct_claim_id": direct_claim.id,
        "driver_claim_id": driver_claim.id,
    }
    semantic_payload = _SEMANTICS._payload(semantic_context)
    semantic_payload["information_cutoff_date"] = _OWNER.CUTOFF.isoformat()
    semantic_payload["recorded_at_utc"] = (
        _OWNER.BASE_TIME + timedelta(seconds=2, microseconds=500_000)
    ).isoformat()
    recorded = BeneficiarySemanticCommandService(database).record(semantic_payload)
    return fixture, rows, raw, semantic_payload, recorded


def _owner_semantic_payload(full_payload: dict, *, expected_latest: UUID) -> dict:
    payload = {
        key: deepcopy(value)
        for key, value in full_payload.items()
        if key
        not in {
            "beneficiary_id",
            "beneficiary_revision_id",
            "selected_map_revision_id",
            "information_cutoff_date",
            "recorded_at_utc",
        }
    }
    payload["expected_latest_revision_id"] = str(expected_latest)
    payload["taxonomy_version"] = TAXONOMY_VERSION
    for assertion in payload["assertions"]:
        assertion.setdefault("subject_text", None)
        assertion.setdefault("map_observation_revision_id", None)
    return payload


def _assert_all_exact_reads_fail(
    database,
    output_id: UUID,
    *,
    as_of_cutoff,
    as_of_recorded_at_utc: datetime,
) -> None:
    for method_name in ("get_output", "get_result", "get_readiness"):
        with database() as session:
            query = IndustryThesisAcceptedOutputQueryService(session)
            method = getattr(query, method_name)
            with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
                method(
                    output_id,
                    as_of_cutoff=as_of_cutoff,
                    as_of_recorded_at_utc=as_of_recorded_at_utc,
                )
            assert caught.value.code == (
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )


def test_later_candidate_stale_failure_rolls_back_prior_candidate_append(
    database,
    monkeypatch,
):
    fixture = build_stage1_beneficiary_fixture(database)
    review, industry_map, map_revision, rows = _OWNER._build_reviewed(
        database,
        beneficiary_ids=(
            fixture.direct_beneficiary_id,
            fixture.secondary_beneficiary_id,
        ),
    )
    raw = _OWNER._acceptance_input(
        review,
        industry_map,
        map_revision,
        rows,
        pool_mode="create_supported_handoff",
    )
    _set_append_stage1(
        database,
        raw["candidate_owner_bindings"][0],
        beneficiary_id=rows[0][0].id,
        revision_id=rows[0][1].id,
        expected_latest_revision_id=rows[0][1].id,
        rationale="The first candidate append must roll back after the later failure.",
    )
    _set_append_stage1(
        database,
        raw["candidate_owner_bindings"][1],
        beneficiary_id=rows[1][0].id,
        revision_id=rows[1][1].id,
        expected_latest_revision_id=uuid4(),
        rationale="The second candidate deliberately carries a stale expected latest.",
    )
    service = IndustryThesisOwnerAcceptanceService(
        database,
        clock=lambda: _OWNER.BASE_TIME + timedelta(seconds=3),
    )
    appended = _track_successful_stage1_appends(service, monkeypatch)
    before = _state_snapshot(database)

    with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
        service.commit(_commit_input(raw))

    assert caught.value.code == "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT"
    assert len(appended) == 1
    assert _state_snapshot(database) == before


def test_later_semantic_stale_failure_rolls_back_stage1_append(
    database,
    monkeypatch,
):
    _fixture, rows, raw, semantic_payload, _recorded = _semantic_owner_fixture(
        database
    )
    binding = raw["candidate_owner_bindings"][0]
    _set_append_stage1(
        database,
        binding,
        beneficiary_id=rows[0][0].id,
        revision_id=rows[0][1].id,
        expected_latest_revision_id=rows[0][1].id,
        rationale="Stage 1 append must roll back after stale semantic expected-latest.",
    )
    binding["semantic_operation"] = "append_complete_semantic_profile"
    binding["semantic"] = _owner_semantic_payload(
        semantic_payload,
        expected_latest=uuid4(),
    )
    service = IndustryThesisOwnerAcceptanceService(
        database,
        clock=lambda: _OWNER.BASE_TIME + timedelta(seconds=3),
    )
    appended = _track_successful_stage1_appends(service, monkeypatch)
    before = _state_snapshot(database)

    with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
        service.commit(_commit_input(raw))

    assert caught.value.code == "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT"
    assert len(appended) == 1
    assert _state_snapshot(database) == before


def test_later_pool_stale_failure_rolls_back_stage1_append(
    database,
    monkeypatch,
):
    fixture, _review, _map, _map_revision, rows, raw = _one_member_raw(database)
    binding = raw["candidate_owner_bindings"][0]
    _set_append_stage1(
        database,
        binding,
        beneficiary_id=rows[0][0].id,
        revision_id=rows[0][1].id,
        expected_latest_revision_id=rows[0][1].id,
        rationale="Stage 1 append must roll back after stale pool expected-latest.",
    )
    raw["candidate_pool_operation"] = {
        "mode": "append_supported_handoff",
        "candidate_pool_id": str(fixture.candidate_pool_id),
        "expected_latest_revision_id": str(uuid4()),
        "title": "Stale pool append",
        "scope": "This append must fail closed and roll back prior writes.",
    }
    service = IndustryThesisOwnerAcceptanceService(
        database,
        clock=lambda: _OWNER.BASE_TIME + timedelta(seconds=3),
    )
    appended = _track_successful_stage1_appends(service, monkeypatch)
    before = _state_snapshot(database)

    with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
        service.commit(_commit_input(raw))

    assert caught.value.code == "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT"
    assert len(appended) == 1
    assert _state_snapshot(database) == before


def test_output_link_failure_rolls_back_candidate_pool_and_accepted_session(
    database,
    monkeypatch,
):
    _fixture, _review, _map, _map_revision, rows, raw = _one_member_raw(database)
    binding = raw["candidate_owner_bindings"][0]
    _set_append_stage1(
        database,
        binding,
        beneficiary_id=rows[0][0].id,
        revision_id=rows[0][1].id,
        expected_latest_revision_id=rows[0][1].id,
        rationale="Every prior owner write must roll back after output-link failure.",
    )
    service = IndustryThesisOwnerAcceptanceService(
        database,
        clock=lambda: _OWNER.BASE_TIME + timedelta(seconds=3),
    )
    appended = _track_successful_stage1_appends(service, monkeypatch)
    reached = {"output_link": False}

    def fail_output_link(session, **kwargs):
        reached["output_link"] = True
        accepted = kwargs["accepted_session"]
        assert accepted.workflow_state == "accepted_outputs_linked"
        assert session.get(IndustryThesisSessionRevision, accepted.id) is accepted
        assert kwargs["pool_result"] is not None
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_CONFLICT",
            "injected output-link failure after all prior owner writes",
        )

    monkeypatch.setattr(service, "_append_output_link", fail_output_link)
    before = _state_snapshot(database)

    with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
        service.commit(_commit_input(raw))

    assert caught.value.code == "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_CONFLICT"
    assert reached["output_link"] is True
    assert len(appended) == 1
    assert _state_snapshot(database) == before


def test_thesis_session_stale_expected_latest_blocks_without_writes(database):
    _fixture, review, _map, _map_revision, _rows, raw = _one_member_raw(database)
    raw["expected_session_latest_revision_number"] = (
        review["reviewed_session_revision_number"] + 1
    )
    service = IndustryThesisOwnerAcceptanceService(
        database,
        clock=lambda: _OWNER.BASE_TIME + timedelta(seconds=3),
    )
    before = _state_snapshot(database)

    preview = service.preview(raw)
    assert preview["commit_ready"] is False
    assert preview["blocked_reasons"][0]["code"] == (
        "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE"
    )
    with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
        service.commit(_commit_input(raw))
    assert caught.value.code == "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE"
    assert _state_snapshot(database) == before


def test_conflicting_replay_is_rejected_and_original_output_remains_exact(database):
    _fixture, _review, _map, _map_revision, _rows, raw = _one_member_raw(database)
    committed = _commit_success(database, raw)
    after_first_commit = _state_snapshot(database)
    conflicting = deepcopy(raw)
    conflicting["output_title"] = "Conflicting replay title"
    conflicting["revision_note"] = "A distinct owner plan must not replace accepted history."
    service = IndustryThesisOwnerAcceptanceService(
        database,
        clock=lambda: _OWNER.BASE_TIME + timedelta(seconds=4),
    )

    preview = service.preview(conflicting)
    assert preview["commit_ready"] is False
    assert preview["blocked_reasons"][0]["code"] == (
        "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_CONFLICT"
    )
    with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
        service.commit(_commit_input(conflicting))
    assert caught.value.code == "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_CONFLICT"
    assert _state_snapshot(database) == after_first_commit

    recorded = datetime.fromisoformat(committed["recorded_at_utc"])
    with database() as session:
        output = IndustryThesisAcceptedOutputQueryService(session).get_output(
            UUID(committed["output_link_revision_id"]),
            as_of_cutoff=_OWNER.CUTOFF,
            as_of_recorded_at_utc=recorded,
        )
    assert output["output_link_revision_id"] == committed["output_link_revision_id"]


def test_exact_reads_apply_both_as_of_boundaries_and_never_fallback(database):
    _fixture, _review, _map, _map_revision, _rows, raw = _one_member_raw(database)
    committed = _commit_success(database, raw)
    output_id = UUID(committed["output_link_revision_id"])
    recorded = datetime.fromisoformat(committed["recorded_at_utc"])

    for method_name in ("get_output", "get_result", "get_readiness"):
        with database() as session:
            query = IndustryThesisAcceptedOutputQueryService(session)
            method = getattr(query, method_name)
            visible = method(
                output_id,
                as_of_cutoff=_OWNER.CUTOFF,
                as_of_recorded_at_utc=recorded,
            )
            assert visible["output_link_revision_id"] == str(output_id)

    _assert_all_exact_reads_fail(
        database,
        output_id,
        as_of_cutoff=_OWNER.CUTOFF - timedelta(days=1),
        as_of_recorded_at_utc=recorded,
    )
    _assert_all_exact_reads_fail(
        database,
        output_id,
        as_of_cutoff=_OWNER.CUTOFF,
        as_of_recorded_at_utc=recorded - timedelta(microseconds=1),
    )
    _assert_all_exact_reads_fail(
        database,
        uuid4(),
        as_of_cutoff=_OWNER.CUTOFF,
        as_of_recorded_at_utc=recorded + timedelta(days=1),
    )


@pytest.mark.parametrize(
    "corruption",
    ("binding_revision_replaced", "accepted_output_link_mismatch"),
)
def test_exact_graph_corruption_fails_closed_for_all_read_surfaces(
    database,
    corruption: str,
):
    _fixture, _review, _map, _map_revision, _rows, raw = _one_member_raw(database)
    committed = _commit_success(database, raw)
    output_id = UUID(committed["output_link_revision_id"])
    accepted_id = UUID(committed["accepted_session_revision_id"])
    recorded = datetime.fromisoformat(committed["recorded_at_utc"])

    if corruption == "binding_revision_replaced":
        with database() as session:
            stored_bindings = session.scalar(
                select(
                    IndustryThesisOutputLinkRevision.ordered_owner_output_bindings_json
                ).where(IndustryThesisOutputLinkRevision.id == output_id)
            )
        bindings = json_value(stored_bindings, "stored owner bindings")
        bindings[0]["beneficiary_revision_id"] = str(uuid4())
        with database.begin() as session:
            session.execute(
                update(IndustryThesisOutputLinkRevision)
                .where(IndustryThesisOutputLinkRevision.id == output_id)
                .values(
                    ordered_owner_output_bindings_json=canonical_json_text(
                        bindings,
                        "corrupted owner bindings fixture",
                    )
                )
            )
    else:
        with database() as session:
            stored_graph = session.scalar(
                select(IndustryThesisSessionRevision.draft_graph_json).where(
                    IndustryThesisSessionRevision.id == accepted_id
                )
            )
        graph = json_value(stored_graph, "stored accepted graph")
        graph["output_link_revision_id"] = str(uuid4())
        with database.begin() as session:
            session.execute(
                update(IndustryThesisSessionRevision)
                .where(IndustryThesisSessionRevision.id == accepted_id)
                .values(
                    draft_graph_json=canonical_json_text(
                        graph,
                        "corrupted accepted graph fixture",
                    )
                )
            )

    _assert_all_exact_reads_fail(
        database,
        output_id,
        as_of_cutoff=_OWNER.CUTOFF,
        as_of_recorded_at_utc=recorded + timedelta(days=1),
    )
