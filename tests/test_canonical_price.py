from __future__ import annotations

from datetime import date, datetime, timezone
import json
import socket
from uuid import UUID

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price import (
    CanonicalPriceCommandService,
    CanonicalPriceError,
    CanonicalPriceQueryService,
    canonicalize_float,
)
from backend.database.canonical_price_models import (
    CanonicalPriceRevision,
    CanonicalPriceSeries,
    ComparisonEligibilityRevision,
    ListedInstrument,
)
from backend.database.models import Base, DailyPriceRecord, IngestionRun
import scripts.canonical_price_cli as canonical_cli
import scripts.record_canonical_price as price_cli
import scripts.record_canonical_price_series as series_cli
import scripts.record_listed_instrument as instrument_cli
import scripts.record_price_comparison_eligibility as eligibility_cli

UTC = timezone.utc
RECORDED = "2026-07-22T10:00:00Z"
CUTOFF = "2026-07-22"


@pytest.fixture()
def database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


def _seed_source(factory, *, close: float = 12.345):
    with factory.begin() as session:
        run = IngestionRun(
            batch_identifier="a" * 64, series_key="b" * 64, series_identity={},
            provider="fixture", dataset="daily_price",
            imported_at=datetime(2026, 7, 22, 8, tzinfo=UTC),
            completed_at=datetime(2026, 7, 22, 9, tzinfo=UTC),
            requested_start_date=date(2026, 7, 22), requested_end_date=date(2026, 7, 22),
            information_cutoff_date=date(2026, 7, 22), requested_scope={},
            provider_request_metadata={}, adapter_version="fixture.v1", snapshot_mode="complete",
            contract_version="v1", status="succeeded", row_count_received=1,
            row_count_written=1, dataset_counts={"daily_price": 1}, error_summary=None,
        )
        session.add(run); session.flush()
        price = DailyPriceRecord(
            ingestion_run_id=run.id, trade_date=date(2026, 7, 22), stock_code="000001",
            open=12.0, high=13.0, low=11.0, close=close, volume=100.0, amount=1234.5,
            adjust_type="", source="fixture",
        )
        session.add(price); session.flush()
        return run.id, price.id


def _common():
    return {"recorded_by": "fixture", "information_cutoff_date": CUTOFF, "recorded_at_utc": RECORDED}


def _golden(factory):
    run_id, source_id = _seed_source(factory)
    service = CanonicalPriceCommandService(factory)
    instrument = service.record_listed_instrument({
        **_common(), "instrument_key": "fixture-cn-equity-000001", "expected_latest_revision_id": None,
        "canonical_symbol": "000001", "security_type": "common_equity", "market_code": "CN_A",
        "exchange_code_namespace": "ISO_MIC", "exchange_code": "XSHE", "currency_code": "CNY",
        "listing_date": "1991-04-03", "delisting_date": None, "listing_status": "active",
    })
    series = service.record_series({
        **_common(), "series_contract_key": "fixture-000001-close", "instrument_id": instrument["instrument_id"],
        "instrument_revision_id": instrument["instrument_revision_id"], "expected_latest_revision_id": None,
        "provider": "fixture", "dataset": "daily_price", "series_key": "b" * 64,
        "source_stock_code": "000001", "source_adjust_type": "", "price_kind": "official_close",
        "adjustment_basis": "unadjusted", "unit_code": "currency_per_share", "currency_code": "CNY",
        "decimal_scale": 2, "decimal_rule_code": "float_repr_decimal_v1", "rounding_mode": "ROUND_HALF_EVEN", "status": "accepted",
    })
    price_input = {
        **_common(), "series_id": series["series_id"], "series_revision_id": series["series_revision_id"],
        "instrument_revision_id": instrument["instrument_revision_id"], "source_daily_price_id": source_id,
        "source_ingestion_run_id": run_id, "trade_date": CUTOFF, "expected_latest_revision_id": None,
        "canonical_status": "accepted", "conflict_summary": None,
    }
    dry_run = service.record_price(price_input, dry_run=True)
    price = service.record_price(price_input)
    eligibility = service.record_eligibility({
        **_common(), "assessment_key": "fixture-price-context", "purpose_code": "company_research_price_context_v1",
        "expected_latest_revision_id": None, "rule_version": "aquantai.company-research-price-context-eligibility.v1",
        "state": "eligible", "reason_codes": ["canonical_price_accepted", "source_numeric_fidelity_disclosed"],
        "requested_trade_date": CUTOFF, "canonical_price_revision_ids": [price["canonical_price_revision_id"]],
    })
    return instrument, series, price, eligibility, dry_run


def test_decimal_conversion_is_deterministic_and_rejects_invalid_values():
    assert canonicalize_float(2.345, 2)[:2] == ("2.345", "2.34")
    assert canonicalize_float(2.355, 2)[1] == "2.36"
    for value in (float("nan"), float("inf"), float("-inf"), 0.0, -1.0):
        with pytest.raises(CanonicalPriceError, match="finite and positive"):
            canonicalize_float(value, 2)
    with pytest.raises(CanonicalPriceError, match="outside the accepted bounds"):
        canonicalize_float(1e18, 2)


