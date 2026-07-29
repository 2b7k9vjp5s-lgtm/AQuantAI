from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import inspect
import json

import pytest

from backend.database.models import (
    BenchmarkIndexDailyRecord,
    DailyPriceRecord,
    IngestionRun,
    StockBasicRecord,
    TradeCalendarRecord,
)
from datasource import ths_structured_provider as ths
from datasource.ths_structured_provider import credentials, live_contracts, transport


def test_live_source_policy_is_exact_secret_free_and_disabled_by_default() -> None:
    policy = ths.DEFAULT_LIVE_SOURCE_POLICY

    assert policy.source_key == "ths-account-structured-provider-v1"
    assert policy.authorized_https_hosts == (
        "quantapi.51ifind.com",
        "ft.10jqka.com.cn",
    )
    assert policy.authentication_reference_type == "runtime_credential_reference"
    assert policy.per_function_qps == 10
    assert policy.account_total_qps == 20
    assert policy.historical_query_years == 10
    assert policy.private_local_retention == "indefinite_for_project_use"
    assert policy.public_fixture_policy == "synthetic_only"
    assert policy.remote_execution_default is False
    assert policy.runtime_provider_fallback is False
    assert policy.cross_provider_row_mixing is False
    assert len(policy.policy_fingerprint) == 64

    serialized = json.dumps(policy.fingerprint_payload(), ensure_ascii=False, sort_keys=True)
    lowered = serialized.lower()
    for forbidden in ("api_key", "apikey", "password", "secret", "access_token", "refresh_token"):
        assert forbidden not in lowered


def test_live_source_policy_rejects_runtime_contract_overrides() -> None:
    with pytest.raises(ValueError, match="exact reviewed Slice A v1 profile"):
        ths.LiveDailyMarketSourcePolicy(remote_execution_default=True)

    with pytest.raises(ValueError, match="exact reviewed Slice A v1 profile"):
        ths.LiveDailyMarketSourcePolicy(historical_query_years=11)

    with pytest.raises(ValueError, match="exact reviewed Slice A v1 profile"):
        ths.LiveDailyMarketSourcePolicy(
            authorized_https_hosts=("unreviewed.example",)
        )


def test_host_and_capability_selection_are_closed() -> None:
    policy = ths.DEFAULT_LIVE_SOURCE_POLICY

    assert policy.assert_authorized_host(" QUANTAPI.51IFIND.COM ") == "quantapi.51ifind.com"
    assert policy.assert_authorized_host("ft.10jqka.com.cn") == "ft.10jqka.com.cn"
    with pytest.raises(ValueError, match="outside the reviewed"):
        policy.assert_authorized_host("example.com")

    capability = ths.DailyMarketCapability.A_SHARE_DAILY_RAW
    assert policy.assert_capability(capability) is capability
    with pytest.raises(TypeError, match="DailyMarketCapability"):
        policy.assert_capability("a_share_daily_raw")  # type: ignore[arg-type]


def test_readiness_distinguishes_public_evidence_owner_assumptions_and_fail_closed_facts() -> None:
    facts = ths.LIVE_READINESS_BY_KEY

    assert facts["quota_and_qps"].evidence_basis is ths.EvidenceBasis.PROVIDER_PUBLIC_DOCUMENTATION
    assert facts["quota_and_qps"].disposition is ths.ReadinessDisposition.CONFIRMED

    assert (
        facts["private_local_retention"].evidence_basis
        is ths.EvidenceBasis.PROJECT_OWNER_PROVISIONAL_ASSUMPTION
    )
    assert facts["private_local_retention"].disposition is ths.ReadinessDisposition.PROVISIONAL

    assert facts["historical_taxonomy_date"].evidence_basis is ths.EvidenceBasis.FAIL_CLOSED_AT_REQUEST
    assert (
        facts["historical_taxonomy_date"].disposition
        is ths.ReadinessDisposition.VALIDATE_PER_REQUEST
    )

    assert facts["remote_execution"].disposition is ths.ReadinessDisposition.DISABLED
    assert tuple(sorted(facts)) == tuple(fact.fact_key for fact in ths.LIVE_READINESS_FACTS)
    assert len(ths.readiness_fingerprint()) == 64


def test_public_contract_snapshot_is_deterministic_and_top_level_immutable() -> None:
    first = ths.public_contract_snapshot()
    second = ths.public_contract_snapshot()

    assert dict(first) == dict(second)
    assert first["source_policy_fingerprint"] == ths.DEFAULT_LIVE_SOURCE_POLICY.policy_fingerprint
    assert first["readiness_fingerprint"] == ths.readiness_fingerprint()
    assert first["required_capabilities"] == tuple(
        capability.value for capability in ths.FOUNDATION_REQUIRED_CAPABILITIES
    )
    with pytest.raises(TypeError):
        first["source_policy_fingerprint"] = "changed"  # type: ignore[index]


