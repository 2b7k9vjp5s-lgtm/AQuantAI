from __future__ import annotations

from copy import deepcopy
from datetime import date
import inspect
from pathlib import Path

import pytest

from datasource import ths_structured_provider as ths
from datasource.ths_structured_provider import live_schemas


FIXTURES = Path(__file__).parent / "fixtures" / "ths_daily_market_acquisition"


def _equities() -> tuple[ths.EquityIdentity, ...]:
    return (
        ths.EquityIdentity("SYNTH.SSE.EQ001", "990001", ths.Exchange.SSE),
        ths.EquityIdentity("SYNTH.SZSE.EQ002", "990002", ths.Exchange.SZSE),
    )


def _sessions() -> tuple[date, ...]:
    return (date(2026, 7, 27), date(2026, 7, 28))


def _equity_observations() -> tuple[ths.ExpectedObservation, ...]:
    return tuple(
        ths.ExpectedObservation(identity.identity_key, session)
        for session in _sessions()
        for identity in _equities()
    )


def _daily_selector(
    adjustment: ths.DailyAdjustment = ths.DailyAdjustment.RAW,
) -> ths.AShareDailySelector:
    return ths.AShareDailySelector(
        identities=_equities(),
        requested_sessions=_sessions(),
        expected_observations=_equity_observations(),
        adjustment=adjustment,
        provider_horizon_reference_date=_sessions()[-1],
    )


def _benchmark_selector() -> ths.BenchmarkDailySelector:
    identity = ths.BenchmarkIdentity(
        "SYNTH.SSE.IDX50",
        "999950",
        ths.Exchange.SSE,
    )
    return ths.BenchmarkDailySelector(
        identities=(identity,),
        requested_sessions=_sessions(),
        expected_observations=tuple(
            ths.ExpectedObservation(identity.identity_key, session)
            for session in _sessions()
        ),
        provider_horizon_reference_date=_sessions()[-1],
    )


def _fixture(name: str) -> dict[str, object]:
    return ths.load_synthetic_live_fixture(FIXTURES / name)


def test_all_required_success_fixtures_validate_with_exact_coverage() -> None:
    listed = ths.validate_live_response(
        ths.ListedInstrumentSelector(
            identities=_equities(),
            as_of_date=_sessions()[-1],
            provider_horizon_reference_date=_sessions()[-1],
        ),
        _fixture("stock_basic_success.synthetic.json"),
    )
    assert listed.item_count == 2
    assert listed.covered_sessions == ("2026-07-28",)

    calendar = ths.validate_live_response(
        ths.TradingCalendarSelector(
            exchange=ths.Exchange.SSE,
            requested_dates=_sessions(),
            provider_horizon_reference_date=_sessions()[-1],
        ),
        _fixture("trade_calendar_success.synthetic.json"),
    )
    assert calendar.item_count == 2
    assert calendar.covered_sessions == ("2026-07-27", "2026-07-28")

    daily = ths.validate_live_response(
        _daily_selector(),
        _fixture("a_share_daily_success.synthetic.json"),
    )
    assert daily.item_count == 4
    assert daily.covered_sessions == ("2026-07-27", "2026-07-28")

    benchmark = ths.validate_live_response(
        _benchmark_selector(),
        _fixture("benchmark_daily_success.synthetic.json"),
    )
    assert benchmark.item_count == 2
    assert benchmark.covered_sessions == ("2026-07-27", "2026-07-28")


def test_request_id_is_transport_metadata_and_does_not_change_content_fingerprint() -> None:
    selector = _daily_selector()
    first_fixture = _fixture("a_share_daily_success.synthetic.json")
    second_fixture = deepcopy(first_fixture)
    second_fixture["request_id"] = "SYNTH-OTHER-REQUEST"

    first = ths.validate_live_response(selector, first_fixture)
    second = ths.validate_live_response(selector, second_fixture)
    assert first.content_fingerprint == second.content_fingerprint
    assert first.items_as_dicts() == second.items_as_dicts()


def test_partial_response_fails_closed_with_exact_missing_natural_key() -> None:
    with pytest.raises(ths.LiveResponseValidationError) as error:
        ths.validate_live_response(
            _daily_selector(),
            _fixture("partial_response.synthetic.json"),
        )
    assert error.value.reason_code is ths.LiveResponseFailureCode.COVERAGE_INCOMPLETE
    assert "2026-07-28" in str(error.value)
    assert "990002" in str(error.value)


def test_unknown_field_and_wrong_source_or_capability_are_rejected() -> None:
    selector = _daily_selector()

    unknown = _fixture("a_share_daily_success.synthetic.json")
    unknown["data"]["items"][0]["unexpected"] = "reject"
    with pytest.raises(ths.LiveResponseValidationError) as unknown_error:
        ths.validate_live_response(selector, unknown)
    assert unknown_error.value.reason_code is ths.LiveResponseFailureCode.SCHEMA_MISMATCH

    wrong_source = _fixture("a_share_daily_success.synthetic.json")
    wrong_source["data"]["source_key"] = "another-source"
    with pytest.raises(ths.LiveResponseValidationError) as source_error:
        ths.validate_live_response(selector, wrong_source)
    assert source_error.value.reason_code is ths.LiveResponseFailureCode.SOURCE_MISMATCH

    wrong_capability = _fixture("a_share_daily_success.synthetic.json")
    wrong_capability["data"]["capability"] = "benchmark_index_daily"
    with pytest.raises(ths.LiveResponseValidationError) as capability_error:
        ths.validate_live_response(selector, wrong_capability)
    assert capability_error.value.reason_code is ths.LiveResponseFailureCode.CAPABILITY_MISMATCH


