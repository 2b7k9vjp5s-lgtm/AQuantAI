from __future__ import annotations

from collections.abc import Iterator

import pandas as pd
import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.engine import build_session_factory
from backend.database.models import (
    Base,
    IngestionRun,
    SectorDailyRecord,
    SectorDefinitionRecord,
)
from backend.database.sector_data import (
    SECTOR_PROVIDER_METADATA_FIELDS,
    SectorDataValidationError,
    SectorPersistenceService,
    validate_sector_bundle,
)
from backend.database.series import (
    build_benchmark_series_identity,
    build_sector_series_identity,
)
from datasource.base import SectorMarketBundle
from datasource.akshare import SECTOR_ENDPOINT_COMPATIBILITY_VERSION
from market_cockpit.sector_fixtures import (
    SECTOR_FIXTURE_CODES,
    SECTOR_FIXTURE_CURRENT_CUTOFF,
    SECTOR_FIXTURE_END_DATE,
    SECTOR_FIXTURE_HISTORICAL_CUTOFF,
    SECTOR_FIXTURE_PROVIDER,
    SECTOR_FIXTURE_SCOPE,
    SECTOR_FIXTURE_START_DATE,
    build_sector_fixture,
)
from market_cockpit.sector_repository import (
    SectorRepository,
    SectorSelectionError,
    SectorSnapshotNotFound,
)


