"""Closed v1 contracts for typed beneficiary evidence semantics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

TAXONOMY_VERSION = "aquantai.typed-beneficiary-evidence-semantics.v1"

OVERALL_STATUSES = frozenset({"draft", "supported", "disputed", "rejected"})
EVIDENCE_STATES = frozenset({"supported", "disputed", "missing", "not_applicable"})
CLAIM_RELATIONS = frozenset({"support", "contradict", "context"})

EXPOSURE_STATES = frozenset({"direct", "conditional", "indirect", "conceptual"})
OFFERING_STATES = frozenset(
    {
        "product",
        "material",
        "equipment",
        "service",
        "software",
        "process_capability",
        "capacity_resource",
        "other_explicit",
    }
)
CUSTOMER_STATES = frozenset(
    {
        "unknown",
        "target_identified",
        "technical_contact",
        "sample_or_trial",
        "qualification_in_progress",
        "approved_supplier",
        "commercial_supply",
        "recurring_supply",
        "not_applicable",
    }
)
CERTIFICATION_STATES = frozenset(
    {
        "unknown",
        "not_started",
        "preparation",
        "submitted",
        "testing",
        "approved",
        "suspended_or_expired",
        "rejected",
        "not_applicable",
    }
)
CAPACITY_STATES = frozenset(
    {
        "unknown",
        "announced",
        "funded_or_approved",
        "under_construction",
        "installed",
        "commissioning",
        "operational",
        "expansion_suspended",
        "not_applicable",
    }
)
PRODUCTION_STATES = frozenset(
    {
        "unknown",
        "research_or_lab",
        "pilot",
        "small_batch",
        "ramping",
        "mass_production",
        "stable_mass_production",
        "suspended",
        "not_applicable",
    }
)
ORDER_STATES = frozenset(
    {
        "unknown",
        "inquiry_or_intent",
        "sample_order",
        "framework_agreement",
        "purchase_order",
        "delivery_started",
        "recurring_orders",
        "cancelled_or_expired",
        "not_applicable",
    }
)

DRIVER_SUBTYPES: dict[str, frozenset[str]] = {
    "demand_expansion": frozenset(
        {"end_demand_growth", "capacity_expansion", "mix_upgrade", "replacement_cycle"}
    ),
    "supply_contraction": frozenset(
        {
            "capacity_exit",
            "supply_disruption",
            "input_shortage",
            "compliance_constraint",
            "price_repair",
        }
    ),
    "policy_institutional_change": frozenset(
        {
            "subsidy_or_fiscal_support",
            "procurement_or_localization",
            "access_or_approval",
            "regulation_or_standard",
            "trade_policy",
        }
    ),
    "technology_substitution": frozenset(
        {
            "process_upgrade",
            "material_substitution",
            "equipment_substitution",
            "architecture_shift",
            "domestic_substitution",
        }
    ),
    "event_shock": frozenset(
        {
            "geopolitical",
            "disaster_or_accident",
            "public_health",
            "trade_restriction",
            "temporary_supply_demand_dislocation",
        }
    ),
}
DRIVER_STATES = frozenset(
    f"{driver_type}/{driver_subtype}"
    for driver_type, subtypes in DRIVER_SUBTYPES.items()
    for driver_subtype in subtypes
)

FIELD_STATE_CODES: dict[str, frozenset[str]] = {
    "exposure": EXPOSURE_STATES,
    "driver": DRIVER_STATES,
    "offering": OFFERING_STATES,
    "customer": CUSTOMER_STATES,
    "certification": CERTIFICATION_STATES,
    "capacity": CAPACITY_STATES,
    "production": PRODUCTION_STATES,
    "order": ORDER_STATES,
}
FIELD_KINDS = frozenset(FIELD_STATE_CODES)
SINGLETON_FIELDS = frozenset(
    {"exposure", "customer", "certification", "capacity", "production", "order"}
)
MULTI_FIELDS = frozenset({"driver", "offering"})

SEMANTICS_NOTICES: dict[str, Any] = {
    "read_only": True,
    "purpose": "Local analyst-authored research semantics; not investment advice.",
    "legacy_boundary": (
        "Legacy direct/secondary/potential and typed direct/conditional/indirect/conceptual "
        "are separate recorded judgments and are never automatically mapped."
    ),
    "derivation": {
        "identity_and_chronology": "D0",
        "deterministic_validation_and_counts": "D1",
        "typed_values_and_rationale": "D3 analyst judgment",
    },
    "unsupported": [
        "scores, weights, ranks, probabilities, or recommendations",
        "fair value, target price, expected return, or trading actions",
        "automatic inference from company names, codes, provider text, claims, or AI output",
    ],
}


def split_driver_state(state_code: str) -> tuple[str, str]:
    """Return the reviewed driver type/subtype pair from one closed stored code."""
    if state_code not in DRIVER_STATES:
        raise ValueError("driver state code is not part of the v1 vocabulary")
    driver_type, driver_subtype = state_code.split("/", 1)
    return driver_type, driver_subtype


@dataclass(frozen=True)
class BeneficiarySemanticDetailContract:
    beneficiary: dict[str, Any]
    profile: dict[str, Any]
    as_of_cutoff: str | None
    latest_revision: dict[str, Any]
    revision_history: tuple[dict[str, Any], ...]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
