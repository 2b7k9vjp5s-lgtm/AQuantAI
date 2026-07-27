"""Run the deterministic Today Market Mock golden path with zero network."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any

from backend.today_market_refresh import (
    REQUIRED_CAPABILITY_FAMILIES,
    SYNTHETIC_SOURCE_KEY,
    DeterministicTodayMarketMock,
    RefreshTrigger,
    SnapshotReference,
    TodayMarketRefreshIntent,
    run_mock_refresh,
)

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "today_market_mock"


def build_demo_summary() -> dict[str, Any]:
    prior = SnapshotReference(
        snapshot_id="synthetic-prior-snapshot",
        data_through_session=date(2026, 7, 24),
        content_fingerprint="c" * 64,
    )
    outcome = run_mock_refresh(
        intent=TodayMarketRefreshIntent(
            scope_revision_id="synthetic-today-market-scope-v1",
            trigger=RefreshTrigger.APPLICATION_START,
            prior_snapshot_id=prior.snapshot_id,
            local_clock_utc=datetime(2026, 7, 27, 3, 0, tzinfo=timezone.utc),
        ),
        expected_completed_sessions=(date(2026, 7, 24), date(2026, 7, 25)),
        prior_snapshot=prior,
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
        port=DeterministicTodayMarketMock(fixture_root=FIXTURES),
    )
    projection = outcome.candidate_projection
    if projection is None or outcome.plan is None:
        raise RuntimeError(
            "Today Market Mock golden path did not produce a candidate projection"
        )
    return {
        "state": outcome.state.value,
        "message_zh": outcome.message_zh,
        "is_synthetic": projection.is_synthetic,
        "source_key": SYNTHETIC_SOURCE_KEY,
        "source_label": projection.source_label,
        "production_live_source_ready": projection.production_live_source_ready,
        "overall_live_gate": projection.overall_live_gate,
        "data_through_session": projection.data_through_session.isoformat(),
        "plan_fingerprint": outcome.plan.plan_fingerprint,
        "projection_fingerprint": projection.projection_fingerprint,
        "prior_snapshot_retained_until_candidate": outcome.prior_snapshot is prior,
        "network_used": False,
        "credentials_used": False,
        "persistence_used": False,
    }


def main() -> None:
    print(
        json.dumps(
            build_demo_summary(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
