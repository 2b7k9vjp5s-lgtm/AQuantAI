"""Manually ingest one bounded benchmark-index snapshot or validate it offline."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from backend.database.benchmark_data import (
    BENCHMARK_CONTRACT_VERSION,
    BENCHMARK_DATASET,
    DEFAULT_BENCHMARK_ADAPTER_VERSION,
    BenchmarkPersistenceService,
    validate_benchmark_bundle,
)
from datasource.akshare import (
    ADAPTER_VERSION,
    BENCHMARK_INDEX_ENDPOINT,
    MAX_BENCHMARK_CODES_PER_REQUEST,
    AkshareDataProvider,
)
from datasource.akshare.provider import (
    RAW_AMOUNT,
    RAW_CLOSE,
    RAW_DATE,
    RAW_HIGH,
    RAW_LOW,
    RAW_OPEN,
    RAW_VOLUME,
)


@dataclass(frozen=True)
class BenchmarkIngestionRequest:
    index_codes: tuple[str, ...]
    start_date: str
    end_date: str
    information_cutoff_date: str
    allow_network: bool = False
    offline_fixture: bool = False
    dry_run: bool = False
    timeout_seconds: float = 20.0
    max_retries: int = 2


def run_controlled_benchmark_ingestion(
    request: BenchmarkIngestionRequest,
    *,
    provider: AkshareDataProvider | None = None,
    session_factory: sessionmaker[Session] | None = None,
    database_url: str | None = None,
    clock: Callable[[], datetime] | None = None,
    engine_factory: Callable[[str | None], Engine] = build_engine,
) -> dict[str, Any]:
    """Execute one explicit benchmark collection with no implicit network path."""
    if request.allow_network and request.offline_fixture:
        raise ValueError("allow_network and offline_fixture are mutually exclusive.")
    if provider is None and not request.allow_network and not request.offline_fixture:
        raise ValueError(
            "Benchmark collection requires --allow-network; use --offline-fixture for local validation."
        )
    codes = _index_codes(request.index_codes)
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
            "Live AKShare benchmark cutoff must equal the UTC collection date "
            f"{collection_date}; past and future live cutoffs are not permitted."
        )
    provider = provider or AkshareDataProvider(
        _FrozenBenchmarkAkshareClient() if request.offline_fixture else None,
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
        "datasets": [BENCHMARK_DATASET],
        "index_codes": codes,
        "index_code_semantics": "exact",
    }
    metadata = provider.benchmark_request_metadata(
        index_codes=codes,
        start_date=start,
        end_date=end,
        network_mode=network_mode,
        contract_version=BENCHMARK_CONTRACT_VERSION,
        adapter_compatibility_version=DEFAULT_BENCHMARK_ADAPTER_VERSION,
    )
    metadata.update(
        {
            "collection_timestamp_utc": collected_at.isoformat().replace("+00:00", "Z"),
            "effective_information_cutoff_date": cutoff,
        }
    )
    engine = None
    if not request.dry_run and session_factory is None:
        engine = engine_factory(database_url)
        session_factory = build_session_factory(engine)
    service = (
        BenchmarkPersistenceService(session_factory)
        if not request.dry_run and session_factory is not None
        else None
    )
    try:
        try:
            bundle = provider.get_benchmark_index_daily(codes, start, end)
        except Exception as exc:
            if service is not None:
                service.record_failed_attempt(
                    exc,
                    provider=provider.source_name,
                    requested_start_date=start,
                    requested_end_date=end,
                    information_cutoff_date=cutoff,
                    requested_scope=scope,
                    endpoint=BENCHMARK_INDEX_ENDPOINT,
                    adapter_compatibility_version=DEFAULT_BENCHMARK_ADAPTER_VERSION,
                    provider_request_metadata=metadata,
                    adapter_version=ADAPTER_VERSION,
                )
            raise
        if request.dry_run:
            validation = validate_benchmark_bundle(
                bundle,
                provider=provider.source_name,
                requested_start_date=start,
                requested_end_date=end,
                information_cutoff_date=cutoff,
                requested_scope=scope,
                endpoint=BENCHMARK_INDEX_ENDPOINT,
                adapter_compatibility_version=DEFAULT_BENCHMARK_ADAPTER_VERSION,
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
            endpoint=BENCHMARK_INDEX_ENDPOINT,
            adapter_compatibility_version=DEFAULT_BENCHMARK_ADAPTER_VERSION,
            provider_request_metadata=metadata,
            adapter_version=ADAPTER_VERSION,
        )
        return {"mode": "persist", "network_mode": network_mode, **result.to_dict()}
    finally:
        if engine is not None:
            engine.dispose()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manually collect one bounded AKShare benchmark-index complete snapshot."
    )
    parser.add_argument("--index-code", action="append", required=True, dest="index_codes")
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
    request = BenchmarkIngestionRequest(
        index_codes=tuple(args.index_codes),
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
        payload = run_controlled_benchmark_ingestion(request)
    except Exception as exc:
        raise SystemExit(
            f"AKShare benchmark ingestion failed: {type(exc).__name__}: {str(exc).splitlines()[0]}"
        ) from exc
    print(json.dumps(payload, indent=2, sort_keys=True))


def _index_codes(values: tuple[str, ...]) -> list[str]:
    normalized = sorted({str(value).strip() for value in values})
    if not normalized or len(normalized) != len(values):
        raise ValueError("At least one unique --index-code is required.")
    if len(normalized) > MAX_BENCHMARK_CODES_PER_REQUEST:
        raise ValueError(
            f"At most {MAX_BENCHMARK_CODES_PER_REQUEST} --index-code values are allowed."
        )
    if any(len(value) != 6 or not value.isdigit() for value in normalized):
        raise ValueError("Every --index-code must be exactly six digits.")
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


class _FrozenBenchmarkAkshareClient:
    """Deterministic raw endpoint response used only for offline CLI validation."""

    def index_zh_a_hist(
        self,
        symbol: str,
        period: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        del period
        rows = []
        for index, trade_date in enumerate(pd.bdate_range("2026-01-05", periods=65)):
            close = 1000.0 + index * (1.0 if symbol == "000001" else 0.5)
            rows.append(
                {
                    RAW_DATE: trade_date.strftime("%Y-%m-%d"),
                    RAW_OPEN: close - 1.0,
                    RAW_HIGH: close + 2.0,
                    RAW_LOW: close - 2.0,
                    RAW_CLOSE: close,
                    RAW_VOLUME: 100000.0 + index,
                    RAW_AMOUNT: 100000000.0 + index * 1000,
                }
            )
        frame = pd.DataFrame(rows)
        compact = pd.to_datetime(frame[RAW_DATE]).dt.strftime("%Y%m%d")
        return frame.loc[(compact >= start_date) & (compact <= end_date)].reset_index(drop=True)


if __name__ == "__main__":
    main()
