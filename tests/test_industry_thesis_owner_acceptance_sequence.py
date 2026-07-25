from __future__ import annotations

from uuid import uuid4

import pytest

from industry_alpha.industry_thesis_owner_acceptance import (
    IndustryThesisOwnerAcceptanceService,
)
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    OWNER_ACCEPTANCE_PLAN_VERSION,
    IndustryThesisOwnerAcceptanceError,
    normalize_owner_acceptance_plan,
)


class _FailSessionFactory:
    def __call__(self):
        raise AssertionError("invalid sequence must fail before opening a Session")

    def begin(self):
        raise AssertionError("invalid sequence must fail before opening a transaction")


def _plan(sequences: list[int]) -> dict:
    bindings = []
    for index, sequence in enumerate(sequences):
        bindings.append(
            {
                "reviewed_candidate_revision_id": str(uuid4()),
                "sequence": sequence,
                "stage1_operation": "reuse_exact_beneficiary_revision",
                "stage1": {
                    "beneficiary_id": str(uuid4()),
                    "beneficiary_revision_id": str(uuid4()),
                    "stock_basic_record_id": index + 1,
                },
                "semantic_operation": "none",
                "semantic": None,
                "readiness_note": "Sequence validation fixture.",
            }
        )
    return {
        "reviewed_session_revision_id": str(uuid4()),
        "expected_session_latest_revision_number": 1,
        "reviewed_plan_fingerprint_sha256": "a" * 64,
        "research_case_id": str(uuid4()),
        "map_mode": "reuse_exact_existing_map_revision",
        "industry_map_id": str(uuid4()),
        "industry_map_revision_id": str(uuid4()),
        "candidate_owner_bindings": bindings,
        "candidate_pool_operation": {"mode": "none_no_supported_members"},
        "output_title": "Sequence validation fixture",
        "output_scope": "Contract-only fixture.",
        "information_cutoff_date": "2026-07-09",
        "revision_note": "Reject non-dense sequence before writes.",
        "owner_acceptance_plan_version": OWNER_ACCEPTANCE_PLAN_VERSION,
    }


@pytest.mark.parametrize("sequences", ([1], [0, 2]))
def test_non_dense_sequence_is_rejected_before_preview_or_commit_writes(
    sequences: list[int],
) -> None:
    raw = _plan(sequences)

    with pytest.raises(IndustryThesisOwnerAcceptanceError) as normalized_error:
        normalize_owner_acceptance_plan(raw)
    assert normalized_error.value.code == (
        "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE"
    )
    assert normalized_error.value.detail == (
        "candidate owner binding sequence must be dense from zero"
    )

    service = IndustryThesisOwnerAcceptanceService(_FailSessionFactory())  # type: ignore[arg-type]
    preview = service.preview(raw)
    assert preview["commit_ready"] is False
    assert preview["preview_fingerprint_sha256"] is None
    assert preview["blocked_reasons"][0]["code"] == (
        "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE"
    )

    with pytest.raises(IndustryThesisOwnerAcceptanceError) as commit_error:
        service.commit({**raw, "preview_fingerprint_sha256": "b" * 64})
    assert commit_error.value.code == (
        "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE"
    )