@pytest.fixture
def database() -> Iterator[sessionmaker[Session]]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _foreign_keys(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield build_session_factory(engine)
    engine.dispose()


def _ingest(
    service: SectorPersistenceService,
    *,
    revision: str = "current",
    cutoff: str = SECTOR_FIXTURE_CURRENT_CUTOFF,
    bundle: SectorMarketBundle | None = None,
    metadata: dict | None = None,
):
    return service.ingest_bundle(
        bundle or build_sector_fixture(revision=revision),
        provider=SECTOR_FIXTURE_PROVIDER,
        requested_start_date=SECTOR_FIXTURE_START_DATE,
        requested_end_date=SECTOR_FIXTURE_END_DATE,
        information_cutoff_date=cutoff,
        requested_scope=SECTOR_FIXTURE_SCOPE,
        taxonomy_endpoint="fixture_sector_taxonomy",
        history_endpoint="fixture_sector_history",
        adapter_compatibility_version="sector-fixture-v1",
        adapter_version="sector-fixture-v1",
        provider_request_metadata=(
            metadata if metadata is not None else _metadata(cutoff=cutoff)
        ),
    )


def _metadata(*, cutoff: str = SECTOR_FIXTURE_CURRENT_CUTOFF, **changes):
    values = {
        "taxonomy_endpoint": "fixture_sector_taxonomy",
        "history_endpoint": "fixture_sector_history",
        "classification_system": "eastmoney_industry_board",
        "classification_level": None,
        "frequency": "daily",
        "adjust_type": "",
        "sector_codes": list(SECTOR_FIXTURE_CODES),
        "start_date": SECTOR_FIXTURE_START_DATE,
        "end_date": SECTOR_FIXTURE_END_DATE,
        "network_mode": "offline-fixture",
        "timeout_seconds": 20,
        "max_retries": 2,
        "akshare_package_version": "1.18.64",
        "definition_contract_version": "1.0",
        "daily_contract_version": "1.0",
        "adapter_version": "sector-fixture-v1",
        "adapter_compatibility_version": "sector-fixture-v1",
        "collection_timestamp_utc": "2026-04-05T12:00:00Z",
        "effective_information_cutoff_date": cutoff,
    }
    values.update(changes)
    return values


def _record_failed_attempt(service: SectorPersistenceService, metadata: dict) -> int:
    return service.record_failed_attempt(
        RuntimeError("bounded provider failure"),
        provider=SECTOR_FIXTURE_PROVIDER,
        requested_start_date=SECTOR_FIXTURE_START_DATE,
        requested_end_date=SECTOR_FIXTURE_END_DATE,
        information_cutoff_date=SECTOR_FIXTURE_CURRENT_CUTOFF,
        requested_scope=SECTOR_FIXTURE_SCOPE,
        taxonomy_endpoint="fixture_sector_taxonomy",
        history_endpoint="fixture_sector_history",
        adapter_compatibility_version="sector-fixture-v1",
        adapter_version="sector-fixture-v1",
        provider_request_metadata=metadata,
    )


def test_sector_contract_builds_distinct_exact_series_and_preserves_null_metadata(database) -> None:
    summary = validate_sector_bundle(
        build_sector_fixture(),
        provider=SECTOR_FIXTURE_PROVIDER,
        requested_start_date=SECTOR_FIXTURE_START_DATE,
        requested_end_date=SECTOR_FIXTURE_END_DATE,
        information_cutoff_date=SECTOR_FIXTURE_CURRENT_CUTOFF,
        requested_scope=SECTOR_FIXTURE_SCOPE,
        taxonomy_endpoint="fixture_sector_taxonomy",
        history_endpoint="fixture_sector_history",
        adapter_compatibility_version="sector-fixture-v1",
    )
    benchmark = build_benchmark_series_identity(
        provider="fixture",
        contract_version="1.0",
        index_codes=["000001"],
        requested_start_date=SECTOR_FIXTURE_START_DATE,
        requested_end_date=SECTOR_FIXTURE_END_DATE,
        endpoint="fixture_index_history",
        adapter_compatibility_version="benchmark-fixture-v1",
    )
    assert summary.valid is True
    assert summary.dataset_counts == {"sector_definition": 2, "sector_daily": 130}
    assert summary.canonical_scope["series_schema"] == "aquantai.sector-snapshot-series.v1"
    assert summary.canonical_scope["sector_codes"] == SECTOR_FIXTURE_CODES
    assert summary.canonical_scope["classification_level"] is None
    assert summary.series_key != benchmark.series_key

    result = _ingest(SectorPersistenceService(database))
    with database() as session:
        definition = session.scalar(select(SectorDefinitionRecord).where(
            SectorDefinitionRecord.ingestion_run_id == result.ingestion_run_id
        ))
        assert definition is not None
        assert definition.classification_level is None
        assert definition.parent_sector_code is None
        assert definition.parent_sector_name is None


def test_fixed_provider_metadata_allowlist_persists_only_normalized_reviewed_fields(database) -> None:
    result = _ingest(
        SectorPersistenceService(database),
        metadata=_metadata(sector_codes=list(reversed(SECTOR_FIXTURE_CODES))),
    )
    with database() as session:
        run = session.get(IngestionRun, result.ingestion_run_id)
        assert run is not None
        assert set(run.provider_request_metadata) == SECTOR_PROVIDER_METADATA_FIELDS
        assert run.provider_request_metadata["sector_codes"] == SECTOR_FIXTURE_CODES
        assert run.provider_request_metadata["classification_level"] is None
        assert run.provider_request_metadata["collection_timestamp_utc"] == (
            "2026-04-05T12:00:00Z"
        )


def test_missing_provider_metadata_field_is_rejected_without_audit_or_data_rows(database) -> None:
    metadata = _metadata()
    metadata.pop("history_endpoint")
    with pytest.raises(SectorDataValidationError, match=r"missing=\['history_endpoint'\]"):
        _ingest(SectorPersistenceService(database), metadata=metadata)
    with database() as session:
        assert session.scalar(select(func.count()).select_from(IngestionRun)) == 0
        assert session.scalar(select(func.count()).select_from(SectorDefinitionRecord)) == 0
        assert session.scalar(select(func.count()).select_from(SectorDailyRecord)) == 0


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"unknown_scalar": "debug"}, "fixed sector allowlist"),
        ({"raw_response": {"rows": [1, 2]}}, "fixed sector allowlist"),
        ({"host_path": "C:/private/debug.json"}, "fixed sector allowlist"),
        ({"api_token": "not-persisted"}, "Sensitive metadata field"),
        ({"network_mode": {"raw": "offline-fixture"}}, "flat scalar"),
        ({"classification_level": "level_1"}, "explicitly null"),
        ({"taxonomy_endpoint": "other_taxonomy"}, "canonical sector request"),
        ({"history_endpoint": "other_history"}, "canonical sector request"),
        ({"sector_codes": ["BK0001"]}, "canonical sector request"),
        ({"start_date": "20260106"}, "canonical sector request"),
        ({"end_date": "20260402"}, "canonical sector request"),
        ({"definition_contract_version": "2.0"}, "canonical sector request"),
        ({"daily_contract_version": "2.0"}, "canonical sector request"),
        ({"adapter_compatibility_version": "sector-fixture-v2"}, "canonical sector request"),
        ({"collection_timestamp_utc": "2026-04-05T12:00:00"}, "timezone-aware UTC"),
        ({"collection_timestamp_utc": "2026-04-05T20:00:00+08:00"}, "timezone-aware UTC"),
        ({"timeout_seconds": float("inf")}, "finite and in"),
        ({"timeout_seconds": "20"}, "finite and in"),
        ({"timeout_seconds": "twenty"}, "finite and in"),
        ({"max_retries": 2.0}, "integer between"),
        ({"max_retries": 6}, "integer between"),
        ({"akshare_package_version": "1.17.0"}, "reviewed sector endpoint version"),
    ],
)
def test_provider_metadata_rejection_is_fail_closed_without_rows(
    database, changes: dict, message: str
) -> None:
    with pytest.raises(SectorDataValidationError, match=message):
        _ingest(
            SectorPersistenceService(database),
            bundle=build_sector_fixture(),
            metadata=_metadata(**changes),
        )
    with database() as session:
        assert session.scalar(select(func.count()).select_from(IngestionRun)) == 0
        assert session.scalar(select(func.count()).select_from(SectorDefinitionRecord)) == 0
        assert session.scalar(select(func.count()).select_from(SectorDailyRecord)) == 0


