from datetime import date
from decimal import Decimal

import pytest

from industry_alpha.normalized_financial_rules import (
    NormalizedMetricError,
    build_structured_observation,
)
from industry_alpha.normalized_valuation_rules import (
    CanonicalPriceInput,
    ComparisonMember,
    calculate_historical_context,
    calculate_peer_context,
    evaluate_normalized_valuation,
)

VALUATION_DATE = date(2026, 6, 30)


def price(*, trade_date: date = VALUATION_DATE) -> CanonicalPriceInput:
    return CanonicalPriceInput(
        instrument_id="instrument-a",
        value=Decimal("20.000000"),
        currency_code="CNY",
        unit_code="currency_per_share",
        trade_date=trade_date,
        canonical_status="accepted",
        price_kind="official_close",
        adjustment_basis="unadjusted",
        eligibility_state="eligible",
        eligibility_purpose="normalized_valuation_metric_v1",
    )


def shares(*, effective_end_date: date | None = None):
    return build_structured_observation(
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
        effective_end_date=effective_end_date,
    )


def actual_flow(metric_code: str, value: str):
    scope = (
        "consolidated_attributable"
        if metric_code == "net_profit_attributable"
        else "consolidated"
    )
    return build_structured_observation(
        instrument_id="instrument-a",
        company_research_id="research-a",
        metric_code=metric_code,
        source_kind="actual",
        observation_state="supported",
        value_text=value,
        currency_code="CNY",
        unit_code="currency_amount",
        period_basis="ttm",
        target_period_key="TTM-2026-06-20",
        accounting_scope=scope,
        observation_as_of_date=date(2026, 6, 25),
        period_start_date=date(2025, 6, 21),
        period_end_date=date(2026, 6, 20),
    )


def net_debt(value: str = "1000000000"):
    return build_structured_observation(
        instrument_id="instrument-a",
        company_research_id="research-a",
        metric_code="net_debt",
        source_kind="actual",
        observation_state="supported",
        value_text=value,
        currency_code="CNY",
        unit_code="currency_amount",
        period_basis="instant",
        target_period_key="net-debt-2026-06-20",
        accounting_scope="consolidated",
        observation_as_of_date=date(2026, 6, 25),
        period_end_date=date(2026, 6, 20),
    )


def evaluate(metric_code: str, denominator, *, debt=None, canonical_price=None, share_input=None):
    return evaluate_normalized_valuation(
        metric_code=metric_code,
        valuation_as_of_date=VALUATION_DATE,
        target_period_key="TTM-2026-06-20",
        period_basis="ttm",
        accounting_scope=denominator.accounting_scope,
        price=canonical_price or price(),
        shares=share_input or shares(),
        denominator=denominator,
        net_debt=debt,
    )


def test_golden_path_produces_exact_pe_ps_ev_ebitda_and_fcf_yield() -> None:
    pe = evaluate("pe", actual_flow("net_profit_attributable", "2000000000"))
    ps = evaluate("ps", actual_flow("revenue", "10000000000"))
    ev = evaluate(
        "ev_ebitda",
        actual_flow("ebitda", "3000000000"),
        debt=net_debt(),
    )
    fcf = evaluate("fcf_yield", actual_flow("free_cash_flow", "1000000000"))

    assert pe.normalized_value == Decimal("10.0000")
    assert ps.normalized_value == Decimal("2.0000")
    assert ev.enterprise_value == Decimal("21000000000.000000")
    assert ev.normalized_value == Decimal("7.0000")
    assert fcf.normalized_value == Decimal("5.0000")
    assert {pe.calculation_state, ps.calculation_state, ev.calculation_state, fcf.calculation_state} == {
        "calculated"
    }


def test_nonpositive_denominators_and_negative_fcf_are_explicit() -> None:
    loss = evaluate("pe", actual_flow("net_profit_attributable", "-1"))
    assert loss.calculation_state == "non_meaningful_nonpositive_denominator"
    assert loss.normalized_value is None
    assert loss.reason_codes == ("profit_nonpositive",)

    negative_fcf = evaluate("fcf_yield", actual_flow("free_cash_flow", "-1000000000"))
    assert negative_fcf.calculation_state == "calculated_negative"
    assert negative_fcf.normalized_value == Decimal("-5.0000")
    assert negative_fcf.reason_codes == ("free_cash_flow_negative",)


def test_price_age_and_share_effective_range_fail_closed() -> None:
    stale = evaluate(
        "pe",
        actual_flow("net_profit_attributable", "2000000000"),
        canonical_price=price(trade_date=date(2026, 6, 20)),
    )
    assert stale.calculation_state == "stale_input"
    assert stale.reason_codes == ("price_too_old",)

    mismatch = evaluate(
        "pe",
        actual_flow("net_profit_attributable", "2000000000"),
        share_input=shares(effective_end_date=date(2026, 6, 29)),
    )
    assert mismatch.calculation_state == "incompatible_input"
    assert mismatch.reason_codes == ("share_effective_range_mismatch",)


def test_equity_value_must_be_strictly_positive() -> None:
    invalid_price = CanonicalPriceInput(
        **{**price().__dict__, "value": Decimal("0")}
    )
    with pytest.raises(NormalizedMetricError) as exc_info:
        evaluate(
            "pe",
            actual_flow("net_profit_attributable", "2000000000"),
            canonical_price=invalid_price,
        )
    assert exc_info.value.code == "normalized_valuation_equity_value_invalid"


def test_historical_context_uses_midrank_percentile_and_exact_sufficiency() -> None:
    dates = (
        date(2023, 1, 1),
        date(2023, 5, 1),
        date(2023, 9, 1),
        date(2024, 1, 1),
        date(2024, 5, 1),
        date(2024, 9, 1),
        date(2025, 1, 1),
        date(2025, 5, 5),
    )
    values = ("10", "5", "10", "15", "20", "25", "30", "35")
    members = tuple(
        ComparisonMember(
            member_id=f"member-{index}",
            value=Decimal(value),
            valuation_date=valuation_date,
            period_end_date=date(2022 + (index // 2), 12, 31),
            eligible=True,
        )
        for index, (value, valuation_date) in enumerate(zip(values, dates, strict=True))
    )
    result = calculate_historical_context(subject_member_id="member-0", members=members)
    assert result.comparison_state == "calculated"
    assert result.eligible_member_count == 8
    assert result.subject_percentile == Decimal("25.00")
    assert result.minimum == Decimal("5.0000")
    assert result.maximum == Decimal("35.0000")
    assert result.median == Decimal("17.5000")


def test_peer_context_preserves_ineligible_member_and_uses_only_eligible_values() -> None:
    members = (
        ComparisonMember("a", Decimal("20"), VALUATION_DATE, date(2026, 6, 20), True),
        ComparisonMember("b", Decimal("10"), VALUATION_DATE, date(2026, 6, 20), True),
        ComparisonMember("c", Decimal("30"), VALUATION_DATE, date(2026, 6, 20), True),
        ComparisonMember(
            "d",
            None,
            VALUATION_DATE,
            date(2026, 6, 20),
            False,
            ("profit_nonpositive",),
        ),
    )
    result = calculate_peer_context(subject_member_id="a", members=members)
    assert result.comparison_state == "calculated"
    assert result.total_member_count == 4
    assert result.eligible_member_count == 3
    assert result.excluded_member_count == 1
    assert result.subject_percentile == Decimal("50.00")
    assert tuple(member.member_id for member in result.members) == ("a", "b", "c", "d")
