from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable
from uuid import UUID, uuid4

import pytest

from industry_alpha.industry_thesis_owner_acceptance import (
    IndustryThesisOwnerAcceptanceService,
)
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    IndustryThesisOwnerAcceptanceError,
)
from industry_alpha.industry_thesis_review import (
    ACCEPTANCE_PLAN_VERSION,
    HISTORICAL_ACCEPTANCE_PLAN_VERSION,
    OWNER_CONTEXT_VERSION,
    OWNER_MAP_MODE,
)


def _owner_context() -> dict[str, str]:
    return {
        "owner_context_contract_version": OWNER_CONTEXT_VERSION,
        "map_mode": OWNER_MAP_MODE,
        "research_case_id": str(uuid4()),
        "industry_map_id": str(uuid4()),
        "industry_map_revision_id": str(uuid4()),
    }


def _normalized(context: dict[str, str]) -> dict[str, Any]:
    return {
        "reviewed_session_revision_id": str(uuid4()),
        "reviewed_plan_fingerprint_sha256": "a" * 64,
        "map_mode": context["map_mode"],
        "research_case_id": context["research_case_id"],
        "industry_map_id": context["industry_map_id"],
        "industry_map_revision_id": context["industry_map_revision_id"],
    }


def _output(context: dict[str, str]) -> SimpleNamespace:
    return SimpleNamespace(
        reviewed_plan_fingerprint_sha256="a" * 64,
        research_case_id=UUID(context["research_case_id"]),
        accepted_industry_map_identity_id=UUID(context["industry_map_id"]),
        accepted_industry_map_revision_id=UUID(
            context["industry_map_revision_id"]
        ),
    )


class _OrderGuardService(IndustryThesisOwnerAcceptanceService):
    """Expose whether core execution reached graph/owner work."""

    def __init__(self, reviewed_plan: dict[str, Any]) -> None:
        self.reviewed_plan = reviewed_plan
        self.graph_or_owner_work_reached = False

    def _lock_and_validate_reviewed(self, session, normalized):
        del session, normalized
        reviewed = SimpleNamespace(id=uuid4())
        identity = SimpleNamespace()
        latest = reviewed
        return reviewed, identity, latest, self.reviewed_plan

    @staticmethod
    def _lock_existing_output(session, *, identity, normalized):
        del session, identity, normalized
        return None

    def _validate_case_and_map(self, *args, **kwargs):
        del args, kwargs
        self.graph_or_owner_work_reached = True
        raise AssertionError("context failure must occur before graph/owner work")


def test_unaccepted_historical_v1_plan_fails_closed() -> None:
    with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
        IndustryThesisOwnerAcceptanceService._validate_reviewed_owner_context(
            {"acceptance_plan_version": HISTORICAL_ACCEPTANCE_PLAN_VERSION}
        )

    assert caught.value.code == "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_NOT_READY"
    assert "explicitly re-review" in (caught.value.detail or "")


def test_v2_owner_context_requires_exact_contract_shape() -> None:
    context = _owner_context()
    reviewed = IndustryThesisOwnerAcceptanceService._validate_reviewed_owner_context(
        {
            "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
            "owner_context": context,
        }
    )
    assert reviewed == context

    malformed = dict(context)
    malformed["unexpected"] = "not-authority"
    with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
        IndustryThesisOwnerAcceptanceService._validate_reviewed_owner_context(
            {
                "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
                "owner_context": malformed,
            }
        )
    assert caught.value.code == "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"


@pytest.mark.parametrize(
    ("field", "replacement", "expected_code"),
    [
        (
            "map_mode",
            "create_new_map",
            "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED",
        ),
        (
            "research_case_id",
            lambda: str(uuid4()),
            "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED",
        ),
        (
            "industry_map_id",
            lambda: str(uuid4()),
            "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED",
        ),
        (
            "industry_map_revision_id",
            lambda: str(uuid4()),
            "INDUSTRY_THESIS_ACCEPTANCE_MAP_REVISION_MISMATCH",
        ),
    ],
)
def test_submitted_owner_context_substitution_is_rejected(
    field: str,
    replacement: str | Callable[[], str],
    expected_code: str,
) -> None:
    context = _owner_context()
    submitted = _normalized(context)
    submitted[field] = replacement() if callable(replacement) else replacement

    with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
        IndustryThesisOwnerAcceptanceService._validate_submitted_owner_context(
            submitted,
            context,
        )
    assert caught.value.code == expected_code


def test_v1_missing_context_stops_before_graph_or_owner_work() -> None:
    service = _OrderGuardService(
        {"acceptance_plan_version": HISTORICAL_ACCEPTANCE_PLAN_VERSION}
    )
    context = _owner_context()

    with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
        service._run(object(), _normalized(context), dry_run=True)

    assert caught.value.code == "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_NOT_READY"
    assert service.graph_or_owner_work_reached is False


def test_v2_substitution_stops_before_graph_or_owner_work() -> None:
    context = _owner_context()
    service = _OrderGuardService(
        {
            "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
            "owner_context": context,
        }
    )
    submitted = _normalized(context)
    submitted["industry_map_revision_id"] = str(uuid4())

    with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
        service._run(object(), submitted, dry_run=True)

    assert caught.value.code == "INDUSTRY_THESIS_ACCEPTANCE_MAP_REVISION_MISMATCH"
    assert service.graph_or_owner_work_reached is False


def test_exact_accepted_v1_output_replay_remains_valid() -> None:
    context = _owner_context()
    normalized = _normalized(context)
    output = _output(context)

    IndustryThesisOwnerAcceptanceService._validate_existing_output_replay(
        output,
        normalized,
        {"acceptance_plan_version": HISTORICAL_ACCEPTANCE_PLAN_VERSION},
    )


def test_v1_output_replay_rejects_context_substitution() -> None:
    context = _owner_context()
    normalized = _normalized(context)
    normalized["industry_map_revision_id"] = str(uuid4())

    with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
        IndustryThesisOwnerAcceptanceService._validate_existing_output_replay(
            _output(context),
            normalized,
            {"acceptance_plan_version": HISTORICAL_ACCEPTANCE_PLAN_VERSION},
        )
    assert caught.value.code == "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_CONFLICT"


def test_v2_output_replay_requires_reviewed_context_match() -> None:
    context = _owner_context()
    normalized = _normalized(context)
    plan_context = dict(context)
    plan_context["industry_map_id"] = str(uuid4())

    with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
        IndustryThesisOwnerAcceptanceService._validate_existing_output_replay(
            _output(context),
            normalized,
            {
                "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
                "owner_context": plan_context,
            },
        )
    assert caught.value.code == "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED"
