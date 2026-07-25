import socket

from scripts.demo_industry_thesis_owner_acceptance import (
    build_industry_thesis_owner_acceptance_demo_payload,
)


def test_owner_acceptance_demo_is_offline_complete_and_unranked(monkeypatch):
    def reject_network(_socket, _address):
        raise AssertionError("owner-acceptance demo must remain offline")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    payload = build_industry_thesis_owner_acceptance_demo_payload()
    assert payload["workflow_state"] == "accepted_outputs_linked"
    assert payload["complete_member_count"] == 3
    assert payload["supported_handoff_count"] == 2
    assert payload["accepted_candidate_pool_revision_present"] is True
    assert payload["assessment_statuses"] == ["supported", "draft", "supported"]
    assert payload["ranking_applied"] is False
    assert len(payload["owner_acceptance_plan_fingerprint_sha256"]) == 64
