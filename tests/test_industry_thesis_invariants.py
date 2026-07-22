from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.errors import EvidenceLedgerImmutableError
import industry_alpha.stage1_models  # noqa: F401 - register output-link FK targets
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateIdentity,
    IndustryThesisCandidateRevision,
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_rules import BUILDER_VERSION

UTC = timezone.utc
NOW = datetime(2026, 7, 22, 17, 0, tzinfo=UTC)


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


def thesis_input(*, title: str = "离线行业命题") -> dict:
    return {
        "thesis_text_original": title,
        "thesis_title_reviewed": None,
        "driver_type": "unknown",
        "analysis_horizon_kind": "unknown",
        "market_scope": [
            {
                "market_namespace": "CN_A",
                "exchange_namespace": None,
                "security_type": "common_equity",
                "include_status": "active",
                "listed_instrument_ids": [],
            }
        ],
        "chain_boundary": {},
        "exclusions": [],
        "seed_companies": [],
        "seed_products": [],
        "seed_technologies": [],
        "seed_bottlenecks": [],
        "draft_graph": {},
        "coverage_state": "coverage_unknown",
        "workflow_state": "candidate_build_ready",
        "information_cutoff_date": date(2026, 7, 22).isoformat(),
        "revision_note": "test",
    }


def build_input(session_revision_id: str) -> dict:
    return {
        "session_revision_id": session_revision_id,
        "expected_session_latest_revision_number": 1,
        "builder_version": BUILDER_VERSION,
        "allowed_source_kinds": ["user_seed"],
        "proposals": [
            {
                "source_kind": "user_seed",
                "source_reference": {"seed_key": "same-time"},
                "company_label_original": "待核验公司",
                "benefit_path_text": "用户提供的待核验候选。",
                "proposed_exposure_type": "unknown",
                "proposal_confidence": "unknown",
                "identity_state": "unresolved_identity",
                "review_state": "proposed",
                "rationale": {},
                "uncertainty": {"identity": "unresolved"},
            }
        ],
    }


def test_candidate_recorded_time_must_be_later_than_session_revision(database) -> None:
    service = IndustryThesisCommandService(
        database,
        clock=SequenceClock(NOW, NOW),
    )
    created = service.create_session(thesis_input())
    with pytest.raises(EvidenceLedgerImmutableError, match="must be later"):
        service.build_candidates(build_input(created["session_revision_id"]))


def test_session_identity_state_is_not_an_ordinary_mutable_field(database) -> None:
    service = IndustryThesisCommandService(database, clock=SequenceClock(NOW))
    created = service.create_session(thesis_input())
    with database() as session:
        identity = session.get(IndustryThesisSessionIdentity, UUID(created["session_id"]))
        identity.state = "completed"
        with pytest.raises(EvidenceLedgerImmutableError, match="identity fields are immutable"):
            session.flush()
        session.rollback()


def test_session_revision_cannot_supersede_another_session(database) -> None:
    service = IndustryThesisCommandService(
        database,
        clock=SequenceClock(NOW, NOW + timedelta(seconds=1)),
    )
    first = service.create_session(thesis_input(title="Session A"))
    second = service.create_session(thesis_input(title="Session B"))
    with database() as session:
        first_revision = session.get(
            IndustryThesisSessionRevision,
            UUID(first["session_revision_id"]),
        )
        session.add(
            IndustryThesisSessionRevision(
                session_id=UUID(first["session_id"]),
                revision_number=2,
                thesis_text_original=first_revision.thesis_text_original,
                thesis_title_reviewed="Invalid cross-session chain",
                driver_type=first_revision.driver_type,
                analysis_horizon_kind=first_revision.analysis_horizon_kind,
                analysis_start_date=first_revision.analysis_start_date,
                analysis_end_date=first_revision.analysis_end_date,
                market_scope_json=first_revision.market_scope_json,
                chain_boundary_json=first_revision.chain_boundary_json,
                exclusions_json=first_revision.exclusions_json,
                seed_companies_json=first_revision.seed_companies_json,
                seed_products_json=first_revision.seed_products_json,
                seed_technologies_json=first_revision.seed_technologies_json,
                seed_bottlenecks_json=first_revision.seed_bottlenecks_json,
                draft_graph_json=first_revision.draft_graph_json,
                coverage_state=first_revision.coverage_state,
                workflow_state=first_revision.workflow_state,
                information_cutoff_date=first_revision.information_cutoff_date,
                recorded_at_utc=NOW + timedelta(seconds=2),
                input_fingerprint_sha256="a" * 64,
                supersedes_revision_id=UUID(second["session_revision_id"]),
                revision_note="invalid cross-session supersedes",
            )
        )
        with pytest.raises(EvidenceLedgerImmutableError, match="same session identity"):
            session.flush()
        session.rollback()


def test_candidate_revision_cannot_cross_session_ownership(database) -> None:
    service = IndustryThesisCommandService(
        database,
        clock=SequenceClock(NOW, NOW + timedelta(seconds=1)),
    )
    first = service.create_session(thesis_input(title="Candidate session A"))
    second = service.create_session(thesis_input(title="Candidate session B"))
    with database() as session:
        candidate = IndustryThesisCandidateIdentity(
            session_id=UUID(first["session_id"]),
            candidate_key="b" * 64,
            created_recorded_utc=NOW + timedelta(seconds=2),
            latest_revision_number=0,
        )
        session.add(candidate)
        session.flush()
        session.add(
            IndustryThesisCandidateRevision(
                candidate_id=candidate.id,
                session_revision_id=UUID(second["session_revision_id"]),
                revision_number=1,
                source_kind="user_seed",
                source_reference_json='{"seed_key":"cross-session"}',
                proposed_stock_basic_record_id=None,
                proposed_listed_instrument_id=None,
                company_label_original="跨会话候选",
                product_or_service_fit=None,
                industry_position=None,
                benefit_path_text="该直接写入必须失败。",
                proposed_exposure_type="unknown",
                proposal_confidence="unknown",
                identity_state="unresolved_identity",
                review_state="proposed",
                rationale_json="{}",
                uncertainty_json="{}",
                manifest_fingerprint_sha256=None,
                information_cutoff_date=date(2026, 7, 22),
                recorded_at_utc=NOW + timedelta(seconds=3),
                supersedes_revision_id=None,
            )
        )
        with pytest.raises(EvidenceLedgerImmutableError, match="same session"):
            session.flush()
        session.rollback()