def test_slice_a_schema_audit_is_reachable_without_model_or_migration_changes() -> None:
    ingestion_columns = set(IngestionRun.__table__.columns.keys())
    assert {
        "batch_identifier",
        "series_key",
        "series_identity",
        "provider",
        "dataset",
        "requested_start_date",
        "requested_end_date",
        "information_cutoff_date",
        "requested_scope",
        "provider_request_metadata",
        "adapter_version",
        "contract_version",
        "status",
        "completed_at",
    } <= ingestion_columns

    assert {"source", "stock_code", "exchange", "listing_date"} <= set(
        StockBasicRecord.__table__.columns.keys()
    )
    assert {
        "source",
        "stock_code",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "adjust_type",
        "ingestion_run_id",
    } <= set(DailyPriceRecord.__table__.columns.keys())
    assert {"source", "trade_date", "is_open", "ingestion_run_id"} <= set(
        TradeCalendarRecord.__table__.columns.keys()
    )
    assert {
        "source",
        "index_code",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "ingestion_run_id",
    } <= set(BenchmarkIndexDailyRecord.__table__.columns.keys())


def test_initial_live_contract_increment_has_no_network_or_secret_lookup_imports() -> None:
    source = inspect.getsource(live_contracts)

    for forbidden_import in (
        "import requests",
        "import httpx",
        "import socket",
        "import subprocess",
        "urllib.request",
    ):
        assert forbidden_import not in source

    assert "os.environ" not in source
    assert "getenv(" not in source


def _transport_plan() -> ths.DailyMarketRequestPlan:
    selector = ths.TradingCalendarSelector(
        exchange=ths.Exchange.SSE,
        requested_dates=(date(2026, 7, 28), date(2026, 7, 29)),
        provider_horizon_reference_date=date(2026, 7, 29),
    )
    budget = ths.AcquisitionQuotaBudget(
        budget_revision_id="synthetic-transport-budget-v1",
        remaining_calls=10,
        remaining_cells=10_000,
        per_function_qps=10,
        account_total_qps=20,
    )
    return ths.build_live_request_plan(selector, budget)


class _Resolver:
    def __init__(self, resolved: ths.ResolvedCredential | None) -> None:
        self.resolved = resolved
        self.calls = 0

    def resolve(self, reference: ths.CredentialReference) -> ths.ResolvedCredential | None:
        self.calls += 1
        assert reference.reference_id == "ths-primary-runtime-slot"
        return self.resolved


class _Executor:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0
        self.credential_values: list[str] = []
        self.requests: list[ths.TransportOperationRequest] = []

    def execute(
        self,
        request: ths.TransportOperationRequest,
        *,
        credential_value: str,
    ) -> dict[str, object]:
        self.calls += 1
        self.requests.append(request)
        self.credential_values.append(credential_value)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        assert isinstance(outcome, dict)
        return outcome


def test_credential_reference_and_resolved_value_are_secret_free_by_default() -> None:
    reference = ths.CredentialReference("ths-primary-runtime-slot")
    resolved = ths.ResolvedCredential(
        "SYNTHETIC-SECRET-THAT-MUST-NOT-LEAK",
        expires_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
    )

    assert len(reference.reference_fingerprint) == 64
    assert "SYNTHETIC-SECRET" not in repr(resolved)
    assert "SYNTHETIC-SECRET" not in str(resolved)
    assert "SYNTHETIC-SECRET" not in json.dumps(resolved.safe_metadata())
    assert "credential_value" not in json.dumps(reference.fingerprint_payload())


def test_transport_is_disabled_before_resolver_or_executor_is_touched() -> None:
    resolver = _Resolver(ths.ResolvedCredential("SYNTHETIC-TOKEN"))
    executor = _Executor([{"status": "ok"}])
    client = ths.ThsDailyMarketTransport(
        credential_resolver=resolver,
        executor=executor,
    )

    with pytest.raises(ths.TransportExecutionError) as error:
        client.execute(
            _transport_plan(),
            ths.CredentialReference("ths-primary-runtime-slot"),
            now=datetime(2026, 7, 29, tzinfo=timezone.utc),
        )

    assert error.value.reason_code is ths.TransportFailureCode.REMOTE_EXECUTION_DISABLED
    assert resolver.calls == 0
    assert executor.calls == 0


def test_enabled_transport_uses_injected_credential_without_public_leakage() -> None:
    secret = "SYNTHETIC-TOKEN-VALUE"
    resolver = _Resolver(
        ths.ResolvedCredential(
            secret,
            expires_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
        )
    )
    executor = _Executor([{"schema_version": "synthetic", "data": []}])
    client = ths.ThsDailyMarketTransport(
        credential_resolver=resolver,
        executor=executor,
        config=ths.TransportExecutionConfig(enabled=True),
    )

    result = client.execute(
        _transport_plan(),
        ths.CredentialReference("ths-primary-runtime-slot"),
        now=datetime(2026, 7, 29, tzinfo=timezone.utc),
    )

    assert result.attempts == 1
    assert resolver.calls == 1
    assert executor.calls == 1
    assert executor.credential_values == [secret]
    assert executor.requests[0].host == "quantapi.51ifind.com"
    summary = json.dumps(dict(result.public_summary()), sort_keys=True)
    assert secret not in summary
    assert "credential_reference_fingerprint" in summary


