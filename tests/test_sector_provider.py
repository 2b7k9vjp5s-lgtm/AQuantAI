from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone

import pandas as pd
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.engine import build_session_factory
from backend.database.models import Base, IngestionRun, SectorDailyRecord, SectorDefinitionRecord
from backend.database.sector_data import (
    DEFAULT_SECTOR_ADAPTER_COMPATIBILITY_VERSION,
    DEFAULT_SECTOR_REVIEWED_AKSHARE_VERSION,
    SECTOR_PROVIDER_METADATA_FIELDS,
)
from datasource.akshare import (
    SECTOR_ENDPOINT_COMPATIBILITY_VERSION,
    SECTOR_REVIEWED_AKSHARE_VERSION,
    AkshareDataProvider,
    AkshareProviderError,
    validate_akshare_runtime_version,
    validate_sector_akshare_runtime_version,
)
from datasource.akshare.provider import (
    RAW_AMOUNT,
    RAW_CLOSE,
    RAW_DATE,
    RAW_HIGH,
    RAW_LOW,
    RAW_OPEN,
    RAW_SECTOR_CODE,
    RAW_SECTOR_NAME,
    RAW_TURNOVER_RATE,
    RAW_VOLUME,
    SECTOR_HISTORY_ENDPOINT,
    SECTOR_TAXONOMY_ENDPOINT,
)
from scripts.ingest_akshare_sector_data import (
    SectorIngestionRequest,
    run_controlled_sector_ingestion,
)


class _SectorClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def stock_board_industry_name_em(self) -> pd.DataFrame:
        self.calls.append((SECTOR_TAXONOMY_ENDPOINT, {}))
        return pd.DataFrame([
            {RAW_SECTOR_CODE: "BK0002", RAW_SECTOR_NAME: "Industry Two"},
            {RAW_SECTOR_CODE: "BK0001", RAW_SECTOR_NAME: "Industry One"},
            {RAW_SECTOR_CODE: "BK9999", RAW_SECTOR_NAME: "Unrequested"},
        ])

    def stock_board_industry_hist_em(self, **kwargs) -> pd.DataFrame:
        self.calls.append((SECTOR_HISTORY_ENDPOINT, dict(kwargs)))
        close = 100.0 if kwargs["symbol"] == "BK0001" else 200.0
        return pd.DataFrame([
            {
                RAW_DATE: "2026-04-01",
                RAW_OPEN: close,
                RAW_HIGH: close + 1,
                RAW_LOW: close - 1,
                RAW_CLOSE: close,
                RAW_VOLUME: 1000,
                RAW_AMOUNT: 10000,
                RAW_TURNOVER_RATE: 1.2,
            },
            {
                RAW_DATE: "2026-04-02",
                RAW_OPEN: close + 1,
                RAW_HIGH: close + 2,
                RAW_LOW: close,
                RAW_CLOSE: close + 1,
                RAW_VOLUME: 1100,
                RAW_AMOUNT: 11000,
                RAW_TURNOVER_RATE: 1.3,
            },
        ])


@pytest.fixture
def database() -> Iterator[sessionmaker[Session]]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield build_session_factory(engine)
    engine.dispose()


def _request(**changes) -> SectorIngestionRequest:
    values = dict(
        sector_codes=("BK0001", "BK0002"),
        start_date="20260401",
        end_date="20260402",
        information_cutoff_date="20260405",
    )
    values.update(changes)
    return SectorIngestionRequest(**values)


def _provider(client=None, *, package_version: str = SECTOR_REVIEWED_AKSHARE_VERSION) -> AkshareDataProvider:
    return AkshareDataProvider(
        client or _SectorClient(),
        request_timeout_seconds=3,
        max_retries=1,
        retry_delay_seconds=0,
        akshare_package_version=package_version,
    )


