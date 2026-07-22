import json
from pathlib import Path
from uuid import uuid4

import pytest

from industry_alpha.normalized_comparison_commands import parse_comparison_command
from industry_alpha.normalized_expectation_commands import parse_expectation_gap_command
from industry_alpha.normalized_financial_commands import parse_observation_command
from industry_alpha.normalized_financial_rules import NormalizedMetricError
from industry_alpha.normalized_valuation_cli import MAX_INPUT_BYTES, _load
from industry_alpha.normalized_valuation_commands import parse_valuation_command


def observation_input(**overrides):
    raw = {
        "observation_key": "revenue-ttm-2026-06-30",
        "company_research_id": str(uuid4()),
        "company_research_revision_id": str(uuid4()),
        "instrument_id": str(uuid4()),
        "instrument_revision_id": str(uuid4()),
        "metric_code": "revenue",
        "source_kind": "research_assumption",
        "observation_state": "supported",
        "value_text": "10000000000",
        "currency_code": "CNY",
        "unit_code": "currency_amount",
        "period_basis": "forward_fy1",
        "target_period_key": "FY2026",
        "accounting_scope": "consolidated",
        "observation_as_of_date": "2026-06-30",
        "period_start_date": "2026-01-01",
        "period_end_date": "2026-12-31",
        "fiscal_year": 2026,
        "rationale": "Explicit analyst assumption.",
        "falsification_condition": "Reported revenue differs materially.",
        "information_cutoff_date": "2026-06-30",
        "recorded_at_utc": "2026-07-01T00:00:00+00:00",
        "recorded_by": "test",
        "claim_revision_ids": [],
        "evidence_links": [],
    }
    raw.update(overrides)
    return raw


def test_observation_parser_is_strict_and_preserves_exact_decimal() -> None:
    parsed = parse_observation_command(observation_input())
    assert parsed["standardized_value_text"] == "10000000000.000000"
    assert parsed["source_kind"] == "research_assumption"

    with pytest.raises(NormalizedMetricError) as exc_info:
        parse_observation_command(observation_input(unexpected="no"))
    assert exc_info.value.code == "normalized_metric_unknown_field"


def test_supported_sourced_observation_requires_claim_and_evidence() -> None:
    with pytest.raises(NormalizedMetricError) as exc_info:
        parse_observation_command(
            observation_input(
                source_kind="consensus",
                rationale=None,
                falsification_condition=None,
            )
        )
    assert exc_info.value.code == "normalized_financial_provenance_required"


def valuation_input(**overrides):
    raw = {
        "metric_key": "instrument-a-pe-2026-06-30",
        "instrument_id": str(uuid4()),
        "instrument_revision_id": str(uuid4()),
        "metric_code": "pe",
        "valuation_as_of_date": "2026-06-30",
        "target_period_key": "TTM-2026-06-20",
        "period_basis": "ttm",
        "accounting_scope": "consolidated_attributable",
        "formula_version": "aquantai.normalized-valuation.v1",
        "canonical_price_revision_id": str(uuid4()),
        "comparison_eligibility_revision_id": str(uuid4()),
        "diluted_shares_revision_id": str(uuid4()),
        "denominator_revision_id": str(uuid4()),
        "information_cutoff_date": "2026-06-30",
        "recorded_at_utc": "2026-07-01T00:00:00+00:00",
        "recorded_by": "test",
    }
    raw.update(overrides)
    return raw


def test_valuation_parser_closes_formula_and_net_debt_contract() -> None:
    assert parse_valuation_command(valuation_input())["metric_code"] == "pe"
    with pytest.raises(NormalizedMetricError):
        parse_valuation_command(valuation_input(net_debt_revision_id=str(uuid4())))
    with pytest.raises(NormalizedMetricError):
        parse_valuation_command(valuation_input(metric_code="ev_ebitda"))


def comparison_input(**overrides):
    subject_revision = str(uuid4())
    raw = {
        "comparison_key": "peer-pe-fy2026",
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
        "rationale": "Explicit analyst peer rationale.",
        "subject_metric_revision_id": subject_revision,
        "information_cutoff_date": "2026-06-30",
        "recorded_at_utc": "2026-07-01T00:00:00+00:00",
        "recorded_by": "test",
        "members": [
            {
                "member_key": "subject",
                "company_research_revision_id": str(uuid4()),
                "instrument_revision_id": str(uuid4()),
                "metric_revision_id": subject_revision,
                "is_subject": True,
                "missing_reason_codes": [],
            },
            {
                "member_key": "peer-b",
                "company_research_revision_id": str(uuid4()),
                "instrument_revision_id": str(uuid4()),
                "metric_revision_id": None,
                "is_subject": False,
                "missing_reason_codes": ["input_missing"],
            },
        ],
    }
    raw.update(overrides)
    return raw


def test_comparison_parser_preserves_complete_explicit_membership() -> None:
    parsed = parse_comparison_command(comparison_input())
    assert [member["member_key"] for member in parsed["members"]] == ["subject", "peer-b"]
    duplicate_subject = comparison_input()
    duplicate_subject["members"][1]["is_subject"] = True
    with pytest.raises(NormalizedMetricError) as exc_info:
        parse_comparison_command(duplicate_subject)
    assert exc_info.value.code == "normalized_comparison_universe_mismatch"


def test_expectation_parser_requires_closed_rule_and_source_kind() -> None:
    raw = {
        "gap_key": "profit-fy2026-consensus",
        "company_research_id": str(uuid4()),
        "company_research_revision_id": str(uuid4()),
        "instrument_id": str(uuid4()),
        "instrument_revision_id": str(uuid4()),
        "metric_code": "net_profit_attributable",
        "target_period_key": "FY2026",
        "expected_source_kind": "consensus",
        "rule_version": "aquantai.normalized-expectation-gap.v1",
        "expected_observation_revision_id": str(uuid4()),
        "actual_observation_revision_id": str(uuid4()),
        "calculation_as_of_date": "2027-03-01",
        "information_cutoff_date": "2027-03-01",
        "recorded_at_utc": "2027-03-02T00:00:00+00:00",
        "recorded_by": "test",
    }
    assert parse_expectation_gap_command(raw)["expected_source_kind"] == "consensus"
    raw["expected_source_kind"] = "social_estimate"
    with pytest.raises(NormalizedMetricError):
        parse_expectation_gap_command(raw)


def test_cli_loader_is_local_bounded_and_requires_object(tmp_path: Path) -> None:
    valid = tmp_path / "valid.json"
    valid.write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert _load(valid) == {"a": 1}

    list_input = tmp_path / "list.json"
    list_input.write_text("[]", encoding="utf-8")
    with pytest.raises(NormalizedMetricError):
        _load(list_input)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"{" + b" " * MAX_INPUT_BYTES + b"}")
    with pytest.raises(NormalizedMetricError):
        _load(oversized)
