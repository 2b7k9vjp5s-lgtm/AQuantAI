import numpy as np
import pandas as pd
import pytest

from factors import FACTOR_VALUE_COLUMNS
from factors.growth import NetProfitGrowthCalculator, RevenueGrowthCalculator
from factors.momentum import Return20DCalculator, Return60DCalculator
from factors.quality import GrossMarginCalculator, RoeCalculator
from factors.risk import MaxDrawdown60DCalculator, Volatility20DCalculator
from factors.value import PbInverseCalculator, PeInverseCalculator


def test_value_growth_quality_outputs_use_normalized_columns() -> None:
    data = pd.DataFrame(
        [
            {
                "factor_date": "20260630",
                "stock_code": "000001",
                "pe": 10.0,
                "pb": 2.0,
                "revenue": 120.0,
                "revenue_prev": 100.0,
                "net_profit": 22.0,
                "net_profit_prev": 20.0,
                "equity": 110.0,
                "gross_profit": 36.0,
            }
        ]
    )

    calculators = [
        PeInverseCalculator(),
        PbInverseCalculator(),
        RevenueGrowthCalculator(),
        NetProfitGrowthCalculator(),
        RoeCalculator(),
        GrossMarginCalculator(),
    ]

    results = [calculator.calculate(data).values for calculator in calculators]

    for result in results:
        assert list(result.columns) == FACTOR_VALUE_COLUMNS
        assert result.iloc[0]["factor_date"] == "20260630"
        assert result.iloc[0]["stock_code"] == "000001"
    assert results[0].iloc[0]["factor_value"] == pytest.approx(0.1)
    assert results[2].iloc[0]["factor_value"] == pytest.approx(0.2)
    assert results[4].iloc[0]["factor_value"] == pytest.approx(0.2)


def test_price_based_factors_use_latest_trade_date() -> None:
    rows = []
    for stock_code, start_price in [("000001", 10.0), ("000002", 20.0)]:
        for index in range(65):
            rows.append(
                {
                    "trade_date": f"202601{index + 1:02d}",
                    "stock_code": stock_code,
                    "close": start_price + index,
                }
            )
    prices = pd.DataFrame(rows)

    calculators = [
        Return20DCalculator(),
        Return60DCalculator(),
        Volatility20DCalculator(),
        MaxDrawdown60DCalculator(),
    ]

    results = [calculator.calculate(prices).values for calculator in calculators]

    for result in results:
        assert list(result.columns) == FACTOR_VALUE_COLUMNS
        assert set(result["stock_code"]) == {"000001", "000002"}
        assert set(result["factor_date"]) == {"20260165"}
    assert results[0]["factor_value"].notna().all()
    assert results[2]["factor_value"].notna().all()


def test_factor_calculator_rejects_missing_required_columns() -> None:
    data = pd.DataFrame([{"factor_date": "20260630", "stock_code": "000001"}])

    with pytest.raises(ValueError, match="Missing required factor input columns"):
        PeInverseCalculator().calculate(data)


def test_invalid_denominators_become_missing_values() -> None:
    data = pd.DataFrame(
        [
            {"factor_date": "20260630", "stock_code": "000001", "pe": 0.0},
            {"factor_date": "20260630", "stock_code": "000002", "pe": -1.0},
        ]
    )

    result = PeInverseCalculator().calculate(data).values

    assert np.isnan(result["factor_value"]).all()