def test_missing_or_expired_credentials_fail_with_sanitized_reason() -> None:
    reference = ths.CredentialReference("ths-primary-runtime-slot")
    executor = _Executor([{"status": "unused"}])

    missing = ths.ThsDailyMarketTransport(
        credential_resolver=_Resolver(None),
        executor=executor,
        config=ths.TransportExecutionConfig(enabled=True),
    )
    with pytest.raises(ths.TransportExecutionError) as missing_error:
        missing.execute(
            _transport_plan(),
            reference,
            now=datetime(2026, 7, 29, tzinfo=timezone.utc),
        )
    assert missing_error.value.reason_code is ths.TransportFailureCode.CREDENTIAL_UNAVAILABLE

    expired = ths.ThsDailyMarketTransport(
        credential_resolver=_Resolver(
            ths.ResolvedCredential(
                "SYNTHETIC-EXPIRED",
                expires_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
            )
        ),
        executor=executor,
        config=ths.TransportExecutionConfig(enabled=True),
    )
    with pytest.raises(ths.TransportExecutionError) as expired_error:
        expired.execute(
            _transport_plan(),
            reference,
            now=datetime(2026, 7, 29, tzinfo=timezone.utc),
        )
    assert expired_error.value.reason_code is ths.TransportFailureCode.CREDENTIAL_UNAVAILABLE
    assert executor.calls == 0


def test_transport_retry_is_bounded_and_auth_or_rate_limit_never_retries() -> None:
    now = datetime(2026, 7, 29, tzinfo=timezone.utc)
    reference = ths.CredentialReference("ths-primary-runtime-slot")
    resolver = _Resolver(
        ths.ResolvedCredential("SYNTHETIC-TOKEN", expires_at=now + timedelta(days=1))
    )
    sleeps: list[float] = []
    executor = _Executor(
        [ths.ExecutorTimeoutError("synthetic timeout"), {"status": "ok"}]
    )
    client = ths.ThsDailyMarketTransport(
        credential_resolver=resolver,
        executor=executor,
        config=ths.TransportExecutionConfig(
            enabled=True,
            max_attempts=2,
            retry_delay_seconds=0.25,
        ),
        sleep=sleeps.append,
    )
    result = client.execute(_transport_plan(), reference, now=now)
    assert result.attempts == 2
    assert executor.calls == 2
    assert sleeps == [0.25]

    for failure, reason in (
        (ths.ExecutorAuthenticationError("synthetic auth"), ths.TransportFailureCode.AUTHENTICATION_FAILED),
        (ths.ExecutorRateLimitError("synthetic quota"), ths.TransportFailureCode.RATE_LIMITED),
    ):
        no_retry_executor = _Executor([failure, {"status": "must-not-run"}])
        no_retry = ths.ThsDailyMarketTransport(
            credential_resolver=resolver,
            executor=no_retry_executor,
            config=ths.TransportExecutionConfig(enabled=True, max_attempts=3),
        )
        with pytest.raises(ths.TransportExecutionError) as error:
            no_retry.execute(_transport_plan(), reference, now=now)
        assert error.value.reason_code is reason
        assert no_retry_executor.calls == 1


def test_transport_rejects_unreviewed_host_and_unsupported_block_operation() -> None:
    plan = _transport_plan()
    reference = ths.CredentialReference("ths-primary-runtime-slot")
    with pytest.raises(ths.TransportExecutionError) as host_error:
        ths.build_transport_request(
            plan,
            reference,
            ths.TransportExecutionConfig(enabled=True, host="ft.10jqka.com.cn"),
        )
    assert host_error.value.reason_code is ths.TransportFailureCode.HOST_NOT_AUTHORIZED

    block_selector = ths.HistoricalBlockSnapshotSelector(
        taxonomy=ths.BlockTaxonomy.INDUSTRY,
        block_id="SYNTH.INDUSTRY.A",
        snapshot_date=date(2026, 7, 29),
        expected_member_count=2,
        provider_horizon_reference_date=date(2026, 7, 29),
    )
    budget = ths.AcquisitionQuotaBudget(
        budget_revision_id="synthetic-block-budget",
        remaining_calls=10,
        remaining_cells=100,
        per_function_qps=10,
        account_total_qps=20,
    )
    with pytest.raises(ths.TransportExecutionError) as block_error:
        ths.build_transport_request(
            ths.build_live_request_plan(block_selector, budget),
            reference,
            ths.TransportExecutionConfig(enabled=True),
        )
    assert block_error.value.reason_code is ths.TransportFailureCode.OPERATION_NOT_AUTHORIZED


def test_m4_modules_have_no_network_client_or_environment_lookup() -> None:
    source = inspect.getsource(credentials) + inspect.getsource(transport)
    for forbidden in (
        "import requests",
        "import httpx",
        "import socket",
        "urllib.request",
        "os.environ",
        "getenv(",
    ):
        assert forbidden not in source
