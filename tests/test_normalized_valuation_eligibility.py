from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price import (
    CanonicalPriceCommandService,
    CanonicalPriceError,
    CanonicalPriceQueryService,
)
from backend.database.models import Base, DailyPriceRecord, IngestionRun
from backend.database.normalized_valuation_eligibility import (
    NORMALIZED_VALUATION_PURPOSE,
    NORMALIZED_VALUATION_RULE_VERSION,
    NormalizedValuationEligibilityCommandService,
    _validate_normalized_valuation_eligibility,
)

UTC = timezone.utc


@pytest.fixture()
def database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


def accepted_price(**overrides):
    values = {
        "canonical_status": "accepted",
        "trade_date": date(2026, 6, 30),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def eligibility_input(**overrides):
    values = {
        "purpose_code": NORMALIZED_VALUATION_PURPOSE,
        "rule_version": NORMALIZED_VALUATION_RULE_VERSION,
        "state": "eligible",
        "requested_trade_date": date(2026, 6, 30),
        "reason_codes": (
            "canonical_price_accepted",
            "source_numeric_fidelity_disclosed",
        ),
    }
    values.update(overrides)
    return values


def common() -> dict:
    return {
        "recorded_by": "normalized-valuation-test",
        "information_cutoff_date": "2026-06-30",
        "recorded_at_utc": "2026-07-01T00:00:00Z",
    }


def build_price(factory) -> tuple[dict, dict]:
    with factory.begin() as session:
        run = IngestionRun(
            batch_identifier="c" * 64,
            series_key="d" * 64,
            series_identity={},
            provider="fixture",
            dataset="daily_price",
            imported_at=datetime(2026, 6, 30, 20, tzinfo=UTC),
            completed_at=datetime(2026, 6, 30, 21, tzinfo=UTC),
            requested_start_date=date(2026, 6, 30),
            requested_end_date=date(2026, 6, 30),
            information_cutoff_date=date(2026, 6, 30),
            requested_scope={},
            provider_request_metadata={},
            adapter_version="fixture.v1",
            snapshot_mode="complete",
            contract_version="v1",
            status="succeeded",
            row_count_received=1,
            row_count_written=1,
            dataset_counts={"daily_price": 1},
            error_summary=None,
        )
        session.add(run)
        session.flush()
        source = DailyPriceRecord(
            ingestion_run_id=run.id,
            trade_date=date(2026, 6, 30),
            stock_code="000001",
            open=20.0,
            high=20.0,
            low=20.0,
            close=20.0,
            volume=100.0,
            amount=2000.0,
            adjust_type="",
            source="fixture",
        )
        session.add(source)
        session.flush()
        run_id = run.id
        source_id = source.id

    service = CanonicalPriceCommandService(factory)
    instrument = service.record_listed_instrument(
        {
            **common(),
            "instrument_key": "normalized-valuation-000001",
            "expected_latest_revision_id": None,
            "canonical_symbol": "000001",
            "security_type": "common_equity",
            "market_code": "CN_A",
            "exchange_code_namespace": "ISO_MIC",
            "exchange_code": "XSHE",
            "currency_code": "CNY",
            "listing_date": "1991-04-03",
            "delisting_date": None,
            "listing_status": "active",
        }
    )
    series = service.record_series(
        {
            **common(),
            "series_contract_key": "normalized-valuation-000001-close",
            "instrument_id": instrument["instrument_id"],
            "instrument_revision_id": instrument["instrument_revision_id"],
            "expected_latest_revision_id": None,
            "provider": "fixture",
            "dataset": "daily_price",
            "series_key": "d" * 64,
            "source_stock_code": "000001",
            "source_adjust_type": "",
            "price_kind": "official_close",
            "adjustment_basis": "unadjusted",
            "unit_code": "currency_per_share",
            "currency_code": "CNY",
            "decimal_scale": 2,
            "decimal_rule_code": "float_repr_decimal_v1",
            "rounding_mode": "ROUND_HALF_EVEN",
            "status": "accepted",
        }
    )
    price = service.record_price(
        {
            **common(),
            "series_id": series["series_id"],
            "series_revision_id": series["series_revision_id"],
            "instrument_revision_id": instrument["instrument_revision_id"],
            "source_daily_price_id": str(source_id),
            "source_ingestion_run_id": str(run_id),
            "trade_date": "2026-06-30",
            "expected_latest_revision_id": None,
            "canonical_status": "accepted",
            "conflict_summary": None,
        }
    )
    return instrument, price


def test_normalized_valuation_eligibility_accepts_exact_reviewed_contract() -> None:
    _validate_normalized_valuation_eligibility(
        eligibility_input(), [accepted_price()]
    )


def test_normalized_valuation_eligibility_rejects_wrong_rule_or_price_date() -> None:
    with pytest.raises(CanonicalPriceError, match="rule_version"):
        _validate_normalized_valuation_eligibility(
            eligibility_input(rule_version="wrong"), [accepted_price()]
        )
    with pytest.raises(CanonicalPriceError, match="requested trade date"):
        _validate_normalized_valuation_eligibility(
            eligibility_input(), [accepted_price(trade_date=date(2026, 6, 29))]
        )


def test_normalized_valuation_eligibility_requires_exact_eligible_reasons() -> None:
    with pytest.raises(CanonicalPriceError, match="exactly"):
        _validate_normalized_valuation_eligibility(
            eligibility_input(reason_codes=("canonical_price_accepted",)),
            [accepted_price()],
        )


def test_non_eligible_states_remain_fail_closed() -> None:
    with pytest.raises(CanonicalPriceError, match="cannot have members"):
        _validate_normalized_valuation_eligibility(
            eligibility_input(
                state="missing",
                reason_codes=("canonical_price_missing",),
            ),
            [accepted_price()],
        )
    with pytest.raises(CanonicalPriceError, match="conflicting canonical price"):
        _validate_normalized_valuation_eligibility(
            eligibility_input(
                state="conflicting",
                reason_codes=("canonical_price_conflicting",),
            ),
            [accepted_price()],
        )


def test_production_service_records_exact_slice5_purpose(database) -> None:
    _instrument, price = build_price(database)
    service = NormalizedValuationEligibilityCommandService(database)
    eligibility = service.record_eligibility(
        {
            **common(),
            "assessment_key": "normalized-valuation-price-context",
            "purpose_code": NORMALIZED_VALUATION_PURPOSE,
            "expected_latest_revision_id": None,
            "rule_version": NORMALIZED_VALUATION_RULE_VERSION,
            "state": "eligible",
            "reason_codes": [
                "canonical_price_accepted",
                "source_numeric_fidelity_disclosed",
            ],
            "requested_trade_date": "2026-06-30",
            "canonical_price_revision_ids": [price["canonical_price_revision_id"]],
        }
    )
    with database() as session:
        payload = CanonicalPriceQueryService(session).get_eligibility(
            UUID(eligibility["assessment_id"]),
            as_of_cutoff=date(2026, 6, 30),
            as_of_recorded_at_utc=datetime(2026, 7, 1, tzinfo=UTC),
        )
    assert payload["identity"]["purpose_code"] == NORMALIZED_VALUATION_PURPOSE
    assert payload["revision"]["rule_version"] == NORMALIZED_VALUATION_RULE_VERSION
    assert payload["revision"]["state"] == "eligible"
    assert payload["members"] == [price["canonical_price_revision_id"]]
