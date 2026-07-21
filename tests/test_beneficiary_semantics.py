from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import json
import socket
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.beneficiary_semantics_commands import (
    BeneficiarySemanticCommandService,
)
from industry_alpha.beneficiary_semantics_contracts import (
    DRIVER_STATES,
    EXPOSURE_STATES,
    TAXONOMY_VERSION,
)
from industry_alpha.beneficiary_semantics_models import (
    Stage1BeneficiarySemanticProfileRevision,
)
from industry_alpha.beneficiary_semantics_query import BeneficiarySemanticQueryService
from industry_alpha.beneficiary_semantics_repository import BeneficiarySemanticRepository
from industry_alpha.chain_map_models import (
    IndustryMapObservation,
    IndustryMapObservationRevision,
    IndustryMapRevision,
)
from industry_alpha.errors import (
    EvidenceLedgerConflictError,
    EvidenceLedgerNotVisible,
    EvidenceLedgerValidationError,
)
from industry_alpha.models import Claim, ClaimRevision
from industry_alpha.stage1_commands import (
    MapAssertionRevisionInput,
    Stage1BeneficiaryCommandService,
)
from industry_alpha.stage1_fixtures import build_stage1_beneficiary_fixture
from industry_alpha.stage1_models import Stage1BeneficiaryRevision
import scripts.record_beneficiary_semantics as semantics_cli


def _recorded(day: int) -> datetime:
    return datetime(2026, 7, day, 12, tzinfo=timezone.utc)


@pytest.fixture()
def semantic_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    fixture = build_stage1_beneficiary_fixture(factory)

    with factory() as session:
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

    beneficiary_revision = Stage1BeneficiaryCommandService(
        factory
    ).append_beneficiary_revision(
        fixture.direct_beneficiary_id,
        selected_map_revision_id=map_revision.id,
        stock_basic_record_id=prior.stock_basic_record_id,
        beneficiary_kind="direct",
        assessment_status="supported",
        rationale_summary=(
            "Fixture revision freezes one exact driver and two attributable claims "
            "for typed semantic testing."
        ),
        information_cutoff_date=date(2026, 7, 10),
        assertion_revisions=(
            MapAssertionRevisionInput("observation", driver_revision.id),
        ),
        claim_revision_ids=(direct_claim.id, driver_claim.id),
        recorded_at_utc=_recorded(10),
    )
    context = {
        "engine": engine,
        "factory": factory,
        "beneficiary_id": fixture.direct_beneficiary_id,
        "beneficiary_revision_id": beneficiary_revision.id,
        "map_revision_id": map_revision.id,
        "driver_revision_id": driver_revision.id,
        "direct_claim_id": direct_claim.id,
        "driver_claim_id": driver_claim.id,
    }
    yield context
    engine.dispose()


def _payload(context):
    direct_claim = str(context["direct_claim_id"])
    driver_claim = str(context["driver_claim_id"])
    assertions = [
        {
            "assertion_key": "exposure",
            "field_kind": "exposure",
            "state_code": "direct",
            "evidence_state": "supported",
            "rationale": "The exact frozen company claim supports direct exposure.",
            "position": 0,
            "claim_links": [
                {"claim_revision_id": direct_claim, "relation": "support"}
            ],
        },
        {
            "assertion_key": "driver-demand",
            "field_kind": "driver",
            "state_code": "demand_expansion/end_demand_growth",
            "evidence_state": "supported",
            "rationale": "The exact frozen map driver has attributable B-grade support.",
            "map_observation_revision_id": str(context["driver_revision_id"]),
            "position": 0,
            "claim_links": [
                {"claim_revision_id": driver_claim, "relation": "support"}
            ],
        },
        {
            "assertion_key": "offering-product",
            "field_kind": "offering",
            "state_code": "product",
            "evidence_state": "supported",
            "subject_text": "Fixture attributable product",
            "rationale": "The exact frozen company claim supports this explicit offering.",
            "position": 0,
            "claim_links": [
                {"claim_revision_id": direct_claim, "relation": "support"}
            ],
        },
    ]
    verification_items = []
    for field in ("customer", "certification", "capacity", "production"):
        key = f"{field}-unknown"
        assertions.append(
            {
                "assertion_key": key,
                "field_kind": field,
                "state_code": "unknown",
                "evidence_state": "missing",
                "rationale": f"The fixture does not contain typed {field} evidence.",
                "position": 0,
                "claim_links": [],
            }
        )
        verification_items.append(
            {
                "assertion_key": key,
                "verification_question": f"What attributable evidence resolves {field}?",
                "expected_evidence_type": "Exact accepted claim revision with attributable evidence",
            }
        )
    assertions.append(
        {
            "assertion_key": "order-na",
            "field_kind": "order",
            "state_code": "not_applicable",
            "evidence_state": "not_applicable",
            "rationale": "The explicit fixture scope models no order relationship.",
            "position": 0,
            "claim_links": [
                {"claim_revision_id": direct_claim, "relation": "context"}
            ],
        }
    )
    return {
        "beneficiary_id": str(context["beneficiary_id"]),
        "beneficiary_revision_id": str(context["beneficiary_revision_id"]),
        "selected_map_revision_id": str(context["map_revision_id"]),
        "taxonomy_version": TAXONOMY_VERSION,
        "overall_status": "supported",
        "summary": "Fixture typed beneficiary semantic profile.",
        "recorded_by": "fixture-analyst",
        "information_cutoff_date": "2026-07-10",
        "recorded_at_utc": "2026-07-10T12:00:00Z",
        "expected_latest_revision_id": None,
        "assertions": assertions,
        "verification_items": verification_items,
    }


