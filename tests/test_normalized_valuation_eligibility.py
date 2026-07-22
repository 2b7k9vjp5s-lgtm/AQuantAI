from datetime import date
from types import SimpleNamespace

import pytest

from backend.database.canonical_price import CanonicalPriceError
from backend.database.normalized_valuation_eligibility import (
    NORMALIZED_VALUATION_PURPOSE,
    NORMALIZED_VALUATION_RULE_VERSION,
    _validate_normalized_valuation_eligibility,
)


def accepted_price(**overrides):
    values = {
        "canonical_status": "accepted",
        "trade_date": date(2026, 6, 30),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def eligibility_input(**overrides):
    values = {
        "purpose_code": NORMALIZED_VALUATION_PURPOSE,
        "rule_version": NORMALIZED_VALUATION_RULE_VERSION,
        "state": "eligible",
        "requested_trade_date": date(2026, 6, 30),
        "reason_codes": (
            "canonical_price_accepted",
            "source_numeric_fidelity_disclosed",
        ),
    }
    values.update(overrides)
    return values


def test_normalized_valuation_eligibility_accepts_exact_reviewed_contract() -> None:
    _validate_normalized_valuation_eligibility(
        eligibility_input(), [accepted_price()]
    )


def test_normalized_valuation_eligibility_rejects_wrong_rule_or_price_date() -> None:
    with pytest.raises(CanonicalPriceError, match="rule_version"):
        _validate_normalized_valuation_eligibility(
            eligibility_input(rule_version="wrong"), [accepted_price()]
        )
    with pytest.raises(CanonicalPriceError, match="requested trade date"):
        _validate_normalized_valuation_eligibility(
            eligibility_input(), [accepted_price(trade_date=date(2026, 6, 29))]
        )


def test_normalized_valuation_eligibility_requires_exact_eligible_reasons() -> None:
    with pytest.raises(CanonicalPriceError, match="exactly"):
        _validate_normalized_valuation_eligibility(
            eligibility_input(reason_codes=("canonical_price_accepted",)),
            [accepted_price()],
        )


def test_non_eligible_states_remain_fail_closed() -> None:
    with pytest.raises(CanonicalPriceError, match="cannot have members"):
        _validate_normalized_valuation_eligibility(
            eligibility_input(
                state="missing",
                reason_codes=("canonical_price_missing",),
            ),
            [accepted_price()],
        )
    with pytest.raises(CanonicalPriceError, match="conflicting canonical price"):
        _validate_normalized_valuation_eligibility(
            eligibility_input(
                state="conflicting",
                reason_codes=("canonical_price_conflicting",),
            ),
            [accepted_price()],
        )