def test_provider_uses_stable_codes_one_taxonomy_and_one_bounded_history_endpoint() -> None:
    client = _SectorClient()
    provider = _provider(client)
    bundle = provider.get_sector_market_bundle(
        ["BK0002", "BK0001"], "20260401", "20260402"
    )
    assert bundle.sector_definition["sector_code"].tolist() == ["BK0001", "BK0002"]
    assert bundle.sector_definition["sector_name"].tolist() == ["Industry One", "Industry Two"]
    assert bundle.sector_definition["classification_level"].isna().all()
    assert bundle.sector_daily["sector_code"].unique().tolist() == ["BK0001", "BK0002"]
    assert client.calls[0] == (SECTOR_TAXONOMY_ENDPOINT, {})
    history_calls = [kwargs for endpoint, kwargs in client.calls if endpoint == SECTOR_HISTORY_ENDPOINT]
    assert history_calls == [
        {"symbol": "BK0001", "start_date": "20260401", "end_date": "20260402", "period": "\u65e5k", "adjust": ""},
        {"symbol": "BK0002", "start_date": "20260401", "end_date": "20260402", "period": "\u65e5k", "adjust": ""},
    ]


def test_provider_rejects_missing_taxonomy_code_and_name_only_scope() -> None:
    provider = _provider()
    with pytest.raises(AkshareProviderError, match="stable Eastmoney BK"):
        provider.get_sector_market_bundle(["Industry One"], "20260401", "20260402")
    with pytest.raises(AkshareProviderError, match="did not contain requested codes"):
        provider.get_sector_market_bundle(["BK4040"], "20260401", "20260402")


def test_request_metadata_records_endpoints_version_and_operational_settings() -> None:
    metadata = _provider().sector_request_metadata(
        sector_codes=["BK0002", "BK0001"],
        start_date="20260401",
        end_date="20260402",
        network_mode="injected-mock",
        definition_contract_version="1.0",
        daily_contract_version="1.0",
        adapter_compatibility_version=SECTOR_ENDPOINT_COMPATIBILITY_VERSION,
    )
    assert metadata["taxonomy_endpoint"] == SECTOR_TAXONOMY_ENDPOINT
    assert metadata["history_endpoint"] == SECTOR_HISTORY_ENDPOINT
    assert metadata["sector_codes"] == ["BK0001", "BK0002"]
    assert metadata["akshare_package_version"] == "1.18.64"
    assert metadata["timeout_seconds"] == 3
    assert metadata["max_retries"] == 1


def test_sector_endpoint_compatibility_gate_is_exact_and_generic_gate_is_unchanged() -> None:
    assert (
        DEFAULT_SECTOR_ADAPTER_COMPATIBILITY_VERSION
        == SECTOR_ENDPOINT_COMPATIBILITY_VERSION
    )
    assert DEFAULT_SECTOR_REVIEWED_AKSHARE_VERSION == SECTOR_REVIEWED_AKSHARE_VERSION
    assert validate_sector_akshare_runtime_version("1.18.64") == "1.18.64"
    assert validate_akshare_runtime_version("1.17.0") == "1.17.0"
    for unsupported in ("1.17.0", "1.18.63", "1.18.65", "1.15.9", "2.0.0", "bad"):
        with pytest.raises(
            AkshareProviderError,
            match="reviewed sector endpoint contract; accepted version: 1.18.64",
        ):
            validate_sector_akshare_runtime_version(unsupported)

    with pytest.raises(AkshareProviderError, match="must equal the reviewed endpoint contract"):
        _provider().sector_request_metadata(
            sector_codes=["BK0001"],
            start_date="20260401",
            end_date="20260402",
            network_mode="injected-mock",
            definition_contract_version="1.0",
            daily_contract_version="1.0",
            adapter_compatibility_version="unreviewed-sector-contract",
        )


def test_generically_allowed_unreviewed_sector_version_fails_before_calls_or_engine() -> None:
    client = _SectorClient()
    provider = _provider(client, package_version="1.17.0")
    engine_calls: list[bool] = []

    def reject_engine(_url):
        engine_calls.append(True)
        raise AssertionError("engine must not be created")

    with pytest.raises(AkshareProviderError, match="accepted version: 1.18.64"):
        run_controlled_sector_ingestion(
            _request(), provider=provider, engine_factory=reject_engine
        )
    assert client.calls == []
    assert engine_calls == []


