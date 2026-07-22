"""Deterministic normalized expectation-gap rules for Slice 5."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN, localcontext

from industry_alpha.normalized_financial_rules import (
    NormalizedMetricError,
    StructuredObservationInput,
)

NORMALIZED_EXPECTATION_RULE_VERSION = "aquantai.normalized-expectation-gap.v1"
SUPPORTED_METRICS = frozenset(
    {"revenue", "net_profit_attributable", "ebitda", "free_cash_flow"}
)
EXPECTED_SOURCE_KINDS = frozenset({"guidance", "consensus", "research_assumption"})
SIX_PLACES = Decimal("0.000001")
FOUR_PLACES = Decimal("0.0001")
HUNDRED = Decimal("100")
ZERO = Decimal("0")
REASON_CODES = frozenset(
    {
        "input_missing",
        "input_disputed",
        "input_rejected",
        "source_kind_invalid",
        "instrument_mismatch",
        "company_research_mismatch",
        "metric_mismatch",
        "target_period_mismatch",
        "period_mismatch",
        "currency_mismatch",
        "unit_mismatch",
        "accounting_scope_mismatch",
        "input_after_calculation_date",
        "expected_value_zero",
    }
)


@dataclass(frozen=True)
class ExpectationGapResult:
    metric_code: str
    gap_state: str
    absolute_gap: Decimal | None
    percentage_gap: Decimal | None
    direction: str | None
    reason_codes: tuple[str, ...]


def calculate_normalized_expectation_gap(
    *,
    expected: StructuredObservationInput,
    actual: StructuredObservationInput,
    calculation_as_of_date: date,
) -> ExpectationGapResult:
    """Compare one exact expected observation with one exact actual observation."""

    metric_code = expected.metric_code
    if metric_code not in SUPPORTED_METRICS or actual.metric_code not in SUPPORTED_METRICS:
        raise NormalizedMetricError(
            "normalized_expectation_metric_invalid", "unsupported expectation-gap metric"
        )

    state_failure = _state_failure(expected, actual)
    if state_failure is not None:
        state, reasons = state_failure
        return _without_gap(metric_code, state, reasons)

    reasons: set[str] = set()
    if expected.source_kind not in EXPECTED_SOURCE_KINDS or actual.source_kind != "actual":
        reasons.add("source_kind_invalid")
    if expected.instrument_id != actual.instrument_id:
        reasons.add("instrument_mismatch")
    if expected.company_research_id != actual.company_research_id:
        reasons.add("company_research_mismatch")
    if expected.metric_code != actual.metric_code:
        reasons.add("metric_mismatch")
    if expected.target_period_key != actual.target_period_key:
        reasons.add("target_period_mismatch")
    if expected.period_start_date != actual.period_start_date or expected.period_end_date != actual.period_end_date:
        reasons.add("period_mismatch")
    if expected.currency_code != actual.currency_code:
        reasons.add("currency_mismatch")
    if expected.unit_code != actual.unit_code:
        reasons.add("unit_mismatch")
    if expected.accounting_scope != actual.accounting_scope:
        reasons.add("accounting_scope_mismatch")
    if (
        expected.observation_as_of_date > calculation_as_of_date
        or actual.observation_as_of_date > calculation_as_of_date
    ):
        reasons.add("input_after_calculation_date")
    if reasons:
        state = "stale_input" if reasons == {"input_after_calculation_date"} else "incompatible_input"
        return _without_gap(metric_code, state, reasons)

    if expected.value is None or actual.value is None:
        return _without_gap(metric_code, "missing_input", {"input_missing"})

    with localcontext() as context:
        context.prec = 28
        absolute_gap = (actual.value - expected.value).quantize(
            SIX_PLACES, rounding=ROUND_HALF_EVEN
        )
        if expected.value == ZERO:
            return ExpectationGapResult(
                metric_code=metric_code,
                gap_state="percentage_not_meaningful_zero_expected",
                absolute_gap=absolute_gap,
                percentage_gap=None,
                direction=_direction(absolute_gap),
                reason_codes=("expected_value_zero",),
            )
        percentage_gap = (
            absolute_gap / abs(expected.value) * HUNDRED
        ).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)

    return ExpectationGapResult(
        metric_code=metric_code,
        gap_state="calculated",
        absolute_gap=absolute_gap,
        percentage_gap=percentage_gap,
        direction=_direction(absolute_gap),
        reason_codes=(),
    )


def _state_failure(
    expected: StructuredObservationInput, actual: StructuredObservationInput
) -> tuple[str, set[str]] | None:
    states = {expected.observation_state, actual.observation_state}
    if "disputed" in states:
        return "disputed_input", {"input_disputed"}
    if "rejected" in states:
        return "rejected_input", {"input_rejected"}
    if states & {"missing", "not_applicable"}:
        return "missing_input", {"input_missing"}
    return None


def _without_gap(metric_code: str, state: str, reasons: set[str]) -> ExpectationGapResult:
    if not reasons.issubset(REASON_CODES):
        raise NormalizedMetricError(
            "normalized_expectation_reason_invalid", "unknown expectation-gap reason code"
        )
    return ExpectationGapResult(
        metric_code=metric_code,
        gap_state=state,
        absolute_gap=None,
        percentage_gap=None,
        direction=None,
        reason_codes=tuple(sorted(reasons)),
    )


def _direction(absolute_gap: Decimal) -> str:
    if absolute_gap > ZERO:
        return "above_expected"
    if absolute_gap < ZERO:
        return "below_expected"
    return "equal_expected"
