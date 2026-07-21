import json
from uuid import UUID

import pytest

from industry_alpha.guarded_ai_contracts import GuardedAIInputTooLargeError
from industry_alpha.guarded_ai_manifest import build_guarded_ai_manifest


def _workspace(summary: str = "accepted summary") -> dict:
    research_id = str(UUID(int=1))
    return {
        "as_of_cutoff": "2026-07-21",
        "identity": {
            "company_research_id": research_id,
            "stock_code": "000001.SZ",
            "detail_path": "/private/local/route",
        },
        "frozen_stage1": {
            "candidate_pool": {"candidate_pool_id": str(UUID(int=2))},
            "stock": {"stock_basic_record_id": 7},
        },
        "company_research": {
            "latest_revision": {
                "revision_id": str(UUID(int=3)),
                "summary": summary,
            },
            "detail_path": "/industry-alpha/company-research/private",
        },
        "hypotheses": [],
        "expectations": [],
        "valuation_observations": [],
        "catalysts": [],
        "risks": [],
        "industry_judgments": [],
        "company_judgments": [],
        "evidence_summary": {"conflict_count": 1, "missing_evidence_count": 2},
        "detail_routes": {"company_research": "/private"},
        "notices": {"not_investment_advice": True},
    }


def test_manifest_is_stable_and_excludes_local_routes() -> None:
    workspace = _workspace()
    first = build_guarded_ai_manifest(
        workspace,
        company_research_id=str(UUID(int=1)),
        as_of_cutoff="2026-07-21",
    )
    reordered = dict(reversed(list(workspace.items())))
    second = build_guarded_ai_manifest(
        reordered,
        company_research_id=str(UUID(int=1)),
        as_of_cutoff="2026-07-21",
    )

    assert first.fingerprint == second.fingerprint
    assert first.canonical_json == second.canonical_json
    assert "detail_path" not in first.canonical_json
    assert "detail_routes" not in first.canonical_json
    assert "/private" not in first.canonical_json
    assert first.fingerprint.startswith("sha256:")
    assert len(first.manifest_item_ids) == len(set(first.manifest_item_ids))
    assert "hypotheses" in first.unavailable_sections
    assert "identity" in first.included_sections


def test_manifest_contains_exact_ids_conflicts_and_missing_evidence() -> None:
    manifest = build_guarded_ai_manifest(
        _workspace(),
        company_research_id=str(UUID(int=1)),
        as_of_cutoff="2026-07-21",
    )
    payload = json.loads(manifest.canonical_json)
    serialized = json.dumps(payload, ensure_ascii=False)

    assert str(UUID(int=2)) in serialized
    assert str(UUID(int=3)) in serialized
    assert "conflict_count" in serialized
    assert "missing_evidence_count" in serialized
    assert all(item_id.startswith("manifest:") for item_id in manifest.manifest_item_ids)


def test_manifest_rejects_identity_or_cutoff_mismatch() -> None:
    with pytest.raises(ValueError, match="identity"):
        build_guarded_ai_manifest(
            _workspace(),
            company_research_id=str(UUID(int=9)),
            as_of_cutoff="2026-07-21",
        )
    with pytest.raises(ValueError, match="cutoff"):
        build_guarded_ai_manifest(
            _workspace(),
            company_research_id=str(UUID(int=1)),
            as_of_cutoff="2026-07-20",
        )


def test_manifest_rejects_oversized_input_without_truncation() -> None:
    with pytest.raises(GuardedAIInputTooLargeError):
        build_guarded_ai_manifest(
            _workspace(summary="x" * 70_000),
            company_research_id=str(UUID(int=1)),
            as_of_cutoff="2026-07-21",
        )
