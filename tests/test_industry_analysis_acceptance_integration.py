from __future__ import annotations

from datetime import timedelta
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from industry_alpha.industry_thesis_models import IndustryThesisOutputLinkRevision
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


def _committed_golden_fixture():
    fixture = build_golden_fixture()
    client_context = api_client(fixture.database)
    client = client_context.__enter__()
    view = _view(client, fixture.reviewed)
    plan = golden_plan(view)
    preview = _preview(client, fixture.reviewed, plan)
    committed = _commit(
        client,
        fixture.reviewed,
        plan,
        preview["preview_fingerprint_sha256"],
    )
    return fixture, client_context, client, committed


def test_accepted_result_respects_recorded_boundary() -> None:
    fixture, client_context, client, committed = _committed_golden_fixture()
    try:
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
    finally:
        client_context.__exit__(None, None, None)
        fixture.database.engine.dispose()


def test_accepted_result_fails_closed_when_output_revision_is_missing() -> None:
    fixture, client_context, client, committed = _committed_golden_fixture()
    try:
        output_revision_id = UUID(committed["output_link_revision_id"])
        with fixture.database.engine.begin() as connection:
            deleted = connection.execute(
                IndustryThesisOutputLinkRevision.__table__.delete().where(
                    IndustryThesisOutputLinkRevision.id == output_revision_id
                )
            )
        assert deleted.rowcount == 1

        parsed = urlparse(committed["accepted_result_path"])
        boundary = {
            key: values[-1] for key, values in parse_qs(parsed.query).items()
        }
        response = client.get(
            f"/industry-analysis/api/session-revisions/"
            f"{committed['accepted_session_revision_id']}/accepted-result-view",
            params={"session_id": str(fixture.reviewed.session_id), **boundary},
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == (
            "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
        )
    finally:
        client_context.__exit__(None, None, None)
        fixture.database.engine.dispose()