def test_unrequested_date_identity_mismatch_duplicate_and_ordering_fail_closed() -> None:
    selector = _daily_selector()

    wrong_date = _fixture("a_share_daily_success.synthetic.json")
    wrong_date["data"]["items"][-1]["trade_date"] = "2026-07-29"
    with pytest.raises(ths.LiveResponseValidationError) as date_error:
        ths.validate_live_response(selector, wrong_date)
    assert date_error.value.reason_code is ths.LiveResponseFailureCode.COVERAGE_INCOMPLETE

    wrong_identity = _fixture("a_share_daily_success.synthetic.json")
    wrong_identity["data"]["items"][0]["provider_symbol"] = "SYNTH.SSE.UNKNOWN"
    with pytest.raises(ths.LiveResponseValidationError) as identity_error:
        ths.validate_live_response(selector, wrong_identity)
    assert identity_error.value.reason_code is ths.LiveResponseFailureCode.COVERAGE_INCOMPLETE

    duplicate = _fixture("a_share_daily_success.synthetic.json")
    duplicate["data"]["items"][1] = deepcopy(duplicate["data"]["items"][0])
    with pytest.raises(ths.LiveResponseValidationError) as duplicate_error:
        ths.validate_live_response(selector, duplicate)
    assert duplicate_error.value.reason_code is ths.LiveResponseFailureCode.DUPLICATE_NATURAL_KEY

    out_of_order = _fixture("a_share_daily_success.synthetic.json")
    out_of_order["data"]["items"][0], out_of_order["data"]["items"][1] = (
        out_of_order["data"]["items"][1],
        out_of_order["data"]["items"][0],
    )
    with pytest.raises(ths.LiveResponseValidationError) as ordering_error:
        ths.validate_live_response(selector, out_of_order)
    assert ordering_error.value.reason_code is ths.LiveResponseFailureCode.ORDERING_INVALID


def test_invalid_ohlc_nonfinite_and_negative_volume_are_rejected() -> None:
    selector = _daily_selector()

    invalid_ohlc = _fixture("a_share_daily_success.synthetic.json")
    invalid_ohlc["data"]["items"][0]["high"] = 8
    with pytest.raises(ths.LiveResponseValidationError) as ohlc_error:
        ths.validate_live_response(selector, invalid_ohlc)
    assert ohlc_error.value.reason_code is ths.LiveResponseFailureCode.OHLC_INVALID

    nonfinite = _fixture("a_share_daily_success.synthetic.json")
    nonfinite["data"]["items"][0]["close"] = float("inf")
    with pytest.raises(ths.LiveResponseValidationError) as finite_error:
        ths.validate_live_response(selector, nonfinite)
    assert finite_error.value.reason_code is ths.LiveResponseFailureCode.SCHEMA_MISMATCH

    negative_volume = _fixture("a_share_daily_success.synthetic.json")
    negative_volume["data"]["items"][0]["volume"] = -1
    with pytest.raises(ths.LiveResponseValidationError) as volume_error:
        ths.validate_live_response(selector, negative_volume)
    assert volume_error.value.reason_code is ths.LiveResponseFailureCode.OHLC_INVALID


def test_adjusted_daily_requires_exact_adjustment_capability_and_values() -> None:
    selector = _daily_selector(ths.DailyAdjustment.QFQ)
    value = _fixture("a_share_daily_success.synthetic.json")
    value["data"]["capability"] = "a_share_daily_adjusted"
    for item in value["data"]["items"]:
        item["adjust_type"] = "qfq"

    validated = ths.validate_live_response(selector, value)
    assert validated.capability is ths.DailyMarketCapability.A_SHARE_DAILY_ADJUSTED
    assert all(item["adjust_type"] == "qfq" for item in validated.items_as_dicts())

    wrong_adjustment = deepcopy(value)
    wrong_adjustment["data"]["items"][0]["adjust_type"] = "hfq"
    with pytest.raises(ths.LiveResponseValidationError) as error:
        ths.validate_live_response(selector, wrong_adjustment)
    assert error.value.reason_code is ths.LiveResponseFailureCode.CAPABILITY_MISMATCH


def test_historical_block_response_schema_remains_explicitly_fail_closed() -> None:
    selector = ths.HistoricalBlockSnapshotSelector(
        taxonomy=ths.BlockTaxonomy.CONCEPT,
        block_id="SYNTH.CONCEPT.A",
        snapshot_date=_sessions()[-1],
        expected_member_count=2,
        provider_horizon_reference_date=_sessions()[-1],
    )
    with pytest.raises(ths.LiveResponseValidationError) as error:
        ths.validate_live_response(selector, {})
    assert error.value.reason_code is ths.LiveResponseFailureCode.UNSUPPORTED_CAPABILITY


def test_fixture_marker_is_mandatory_and_not_accepted_as_provider_field() -> None:
    raw_path = FIXTURES / "stock_basic_success.synthetic.json"
    raw = raw_path.read_text(encoding="utf-8")
    assert "_aquantai_fixture_kind" in raw

    loaded = ths.load_synthetic_live_fixture(raw_path)
    assert "_aquantai_fixture_kind" not in loaded

    with pytest.raises(ths.LiveResponseValidationError):
        ths.strip_synthetic_live_fixture_marker({"code": 0})


def test_m3_module_has_no_network_secret_environment_or_persistence_path() -> None:
    source = inspect.getsource(live_schemas)
    for forbidden in (
        "import requests",
        "import httpx",
        "import socket",
        "import subprocess",
        "urllib.request",
        "os.environ",
        "getenv(",
        "Session(",
        "create_engine",
    ):
        assert forbidden not in source
