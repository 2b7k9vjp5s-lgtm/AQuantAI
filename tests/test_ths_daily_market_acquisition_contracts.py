from __future__ import annotations

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
from datasource.ths_structured_provider import live_contracts


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
