from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
import inspect
import json
from types import SimpleNamespace

import pytest

from backend.today_market_refresh import contracts
from backend.today_market_refresh import port as live_port
from datasource import ths_structured_provider as ths


def _component(
    owner: str,
    run_id: int,
    batch_character: str,
    series_character: str,
    rows: int,
) -> ths.PersistedComponentReceipt:
    return ths.PersistedComponentReceipt(
        owner=owner,
        ingestion_run_id=run_id,
        batch_identifier=batch_character * 64,
        series_key=series_character * 64,
        information_cutoff_date="20260728",
        rows_received=rows,
        rows_written=rows,
        idempotent=False,
    )


def _receipt() -> ths.DailyMarketFoundationReceipt:
    return ths.DailyMarketFoundationReceipt(
        source_key="ths-account-structured-provider-v1",
        acquisition_contract_version=ths.ACQUISITION_CONTRACT_VERSION,
        acquisition_fingerprint=ths.canonical_sha256(
            {"synthetic_acquisition": "handoff-golden-path"}
        ),
        information_cutoff_date="20260728",
        covered_sessions=("2026-07-27", "2026-07-28"),
        stock_codes=("990001", "990002"),
        index_codes=("999950",),
        market=_component(
            "MarketDataPersistenceService",
            101,
            "a",
            "b",
            8,
        ),
        benchmark=_component(
            "BenchmarkPersistenceService",
            102,
            "c",
            "d",
            2,
        ),
    )


def _request(
    receipt: ths.DailyMarketFoundationReceipt,
    *,
    source_key: str | None = None,
    expected_acquisition_fingerprint: str | None = None,
    requested_sessions: tuple[date, ...] = (
        date(2026, 7, 27),
        date(2026, 7, 28),
    ),
) -> live_port.TodayMarketLiveHandoffRequest:
    return live_port.build_live_handoff_request(
        scope_revision_id="today-market-live-scope-v1",
        refresh_attempt_id="today-market-live-attempt-v1",
        trigger=contracts.RefreshTrigger.EXPLICIT_MANUAL_CATCHUP,
        prior_snapshot_id="prior-snapshot-v1",
        requested_sessions=requested_sessions,
        information_cutoff=requested_sessions[-1],
        recorded_at_utc=datetime(2026, 7, 28, 8, 0, tzinfo=timezone.utc),
        source_key=source_key or receipt.source_key,
        source_policy_fingerprint=ths.DEFAULT_LIVE_SOURCE_POLICY.policy_fingerprint,
        expected_acquisition_fingerprint=(
            expected_acquisition_fingerprint or receipt.acquisition_fingerprint
        ),
    )


def test_complete_m5_receipt_projects_to_live_completeness_and_provenance_only() -> None:
    receipt = _receipt()
    request = _request(receipt)

    batch = live_port.project_live_foundation_receipt(
        request,
        receipt,
        observed_at_utc=datetime(2026, 7, 28, 8, 1, tzinfo=timezone.utc),
    )

    assert batch.verify_fingerprint()
    assert batch.refresh_attempt_id == request.refresh_attempt_id
    assert batch.source_attempt_id == receipt.acquisition_fingerprint
    assert batch.source_provenance.source_mode is contracts.SourceMode.SOURCE_SPECIFIC_LIVE
    assert batch.source_provenance.source_key == receipt.source_key
    assert batch.source_provenance.provider_confirmed is False
    assert batch.coverage.status is contracts.CoverageStatus.COMPLETE
    assert batch.coverage.requested_sessions == (
        date(2026, 7, 27),
        date(2026, 7, 28),
    )
    assert tuple(component.component_key for component in batch.components) == (
        live_port.LiveComponentKey.BENCHMARK_INDEX_DAILY,
        live_port.LiveComponentKey.MARKET_DATA_BUNDLE,
    )
    assert {component.ingestion_run_id for component in batch.components} == {101, 102}

    summary = json.dumps(dict(batch.public_summary()), sort_keys=True)
    for forbidden in (
        "stock_codes",
        "index_codes",
        "provider_symbol",
        "credential",
        "token",
        "http",
        "market_state",
        "sector_state",
        "anomaly",
    ):
        assert forbidden not in summary.lower()


