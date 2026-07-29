from __future__ import annotations

from datetime import date, timedelta
import inspect
import json

import pytest

from datasource import ths_structured_provider as ths
from datasource.ths_structured_provider import live_planner, live_selectors


def _equities() -> tuple[ths.EquityIdentity, ...]:
    return (
        ths.EquityIdentity("SYNTH.SSE.EQ001", "990001", ths.Exchange.SSE),
        ths.EquityIdentity("SYNTH.SZSE.EQ002", "990002", ths.Exchange.SZSE),
    )


def _observations(
    identities: tuple[ths.EquityIdentity, ...],
    sessions: tuple[date, ...],
) -> tuple[ths.ExpectedObservation, ...]:
    return tuple(
        ths.ExpectedObservation(identity.identity_key, session)
        for session in sessions
        for identity in identities
    )


def _budget(*, calls: int = 100, cells: int = 1_000_000) -> ths.AcquisitionQuotaBudget:
    return ths.AcquisitionQuotaBudget(
        budget_revision_id="synthetic-budget-revision-v1",
        remaining_calls=calls,
        remaining_cells=cells,
        per_function_qps=10,
        account_total_qps=20,
    )


def test_one_and_ten_session_daily_plans_are_deterministic_and_non_executable() -> None:
    identities = _equities()
    reference = date(2026, 7, 28)

    one_session = (reference,)
    one_selector = ths.AShareDailySelector(
        identities=identities,
        requested_sessions=one_session,
        expected_observations=_observations(identities, one_session),
        adjustment=ths.DailyAdjustment.RAW,
        provider_horizon_reference_date=reference,
    )
    one_first = ths.build_live_request_plan(one_selector, _budget())
    one_second = ths.build_live_request_plan(one_selector, _budget())

    assert one_first == one_second
    assert one_first.planned_calls == 2
    assert one_first.item_count == 2
    assert one_first.estimated_cells == 22
    assert one_first.requested_sessions == ("2026-07-28",)
    assert one_first.remote_executable is False
    assert one_first.transport_mapping_status == "deferred_to_m4_reviewed_mapping"

    ten_sessions = tuple(reference - timedelta(days=offset) for offset in reversed(range(10)))
    ten_selector = ths.AShareDailySelector(
        identities=identities,
        requested_sessions=ten_sessions,
        expected_observations=_observations(identities, ten_sessions),
        adjustment=ths.DailyAdjustment.RAW,
        provider_horizon_reference_date=reference,
    )
    ten_plan = ths.build_live_request_plan(ten_selector, _budget())
    assert len(ten_plan.requested_sessions) == 10
    assert ten_plan.item_count == 20
    assert ten_plan.estimated_cells == 220
    assert len(ten_plan.request_fingerprint) == 64
    assert len(ten_plan.plan_fingerprint) == 64


def test_more_than_ten_daily_sessions_fail_closed() -> None:
    identity = (_equities()[0],)
    reference = date(2026, 7, 28)
    sessions = tuple(reference - timedelta(days=offset) for offset in reversed(range(11)))

    with pytest.raises(ths.LiveSelectorError, match="maximum of 10"):
        ths.AShareDailySelector(
            identities=identity,
            requested_sessions=sessions,
            expected_observations=_observations(identity, sessions),
            adjustment=ths.DailyAdjustment.RAW,
            provider_horizon_reference_date=reference,
        )


def test_rolling_ten_year_boundary_is_exact_and_never_silently_clamped() -> None:
    identity = (_equities()[0],)
    reference = date(2026, 7, 28)
    exact_floor = date(2016, 7, 28)
    accepted = ths.AShareDailySelector(
        identities=identity,
        requested_sessions=(exact_floor,),
        expected_observations=_observations(identity, (exact_floor,)),
        adjustment=ths.DailyAdjustment.RAW,
        provider_horizon_reference_date=reference,
    )
    assert accepted.requested_sessions == (exact_floor,)

    too_old = exact_floor - timedelta(days=1)
    with pytest.raises(ths.LiveSelectorError, match="older than the rolling 10-year"):
        ths.AShareDailySelector(
            identities=identity,
            requested_sessions=(too_old,),
            expected_observations=_observations(identity, (too_old,)),
            adjustment=ths.DailyAdjustment.RAW,
            provider_horizon_reference_date=reference,
        )


def test_selectors_require_sorted_unique_explicit_sessions_and_identities() -> None:
    first, second = _equities()
    reference = date(2026, 7, 28)

    with pytest.raises(ths.LiveSelectorError, match="sorted by identity_key"):
        ths.ListedInstrumentSelector(
            identities=(second, first),
            as_of_date=reference,
            provider_horizon_reference_date=reference,
        )

    with pytest.raises(ths.LiveSelectorError, match="sorted and unique"):
        ths.TradingCalendarSelector(
            exchange=ths.Exchange.SSE,
            requested_dates=(reference, reference),
            provider_horizon_reference_date=reference,
        )


