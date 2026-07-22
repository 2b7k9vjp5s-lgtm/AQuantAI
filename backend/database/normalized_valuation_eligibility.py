"""Slice 5 purpose extension for existing Comparison Eligibility histories."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price import (
    CanonicalPriceCommandService,
    CanonicalPriceError,
    _chronology,
    _eligibility_input,
    _expected,
    _latest,
    _visible_upstream,
)
from backend.database.canonical_price_models import (
    CanonicalPriceRevision,
    ComparisonEligibilityAssessment,
    ComparisonEligibilityMember,
    ComparisonEligibilityRevision,
)

NORMALIZED_VALUATION_PURPOSE = "normalized_valuation_metric_v1"
NORMALIZED_VALUATION_RULE_VERSION = (
    "aquantai.comparison-eligibility.normalized-valuation-metric.v1"
)


class NormalizedValuationEligibilityCommandService(CanonicalPriceCommandService):
    """Record the one additional reviewed eligibility purpose for Slice 5."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        super().__init__(session_factory)

    def record_eligibility(
        self, raw: dict[str, Any], *, dry_run: bool = False
    ) -> dict[str, Any]:
        data = _eligibility_input(raw)
        if data["purpose_code"] != NORMALIZED_VALUATION_PURPOSE:
            raise CanonicalPriceError(
                "eligibility_invalid",
                "this bounded service accepts only normalized_valuation_metric_v1",
            )
        return self._execute(
            "eligibility",
            f"{data['assessment_key']}:{data['purpose_code']}",
            dry_run,
            lambda session: self._record_normalized_eligibility(
                session, data, dry_run
            ),
        )

    def _record_normalized_eligibility(
        self, session: Session, data: dict[str, Any], dry_run: bool
    ) -> dict[str, Any]:
        prices: list[CanonicalPriceRevision] = []
        for price_id in data["canonical_price_revision_ids"]:
            row = session.get(CanonicalPriceRevision, price_id)
            if row is None:
                raise CanonicalPriceError(
                    "canonical_price_missing",
                    "exact canonical price revision was not found",
                )
            _visible_upstream(row, data)
            prices.append(row)
        _validate_normalized_valuation_eligibility(data, prices)

        identity = session.scalar(
            select(ComparisonEligibilityAssessment)
            .where(
                ComparisonEligibilityAssessment.assessment_key
                == data["assessment_key"],
                ComparisonEligibilityAssessment.purpose_code
                == data["purpose_code"],
            )
            .with_for_update()
        )
        latest = _latest(
            session,
            ComparisonEligibilityRevision,
            "assessment_id",
            None if identity is None else identity.id,
        )
        _expected(data["expected_latest_revision_id"], latest)
        _chronology(data, latest)
        result = {
            "dry_run": dry_run,
            "assessment_key": data["assessment_key"],
            "purpose_code": data["purpose_code"],
            "rule_version": data["rule_version"],
            "next_revision_no": 1 if latest is None else latest.revision_no + 1,
            "state": data["state"],
            "reason_codes": list(data["reason_codes"]),
            "member_count": len(prices),
        }
        if dry_run:
            return result

        if identity is None:
            identity = ComparisonEligibilityAssessment(
                assessment_key=data["assessment_key"],
                purpose_code=data["purpose_code"],
                created_at_utc=data["recorded_at_utc"],
            )
            session.add(identity)
            session.flush()
        revision = ComparisonEligibilityRevision(
            assessment_id=identity.id,
            revision_no=result["next_revision_no"],
            rule_version=data["rule_version"],
            state=data["state"],
            reason_codes=list(data["reason_codes"]),
            requested_trade_date=data["requested_trade_date"],
            recorded_by=data["recorded_by"],
            information_cutoff_date=data["information_cutoff_date"],
            recorded_at_utc=data["recorded_at_utc"],
            supersedes_revision_id=None if latest is None else latest.id,
        )
        session.add(revision)
        session.flush()
        session.add_all(
            [
                ComparisonEligibilityMember(
                    eligibility_revision_id=revision.id,
                    position=position,
                    canonical_price_revision_id=price.id,
                    recorded_at_utc=data["recorded_at_utc"],
                )
                for position, price in enumerate(prices)
            ]
        )
        session.flush()
        return {
            **result,
            "assessment_id": str(identity.id),
            "eligibility_revision_id": str(revision.id),
        }


def _validate_normalized_valuation_eligibility(
    data: dict[str, Any], prices: list[CanonicalPriceRevision]
) -> None:
    if data["rule_version"] != NORMALIZED_VALUATION_RULE_VERSION:
        raise CanonicalPriceError(
            "eligibility_invalid",
            "rule_version is not accepted for normalized valuation",
        )
    if data["state"] == "not_applicable":
        raise CanonicalPriceError(
            "eligibility_invalid",
            "the normalized valuation purpose cannot use not_applicable",
        )
    if data["state"] == "eligible":
        if not prices or any(
            price.canonical_status != "accepted"
            or price.trade_date != data["requested_trade_date"]
            for price in prices
        ):
            raise CanonicalPriceError(
                "eligibility_invalid",
                "eligible members must be accepted prices for the requested trade date",
            )
        required = (
            "canonical_price_accepted",
            "source_numeric_fidelity_disclosed",
        )
        if data["reason_codes"] != required:
            raise CanonicalPriceError(
                "eligibility_invalid",
                "eligible state requires exactly the accepted and fidelity reason codes",
            )
    elif prices and data["state"] == "missing":
        raise CanonicalPriceError(
            "eligibility_invalid", "missing state cannot have members"
        )
    if data["state"] == "conflicting" and not any(
        price.canonical_status == "conflicting" for price in prices
    ):
        raise CanonicalPriceError(
            "eligibility_invalid",
            "conflicting state requires a conflicting canonical price member",
        )
    if "canonical_price_rejected" in data["reason_codes"] and not any(
        price.canonical_status == "rejected" for price in prices
    ):
        raise CanonicalPriceError(
            "eligibility_invalid",
            "rejected reason requires a rejected canonical price member",
        )
    if data["state"] == "stale" and not any(
        price.trade_date != data["requested_trade_date"] for price in prices
    ):
        raise CanonicalPriceError(
            "eligibility_invalid",
            "stale state requires a member outside the requested trade date",
        )
    required_reason = {
        "missing": {"canonical_price_missing", "canonical_price_not_visible"},
        "stale": {"stale_for_requested_context"},
        "conflicting": {"canonical_price_conflicting"},
        "ineligible": {
            "canonical_price_rejected",
            "instrument_revision_mismatch",
            "market_missing",
            "exchange_missing",
            "currency_missing",
            "unit_mismatch",
            "price_kind_mismatch",
            "adjustment_basis_mismatch",
            "trade_date_mismatch",
            "source_contract_mismatch",
            "source_run_not_succeeded",
        },
    }.get(data["state"])
    if required_reason is not None and not required_reason.intersection(
        data["reason_codes"]
    ):
        raise CanonicalPriceError(
            "eligibility_invalid",
            "eligibility state lacks a compatible reason code",
        )
