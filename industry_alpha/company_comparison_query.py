"""Deterministic projection for the component-only company comparison matrix."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable
from uuid import UUID

from industry_alpha.company_comparison_contracts import CompanyComparisonContract
from industry_alpha.company_comparison_repository import (
    COMPARISON_QUERY_COUNT,
    TAXONOMY_VERSION,
    CompanyComparisonDataError,
    CompanyComparisonRepository,
    ComparisonReadSet,
)
from industry_alpha.errors import EvidenceLedgerNotFound
from industry_alpha.stage2_query_values import stored_utc, timestamp_text

MODULE_RESPONSE_KEYS = {
    "hypothesis": "hypotheses",
    "expectation": "expectations",
    "valuation": "valuation_contexts",
    "catalyst": "catalysts",
    "risk": "risks",
    "industry_judgment": "industry_judgments",
    "company_judgment": "company_judgments",
}

NOTICES: dict[str, Any] = {
    "read_only": True,
    "research_only": True,
    "not_investment_advice": True,
    "component_only_comparison": True,
    "complete_universe_meaning": (
        "仅完整展示所选候选池修订中已持久化的全部成员，不代表全市场或全行业穷尽覆盖。"
    ),
    "neutral_ordering": "按来源、股票代码、受益公司 ID 的中性标识顺序展示。",
    "no_scores_rankings_or_priority_labels": True,
    "no_canonical_price_or_comparison_eligibility": True,
    "no_valuation_attractiveness_or_expectation_gap": True,
    "no_target_price_expected_return_or_recommendation": True,
    "valuation_context_meaning": (
        "仅展示估值研究方法和状态是否存在；不跨公司比较数值，不形成价格吸引力判断。"
    ),
    "no_hidden_network_requests": True,
}


class CompanyComparisonSelectorError(ValueError):
    """The explicit comparison selector or chronology is invalid."""


class CompanyComparisonQueryService:
    def __init__(self, repository: CompanyComparisonRepository) -> None:
        self._repository = repository

    def get_comparison(
        self,
        candidate_pool_revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> CompanyComparisonContract:
        recorded_boundary = _explicit_utc(as_of_recorded_at_utc)
        header = self._repository.load_header(candidate_pool_revision_id)
        if header is None:
            raise EvidenceLedgerNotFound(
                f"Candidate-pool revision {candidate_pool_revision_id} was not found."
            )
        _validate_header(
            header,
            candidate_pool_revision_id,
            as_of_cutoff,
            recorded_boundary,
        )
        read_set = self._repository.load_components(
            candidate_pool_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=recorded_boundary,
        )
        memberships = _validate_memberships(
            read_set.memberships, header, as_of_cutoff, recorded_boundary
        )
        if not memberships:
            raise CompanyComparisonDataError(
                "selected candidate-pool revision has no persisted memberships"
            )
        research_by_membership = _research_roots_by_membership(
            read_set.research_roots, memberships, header
        )
        research_history = _research_history_by_identity(
            read_set.research_revisions, research_by_membership
        )
        semantic_candidates = _semantic_candidates_by_beneficiary(
            read_set.semantic_revisions, memberships
        )
        assertions_by_revision = _assertions_by_revision(
            read_set.semantic_assertions
        )
        modules_by_research = _modules_by_research(
            read_set.modules, research_history
        )

        rows = []
        for membership in memberships:
            membership_id = _uuid(membership, "candidate_pool_membership_id")
            research = research_by_membership.get(membership_id)
            research_payload = _company_research_payload(
                research,
                research_history,
                modules_by_research,
            )
            semantics_payload = _typed_semantics_payload(
                membership,
                semantic_candidates,
                assertions_by_revision,
            )
            rows.append(
                {
                    "identity": {
                        "candidate_pool_revision_id": str(candidate_pool_revision_id),
                        "candidate_pool_membership_id": str(membership_id),
                        "beneficiary_id": str(_uuid(membership, "beneficiary_id")),
                        "beneficiary_revision_id": str(
                            _uuid(membership, "beneficiary_revision_id")
                        ),
                        "selected_map_revision_id": str(
                            _uuid(membership, "beneficiary_selected_map_revision_id")
                        ),
                        "source": _text(membership, "source"),
                        "stock_code": _text(membership, "stock_code"),
                        "stock_name": _text(
                            membership, "stock_name", allow_empty=True
                        ),
                        "exchange": _text(
                            membership, "exchange", allow_empty=True
                        ),
                        "stock_basic_record_id": _int(
                            membership, "stock_basic_record_id"
                        ),
                    },
                    "legacy_stage1": {
                        "beneficiary_kind": _text(
                            membership, "beneficiary_kind"
                        ),
                        "assessment_status": _text(
                            membership, "beneficiary_assessment_status"
                        ),
                        "revision_no": _int(
                            membership, "beneficiary_revision_no"
                        ),
                        "information_cutoff_date": _date(
                            membership, "beneficiary_information_cutoff_date"
                        ).isoformat(),
                        "recorded_at_utc": timestamp_text(
                            _datetime(membership, "beneficiary_recorded_at_utc")
                        ),
                    },
                    "typed_semantics": semantics_payload,
                    "company_research": research_payload,
                    "detail_routes": {
                        "company_research_page": (
                            None
                            if research is None
                            else "/company-research?company_research_id="
                            + str(_uuid(research, "company_research_id"))
                        ),
                        "company_research_api": (
                            None
                            if research is None
                            else "/company-research/research/"
                            + str(_uuid(research, "company_research_id"))
                            + "/workspace"
                        ),
                        "beneficiary_semantics_api": (
                            "/industry-alpha/beneficiary-semantics/"
                            + str(_uuid(membership, "beneficiary_id"))
                        ),
                    },
                }
            )

        rows.sort(
            key=lambda row: (
                row["identity"]["source"],
                row["identity"]["stock_code"],
                row["identity"]["beneficiary_id"],
            )
        )
        return CompanyComparisonContract(
            selector={
                "candidate_pool_revision_id": str(candidate_pool_revision_id),
                "as_of_cutoff": as_of_cutoff.isoformat(),
                "as_of_recorded_at_utc": timestamp_text(recorded_boundary),
            },
            universe=_universe_payload(header, len(rows)),
            rows=tuple(rows),
            notices=dict(NOTICES),
            query_count=read_set.query_count,
        )


def _validate_header(
    header: dict[str, Any],
    requested_id: UUID,
    as_of_cutoff: date,
    recorded_boundary: datetime,
) -> None:
    if _uuid(header, "candidate_pool_revision_id") != requested_id:
        raise CompanyComparisonDataError(
            "candidate-pool revision identity does not match the request"
        )
    map_id = _uuid(header, "map_id")
    if _uuid(header, "map_revision_map_id") != map_id:
        raise CompanyComparisonDataError(
            "candidate-pool selected map revision belongs to another map"
        )
    pool_cutoff = _date(header, "candidate_pool_information_cutoff_date")
    pool_recorded = stored_utc(
        _datetime(header, "candidate_pool_recorded_at_utc")
    )
    map_cutoff = _date(header, "map_information_cutoff_date")
    map_recorded = stored_utc(_datetime(header, "map_recorded_at_utc"))
    pool_created = stored_utc(
        _datetime(header, "candidate_pool_created_at_utc")
    )
    if as_of_cutoff < pool_cutoff:
        raise CompanyComparisonSelectorError(
            "as_of_cutoff precedes the selected candidate-pool revision"
        )
    if as_of_cutoff < map_cutoff:
        raise CompanyComparisonSelectorError(
            "as_of_cutoff precedes the selected Industry Map revision"
        )
    if recorded_boundary < pool_recorded:
        raise CompanyComparisonSelectorError(
            "as_of_recorded_at_utc precedes the selected candidate-pool revision"
        )
    if recorded_boundary < map_recorded or recorded_boundary < pool_created:
        raise CompanyComparisonSelectorError(
            "as_of_recorded_at_utc precedes required frozen provenance"
        )


def _validate_memberships(
    rows: Iterable[dict[str, Any]],
    header: dict[str, Any],
    as_of_cutoff: date,
    recorded_boundary: datetime,
) -> tuple[dict[str, Any], ...]:
    pool_revision_id = _uuid(header, "candidate_pool_revision_id")
    case_id = _uuid(header, "case_id")
    map_id = _uuid(header, "map_id")
    map_revision_id = _uuid(header, "selected_map_revision_id")
    seen_memberships: set[UUID] = set()
    seen_beneficiaries: set[UUID] = set()
    result = []
    for row in rows:
        membership_id = _uuid(row, "candidate_pool_membership_id")
        beneficiary_id = _uuid(row, "beneficiary_id")
        if membership_id in seen_memberships or beneficiary_id in seen_beneficiaries:
            raise CompanyComparisonDataError(
                "candidate-pool revision contains duplicate exact membership"
            )
        seen_memberships.add(membership_id)
        seen_beneficiaries.add(beneficiary_id)
        if _uuid(row, "candidate_pool_revision_id") != pool_revision_id:
            raise CompanyComparisonDataError("membership belongs to another pool revision")
        if _uuid(row, "beneficiary_case_id") != case_id:
            raise CompanyComparisonDataError("beneficiary case boundary mismatch")
        if _uuid(row, "beneficiary_map_id") != map_id:
            raise CompanyComparisonDataError("beneficiary map boundary mismatch")
        if _uuid(row, "beneficiary_selected_map_revision_id") != map_revision_id:
            raise CompanyComparisonDataError("beneficiary frozen map revision mismatch")
        if _text(row, "stock_record_source") != _text(row, "source"):
            raise CompanyComparisonDataError("stock source provenance mismatch")
        if _text(row, "stock_record_code") != _text(row, "stock_code"):
            raise CompanyComparisonDataError("stock-code provenance mismatch")
        if _date(row, "beneficiary_information_cutoff_date") > as_of_cutoff:
            raise CompanyComparisonDataError(
                "frozen beneficiary revision is outside the comparison cutoff"
            )
        for field in (
            "membership_recorded_at_utc",
            "beneficiary_created_at_utc",
            "beneficiary_recorded_at_utc",
        ):
            if stored_utc(_datetime(row, field)) > recorded_boundary:
                raise CompanyComparisonDataError(
                    "frozen membership provenance is outside the recorded boundary"
                )
        result.append(row)
    result.sort(
        key=lambda row: (
            _text(row, "source"),
            _text(row, "stock_code"),
            str(_uuid(row, "beneficiary_id")),
        )
    )
    return tuple(result)


def _research_roots_by_membership(
    rows: Iterable[dict[str, Any]],
    memberships: Iterable[dict[str, Any]],
    header: dict[str, Any],
) -> dict[UUID, dict[str, Any]]:
    member_map = {
        _uuid(row, "candidate_pool_membership_id"): row for row in memberships
    }
    result: dict[UUID, dict[str, Any]] = {}
    for row in rows:
        membership_id = _uuid(row, "candidate_pool_membership_id")
        member = member_map.get(membership_id)
        if member is None:
            raise CompanyComparisonDataError(
                "Company Research references a membership outside the selected universe"
            )
        if membership_id in result:
            raise CompanyComparisonDataError(
                "multiple Company Research identities attach to one exact membership"
            )
        checks = (
            ("candidate_pool_revision_id", "candidate_pool_revision_id"),
            ("beneficiary_id", "beneficiary_id"),
            ("beneficiary_revision_id", "beneficiary_revision_id"),
            ("selected_map_revision_id", "beneficiary_selected_map_revision_id"),
        )
        for research_field, member_field in checks:
            if _uuid(row, research_field) != _uuid(member, member_field):
                raise CompanyComparisonDataError(
                    f"Company Research frozen {research_field} boundary mismatch"
                )
        if _uuid(row, "candidate_pool_id") != _uuid(header, "candidate_pool_id"):
            raise CompanyComparisonDataError("Company Research pool identity mismatch")
        if _uuid(row, "case_id") != _uuid(header, "case_id"):
            raise CompanyComparisonDataError("Company Research case identity mismatch")
        if _uuid(row, "map_id") != _uuid(header, "map_id"):
            raise CompanyComparisonDataError("Company Research map identity mismatch")
        if _int(row, "stock_basic_record_id") != _int(
            member, "stock_basic_record_id"
        ):
            raise CompanyComparisonDataError("Company Research stock row mismatch")
        if _text(row, "source") != _text(member, "source") or _text(
            row, "stock_code"
        ) != _text(member, "stock_code"):
            raise CompanyComparisonDataError("Company Research stock identity mismatch")
        result[membership_id] = row
    return result


def _research_history_by_identity(
    rows: Iterable[dict[str, Any]],
    research_by_membership: dict[UUID, dict[str, Any]],
) -> dict[UUID, tuple[dict[str, Any], ...]]:
    allowed = {
        _uuid(row, "company_research_id") for row in research_by_membership.values()
    }
    grouped: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
    revision_numbers: dict[UUID, set[int]] = defaultdict(set)
    for row in rows:
        research_id = _uuid(row, "company_research_id")
        if research_id not in allowed:
            raise CompanyComparisonDataError(
                "Company Research revision references an unknown identity"
            )
        revision_no = _int(row, "revision_no")
        if revision_no in revision_numbers[research_id]:
            raise CompanyComparisonDataError(
                "duplicate Company Research revision number"
            )
        revision_numbers[research_id].add(revision_no)
        grouped[research_id].append(row)
    return {
        research_id: tuple(
            sorted(history, key=lambda row: (_int(row, "revision_no"), str(_uuid(row, "revision_id"))))
        )
        for research_id, history in grouped.items()
    }


def _semantic_candidates_by_beneficiary(
    rows: Iterable[dict[str, Any]],
    memberships: Iterable[dict[str, Any]],
) -> dict[UUID, tuple[dict[str, Any], ...]]:
    allowed = {_uuid(row, "beneficiary_id") for row in memberships}
    grouped: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
    seen: set[UUID] = set()
    for row in rows:
        beneficiary_id = _uuid(row, "beneficiary_id")
        revision_id = _uuid(row, "profile_revision_id")
        if beneficiary_id not in allowed:
            raise CompanyComparisonDataError(
                "Typed Semantics references a beneficiary outside the selected universe"
            )
        if revision_id in seen:
            raise CompanyComparisonDataError(
                "duplicate Typed Semantic profile revision"
            )
        seen.add(revision_id)
        grouped[beneficiary_id].append(row)
    return {
        beneficiary_id: tuple(
            sorted(history, key=lambda row: (_int(row, "revision_no"), str(_uuid(row, "profile_revision_id"))))
        )
        for beneficiary_id, history in grouped.items()
    }


def _assertions_by_revision(
    rows: Iterable[dict[str, Any]],
) -> dict[UUID, tuple[dict[str, Any], ...]]:
    grouped: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
    seen: set[UUID] = set()
    for row in rows:
        assertion_id = _uuid(row, "assertion_id")
        if assertion_id in seen:
            raise CompanyComparisonDataError("duplicate semantic assertion")
        seen.add(assertion_id)
        grouped[_uuid(row, "profile_revision_id")].append(row)
    return {
        revision_id: tuple(
            sorted(
                assertions,
                key=lambda row: (
                    _text(row, "field_kind"),
                    _int(row, "position"),
                    _text(row, "assertion_key"),
                ),
            )
        )
        for revision_id, assertions in grouped.items()
    }


def _modules_by_research(
    module_rows: dict[str, tuple[dict[str, Any], ...]],
    research_history: dict[UUID, tuple[dict[str, Any], ...]],
) -> dict[UUID, dict[str, tuple[dict[str, Any], ...]]]:
    visible_revisions = {
        research_id: {_uuid(row, "revision_id") for row in rows}
        for research_id, rows in research_history.items()
    }
    result: dict[UUID, dict[str, tuple[dict[str, Any], ...]]] = defaultdict(dict)
    for module, rows in module_rows.items():
        if module not in MODULE_RESPONSE_KEYS:
            raise CompanyComparisonDataError("unsupported comparison module")
        grouped: dict[UUID, dict[UUID, dict[str, Any]]] = defaultdict(dict)
        frozen_links: dict[tuple[UUID, UUID], set[UUID]] = defaultdict(set)
        for row in rows:
            research_id = _uuid(row, "company_research_id")
            frozen_revision_id = _uuid(row, "company_research_revision_id")
            if research_id not in visible_revisions:
                raise CompanyComparisonDataError(
                    f"{module} references an unknown Company Research identity"
                )
            if frozen_revision_id not in visible_revisions[research_id]:
                raise CompanyComparisonDataError(
                    f"{module} freezes a cutoff-invisible Company Research revision"
                )
            item_id = _uuid(row, "item_id")
            revision_id = _uuid(row, "revision_id")
            frozen_links[(research_id, revision_id)].add(frozen_revision_id)
            current = grouped[research_id].get(item_id)
            if current is None or _int(row, "revision_no") > _int(
                current, "revision_no"
            ):
                grouped[research_id][item_id] = row
            elif _int(row, "revision_no") == _int(current, "revision_no") and revision_id != _uuid(current, "revision_id"):
                raise CompanyComparisonDataError(
                    f"{module} has duplicate latest revision numbers"
                )
        for research_id, items in grouped.items():
            payloads = []
            for row in items.values():
                payload = {
                    key: _json_value(value)
                    for key, value in row.items()
                    if key
                    not in {
                        "created_at_utc",
                        "supersedes_revision_id",
                        "company_research_id",
                        "company_research_revision_id",
                    }
                }
                payload["frozen_company_research_revision_ids"] = tuple(
                    sorted(
                        str(value)
                        for value in frozen_links[
                            (research_id, _uuid(row, "revision_id"))
                        ]
                    )
                )
                payloads.append(payload)
            payloads.sort(key=lambda item: (str(item["item_key"]), str(item["item_id"])))
            result[research_id][module] = tuple(payloads)
    return result


def _typed_semantics_payload(
    membership: dict[str, Any],
    candidates: dict[UUID, tuple[dict[str, Any], ...]],
    assertions_by_revision: dict[UUID, tuple[dict[str, Any], ...]],
) -> dict[str, Any]:
    beneficiary_id = _uuid(membership, "beneficiary_id")
    frozen_beneficiary_revision_id = _uuid(membership, "beneficiary_revision_id")
    frozen_map_revision_id = _uuid(
        membership, "beneficiary_selected_map_revision_id"
    )
    visible = candidates.get(beneficiary_id, ())
    exact = [
        row
        for row in visible
        if _uuid(row, "beneficiary_revision_id")
        == frozen_beneficiary_revision_id
        and _uuid(row, "selected_map_revision_id") == frozen_map_revision_id
    ]
    if not exact:
        return {
            "state": "historical_mismatch" if visible else "missing",
            "profile_revision": None,
            "assertions": {},
            "notices": {
                "newer_or_other_frozen_history_exists": bool(visible),
                "values_hidden_on_mismatch": bool(visible),
            },
        }
    unsupported = [
        row for row in exact if _text(row, "taxonomy_version") != TAXONOMY_VERSION
    ]
    if unsupported:
        raise CompanyComparisonDataError(
            "exact Typed Semantic revision uses an unsupported taxonomy version"
        )
    selected = max(
        exact,
        key=lambda row: (_int(row, "revision_no"), str(_uuid(row, "profile_revision_id"))),
    )
    revision_id = _uuid(selected, "profile_revision_id")
    assertions = assertions_by_revision.get(revision_id, ())
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in assertions:
        field_kind = _text(row, "field_kind")
        grouped[field_kind].append(
            {
                "assertion_id": str(_uuid(row, "assertion_id")),
                "assertion_key": _text(row, "assertion_key"),
                "state_code": _text(row, "state_code"),
                "evidence_state": _text(row, "evidence_state"),
                "subject_text": _text(row, "subject_text", allow_none=True),
                "map_observation_revision_id": _uuid_text(
                    row.get("map_observation_revision_id")
                ),
                "position": _int(row, "position"),
            }
        )
    if "exposure" not in grouped:
        raise CompanyComparisonDataError(
            "exact Typed Semantic revision has no exposure assertion"
        )
    evidence_states = {
        item["evidence_state"] for values in grouped.values() for item in values
    }
    if _text(selected, "overall_status") == "disputed" or "disputed" in evidence_states:
        state = "disputed"
    elif evidence_states and evidence_states == {"not_applicable"}:
        state = "not_applicable"
    else:
        state = "available"
    return {
        "state": state,
        "profile_revision": {
            "profile_id": str(_uuid(selected, "profile_id")),
            "profile_revision_id": str(revision_id),
            "revision_no": _int(selected, "revision_no"),
            "taxonomy_version": _text(selected, "taxonomy_version"),
            "overall_status": _text(selected, "overall_status"),
            "information_cutoff_date": _date(
                selected, "information_cutoff_date"
            ).isoformat(),
            "recorded_at_utc": timestamp_text(
                _datetime(selected, "recorded_at_utc")
            ),
        },
        "assertions": {
            field: tuple(values) for field, values in sorted(grouped.items())
        },
        "notices": {
            "missing_fields": tuple(
                sorted(
                    field
                    for field, values in grouped.items()
                    if any(item["evidence_state"] == "missing" for item in values)
                )
            ),
            "disputed_fields": tuple(
                sorted(
                    field
                    for field, values in grouped.items()
                    if any(item["evidence_state"] == "disputed" for item in values)
                )
            ),
            "not_applicable_fields": tuple(
                sorted(
                    field
                    for field, values in grouped.items()
                    if all(
                        item["evidence_state"] == "not_applicable"
                        for item in values
                    )
                )
            ),
        },
    }


def _company_research_payload(
    research: dict[str, Any] | None,
    history_by_research: dict[UUID, tuple[dict[str, Any], ...]],
    modules_by_research: dict[UUID, dict[str, tuple[dict[str, Any], ...]]],
) -> dict[str, Any]:
    if research is None:
        return {
            "state": "missing",
            "identity": None,
            "latest_revision": None,
            "components": {
                response_key: {"state": "missing", "items": ()}
                for response_key in MODULE_RESPONSE_KEYS.values()
            },
        }
    research_id = _uuid(research, "company_research_id")
    history = history_by_research.get(research_id, ())
    if not history:
        return {
            "state": "missing_at_as_of",
            "identity": {
                "company_research_id": str(research_id),
                "created_at_utc": timestamp_text(
                    _datetime(research, "created_at_utc")
                ),
            },
            "latest_revision": None,
            "components": {
                response_key: {"state": "missing", "items": ()}
                for response_key in MODULE_RESPONSE_KEYS.values()
            },
        }
    latest = history[-1]
    state = (
        "disputed"
        if _text(latest, "conclusion_status") == "disputed"
        else "available"
    )
    components = {}
    module_payloads = modules_by_research.get(research_id, {})
    for module, response_key in MODULE_RESPONSE_KEYS.items():
        items = module_payloads.get(module, ())
        component_state = "missing"
        if items:
            component_state = (
                "disputed"
                if any(
                    item.get("status") == "disputed"
                    or item.get("evidence_state") == "disputed"
                    or item.get("hypothesis_status") == "disputed"
                    for item in items
                )
                else "available"
            )
        components[response_key] = {
            "state": component_state,
            "items": items,
        }
    return {
        "state": state,
        "identity": {
            "company_research_id": str(research_id),
            "created_at_utc": timestamp_text(_datetime(research, "created_at_utc")),
        },
        "latest_revision": {
            "revision_id": str(_uuid(latest, "revision_id")),
            "revision_no": _int(latest, "revision_no"),
            "workflow_state": _text(latest, "workflow_state"),
            "conclusion_status": _text(latest, "conclusion_status"),
            "information_cutoff_date": _date(
                latest, "information_cutoff_date"
            ).isoformat(),
            "recorded_at_utc": timestamp_text(
                _datetime(latest, "recorded_at_utc")
            ),
        },
        "components": components,
    }


def _universe_payload(header: dict[str, Any], member_count: int) -> dict[str, Any]:
    return {
        "candidate_pool_id": str(_uuid(header, "candidate_pool_id")),
        "candidate_pool_revision_id": str(
            _uuid(header, "candidate_pool_revision_id")
        ),
        "candidate_pool_revision_no": _int(
            header, "candidate_pool_revision_no"
        ),
        "candidate_pool_key": _text(header, "candidate_pool_key"),
        "title": _text(header, "candidate_pool_title"),
        "scope": _text(header, "candidate_pool_scope"),
        "case_id": str(_uuid(header, "case_id")),
        "map_id": str(_uuid(header, "map_id")),
        "selected_map_revision_id": str(
            _uuid(header, "selected_map_revision_id")
        ),
        "map_revision_no": _int(header, "map_revision_no"),
        "map_title": _text(header, "map_revision_title"),
        "information_cutoff_date": _date(
            header, "candidate_pool_information_cutoff_date"
        ).isoformat(),
        "recorded_at_utc": timestamp_text(
            _datetime(header, "candidate_pool_recorded_at_utc")
        ),
        "member_count": member_count,
    }


def _explicit_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CompanyComparisonSelectorError(
            "as_of_recorded_at_utc must include an explicit UTC offset"
        )
    normalized = value.astimezone(timezone.utc)
    if value.utcoffset() != timedelta(0):
        raise CompanyComparisonSelectorError(
            "as_of_recorded_at_utc must be expressed in UTC"
        )
    return normalized


def _json_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return timestamp_text(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _uuid(row: dict[str, Any], field: str) -> UUID:
    value = row.get(field)
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise CompanyComparisonDataError(f"required UUID field {field} is invalid") from exc


def _uuid_text(value: Any) -> str | None:
    return None if value is None else str(value)


def _text(
    row: dict[str, Any],
    field: str,
    *,
    allow_empty: bool = False,
    allow_none: bool = False,
) -> str | None:
    value = row.get(field)
    if value is None and allow_none:
        return None
    if not isinstance(value, str):
        raise CompanyComparisonDataError(f"required text field {field} is invalid")
    if not allow_empty and value == "":
        raise CompanyComparisonDataError(f"required text field {field} is empty")
    return value


def _int(row: dict[str, Any], field: str) -> int:
    value = row.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise CompanyComparisonDataError(f"required integer field {field} is invalid")
    return value


def _date(row: dict[str, Any], field: str) -> date:
    value = row.get(field)
    if not isinstance(value, date) or isinstance(value, datetime):
        raise CompanyComparisonDataError(f"required date field {field} is invalid")
    return value


def _datetime(row: dict[str, Any], field: str) -> datetime:
    value = row.get(field)
    if not isinstance(value, datetime):
        raise CompanyComparisonDataError(
            f"required datetime field {field} is invalid"
        )
    return value
