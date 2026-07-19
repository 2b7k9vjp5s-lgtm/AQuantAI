from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from datasource.hithink.probe import (
    API_KEY_ENV,
    HttpResponse,
    ProbeConfigurationError,
    ProbeOptions,
    report_json,
    run_contract_probe,
)
from scripts.probe_hithink_contracts import main


REPRESENTATIVES = ("600000.SH", "000001.SZ", "430001.BJ")
SECRET = "never-print-this-key"


def _options(**overrides: object) -> ProbeOptions:
    values: dict[str, object] = {
        "mode": "offline",
        "representatives": REPRESENTATIVES,
        "start_date": "2026-07-01",
        "end_date": "2026-07-10",
    }
    values.update(overrides)
    return ProbeOptions(**values)


def _manifest() -> dict[str, object]:
    return {
        "dump_id": "a_share_daily_k_1d_none_10d",
        "version": "20260710.1",
        "mode": "RECENT_TRADING_DAYS",
        "coverage_start": "2026-06-27",
        "coverage_end": "2026-07-10",
        "row_count": 30,
        "ticker_count": 3,
        "failed_tickers": [],
        "file_name": "daily-k-10d.parquet",
        "sha256": "a" * 64,
        "schema": sorted(
            [
                "thscode",
                "currency",
                "interval",
                "adjusted",
                "date_ms",
                "open_price",
                "high_price",
                "low_price",
                "close_price",
                "volume",
                "turnover",
            ]
        ),
    }


def _rights() -> dict[str, object]:
    return {
        "enabled_capabilities": True,
        "quotas_and_qps": True,
        "local_long_term_storage": True,
        "caching_and_transformation": True,
        "local_display": True,
        "redistribution_and_deployment": False,
        "retention_and_deletion": True,
        "dump_reproducibility": True,
        "free_text": SECRET,
        "account_id": SECRET,
    }


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class FakeTransport:
    def __init__(self, responses: list[HttpResponse] | None = None) -> None:
        self.responses = list(responses or [])
        self.calls: list[tuple[str, dict[str, object], float]] = []

    def get(self, path, params, *, api_key, timeout):
        assert api_key == SECRET
        self.calls.append((path, dict(params), timeout))
        if self.responses:
            return self.responses.pop(0)
        return _live_response(path, params)


def _envelope(data: object, *, code: int = 0, request_id: str = "safe-request") -> HttpResponse:
    return HttpResponse(
        200,
        {"code": code, "message": SECRET, "request_id": request_id, "data": data},
    )


def _live_response(path: str, params: dict[str, object]) -> HttpResponse:
    if path.endswith("tickers/list"):
        return _envelope(
            {
                "timestamp": 1783900800000,
                "item": [
                    {
                        "thscode": symbol,
                        "ticker": symbol[:6],
                        "name": SECRET,
                        "exchange": symbol[-2:],
                        "asset_type": "a-share",
                        "currency": "CNY",
                    }
                    for symbol in REPRESENTATIVES
                ]
            }
        )
    if path.endswith("trading-days"):
        return _envelope(
            {
                "timestamp": 1783900800000,
                "item": [{"date_ms": 1783900800000, "date": "20260713"}],
            }
        )
    if path.endswith("historical"):
        assert params["adjust"] == "none"
        return _envelope(
            {
                "timestamp": 1783900800000,
                "item": [
                    {
                        "date_ms": 1783900800000,
                        "open_price": 1.0,
                        "high_price": 2.0,
                        "low_price": 0.5,
                        "close_price": 1.5,
                        "volume": 10.0,
                        "turnover": 15.0,
                    }
                ]
            }
        )
    return _envelope({"url": f"https://example.invalid/dump?key={SECRET}"})


def test_mode_gate_is_explicit_and_cli_modes_are_mutually_exclusive() -> None:
    with pytest.raises(ProbeConfigurationError, match="execution mode"):
        run_contract_probe(_options(mode="invalid"))
    with pytest.raises(SystemExit):
        main(
            [
                "--allow-network",
                "--offline-contract",
                "--representative",
                REPRESENTATIVES[0],
                "--representative",
                REPRESENTATIVES[1],
                "--representative",
                REPRESENTATIVES[2],
                "--start-date",
                "2026-07-01",
                "--end-date",
                "2026-07-10",
            ]
        )


def test_offline_mode_does_not_read_key_or_construct_transport() -> None:
    def fail_env(_name: str) -> str | None:
        raise AssertionError("environment must not be read")

    def fail_transport():
        raise AssertionError("transport must not be constructed")

    report = run_contract_probe(
        _options(), env_getter=fail_env, transport_factory=fail_transport
    )
    assert report["overall_status"] == "blocked"
    assert len(report["endpoints"]) == 6


def test_missing_live_key_fails_before_transport_construction() -> None:
    constructed = False

    def factory():
        nonlocal constructed
        constructed = True
        return FakeTransport()

    with pytest.raises(ProbeConfigurationError, match="not configured"):
        run_contract_probe(
            _options(mode="live"), env_getter=lambda _name: None, transport_factory=factory
        )
    assert not constructed


