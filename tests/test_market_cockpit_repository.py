from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database.engine import build_session_factory
from backend.database.market_data import MarketDataPersistenceService
from backend.database.models import Base
from backend.database.series import SnapshotSeriesIdentity
from datasource.fixtures import FIXTURE_PROVIDER, FIXTURE_SCOPE, build_market_data_fixture
from market_cockpit.repository import (
    MarketCockpitRepository,
    MarketCockpitSelectionError,
    MarketCockpitSnapshotNotFound,
)


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
