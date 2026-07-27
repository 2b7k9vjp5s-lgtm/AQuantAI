from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.today_market_refresh import (
    REQUIRED_CAPABILITY_FAMILIES,
    DeterministicTodayMarketMock,
    FailureCategory,
    MockScenario,
    OrchestrationState,
    RefreshTrigger,
    SnapshotReference,
    TodayMarketRefreshIntent,
    canonical_sha256,
    run_mock_refresh,
)

FIXTURES = Path(__file__).parent / "fixtures" / "today_market_mock"


def _intent() -> TodayMarketRefreshIntent:
    return TodayMarketRefreshIntent(
        scope_revision_id="scope-synthetic-v1",
        trigger=RefreshTrigger.APPLICATION_START,
        prior_snapshot_id="snapshot-prior",
        local_clock_utc=datetime(2026, 7, 27, 2, 0, tzinfo=timezone.utc),
    )


def _prior() -> SnapshotReference:
    return SnapshotReference(
        snapshot_id="snapshot-prior",
        data_through_session=date(2026, 7, 24),
        content_fingerprint="b" * 64,
    )


def _sessions(count: int) -> tuple[date, ...]:
    start = date(2026, 7, 24)
    return tuple(start + timedelta(days=index) for index in range(count))


@pytest.mark.parametrize(
    ("scenario", "expected_category", "expected_code"),
    (
        (
            MockScenario.PARTIAL_FAMILY_FAILURE,
            FailureCategory.COVERAGE_INCOMPLETE,
            "mock_batch_coverage_incomplete",
        ),
        (
            MockScenario.SCHEMA_MISMATCH,
            FailureCategory.SCHEMA_MISMATCH,
            "mock_family_schema_invalid",
        ),
        (
            MockScenario.COVERAGE_INCOMPLETE,
            FailureCategory.COVERAGE_INCOMPLETE,
            "mock_batch_coverage_incomplete",
        ),
        (
            MockScenario.QUOTA_ASSUMPTION_EXHAUSTED,
            FailureCategory.ASSUMPTION_BUDGET_EXHAUSTED,
            "mock_daily_budget_exhausted",
        ),
    ),
)
def test_failure_scenarios_retain_prior_and_publish_nothing(
    scenario: MockScenario,
    expected_category: FailureCategory,
    expected_code: str,
) -> None:
    prior = _prior()
    outcome = run_mock_refresh(
        intent=_intent(),
        expected_completed_sessions=_sessions(2),
        prior_snapshot=prior,
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
        port=DeterministicTodayMarketMock(
            fixture_root=FIXTURES,
            scenario=scenario,
        ),
    )
    assert outcome.state is OrchestrationState.FAILED_RETAINED_PRIOR
    assert outcome.prior_snapshot is prior
    assert outcome.candidate_projection is None
    assert outcome.failure is not None
    assert outcome.failure.category is expected_category
    assert outcome.failure.failure_code == expected_code
    rendered = repr(outcome)
    assert "X-api-key" not in rendered
    assert "request_id" not in rendered


def test_missing_fixture_returns_typed_redacted_failure(tmp_path: Path) -> None:
    prior = _prior()
    outcome = run_mock_refresh(
        intent=_intent(),
        expected_completed_sessions=_sessions(2),
        prior_snapshot=prior,
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
        port=DeterministicTodayMarketMock(fixture_root=tmp_path),
    )
    assert outcome.state is OrchestrationState.FAILED_RETAINED_PRIOR
    assert outcome.prior_snapshot is prior
    assert outcome.candidate_projection is None
    assert outcome.failure is not None
    assert outcome.failure.category is FailureCategory.SCHEMA_MISMATCH
    assert outcome.failure.failure_code == "mock_fixture_contract_invalid"
    assert str(tmp_path) not in repr(outcome)


def test_application_shutdown_before_publish_retains_prior() -> None:
    prior = _prior()
    outcome = run_mock_refresh(
        intent=_intent(),
        expected_completed_sessions=_sessions(2),
        prior_snapshot=prior,
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
        port=DeterministicTodayMarketMock(fixture_root=FIXTURES),
        shutdown_requested=lambda: True,
    )
    assert outcome.state is OrchestrationState.CANCELLED_RETAINED_PRIOR
    assert outcome.prior_snapshot is prior
    assert outcome.candidate_projection is None
    assert outcome.failure is not None
    assert outcome.failure.category is FailureCategory.APPLICATION_SHUTDOWN
    assert outcome.failure.failure_code == "application_shutdown_before_publish"
    assert outcome.message_zh == "应用已关闭，更新未继续执行"


def test_no_refresh_and_manual_catchup_never_call_adapter() -> None:
    current_adapter = DeterministicTodayMarketMock(fixture_root=FIXTURES)
    current = run_mock_refresh(
        intent=_intent(),
        expected_completed_sessions=(date(2026, 7, 24),),
        prior_snapshot=_prior(),
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
        port=current_adapter,
    )
    assert current.state is OrchestrationState.NO_REFRESH_NEEDED
    assert current_adapter.call_count == 0

    catchup_adapter = DeterministicTodayMarketMock(fixture_root=FIXTURES)
    catchup = run_mock_refresh(
        intent=_intent(),
        expected_completed_sessions=_sessions(12),
        prior_snapshot=_prior(),
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
        port=catchup_adapter,
    )
    assert catchup.state is OrchestrationState.MANUAL_CATCHUP_REQUIRED
    assert catchup_adapter.call_count == 0


def test_synthetic_correction_creates_distinct_candidate_fingerprint() -> None:
    kwargs = dict(
        intent=_intent(),
        expected_completed_sessions=_sessions(2),
        prior_snapshot=_prior(),
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
    )
    base = run_mock_refresh(
        port=DeterministicTodayMarketMock(
            fixture_root=FIXTURES,
            scenario=MockScenario.STALE_SUCCESS,
        ),
        **kwargs,
    )
    correction = run_mock_refresh(
        port=DeterministicTodayMarketMock(
            fixture_root=FIXTURES,
            scenario=MockScenario.SYNTHETIC_CORRECTION_REVISION,
        ),
        **kwargs,
    )
    assert base.state is correction.state is OrchestrationState.PUBLISHED_DEMO
    assert base.candidate_projection is not None
    assert correction.candidate_projection is not None
    assert (
        base.candidate_projection.projection_fingerprint
        != correction.candidate_projection.projection_fingerprint
    )
    assert base.prior_snapshot == correction.prior_snapshot == _prior()


def test_ten_session_golden_path_is_complete_and_in_memory_only() -> None:
    prior = _prior()
    outcome = run_mock_refresh(
        intent=_intent(),
        expected_completed_sessions=_sessions(11),
        prior_snapshot=prior,
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
        port=DeterministicTodayMarketMock(fixture_root=FIXTURES),
    )
    assert outcome.state is OrchestrationState.PUBLISHED_DEMO
    assert outcome.prior_snapshot is prior
    assert outcome.plan is not None
    assert len(outcome.plan.requested_completed_sessions) == 10
    assert outcome.candidate_projection is not None
    assert len(outcome.candidate_projection.projection_fingerprint) == 64
    assert outcome.candidate_projection.projection_fingerprint != canonical_sha256(
        prior
    )
