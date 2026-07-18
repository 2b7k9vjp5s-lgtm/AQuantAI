from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database.engine import build_session_factory
from backend.database.market_data import MarketDataPersistenceService
from backend.database.models import Base, IngestionRun
from backend.database.series import SnapshotSeriesIdentity
from datasource.fixtures import FIXTURE_PROVIDER, FIXTURE_SCOPE, build_market_data_fixture
from market_cockpit.repository import (
    MarketCockpitRepository,
    MarketCockpitSelectionError,
    MarketCockpitSnapshotNotFound,
)
from market_cockpit.service import MarketCockpitService


@pytest.fixture
def database() -> Iterator[tuple[Engine, sessionmaker[Session]]]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine, build_session_factory(engine)
    engine.dispose()


def _ingest(
    session_factory: sessionmaker[Session],
    *,
    cutoff: str,
    name: str,
    adjust_type: str = "",
    compatibility_parameters: dict | None = None,
    provider_request_metadata: dict | None = None,
):
    bundle = build_market_data_fixture()
    bundle.stock_basic.loc[0, "stock_name"] = name
    bundle.daily_price.loc[:, "adjust_type"] = adjust_type
    return MarketDataPersistenceService(session_factory).ingest_bundle(
        bundle,
        provider=FIXTURE_PROVIDER,
        requested_start_date="20260708",
        requested_end_date="20260709",
        information_cutoff_date=cutoff,
        requested_scope=FIXTURE_SCOPE,
        adjust_type=adjust_type,
        compatibility_parameters=compatibility_parameters,
        provider_request_metadata=provider_request_metadata,
    )


def test_repository_requires_explicit_series_and_rejects_provider_only(database) -> None:
    _, session_factory = database
    with session_factory() as session:
        with pytest.raises(MarketCockpitSelectionError, match="provider-only selection is not allowed"):
            MarketCockpitRepository(session).load_snapshot()


def test_current_and_historical_cutoff_select_one_complete_run(database) -> None:
    _, session_factory = database
    old = _ingest(session_factory, cutoff="20260709", name="Historical")
    current = _ingest(session_factory, cutoff="20260710", name="Current")
    assert old.series_key == current.series_key

    with session_factory() as session:
        repository = MarketCockpitRepository(session)
        current_snapshot = repository.load_snapshot(series_key=current.series_key)
        historical_snapshot = repository.load_snapshot(
            series_key=current.series_key,
            as_of_cutoff="20260709",
        )

    assert current_snapshot.ingestion_run_id == current.ingestion_run_id
    assert historical_snapshot.ingestion_run_id == old.ingestion_run_id
    assert current_snapshot.stock_basic.loc[0, "stock_name"] == "Current"
    assert historical_snapshot.stock_basic.loc[0, "stock_name"] == "Historical"
    assert set(current_snapshot.daily_price["adjust_type"]) == {""}


def test_complete_selector_is_equivalent_and_forged_selector_fails(database) -> None:
    _, session_factory = database
    result = _ingest(session_factory, cutoff="20260710", name="Current")
    with session_factory() as session:
        by_key = MarketCockpitRepository(session).load_snapshot(series_key=result.series_key)
        selector = SnapshotSeriesIdentity(result.series_key, by_key.series_identity)
        by_selector = MarketCockpitRepository(session).load_snapshot(selector=selector)
        forged = dict(by_key.series_identity)
        forged["adjust_type"] = "qfq"
        with pytest.raises(ValueError):
            MarketCockpitRepository(session).load_snapshot(
                selector=SnapshotSeriesIdentity(result.series_key, forged)
            )

    assert by_selector.ingestion_run_id == by_key.ingestion_run_id


def test_incompatible_series_and_adjustment_are_never_stitched(database) -> None:
    _, session_factory = database
    unadjusted = _ingest(
        session_factory,
        cutoff="20260710",
        name="Unadjusted",
        compatibility_parameters={"frequency": "daily"},
    )
    qfq = _ingest(
        session_factory,
        cutoff="20260710",
        name="Adjusted",
        adjust_type="qfq",
        compatibility_parameters={"frequency": "daily"},
    )
    alternate = _ingest(
        session_factory,
        cutoff="20260710",
        name="Alternate",
        compatibility_parameters={"frequency": "alternate"},
    )

    assert len({unadjusted.series_key, qfq.series_key, alternate.series_key}) == 3
    with session_factory() as session:
        repository = MarketCockpitRepository(session)
        unadjusted_snapshot = repository.load_snapshot(series_key=unadjusted.series_key)
        qfq_snapshot = repository.load_snapshot(series_key=qfq.series_key)
        alternate_snapshot = repository.load_snapshot(series_key=alternate.series_key)

    assert set(unadjusted_snapshot.daily_price["adjust_type"]) == {""}
    assert set(qfq_snapshot.daily_price["adjust_type"]) == {"qfq"}
    assert unadjusted_snapshot.ingestion_run_id != alternate_snapshot.ingestion_run_id
    assert set(alternate_snapshot.stock_basic["stock_name"]) == {"Alternate", "SPDB"}


