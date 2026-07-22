"""Deterministic D2 rules for Investment Candidate Intelligence v1."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from uuid import UUID

from industry_alpha.investment_candidate_models import COMPONENT_CODES

PURPOSE_CODE = "industry_beneficiary_investment_candidate_v1"
RULE_VERSION = "aquantai.investment-candidate-priority.v1"
PRICE_PURPOSE_CODE = "company_research_price_context_v1"
TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")

POSITIVE_WEIGHTS: dict[str, Decimal] = {
    "industry_opportunity": Decimal("0.15"),
    "beneficiary_strength": Decimal("0.20"),
    "earnings_conversion": Decimal("0.20"),
    "expectation_gap": Decimal("0.15"),
    "valuation_context": Decimal("0.15"),
    "catalyst_readiness": Decimal("0.10"),
    "evidence_quality": Decimal("0.05"),
}
RISK_WEIGHT = Decimal("0.25")
REASON_CODES = frozenset(
    {
        "canonical_price_conflicting",
        "canonical_price_ineligible",
        "canonical_price_missing",
        "canonical_price_stale",
        "component_disputed",
        "critical_component_missing",
        "earnings_conversion_weak",
        "evidence_quality_low",
        "expectation_already_reflected",
        "expectation_input_disputed",
        "expectation_input_missing",
        "falsification_triggered",
        "market_attention_not_available_v1",
        "priority_threshold_met",
        "pricing_demanding",
        "risk_high",
        "score_below_watch_threshold",
        "valuation_input_disputed",
        "valuation_input_missing",
        "verification_failed",
        "verification_pending",
        "watch_threshold_met",
    }
)


class InvestmentCandidateError(RuntimeError):
    """Stable credential-safe public error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class InvestmentCandidateNotFound(InvestmentCandidateError):
    pass


def decimal_score(value: str | None, *, required: bool) -> tuple[str | None, Decimal | None]:
    if value is None:
        if required:
            raise InvestmentCandidateError(
                "investment_candidate_score_required",
                "supported component requires score_text",
            )
        return None, None
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 64:
        raise InvestmentCandidateError(
            "investment_candidate_decimal_invalid", "score must be bounded decimal text"
        )
    text = value.strip()
    try:
        number = Decimal(text)
        standardized = number.quantize(TWO_PLACES, rounding=ROUND_HALF_EVEN)
    except (InvalidOperation, ValueError) as exc:
        raise InvestmentCandidateError(
            "investment_candidate_decimal_invalid", "score must be valid decimal text"
        ) from exc
    if not number.is_finite() or standardized < ZERO or standardized > Decimal("100.00"):
        raise InvestmentCandidateError(
            "investment_candidate_decimal_invalid", "score must be within 0.00 to 100.00"
        )
    return text, standardized


def quantize(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True)
class ComponentState:
    code: str
    assessment_state: str
    verification_state: str
    verification_material: bool
    falsification_state: str
    score: Decimal | None


@dataclass(frozen=True)
class CandidateResult:
    candidate_status: str
    base_score: Decimal | None
    business_quality_score: Decimal | None
    risk_penalty_points: Decimal | None
    final_score: Decimal | None
    reason_codes: tuple[str, ...]
    contributions: dict[str, Decimal | None]


