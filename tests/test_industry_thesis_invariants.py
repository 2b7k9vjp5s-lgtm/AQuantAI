from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.errors import EvidenceLedgerImmutableError
import industry_alpha.stage1_models  # noqa: F401 - register output-link FK targets
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_models import IndustryThesisSessionIdentity
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


def thesis_input() -> dict:
    return {
        "thesis_text_original": "离线行业命题",
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