def test_missing_or_too_early_cutoff_returns_actionable_not_found(database) -> None:
    _, session_factory = database
    result = _ingest(session_factory, cutoff="20260710", name="Current")
    with session_factory() as session:
        repository = MarketCockpitRepository(session)
        with pytest.raises(MarketCockpitSnapshotNotFound, match="at or before cutoff 20260708"):
            repository.load_snapshot(series_key=result.series_key, as_of_cutoff="20260708")


def test_repository_exposes_only_allowlisted_normalized_immutable_provenance(database) -> None:
    _, session_factory = database
    compatibility = {
        "stock_basic_endpoint": "stock_info_a_code_name",
        "daily_price_endpoint": "stock_zh_a_hist",
        "trade_calendar_endpoint": "tool_trade_date_hist_sina",
        "frequency": "daily",
        "adapter_compatibility_version": "akshare-normalized-v1",
        "unknown_compatibility": "must-not-be-public",
    }
    result = _ingest(
        session_factory,
        cutoff="20260710",
        name="Current",
        compatibility_parameters=compatibility,
    )
    with session_factory.begin() as session:
        run = session.get(IngestionRun, result.ingestion_run_id)
        assert run is not None
        run.imported_at = datetime(2026, 7, 18, 4, 0, tzinfo=timezone.utc)
        run.completed_at = datetime(2026, 7, 18, 4, 0, 1, tzinfo=timezone.utc)
        run.provider_request_metadata = {
            "collection_timestamp_utc": "2026-07-18T12:30:00+08:00",
            "effective_information_cutoff_date": "20260718",
            "akshare_package_version": "1.17.0",
            "api_token": "must-not-be-public",
            "unknown_metadata": "must-not-be-public",
        }

    with session_factory() as session:
        service = MarketCockpitService(
            MarketCockpitRepository(session),
            clock=lambda: datetime(2026, 7, 18, 5, 0, tzinfo=timezone.utc),
        )
        payload = service.build_snapshot(
            series_key=result.series_key,
            as_of_cutoff="2026-07-18",
        ).to_dict()

    provenance = payload["provenance"]
    assert provenance["ingestion_imported_at_utc"] == "2026-07-18T04:00:00Z"
    assert provenance["ingestion_completed_at_utc"] == "2026-07-18T04:00:01Z"
    assert provenance["collection_timestamp_utc"] == "2026-07-18T04:30:00Z"
    assert provenance["effective_information_cutoff_date"] == "20260718"
    assert provenance["akshare_package_version"] == "1.17.0"
    assert provenance["stock_basic_endpoint"] == "stock_info_a_code_name"
    assert provenance["daily_price_endpoint"] == "stock_zh_a_hist"
    assert provenance["trade_calendar_endpoint"] == "tool_trade_date_hist_sina"
    assert provenance["frequency"] == "daily"
    assert provenance["adapter_compatibility_version"] == "akshare-normalized-v1"
    assert provenance["requested_as_of_cutoff"] == "20260718"
    assert provenance["generated_at_utc"] == "2026-07-18T05:00:00Z"
    serialized = str(payload)
    assert "api_token" not in serialized
    assert "unknown_metadata" not in serialized
    assert "unknown_compatibility" not in serialized
    assert "must-not-be-public" not in serialized


def test_backfilled_or_fixture_run_keeps_optional_provenance_null(database) -> None:
    _, session_factory = database
    result = _ingest(session_factory, cutoff="20260710", name="Fixture")

    with session_factory() as session:
        snapshot = MarketCockpitRepository(session).load_snapshot(series_key=result.series_key)

    assert snapshot.collection_timestamp_utc is None
    assert snapshot.effective_information_cutoff_date is None
    assert snapshot.akshare_package_version is None
    assert snapshot.stock_basic_endpoint is None
    assert snapshot.adapter_compatibility_version is None


def test_connection_string_shaped_compatibility_value_is_not_exposed(database) -> None:
    _, session_factory = database
    result = _ingest(
        session_factory,
        cutoff="20260710",
        name="Unsafe compatibility",
        compatibility_parameters={
            "stock_basic_endpoint": "postgresql://user:password@host/database",
            "daily_price_endpoint": "stock_zh_a_hist",
        },
    )

    with session_factory() as session:
        snapshot = MarketCockpitRepository(session).load_snapshot(series_key=result.series_key)

    assert snapshot.stock_basic_endpoint is None
    assert snapshot.daily_price_endpoint == "stock_zh_a_hist"