def test_failed_attempt_uses_the_same_fixed_metadata_contract(database) -> None:
    service = SectorPersistenceService(database)
    with pytest.raises(SectorDataValidationError, match="fixed sector allowlist"):
        _record_failed_attempt(service, _metadata(debug_dump="not allowed"))
    with database() as session:
        assert session.scalar(select(func.count()).select_from(IngestionRun)) == 0

    run_id = _record_failed_attempt(service, _metadata())
    with database() as session:
        run = session.get(IngestionRun, run_id)
        assert run is not None and run.status == "failed"
        assert set(run.provider_request_metadata) == SECTOR_PROVIDER_METADATA_FIELDS
        assert session.scalar(select(func.count()).select_from(SectorDefinitionRecord)) == 0
        assert session.scalar(select(func.count()).select_from(SectorDailyRecord)) == 0


@pytest.mark.parametrize(
    ("dataset", "mutation", "message"),
    [
        ("daily", lambda frame: frame.assign(close=float("nan")), "close must be finite"),
        ("daily", lambda frame: frame.assign(low=frame["high"] + 1), "OHLC values violate"),
        ("daily", lambda frame: frame.assign(turnover_rate=-1), "turnover_rate must be nonnegative"),
        ("daily", lambda frame: pd.concat([frame, frame.iloc[[0]]], ignore_index=True), "Duplicate sector"),
        ("definition", lambda frame: frame.assign(sector_name="  "), "sector_name must not be blank"),
        ("definition", lambda frame: pd.concat([frame, frame.iloc[[0]]], ignore_index=True), "exact scope"),
    ],
)
def test_invalid_sector_rows_roll_back_entire_snapshot(
    database, dataset: str, mutation, message: str
) -> None:
    original = build_sector_fixture()
    malformed = SectorMarketBundle(
        sector_definition=(
            mutation(original.sector_definition.copy())
            if dataset == "definition"
            else original.sector_definition.copy()
        ),
        sector_daily=(
            mutation(original.sector_daily.copy())
            if dataset == "daily"
            else original.sector_daily.copy()
        ),
    )
    with pytest.raises(SectorDataValidationError, match=message):
        _ingest(SectorPersistenceService(database), bundle=malformed)
    with database() as session:
        run = session.scalar(select(IngestionRun))
        assert run is not None and run.status == "failed"
        assert session.scalar(select(func.count()).select_from(SectorDefinitionRecord)) == 0
        assert session.scalar(select(func.count()).select_from(SectorDailyRecord)) == 0


def test_exact_scope_rejects_unexpected_or_name_only_identity(database) -> None:
    bundle = build_sector_fixture()
    definitions = bundle.sector_definition.copy()
    definitions.loc[0, "sector_code"] = definitions.loc[0, "sector_name"]
    malformed = SectorMarketBundle(definitions, bundle.sector_daily)
    with pytest.raises(SectorDataValidationError, match="stable Eastmoney BK"):
        _ingest(SectorPersistenceService(database), bundle=malformed)

    daily = bundle.sector_daily.loc[lambda frame: frame["sector_code"].eq("BK0001")].copy()
    with pytest.raises(SectorDataValidationError, match="exact scope"):
        _ingest(
            SectorPersistenceService(database),
            bundle=SectorMarketBundle(bundle.sector_definition, daily),
        )


def test_repeated_success_is_idempotent_and_records_one_physical_version(database) -> None:
    service = SectorPersistenceService(database)
    first = _ingest(service)
    second = _ingest(service)
    assert first.ingestion_run_id == second.ingestion_run_id
    assert first.rows_written == 132
    assert second.rows_written == 0
    assert second.idempotent is True
    with database() as session:
        assert session.scalar(select(func.count()).select_from(IngestionRun)) == 1
        assert session.scalar(select(func.count()).select_from(SectorDefinitionRecord)) == 2
        assert session.scalar(select(func.count()).select_from(SectorDailyRecord)) == 130