def evaluate_candidate(components: dict[str, ComponentState]) -> CandidateResult:
    reasons = {"market_attention_not_available_v1"}
    missing_codes = set(COMPONENT_CODES) - set(components)
    if missing_codes:
        reasons.add("critical_component_missing")
        if "expectation_gap" in missing_codes:
            reasons.add("expectation_input_missing")
        if "valuation_context" in missing_codes:
            reasons.add("valuation_input_missing")
        return _without_aggregate("evidence_insufficient", reasons)

    disputed = {c.code for c in components.values() if c.assessment_state == "disputed"}
    missing = {
        c.code
        for c in components.values()
        if c.assessment_state in {"missing", "not_applicable"} or c.score is None
    }
    if disputed:
        reasons.add("component_disputed")
        if "expectation_gap" in disputed:
            reasons.add("expectation_input_disputed")
        if "valuation_context" in disputed:
            reasons.add("valuation_input_disputed")
        return _without_aggregate("evidence_insufficient", reasons)
    if missing:
        reasons.add("critical_component_missing")
        if "expectation_gap" in missing:
            reasons.add("expectation_input_missing")
        if "valuation_context" in missing:
            reasons.add("valuation_input_missing")
        return _without_aggregate("evidence_insufficient", reasons)
    if any(c.falsification_state == "active" for c in components.values()):
        reasons.add("falsification_triggered")
        return _without_aggregate("not_current_candidate", reasons)
    if any(
        c.verification_state == "failed" and c.verification_material
        for c in components.values()
    ):
        reasons.add("verification_failed")
        return _without_aggregate("not_current_candidate", reasons)
    if any(c.verification_state == "pending" for c in components.values()):
        reasons.add("verification_pending")
        return _without_aggregate("awaiting_verification", reasons)

    scores = {code: state.score for code, state in components.items()}
    if any(value is None for value in scores.values()):
        reasons.add("critical_component_missing")
        return _without_aggregate("evidence_insufficient", reasons)
    numeric = {code: value for code, value in scores.items() if value is not None}
    base = quantize(sum((numeric[c] * w for c, w in POSITIVE_WEIGHTS.items()), ZERO))
    business = quantize(
        (
            numeric["industry_opportunity"] * Decimal("0.15")
            + numeric["beneficiary_strength"] * Decimal("0.20")
            + numeric["earnings_conversion"] * Decimal("0.20")
            + numeric["catalyst_readiness"] * Decimal("0.10")
            + numeric["evidence_quality"] * Decimal("0.05")
        )
        / Decimal("0.70")
    )
    risk = numeric["risk_penalty"]
    penalty = quantize(risk * RISK_WEIGHT)
    final = quantize(max(ZERO, base - penalty))
    contributions: dict[str, Decimal | None] = {
        code: quantize(numeric[code] * weight)
        for code, weight in POSITIVE_WEIGHTS.items()
    }
    contributions["risk_penalty"] = -penalty

    if risk >= Decimal("75.00"):
        status = "not_current_candidate"
        reasons.add("risk_high")
    elif business >= Decimal("70.00") and (
        numeric["valuation_context"] < Decimal("40.00")
        or numeric["expectation_gap"] < Decimal("40.00")
    ):
        status = "pricing_demanding"
        reasons.add("pricing_demanding")
        if numeric["expectation_gap"] < Decimal("40.00"):
            reasons.add("expectation_already_reflected")
    elif (
        final >= Decimal("75.00")
        and numeric["beneficiary_strength"] >= Decimal("65.00")
        and numeric["earnings_conversion"] >= Decimal("65.00")
        and numeric["expectation_gap"] >= Decimal("50.00")
        and numeric["valuation_context"] >= Decimal("50.00")
        and risk < Decimal("50.00")
    ):
        status = "priority_candidate"
        reasons.add("priority_threshold_met")
    elif final >= Decimal("60.00") and risk < Decimal("65.00"):
        status = "watch_candidate"
        reasons.add("watch_threshold_met")
    else:
        status = "not_current_candidate"
        reasons.add("score_below_watch_threshold")
        if numeric["earnings_conversion"] < Decimal("50.00"):
            reasons.add("earnings_conversion_weak")
        if numeric["evidence_quality"] < Decimal("50.00"):
            reasons.add("evidence_quality_low")
    return CandidateResult(
        candidate_status=status,
        base_score=base,
        business_quality_score=business,
        risk_penalty_points=penalty,
        final_score=final,
        reason_codes=_reasons(reasons),
        contributions=contributions,
    )


def priority_sort_key(
    *,
    status: str,
    final_score: Decimal,
    business_quality_score: Decimal,
    risk_score: Decimal,
    beneficiary_strength: Decimal,
    beneficiary_id: UUID,
) -> tuple[int, Decimal, Decimal, Decimal, Decimal, str]:
    bucket = 0 if status == "priority_candidate" else 1
    return (
        bucket,
        -final_score,
        -business_quality_score,
        risk_score,
        -beneficiary_strength,
        str(beneficiary_id),
    )


def _without_aggregate(status: str, reasons: set[str]) -> CandidateResult:
    return CandidateResult(
        candidate_status=status,
        base_score=None,
        business_quality_score=None,
        risk_penalty_points=None,
        final_score=None,
        reason_codes=_reasons(reasons),
        contributions={code: None for code in COMPONENT_CODES},
    )


def _reasons(values: set[str]) -> tuple[str, ...]:
    if not values.issubset(REASON_CODES):
        raise InvestmentCandidateError(
            "investment_candidate_reason_invalid", "unknown deterministic reason code"
        )
    return tuple(sorted(values))
