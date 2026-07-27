"""Zero-network demo for Today Market runtime integration v1."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any

from backend.api.today_market import TodayMarketBoundaries, TodayMarketSnapshotRequest
from backend.today_market_refresh import (
    MockScenario,
    RefreshTrigger,
    SnapshotReference,
    TodayMarketMockRuntimeConfigurationV1,
    TodayMarketPriorSnapshotContext,
    TodayMarketRuntimeCoordinator,
    build_runtime_scope,
)

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "today_market_mock"


def build_runtime_demo_summary() -> dict[str, Any]:
    recorded = datetime(2026, 7, 27, 3, 0, tzinfo=timezone.utc)
    request = TodayMarketSnapshotRequest(
        equity_series_key="runtime-demo-equity-series",
        benchmark_series_key=None,
        sector_series_key=None,
        boundaries=TodayMarketBoundaries(
            cutoff=date(2026, 7, 27),
            cutoff_compact="20260727",
            recorded_at=recorded,
            recorded_at_iso=recorded.isoformat().replace("+00:00", "Z"),
        ),
    )
    reference = SnapshotReference(
        snapshot_id="today-market-local-v1:runtime-demo",
        data_through_session=date(2026, 7, 24),
        content_fingerprint="d" * 64,
    )
    prior = TodayMarketPriorSnapshotContext(
        snapshot_reference=reference,
        identity_payload={"snapshot_id": reference.snapshot_id},
        content_payload={"content_fingerprint": reference.content_fingerprint},
        projected_snapshot={"status": "complete_selected_scope"},
    )
    disabled = TodayMarketMockRuntimeConfigurationV1()
    disabled_scope = build_runtime_scope(
        request=request,
        prior=prior,
        configuration=disabled,
    )
    disabled_status = TodayMarketRuntimeCoordinator().get_status(
        disabled_scope,
        disabled,
    )

    enabled = TodayMarketMockRuntimeConfigurationV1(
        mock_enabled=True,
        mock_scenario_id=MockScenario.STALE_SUCCESS.value,
    )
    enabled_scope = build_runtime_scope(
        request=request,
        prior=prior,
        configuration=enabled,
    )
    coordinator = TodayMarketRuntimeCoordinator()
    initial = coordinator.get_status(enabled_scope, enabled)
    completed = coordinator.execute(
        scope=enabled_scope,
        configuration=enabled,
        expected_runtime_status_fingerprint=initial[
            "runtime_status_fingerprint"
        ],
        trigger=RefreshTrigger.FIRST_TODAY_MARKET_ENTRY,
        fixture_root=FIXTURES,
    )
    replay = coordinator.execute(
        scope=enabled_scope,
        configuration=enabled,
        expected_runtime_status_fingerprint=initial[
            "runtime_status_fingerprint"
        ],
        trigger=RefreshTrigger.FIRST_TODAY_MARKET_ENTRY,
        fixture_root=FIXTURES,
    )
    return {
        "default_application": {
            "phase": disabled_status["phase"],
            "mock_enabled": disabled_status["mock_enabled"],
            "automatic_acquisition": False,
        },
        "demo_application": {
            "initial_phase": initial["phase"],
            "completed_phase": completed["phase"],
            "automatic_attempt_state": completed["automatic_attempt_state"],
            "is_synthetic": completed["candidate_projection"]["is_synthetic"],
            "data_through_session": completed["candidate_projection"][
                "data_through_session"
            ],
            "production_live_source_ready": completed["candidate_projection"][
                "production_live_source_ready"
            ],
            "scope_revision_id": completed["runtime_scope_revision_id"],
            "status_fingerprint": completed["runtime_status_fingerprint"],
            "completed_replay_identical": (
                replay["runtime_status_fingerprint"]
                == completed["runtime_status_fingerprint"]
            ),
        },
        "network_used": False,
        "credentials_used": False,
        "database_write_used": False,
        "background_work_used": False,
        "live_ths_gate": "Issue #225 remains open",
    }


def main() -> None:
    print(
        json.dumps(
            build_runtime_demo_summary(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