def test_live_request_and_batch_fingerprints_are_deterministic() -> None:
    receipt = _receipt()
    first_request = _request(receipt)
    second_request = _request(receipt)
    assert first_request.request_fingerprint == second_request.request_fingerprint
    assert first_request.verify_fingerprint()

    projector = live_port.DeterministicLiveReceiptProjector()
    first = projector.project_live(
        first_request,
        receipt,
        observed_at_utc=datetime(2026, 7, 28, 8, 1, tzinfo=timezone.utc),
    )
    second = projector.project_live(
        second_request,
        receipt,
        observed_at_utc=datetime(2026, 7, 28, 8, 1, tzinfo=timezone.utc),
    )
    assert first.batch_fingerprint == second.batch_fingerprint
    assert first.verify_fingerprint()


def test_wrong_source_acquisition_or_coverage_fails_closed() -> None:
    receipt = _receipt()

    with pytest.raises(live_port.LiveHandoffValidationError) as source_error:
        live_port.project_live_foundation_receipt(
            _request(receipt, source_key="another-live-source"),
            receipt,
            observed_at_utc=datetime(2026, 7, 28, 8, 1, tzinfo=timezone.utc),
        )
    assert source_error.value.reason_code is live_port.LiveHandoffFailureCode.SOURCE_MISMATCH

    with pytest.raises(live_port.LiveHandoffValidationError) as acquisition_error:
        live_port.project_live_foundation_receipt(
            _request(receipt, expected_acquisition_fingerprint="f" * 64),
            receipt,
            observed_at_utc=datetime(2026, 7, 28, 8, 1, tzinfo=timezone.utc),
        )
    assert (
        acquisition_error.value.reason_code
        is live_port.LiveHandoffFailureCode.ACQUISITION_MISMATCH
    )

    shortened_receipt = replace(receipt, covered_sessions=("2026-07-28",))
    with pytest.raises(live_port.LiveHandoffValidationError) as coverage_error:
        live_port.project_live_foundation_receipt(
            _request(receipt),
            shortened_receipt,
            observed_at_utc=datetime(2026, 7, 28, 8, 1, tzinfo=timezone.utc),
        )
    assert coverage_error.value.reason_code is live_port.LiveHandoffFailureCode.COVERAGE_MISMATCH


def test_incomplete_or_wrong_owner_receipt_cannot_be_promoted() -> None:
    receipt = _receipt()
    incomplete = SimpleNamespace(
        source_key=receipt.source_key,
        acquisition_contract_version=receipt.acquisition_contract_version,
        acquisition_fingerprint=receipt.acquisition_fingerprint,
        information_cutoff_date=receipt.information_cutoff_date,
        covered_sessions=receipt.covered_sessions,
        receipt_fingerprint=receipt.receipt_fingerprint,
        market=receipt.market,
    )
    with pytest.raises(live_port.LiveHandoffValidationError) as missing_error:
        live_port.project_live_foundation_receipt(
            _request(receipt),
            incomplete,
            observed_at_utc=datetime(2026, 7, 28, 8, 1, tzinfo=timezone.utc),
        )
    assert missing_error.value.reason_code is live_port.LiveHandoffFailureCode.COMPONENT_MISMATCH

    wrong_owner = replace(
        receipt,
        benchmark=replace(receipt.benchmark, owner="UnknownPersistenceOwner"),
    )
    with pytest.raises(live_port.LiveHandoffValidationError) as owner_error:
        live_port.project_live_foundation_receipt(
            _request(receipt),
            wrong_owner,
            observed_at_utc=datetime(2026, 7, 28, 8, 1, tzinfo=timezone.utc),
        )
    assert owner_error.value.reason_code is live_port.LiveHandoffFailureCode.COMPONENT_MISMATCH


