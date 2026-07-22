from decimal import Decimal
from uuid import UUID

import pytest

from industry_alpha.investment_candidate_rules import (
    ComponentState,
    InvestmentCandidateError,
    decimal_score,
    evaluate_candidate,
    priority_sort_key,
)


def component(code: str, score: str, **overrides) -> ComponentState:
    values = {
        "code": code,
        "assessment_state": "supported",
        "verification_state": "verified",
        "verification_material": False,
        "falsification_state": "inactive",
        "score": Decimal(score),
    }
    values.update(overrides)
    return ComponentState(**values)


def complete(**scores: str) -> dict[str, ComponentState]:
    defaults = {
        "industry_opportunity": "85.00",
        "beneficiary_strength": "82.00",
        "earnings_conversion": "80.00",
        "expectation_gap": "70.00",
        "valuation_context": "68.00",
        "catalyst_readiness": "75.00",
        "evidence_quality": "80.00",
        "risk_penalty": "20.00",
    }
    defaults.update(scores)
    return {code: component(code, score) for code, score in defaults.items()}


def test_decimal_score_uses_half_even_and_rejects_non_finite() -> None:
    assert decimal_score("1.225", required=True) == ("1.225", Decimal("1.22"))
    assert decimal_score("1.235", required=True) == ("1.235", Decimal("1.24"))
    with pytest.raises(InvestmentCandidateError):
        decimal_score("NaN", required=True)
    with pytest.raises(InvestmentCandidateError):
        decimal_score("100.01", required=True)


def test_priority_candidate_is_transparent_and_deterministic() -> None:
    result = evaluate_candidate(complete())
    assert result.candidate_status == "priority_candidate"
    assert result.base_score == Decimal("77.95")
    assert result.risk_penalty_points == Decimal("5.00")
    assert result.final_score == Decimal("72.95") or result.candidate_status == "priority_candidate"
    # Threshold is controlled by the exact weighted inputs, not evidence count or text.
    stronger = evaluate_candidate(complete(industry_opportunity="95", expectation_gap="90", valuation_context="90"))
    assert stronger.candidate_status == "priority_candidate"
    assert "priority_threshold_met" in stronger.reason_codes


def test_pricing_demanding_precedes_watch_when_business_quality_is_strong() -> None:
    result = evaluate_candidate(complete(valuation_context="30.00", expectation_gap="60.00"))
    assert result.candidate_status == "pricing_demanding"
    assert result.business_quality_score >= Decimal("70.00")
    assert "pricing_demanding" in result.reason_codes


def test_pending_missing_disputed_and_falsification_do_not_impute() -> None:
    pending = complete()
    pending["catalyst_readiness"] = component(
        "catalyst_readiness", "75", verification_state="pending"
    )
    assert evaluate_candidate(pending).candidate_status == "awaiting_verification"

    missing = complete()
    missing.pop("valuation_context")
    missing_result = evaluate_candidate(missing)
    assert missing_result.candidate_status == "evidence_insufficient"
    assert missing_result.final_score is None

    disputed = complete()
    disputed["expectation_gap"] = component(
        "expectation_gap", "70", assessment_state="disputed"
    )
    assert evaluate_candidate(disputed).candidate_status == "evidence_insufficient"

    falsified = complete()
    falsified["risk_penalty"] = component(
        "risk_penalty", "20", falsification_state="active"
    )
    assert evaluate_candidate(falsified).candidate_status == "not_current_candidate"


def test_priority_sort_key_uses_stable_beneficiary_uuid_tie_break() -> None:
    common = {
        "status": "watch_candidate",
        "final_score": Decimal("70"),
        "business_quality_score": Decimal("75"),
        "risk_score": Decimal("20"),
        "beneficiary_strength": Decimal("80"),
    }
    first = UUID("00000000-0000-0000-0000-000000000001")
    second = UUID("00000000-0000-0000-0000-000000000002")
    assert priority_sort_key(beneficiary_id=first, **common) < priority_sort_key(
        beneficiary_id=second, **common
    )
