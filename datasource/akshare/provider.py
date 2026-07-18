"""AKShare-backed data provider with normalized AQuantAI contracts."""

from __future__ import annotations

import multiprocessing
import re
import time
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import pandas as pd

from datasource.base import (
    DAILY_PRICE_COLUMNS,
    STOCK_BASIC_COLUMNS,
    TRADE_CALENDAR_COLUMNS,
    AdjustType,
    DataProvider,
    MarketDataBundle,
)

ADAPTER_VERSION = "akshare-normalizer-v1"
ADAPTER_COMPATIBILITY_VERSION = "aquantai.akshare-adapter.v1"
STOCK_BASIC_ENDPOINT = "stock_info_a_code_name"
DAILY_PRICE_ENDPOINT = "stock_zh_a_hist"
TRADE_CALENDAR_ENDPOINT = "tool_trade_date_hist_sina"
ALLOWED_ENDPOINTS = {STOCK_BASIC_ENDPOINT, DAILY_PRICE_ENDPOINT, TRADE_CALENDAR_ENDPOINT}
MAX_STOCK_CODES_PER_REQUEST = 50
MIN_AKSHARE_VERSION = (1, 16, 0)
MAX_AKSHARE_VERSION_EXCLUSIVE = (2, 0, 0)

RAW_CODE = "\u4ee3\u7801"
RAW_NAME = "\u540d\u79f0"
RAW_DATE = "\u65e5\u671f"
RAW_STOCK_CODE = "\u80a1\u7968\u4ee3\u7801"
RAW_OPEN = "\u5f00\u76d8"
RAW_HIGH = "\u6700\u9ad8"
RAW_LOW = "\u6700\u4f4e"
RAW_CLOSE = "\u6536\u76d8"
RAW_VOLUME = "\u6210\u4ea4\u91cf"
RAW_AMOUNT = "\u6210\u4ea4\u989d"


class AkshareProviderError(RuntimeError):
    """Raised when a bounded AKShare request or response cannot be used."""


class AkshareProviderTimeout(AkshareProviderError):
    """Raised when a live endpoint exceeds its configured hard timeout."""


def installed_akshare_version() -> str:
    """Return the installed, reviewed-compatible AKShare package version."""
    try:
        package_version = version("akshare")
    except PackageNotFoundError as exc:
        raise AkshareProviderError(
            "AKShare is not installed. Install the project dependencies before manual collection."
        ) from exc
    return validate_akshare_runtime_version(package_version)


def validate_akshare_runtime_version(package_version: str) -> str:
    """Fail closed outside the AKShare major/minor range reviewed by this adapter."""
    normalized = str(package_version).strip()
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", normalized)
    if match is None:
        raise AkshareProviderError(
            f"Unsupported AKShare version {normalized!r}; expected a semantic version in [1.16.0, 2.0.0)."
        )
    parsed = tuple(int(value) for value in match.groups())
    if not MIN_AKSHARE_VERSION <= parsed < MAX_AKSHARE_VERSION_EXCLUSIVE:
        raise AkshareProviderError(
            f"Unsupported AKShare version {normalized!r}; this adapter supports [1.16.0, 2.0.0)."
        )
    return normalized


class _ClientRunner:
    def __init__(self, client: Any) -> None:
        self._client = client

    def call(self, endpoint: str, kwargs: dict[str, Any], _timeout_seconds: float) -> Any:
        return getattr(self._client, endpoint)(**kwargs)