def test_offline_golden_path_and_strict_json(database):
    instrument, _series, price, eligibility, dry_run = _golden(database)
    assert dry_run["standardized_value_text"] == "12.34"
    assert dry_run["numeric_fidelity"] == "binary_float_normalized"
    boundary = datetime(2026, 7, 22, 10, tzinfo=UTC)
    with database() as session:
        query = CanonicalPriceQueryService(session)
        instrument_payload = query.get_instrument(UUID(instrument["instrument_id"]), as_of_cutoff=date(2026, 7, 22), as_of_recorded_at_utc=boundary)
        price_payload = query.get_price(UUID(price["canonical_price_id"]), as_of_cutoff=date(2026, 7, 22), as_of_recorded_at_utc=boundary)
        eligibility_payload = query.get_eligibility(UUID(eligibility["assessment_id"]), as_of_cutoff=date(2026, 7, 22), as_of_recorded_at_utc=boundary)
    assert instrument_payload["revision"]["exchange_code"] == "XSHE"
    assert price_payload["revision"]["value_decimal"] == "12.34"
    assert eligibility_payload["revision"]["state"] == "eligible"
    json.dumps({"instrument": instrument_payload, "price": price_payload, "eligibility": eligibility_payload}, allow_nan=False)


def test_missing_identity_and_bad_source_roll_back_atomically(database):
    service = CanonicalPriceCommandService(database)
    bad = {
        **_common(), "instrument_key": "bad", "expected_latest_revision_id": None,
        "canonical_symbol": "000001", "security_type": "common_equity", "market_code": "CN_A",
        "exchange_code_namespace": "ISO_MIC", "exchange_code": "", "currency_code": "CNY",
        "listing_date": "1991-04-03", "delisting_date": None, "listing_status": "active",
    }
    with pytest.raises(CanonicalPriceError): service.record_listed_instrument(bad)
    with database() as session:
        assert session.scalar(select(func.count()).select_from(ListedInstrument)) == 0


def test_dry_run_and_expected_latest_do_not_write(database):
    service = CanonicalPriceCommandService(database)
    payload = {
        **_common(), "instrument_key": "dry", "expected_latest_revision_id": None,
        "canonical_symbol": "000002", "security_type": "common_equity", "market_code": "CN_A",
        "exchange_code_namespace": "ISO_MIC", "exchange_code": "XSHG", "currency_code": "CNY",
        "listing_date": "2000-01-01", "delisting_date": None, "listing_status": "active",
    }
    assert service.record_listed_instrument(payload, dry_run=True)["dry_run"] is True
    with database() as session: assert session.scalar(select(func.count()).select_from(ListedInstrument)) == 0
    first = service.record_listed_instrument(payload)
    payload["expected_latest_revision_id"] = "00000000-0000-0000-0000-000000000001"
    with pytest.raises(CanonicalPriceError, match="expected_latest"):
        service.record_listed_instrument(payload)
    with database() as session: assert session.get(ListedInstrument, UUID(first["instrument_id"])) is not None


def test_unknown_fields_and_unsupported_purpose_fail_closed(database):
    service = CanonicalPriceCommandService(database)
    with pytest.raises(CanonicalPriceError, match="unknown fields"):
        service.record_listed_instrument({"unexpected": True})
    result = service.record_eligibility({
        **_common(), "assessment_key": "future", "purpose_code": "future-purpose",
        "expected_latest_revision_id": None, "rule_version": "future-rule", "state": "not_applicable",
        "reason_codes": ["purpose_not_supported"], "requested_trade_date": CUTOFF,
        "canonical_price_revision_ids": [],
    })
    assert result["state"] == "not_applicable"


def test_histories_are_append_only(database):
    _instrument, series, _price, _eligibility, _dry = _golden(database)
    with pytest.raises(Exception, match="append-only"):
        with database.begin() as session:
            row = session.get(CanonicalPriceSeries, UUID(series["series_id"]))
            row.series_contract_key = "changed"


def test_source_mutation_is_detected_on_read(database):
    _instrument, _series, price, _eligibility, _dry = _golden(database)
    with database.begin() as session:
        revision = session.get(CanonicalPriceRevision, UUID(price["canonical_price_revision_id"]))
        source = session.get(DailyPriceRecord, revision.source_daily_price_id)
        source.close = 99.0
    with database() as session:
        with pytest.raises(CanonicalPriceError, match="no longer matches"):
            CanonicalPriceQueryService(session).get_price(
                UUID(price["canonical_price_id"]),
                as_of_cutoff=date(2026, 7, 22),
                as_of_recorded_at_utc=datetime(2026, 7, 22, 10, tzinfo=UTC),
            )


def test_four_cli_entrypoints_and_local_dry_run(database, tmp_path, monkeypatch, capsys):
    payload = {
        **_common(), "instrument_key": "cli-dry", "expected_latest_revision_id": None,
        "canonical_symbol": "000003", "security_type": "common_equity", "market_code": "CN_A",
        "exchange_code_namespace": "ISO_MIC", "exchange_code": "XSHE", "currency_code": "CNY",
        "listing_date": "2001-01-01", "delisting_date": None, "listing_status": "active",
    }
    path = tmp_path / "instrument.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    engine = database.kw["bind"]
    monkeypatch.setattr(canonical_cli, "build_engine", lambda: engine)

    def reject_network(_socket, _address):
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    assert instrument_cli.main(["--input", str(path), "--dry-run"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "ok"
    assert output["result"]["dry_run"] is True
    assert all(callable(module.main) for module in (price_cli, series_cli, instrument_cli, eligibility_cli))
