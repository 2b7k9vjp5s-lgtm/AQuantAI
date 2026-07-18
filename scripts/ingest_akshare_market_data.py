"""Manually collect one bounded AKShare snapshot or validate it without writes."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from backend.database.market_data import (
    MarketDataPersistenceService,
    validate_market_data_bundle,
)
from datasource.akshare import ADAPTER_VERSION, AkshareDataProvider
from datasource.akshare.provider import (
    MAX_STOCK_CODES_PER_REQUEST,
    RAW_AMOUNT,
    RAW_CLOSE,
    RAW_DATE,
    RAW_HIGH,
    RAW_LOW,
    RAW_OPEN,
    RAW_STOCK_CODE,
    RAW_VOLUME,
)
from datasource.base import AdjustType

AKSHARE_SCOPE_DATASETS = ["daily_price", "stock_basic", "trade_calendar"]
AKSHARE_COMPATIBILITY_PARAMETERS = {
    "frequency": "daily",
    "trade_calendar": "tool_trade_date_hist_sina",
}


@dataclass(frozen=True)
class AkshareIngestionRequest:
    stock_codes: tuple[str, ...]
    start_date: str
    end_date: str
    adjust_type: AdjustType
    information_cutoff_date: str
    allow_network: bool = False
    offline_fixture: bool = False
    dry_run: bool = False
    timeout_seconds: float = 20.0
    max_retries: int = 2


def run_controlled_akshare_ingestion(
    request: AkshareIngestionRequest,
    *,
    provider: AkshareDataProvider | None = None,
    session_factory: sessionmaker[Session] | None = None,
    database_url: str | None = None,
) -> dict[str, Any]:
    """Execute one explicit collection; no default path can access the network."""
    if request.allow_network and request.offline_fixture:
        raise ValueError("allow_network and offline_fixture are mutually exclusive.")
    if provider is None and not request.allow_network and not request.offline_fixture:
        raise ValueError("Network collection requires --allow-network; use --offline-fixture for local validation.")
    stock_codes = _stock_codes(request.stock_codes)
    start_date = _date(request.start_date, "start_date")
    end_date = _date(request.end_date, "end_date")
    cutoff_date = _date(request.information_cutoff_date, "cutoff")
    if start_date > end_date:
        raise ValueError("start_date must not be after end_date.")
    if end_date > cutoff_date:
        raise ValueError("end_date must not exceed cutoff.")
    if request.adjust_type not in ("", "qfq", "hfq"):
        raise ValueError("adjust_type must be '', 'qfq', or 'hfq'.")
    provider = provider or AkshareDataProvider(
        _FrozenAkshareClient() if request.offline_fixture else None,
        request_timeout_seconds=request.timeout_seconds,
        max_retries=request.max_retries,
    )
    network_mode = "live-opt-in" if request.allow_network else (
        "offline-fixture" if request.offline_fixture else "injected-mock"
    )
    scope = {
        "datasets": list(AKSHARE_SCOPE_DATASETS),
        "stock_codes": stock_codes,
    }
    request_metadata = provider.request_metadata(
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date,
        adjust=request.adjust_type,
        network_mode=network_mode,
    )

    engine = None
    if not request.dry_run and session_factory is None:
        engine = build_engine(database_url)
        session_factory = build_session_factory(engine)
    service = (
        MarketDataPersistenceService(session_factory)
        if not request.dry_run and session_factory is not None
        else None
    )
    try:
        try:
            bundle = provider.get_market_data_bundle(
                stock_codes,
                start_date,
                end_date,
                request.adjust_type,
            )
        except Exception as exc:
            if service is not None:
                service.record_failed_attempt(
                    exc,
                    provider=provider.source_name,
                    requested_start_date=start_date,
                    requested_end_date=end_date,
                    information_cutoff_date=cutoff_date,
                    requested_scope=scope,
                    adjust_type=request.adjust_type,
                    compatibility_parameters=AKSHARE_COMPATIBILITY_PARAMETERS,
                    provider_request_metadata=request_metadata,
                    adapter_version=ADAPTER_VERSION,
                )
            raise

        if request.dry_run:
            validation = validate_market_data_bundle(
                bundle,
                provider=provider.source_name,
                requested_start_date=start_date,
                requested_end_date=end_date,
                information_cutoff_date=cutoff_date,
                requested_scope=scope,
                adjust_type=request.adjust_type,
                compatibility_parameters=AKSHARE_COMPATIBILITY_PARAMETERS,
            )
            return {
                "mode": "dry-run",
                "network_mode": network_mode,
                **validation.to_dict(),
            }
        assert service is not None
        result = service.ingest_bundle(
            bundle,
            provider=provider.source_name,
            requested_start_date=start_date,
            requested_end_date=end_date,
            information_cutoff_date=cutoff_date,
            requested_scope=scope,
            adjust_type=request.adjust_type,
            compatibility_parameters=AKSHARE_COMPATIBILITY_PARAMETERS,
            provider_request_metadata=request_metadata,
            adapter_version=ADAPTER_VERSION,
        )
        return {
            "mode": "persist",
            "network_mode": network_mode,
            **result.to_dict(),
        }
    finally:
        if engine is not None:
            engine.dispose()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manually collect one bounded AKShare complete snapshot.",
    )
    parser.add_argument("--stock-code", action="append", required=True, dest="stock_codes")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--adjust", choices=("", "qfq", "hfq"), required=True)
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
    request = AkshareIngestionRequest(
        stock_codes=tuple(args.stock_codes),
        start_date=args.start_date,
        end_date=args.end_date,
        adjust_type=args.adjust,
        information_cutoff_date=args.information_cutoff_date,
        allow_network=args.allow_network,
        offline_fixture=args.offline_fixture,
        dry_run=args.dry_run,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
    )
    try:
        payload = run_controlled_akshare_ingestion(request)
    except Exception as exc:
        raise SystemExit(f"AKShare ingestion failed: {type(exc).__name__}: {str(exc).splitlines()[0]}") from exc
    print(json.dumps(payload, indent=2, sort_keys=True))


def _stock_codes(values: tuple[str, ...]) -> list[str]:
    normalized = sorted({str(value).strip() for value in values})
    if not normalized or len(normalized) != len(values):
        raise ValueError("At least one unique --stock-code is required.")
    if len(normalized) > MAX_STOCK_CODES_PER_REQUEST:
        raise ValueError(
            f"At most {MAX_STOCK_CODES_PER_REQUEST} --stock-code values are allowed per request."
        )
    if any(len(value) != 6 or not value.isdigit() for value in normalized):
        raise ValueError("Every --stock-code must be exactly six digits.")
    return normalized


def _date(value: str, field: str) -> str:
    normalized = str(value).strip().replace("-", "")
    try:
        return datetime.strptime(normalized, "%Y%m%d").strftime("%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"{field} must use YYYYMMDD format.") from exc


class _FrozenAkshareClient:
    """Small deterministic raw response set for offline CLI verification only."""

    def stock_info_a_code_name(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"code": "000001", "name": "Ping An Bank"},
                {"code": "600000", "name": "SPDB"},
            ]
        )

    def stock_zh_a_hist(
        self,
        symbol: str,
        period: str,
        start_date: str,
        end_date: str,
        adjust: str,
    ) -> pd.DataFrame:
        del period
        rows = [
            _raw_daily_row("2026-07-08", symbol, 10.0),
            _raw_daily_row("2026-07-09", symbol, 10.5),
        ]
        frame = pd.DataFrame(rows)
        compact_dates = pd.to_datetime(frame[RAW_DATE]).dt.strftime("%Y%m%d")
        return frame.loc[(compact_dates >= start_date) & (compact_dates <= end_date)].reset_index(drop=True)

    def tool_trade_date_hist_sina(self) -> pd.DataFrame:
        return pd.DataFrame([{"trade_date": "2026-07-08"}, {"trade_date": "2026-07-09"}])


def _raw_daily_row(trade_date: str, stock_code: str, open_price: float) -> dict[str, Any]:
    return {
        RAW_DATE: trade_date,
        RAW_STOCK_CODE: stock_code,
        RAW_OPEN: open_price,
        RAW_HIGH: open_price + 0.8,
        RAW_LOW: open_price - 0.1,
        RAW_CLOSE: open_price + 0.5,
        RAW_VOLUME: 1000.0,
        RAW_AMOUNT: 10500.0,
    }


if __name__ == "__main__":
    main()