def test_live_cutoff_is_rejected_before_provider_or_engine_creation() -> None:
    engine_calls = []

    def reject_engine(_url):
        engine_calls.append(True)
        raise AssertionError("engine must not be created")

    with pytest.raises(ValueError, match="must equal the UTC collection date"):
        run_controlled_sector_ingestion(
            _request(allow_network=True, information_cutoff_date="20260405"),
            clock=lambda: datetime(2026, 7, 18, 1, tzinfo=timezone.utc),
            engine_factory=reject_engine,
        )
    assert engine_calls == []


def test_offline_dry_run_creates_no_engine_or_rows() -> None:
    def reject_engine(_url):
        raise AssertionError("dry-run must not create an engine")

    payload = run_controlled_sector_ingestion(
        SectorIngestionRequest(
            sector_codes=("BK0001", "BK0002"),
            start_date="20260105",
            end_date="20260403",
            information_cutoff_date="20260405",
            offline_fixture=True,
            dry_run=True,
        ),
        clock=lambda: datetime(2026, 4, 5, 12, tzinfo=timezone.utc),
        engine_factory=reject_engine,
    )
    assert payload["mode"] == "dry-run"
    assert payload["network_mode"] == "offline-fixture"
    assert payload["dataset_counts"] == {"sector_definition": 2, "sector_daily": 130}


def test_injected_persistence_is_idempotent_and_failure_preserves_audit(database) -> None:
    provider = _provider()
    first = run_controlled_sector_ingestion(
        _request(), provider=provider, session_factory=database,
        clock=lambda: datetime(2026, 4, 5, 12, tzinfo=timezone.utc),
    )
    second = run_controlled_sector_ingestion(
        _request(), provider=_provider(), session_factory=database,
        clock=lambda: datetime(2026, 4, 5, 12, tzinfo=timezone.utc),
    )
    assert first["ingestion_run_id"] == second["ingestion_run_id"]
    assert second["idempotent"] is True and second["rows_written"] == 0
    with database() as session:
        succeeded = session.get(IngestionRun, first["ingestion_run_id"])
        assert succeeded is not None
        assert set(succeeded.provider_request_metadata) == SECTOR_PROVIDER_METADATA_FIELDS
        assert succeeded.provider_request_metadata["akshare_package_version"] == "1.18.64"
        assert succeeded.provider_request_metadata["adapter_compatibility_version"] == (
            SECTOR_ENDPOINT_COMPATIBILITY_VERSION
        )

    class BrokenClient(_SectorClient):
        def stock_board_industry_name_em(self) -> pd.DataFrame:
            raise RuntimeError("fixture taxonomy failure")

    with pytest.raises(AkshareProviderError, match="fixture taxonomy failure"):
        run_controlled_sector_ingestion(
            _request(), provider=_provider(BrokenClient()), session_factory=database,
            clock=lambda: datetime(2026, 4, 5, 12, tzinfo=timezone.utc),
        )
    with database() as session:
        assert session.scalar(select(func.count()).select_from(SectorDefinitionRecord)) == 2
        assert session.scalar(select(func.count()).select_from(SectorDailyRecord)) == 4
        failed = session.scalars(select(IngestionRun).where(IngestionRun.status == "failed")).all()
        assert len(failed) == 1
        assert "fixture taxonomy failure" in (failed[0].error_summary or "")


def test_scope_limit_and_retry_are_bounded() -> None:
    too_many = tuple(f"BK{index:04d}" for index in range(31))
    with pytest.raises(ValueError, match="At most 30"):
        run_controlled_sector_ingestion(
            _request(sector_codes=too_many, dry_run=True), provider=_provider()
        )

    class FailingRunner:
        def __init__(self) -> None:
            self.calls = 0

        def call(self, endpoint, kwargs, timeout_seconds):
            del endpoint, kwargs, timeout_seconds
            self.calls += 1
            raise RuntimeError("bounded failure")

    runner = FailingRunner()
    provider = AkshareDataProvider(
        runner=runner,
        request_timeout_seconds=1,
        max_retries=2,
        retry_delay_seconds=0,
        akshare_package_version="1.18.64",
    )
    with pytest.raises(AkshareProviderError, match="after 3 attempts"):
        provider.get_sector_market_bundle(["BK0001"], "20260401", "20260402")
    assert runner.calls == 3
