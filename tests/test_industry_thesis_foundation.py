from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from backend.database.canonical_price_models import ListedInstrument
from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.errors import EvidenceLedgerImmutableError
import industry_alpha.stage1_models  # noqa: F401 - register output-link FK targets
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_models import (
    INDUSTRY_THESIS_MODELS,
    IndustryThesisCandidateIdentity,
    IndustryThesisCandidateRevision,
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_query import IndustryThesisQueryService
from industry_alpha.industry_thesis_rules import (
    BUILDER_VERSION,
    IndustryThesisError,
    IndustryThesisNotFound,
    canonical_json_text,
    fingerprint,
    normalize_session_payload,
)

UTC = timezone.utc
BASE_TIME = datetime(2026, 7, 22, 16, 0, tzinfo=UTC)
CUTOFF = date(2026, 7, 22)


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


def session_input(**overrides):
    raw = {
        "thesis_text_original": "先进材料需求扩张与关键工艺瓶颈",
        "thesis_title_reviewed": "先进材料产业链",
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
        "chain_boundary": {"included": ["materials", "processing"]},
        "exclusions": [],
        "seed_companies": [],
        "seed_products": ["synthetic-material"],
        "seed_technologies": [],
        "seed_bottlenecks": ["purification"],
        "draft_graph": {"nodes": [], "relationships": []},
        "coverage_state": "partial_local_coverage",
        "workflow_state": "draft",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "initial offline thesis",
    }
    raw.update(overrides)
    return raw


def proposal(
    *,
    source_kind: str,
    source_reference: dict,
    label: str,
    identity_state: str,
    instrument_id: UUID | None = None,
    expected_latest_revision_number: int | None = None,
):
    raw = {
        "source_kind": source_kind,
        "source_reference": source_reference,
        "company_label_original": label,
        "benefit_path_text": f"{label} participates in the reviewed synthetic chain.",
        "proposed_exposure_type": (
            "direct" if identity_state == "exact_accepted_identity" else "unknown"
        ),
        "proposal_confidence": "medium",
        "identity_state": identity_state,
        "review_state": "proposed",
        "rationale": {"reason": "explicit local test input"},
        "uncertainty": {
            "state": "none"
            if identity_state == "exact_accepted_identity"
            else "identity_pending"
        },
    }
    if instrument_id is not None:
        raw["proposed_listed_instrument_id"] = str(instrument_id)
    if expected_latest_revision_number is not None:
        raw["expected_latest_revision_number"] = expected_latest_revision_number
    return raw


def test_exact_six_table_contract() -> None:
    assert {model.__tablename__ for model in INDUSTRY_THESIS_MODELS} == {
        "industry_thesis_session_identities",
        "industry_thesis_session_revisions",
        "industry_thesis_candidate_identities",
        "industry_thesis_candidate_revisions",
        "industry_thesis_output_link_identities",
        "industry_thesis_output_link_revisions",
    }


def test_canonical_json_and_fingerprint_are_deterministic_and_float_free() -> None:
    first = {"b": [2, {"x": True}], "a": "value"}
    second = {"a": "value", "b": [2, {"x": True}]}
    assert canonical_json_text(first, "test") == canonical_json_text(second, "test")
    assert fingerprint(first) == fingerprint(second)
    with pytest.raises(IndustryThesisError, match="floating-point"):
        canonical_json_text({"value": 1.5}, "test")


def test_market_scope_is_explicit_and_unknown_fields_fail() -> None:
    raw = session_input()
    raw["market_scope"] = []
    with pytest.raises(IndustryThesisError, match="non-empty"):
        normalize_session_payload(raw)
    raw = session_input(unexpected=True)
    with pytest.raises(IndustryThesisError, match="unknown fields"):
        normalize_session_payload(raw)


def test_create_revise_and_query_dual_as_of(database) -> None:
    clock = SequenceClock(
        BASE_TIME,
        BASE_TIME + timedelta(seconds=1),
        BASE_TIME + timedelta(seconds=2),
    )
    service = IndustryThesisCommandService(database, clock=clock)

    dry_run = service.create_session(session_input(), dry_run=True)
    assert dry_run["dry_run"] is True
    assert dry_run["session_id"] is None
    with database() as session:
        assert session.scalar(
            select(func.count()).select_from(IndustryThesisSessionIdentity)
        ) == 0

    created = service.create_session(session_input())
    assert created["revision_number"] == 1
    session_id = UUID(created["session_id"])
    first_revision_id = UUID(created["session_revision_id"])

    revised = service.revise_session(
        {
            "session_id": str(session_id),
            "expected_latest_revision_number": 1,
            "changes": {
                "workflow_state": "candidate_build_ready",
                "coverage_state": "reviewed_local_scope",
            },
            "revision_note": "reviewed local scope",
        }
    )
    assert revised["revision_number"] == 2
    assert revised["input_fingerprint_sha256"] != created["input_fingerprint_sha256"]

    with pytest.raises(IndustryThesisError, match="expected latest"):
        service.revise_session(
            {
                "session_id": str(session_id),
                "expected_latest_revision_number": 1,
                "changes": {"workflow_state": "awaiting_review"},
                "revision_note": "stale write",
            }
        )

    with database() as session:
        query = IndustryThesisQueryService(session)
        first = query.get_session_revision(
            first_revision_id,
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BASE_TIME + timedelta(seconds=1),
        )
        assert first["revision_number"] == 1
        overview = query.get_session(
            session_id,
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BASE_TIME + timedelta(seconds=2),
        )
        assert overview["visible_revision_count"] == 2
        with pytest.raises(IndustryThesisNotFound, match="recorded-time"):
            query.get_session_revision(
                UUID(revised["session_revision_id"]),
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=BASE_TIME + timedelta(seconds=1),
            )


def test_three_proposal_golden_path_and_deterministic_order(database) -> None:
    with database.begin() as session:
        instrument = ListedInstrument(
            instrument_key="fixture-exact-company",
            created_at_utc=BASE_TIME,
        )
        session.add(instrument)
        session.flush()
        instrument_id = instrument.id

    service = IndustryThesisCommandService(
        database,
        clock=SequenceClock(
            BASE_TIME,
            BASE_TIME + timedelta(seconds=1),
            BASE_TIME + timedelta(seconds=2),
        ),
    )
    created = service.create_session(
        session_input(workflow_state="candidate_build_ready")
    )
    build_input = {
        "session_revision_id": created["session_revision_id"],
        "expected_session_latest_revision_number": 1,
        "builder_version": BUILDER_VERSION,
        "allowed_source_kinds": ["user_seed", "accepted_local_mapping"],
        "proposals": [
            proposal(
                source_kind="user_seed",
                source_reference={"seed_key": "company-c"},
                label="Company C",
                identity_state="unresolved_identity",
            ),
            proposal(
                source_kind="accepted_local_mapping",
                source_reference={"mapping_key": "company-a-product-x"},
                label="Company A",
                identity_state="exact_accepted_identity",
                instrument_id=instrument_id,
            ),
            proposal(
                source_kind="user_seed",
                source_reference={"seed_key": "company-b"},
                label="Company B",
                identity_state="ambiguous_identity",
            ),
        ],
    }
    dry_run = service.build_candidates(build_input, dry_run=True)
    assert dry_run["candidate_count"] == 3
    assert dry_run["candidates"][0]["source_kind"] == "accepted_local_mapping"

    committed = service.build_candidates(build_input)
    assert committed["candidate_count"] == 3
    assert [row["source_kind"] for row in committed["candidates"]] == [
        "accepted_local_mapping",
        "user_seed",
        "user_seed",
    ]
    assert {row["identity_state"] for row in committed["candidates"]} == {
        "exact_accepted_identity",
        "ambiguous_identity",
        "unresolved_identity",
    }

    with database() as session:
        query = IndustryThesisQueryService(session)
        result = query.list_candidate_revisions(
            UUID(created["session_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BASE_TIME + timedelta(seconds=2),
        )
        assert result["candidate_count"] == 3
        assert result["coverage_state"] == "partial_local_coverage"
        assert result["candidates"][0]["company_label_original"] == "Company A"
        assert session.scalar(
            select(func.count()).select_from(IndustryThesisCandidateIdentity)
        ) == 3
        assert session.scalar(
            select(func.count()).select_from(IndustryThesisCandidateRevision)
        ) == 3


def test_duplicate_source_ai_and_stale_candidate_updates_fail(database) -> None:
    service = IndustryThesisCommandService(
        database,
        clock=SequenceClock(
            BASE_TIME,
            BASE_TIME + timedelta(seconds=1),
            BASE_TIME + timedelta(seconds=2),
        ),
    )
    created = service.create_session(
        session_input(workflow_state="candidate_build_ready")
    )
    base_proposal = proposal(
        source_kind="user_seed",
        source_reference={"seed_key": "duplicate"},
        label="Duplicate",
        identity_state="unresolved_identity",
    )
    build = {
        "session_revision_id": created["session_revision_id"],
        "expected_session_latest_revision_number": 1,
        "builder_version": BUILDER_VERSION,
        "allowed_source_kinds": ["user_seed"],
        "proposals": [base_proposal, dict(base_proposal)],
    }
    with pytest.raises(IndustryThesisError, match="same exact candidate source"):
        service.build_candidates(build)

    build["proposals"] = [base_proposal]
    service.build_candidates(build)
    with pytest.raises(IndustryThesisError, match="exact latest revision"):
        service.build_candidates(build)

    ai = dict(base_proposal)
    ai["source_kind"] = "ai_draft"
    ai["manifest_fingerprint_sha256"] = "0" * 64
    build["allowed_source_kinds"] = ["ai_draft"]
    build["proposals"] = [ai]
    with pytest.raises(IndustryThesisError, match="unsupported value"):
        service.build_candidates(build)


def test_append_only_revision_mutation_is_rejected(database) -> None:
    service = IndustryThesisCommandService(database, clock=SequenceClock(BASE_TIME))
    created = service.create_session(session_input())
    with database() as session:
        revision = session.get(
            IndustryThesisSessionRevision,
            UUID(created["session_revision_id"]),
        )
        revision.thesis_text_original = "mutated"
        with pytest.raises(EvidenceLedgerImmutableError, match="append-only"):
            session.flush()
        session.rollback()
