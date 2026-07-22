from datetime import date
from decimal import Decimal

from industry_alpha.normalized_valuation_rules import (
    ComparisonMember,
    calculate_historical_context,
)


def test_excluded_old_member_cannot_satisfy_pure_rule_history_span() -> None:
    eligible_dates = (
        date(2025, 7, 1),
        date(2025, 8, 1),
        date(2025, 9, 1),
        date(2025, 10, 1),
        date(2025, 11, 1),
        date(2025, 12, 1),
        date(2026, 1, 1),
        date(2026, 2, 1),
    )
    eligible = tuple(
        ComparisonMember(
            member_id=f"eligible-{index}",
            value=Decimal(index + 1),
            valuation_date=valuation_date,
            period_end_date=date(2025 + index // 4, 3 * (index % 4 + 1), 1),
            eligible=True,
        )
        for index, valuation_date in enumerate(eligible_dates)
    )
    excluded_old = ComparisonMember(
        member_id="excluded-old",
        value=None,
        valuation_date=date(2020, 1, 1),
        period_end_date=date(2019, 12, 31),
        eligible=False,
        reason_codes=("input_missing",),
    )

    result = calculate_historical_context(
        subject_member_id="eligible-0",
        members=eligible + (excluded_old,),
    )

    assert result.comparison_state == "insufficient_history"
    assert result.eligible_member_count == 8
    assert result.excluded_member_count == 1
    assert result.subject_percentile is None


def test_excluded_duplicate_date_does_not_invalidate_eligible_history() -> None:
    eligible_dates = (
        date(2023, 1, 1),
        date(2023, 5, 1),
        date(2023, 9, 1),
        date(2024, 1, 1),
        date(2024, 5, 1),
        date(2024, 9, 1),
        date(2025, 1, 1),
        date(2025, 5, 5),
    )
    eligible = tuple(
        ComparisonMember(
            member_id=f"eligible-{index}",
            value=Decimal(index + 1),
            valuation_date=valuation_date,
            period_end_date=date(2022 + index // 2, 12, 31),
            eligible=True,
        )
        for index, valuation_date in enumerate(eligible_dates)
    )
    excluded_duplicate = ComparisonMember(
        member_id="excluded-duplicate",
        value=None,
        valuation_date=eligible_dates[0],
        period_end_date=date(2022, 12, 31),
        eligible=False,
        reason_codes=("input_missing",),
    )

    result = calculate_historical_context(
        subject_member_id="eligible-0",
        members=eligible + (excluded_duplicate,),
    )

    assert result.comparison_state == "calculated"
    assert result.eligible_member_count == 8
    assert result.excluded_member_count == 1
