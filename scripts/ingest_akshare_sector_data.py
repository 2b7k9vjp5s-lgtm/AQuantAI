"""Manually ingest one bounded sector snapshot or validate it offline."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from backend.database.sector_data import (
    DEFAULT_SECTOR_ADAPTER_VERSION,
    DEFAULT_SECTOR_CLASSIFICATION_LEVEL,
    DEFAULT_SECTOR_CLASSIFICATION_SYSTEM,
    DEFAULT_SECTOR_HISTORY_ENDPOINT,
    DEFAULT_SECTOR_TAXONOMY_ENDPOINT,
    SECTOR_DAILY_CONTRACT_VERSION,
    SECTOR_DAILY_DATASET,
    SECTOR_DEFINITION_CONTRACT_VERSION,
    SECTOR_DEFINITION_DATASET,
    SectorPersistenceService,
    validate_sector_bundle,
)
from datasource.akshare import (
    ADAPTER_VERSION,
    MAX_SECTOR_CODES_PER_REQUEST,
    AkshareDataProvider,
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
)


@dataclass(frozen=True)
class SectorIngestionRequest:
    sector_codes: tuple[str, ...]
    start_date: str
    end_date: str
    information_cutoff_date: str
    allow_network: bool = False
    offline_fixture: bool = False
    dry_run: bool = False
    timeout_seconds: float = 20.0
    max_retries: int = 2


def run_controlled_sector_ingestion(
    request: SectorIngestionRequest,
    *,
    provider: AkshareDataProvider | None = None,
    session_factory: sessionmaker[Session] | None = None,
    database_url: str | None = None,
    clock: Callable[[], datetime] | None = None,
    engine_factory: Callable[[str | None], Engine] = build_engine,
) -> dict[str, Any]:
    """Execute one explicit stable-code sector collection with no implicit network."""
    if request.allow_network and request.offline_fixture:
        raise ValueError("allow_network and offline_fixture are mutually exclusive.")
    if provider is None and not request.allow_network and not request.offline_fixture:
        raise ValueError(
            "Sector collection requires --allow-network; use --offline-fixture for local validation."
        )
    codes = _sector_codes(request.sector_codes)
    start = _date(request.start_date, "start_date")
    end = _date(request.end_date, "end_date")
    cutoff = _date(request.information_cutoff_date, "cutoff")
    if start > end:
        raise ValueError("start_date must not be after end_date.")
    if end > cutoff:
        raise ValueError("end_date must not exceed cutoff.")
    collected_at = _collection_timestamp(clock)
    collection_date = collected_at.strftime("%Y%m%d")
    if request.allow_network and cutoff != collection_date:
        raise ValueError(
            "Live AKShare sector cutoff must equal the UTC collection date "
            f"{collection_date}; past and future live cutoffs are not permitted."
        )
    provider = provider or AkshareDataProvider(
        _FrozenSectorAkshareClient() if request.offline_fixture else None,
        request_timeout_seconds=request.timeout_seconds,
        max_retries=request.max_retries,
    )
    network_mode = (
        "live-opt-in"
        if request.allow_network
        else "offline-fixture"
        if request.offline_fixture
        else "injected-mock"
    )
    scope = {
        "datasets": [SECTOR_DEFINITION_DATASET, SECTOR_DAILY_DATASET],
        "sector_codes": codes,
        "sector_code_semantics": "exact",
        "classification_system": DEFAULT_SECTOR_CLASSIFICATION_SYSTEM,
        "classification_level": DEFAULT_SECTOR_CLASSIFICATION_LEVEL,
    }
    metadata = provider.sector_request_metadata(
        sector_codes=codes,
        start_date=start,
        end_date=end,
        network_mode=network_mode,
        definition_contract_version=SECTOR_DEFINITION_CONTRACT_VERSION,
        daily_contract_version=SECTOR_DAILY_CONTRACT_VERSION,
        adapter_compatibility_version=DEFAULT_SECTOR_ADAPTER_VERSION,
    )
    metadata.update({
        "collection_timestamp_utc": collected_at.isoformat().replace("+00:00", "Z"),
        "effective_information_cutoff_date": cutoff,
    })
    engine = None
    if not request.dry_run and session_factory is None:
        engine = engine_factory(database_url)
        session_factory = build_session_factory(engine)
    service = (
        SectorPersistenceService(session_factory)
        if not request.dry_run and session_factory is not None
        else None
    )
    try:
        try:
            bundle = provider.get_sector_market_bundle(codes, start, end)
        except Exception as exc:
            if service is not None:
                service.record_failed_attempt(
                    exc,
                    provider=provider.source_name,
                    requested_start_date=start,
                    requested_end_date=end,
                    information_cutoff_date=cutoff,
                    requested_scope=scope,
                    taxonomy_endpoint=DEFAULT_SECTOR_TAXONOMY_ENDPOINT,
                    history_endpoint=DEFAULT_SECTOR_HISTORY_ENDPOINT,
                    adapter_compatibility_version=DEFAULT_SECTOR_ADAPTER_VERSION,
                    provider_request_metadata=metadata,
                    adapter_version=ADAPTER_VERSION,
                )
            raise
        if request.dry_run:
            validation = validate_sector_bundle(
                bundle,
                provider=provider.source_name,
                requested_start_date=start,
                requested_end_date=end,
                information_cutoff_date=cutoff,
                requested_scope=scope,
                taxonomy_endpoint=DEFAULT_SECTOR_TAXONOMY_ENDPOINT,
                history_endpoint=DEFAULT_SECTOR_HISTORY_ENDPOINT,
                adapter_compatibility_version=DEFAULT_SECTOR_ADAPTER_VERSION,
            )
            return {"mode": "dry-run", "network_mode": network_mode, **validation.to_dict()}
        assert service is not None
        result = service.ingest_bundle(
            bundle,
            provider=provider.source_name,
            requested_start_date=start,
            requested_end_date=end,
            information_cutoff_date=cutoff,
            requested_scope=scope,
            taxonomy_endpoint=DEFAULT_SECTOR_TAXONOMY_ENDPOINT,
            history_endpoint=DEFAULT_SECTOR_HISTORY_ENDPOINT,
            adapter_compatibility_version=DEFAULT_SECTOR_ADAPTER_VERSION,
            provider_request_metadata=metadata,
            adapter_version=ADAPTER_VERSION,
        )
        return {"mode": "persist", "network_mode": network_mode, **result.to_dict()}
    finally:
        if engine is not None:
            engine.dispose()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manually collect one bounded AKShare sector complete snapshot."
    )
    parser.add_argument("--sector-code", action="append", required=True, dest="sector_codes")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--cutoff", required=True, dest="information_cutoff_date")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--allow-network", action="store_true")
    mode.add_argument("--offline-fixture", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--max-retries", type=int, default=2)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    request = SectorIngestionRequest(
        sector_codes=tuple(args.sector_codes),
        start_date=args.start_date,
        end_date=args.end_date,
        information_cutoff_date=args.information_cutoff_date,
        allow_network=args.allow_network,
        offline_fixture=args.offline_fixture,
        dry_run=args.dry_run,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
    )
    try:
        payload = run_controlled_sector_ingestion(request)
    except Exception as exc:
        raise SystemExit(
            f"AKShare sector ingestion failed: {type(exc).__name__}: {str(exc).splitlines()[0]}"
        ) from exc
    print(json.dumps(payload, indent=2, sort_keys=True))


def _sector_codes(values: tuple[str, ...]) -> list[str]:
    normalized = sorted({str(value).strip().upper() for value in values})
    if not normalized or len(normalized) != len(values):
        raise ValueError("At least one unique --sector-code is required.")
    if len(normalized) > MAX_SECTOR_CODES_PER_REQUEST:
        raise ValueError(
            f"At most {MAX_SECTOR_CODES_PER_REQUEST} --sector-code values are allowed."
        )
    if any(re.fullmatch(r"BK[0-9]+", value) is None for value in normalized):
        raise ValueError("Every --sector-code must be a stable Eastmoney BK identifier.")
    return normalized


def _date(value: str, field: str) -> str:
    normalized = str(value).strip().replace("-", "")
    try:
        return datetime.strptime(normalized, "%Y%m%d").strftime("%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"{field} must use YYYYMMDD format.") from exc


def _collection_timestamp(clock: Callable[[], datetime] | None) -> datetime:
    collected_at = (clock or (lambda: datetime.now(timezone.utc)))()
    if collected_at.tzinfo is None or collected_at.utcoffset() is None:
        raise ValueError("Collection clock must return a timezone-aware datetime.")
    return collected_at.astimezone(timezone.utc)


class _FrozenSectorAkshareClient:
    """Deterministic raw endpoint responses used only by offline validation."""

    def stock_board_industry_name_em(self) -> pd.DataFrame:
        return pd.DataFrame([
            {RAW_SECTOR_CODE: "BK0001", RAW_SECTOR_NAME: "Fixture Industry One"},
            {RAW_SECTOR_CODE: "BK0002", RAW_SECTOR_NAME: "Fixture Industry Two"},
        ])

    def stock_board_industry_hist_em(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str,
        adjust: str,
    ) -> pd.DataFrame:
        del period, adjust
        rows = []
        slope = 1.0 if symbol == "BK0001" else 0.5
        for index, trade_date in enumerate(pd.bdate_range("2026-01-05", periods=65)):
            close = 1000.0 + index * slope
            rows.append({
                RAW_DATE: trade_date.strftime("%Y-%m-%d"),
                RAW_OPEN: close - 1.0,
                RAW_HIGH: close + 2.0,
                RAW_LOW: close - 2.0,
                RAW_CLOSE: close,
                RAW_VOLUME: 100000.0 + index,
                RAW_AMOUNT: 100000000.0 + index * 1000,
                RAW_TURNOVER_RATE: 1.0 + index / 1000,
            })
        frame = pd.DataFrame(rows)
        compact = pd.to_datetime(frame[RAW_DATE]).dt.strftime("%Y%m%d")
        return frame.loc[(compact >= start_date) & (compact <= end_date)].reset_index(drop=True)


if __name__ == "__main__":
    main()
