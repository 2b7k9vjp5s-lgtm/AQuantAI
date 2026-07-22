from datetime import date
from decimal import Decimal

from industry_alpha.normalized_expectation_rules import (
    calculate_normalized_expectation_gap,
)
from industry_alpha.normalized_financial_rules import build_structured_observation


def expected(value: str, *, currency: str = "CNY"):
    return build_structured_observation(
        instrument_id="instrument-a",
        company_research_id="research-a",
        metric_code="net_profit_attributable",
        source_kind="consensus",
        observation_state="supported",
        value_text=value,
        currency_code=currency,
        unit_code="currency_amount",
        period_basis="forward_fy1",
        target_period_key="FY2026",
        accounting_scope="consolidated_attributable",
        observation_as_of_date=date(2026, 6, 15),
        period_start_date=date(2026, 1, 1),
        period_end_date=date(2026, 12, 31),
        fiscal_year=2026,
    )


def actual(value: str, *, currency: str = "CNY"):
    return build_structured_observation(
        instrument_id="instrument-a",
        company_research_id="research-a",
        metric_code="net_profit_attributable",
        source_kind="actual",
        observation_state="supported",
        value_text=value,
        currency_code=currency,
        unit_code="currency_amount",
        period_basis="fy_actual",
        target_period_key="FY2026",
        accounting_scope="consolidated_attributable",
        observation_as_of_date=date(2027, 2, 20),
        period_start_date=date(2026, 1, 1),
        period_end_date=date(2026, 12, 31),
        fiscal_year=2026,
    )


def test_expectation_gap_golden_path_is_exact_and_directional() -> None:
    result = calculate_normalized_expectation_gap(
        expected=expected("2000000000"),
        actual=actual("2200000000"),
        calculation_as_of_date=date(2027, 3, 1),
    )
    assert result.gap_state == "calculated"
    assert result.absolute_gap == Decimal("200000000.000000")
    assert result.percentage_gap == Decimal("10.0000")
    assert result.direction == "above_expected"
    assert result.reason_codes == ()


def test_zero_expected_preserves_absolute_gap_without_percentage() -> None:
    result = calculate_normalized_expectation_gap(
        expected=expected("0"),
        actual=actual("100"),
        calculation_as_of_date=date(2027, 3, 1),
    )
    assert result.gap_state == "percentage_not_meaningful_zero_expected"
    assert result.absolute_gap == Decimal("100.000000")
    assert result.percentage_gap is None
    assert result.direction == "above_expected"
    assert result.reason_codes == ("expected_value_zero",)


def test_currency_mismatch_and_future_input_fail_closed() -> None:
    mismatch = calculate_normalized_expectation_gap(
        expected=expected("200", currency="CNY"),
        actual=actual("220", currency="USD"),
        calculation_as_of_date=date(2027, 3, 1),
    )
    assert mismatch.gap_state == "incompatible_input"
    assert mismatch.absolute_gap is None
    assert mismatch.reason_codes == ("currency_mismatch",)

    future = calculate_normalized_expectation_gap(
        expected=expected("200"),
        actual=actual("220"),
        calculation_as_of_date=date(2027, 1, 1),
    )
    assert future.gap_state == "stale_input"
    assert future.reason_codes == ("input_after_calculation_date",)


def test_equal_and_below_expected_direction_are_deterministic() -> None:
    equal = calculate_normalized_expectation_gap(
        expected=expected("200"),
        actual=actual("200"),
        calculation_as_of_date=date(2027, 3, 1),
    )
    below = calculate_normalized_expectation_gap(
        expected=expected("200"),
        actual=actual("150"),
        calculation_as_of_date=date(2027, 3, 1),
    )
    assert equal.direction == "equal_expected"
    assert equal.percentage_gap == Decimal("0.0000")
    assert below.direction == "below_expected"
    assert below.percentage_gap == Decimal("-25.0000")
