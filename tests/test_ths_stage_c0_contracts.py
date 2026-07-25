from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from datetime import datetime
import importlib
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from datasource.ths_structured_provider.contracts import (
    CONTRACT_REGISTRY,
    INDEX_DAILY_HISTORY_CONTRACT,
    INDEX_HISTORY_CAPABILITY,
    get_contract,
)
from datasource.ths_structured_provider.fingerprint import canonical_json_bytes, canonical_sha256
from datasource.ths_structured_provider.planner import build_index_history_plan
from datasource.ths_structured_provider.readiness import (
    BLOCKED_REASON_MESSAGES_ZH,
    BlockedReasonCode,
    CapabilityReadiness,
    ReadinessStatus,
)
from datasource.ths_structured_provider.redaction import (
    REDACTED,
    assert_safe_display_url,
    redact_mapping,
    redact_text,
)
from datasource.ths_structured_provider.schemas import (
    SchemaValidationError,
    index_history_schema_fingerprint,
    load_synthetic_fixture,
    strip_synthetic_fixture_marker,
    validate_error_envelope,
    validate_index_history_envelope,
)
from datasource.ths_structured_provider.selectors import IndexHistorySelector, SelectorValidationError

ROOT = Path(__file__).parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "ths_stage_c0"
PACKAGE_ROOT = ROOT / "datasource" / "ths_structured_provider"
FORBIDDEN_MODULE_PREFIXES = (
    "requests",
    "httpx",
    "urllib.request",
    "socket",
    "subprocess",
    "sqlalchemy",
    "fastapi",
    "os",
    "sqlite3",
    "psycopg",
)


def test_index_history_contract_is_frozen_exact_and_registry_closed() -> None:
    contract = get_contract(INDEX_HISTORY_CAPABILITY)
    assert contract is INDEX_DAILY_HISTORY_CONTRACT
    assert contract.https_host == "fuyao.aicubes.cn"
    assert contract.http_method == "GET"
    assert contract.path_template == "/api/a-share-index/prices/historical"
    assert contract.ordered_query_fields == ("thscode", "interval", "start", "end")
    assert dict(contract.public_limit_contract)["maximum_window_years"] == "10"
    assert len(contract.contract_fingerprint) == 64
    with pytest.raises(FrozenInstanceError):
        contract.https_host = "example.invalid"  # type: ignore[misc]
    with pytest.raises(TypeError):
        CONTRACT_REGISTRY["other"] = INDEX_DAILY_HISTORY_CONTRACT  # type: ignore[index]
    with pytest.raises(KeyError, match="Unsupported THS Stage C0 capability"):
        get_contract("unknown_capability")


def test_default_readiness_fails_closed_and_optional_gates_are_scoped() -> None:
    readiness = CapabilityReadiness()
    assert readiness.blocked_reason_codes() == (
        BlockedReasonCode.QUOTA_CONTRACT_UNRESOLVED,
        BlockedReasonCode.COMPLETION_CONTRACT_UNRESOLVED,
        BlockedReasonCode.REVISION_CONTRACT_UNRESOLVED,
        BlockedReasonCode.KEY_LIFECYCLE_UNRESOLVED,
    )
    assert readiness.live_readiness_candidate == "blocked"
    assert readiness.blocked_messages_zh()[0] == "数据源额度或调用规则尚未确认"
    assert readiness.blocked_reason_codes(require_historical_membership=True)[-1] is BlockedReasonCode.HISTORICAL_MEMBERSHIP_UNSUPPORTED
    assert readiness.blocked_reason_codes(require_corporate_action=True)[-1] is BlockedReasonCode.CORPORATE_ACTION_NOT_VALIDATED
    assert set(BLOCKED_REASON_MESSAGES_ZH) == set(BlockedReasonCode)