class SubprocessAkshareRunner:
    """Run each live AKShare call in a process that can be terminated on timeout."""

    def call(self, endpoint: str, kwargs: dict[str, Any], timeout_seconds: float) -> Any:
        if endpoint not in ALLOWED_ENDPOINTS:
            raise AkshareProviderError(f"AKShare endpoint {endpoint!r} is not authorized.")
        context = multiprocessing.get_context("spawn")
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(target=_akshare_subprocess_worker, args=(sender, endpoint, kwargs))
        process.daemon = True
        process.start()
        sender.close()
        try:
            if not receiver.poll(timeout_seconds):
                process.terminate()
                process.join(timeout=2)
                raise AkshareProviderTimeout(
                    f"AKShare endpoint {endpoint} exceeded {timeout_seconds:g} seconds. "
                    "Retry later or reduce the requested date/code scope."
                )
            status, payload = receiver.recv()
        finally:
            receiver.close()
            process.join(timeout=2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
        if status == "error":
            raise AkshareProviderError(f"AKShare endpoint {endpoint} failed: {payload}")
        return payload


def _akshare_subprocess_worker(sender: Any, endpoint: str, kwargs: dict[str, Any]) -> None:
    try:
        import akshare as akshare_client

        result = getattr(akshare_client, endpoint)(**kwargs)
        sender.send(("ok", result))
    except Exception as exc:
        sender.send(("error", f"{type(exc).__name__}: {str(exc).splitlines()[0]}"))
    finally:
        sender.close()


class AkshareDataProvider(DataProvider):
    """Wrap AKShare calls and return stable internal column names."""

    source_name = "akshare"

    def __init__(
        self,
        akshare_client: Any | None = None,
        *,
        runner: Any | None = None,
        request_timeout_seconds: float = 20.0,
        max_retries: int = 2,
        retry_delay_seconds: float = 0.25,
        sleep: Callable[[float], None] = time.sleep,
        akshare_package_version: str | None = None,
    ) -> None:
        if akshare_client is not None and runner is not None:
            raise ValueError("Provide akshare_client or runner, not both.")
        if not 0 < request_timeout_seconds <= 120:
            raise ValueError("request_timeout_seconds must be in (0, 120].")
        if not 0 <= max_retries <= 5:
            raise ValueError("max_retries must be between 0 and 5.")
        if not 0 <= retry_delay_seconds <= 10:
            raise ValueError("retry_delay_seconds must be between 0 and 10.")
        self._akshare = akshare_client
        self._runner = runner or (_ClientRunner(akshare_client) if akshare_client is not None else SubprocessAkshareRunner())
        self.request_timeout_seconds = float(request_timeout_seconds)
        self.max_retries = max_retries
        self.retry_delay_seconds = float(retry_delay_seconds)
        self._sleep = sleep
        self.akshare_package_version = (
            validate_akshare_runtime_version(akshare_package_version)
            if akshare_package_version is not None
            else installed_akshare_version()
        )

    @property
    def akshare(self) -> Any:
        if self._akshare is None:
            import akshare as akshare_client

            self._akshare = akshare_client
        return self._akshare

    def get_stock_basic(self) -> pd.DataFrame:
        """Return normalized A-share stock identity data."""
        raw = self._call(STOCK_BASIC_ENDPOINT)
        _require_frame(raw, STOCK_BASIC_ENDPOINT)
        if raw.empty:
            return _empty_frame(STOCK_BASIC_COLUMNS)

        frame = raw.rename(
            columns={
                "code": "stock_code",
                "name": "stock_name",
                RAW_CODE: "stock_code",
                RAW_NAME: "stock_name",
            }
        )
        _require_columns(frame, ["stock_code", "stock_name"], STOCK_BASIC_ENDPOINT)
        frame = _ensure_columns(
            frame,
            STOCK_BASIC_COLUMNS,
            defaults={
                "exchange": "",
                "industry": "",
                "listing_date": pd.NA,
                "status": "active",
                "source": self.source_name,
            },
        )
        frame["stock_code"] = frame["stock_code"].astype(str)
        return frame[STOCK_BASIC_COLUMNS]

    def get_daily_price(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: AdjustType = "",
    ) -> pd.DataFrame:
        """Return normalized daily prices for one A-share symbol."""
        raw = self._call(
            DAILY_PRICE_ENDPOINT,
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        _require_frame(raw, DAILY_PRICE_ENDPOINT)
        if raw.empty:
            return _empty_frame(DAILY_PRICE_COLUMNS)

        frame = raw.rename(
            columns={
                RAW_DATE: "trade_date",
                RAW_STOCK_CODE: "stock_code",
                RAW_CODE: "stock_code",
                RAW_OPEN: "open",
                RAW_HIGH: "high",
                RAW_LOW: "low",
                RAW_CLOSE: "close",
                RAW_VOLUME: "volume",
                RAW_AMOUNT: "amount",
            }
        )
        _require_columns(
            frame,
            ["trade_date", "open", "high", "low", "close", "volume", "amount"],
            DAILY_PRICE_ENDPOINT,
        )
        frame = _ensure_columns(
            frame,
            DAILY_PRICE_COLUMNS,
            defaults={
                "stock_code": symbol,
                "adjust_type": adjust,
                "source": self.source_name,
            },
        )
        frame["stock_code"] = frame["stock_code"].astype(str)
        frame["trade_date"] = _normalize_date(frame["trade_date"])
        return frame[DAILY_PRICE_COLUMNS]

    def get_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Return normalized open trading dates within the requested range."""
        raw = self._call(TRADE_CALENDAR_ENDPOINT)
        _require_frame(raw, TRADE_CALENDAR_ENDPOINT)
        if raw.empty:
            return _empty_frame(TRADE_CALENDAR_COLUMNS)

        frame = raw.rename(columns={"trade_date": "trade_date", RAW_DATE: "trade_date"})
        _require_columns(frame, ["trade_date"], TRADE_CALENDAR_ENDPOINT)
        frame = _ensure_columns(
            frame,
            TRADE_CALENDAR_COLUMNS,
            defaults={"is_open": True, "source": self.source_name},
        )
        frame["trade_date"] = _normalize_date(frame["trade_date"])
        frame = frame[
            (frame["trade_date"] >= _compact_date(start_date))
            & (frame["trade_date"] <= _compact_date(end_date))
        ]
        return frame[TRADE_CALENDAR_COLUMNS]

    def get_market_data_bundle(
        self,
        stock_codes: list[str],
        start_date: str,
        end_date: str,
        adjust: AdjustType,
    ) -> MarketDataBundle:
        """Collect one explicit, bounded complete snapshot using existing contracts."""
        normalized_codes = sorted({str(value).strip() for value in stock_codes})
        if not normalized_codes or len(normalized_codes) != len(stock_codes):
            raise AkshareProviderError("stock_codes must be a non-empty list without duplicates.")
        if len(normalized_codes) > MAX_STOCK_CODES_PER_REQUEST:
            raise AkshareProviderError(
                f"At most {MAX_STOCK_CODES_PER_REQUEST} stock codes are allowed per manual request."
            )
        stock_basic = self.get_stock_basic()
        stock_basic = stock_basic.loc[stock_basic["stock_code"].isin(normalized_codes)].copy()
        missing_codes = sorted(set(normalized_codes) - set(stock_basic["stock_code"]))
        if missing_codes:
            raise AkshareProviderError(
                f"AKShare stock basic response did not contain requested codes: {missing_codes}."
            )
        daily_frames = [
            self.get_daily_price(code, start_date, end_date, adjust)
            for code in normalized_codes
        ]
        daily_price = pd.concat(daily_frames, ignore_index=True) if daily_frames else _empty_frame(DAILY_PRICE_COLUMNS)
        trade_calendar = self.get_trade_calendar(start_date, end_date)
        return MarketDataBundle(
            stock_basic=stock_basic.reset_index(drop=True),
            daily_price=daily_price.reset_index(drop=True),
            trade_calendar=trade_calendar.reset_index(drop=True),
        )

    def request_metadata(
        self,
        *,
        stock_codes: list[str],
        start_date: str,
        end_date: str,
        adjust: AdjustType,
        network_mode: str,
    ) -> dict[str, Any]:
        return {
            "adapter_version": ADAPTER_VERSION,
            "akshare_package_version": self.akshare_package_version,
            "endpoints": [STOCK_BASIC_ENDPOINT, DAILY_PRICE_ENDPOINT, TRADE_CALENDAR_ENDPOINT],
            "stock_codes": sorted(stock_codes),
            "start_date": _compact_date(start_date),
            "end_date": _compact_date(end_date),
            "adjust_type": adjust,
            "period": "daily",
            "network_mode": network_mode,
            "timeout_seconds": self.request_timeout_seconds,
            "max_retries": self.max_retries,
        }

    def _call(self, endpoint: str, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self._runner.call(endpoint, kwargs, self.request_timeout_seconds)
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    self._sleep(self.retry_delay_seconds)
        assert last_error is not None
        if isinstance(last_error, AkshareProviderError):
            raise last_error
        raise AkshareProviderError(
            f"AKShare endpoint {endpoint} failed after {self.max_retries + 1} attempts: "
            f"{type(last_error).__name__}: {str(last_error).splitlines()[0]}"
        ) from last_error


def _empty_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _ensure_columns(
    frame: pd.DataFrame,
    columns: list[str],
    defaults: dict[str, Any],
) -> pd.DataFrame:
    normalized = frame.copy()
    for column in columns:
        if column not in normalized.columns:
            normalized[column] = defaults.get(column, pd.NA)
    return normalized


def _require_frame(value: Any, endpoint: str) -> None:
    if not isinstance(value, pd.DataFrame):
        raise AkshareProviderError(f"AKShare endpoint {endpoint} returned a non-DataFrame payload.")


def _require_columns(frame: pd.DataFrame, columns: list[str], endpoint: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise AkshareProviderError(f"AKShare endpoint {endpoint} response is missing columns: {missing}.")


def _normalize_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.strftime("%Y%m%d")


def _compact_date(value: str) -> str:
    return value.replace("-", "")
