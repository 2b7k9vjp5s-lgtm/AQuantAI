"""Offline production-adapter demo for Personal Research Workbench UI Phase 2B."""

from __future__ import annotations

import json
from copy import deepcopy

from backend.api.industry_analysis import _exact_continuation
from scripts.demo_industry_analysis_workbench import run_demo as run_workbench_demo


def run_demo() -> dict:
    workbench = run_workbench_demo()
    visible = deepcopy(workbench["history"]["sessions"][0])
    visible["workflow_state"] = "draft"
    draft = _exact_continuation(visible)
    assert draft["kind"] == "scope"
    assert draft["path"] is not None
    assert visible["session_id"] in draft["path"]
    assert visible["visible_latest_revision_id"] in draft["path"]
    assert visible["information_cutoff_date"] in draft["path"]

    states = {}
    for workflow_state in (
        "candidate_build_ready",
        "awaiting_review",
        "reviewed_plan_ready",
    ):
        item = deepcopy(visible)
        item["workflow_state"] = workflow_state
        states[workflow_state] = _exact_continuation(item)
        assert states[workflow_state]["path"] is not None

    newest_stopped = deepcopy(visible)
    newest_stopped["workflow_state"] = "abandoned"
    older_reviewable = deepcopy(visible)
    older_reviewable["workflow_state"] = "awaiting_review"
    ordered_history = [newest_stopped, older_reviewable]
    projected = [
        {**item, "continuation": _exact_continuation(item)}
        for item in ordered_history
    ]
    assert projected[0]["continuation"]["kind"] == "unavailable"
    assert projected[0]["continuation"]["path"] is None
    assert projected[1]["continuation"]["kind"] == "candidate_review"
    assert projected[1]["continuation"]["path"] is not None

    malformed = deepcopy(visible)
    malformed["visible_latest_revision_id"] = "invalid"
    malformed_projection = _exact_continuation(malformed)
    assert malformed_projection["kind"] == "unavailable"
    assert malformed_projection["path"] is None
    assert malformed_projection["reason_code"] == "malformed_exact_metadata"

    return {
        "exact_history_first_record": visible,
        "draft_continuation": draft,
        "other_continuations": states,
        "no_skipping_order": projected,
        "malformed_fail_closed": malformed_projection,
        "notices": {
            "single_existing_history_owner": True,
            "external_network": False,
            "automatic_navigation": False,
            "accepted_owner_write": False,
            "not_investment_advice": True,
        },
    }


def main() -> None:
    print(json.dumps(run_demo(), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
