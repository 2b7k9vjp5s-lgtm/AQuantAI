"""Exact read-only downstream explanation projection for assembled research results."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.canonical_price_models import (
    CanonicalPriceRevision,
    ComparisonEligibilityRevision,
)
from industry_alpha.beneficiary_semantics_models import (
    Stage1BeneficiarySemanticAssertion,
    Stage1BeneficiarySemanticProfileRevision,
    Stage1BeneficiarySemanticVerificationItem,
)
from industry_alpha.chain_map_models import (
    IndustryMapObservationRevision,
    IndustryMapRevision,
)
from industry_alpha.investment_candidate_models import (
    InvestmentCandidateComponentInputLink,
    InvestmentCandidateComponentRevision,
)
from industry_alpha.models import ClaimRevision, EvidenceItem
from industry_alpha.stage2_assessments_models import (
    Stage2CatalystAssessmentRevision,
    Stage2RiskAssessmentRevision,
)
from industry_alpha.stage2_expectations_models import (
    Stage2MarketExpectationRevision,
    Stage2ValuationSnapshotRevision,
)
from industry_alpha.stage2_judgments_models import (
    Stage2CompanyJudgmentRevision,
    Stage2IndustryJudgmentRevision,
)
from industry_alpha.stage2_models import (
    Stage2CompanyResearchRevision,
    Stage2FinancialHypothesisRevision,
)
from industry_alpha.industry_research_result_rules import stored_utc


_INPUT_FIELDS: tuple[tuple[str, str, type[Any]], ...] = (
    ("map_revision", "map_revision_id", IndustryMapRevision),
    ("map_observation", "map_observation_revision_id", IndustryMapObservationRevision),
    (
        "beneficiary_semantic",
        "beneficiary_semantic_revision_id",
        Stage1BeneficiarySemanticProfileRevision,
    ),
    (
        "financial_hypothesis",
        "financial_hypothesis_revision_id",
        Stage2FinancialHypothesisRevision,
    ),
    (
        "market_expectation",
        "market_expectation_revision_id",
        Stage2MarketExpectationRevision,
    ),
    ("valuation", "valuation_revision_id", Stage2ValuationSnapshotRevision),
    ("catalyst", "catalyst_revision_id", Stage2CatalystAssessmentRevision),
    ("risk", "risk_revision_id", Stage2RiskAssessmentRevision),
    (
        "industry_judgment",
        "industry_judgment_revision_id",
        Stage2IndustryJudgmentRevision,
    ),
    (
        "company_judgment",
        "company_judgment_revision_id",
        Stage2CompanyJudgmentRevision,
    ),
    (
        "canonical_price",
        "canonical_price_revision_id",
        CanonicalPriceRevision,
    ),
    (
        "comparison_eligibility",
        "comparison_eligibility_revision_id",
        ComparisonEligibilityRevision,
    ),
    ("claim", "claim_revision_id", ClaimRevision),
    ("evidence", "evidence_id", EvidenceItem),
)
_MODEL_BY_KIND = {kind: model for kind, _field, model in _INPUT_FIELDS}
_FIELD_BY_KIND = {kind: field for kind, field, _model in _INPUT_FIELDS}


def _scalar(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _visible(row: Any, *, cutoff: date, recorded_at: datetime) -> bool:
    information = getattr(row, "information_cutoff_date", None)
    if information is None:
        information = getattr(row, "information_date", None)
    recorded = getattr(row, "recorded_at_utc", None)
    if information is not None and information > cutoff:
        return False
    if recorded is not None and stored_utc(recorded) > recorded_at:
        return False
    return True


def _load_exact_rows(
    session: Session,
    model: type[Any],
    ids: set[UUID],
) -> dict[UUID, Any]:
    if not ids:
        return {}
    return {
        row.id: row
        for row in session.scalars(select(model).where(model.id.in_(sorted(ids, key=str))))
    }


def _input_target(link: InvestmentCandidateComponentInputLink) -> tuple[str, UUID]:
    found: list[tuple[str, UUID]] = []
    for kind, field, _model in _INPUT_FIELDS:
        value = getattr(link, field)
        if value is not None:
            found.append((kind, value))
    if len(found) != 1:
        raise ValueError("component input link must contain exactly one exact target")
    return found[0]


def _serialize_semantic_revision(row: Stage1BeneficiarySemanticProfileRevision) -> dict[str, Any]:
    return {
        "revision_id": str(row.id),
        "beneficiary_revision_id": str(row.beneficiary_revision_id),
        "selected_map_revision_id": str(row.selected_map_revision_id),
        "taxonomy_version": row.taxonomy_version,
        "overall_status": row.overall_status,
        "summary": row.summary,
        "information_cutoff_date": row.information_cutoff_date.isoformat(),
        "recorded_at_utc": stored_utc(row.recorded_at_utc).isoformat(),
        "source_layer": "accepted_research_judgment",
    }


def _serialize_semantic_assertion(row: Stage1BeneficiarySemanticAssertion) -> dict[str, Any]:
    return {
        "assertion_id": str(row.id),
        "assertion_key": row.assertion_key,
        "field_kind": row.field_kind,
        "state_code": row.state_code,
        "evidence_state": row.evidence_state,
        "subject_text": row.subject_text,
        "rationale": row.rationale,
        "map_observation_revision_id": _scalar(row.map_observation_revision_id),
        "position": row.position,
        "source_layer": "accepted_research_judgment",
    }


def _serialize_company_research(row: Stage2CompanyResearchRevision) -> dict[str, Any]:
    return {
        "revision_id": str(row.id),
        "company_research_id": str(row.company_research_id),
        "revision_no": row.revision_no,
        "workflow_state": row.workflow_state,
        "conclusion_status": row.conclusion_status,
        "research_question": row.research_question,
        "summary": row.summary,
        "information_cutoff_date": row.information_cutoff_date.isoformat(),
        "recorded_at_utc": stored_utc(row.recorded_at_utc).isoformat(),
        "source_layer": "accepted_research_judgment",
    }


def _target_source_layer(kind: str, row: Any) -> str:
    """Classify only from persisted meaning; never promote derived material to fact."""
    if kind == "claim":
        return (
            "accepted_fact"
            if getattr(row, "claim_kind", None) == "fact"
            else "accepted_research_judgment"
        )
    if kind == "canonical_price":
        return "accepted_fact"
    if kind == "comparison_eligibility":
        return "deterministic_candidate"
    return "accepted_research_judgment"


def _serialize_target(kind: str, row: Any) -> dict[str, Any]:
    common = {
        "kind": kind,
        "revision_id": str(row.id),
        "source_layer": _target_source_layer(kind, row),
    }
    fields: dict[str, tuple[str, ...]] = {
        "map_revision": ("revision_no", "title", "scope", "information_cutoff_date", "recorded_at_utc"),
        "map_observation": ("revision_no", "title", "description", "assertion_status", "information_cutoff_date", "recorded_at_utc"),
        "beneficiary_semantic": ("overall_status", "summary", "taxonomy_version", "information_cutoff_date", "recorded_at_utc"),
        "financial_hypothesis": ("revision_no", "hypothesis_status", "mechanism", "direction", "operating_metric", "financial_statement_line", "expected_lag_horizon", "confidence", "basis", "information_cutoff_date", "recorded_at_utc"),
        "market_expectation": ("revision_no", "company_research_revision_id", "subject", "period_horizon", "expectation_kind", "direction", "status", "confidence", "basis", "information_cutoff_date", "recorded_at_utc"),
        "valuation": ("revision_no", "company_research_revision_id", "valuation_method", "metric_context", "observed_value", "missing_data_reason", "unit", "currency", "comparison_basis", "assumptions", "status", "confidence", "information_cutoff_date", "recorded_at_utc"),
        "catalyst": ("revision_no", "company_research_revision_id", "catalyst_category", "subject", "expected_observation_window", "status", "confidence", "trigger_observation_criteria", "basis", "uncertainty", "information_cutoff_date", "recorded_at_utc"),
        "risk": ("revision_no", "company_research_revision_id", "risk_category", "subject", "downside_path", "thesis_invalidation_condition", "mitigants", "status", "confidence", "basis", "uncertainty", "information_cutoff_date", "recorded_at_utc"),
        "industry_judgment": ("revision_no", "company_research_revision_id", "outcome", "evidence_state", "confidence", "decision_criteria", "rationale", "uncertainty", "follow_up_verification", "driver_durability", "value_pool_direction", "chain_bottleneck_support", "information_cutoff_date", "recorded_at_utc"),
        "company_judgment": ("revision_no", "company_research_revision_id", "outcome", "evidence_state", "confidence", "decision_criteria", "rationale", "uncertainty", "follow_up_verification", "beneficiary_credibility", "financial_transmission_credibility", "execution_risks", "information_cutoff_date", "recorded_at_utc"),
        "canonical_price": ("revision_no", "standardized_value_text", "currency_code", "unit_code", "trade_date", "canonical_status", "conflict_summary", "information_cutoff_date", "recorded_at_utc"),
        "comparison_eligibility": ("revision_no", "rule_version", "state", "reason_codes", "requested_trade_date", "information_cutoff_date", "recorded_at_utc"),
        "claim": ("revision_no", "statement", "claim_kind", "claim_status", "inference_confidence", "inference_basis", "information_cutoff_date", "recorded_at_utc"),
        "evidence": ("evidence_grade", "source_kind", "source_title", "publisher_or_author", "source_locator", "information_date", "recorded_at_utc", "summary"),
    }
    for field in fields[kind]:
        value = getattr(row, field)
        if field == "recorded_at_utc" and value is not None:
            value = stored_utc(value)
        common[field] = _scalar(value)
    return common


def _serialize_component(
    row: InvestmentCandidateComponentRevision,
    *,
    component_code: str,
    inputs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "component_revision_id": str(row.id),
        "component_code": component_code,
        "assessment_state": row.assessment_state,
        "verification_state": row.verification_state,
        "verification_material": row.verification_material,
        "verification_item_code": row.verification_item_code,
        "verification_question": row.verification_question,
        "source_score_text": row.source_score_text,
        "score_value": _scalar(row.score_value),
        "missing_reason": row.missing_reason,
        "rationale": row.rationale,
        "falsification_condition": row.falsification_condition,
        "falsification_state": row.falsification_state,
        "information_cutoff_date": row.information_cutoff_date.isoformat(),
        "recorded_at_utc": stored_utc(row.recorded_at_utc).isoformat(),
        "inputs": inputs,
        "source_layer": "deterministic_candidate",
    }


class ExplainedCompanyProjectionReader:
    """Read only exact frozen downstream revisions for an accepted result."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def explain(
        self,
        members: list[dict[str, Any]],
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        recorded = stored_utc(as_of_recorded_at_utc)
        member_by_revision = {
            UUID(item["beneficiary_revision_id"]): item for item in members
        }

        semantic_ids = {
            UUID(item["semantic_profile_revision_id"])
            for item in members
            if item.get("semantic_profile_revision_id") is not None
        }
        semantic_rows = _load_exact_rows(
            self._session, Stage1BeneficiarySemanticProfileRevision, semantic_ids
        )
        assertions = (
            list(
                self._session.scalars(
                    select(Stage1BeneficiarySemanticAssertion)
                    .where(
                        Stage1BeneficiarySemanticAssertion.profile_revision_id.in_(
                            sorted(semantic_ids, key=str)
                        )
                    )
                    .order_by(
                        Stage1BeneficiarySemanticAssertion.profile_revision_id,
                        Stage1BeneficiarySemanticAssertion.position,
                        Stage1BeneficiarySemanticAssertion.id,
                    )
                )
            )
            if semantic_ids
            else []
        )
        semantic_verifications = (
            list(
                self._session.scalars(
                    select(Stage1BeneficiarySemanticVerificationItem)
                    .where(
                        Stage1BeneficiarySemanticVerificationItem.profile_revision_id.in_(
                            sorted(semantic_ids, key=str)
                        ),
                        Stage1BeneficiarySemanticVerificationItem.recorded_at_utc
                        <= recorded,
                    )
                    .order_by(
                        Stage1BeneficiarySemanticVerificationItem.profile_revision_id,
                        Stage1BeneficiarySemanticVerificationItem.id,
                    )
                )
            )
            if semantic_ids
            else []
        )
        assertions_by_profile: dict[UUID, list[Stage1BeneficiarySemanticAssertion]] = defaultdict(list)
        for row in assertions:
            assertions_by_profile[row.profile_revision_id].append(row)
        verifications_by_profile: dict[UUID, list[Stage1BeneficiarySemanticVerificationItem]] = defaultdict(list)
        for row in semantic_verifications:
            verifications_by_profile[row.profile_revision_id].append(row)

        candidate_members = [
            item["candidate_overlay"]
            for item in members
            if item.get("candidate_overlay") is not None
        ]
        company_research_ids = {
            UUID(item["company_research_revision_id"])
            for item in candidate_members
            if item.get("company_research_revision_id") is not None
        }
        company_research_rows = _load_exact_rows(
            self._session, Stage2CompanyResearchRevision, company_research_ids
        )

        component_ids: set[UUID] = set()
        component_code_by_id: dict[UUID, str] = {}
        component_owner_by_id: dict[UUID, tuple[UUID, UUID | None]] = {}
        for candidate in candidate_members:
            beneficiary_revision_id = UUID(candidate["beneficiary_revision_id"])
            company_research_revision_id = (
                None
                if candidate.get("company_research_revision_id") is None
                else UUID(candidate["company_research_revision_id"])
            )
            for component in candidate.get("components", []):
                component_id = UUID(component["component_revision_id"])
                component_ids.add(component_id)
                component_code_by_id[component_id] = component["component_code"]
                component_owner_by_id[component_id] = (
                    beneficiary_revision_id,
                    company_research_revision_id,
                )
        component_rows = _load_exact_rows(
            self._session, InvestmentCandidateComponentRevision, component_ids
        )
        input_links = (
            list(
                self._session.scalars(
                    select(InvestmentCandidateComponentInputLink)
                    .where(
                        InvestmentCandidateComponentInputLink.component_revision_id.in_(
                            sorted(component_ids, key=str)
                        )
                    )
                    .order_by(
                        InvestmentCandidateComponentInputLink.component_revision_id,
                        InvestmentCandidateComponentInputLink.position,
                        InvestmentCandidateComponentInputLink.id,
                    )
                )
            )
            if component_ids
            else []
        )
        links_by_component: dict[UUID, list[InvestmentCandidateComponentInputLink]] = defaultdict(list)
        target_ids: dict[str, set[UUID]] = {kind: set() for kind in _MODEL_BY_KIND}
        bad_input_components: set[UUID] = set()
        for link in input_links:
            if stored_utc(link.recorded_at_utc) > recorded:
                bad_input_components.add(link.component_revision_id)
                continue
            try:
                kind, target_id = _input_target(link)
            except ValueError:
                bad_input_components.add(link.component_revision_id)
                continue
            links_by_component[link.component_revision_id].append(link)
            target_ids[kind].add(target_id)

        target_rows: dict[str, dict[UUID, Any]] = {
            kind: _load_exact_rows(self._session, model, target_ids[kind])
            for kind, model in _MODEL_BY_KIND.items()
        }

        explained: list[dict[str, Any]] = []
        for beneficiary_revision_id, member in member_by_revision.items():
            missing: list[str] = []
            semantic_projection = None
            semantic_id_text = member.get("semantic_profile_revision_id")
            semantic_assertions: list[dict[str, Any]] = []
            semantic_verification_payload: list[dict[str, Any]] = []
            if semantic_id_text is None:
                missing.append("typed_semantics_missing")
            else:
                semantic_id = UUID(semantic_id_text)
                semantic_row = semantic_rows.get(semantic_id)
                if semantic_row is None:
                    missing.append("typed_semantics_exact_revision_missing")
                elif semantic_row.beneficiary_revision_id != beneficiary_revision_id:
                    missing.append("typed_semantics_beneficiary_mismatch")
                elif not _visible(
                    semantic_row,
                    cutoff=as_of_cutoff,
                    recorded_at=recorded,
                ):
                    missing.append("typed_semantics_exact_revision_not_visible")
                else:
                    semantic_projection = _serialize_semantic_revision(semantic_row)
                    semantic_assertions = [
                        _serialize_semantic_assertion(row)
                        for row in assertions_by_profile.get(semantic_id, [])
                    ]
                    semantic_verification_payload = [
                        {
                            "verification_item_id": str(row.id),
                            "assertion_id": _scalar(row.assertion_id),
                            "verification_question": row.verification_question,
                            "expected_evidence_type": row.expected_evidence_type,
                            "status": row.status,
                            "recorded_at_utc": stored_utc(row.recorded_at_utc).isoformat(),
                            "source_layer": "accepted_research_judgment",
                        }
                        for row in verifications_by_profile.get(semantic_id, [])
                    ]

            candidate = member.get("candidate_overlay")
            company_research_projection = None
            components: list[dict[str, Any]] = []
            sections: dict[str, list[dict[str, Any]]] = {
                "earnings_transmission": [],
                "expectation": [],
                "valuation": [],
                "catalysts": [],
                "risks": [],
                "industry_judgments": [],
                "company_judgments": [],
                "evidence_inputs": [],
            }
            technical_links: list[dict[str, str]] = []
            if candidate is None:
                missing.append("candidate_snapshot_not_selected_or_member_not_present")
            else:
                company_research_id_text = candidate.get("company_research_revision_id")
                expected_company_research_id = (
                    None
                    if company_research_id_text is None
                    else UUID(company_research_id_text)
                )
                if expected_company_research_id is None:
                    missing.append("company_research_exact_revision_missing")
                else:
                    row = company_research_rows.get(expected_company_research_id)
                    if row is None:
                        missing.append("company_research_exact_revision_missing")
                    elif not _visible(
                        row,
                        cutoff=as_of_cutoff,
                        recorded_at=recorded,
                    ):
                        missing.append("company_research_exact_revision_not_visible")
                    else:
                        company_research_projection = _serialize_company_research(row)

                for component_summary in candidate.get("components", []):
                    component_id = UUID(component_summary["component_revision_id"])
                    row = component_rows.get(component_id)
                    expected_beneficiary, expected_company = component_owner_by_id[component_id]
                    if row is None:
                        missing.append(f"component_exact_revision_missing:{component_summary['component_code']}")
                        continue
                    if row.beneficiary_revision_id != expected_beneficiary:
                        missing.append(f"component_beneficiary_mismatch:{component_summary['component_code']}")
                        continue
                    if expected_company is None or row.company_research_revision_id != expected_company:
                        missing.append(f"component_company_research_mismatch:{component_summary['component_code']}")
                        continue
                    if not _visible(row, cutoff=as_of_cutoff, recorded_at=recorded):
                        missing.append(f"component_exact_revision_not_visible:{component_summary['component_code']}")
                        continue
                    if component_id in bad_input_components:
                        missing.append(f"component_input_link_not_visible_or_invalid:{component_summary['component_code']}")
                        continue
                    input_payloads: list[dict[str, Any]] = []
                    for link in links_by_component.get(component_id, []):
                        kind, target_id = _input_target(link)
                        target = target_rows[kind].get(target_id)
                        technical_links.append({"kind": kind, "revision_id": str(target_id)})
                        if target is None:
                            missing.append(f"exact_input_missing:{kind}")
                            input_payloads.append(
                                {
                                    "kind": kind,
                                    "revision_id": str(target_id),
                                    "state": "unavailable",
                                    "reason": "exact_revision_missing",
                                    "source_layer": "missing_or_unavailable",
                                }
                            )
                            continue
                        if not _visible(target, cutoff=as_of_cutoff, recorded_at=recorded):
                            missing.append(f"exact_input_not_visible:{kind}")
                            input_payloads.append(
                                {
                                    "kind": kind,
                                    "revision_id": str(target_id),
                                    "state": "unavailable",
                                    "reason": "exact_revision_not_visible",
                                    "source_layer": "missing_or_unavailable",
                                }
                            )
                            continue
                        linked_company_research_id = getattr(
                            target, "company_research_revision_id", None
                        )
                        if (
                            linked_company_research_id is not None
                            and expected_company is not None
                            and linked_company_research_id != expected_company
                        ):
                            missing.append(f"exact_input_company_research_mismatch:{kind}")
                            input_payloads.append(
                                {
                                    "kind": kind,
                                    "revision_id": str(target_id),
                                    "state": "unavailable",
                                    "reason": "company_research_revision_mismatch",
                                    "source_layer": "missing_or_unavailable",
                                }
                            )
                            continue
                        if kind == "beneficiary_semantic" and getattr(
                            target, "beneficiary_revision_id", None
                        ) != beneficiary_revision_id:
                            missing.append("exact_input_beneficiary_mismatch:beneficiary_semantic")
                            input_payloads.append(
                                {
                                    "kind": kind,
                                    "revision_id": str(target_id),
                                    "state": "unavailable",
                                    "reason": "beneficiary_revision_mismatch",
                                    "source_layer": "missing_or_unavailable",
                                }
                            )
                            continue
                        payload = _serialize_target(kind, target)
                        payload["state"] = "available"
                        input_payloads.append(payload)
                        section = {
                            "financial_hypothesis": "earnings_transmission",
                            "market_expectation": "expectation",
                            "valuation": "valuation",
                            "canonical_price": "valuation",
                            "comparison_eligibility": "valuation",
                            "catalyst": "catalysts",
                            "risk": "risks",
                            "industry_judgment": "industry_judgments",
                            "company_judgment": "company_judgments",
                            "claim": "evidence_inputs",
                            "evidence": "evidence_inputs",
                        }.get(kind)
                        if section is not None:
                            sections[section].append(payload)
                    components.append(
                        _serialize_component(
                            row,
                            component_code=component_code_by_id[component_id],
                            inputs=input_payloads,
                        )
                    )

            product_and_chain = [
                item
                for item in semantic_assertions
                if item["field_kind"] in {"exposure", "driver", "offering"}
            ]
            customer_execution = [
                item
                for item in semantic_assertions
                if item["field_kind"]
                in {"customer", "certification", "capacity", "production", "order"}
            ]
            overall_state = (
                "accepted_snapshot_only"
                if candidate is None
                else (
                    "selected_exact_overlay_partial"
                    if missing
                    else "selected_exact_overlay"
                )
            )
            explained.append(
                {
                    "beneficiary_revision_id": str(beneficiary_revision_id),
                    "overall_state": overall_state,
                    "source_layers": [
                        "accepted_snapshot",
                        "accepted_research_judgment",
                        *(["deterministic_candidate"] if candidate is not None else []),
                    ],
                    "company_research": company_research_projection,
                    "beneficiary_semantics": {
                        "revision": semantic_projection,
                        "assertions": semantic_assertions,
                        "verification_items": semantic_verification_payload,
                    },
                    "product_and_chain": product_and_chain,
                    "customer_certification_capacity_order": customer_execution,
                    **sections,
                    "candidate_explanation": (
                        None
                        if candidate is None
                        else {
                            "candidate_status": candidate["candidate_status"],
                            "priority_ordinal": candidate["priority_ordinal"],
                            "base_score": candidate["base_score"],
                            "business_quality_score": candidate["business_quality_score"],
                            "risk_penalty_points": candidate["risk_penalty_points"],
                            "final_score": candidate["final_score"],
                            "reason_codes": list(candidate["reason_codes"]),
                            "components": components,
                            "source_layer": "deterministic_candidate",
                        }
                    ),
                    "missing_inputs": sorted(set(missing)),
                    "technical_exact_links": sorted(
                        technical_links,
                        key=lambda item: (item["kind"], item["revision_id"]),
                    ),
                }
            )
        return {
            "members": explained,
            "creates_owner_state": False,
            "recomputes_candidate": False,
            "uses_latest_fallback": False,
            "external_network": False,
        }


__all__ = ("ExplainedCompanyProjectionReader",)