def test_expected_observation_scope_is_explicit_and_cannot_infer_missing_identity_or_session() -> None:
    identities = _equities()
    sessions = (date(2026, 7, 27), date(2026, 7, 28))

    with pytest.raises(ths.LiveSelectorError, match="every requested session"):
        ths.AShareDailySelector(
            identities=identities,
            requested_sessions=sessions,
            expected_observations=tuple(
                ths.ExpectedObservation(identity.identity_key, sessions[0])
                for identity in identities
            ),
            adjustment=ths.DailyAdjustment.RAW,
            provider_horizon_reference_date=sessions[-1],
        )

    unknown = ths.ExpectedObservation("SSE:999999:SYNTH.SSE.UNKNOWN", sessions[0])
    with pytest.raises(ths.LiveSelectorError, match="unknown identities"):
        ths.AShareDailySelector(
            identities=identities,
            requested_sessions=sessions,
            expected_observations=tuple(
                sorted(
                    (*_observations(identities, sessions), unknown),
                    key=lambda item: (item.trade_date, item.identity_key),
                )
            ),
            adjustment=ths.DailyAdjustment.RAW,
            provider_horizon_reference_date=sessions[-1],
        )


def test_quota_budget_is_explicit_and_fails_closed_for_calls_cells_or_qps() -> None:
    identities = _equities()
    sessions = (date(2026, 7, 28),)
    selector = ths.AShareDailySelector(
        identities=identities,
        requested_sessions=sessions,
        expected_observations=_observations(identities, sessions),
        adjustment=ths.DailyAdjustment.RAW,
        provider_horizon_reference_date=sessions[-1],
    )

    with pytest.raises(ths.RequestPlanningError) as call_error:
        ths.build_live_request_plan(selector, _budget(calls=1))
    assert call_error.value.reason_code is ths.RequestPlanningFailureCode.CALL_BUDGET_EXCEEDED

    with pytest.raises(ths.RequestPlanningError) as cell_error:
        ths.build_live_request_plan(selector, _budget(cells=21))
    assert cell_error.value.reason_code is ths.RequestPlanningFailureCode.CELL_BUDGET_EXCEEDED

    with pytest.raises(ths.RequestPlanningError) as qps_error:
        ths.AcquisitionQuotaBudget(
            budget_revision_id="synthetic-budget",
            remaining_calls=10,
            remaining_cells=1000,
            per_function_qps=11,
            account_total_qps=20,
        ).assert_compatible(ths.DEFAULT_LIVE_SOURCE_POLICY)
    assert qps_error.value.reason_code is ths.RequestPlanningFailureCode.QPS_BUDGET_INVALID


def test_request_plan_has_no_arbitrary_transport_or_secret_surface() -> None:
    selector = ths.TradingCalendarSelector(
        exchange=ths.Exchange.SSE,
        requested_dates=(date(2026, 7, 27), date(2026, 7, 28)),
        provider_horizon_reference_date=date(2026, 7, 28),
    )
    summary = dict(ths.build_live_request_plan(selector, _budget()).public_summary())
    serialized = json.dumps(summary, ensure_ascii=False, sort_keys=True).lower()

    assert "https_host" not in summary
    assert "path" not in summary
    assert "headers" not in summary
    assert "query" not in summary
    for forbidden in (
        "api_key",
        "apikey",
        "password",
        "secret",
        "access_token",
        "refresh_token",
        "credential_value",
    ):
        assert forbidden not in serialized


def test_historical_block_plan_is_validation_only_and_remote_disabled() -> None:
    selector = ths.HistoricalBlockSnapshotSelector(
        taxonomy=ths.BlockTaxonomy.INDUSTRY,
        block_id="SYNTH.INDUSTRY.A",
        snapshot_date=date(2026, 7, 28),
        expected_member_count=12,
        provider_horizon_reference_date=date(2026, 7, 28),
    )
    plan = ths.build_live_request_plan(selector, _budget())
    contract = ths.CAPABILITY_PLANNING_REGISTRY[
        ths.DailyMarketCapability.HISTORICAL_BLOCK_SNAPSHOT
    ]

    assert contract.persistence_owner == "none_validation_only"
    assert contract.response_schema_version == "unavailable_until_exact_taxonomy_schema_review"
    assert plan.remote_executable is False


def test_m2_modules_have_no_network_secret_or_environment_lookup() -> None:
    source = inspect.getsource(live_selectors) + inspect.getsource(live_planner)
    for forbidden in (
        "import requests",
        "import httpx",
        "import socket",
        "import subprocess",
        "urllib.request",
        "os.environ",
        "getenv(",
    ):
        assert forbidden not in source