@pytest.mark.parametrize(
    "representatives",
    [
        ("600000", "000001.SZ", "430001.BJ"),
        ("600000.SH", "600000.SH", "430001.BJ"),
        ("600000.SH", "000001.SZ", "430001.SZ"),
        ("600000.sh", "000001.SZ", "430001.BJ"),
    ],
)
def test_representatives_fail_before_key_or_transport(representatives) -> None:
    touched = False

    def env(_name: str) -> str:
        nonlocal touched
        touched = True
        return SECRET

    with pytest.raises(ProbeConfigurationError):
        run_contract_probe(_options(mode="live", representatives=representatives), env_getter=env)
    assert not touched


def test_live_requests_are_bounded_and_dump_is_not_downloaded(tmp_path: Path) -> None:
    manifest = _write_json(tmp_path / "manifest.json", _manifest())
    rights = _write_json(tmp_path / "rights.json", _rights())
    transport = FakeTransport()
    report = run_contract_probe(
        _options(mode="live", manifest_path=manifest, rights_path=rights),
        env_getter=lambda name: SECRET if name == API_KEY_ENV else None,
        transport_factory=lambda: transport,
    )

    assert report["overall_status"] == "accepted"
    assert len(transport.calls) == 6
    assert transport.calls[0][0:2] == (
        "/api/meta/tickers/list",
        {"asset_type": "a-share", "limit": 100, "offset": 0},
    )
    assert transport.calls[1][0:2] == (
        "/api/a-share/calendar/trading-days",
        {},
    )
    assert [call[0] for call in transport.calls].count(
        "/api/a-share/prices/historical"
    ) == 3
    for call, symbol in zip(transport.calls[2:5], REPRESENTATIVES, strict=True):
        assert call[0] == "/api/a-share/prices/historical"
        assert call[1]["thscode"] == symbol
        assert call[1]["interval"] == "1d"
        assert call[1]["adjust"] == "none"
        assert set(call[1]) == {"adjust", "end", "interval", "start", "thscode"}
    assert transport.calls[-1][0:2] == (
        "/dump/market-dumps/daily-k-10d/download-url",
        {},
    )
    assert all(call[2] == 10.0 for call in transport.calls)
    rendered = report_json(report)
    assert "example.invalid" not in rendered
    assert SECRET not in rendered


@pytest.mark.parametrize(
    "code,category",
    [
        (1001, "validation"),
        (2001, "authentication"),
        (2003, "permission"),
        (3001, "absence_or_data_state"),
        (4001, "rate_limit"),
        (5002, "timeout"),
        (5003, "upstream_unavailable"),
        (9999, "unknown"),
    ],
)
def test_http_success_with_business_error_is_classified(code, category) -> None:
    transport = FakeTransport([_envelope(None, code=code)])
    report = run_contract_probe(
        _options(mode="live"),
        env_getter=lambda _name: SECRET,
        transport_factory=lambda: transport,
    )
    ticker = next(item for item in report["endpoints"] if item["endpoint_id"] == "ticker_list")
    assert ticker["status"] == "blocked"
    assert ticker["business_category"] == category


@pytest.mark.parametrize(
    "path,bad_data,endpoint_id",
    [
        (
            "ticker",
            {"timestamp": 1783900800000, "item": [{"thscode": "600000.SH"}]},
            "ticker_list",
        ),
        (
            "calendar",
            {"timestamp": 1783900800000, "item": [{"date_ms": True, "date": "20260713"}]},
            "trading_calendar",
        ),
        (
            "bar",
            {
                "timestamp": 1783900800000,
                "item": [{"date_ms": 1, "open_price": float("inf")}],
            },
            "historical_bar_SH",
        ),
    ],
)
def test_field_and_type_contracts_fail_closed(path, bad_data, endpoint_id) -> None:
    responses = [_live_response("/api/meta/tickers/list", {})]
    if path == "ticker":
        responses[0] = _envelope(bad_data)
    responses.append(_live_response("/api/a-share/calendar/trading-days", {}))
    if path == "calendar":
        responses[1] = _envelope(bad_data)
    responses.extend(
        [_live_response("/api/a-share/prices/historical", {"adjust": "none"}) for _ in range(3)]
    )
    if path == "bar":
        responses[2] = _envelope(bad_data)
    responses.append(_live_response("/dump/market-dumps/daily-k-10d/download-url", {}))
    report = run_contract_probe(
        _options(mode="live"),
        env_getter=lambda _name: SECRET,
        transport_factory=lambda: FakeTransport(responses),
    )
    endpoint = next(item for item in report["endpoints"] if item["endpoint_id"] == endpoint_id)
    assert endpoint["business_category"] == "contract_invalid"
    assert endpoint["status"] == "blocked"


