from __future__ import annotations

from datetime import timedelta
import json
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from sqlalchemy import update

from industry_alpha.industry_thesis_models import IndustryThesisSessionRevision
from scripts.run_industry_thesis_ordinary_user_acceptance_fixture import (
    BASE_TIME,
    CUTOFF,
    _commit,
    _preview,
    _view,
    api_client,
    build_golden_fixture,
    golden_plan,
    run_demo,
)


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


def test_accepted_result_respects_recorded_boundary_and_fails_closed_on_corruption() -> None:
    fixture = build_golden_fixture()
    try:
        with api_client(fixture.database) as client:
            view = _view(client, fixture.reviewed)
            plan = golden_plan(view)
            preview = _preview(client, fixture.reviewed, plan)
            committed = _commit(
                client,
                fixture.reviewed,
                plan,
                preview["preview_fingerprint_sha256"],
            )

            early = client.get(
                f"/industry-analysis/api/session-revisions/"
                f"{committed['accepted_session_revision_id']}/accepted-result-view",
                params={
                    "session_id": str(fixture.reviewed.session_id),
                    "as_of_cutoff": CUTOFF.isoformat(),
                    "as_of_recorded_at_utc": (
                        BASE_TIME + timedelta(seconds=2)
                    ).isoformat(),
                },
            )
            assert early.status_code == 422
            assert early.json()["detail"]["code"] == (
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )

            with fixture.database.factory.begin() as session:
                session.execute(
                    update(IndustryThesisSessionRevision)
                    .where(
                        IndustryThesisSessionRevision.id
                        == UUID(committed["accepted_session_revision_id"])
                    )
                    .values(draft_graph_json=json.dumps({"corrupt": True}))
                )

            parsed = urlparse(committed["accepted_result_path"])
            boundary = {
                key: values[-1] for key, values in parse_qs(parsed.query).items()
            }
            corrupt = client.get(
                f"/industry-analysis/api/session-revisions/"
                f"{committed['accepted_session_revision_id']}/accepted-result-view",
                params={"session_id": str(fixture.reviewed.session_id), **boundary},
            )
            assert corrupt.status_code == 422
            assert corrupt.json()["detail"]["code"] == (
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )
    finally:
        fixture.database.engine.dispose()