def test_existing_mock_contracts_remain_locked_to_synthetic_values() -> None:
    with pytest.raises(ValueError, match="Mock family results must remain explicitly synthetic"):
        contracts.TodayMarketFamilyResult(
            family_key=contracts.CapabilityFamily.TRADING_CALENDAR,
            schema_version="synthetic-schema-v1",
            requested_sessions=(date(2026, 7, 28),),
            covered_sessions=(date(2026, 7, 28),),
            item_count=1,
            synthetic=False,
            source_key="ths-account-structured-provider-v1",
            content_fingerprint="a" * 64,
            validation_status=contracts.ValidationStatus.VALID,
            reason_codes=(),
            payload={},
        )

    with pytest.raises(ValueError, match="only the reviewed synthetic Mock assumption profile"):
        contracts.TodayMarketRefreshPlan(
            scope_revision_id="scope-v1",
            refresh_attempt_id="attempt-v1",
            trigger=contracts.RefreshTrigger.EXPLICIT_MANUAL_CATCHUP,
            prior_snapshot_id=None,
            requested_completed_sessions=(date(2026, 7, 28),),
            capability_set=(contracts.CapabilityFamily.TRADING_CALENDAR,),
            family_bounds=(("trading_calendar", 1),),
            information_cutoff=date(2026, 7, 28),
            recorded_at_utc=datetime(2026, 7, 28, tzinfo=timezone.utc),
            planning_policy_version=contracts.PLANNING_POLICY_VERSION,
            assumption_profile_id="live-profile-must-not-enter-mock-plan",
            plan_fingerprint="a" * 64,
        )


def test_mock_and_live_ports_remain_separate_protocols() -> None:
    class ExistingMockAdapter:
        def acquire(self, plan):
            raise NotImplementedError

    live_projector = live_port.DeterministicLiveReceiptProjector()
    assert isinstance(ExistingMockAdapter(), live_port.TodayMarketAcquisitionPort)
    assert not isinstance(ExistingMockAdapter(), live_port.TodayMarketLiveAcquisitionPort)
    assert isinstance(live_projector, live_port.TodayMarketLiveAcquisitionPort)
    assert not isinstance(live_projector, live_port.TodayMarketAcquisitionPort)


def test_live_failure_projection_is_typed_and_rejects_sensitive_diagnostics() -> None:
    failure = live_port.project_live_acquisition_failure(
        failure_code="THS_ACQUISITION_BENCHMARK_PERSISTENCE_FAILED",
        category=contracts.FailureCategory.INTERNAL_VALIDATION_FAILED,
        refresh_attempt_id="attempt-v1",
        source_key="ths-account-structured-provider-v1",
        redacted_details=("benchmark component incomplete; prior history retained",),
        retryability=contracts.Retryability.EXPLICIT_USER_RETRY,
    )
    assert failure.category is contracts.FailureCategory.INTERNAL_VALIDATION_FAILED
    assert failure.retryability is contracts.Retryability.EXPLICIT_USER_RETRY

    with pytest.raises(live_port.LiveHandoffValidationError) as error:
        live_port.project_live_acquisition_failure(
            failure_code="THS_TRANSPORT_AUTHENTICATION_FAILED",
            category=contracts.FailureCategory.SOURCE_UNAVAILABLE,
            refresh_attempt_id="attempt-v1",
            source_key="ths-account-structured-provider-v1",
            redacted_details=("token value leaked",),
            retryability=contracts.Retryability.EXPLICIT_USER_RETRY,
        )
    assert error.value.reason_code is live_port.LiveHandoffFailureCode.SENSITIVE_DIAGNOSTIC


def test_m6_port_has_no_network_persistence_runtime_or_market_truth_path() -> None:
    source = inspect.getsource(live_port)
    for forbidden in (
        "import requests",
        "import httpx",
        "urllib.request",
        "from .runtime",
        "MarketDataPersistenceService",
        "BenchmarkPersistenceService",
        "market_state",
        "sector_state",
        "hotspot",
        "anomaly",
    ):
        assert forbidden not in source
