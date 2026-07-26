from __future__ import annotations

from scripts.run_industry_thesis_ordinary_user_acceptance_fixture import run_demo


def test_offline_demo_proves_golden_zero_supported_and_query_ceilings() -> None:
    result = run_demo()
    golden = result["golden_path"]
    zero = result["zero_supported_path"]

    assert golden["complete_universe_count"] == 3
    assert golden["supported_handoff_count"] == 2
    assert golden["candidate_pool_mode"] == "create_supported_handoff"
    assert golden["assessment_statuses"] == ["supported", "draft", "supported"]
    assert golden["semantic_covered_count"] == 1
    assert golden["preview_zero_writes"] is True
    assert golden["acceptance_view_sql_statements"] <= 14
    assert golden["accepted_result_sql_statements"] <= 10
    assert golden["company_research_created"] is False

    assert zero["complete_universe_count"] == 2
    assert zero["supported_handoff_count"] == 0
    assert zero["candidate_pool_mode"] == "none_no_supported_members"
    assert zero["accepted_candidate_pool_revision_id"] is None
    assert zero["zero_supported_notice"]
    assert result["notices"]["external_network"] is False
    assert result["notices"]["provider_or_ai"] is False
    assert result["notices"]["recommendation_or_trading"] is False
