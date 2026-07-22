from datetime import date
from decimal import Decimal

import pytest

from industry_alpha.normalized_financial_rules import (
    NormalizedMetricError,
    build_structured_observation,
    parse_decimal_text,
)


def test_decimal_text_is_half_even_bounded_and_rejects_exponent() -> None:
    assert parse_decimal_text("1.2345665", required=True) == (
        "1.2345665",
        Decimal("1.234566"),
    )
    assert parse_decimal_text("1.2345675", required=True) == (
        "1.2345675",
        Decimal("1.234568"),
    )
    with pytest.raises(NormalizedMetricError):
        parse_decimal_text("1e6", required=True)
    with pytest.raises(NormalizedMetricError):
        parse_decimal_text("NaN", required=True)
    with pytest.raises(NormalizedMetricError):
        parse_decimal_text("9" * 39, required=True)


def test_supported_share_observation_requires_exact_shape_and_effective_range() -> None:
    observation = build_structured_observation(
        instrument_id="instrument-a",
        company_research_id="research-a",
        metric_code="diluted_shares_outstanding",
        source_kind="actual",
        observation_state="supported",
        value_text="1000000000",
        currency_code=None,
        unit_code="shares",
        period_basis="instant",
        target_period_key="shares-2026-06-30",
        accounting_scope="consolidated_attributable",
        observation_as_of_date=date(2026, 6, 20),
        period_end_date=date(2026, 6, 20),
        effective_start_date=date(2026, 1, 1),
    )
    assert observation.value == Decimal("1000000000.000000")
    assert observation.effective_end_date is None

    with pytest.raises(NormalizedMetricError) as exc_info:
        build_structured_observation(
            instrument_id="instrument-a",
            company_research_id="research-a",
            metric_code="diluted_shares_outstanding",
            source_kind="actual",
            observation_state="supported",
            value_text="100",
            currency_code="CNY",
            unit_code="shares",
            period_basis="instant",
            target_period_key="shares-2026-06-30",
            accounting_scope="consolidated_attributable",
            observation_as_of_date=date(2026, 6, 20),
            period_end_date=date(2026, 6, 20),
            effective_start_date=date(2026, 1, 1),
        )
    assert exc_info.value.code == "normalized_financial_unit_invalid"


def test_flow_source_kind_period_and_scope_are_fail_closed() -> None:
    with pytest.raises(NormalizedMetricError) as exc_info:
        build_structured_observation(
            instrument_id="instrument-a",
            company_research_id="research-a",
            metric_code="net_profit_attributable",
            source_kind="actual",
            observation_state="supported",
            value_text="2000000000",
            currency_code="CNY",
            unit_code="currency_amount",
            period_basis="forward_fy1",
            target_period_key="FY2026",
            accounting_scope="consolidated_attributable",
            observation_as_of_date=date(2026, 6, 20),
            period_start_date=date(2026, 1, 1),
            period_end_date=date(2026, 12, 31),
            fiscal_year=2026,
        )
    assert exc_info.value.code == "normalized_financial_chronology_invalid"

    with pytest.raises(NormalizedMetricError) as exc_info:
        build_structured_observation(
            instrument_id="instrument-a",
            company_research_id="research-a",
            metric_code="revenue",
            source_kind="consensus",
            observation_state="supported",
            value_text="100",
            currency_code="CNY",
            unit_code="currency_amount",
            period_basis="forward_fy1",
            target_period_key="FY2026",
            accounting_scope="consolidated_attributable",
            observation_as_of_date=date(2026, 6, 20),
            period_start_date=date(2026, 1, 1),
            period_end_date=date(2026, 12, 31),
            fiscal_year=2026,
        )
    assert exc_info.value.code == "normalized_financial_accounting_scope_invalid"


def test_non_supported_observation_forbids_numeric_value() -> None:
    with pytest.raises(NormalizedMetricError) as exc_info:
        build_structured_observation(
            instrument_id="instrument-a",
            company_research_id="research-a",
            metric_code="net_debt",
            source_kind="actual",
            observation_state="missing",
            value_text="0",
            currency_code="CNY",
            unit_code="currency_amount",
            period_basis="instant",
            target_period_key="net-debt-2026-06-30",
            accounting_scope="consolidated",
            observation_as_of_date=date(2026, 6, 20),
            period_end_date=date(2026, 6, 20),
        )
    assert exc_info.value.code == "normalized_financial_value_forbidden"
