from copy import deepcopy
from uuid import uuid4

import pytest

from industry_alpha.normalized_comparison_commands import parse_comparison_command
from industry_alpha.normalized_comparison_guarded import (
    validate_comparison_manifest_shape,
)
from industry_alpha.normalized_financial_rules import NormalizedMetricError


def peer_input() -> dict:
    subject_metric = str(uuid4())
    return {
        "comparison_key": "peer-pe-fy2026-guarded",
        "comparison_kind": "peer",
        "subject_company_research_id": str(uuid4()),
        "subject_instrument_id": str(uuid4()),
        "metric_code": "pe",
        "target_period_key": "FY2026",
        "period_basis": "forward_fy1",
        "accounting_scope": "consolidated_attributable",
        "formula_version": "aquantai.normalized-valuation.v1",
        "purpose_code": "normalized_valuation_peer_context_v1",
        "rule_version": "aquantai.normalized-comparison-context.v1",
        "rationale": "Explicit analyst-owned peer membership.",
        "subject_metric_revision_id": subject_metric,
        "information_cutoff_date": "2026-06-30",
        "recorded_at_utc": "2026-07-01T00:00:00Z",
        "recorded_by": "test",
        "expected_latest_revision_id": None,
        "members": [
            {
                "member_key": "subject",
                "company_research_revision_id": str(uuid4()),
                "instrument_revision_id": str(uuid4()),
                "metric_revision_id": subject_metric,
                "is_subject": True,
                "missing_reason_codes": [],
            },
            {
                "member_key": "peer-b",
                "company_research_revision_id": str(uuid4()),
                "instrument_revision_id": str(uuid4()),
                "metric_revision_id": None,
                "is_subject": False,
                "missing_reason_codes": ["loss_making_pe_not_meaningful"],
            },
        ],
    }


def test_guard_accepts_distinct_explicit_peer_revisions() -> None:
    parsed = parse_comparison_command(peer_input())
    validate_comparison_manifest_shape(parsed)


def test_guard_rejects_duplicate_company_research_revision() -> None:
    raw = peer_input()
    raw["members"][1]["company_research_revision_id"] = raw["members"][0][
        "company_research_revision_id"
    ]
    parsed = parse_comparison_command(raw)
    with pytest.raises(NormalizedMetricError) as exc_info:
        validate_comparison_manifest_shape(parsed)
    assert exc_info.value.code == "normalized_comparison_universe_mismatch"


def test_guard_rejects_duplicate_listed_instrument_revision() -> None:
    raw = deepcopy(peer_input())
    raw["members"][1]["instrument_revision_id"] = raw["members"][0][
        "instrument_revision_id"
    ]
    parsed = parse_comparison_command(raw)
    with pytest.raises(NormalizedMetricError) as exc_info:
        validate_comparison_manifest_shape(parsed)
    assert exc_info.value.code == "normalized_comparison_universe_mismatch"