def test_repository_selects_one_current_or_historical_snapshot_without_stitching(database) -> None:
    service = SectorPersistenceService(database)
    historical = _ingest(
        service, revision="historical", cutoff=SECTOR_FIXTURE_HISTORICAL_CUTOFF
    )
    current = _ingest(service, revision="current", cutoff=SECTOR_FIXTURE_CURRENT_CUTOFF)
    assert historical.series_key == current.series_key
    with database() as session:
        repository = SectorRepository(session)
        selected_current = repository.load_snapshot(series_key=current.series_key)
        selected_historical = repository.load_snapshot(
            series_key=current.series_key,
            as_of_cutoff=SECTOR_FIXTURE_HISTORICAL_CUTOFF,
        )
    assert selected_current.ingestion_run_id == current.ingestion_run_id
    assert selected_historical.ingestion_run_id == historical.ingestion_run_id
    assert set(selected_current.sector_daily["ingestion_run_id"] if "ingestion_run_id" in selected_current.sector_daily else []) == set()
    current_last = selected_current.sector_daily.loc[
        selected_current.sector_daily["sector_code"].eq("BK0001"), "close"
    ].iloc[-1]
    historical_last = selected_historical.sector_daily.loc[
        selected_historical.sector_daily["sector_code"].eq("BK0001"), "close"
    ].iloc[-1]
    assert current_last != historical_last


def test_repository_fail_closed_for_missing_provider_only_or_incompatible_selector(database) -> None:
    result = _ingest(SectorPersistenceService(database))
    with database() as session:
        repository = SectorRepository(session)
        with pytest.raises(SectorSelectionError, match="explicit sector series_key"):
            repository.load_snapshot()
        with pytest.raises(SectorSnapshotNotFound, match="No successful complete sector snapshot"):
            repository.load_snapshot(series_key="f" * 64)
        selector = build_sector_series_identity(
            provider="fixture",
            sector_definition_contract_version="1.0",
            sector_daily_contract_version="1.0",
            sector_codes=SECTOR_FIXTURE_CODES,
            requested_start_date=SECTOR_FIXTURE_START_DATE,
            requested_end_date=SECTOR_FIXTURE_END_DATE,
            taxonomy_endpoint="changed_taxonomy",
            history_endpoint="fixture_sector_history",
            classification_system="eastmoney_industry_board",
            classification_level=None,
            adapter_compatibility_version="sector-fixture-v1",
        )
        with pytest.raises(SectorSnapshotNotFound):
            repository.load_snapshot(selector=selector)
        assert repository.load_snapshot(series_key=result.series_key).series_key == result.series_key


@pytest.mark.parametrize(
    ("model", "field", "value", "message"),
    [
        (SectorDefinitionRecord, "source", "other", "canonical provider"),
        (SectorDailyRecord, "source", "other", "canonical provider"),
        (SectorDefinitionRecord, "classification_system", "other", "canonical taxonomy"),
        (SectorDefinitionRecord, "classification_level", "level_1", "classification level"),
        (SectorDefinitionRecord, "sector_name", "", "blank display name"),
    ],
)
def test_repository_rejects_corrupted_provider_or_taxonomy_metadata(
    database, model, field: str, value, message: str
) -> None:
    result = _ingest(SectorPersistenceService(database))
    with database.begin() as session:
        row = session.scalar(select(model).where(model.ingestion_run_id == result.ingestion_run_id))
        assert row is not None
        setattr(row, field, value)
    with database() as session:
        with pytest.raises(SectorSelectionError, match=message):
            SectorRepository(session).load_snapshot(series_key=result.series_key)


def test_series_identity_isolates_every_normalized_compatibility_dimension() -> None:
    base = dict(
        provider="akshare",
        sector_definition_contract_version="1.0",
        sector_daily_contract_version="1.0",
        sector_codes=["BK0001", "BK0002"],
        requested_start_date="20260105",
        requested_end_date="20260403",
        taxonomy_endpoint="stock_board_industry_name_em",
        history_endpoint="stock_board_industry_hist_em",
        classification_system="eastmoney_industry_board",
        classification_level=None,
        adapter_compatibility_version=SECTOR_ENDPOINT_COMPATIBILITY_VERSION,
    )
    original = build_sector_series_identity(**base)
    changes = [
        {"provider": "fixture"},
        {"sector_codes": ["BK0001"]},
        {"requested_end_date": "20260402"},
        {"taxonomy_endpoint": "changed_taxonomy"},
        {"history_endpoint": "changed_history"},
        {"classification_system": "changed_taxonomy"},
        {"classification_level": "level_1"},
        {"sector_daily_contract_version": "2.0"},
        {
            "adapter_compatibility_version": (
                SECTOR_ENDPOINT_COMPATIBILITY_VERSION + ".next"
            )
        },
    ]
    assert all(
        build_sector_series_identity(**{**base, **change}).series_key != original.series_key
        for change in changes
    )
    operational_a = build_sector_series_identity(
        **base, compatibility_parameters={"normalized_unit_policy": "provider_native"}
    )
    operational_b = build_sector_series_identity(
        **base, compatibility_parameters={"normalized_unit_policy": "provider_native"}
    )
    assert operational_a.series_key == operational_b.series_key
