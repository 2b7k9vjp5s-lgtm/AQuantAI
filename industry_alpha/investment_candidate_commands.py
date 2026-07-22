"""Transactional local-only Investment Candidate Intelligence v1 commands."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from threading import Lock, RLock
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price_models import (
    CanonicalPrice,
    CanonicalPriceRevision,
    CanonicalPriceSeriesRevision,
    ComparisonEligibilityAssessment,
    ComparisonEligibilityMember,
    ComparisonEligibilityRevision,
)
from industry_alpha.beneficiary_semantics_models import (
    Stage1BeneficiarySemanticProfile,
    Stage1BeneficiarySemanticProfileRevision,
)
from industry_alpha.chain_map_models import (
    IndustryMapObservation,
    IndustryMapObservationRevision,
    IndustryMapRevision,
)
from industry_alpha.investment_candidate_models import (
    ASSESSMENT_STATES,
    COMPONENT_CODES,
    FALSIFICATION_STATES,
    VERIFICATION_ITEM_CODES,
    VERIFICATION_STATES,
    InvestmentCandidateComponentAssessment,
    InvestmentCandidateComponentInputLink,
    InvestmentCandidateComponentRevision,
    InvestmentCandidateMember,
    InvestmentCandidateMemberComponentLink,
    InvestmentCandidateMemberReasonCode,
    InvestmentCandidateSnapshot,
    InvestmentCandidateSnapshotRevision,
)
from industry_alpha.investment_candidate_rules import (
    POSITIVE_WEIGHTS,
    PRICE_PURPOSE_CODE,
    PURPOSE_CODE,
    RULE_VERSION,
    ComponentState,
    InvestmentCandidateError,
    decimal_score,
    evaluate_candidate,
    priority_sort_key,
)
from industry_alpha.models import ClaimEvidenceLink, ClaimRevision, EvidenceItem
from industry_alpha.stage1_models import (
    Stage1BeneficiaryRevision,
    Stage1CandidatePool,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)
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
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
    Stage2FinancialHypothesisRevision,
    Stage2ResearchHypothesisLink,
)

_LOCK_GUARD = Lock()
_LOCKS: dict[tuple[str, str], RLock] = {}

INPUT_TARGETS: dict[str, tuple[type[Any], str]] = {
    "map_revision": (IndustryMapRevision, "map_revision_id"),
    "map_observation": (IndustryMapObservationRevision, "map_observation_revision_id"),
    "beneficiary_semantic": (
        Stage1BeneficiarySemanticProfileRevision,
        "beneficiary_semantic_revision_id",
    ),
    "financial_hypothesis": (
        Stage2FinancialHypothesisRevision,
        "financial_hypothesis_revision_id",
    ),
    "market_expectation": (
        Stage2MarketExpectationRevision,
        "market_expectation_revision_id",
    ),
    "valuation": (Stage2ValuationSnapshotRevision, "valuation_revision_id"),
    "catalyst": (Stage2CatalystAssessmentRevision, "catalyst_revision_id"),
    "risk": (Stage2RiskAssessmentRevision, "risk_revision_id"),
    "industry_judgment": (
        Stage2IndustryJudgmentRevision,
        "industry_judgment_revision_id",
    ),
    "company_judgment": (
        Stage2CompanyJudgmentRevision,
        "company_judgment_revision_id",
    ),
    "canonical_price": (CanonicalPriceRevision, "canonical_price_revision_id"),
    "comparison_eligibility": (
        ComparisonEligibilityRevision,
        "comparison_eligibility_revision_id",
    ),
    "claim": (ClaimRevision, "claim_revision_id"),
    "evidence": (EvidenceItem, "evidence_id"),
}

REQUIRED_GROUPS: dict[str, tuple[frozenset[str], ...]] = {
    "industry_opportunity": (
        frozenset({"map_revision"}),
        frozenset({"map_observation", "claim"}),
    ),
    "beneficiary_strength": (frozenset({"beneficiary_semantic"}),),
    "earnings_conversion": (frozenset({"financial_hypothesis"}),),
    "expectation_gap": (frozenset({"market_expectation"}),),
    "valuation_context": (
        frozenset({"valuation"}),
        frozenset({"canonical_price"}),
        frozenset({"comparison_eligibility"}),
    ),
    "catalyst_readiness": (frozenset({"catalyst"}),),
    "evidence_quality": (frozenset({"claim"}), frozenset({"evidence"})),
    "risk_penalty": (frozenset({"risk"}),),
}


def _lock(kind: str, key: str) -> RLock:
    with _LOCK_GUARD:
        return _LOCKS.setdefault((kind, key), RLock())


def _stored_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _parse_utc(value: Any, field: str) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", f"{field} must be ISO UTC"
        ) from exc
    if result.tzinfo is None or result.utcoffset() != timezone.utc.utcoffset(result):
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", f"{field} must be explicit UTC"
        )
    return result.astimezone(timezone.utc)


def _parse_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", f"{field} must be YYYY-MM-DD"
        ) from exc


def _uuid(value: Any, field: str, *, optional: bool = False) -> UUID | None:
    if value is None and optional:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", f"{field} must be an explicit UUID"
        ) from exc


def _text(value: Any, field: str, limit: int, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", f"{field} must be bounded text"
        )
    return value.strip()


def _keys(raw: Any, allowed: set[str], required: set[str]) -> None:
    if not isinstance(raw, dict):
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", "input must be a JSON object"
        )
    unknown = sorted(set(raw) - allowed)
    missing = sorted(required - set(raw))
    if unknown:
        raise InvestmentCandidateError(
            "investment_candidate_unknown_field", f"unknown fields: {', '.join(unknown)}"
        )
    if missing:
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", f"missing fields: {', '.join(missing)}"
        )


def _visible(row: Any, cutoff: date, recorded_at: datetime) -> None:
    information = getattr(row, "information_cutoff_date", None)
    if information is None:
        information = getattr(row, "information_date", None)
    recorded = getattr(row, "recorded_at_utc", None)
    if information is not None and information > cutoff:
        raise InvestmentCandidateError(
            "investment_candidate_later_information", "upstream information exceeds cutoff"
        )
    if recorded is not None and _stored_utc(recorded) > recorded_at:
        raise InvestmentCandidateError(
            "investment_candidate_later_information", "upstream record exceeds recorded boundary"
        )


def _latest(session: Session, model: type[Any], foreign_key: Any, identity_id: UUID | None) -> Any | None:
    if identity_id is None:
        return None
    return session.scalar(
        select(model)
        .where(foreign_key == identity_id)
        .order_by(model.revision_no.desc())
        .limit(1)
        .with_for_update()
    )


def _expected(expected: UUID | None, latest: Any | None) -> None:
    if expected != (None if latest is None else latest.id):
        raise InvestmentCandidateError(
            "investment_candidate_revision_conflict", "expected-latest revision does not match"
        )


def _chronology(cutoff: date, recorded_at: datetime, latest: Any | None) -> None:
    if cutoff > recorded_at.date():
        raise InvestmentCandidateError(
            "investment_candidate_chronology_invalid", "cutoff cannot exceed recorded UTC date"
        )
    if latest is not None and (
        cutoff < latest.information_cutoff_date
        or recorded_at <= _stored_utc(latest.recorded_at_utc)
    ):
        raise InvestmentCandidateError(
            "investment_candidate_chronology_invalid", "append-only chronology must advance"
        )


def _parse_component(raw: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "assessment_key", "beneficiary_id", "beneficiary_revision_id",
        "company_research_revision_id", "component_code", "assessment_state",
        "verification_state", "verification_material", "verification_item_code",
        "verification_question", "score_text", "missing_reason",
        "rationale", "falsification_condition", "falsification_state",
        "information_cutoff_date", "recorded_at_utc", "recorded_by",
        "expected_latest_revision_id", "inputs",
    }
    _keys(
        raw,
        fields,
        fields
        - {
            "verification_item_code",
            "verification_question",
            "score_text",
            "missing_reason",
            "expected_latest_revision_id",
        },
    )
    component = _text(raw["component_code"], "component_code", 32)
    state = _text(raw["assessment_state"], "assessment_state", 24)
    verification = _text(raw["verification_state"], "verification_state", 24)
    falsification = _text(raw["falsification_state"], "falsification_state", 24)
    if component not in COMPONENT_CODES or state not in ASSESSMENT_STATES:
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", "unsupported component or assessment state"
        )
    if verification not in VERIFICATION_STATES or falsification not in FALSIFICATION_STATES:
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", "unsupported verification or falsification state"
        )
    if not isinstance(raw["verification_material"], bool):
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", "verification_material must be boolean"
        )
    verification_item_code = _text(
        raw.get("verification_item_code"), "verification_item_code", 40, optional=True
    )
    verification_question = _text(
        raw.get("verification_question"), "verification_question", 2000, optional=True
    )
    if verification in {"pending", "failed"}:
        if (
            raw["verification_material"] is not True
            or verification_item_code not in VERIFICATION_ITEM_CODES
            or verification_question is None
        ):
            raise InvestmentCandidateError(
                "investment_candidate_verification_invalid",
                "pending or failed verification requires material=true, a closed item code and a question",
            )
    elif (
        raw["verification_material"] is not False
        or verification_item_code is not None
        or verification_question is not None
    ):
        raise InvestmentCandidateError(
            "investment_candidate_verification_invalid",
            "verified or not-applicable verification forbids material state and verification item fields",
        )
    source_text, score = decimal_score(raw.get("score_text"), required=state == "supported")
    missing_reason = _text(raw.get("missing_reason"), "missing_reason", 500, optional=True)
    if state == "missing" and missing_reason is None:
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", "missing component requires missing_reason"
        )
    if state in {"missing", "not_applicable"} and score is not None:
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", "missing component cannot have score"
        )
    if state == "supported" and missing_reason is not None:
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", "supported component cannot have missing_reason"
        )
    raw_inputs = raw["inputs"]
    if not isinstance(raw_inputs, list):
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", "inputs must be an explicit list"
        )
    inputs: list[dict[str, Any]] = []
    for position, item in enumerate(raw_inputs):
        _keys(item, {"kind", "revision_id"}, {"kind", "revision_id"})
        kind = _text(item["kind"], "input.kind", 40)
        if kind not in INPUT_TARGETS:
            raise InvestmentCandidateError(
                "investment_candidate_input_invalid", "unsupported exact input kind"
            )
        inputs.append(
            {"kind": kind, "revision_id": _uuid(item["revision_id"], "input.revision_id"), "position": position}
        )
    if state == "supported" and not inputs:
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", "supported component requires exact inputs"
        )
    cutoff = _parse_date(raw["information_cutoff_date"], "information_cutoff_date")
    recorded_at = _parse_utc(raw["recorded_at_utc"], "recorded_at_utc")
    return {
        "assessment_key": _text(raw["assessment_key"], "assessment_key", 128),
        "beneficiary_id": _uuid(raw["beneficiary_id"], "beneficiary_id"),
        "beneficiary_revision_id": _uuid(raw["beneficiary_revision_id"], "beneficiary_revision_id"),
        "company_research_revision_id": _uuid(raw["company_research_revision_id"], "company_research_revision_id"),
        "component_code": component, "assessment_state": state,
        "verification_state": verification,
        "verification_material": raw["verification_material"],
        "verification_item_code": verification_item_code,
        "verification_question": verification_question,
        "source_score_text": source_text, "score_value": score,
        "missing_reason": missing_reason,
        "rationale": _text(raw["rationale"], "rationale", 4000),
        "falsification_condition": _text(raw["falsification_condition"], "falsification_condition", 2000),
        "falsification_state": falsification, "information_cutoff_date": cutoff,
        "recorded_at_utc": recorded_at,
        "recorded_by": _text(raw["recorded_by"], "recorded_by", 100),
        "expected_latest_revision_id": _uuid(raw.get("expected_latest_revision_id"), "expected_latest_revision_id", optional=True),
        "inputs": inputs,
    }


def _parse_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "snapshot_key", "candidate_pool_id", "candidate_pool_revision_id",
        "purpose_code", "rule_version", "information_cutoff_date", "recorded_at_utc",
        "recorded_by", "expected_latest_revision_id", "members",
    }
    _keys(raw, fields, fields - {"expected_latest_revision_id"})
    purpose = _text(raw["purpose_code"], "purpose_code", 64)
    rule = _text(raw["rule_version"], "rule_version", 96)
    if purpose != PURPOSE_CODE or rule != RULE_VERSION:
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", "unsupported purpose_code or rule_version"
        )
    if not isinstance(raw["members"], list) or not raw["members"]:
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid", "members must be a non-empty list"
        )
    member_fields = {
        "candidate_pool_membership_id", "beneficiary_id", "beneficiary_revision_id",
        "company_research_revision_id", "typed_beneficiary_revision_id",
        "canonical_price_revision_id", "comparison_eligibility_revision_id",
        "component_revision_ids",
    }
    members = []
    for item in raw["members"]:
        _keys(
            item,
            member_fields,
            {"candidate_pool_membership_id", "beneficiary_id", "beneficiary_revision_id", "component_revision_ids"},
        )
        components = item["component_revision_ids"]
        if not isinstance(components, dict) or set(components) - set(COMPONENT_CODES):
            raise InvestmentCandidateError(
                "investment_candidate_input_invalid", "component_revision_ids has unsupported keys"
            )
        members.append(
            {
                "candidate_pool_membership_id": _uuid(item["candidate_pool_membership_id"], "candidate_pool_membership_id"),
                "beneficiary_id": _uuid(item["beneficiary_id"], "beneficiary_id"),
                "beneficiary_revision_id": _uuid(item["beneficiary_revision_id"], "beneficiary_revision_id"),
                "company_research_revision_id": _uuid(item.get("company_research_revision_id"), "company_research_revision_id", optional=True),
                "typed_beneficiary_revision_id": _uuid(item.get("typed_beneficiary_revision_id"), "typed_beneficiary_revision_id", optional=True),
                "canonical_price_revision_id": _uuid(item.get("canonical_price_revision_id"), "canonical_price_revision_id", optional=True),
                "comparison_eligibility_revision_id": _uuid(item.get("comparison_eligibility_revision_id"), "comparison_eligibility_revision_id", optional=True),
                "component_revision_ids": {code: _uuid(value, f"component_revision_ids.{code}") for code, value in components.items()},
            }
        )
    return {
        "snapshot_key": _text(raw["snapshot_key"], "snapshot_key", 128),
        "candidate_pool_id": _uuid(raw["candidate_pool_id"], "candidate_pool_id"),
        "candidate_pool_revision_id": _uuid(raw["candidate_pool_revision_id"], "candidate_pool_revision_id"),
        "purpose_code": purpose, "rule_version": rule,
        "information_cutoff_date": _parse_date(raw["information_cutoff_date"], "information_cutoff_date"),
        "recorded_at_utc": _parse_utc(raw["recorded_at_utc"], "recorded_at_utc"),
        "recorded_by": _text(raw["recorded_by"], "recorded_by", 100),
        "expected_latest_revision_id": _uuid(raw.get("expected_latest_revision_id"), "expected_latest_revision_id", optional=True),
        "members": members,
    }


def _validate_required_groups(component: str, kinds: set[str]) -> None:
    for group in REQUIRED_GROUPS[component]:
        if not kinds.intersection(group):
            raise InvestmentCandidateError(
                "investment_candidate_input_invalid",
                f"supported {component} component lacks required exact input",
            )


def _price_graph(
    session: Session,
    price_revision_id: UUID,
    eligibility_revision_id: UUID,
    cutoff: date,
    recorded_at: datetime,
) -> None:
    price_revision = session.get(CanonicalPriceRevision, price_revision_id)
    eligibility = session.get(ComparisonEligibilityRevision, eligibility_revision_id)
    if price_revision is None or eligibility is None:
        raise InvestmentCandidateError(
            "investment_candidate_price_missing", "exact price or eligibility revision is missing"
        )
    _visible(price_revision, cutoff, recorded_at)
    _visible(eligibility, cutoff, recorded_at)
    assessment = session.get(ComparisonEligibilityAssessment, eligibility.assessment_id)
    linked = session.scalar(
        select(ComparisonEligibilityMember.id).where(
            ComparisonEligibilityMember.eligibility_revision_id == eligibility.id,
            ComparisonEligibilityMember.canonical_price_revision_id == price_revision.id,
        )
    )
    price = session.get(CanonicalPrice, price_revision.canonical_price_id)
    series = session.get(CanonicalPriceSeriesRevision, price_revision.series_revision_id)
    if (
        price_revision.canonical_status != "accepted"
        or eligibility.state != "eligible"
        or assessment is None
        or assessment.purpose_code != PRICE_PURPOSE_CODE
        or linked is None
        or price is None
        or series is None
        or series.status != "accepted"
        or price.series_id != series.series_id
        or price.price_kind != "official_close"
        or price.price_kind != series.price_kind
        or price.adjustment_basis != series.adjustment_basis
        or price.trade_date != price_revision.trade_date
        or price_revision.currency_code != series.currency_code
        or price_revision.unit_code != "currency_per_share"
        or price_revision.unit_code != series.unit_code
    ):
        raise InvestmentCandidateError(
            "investment_candidate_price_ineligible", "price graph is not comparison eligible"
        )
    _visible(series, cutoff, recorded_at)


class InvestmentCandidateCommandService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_component(self, raw: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
        data = _parse_component(raw)
        key = f"{data['beneficiary_id']}:{data['component_code']}:{data['assessment_key']}"
        return self._execute("component", key, dry_run, lambda session: self._component(session, data, dry_run))

    def record_snapshot(self, raw: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
        data = _parse_snapshot(raw)
        key = f"{data['candidate_pool_id']}:{data['purpose_code']}:{data['snapshot_key']}"
        return self._execute("snapshot", key, dry_run, lambda session: self._snapshot(session, data, dry_run))

    def _execute(
        self,
        kind: str,
        key: str,
        dry_run: bool,
        action: Callable[[Session], dict[str, Any]],
    ) -> dict[str, Any]:
        try:
            with _lock(kind, key):
                if dry_run:
                    with self._session_factory() as session:
                        return action(session)
                with self._session_factory.begin() as session:
                    return action(session)
        except IntegrityError as exc:
            raise InvestmentCandidateError(
                "investment_candidate_revision_conflict",
                "investment-candidate history conflicts with accepted history",
            ) from exc

    def _component(self, session: Session, data: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        beneficiary_revision = session.get(Stage1BeneficiaryRevision, data["beneficiary_revision_id"])
        research_revision = session.get(Stage2CompanyResearchRevision, data["company_research_revision_id"])
        if beneficiary_revision is None or beneficiary_revision.beneficiary_id != data["beneficiary_id"]:
            raise InvestmentCandidateError(
                "investment_candidate_identity_mismatch", "beneficiary revision does not match"
            )
        if research_revision is None:
            raise InvestmentCandidateError(
                "investment_candidate_identity_mismatch", "company research revision was not found"
            )
        research = session.get(Stage2CompanyResearch, research_revision.company_research_id)
        if (
            research is None
            or research.beneficiary_id != data["beneficiary_id"]
            or research.beneficiary_revision_id != beneficiary_revision.id
        ):
            raise InvestmentCandidateError(
                "investment_candidate_identity_mismatch", "company research does not bind exact beneficiary"
            )
        _visible(beneficiary_revision, data["information_cutoff_date"], data["recorded_at_utc"])
        _visible(research_revision, data["information_cutoff_date"], data["recorded_at_utc"])

        validated: list[tuple[dict[str, Any], str]] = []
        kinds: set[str] = set()
        claim_ids: set[UUID] = set()
        evidence_ids: set[UUID] = set()
        for item in data["inputs"]:
            model, column = INPUT_TARGETS[item["kind"]]
            row = session.get(model, item["revision_id"])
            if row is None:
                raise InvestmentCandidateError(
                    "investment_candidate_input_missing", "exact component input was not found"
                )
            _visible(row, data["information_cutoff_date"], data["recorded_at_utc"])
            kind = item["kind"]
            if kind == "map_revision" and row.id != research.selected_map_revision_id:
                raise InvestmentCandidateError(
                    "investment_candidate_input_invalid", "map input is not exact selected map revision"
                )
            if kind == "map_observation":
                observation = session.get(IndustryMapObservation, row.observation_id)
                if row.assertion_status != "supported" or observation is None or observation.map_id != research.map_id:
                    raise InvestmentCandidateError(
                        "investment_candidate_input_invalid", "map observation is not supported for exact map"
                    )
            if kind == "beneficiary_semantic":
                profile = session.get(Stage1BeneficiarySemanticProfile, row.profile_id)
                if (
                    profile is None
                    or profile.beneficiary_id != data["beneficiary_id"]
                    or row.beneficiary_revision_id != beneficiary_revision.id
                    or row.selected_map_revision_id != research.selected_map_revision_id
                    or row.overall_status != "supported"
                ):
                    raise InvestmentCandidateError(
                        "investment_candidate_input_invalid", "typed beneficiary revision is incompatible"
                    )
            if kind == "financial_hypothesis":
                link = session.scalar(
                    select(Stage2ResearchHypothesisLink.id).where(
                        Stage2ResearchHypothesisLink.company_research_revision_id == research_revision.id,
                        Stage2ResearchHypothesisLink.hypothesis_revision_id == row.id,
                    )
                )
                if row.hypothesis_status != "supported" or link is None:
                    raise InvestmentCandidateError(
                        "investment_candidate_input_invalid", "financial hypothesis is incompatible"
                    )
            if kind in {"market_expectation", "valuation", "catalyst", "risk"}:
                if row.company_research_revision_id != research_revision.id or row.status != "supported":
                    raise InvestmentCandidateError(
                        "investment_candidate_input_invalid", f"{kind} must be supported for exact research revision"
                    )
            if kind in {"industry_judgment", "company_judgment"}:
                if row.company_research_revision_id != research_revision.id or row.evidence_state != "supported":
                    raise InvestmentCandidateError(
                        "investment_candidate_input_invalid", "quality judgment is incompatible"
                    )
            if kind == "canonical_price" and row.canonical_status != "accepted":
                raise InvestmentCandidateError(
                    "investment_candidate_price_ineligible", "canonical price is not accepted"
                )
            if kind == "comparison_eligibility" and row.state != "eligible":
                raise InvestmentCandidateError(
                    "investment_candidate_price_ineligible", "comparison eligibility is not eligible"
                )
            if kind == "claim":
                if row.claim_status != "supported":
                    raise InvestmentCandidateError(
                        "investment_candidate_input_invalid", "claim revision must be supported"
                    )
                claim_ids.add(row.id)
            if kind == "evidence":
                evidence_ids.add(row.id)
            validated.append((item, column))
            kinds.add(kind)
        if data["assessment_state"] == "supported":
            _validate_required_groups(data["component_code"], kinds)
        if data["component_code"] == "evidence_quality" and data["assessment_state"] == "supported":
            linked_pairs = session.scalar(
                select(ClaimEvidenceLink.id).where(
                    ClaimEvidenceLink.claim_revision_id.in_(claim_ids),
                    ClaimEvidenceLink.evidence_id.in_(evidence_ids),
                ).limit(1)
            )
            if linked_pairs is None:
                raise InvestmentCandidateError(
                    "investment_candidate_input_invalid", "evidence-quality inputs lack exact claim/evidence link"
                )
        if data["component_code"] == "valuation_context" and data["assessment_state"] == "supported":
            canonical = next(item["revision_id"] for item in data["inputs"] if item["kind"] == "canonical_price")
            eligibility = next(item["revision_id"] for item in data["inputs"] if item["kind"] == "comparison_eligibility")
            _price_graph(session, canonical, eligibility, data["information_cutoff_date"], data["recorded_at_utc"])

        identity = session.scalar(
            select(InvestmentCandidateComponentAssessment)
            .where(
                InvestmentCandidateComponentAssessment.beneficiary_id == data["beneficiary_id"],
                InvestmentCandidateComponentAssessment.component_code == data["component_code"],
                InvestmentCandidateComponentAssessment.assessment_key == data["assessment_key"],
            )
            .with_for_update()
        )
        latest = _latest(
            session,
            InvestmentCandidateComponentRevision,
            InvestmentCandidateComponentRevision.component_assessment_id,
            None if identity is None else identity.id,
        )
        _expected(data["expected_latest_revision_id"], latest)
        _chronology(data["information_cutoff_date"], data["recorded_at_utc"], latest)
        next_revision = 1 if latest is None else latest.revision_no + 1
        result = {
            "dry_run": dry_run,
            "assessment_key": data["assessment_key"],
            "component_code": data["component_code"],
            "next_revision_no": next_revision,
            "standardized_score_text": None if data["score_value"] is None else format(data["score_value"], ".2f"),
            "verification_state": data["verification_state"],
            "verification_item_code": data["verification_item_code"],
            "verification_question": data["verification_question"],
            "input_count": len(validated),
        }
        if dry_run:
            return result
        if identity is None:
            identity = InvestmentCandidateComponentAssessment(
                beneficiary_id=data["beneficiary_id"], component_code=data["component_code"],
                assessment_key=data["assessment_key"], created_at_utc=data["recorded_at_utc"],
            )
            session.add(identity)
            session.flush()
        revision = InvestmentCandidateComponentRevision(
            component_assessment_id=identity.id, revision_no=next_revision,
            beneficiary_revision_id=beneficiary_revision.id,
            company_research_revision_id=research_revision.id,
            assessment_state=data["assessment_state"], verification_state=data["verification_state"],
            verification_material=data["verification_material"],
            verification_item_code=data["verification_item_code"],
            verification_question=data["verification_question"],
            source_score_text=data["source_score_text"],
            score_value=data["score_value"], missing_reason=data["missing_reason"], rationale=data["rationale"],
            falsification_condition=data["falsification_condition"], falsification_state=data["falsification_state"],
            information_cutoff_date=data["information_cutoff_date"], recorded_at_utc=data["recorded_at_utc"],
            recorded_by=data["recorded_by"], supersedes_revision_id=None if latest is None else latest.id,
        )
        session.add(revision)
        session.flush()
        for item, column in validated:
            session.add(
                InvestmentCandidateComponentInputLink(
                    component_revision_id=revision.id, position=item["position"],
                    recorded_at_utc=data["recorded_at_utc"], **{column: item["revision_id"]},
                )
            )
        session.flush()
        return {**result, "component_assessment_id": str(identity.id), "component_revision_id": str(revision.id)}

    def _snapshot(self, session: Session, data: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        pool = session.get(Stage1CandidatePool, data["candidate_pool_id"])
        pool_revision = session.get(Stage1CandidatePoolRevision, data["candidate_pool_revision_id"])
        if pool is None or pool_revision is None or pool_revision.candidate_pool_id != pool.id:
            raise InvestmentCandidateError(
                "investment_candidate_universe_mismatch", "exact candidate-pool revision is required"
            )
        _visible(pool_revision, data["information_cutoff_date"], data["recorded_at_utc"])
        persisted = list(
            session.scalars(
                select(Stage1CandidatePoolMembership)
                .where(Stage1CandidatePoolMembership.candidate_pool_revision_id == pool_revision.id)
                .order_by(Stage1CandidatePoolMembership.id)
            )
        )
        expected = {
            (row.id, row.beneficiary_id, row.beneficiary_revision_id) for row in persisted
        }
        supplied = {
            (row["candidate_pool_membership_id"], row["beneficiary_id"], row["beneficiary_revision_id"])
            for row in data["members"]
        }
        if len(supplied) != len(data["members"]) or supplied != expected:
            raise InvestmentCandidateError(
                "investment_candidate_universe_mismatch", "snapshot manifest is not set-equal to exact pool membership"
            )
        prepared = [self._prepare_member(session, row, data) for row in data["members"]]
        ordered = sorted(
            [row for row in prepared if row["result"].candidate_status in {"priority_candidate", "watch_candidate"}],
            key=lambda row: priority_sort_key(
                status=row["result"].candidate_status,
                final_score=row["result"].final_score or Decimal("0"),
                business_quality_score=row["result"].business_quality_score or Decimal("0"),
                risk_score=row["components"]["risk_penalty"].score_value,
                beneficiary_strength=row["components"]["beneficiary_strength"].score_value,
                beneficiary_id=row["manifest"]["beneficiary_id"],
            ),
        )
        for ordinal, row in enumerate(ordered, start=1):
            row["priority_ordinal"] = ordinal

        identity = session.scalar(
            select(InvestmentCandidateSnapshot)
            .where(
                InvestmentCandidateSnapshot.candidate_pool_id == pool.id,
                InvestmentCandidateSnapshot.purpose_code == data["purpose_code"],
                InvestmentCandidateSnapshot.snapshot_key == data["snapshot_key"],
            )
            .with_for_update()
        )
        latest = _latest(
            session, InvestmentCandidateSnapshotRevision,
            InvestmentCandidateSnapshotRevision.snapshot_id,
            None if identity is None else identity.id,
        )
        _expected(data["expected_latest_revision_id"], latest)
        _chronology(data["information_cutoff_date"], data["recorded_at_utc"], latest)
        next_revision = 1 if latest is None else latest.revision_no + 1
        result = {
            "dry_run": dry_run, "snapshot_key": data["snapshot_key"],
            "next_revision_no": next_revision, "member_count": len(prepared),
            "status_counts": dict(sorted(self._status_counts(prepared).items())),
            "ordered_beneficiary_ids": [str(row["manifest"]["beneficiary_id"]) for row in ordered],
        }
        if dry_run:
            return result
        if identity is None:
            identity = InvestmentCandidateSnapshot(
                candidate_pool_id=pool.id, purpose_code=data["purpose_code"],
                snapshot_key=data["snapshot_key"], created_at_utc=data["recorded_at_utc"],
            )
            session.add(identity)
            session.flush()
        snapshot_revision = InvestmentCandidateSnapshotRevision(
            snapshot_id=identity.id, revision_no=next_revision,
            candidate_pool_revision_id=pool_revision.id, purpose_code=data["purpose_code"],
            rule_version=data["rule_version"], information_cutoff_date=data["information_cutoff_date"],
            recorded_at_utc=data["recorded_at_utc"], recorded_by=data["recorded_by"],
            supersedes_revision_id=None if latest is None else latest.id,
        )
        session.add(snapshot_revision)
        session.flush()
        for row in prepared:
            manifest = row["manifest"]
            candidate = row["result"]
            member = InvestmentCandidateMember(
                snapshot_revision_id=snapshot_revision.id,
                candidate_pool_membership_id=manifest["candidate_pool_membership_id"],
                beneficiary_id=manifest["beneficiary_id"], beneficiary_revision_id=manifest["beneficiary_revision_id"],
                company_research_revision_id=manifest["company_research_revision_id"],
                typed_beneficiary_revision_id=manifest["typed_beneficiary_revision_id"],
                canonical_price_revision_id=manifest["canonical_price_revision_id"],
                comparison_eligibility_revision_id=manifest["comparison_eligibility_revision_id"],
                base_score=candidate.base_score, business_quality_score=candidate.business_quality_score,
                risk_penalty_points=candidate.risk_penalty_points, final_score=candidate.final_score,
                candidate_status=candidate.candidate_status,
                priority_ordinal=row.get("priority_ordinal"), recorded_at_utc=data["recorded_at_utc"],
            )
            session.add(member)
            session.flush()
            for code, component_revision in sorted(row["components"].items()):
                weight = POSITIVE_WEIGHTS.get(code, Decimal("0.25"))
                session.add(
                    InvestmentCandidateMemberComponentLink(
                        member_id=member.id, component_code=code,
                        component_revision_id=component_revision.id, rule_weight=weight,
                        contribution_amount=candidate.contributions.get(code),
                        recorded_at_utc=data["recorded_at_utc"],
                    )
                )
            for ordinal, reason in enumerate(candidate.reason_codes):
                session.add(
                    InvestmentCandidateMemberReasonCode(
                        member_id=member.id, reason_code=reason, ordinal=ordinal,
                        recorded_at_utc=data["recorded_at_utc"],
                    )
                )
        session.flush()
        return {**result, "snapshot_id": str(identity.id), "snapshot_revision_id": str(snapshot_revision.id)}

    def _prepare_member(self, session: Session, manifest: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
        cutoff = data["information_cutoff_date"]
        recorded_at = data["recorded_at_utc"]
        beneficiary_revision = session.get(Stage1BeneficiaryRevision, manifest["beneficiary_revision_id"])
        if beneficiary_revision is None or beneficiary_revision.beneficiary_id != manifest["beneficiary_id"]:
            raise InvestmentCandidateError(
                "investment_candidate_universe_mismatch", "beneficiary revision was substituted"
            )
        _visible(beneficiary_revision, cutoff, recorded_at)
        research_revision = None
        if manifest["company_research_revision_id"] is not None:
            research_revision = session.get(Stage2CompanyResearchRevision, manifest["company_research_revision_id"])
            root = None if research_revision is None else session.get(Stage2CompanyResearch, research_revision.company_research_id)
            if (
                research_revision is None or root is None
                or root.candidate_pool_membership_id != manifest["candidate_pool_membership_id"]
                or root.beneficiary_id != manifest["beneficiary_id"]
                or root.beneficiary_revision_id != manifest["beneficiary_revision_id"]
            ):
                raise InvestmentCandidateError(
                    "investment_candidate_universe_mismatch", "company research was substituted"
                )
            _visible(research_revision, cutoff, recorded_at)
        if manifest["typed_beneficiary_revision_id"] is not None:
            semantic = session.get(Stage1BeneficiarySemanticProfileRevision, manifest["typed_beneficiary_revision_id"])
            if semantic is None or semantic.beneficiary_revision_id != manifest["beneficiary_revision_id"]:
                raise InvestmentCandidateError(
                    "investment_candidate_universe_mismatch", "typed beneficiary revision was substituted"
                )
            _visible(semantic, cutoff, recorded_at)

        components: dict[str, InvestmentCandidateComponentRevision] = {}
        states: dict[str, ComponentState] = {}
        for code, revision_id in manifest["component_revision_ids"].items():
            revision = session.get(InvestmentCandidateComponentRevision, revision_id)
            assessment = None if revision is None else session.get(
                InvestmentCandidateComponentAssessment, revision.component_assessment_id
            )
            if (
                revision is None or assessment is None
                or assessment.beneficiary_id != manifest["beneficiary_id"]
                or assessment.component_code != code
                or revision.beneficiary_revision_id != manifest["beneficiary_revision_id"]
                or research_revision is None
                or revision.company_research_revision_id != research_revision.id
            ):
                raise InvestmentCandidateError(
                    "investment_candidate_universe_mismatch", "component revision was substituted"
                )
            _visible(revision, cutoff, recorded_at)
            components[code] = revision
            states[code] = ComponentState(
                code=code, assessment_state=revision.assessment_state,
                verification_state=revision.verification_state,
                verification_material=revision.verification_material,
                falsification_state=revision.falsification_state,
                score=revision.score_value,
            )
        result = evaluate_candidate(states)
        valuation = components.get("valuation_context")
        if valuation is not None and valuation.assessment_state == "supported":
            links = list(
                session.scalars(
                    select(InvestmentCandidateComponentInputLink).where(
                        InvestmentCandidateComponentInputLink.component_revision_id == valuation.id
                    )
                )
            )
            price_ids = [link.canonical_price_revision_id for link in links if link.canonical_price_revision_id]
            eligibility_ids = [link.comparison_eligibility_revision_id for link in links if link.comparison_eligibility_revision_id]
            if len(price_ids) != 1 or len(eligibility_ids) != 1:
                raise InvestmentCandidateError(
                    "investment_candidate_price_ineligible", "valuation component lacks exact price graph"
                )
            if (
                manifest["canonical_price_revision_id"] != price_ids[0]
                or manifest["comparison_eligibility_revision_id"] != eligibility_ids[0]
            ):
                raise InvestmentCandidateError(
                    "investment_candidate_universe_mismatch", "price manifest does not match valuation component"
                )
            _price_graph(session, price_ids[0], eligibility_ids[0], cutoff, recorded_at)
        return {"manifest": manifest, "components": components, "result": result, "priority_ordinal": None}

    @staticmethod
    def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
        result: dict[str, int] = defaultdict(int)
        for row in rows:
            result[row["result"].candidate_status] += 1
        return result