def test_readiness_distinguishes_entitlement_and_validates_evidence_fingerprints() -> None:
    not_entitled = CapabilityReadiness(entitlement_status=ReadinessStatus.NOT_ENTITLED)
    assert BlockedReasonCode.CAPABILITY_NOT_ENTITLED in not_entitled.blocked_reason_codes()
    unsupported = CapabilityReadiness(entitlement_status=ReadinessStatus.UNSUPPORTED)
    assert BlockedReasonCode.CAPABILITY_UNSUPPORTED in unsupported.blocked_reason_codes()
    assert CapabilityReadiness(reviewed_evidence_fingerprints=("a" * 64,)).reviewed_evidence_fingerprints == ("a" * 64,)
    with pytest.raises(ValueError, match="SHA-256"):
        CapabilityReadiness(reviewed_evidence_fingerprints=("not-a-fingerprint",))


def test_golden_path_plan_is_deterministic_and_never_executable() -> None:
    selector = IndexHistorySelector("SYNTH.IDX.C0", 1000, 2000)
    readiness = CapabilityReadiness(reviewed_evidence_fingerprints=("b" * 64,))
    first = build_index_history_plan(selector, readiness)
    second = build_index_history_plan(selector, readiness)
    assert first == second
    assert first.ordered_query_items == (
        ("thscode", "SYNTH.IDX.C0"),
        ("interval", "1d"),
        ("start", "1000"),
        ("end", "2000"),
    )
    assert first.synthetic_only is True
    assert first.remote_executable is False
    assert first.live_readiness_candidate == "blocked"
    assert len(first.request_fingerprint) == 64


def test_confirmed_hypothetical_readiness_still_cannot_execute() -> None:
    readiness = CapabilityReadiness(
        quota_status=ReadinessStatus.CONFIRMED,
        completion_status=ReadinessStatus.CONFIRMED,
        revision_status=ReadinessStatus.CONFIRMED,
        credential_lifecycle_status=ReadinessStatus.CONFIRMED,
    )
    plan = build_index_history_plan(IndexHistorySelector("SYNTH.IDX.READY", 1000, 2000), readiness)
    assert plan.live_readiness_candidate == "ready"
    assert plan.blocked_reason_codes == ()
    assert plan.remote_executable is False


def test_selector_and_contract_mutation_fail_closed() -> None:
    with pytest.raises(SelectorValidationError, match="reserved"):
        IndexHistorySelector("000001.SH", 1000, 2000)
    with pytest.raises(SelectorValidationError, match="less than or equal"):
        IndexHistorySelector("SYNTH.IDX.C0", 2000, 1000)
    with pytest.raises(SelectorValidationError, match="integer"):
        IndexHistorySelector("SYNTH.IDX.C0", True, 1000)  # type: ignore[arg-type]
    zone = ZoneInfo("Asia/Shanghai")
    start = int(datetime(2020, 1, 1, tzinfo=zone).timestamp() * 1000)
    too_late = int(datetime(2030, 1, 2, tzinfo=zone).timestamp() * 1000)
    with pytest.raises(SelectorValidationError, match="ten calendar years"):
        IndexHistorySelector("SYNTH.IDX.C0", start, too_late)
    mutated = replace(INDEX_DAILY_HISTORY_CONTRACT, https_host="example.invalid")
    with pytest.raises(ValueError, match="frozen"):
        build_index_history_plan(IndexHistorySelector("SYNTH.IDX.C0", 1000, 2000), CapabilityReadiness(), contract=mutated)


def test_canonical_fingerprints_ignore_mapping_order_but_preserve_list_order() -> None:
    left = {"b": 2, "a": {"y": 2, "x": 1}}
    right = {"a": {"x": 1, "y": 2}, "b": 2}
    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert canonical_sha256(left) == canonical_sha256(right)
    assert canonical_sha256(["a", "b"]) != canonical_sha256(["b", "a"])


def test_redaction_and_safe_display_url() -> None:
    value = {
        "X-api-key": "synthetic-secret",
        "nested": {"request_id": "synthetic-request", "safe": "kept"},
        "rows": [{"account_id": "synthetic-account"}],
    }
    redacted = redact_mapping(value)
    assert redacted["X-api-key"] == REDACTED
    assert redacted["nested"]["request_id"] == REDACTED
    assert redacted["nested"]["safe"] == "kept"
    assert redacted["rows"][0]["account_id"] == REDACTED
    text = redact_text("token=synthetic-token request_id:synthetic-request safe=value")
    assert "synthetic-token" not in text and "synthetic-request" not in text
    assert_safe_display_url("https://fuyao.aicubes.cn/api/path?thscode=SYNTH.IDX.C0")
    with pytest.raises(ValueError, match="user information"):
        assert_safe_display_url("https://user:pass@fuyao.aicubes.cn/api/path")
    with pytest.raises(ValueError, match="sensitive query"):
        assert_safe_display_url("https://fuyao.aicubes.cn/api/path?api_key=synthetic")


