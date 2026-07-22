"""Deterministic normalized-valuation and comparison rules for Slice 5."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN, localcontext

from industry_alpha.normalized_financial_rules import (
    NormalizedMetricError,
    StructuredObservationInput,
)

NORMALIZED_VALUATION_RULE_VERSION = "aquantai.normalized-valuation.v1"
NORMALIZED_COMPARISON_RULE_VERSION = "aquantai.normalized-comparison-context.v1"
PRICE_PURPOSE_CODE = "normalized_valuation_metric_v1"
FOUR_PLACES = Decimal("0.0001")
SIX_PLACES = Decimal("0.000001")
TWO_PLACES = Decimal("0.01")
HUNDRED = Decimal("100")
ZERO = Decimal("0")

VALUATION_METRIC_CODES = frozenset({"pe", "ps", "ev_ebitda", "fcf_yield"})
CALCULATED_STATES = frozenset({"calculated", "calculated_negative"})
REASON_CODES = frozenset(
    {
        "price_not_accepted",
        "price_purpose_ineligible",
        "price_too_old",
        "share_effective_range_mismatch",
        "financial_observation_too_old",
        "currency_mismatch",
        "unit_mismatch",
        "instrument_mismatch",
        "period_mismatch",
        "horizon_mismatch",
        "accounting_scope_mismatch",
        "input_missing",
        "input_disputed",
        "input_rejected",
        "profit_nonpositive",
        "revenue_nonpositive",
        "ebitda_nonpositive",
        "enterprise_value_nonpositive",
        "free_cash_flow_negative",
    }
)


@dataclass(frozen=True)
class CanonicalPriceInput:
    instrument_id: str
    value: Decimal
    currency_code: str
    unit_code: str
    trade_date: date
    canonical_status: str
    price_kind: str
    adjustment_basis: str
    eligibility_state: str
    eligibility_purpose: str


@dataclass(frozen=True)
class ValuationResult:
    metric_code: str
    calculation_state: str
    normalized_value: Decimal | None
    equity_value: Decimal | None
    enterprise_value: Decimal | None
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ComparisonMember:
    member_id: str
    value: Decimal | None
    valuation_date: date
    period_end_date: date
    eligible: bool
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ComparisonResult:
    comparison_state: str
    total_member_count: int
    eligible_member_count: int
    excluded_member_count: int
    minimum: Decimal | None
    maximum: Decimal | None
    median: Decimal | None
    subject_percentile: Decimal | None
    members: tuple[ComparisonMember, ...]


def evaluate_normalized_valuation(
    *,
    metric_code: str,
    valuation_as_of_date: date,
    target_period_key: str,
    period_basis: str,
    accounting_scope: str,
    price: CanonicalPriceInput,
    shares: StructuredObservationInput,
    denominator: StructuredObservationInput,
    net_debt: StructuredObservationInput | None = None,
) -> ValuationResult:
    """Evaluate one exact normalized valuation metric without fallback or imputation."""

    if metric_code not in VALUATION_METRIC_CODES:
        raise NormalizedMetricError(
            "normalized_valuation_metric_invalid", f"unsupported valuation metric: {metric_code}"
        )
    if not isinstance(target_period_key, str) or not target_period_key.strip():
        raise NormalizedMetricError(
            "normalized_valuation_period_invalid", "target_period_key must be explicit"
        )

    price_failure = _validate_price(price, valuation_as_of_date)
    if price_failure is not None:
        return price_failure_for(metric_code, *price_failure)

    required_denominator = {
        "pe": "net_profit_attributable",
        "ps": "revenue",
        "ev_ebitda": "ebitda",
        "fcf_yield": "free_cash_flow",
    }[metric_code]
    if shares.metric_code != "diluted_shares_outstanding" or denominator.metric_code != required_denominator:
        return _without_value(metric_code, "incompatible_input", {"unit_mismatch"})
    if metric_code == "ev_ebitda" and (net_debt is None or net_debt.metric_code != "net_debt"):
        return _without_value(metric_code, "missing_input", {"input_missing"})
    if metric_code != "ev_ebitda" and net_debt is not None:
        raise NormalizedMetricError(
            "normalized_valuation_extra_input", "net debt is only valid for ev_ebitda"
        )

    state_failure = _observation_state_failure(shares, denominator, net_debt)
    if state_failure is not None:
        state, reasons = state_failure
        return _without_value(metric_code, state, reasons)

    reasons = _compatibility_reasons(
        valuation_as_of_date=valuation_as_of_date,
        target_period_key=target_period_key,
        period_basis=period_basis,
        accounting_scope=accounting_scope,
        price=price,
        shares=shares,
        denominator=denominator,
        net_debt=net_debt,
    )
    if reasons:
        state = "stale_input" if reasons <= {"financial_observation_too_old"} else "incompatible_input"
        return _without_value(metric_code, state, reasons)

    if price.value <= ZERO:
        raise NormalizedMetricError(
            "normalized_valuation_equity_value_invalid", "canonical price must be strictly positive"
        )
    if shares.value is None or denominator.value is None:
        return _without_value(metric_code, "missing_input", {"input_missing"})

    with localcontext() as context:
        context.prec = 28
        equity_value = (price.value * shares.value).quantize(
            SIX_PLACES, rounding=ROUND_HALF_EVEN
        )
        if equity_value <= ZERO:
            raise NormalizedMetricError(
                "normalized_valuation_equity_value_invalid",
                "equity value must be strictly positive",
            )

        enterprise_value: Decimal | None = None
        if metric_code == "pe":
            if denominator.value <= ZERO:
                return _without_value(
                    metric_code,
                    "non_meaningful_nonpositive_denominator",
                    {"profit_nonpositive"},
                    equity_value=equity_value,
                )
            result = (equity_value / denominator.value).quantize(
                FOUR_PLACES, rounding=ROUND_HALF_EVEN
            )
            state = "calculated"
        elif metric_code == "ps":
            if denominator.value <= ZERO:
                return _without_value(
                    metric_code,
                    "non_meaningful_nonpositive_denominator",
                    {"revenue_nonpositive"},
                    equity_value=equity_value,
                )
            result = (equity_value / denominator.value).quantize(
                FOUR_PLACES, rounding=ROUND_HALF_EVEN
            )
            state = "calculated"
        elif metric_code == "ev_ebitda":
            assert net_debt is not None and net_debt.value is not None
            enterprise_value = (equity_value + net_debt.value).quantize(
                SIX_PLACES, rounding=ROUND_HALF_EVEN
            )
            if denominator.value <= ZERO:
                return _without_value(
                    metric_code,
                    "non_meaningful_nonpositive_denominator",
                    {"ebitda_nonpositive"},
                    equity_value=equity_value,
                    enterprise_value=enterprise_value,
                )
            if enterprise_value <= ZERO:
                return _without_value(
                    metric_code,
                    "non_meaningful_nonpositive_enterprise_value",
                    {"enterprise_value_nonpositive"},
                    equity_value=equity_value,
                    enterprise_value=enterprise_value,
                )
            result = (enterprise_value / denominator.value).quantize(
                FOUR_PLACES, rounding=ROUND_HALF_EVEN
            )
            state = "calculated"
        else:
            result = (denominator.value / equity_value * HUNDRED).quantize(
                FOUR_PLACES, rounding=ROUND_HALF_EVEN
            )
            state = "calculated_negative" if denominator.value < ZERO else "calculated"
            if state == "calculated_negative":
                reasons = {"free_cash_flow_negative"}
            else:
                reasons = set()

    return ValuationResult(
        metric_code=metric_code,
        calculation_state=state,
        normalized_value=result,
        equity_value=equity_value,
        enterprise_value=enterprise_value,
        reason_codes=_sorted_reasons(reasons),
    )


def calculate_historical_context(
    *, subject_member_id: str, members: tuple[ComparisonMember, ...]
) -> ComparisonResult:
    """Calculate a frozen historical context with exact sufficiency rules."""

    _validate_comparison_members(subject_member_id, members)
    dates = [member.valuation_date for member in members]
    if len(set(dates)) != len(dates):
        raise NormalizedMetricError(
            "normalized_comparison_duplicate_date", "historical valuation dates must be unique"
        )
    eligible = _eligible_members(members)
    subject = _subject(subject_member_id, members)
    span_days = (max(dates) - min(dates)).days if dates else 0
    distinct_periods = len({member.period_end_date for member in eligible})
    sufficient = (
        subject.eligible
        and subject.value is not None
        and len(eligible) >= 8
        and span_days >= 730
        and distinct_periods >= 4
    )
    if not sufficient:
        return _empty_comparison("insufficient_history", members, eligible)
    return _calculate_statistics("calculated", subject, members, eligible)


def calculate_peer_context(
    *, subject_member_id: str, members: tuple[ComparisonMember, ...]
) -> ComparisonResult:
    """Calculate peer context while preserving all explicit members."""

    _validate_comparison_members(subject_member_id, members)
    subject = _subject(subject_member_id, members)
    eligible = _eligible_members(members)
    eligible_dates = {member.valuation_date for member in eligible}
    if len(eligible_dates) > 1:
        raise NormalizedMetricError(
            "normalized_comparison_valuation_date_mismatch",
            "eligible peer members require one common valuation date",
        )
    if not subject.eligible or subject.value is None or len(eligible) < 3:
        return _empty_comparison("insufficient_peer_members", members, eligible)
    return _calculate_statistics("calculated", subject, members, eligible)


def price_failure_for(metric_code: str, state: str, reasons: set[str]) -> ValuationResult:
    return _without_value(metric_code, state, reasons)


def _validate_price(
    price: CanonicalPriceInput, valuation_as_of_date: date
) -> tuple[str, set[str]] | None:
    if price.canonical_status != "accepted" or price.price_kind != "official_close" or price.adjustment_basis != "unadjusted":
        return "ineligible_price", {"price_not_accepted"}
    if price.eligibility_state != "eligible" or price.eligibility_purpose != PRICE_PURPOSE_CODE:
        return "ineligible_price", {"price_purpose_ineligible"}
    if price.unit_code != "currency_per_share":
        return "incompatible_input", {"unit_mismatch"}
    age = (valuation_as_of_date - price.trade_date).days
    if age < 0 or age > 7:
        return "stale_input", {"price_too_old"}
    return None


def _observation_state_failure(
    shares: StructuredObservationInput,
    denominator: StructuredObservationInput,
    net_debt: StructuredObservationInput | None,
) -> tuple[str, set[str]] | None:
    observations = [shares, denominator]
    if net_debt is not None:
        observations.append(net_debt)
    states = {item.observation_state for item in observations}
    if "disputed" in states:
        return "disputed_input", {"input_disputed"}
    if "rejected" in states:
        return "rejected_input", {"input_rejected"}
    if states & {"missing", "not_applicable"}:
        return "missing_input", {"input_missing"}
    return None


def _compatibility_reasons(
    *,
    valuation_as_of_date: date,
    target_period_key: str,
    period_basis: str,
    accounting_scope: str,
    price: CanonicalPriceInput,
    shares: StructuredObservationInput,
    denominator: StructuredObservationInput,
    net_debt: StructuredObservationInput | None,
) -> set[str]:
    reasons: set[str] = set()
    observations = [shares, denominator]
    if net_debt is not None:
        observations.append(net_debt)

    if any(item.instrument_id != price.instrument_id for item in observations):
        reasons.add("instrument_mismatch")
    if shares.unit_code != "shares" or denominator.unit_code != "currency_amount":
        reasons.add("unit_mismatch")
    if denominator.currency_code != price.currency_code:
        reasons.add("currency_mismatch")
    if net_debt is not None and net_debt.currency_code != price.currency_code:
        reasons.add("currency_mismatch")
    if denominator.period_basis != period_basis:
        reasons.add("period_mismatch")
    if denominator.target_period_key != target_period_key:
        reasons.add("horizon_mismatch")
    if denominator.accounting_scope != accounting_scope:
        reasons.add("accounting_scope_mismatch")

    if shares.effective_start_date is None or not (
        shares.effective_start_date <= price.trade_date
        and (shares.effective_end_date is None or price.trade_date <= shares.effective_end_date)
    ):
        reasons.add("share_effective_range_mismatch")

    if shares.observation_as_of_date > valuation_as_of_date:
        reasons.add("financial_observation_too_old")
    if denominator.observation_as_of_date > valuation_as_of_date:
        reasons.add("financial_observation_too_old")
    if denominator.period_basis in {"ttm", "instant"}:
        age = (valuation_as_of_date - denominator.period_end_date).days
        if age < 0 or age > 120:
            reasons.add("financial_observation_too_old")
    if net_debt is not None:
        if net_debt.period_basis != "instant":
            reasons.add("period_mismatch")
        if net_debt.observation_as_of_date > valuation_as_of_date:
            reasons.add("financial_observation_too_old")
        debt_age = (valuation_as_of_date - net_debt.period_end_date).days
        if debt_age < 0 or debt_age > 120:
            reasons.add("financial_observation_too_old")
    return reasons


def _without_value(
    metric_code: str,
    state: str,
    reasons: set[str],
    *,
    equity_value: Decimal | None = None,
    enterprise_value: Decimal | None = None,
) -> ValuationResult:
    return ValuationResult(
        metric_code=metric_code,
        calculation_state=state,
        normalized_value=None,
        equity_value=equity_value,
        enterprise_value=enterprise_value,
        reason_codes=_sorted_reasons(reasons),
    )


def _sorted_reasons(values: set[str]) -> tuple[str, ...]:
    if not values.issubset(REASON_CODES):
        raise NormalizedMetricError(
            "normalized_valuation_reason_invalid", "unknown normalized valuation reason code"
        )
    return tuple(sorted(values))


def _validate_comparison_members(
    subject_member_id: str, members: tuple[ComparisonMember, ...]
) -> None:
    if not members:
        raise NormalizedMetricError(
            "normalized_comparison_members_required", "comparison members are required"
        )
    ids = [member.member_id for member in members]
    if len(set(ids)) != len(ids):
        raise NormalizedMetricError(
            "normalized_comparison_duplicate_member", "comparison member IDs must be unique"
        )
    if ids.count(subject_member_id) != 1:
        raise NormalizedMetricError(
            "normalized_comparison_subject_invalid", "subject must appear exactly once"
        )
    for member in members:
        if member.eligible and member.value is None:
            raise NormalizedMetricError(
                "normalized_comparison_value_required",
                "eligible comparison member requires numeric value",
            )
        if not member.eligible and member.value is not None:
            raise NormalizedMetricError(
                "normalized_comparison_value_forbidden",
                "ineligible comparison member must not enter arithmetic",
            )


def _subject(subject_member_id: str, members: tuple[ComparisonMember, ...]) -> ComparisonMember:
    return next(member for member in members if member.member_id == subject_member_id)


def _eligible_members(members: tuple[ComparisonMember, ...]) -> tuple[ComparisonMember, ...]:
    return tuple(member for member in members if member.eligible and member.value is not None)


def _empty_comparison(
    state: str,
    members: tuple[ComparisonMember, ...],
    eligible: tuple[ComparisonMember, ...],
) -> ComparisonResult:
    return ComparisonResult(
        comparison_state=state,
        total_member_count=len(members),
        eligible_member_count=len(eligible),
        excluded_member_count=len(members) - len(eligible),
        minimum=None,
        maximum=None,
        median=None,
        subject_percentile=None,
        members=members,
    )


def _calculate_statistics(
    state: str,
    subject: ComparisonMember,
    members: tuple[ComparisonMember, ...],
    eligible: tuple[ComparisonMember, ...],
) -> ComparisonResult:
    values = sorted(member.value for member in eligible if member.value is not None)
    assert subject.value is not None
    count_less = sum(value < subject.value for value in values)
    count_equal = sum(value == subject.value for value in values)
    with localcontext() as context:
        context.prec = 28
        percentile = (
            (Decimal(count_less) + Decimal("0.5") * Decimal(count_equal))
            / Decimal(len(values))
            * HUNDRED
        ).quantize(TWO_PLACES, rounding=ROUND_HALF_EVEN)
        middle = len(values) // 2
        if len(values) % 2:
            median = values[middle].quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        else:
            median = ((values[middle - 1] + values[middle]) / Decimal("2")).quantize(
                FOUR_PLACES, rounding=ROUND_HALF_EVEN
            )
    return ComparisonResult(
        comparison_state=state,
        total_member_count=len(members),
        eligible_member_count=len(eligible),
        excluded_member_count=len(members) - len(eligible),
        minimum=values[0].quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN),
        maximum=values[-1].quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN),
        median=median,
        subject_percentile=percentile,
        members=members,
    )
