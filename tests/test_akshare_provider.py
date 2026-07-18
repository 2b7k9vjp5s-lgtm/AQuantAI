import pandas as pd
import pytest

from datasource.akshare import AkshareDataProvider
from datasource.akshare.provider import (
    RAW_AMOUNT,
    RAW_CLOSE,
    RAW_DATE,
    RAW_HIGH,
    RAW_LOW,
    RAW_OPEN,
    RAW_STOCK_CODE,
    RAW_VOLUME,
    AkshareProviderError,
    AkshareProviderTimeout,
)
from datasource.base import DAILY_PRICE_COLUMNS, STOCK_BASIC_COLUMNS, TRADE_CALENDAR_COLUMNS


class FakeAkshare:
    def __init__(self) -> None:
        self.daily_args: dict[str, str] = {}

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
        self.daily_args = {
            "symbol": symbol,
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "adjust": adjust,
        }
        return pd.DataFrame(
            [
                {
                    RAW_DATE: "2026-01-05",
                    RAW_STOCK_CODE: symbol,
                    RAW_OPEN: 10.0,
                    RAW_HIGH: 11.0,
                    RAW_LOW: 9.5,
                    RAW_CLOSE: 10.5,
                    RAW_VOLUME: 1000,
                    RAW_AMOUNT: 10500.0,
                }
            ]
        )

    def tool_trade_date_hist_sina(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"trade_date": "2026-01-03"},
                {"trade_date": "2026-01-05"},
                {"trade_date": "2026-01-06"},
            ]
        )


class EmptyAkshare(FakeAkshare):
    def stock_info_a_code_name(self) -> pd.DataFrame:
        return pd.DataFrame()

    def stock_zh_a_hist(
        self,
        symbol: str,
        period: str,
        start_date: str,
        end_date: str,
        adjust: str,
    ) -> pd.DataFrame:
        self.daily_args = {
            "symbol": symbol,
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "adjust": adjust,
        }
        return pd.DataFrame()

    def tool_trade_date_hist_sina(self) -> pd.DataFrame:
        return pd.DataFrame()


def test_stock_basic_returns_normalized_columns() -> None:
    provider = AkshareDataProvider(FakeAkshare())

    result = provider.get_stock_basic()

    assert list(result.columns) == STOCK_BASIC_COLUMNS
    assert result["source"].tolist() == ["akshare", "akshare"]
    assert "code" not in result.columns
    assert "name" not in result.columns


def test_daily_price_returns_normalized_columns_and_passes_parameters() -> None:
    fake = FakeAkshare()
    provider = AkshareDataProvider(fake)

    result = provider.get_daily_price("000001", "20260101", "20260131", "qfq")

    assert list(result.columns) == DAILY_PRICE_COLUMNS
    assert result.iloc[0]["trade_date"] == "20260105"
    assert result.iloc[0]["adjust_type"] == "qfq"
    assert fake.daily_args == {
        "symbol": "000001",
        "period": "daily",
        "start_date": "20260101",
        "end_date": "20260131",
        "adjust": "qfq",
    }
    assert not {RAW_DATE, RAW_OPEN, RAW_CLOSE, RAW_VOLUME} & set(result.columns)


def test_trade_calendar_returns_open_dates_in_range() -> None:
    provider = AkshareDataProvider(FakeAkshare())

    result = provider.get_trade_calendar("20260104", "20260105")

    assert list(result.columns) == TRADE_CALENDAR_COLUMNS
    assert result["trade_date"].tolist() == ["20260105"]
    assert result["is_open"].tolist() == [True]


def test_empty_provider_responses_return_expected_columns() -> None:
    provider = AkshareDataProvider(EmptyAkshare())

    assert list(provider.get_stock_basic().columns) == STOCK_BASIC_COLUMNS
    assert list(provider.get_daily_price("000001", "20260101", "20260131").columns) == DAILY_PRICE_COLUMNS
    assert list(provider.get_trade_calendar("20260101", "20260131").columns) == TRADE_CALENDAR_COLUMNS


class RaisingRunner:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    def call(self, _endpoint, _kwargs, _timeout_seconds):
        self.calls += 1
        raise self.error


def test_timeout_is_finite_retried_and_actionable() -> None:
    runner = RaisingRunner(AkshareProviderTimeout("bounded timeout"))
    provider = AkshareDataProvider(runner=runner, max_retries=1, sleep=lambda _seconds: None)

    with pytest.raises(AkshareProviderTimeout, match="bounded timeout"):
        provider.get_stock_basic()

    assert runner.calls == 2


def test_provider_exception_is_wrapped_after_finite_attempts() -> None:
    runner = RaisingRunner(RuntimeError("upstream unavailable"))
    provider = AkshareDataProvider(runner=runner, max_retries=2, sleep=lambda _seconds: None)

    with pytest.raises(AkshareProviderError, match="failed after 3 attempts"):
        provider.get_trade_calendar("20260101", "20260131")

    assert runner.calls == 3


class MalformedAkshare(FakeAkshare):
    def stock_zh_a_hist(self, **_kwargs) -> pd.DataFrame:
        return pd.DataFrame([{"unexpected": "payload"}])


def test_malformed_provider_payload_is_rejected_before_contract_mapping() -> None:
    provider = AkshareDataProvider(MalformedAkshare())

    with pytest.raises(AkshareProviderError, match="missing columns"):
        provider.get_daily_price("000001", "20260101", "20260131", "qfq")


def test_bundle_collection_rejects_near_full_market_code_lists() -> None:
    provider = AkshareDataProvider(FakeAkshare())

    with pytest.raises(AkshareProviderError, match="At most 50 stock codes"):
        provider.get_market_data_bundle(
            [f"{value:06d}" for value in range(51)],
            "20260101",
            "20260131",
            "qfq",
        )
