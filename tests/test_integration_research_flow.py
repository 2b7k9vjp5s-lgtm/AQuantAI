from agent import RESEARCH_DISCLAIMER
from backend.safety import validate_allowed_actions, validate_research_text
from scripts.demo_research_flow import build_demo_payload


def test_demo_flow_builds_report_and_dashboard_payloads() -> None:
    payload = build_demo_payload()

    assert set(payload) == {"report", "dashboard"}
    assert payload["report"]["disclaimer"] == RESEARCH_DISCLAIMER
    assert payload["dashboard"]["disclaimer"] == RESEARCH_DISCLAIMER
    assert payload["dashboard"]["read_only"] is True


def test_dashboard_preserves_report_source_refs() -> None:
    payload = build_demo_payload()
    report_refs = set(payload["report"]["source_refs"])
    dashboard_refs = set(payload["dashboard"]["source_refs"])
    report_view_refs = set(payload["dashboard"]["sections"]["research_report_summary"]["source_refs"])

    assert report_refs
    assert report_refs.issubset(dashboard_refs)
    assert report_refs.issubset(report_view_refs)


def test_demo_flow_exposes_no_disallowed_actions_or_advice_language() -> None:
    payload = build_demo_payload()

    validate_allowed_actions(payload["dashboard"]["allowed_actions"])
    validate_research_text(payload)
    assert not {"trade", "order", "buy", "sell", "hold"} & set(payload["dashboard"]["allowed_actions"])


def test_safety_rules_reject_disallowed_actions_and_text() -> None:
    try:
        validate_allowed_actions(["view", "order"])
    except ValueError as exc:
        assert "disallowed actions" in str(exc)
    else:
        raise AssertionError("Expected disallowed action validation failure")

    try:
        validate_research_text("This is a recommendation to buy.")
    except ValueError as exc:
        assert "investment-advice wording" in str(exc)
    else:
        raise AssertionError("Expected disallowed text validation failure")