def test_synthetic_success_and_error_fixtures_are_strict() -> None:
    success = validate_index_history_envelope(load_synthetic_fixture(FIXTURES / "index_history_success.synthetic.json"))
    assert success.code == 0 and success.request_id is None
    assert [row.date_ms for row in success.data.item] == [1000, 2000]
    assert len(index_history_schema_fingerprint()) == 64
    error = validate_error_envelope(load_synthetic_fixture(FIXTURES / "standard_error.synthetic.json"))
    assert error.code == 987654321 and error.request_id is None and error.data is None


def test_schema_rejects_marker_unknown_fields_wrong_types_and_order() -> None:
    with pytest.raises(SchemaValidationError, match="synthetic marker"):
        strip_synthetic_fixture_marker({"code": 0, "message": "synthetic", "data": None})
    base = load_synthetic_fixture(FIXTURES / "index_history_success.synthetic.json")
    marked = {"_aquantai_fixture_kind": "synthetic", **base}
    with pytest.raises(SchemaValidationError, match="unknown fields"):
        validate_index_history_envelope(marked)

    unknown = load_synthetic_fixture(FIXTURES / "index_history_success.synthetic.json")
    unknown["data"]["item"][0]["unreviewed_field"] = "synthetic"  # type: ignore[index]
    with pytest.raises(SchemaValidationError, match="unknown fields"):
        validate_index_history_envelope(unknown)

    wrong_type = load_synthetic_fixture(FIXTURES / "index_history_success.synthetic.json")
    wrong_type["data"]["item"][0]["date_ms"] = "1000"  # type: ignore[index]
    with pytest.raises(SchemaValidationError, match="must be an integer"):
        validate_index_history_envelope(wrong_type)

    bad_order = load_synthetic_fixture(FIXTURES / "index_history_success.synthetic.json")
    bad_order["data"]["item"].reverse()  # type: ignore[index]
    with pytest.raises(SchemaValidationError, match="strictly ascending"):
        validate_index_history_envelope(bad_order)


def test_production_package_has_no_forbidden_imports() -> None:
    for path in PACKAGE_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                assert not module.startswith(FORBIDDEN_MODULE_PREFIXES), f"{path} imports forbidden module {module}"


def test_import_and_demo_do_not_touch_network_subprocess_or_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    import os
    import socket
    import subprocess
    import urllib.request

    import httpx

    def denied(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("Stage C0 attempted a prohibited side effect")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(httpx.Client, "request", denied)
    monkeypatch.setattr(httpx.AsyncClient, "request", denied)
    monkeypatch.setattr(urllib.request, "urlopen", denied)
    monkeypatch.setattr(subprocess, "run", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    monkeypatch.setattr(os, "getenv", denied)

    module_names = (
        "datasource.ths_structured_provider.fingerprint",
        "datasource.ths_structured_provider.contracts",
        "datasource.ths_structured_provider.readiness",
        "datasource.ths_structured_provider.selectors",
        "datasource.ths_structured_provider.redaction",
        "datasource.ths_structured_provider.schemas",
        "datasource.ths_structured_provider.planner",
    )
    for module_name in module_names:
        importlib.reload(importlib.import_module(module_name))
    package = importlib.reload(importlib.import_module("datasource.ths_structured_provider"))
    plan = package.build_index_history_plan(package.IndexHistorySelector("SYNTH.IDX.C0", 1000, 2000), package.CapabilityReadiness())
    assert plan.remote_executable is False
    demo = importlib.import_module("scripts.demo_ths_stage_c0_offline")
    assert demo.build_demo_summary()["remote_executable"] is False