def test_manifest_without_checksum_or_schema_blocks_dump(tmp_path: Path) -> None:
    incomplete = _manifest()
    incomplete.pop("sha256")
    incomplete.pop("schema")
    path = _write_json(tmp_path / "manifest.json", incomplete)
    report = run_contract_probe(_options(manifest_path=path))
    dump = next(item for item in report["endpoints"] if item["endpoint_id"] == "dump_link")
    assert report["manifest_evidence_complete"] is False
    assert dump["dump_https_link_present"] is True
    assert dump["status"] == "blocked"
    assert dump["business_category"] == "local_manifest_incomplete"


def test_rights_are_summarized_without_free_text_or_identifiers(tmp_path: Path) -> None:
    path = _write_json(tmp_path / "rights.json", _rights())
    report = run_contract_probe(_options(rights_path=path))
    rendered = report_json(report)
    assert report["rights_evidence_complete"] is True
    assert SECRET not in rendered
    assert "account_id" not in rendered
    assert "free_text" not in rendered


def test_output_is_deterministic_strict_json_without_raw_rows(tmp_path: Path) -> None:
    manifest = _write_json(tmp_path / "manifest.json", _manifest())
    rights = _write_json(tmp_path / "rights.json", _rights())
    first = run_contract_probe(_options(manifest_path=manifest, rights_path=rights))
    second = run_contract_probe(_options(manifest_path=manifest, rights_path=rights))
    assert report_json(first) == report_json(second)
    assert json.dumps(first, allow_nan=False, sort_keys=True)
    rendered = report_json(first)
    for raw_field in ("open_price", "close_price", "volume", "turnover", "name"):
        assert f'"{raw_field}"' not in rendered


def test_exception_and_request_id_cannot_leak_key() -> None:
    class LeakingTransport:
        def get(self, *_args, **_kwargs):
            raise RuntimeError(SECRET)

    report = run_contract_probe(
        _options(mode="live"),
        env_getter=lambda _name: SECRET,
        transport_factory=LeakingTransport,
    )
    assert SECRET not in report_json(report)

    response = _envelope(
        {"timestamp": 1783900800000, "item": []}, request_id=SECRET
    )
    report = run_contract_probe(
        _options(mode="live"),
        env_getter=lambda _name: SECRET,
        transport_factory=lambda: FakeTransport([response]),
    )
    assert SECRET not in report_json(report)
    assert SECRET not in repr(response)


@pytest.mark.parametrize("failure_point", ["environment", "factory"])
def test_setup_exceptions_are_replaced_with_safe_errors(failure_point) -> None:
    def leaking_env(_name: str) -> str:
        if failure_point == "environment":
            raise RuntimeError(SECRET)
        return SECRET

    def leaking_factory():
        raise RuntimeError(SECRET)

    with pytest.raises(ProbeConfigurationError) as captured:
        run_contract_probe(
            _options(mode="live"),
            env_getter=leaking_env,
            transport_factory=leaking_factory,
        )
    assert SECRET not in str(captured.value)
    assert captured.value.__cause__ is None


def test_cli_error_is_secret_safe(capsys) -> None:
    result = main(
        [
            "--allow-network",
            *sum((["--representative", item] for item in REPRESENTATIVES), []),
            "--start-date",
            "2026-07-01",
            "--end-date",
            "2026-07-10",
        ],
        env_getter=lambda _name: None,
    )
    assert result == 2
    assert SECRET not in capsys.readouterr().out


def test_probe_imports_no_database_or_persistence_modules() -> None:
    forbidden = ("sqlalchemy", "backend.database", "backend.persistence")
    before = set(sys.modules)
    run_contract_probe(_options())
    added = set(sys.modules) - before
    assert not any(name == prefix or name.startswith(f"{prefix}.") for name in added for prefix in forbidden)


def test_malformed_manifest_schema_fails_closed_without_internal_error(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["schema"] = ["thscode", 1]
    path = _write_json(tmp_path / "manifest.json", manifest)
    report = run_contract_probe(_options(manifest_path=path))
    assert report["manifest_evidence_complete"] is False


def test_missing_data_timestamp_is_contract_invalid() -> None:
    transport = FakeTransport([_envelope({"item": []})])
    report = run_contract_probe(
        _options(mode="live"),
        env_getter=lambda _name: SECRET,
        transport_factory=lambda: transport,
    )
    ticker = next(item for item in report["endpoints"] if item["endpoint_id"] == "ticker_list")
    assert ticker["business_category"] == "contract_invalid"


def test_missing_envelope_request_id_is_contract_invalid() -> None:
    response = HttpResponse(
        200,
        {
            "code": 0,
            "message": "success",
            "data": {"timestamp": 1783900800000, "item": []},
        },
    )
    report = run_contract_probe(
        _options(mode="live"),
        env_getter=lambda _name: SECRET,
        transport_factory=lambda: FakeTransport([response]),
    )
    ticker = next(item for item in report["endpoints"] if item["endpoint_id"] == "ticker_list")
    assert ticker["business_category"] == "contract_invalid"