def test_closed_vocabulary_has_no_ranking_semantics():
    assert EXPOSURE_STATES == {"direct", "conditional", "indirect", "conceptual"}
    assert "demand_expansion/end_demand_growth" in DRIVER_STATES
    assert not {"score", "rank", "recommendation", "target_price"}.intersection(
        EXPOSURE_STATES | DRIVER_STATES
    )


def test_record_query_and_historical_cutoff(semantic_context):
    service = BeneficiarySemanticCommandService(semantic_context["factory"])
    preview = service.validate(_payload(semantic_context))
    assert preview["dry_run"] is True
    assert preview["next_revision_no"] == 1

    result = service.record(_payload(semantic_context))
    assert result["revision_no"] == 1
    assert result["assertion_count"] == 8
    assert result["verification_item_count"] == 4

    with semantic_context["factory"]() as session:
        query = BeneficiarySemanticQueryService(
            BeneficiarySemanticRepository(session)
        )
        payload = query.get_profile(semantic_context["beneficiary_id"]).to_dict()
        latest = payload["latest_revision"]
        assert latest["frozen_stage1"]["legacy_beneficiary_kind"] == "direct"
        assert latest["taxonomy_version"] == TAXONOMY_VERSION
        assert latest["missing_assertion_keys"] == [
            "capacity-unknown",
            "certification-unknown",
            "customer-unknown",
            "production-unknown",
        ]
        driver = next(
            item for item in latest["assertions"] if item["field_kind"] == "driver"
        )
        assert driver["driver"]["driver_type"] == "demand_expansion"
        assert driver["evidence_grade_counts"]["B"] >= 1
        with pytest.raises(EvidenceLedgerNotVisible):
            query.get_profile(
                semantic_context["beneficiary_id"], as_of_cutoff=date(2026, 7, 9)
            )


def test_stale_expected_revision_is_atomic(semantic_context):
    service = BeneficiarySemanticCommandService(semantic_context["factory"])
    service.record(_payload(semantic_context))
    stale = deepcopy(_payload(semantic_context))
    stale["expected_latest_revision_id"] = str(uuid4())
    stale["recorded_at_utc"] = "2026-07-11T12:00:00Z"
    stale["information_cutoff_date"] = "2026-07-11"
    with pytest.raises(EvidenceLedgerConflictError):
        service.record(stale)
    with semantic_context["factory"]() as session:
        assert session.scalar(
            select(func.count()).select_from(Stage1BeneficiarySemanticProfileRevision)
        ) == 1


def test_missing_requires_verification_and_frozen_claim(semantic_context):
    payload = _payload(semantic_context)
    payload["verification_items"] = []
    with pytest.raises(EvidenceLedgerValidationError, match="missing assertion"):
        BeneficiarySemanticCommandService(semantic_context["factory"]).validate(payload)

    payload = _payload(semantic_context)
    payload["assertions"][0]["claim_links"][0]["claim_revision_id"] = str(uuid4())
    with pytest.raises(EvidenceLedgerValidationError, match="already be frozen"):
        BeneficiarySemanticCommandService(semantic_context["factory"]).validate(payload)


def test_cli_dry_run_is_local_and_redacts_input_path(
    semantic_context, tmp_path, monkeypatch, capsys
):
    input_path = tmp_path / "semantic-input.json"
    input_path.write_text(
        json.dumps(_payload(semantic_context), ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setattr(
        semantics_cli, "build_engine", lambda: semantic_context["engine"]
    )

    def reject_network(_socket, _address):
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    assert semantics_cli.main(["--input", str(input_path), "--dry-run"]) == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["status"] == "ok"
    assert payload["result"]["dry_run"] is True
    assert str(input_path) not in output
