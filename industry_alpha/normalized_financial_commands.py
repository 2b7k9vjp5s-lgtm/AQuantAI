"""Transactional local-only structured financial observation commands."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price_models import ListedInstrumentRevision
from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem
from industry_alpha.normalized_financial_rules import (
    NormalizedMetricError,
    STRUCTURED_FINANCIAL_RULE_VERSION,
    build_structured_observation,
)
from industry_alpha.normalized_valuation_command_utils import (
    bounded_text,
    decimal_text,
    execute_command,
    integer_value,
    latest_revision,
    parse_date,
    parse_utc,
    parse_uuid,
    require_append_chronology,
    require_expected_latest,
    require_keys,
    require_visible,
)
from industry_alpha.normalized_valuation_models import (
    StructuredFinancialObservation,
    StructuredFinancialObservationClaimLink,
    StructuredFinancialObservationEvidenceLink,
    StructuredFinancialObservationRevision,
)
from industry_alpha.stage2_models import Stage2CompanyResearch, Stage2CompanyResearchRevision


OBSERVATION_FIELDS = {
    "observation_key",
    "company_research_id",
    "company_research_revision_id",
    "instrument_id",
    "instrument_revision_id",
    "metric_code",
    "source_kind",
    "observation_state",
    "value_text",
    "currency_code",
    "unit_code",
    "period_basis",
    "target_period_key",
    "accounting_scope",
    "observation_as_of_date",
    "period_start_date",
    "period_end_date",
    "fiscal_year",
    "effective_start_date",
    "effective_end_date",
    "rationale",
    "falsification_condition",
    "information_cutoff_date",
    "recorded_at_utc",
    "recorded_by",
    "expected_latest_revision_id",
    "claim_revision_ids",
    "evidence_links",
}
OBSERVATION_REQUIRED = OBSERVATION_FIELDS - {
    "value_text",
    "currency_code",
    "period_start_date",
    "fiscal_year",
    "effective_start_date",
    "effective_end_date",
    "rationale",
    "falsification_condition",
    "expected_latest_revision_id",
}


def parse_observation_command(raw: dict[str, Any]) -> dict[str, Any]:
    require_keys(raw, OBSERVATION_FIELDS, OBSERVATION_REQUIRED)
    observation_key = bounded_text(raw["observation_key"], "observation_key", 200)
    company_research_id = parse_uuid(raw["company_research_id"], "company_research_id")
    company_research_revision_id = parse_uuid(
        raw["company_research_revision_id"], "company_research_revision_id"
    )
    instrument_id = parse_uuid(raw["instrument_id"], "instrument_id")
    instrument_revision_id = parse_uuid(raw["instrument_revision_id"], "instrument_revision_id")
    metric_code = bounded_text(raw["metric_code"], "metric_code", 40)
    source_kind = bounded_text(raw["source_kind"], "source_kind", 24)
    observation_state = bounded_text(raw["observation_state"], "observation_state", 24)
    currency_code = bounded_text(raw.get("currency_code"), "currency_code", 3, optional=True)
    unit_code = bounded_text(raw["unit_code"], "unit_code", 32)
    period_basis = bounded_text(raw["period_basis"], "period_basis", 24)
    target_period_key = bounded_text(raw["target_period_key"], "target_period_key", 128)
    accounting_scope = bounded_text(raw["accounting_scope"], "accounting_scope", 40)
    observation_as_of_date = parse_date(
        raw["observation_as_of_date"], "observation_as_of_date"
    )
    period_start_date = parse_date(raw.get("period_start_date"), "period_start_date", optional=True)
    period_end_date = parse_date(raw["period_end_date"], "period_end_date")
    fiscal_year = integer_value(raw.get("fiscal_year"), "fiscal_year", optional=True)
    effective_start_date = parse_date(
        raw.get("effective_start_date"), "effective_start_date", optional=True
    )
    effective_end_date = parse_date(
        raw.get("effective_end_date"), "effective_end_date", optional=True
    )
    rationale = bounded_text(raw.get("rationale"), "rationale", 4000, optional=True)
    falsification = bounded_text(
        raw.get("falsification_condition"),
        "falsification_condition",
        2000,
        optional=True,
    )
    cutoff = parse_date(raw["information_cutoff_date"], "information_cutoff_date")
    recorded_at = parse_utc(raw["recorded_at_utc"], "recorded_at_utc")
    recorded_by = bounded_text(raw["recorded_by"], "recorded_by", 100)
    expected_latest = parse_uuid(
        raw.get("expected_latest_revision_id"),
        "expected_latest_revision_id",
        optional=True,
    )

    built = build_structured_observation(
        instrument_id=str(instrument_id),
        company_research_id=str(company_research_id),
        metric_code=metric_code,
        source_kind=source_kind,
        observation_state=observation_state,
        value_text=raw.get("value_text"),
        currency_code=currency_code,
        unit_code=unit_code,
        period_basis=period_basis,
        target_period_key=target_period_key,
        accounting_scope=accounting_scope,
        observation_as_of_date=observation_as_of_date,
        period_start_date=period_start_date,
        period_end_date=period_end_date,
        fiscal_year=fiscal_year,
        effective_start_date=effective_start_date,
        effective_end_date=effective_end_date,
    )

    if source_kind == "research_assumption" and observation_state == "supported":
        if rationale is None or falsification is None:
            raise NormalizedMetricError(
                "normalized_financial_assumption_invalid",
                "supported research assumption requires rationale and falsification condition",
            )

    claim_ids = _uuid_list(raw["claim_revision_ids"], "claim_revision_ids")
    evidence_links = _evidence_links(raw["evidence_links"])
    if source_kind in {"actual", "guidance", "consensus"} and observation_state == "supported":
        if not claim_ids or not evidence_links:
            raise NormalizedMetricError(
                "normalized_financial_provenance_required",
                "supported sourced observation requires exact claims and evidence links",
            )
    linked_claim_ids = {item["claim_revision_id"] for item in evidence_links}
    if not linked_claim_ids.issubset(set(claim_ids)):
        raise NormalizedMetricError(
            "normalized_financial_provenance_invalid",
            "every evidence link claim must appear in claim_revision_ids",
        )

    return {
        "observation_key": observation_key,
        "company_research_id": company_research_id,
        "company_research_revision_id": company_research_revision_id,
        "instrument_id": instrument_id,
        "instrument_revision_id": instrument_revision_id,
        "metric_code": metric_code,
        "source_kind": source_kind,
        "observation_state": observation_state,
        "source_value_text": built.value_text,
        "standardized_value_text": decimal_text(built.value, 6),
        "value_decimal": built.value,
        "currency_code": currency_code,
        "unit_code": unit_code,
        "period_basis": period_basis,
        "target_period_key": target_period_key,
        "accounting_scope": accounting_scope,
        "observation_as_of_date": observation_as_of_date,
        "period_start_date": period_start_date,
        "period_end_date": period_end_date,
        "fiscal_year": fiscal_year,
        "effective_start_date": effective_start_date,
        "effective_end_date": effective_end_date,
        "rationale": rationale,
        "falsification_condition": falsification,
        "information_cutoff_date": cutoff,
        "recorded_at_utc": recorded_at,
        "recorded_by": recorded_by,
        "expected_latest_revision_id": expected_latest,
        "claim_revision_ids": claim_ids,
        "evidence_links": evidence_links,
    }


def _uuid_list(raw: Any, field: str) -> list[UUID]:
    if not isinstance(raw, list):
        raise NormalizedMetricError(
            "normalized_metric_input_invalid", f"{field} must be an explicit list"
        )
    values = [parse_uuid(value, field) for value in raw]
    if len(set(values)) != len(values):
        raise NormalizedMetricError(
            "normalized_financial_provenance_invalid", f"{field} contains duplicates"
        )
    return values


def _evidence_links(raw: Any) -> list[dict[str, UUID]]:
    if not isinstance(raw, list):
        raise NormalizedMetricError(
            "normalized_metric_input_invalid", "evidence_links must be an explicit list"
        )
    result: list[dict[str, UUID]] = []
    for item in raw:
        require_keys(
            item,
            {"claim_revision_id", "claim_evidence_link_id", "evidence_id"},
            {"claim_revision_id", "claim_evidence_link_id", "evidence_id"},
        )
        result.append(
            {
                "claim_revision_id": parse_uuid(item["claim_revision_id"], "claim_revision_id"),
                "claim_evidence_link_id": parse_uuid(
                    item["claim_evidence_link_id"], "claim_evidence_link_id"
                ),
                "evidence_id": parse_uuid(item["evidence_id"], "evidence_id"),
            }
        )
    signatures = {
        (item["claim_revision_id"], item["claim_evidence_link_id"], item["evidence_id"])
        for item in result
    }
    if len(signatures) != len(result):
        raise NormalizedMetricError(
            "normalized_financial_provenance_invalid", "evidence_links contains duplicates"
        )
    return result


class StructuredFinancialObservationCommandService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_observation(
        self, raw: dict[str, Any], *, dry_run: bool = False
    ) -> dict[str, Any]:
        data = parse_observation_command(raw)
        return execute_command(
            session_factory=self._session_factory,
            kind="structured_financial_observation",
            key=data["observation_key"],
            dry_run=dry_run,
            action=lambda session: self._record(session, data, dry_run),
        )

    def _record(
        self, session: Session, data: dict[str, Any], dry_run: bool
    ) -> dict[str, Any]:
        research_revision = session.get(
            Stage2CompanyResearchRevision, data["company_research_revision_id"]
        )
        instrument_revision = session.get(
            ListedInstrumentRevision, data["instrument_revision_id"]
        )
        if research_revision is None or instrument_revision is None:
            raise NormalizedMetricError(
                "normalized_financial_identity_mismatch",
                "exact company research or instrument revision is missing",
            )
        research = session.get(Stage2CompanyResearch, research_revision.company_research_id)
        if research is None or research.id != data["company_research_id"]:
            raise NormalizedMetricError(
                "normalized_financial_identity_mismatch",
                "company research revision does not match exact identity",
            )
        if instrument_revision.instrument_id != data["instrument_id"]:
            raise NormalizedMetricError(
                "normalized_financial_identity_mismatch",
                "instrument revision does not match exact identity",
            )
        require_visible(
            research_revision, data["information_cutoff_date"], data["recorded_at_utc"]
        )
        require_visible(
            instrument_revision, data["information_cutoff_date"], data["recorded_at_utc"]
        )
        self._validate_provenance(session, data, research.case_id)

        identity = session.scalar(
            select(StructuredFinancialObservation)
            .where(StructuredFinancialObservation.observation_key == data["observation_key"])
            .with_for_update()
        )
        if identity is not None:
            expected_identity = (
                identity.company_research_id == data["company_research_id"]
                and identity.instrument_id == data["instrument_id"]
                and identity.metric_code == data["metric_code"]
                and identity.source_kind == data["source_kind"]
                and identity.target_period_key == data["target_period_key"]
                and identity.accounting_scope == data["accounting_scope"]
                and identity.currency_code == data["currency_code"]
                and identity.unit_code == data["unit_code"]
            )
            if not expected_identity:
                raise NormalizedMetricError(
                    "normalized_financial_identity_mismatch",
                    "observation key is already bound to a different exact identity",
                )

        latest = latest_revision(
            session,
            StructuredFinancialObservationRevision,
            StructuredFinancialObservationRevision.observation_id,
            None if identity is None else identity.id,
        )
        require_expected_latest(data["expected_latest_revision_id"], latest)
        require_append_chronology(
            data["information_cutoff_date"], data["recorded_at_utc"], latest
        )

        identity_id = uuid4() if identity is None else identity.id
        revision_id = uuid4()
        revision_no = 1 if latest is None else latest.revision_no + 1
        if not dry_run:
            if identity is None:
                session.add(
                    StructuredFinancialObservation(
                        id=identity_id,
                        observation_key=data["observation_key"],
                        company_research_id=data["company_research_id"],
                        instrument_id=data["instrument_id"],
                        metric_code=data["metric_code"],
                        source_kind=data["source_kind"],
                        target_period_key=data["target_period_key"],
                        accounting_scope=data["accounting_scope"],
                        currency_code=data["currency_code"],
                        unit_code=data["unit_code"],
                        created_at_utc=data["recorded_at_utc"],
                    )
                )
            session.add(
                StructuredFinancialObservationRevision(
                    id=revision_id,
                    observation_id=identity_id,
                    revision_no=revision_no,
                    company_research_revision_id=data["company_research_revision_id"],
                    instrument_revision_id=data["instrument_revision_id"],
                    observation_state=data["observation_state"],
                    source_value_text=data["source_value_text"],
                    standardized_value_text=data["standardized_value_text"],
                    value_decimal=data["value_decimal"],
                    period_basis=data["period_basis"],
                    period_start_date=data["period_start_date"],
                    period_end_date=data["period_end_date"],
                    fiscal_year=data["fiscal_year"],
                    observation_as_of_date=data["observation_as_of_date"],
                    effective_start_date=data["effective_start_date"],
                    effective_end_date=data["effective_end_date"],
                    rationale=data["rationale"],
                    falsification_condition=data["falsification_condition"],
                    information_cutoff_date=data["information_cutoff_date"],
                    recorded_at_utc=data["recorded_at_utc"],
                    recorded_by=data["recorded_by"],
                    supersedes_revision_id=None if latest is None else latest.id,
                )
            )
            session.add_all(
                [
                    StructuredFinancialObservationClaimLink(
                        id=uuid4(),
                        observation_revision_id=revision_id,
                        position=position,
                        claim_revision_id=claim_id,
                        recorded_at_utc=data["recorded_at_utc"],
                    )
                    for position, claim_id in enumerate(data["claim_revision_ids"])
                ]
            )
            session.add_all(
                [
                    StructuredFinancialObservationEvidenceLink(
                        id=uuid4(),
                        observation_revision_id=revision_id,
                        position=position,
                        claim_revision_id=item["claim_revision_id"],
                        claim_evidence_link_id=item["claim_evidence_link_id"],
                        evidence_id=item["evidence_id"],
                        recorded_at_utc=data["recorded_at_utc"],
                    )
                    for position, item in enumerate(data["evidence_links"])
                ]
            )
            session.flush()

        return {
            "dry_run": dry_run,
            "rule_version": STRUCTURED_FINANCIAL_RULE_VERSION,
            "observation_id": str(identity_id),
            "revision_id": str(revision_id),
            "revision_no": revision_no,
            "metric_code": data["metric_code"],
            "source_kind": data["source_kind"],
            "observation_state": data["observation_state"],
            "standardized_value_text": data["standardized_value_text"],
            "claim_count": len(data["claim_revision_ids"]),
            "evidence_link_count": len(data["evidence_links"]),
        }

    @staticmethod
    def _validate_provenance(
        session: Session, data: dict[str, Any], case_id: UUID
    ) -> None:
        claims: dict[UUID, ClaimRevision] = {}
        for claim_id in data["claim_revision_ids"]:
            revision = session.get(ClaimRevision, claim_id)
            if revision is None:
                raise NormalizedMetricError(
                    "normalized_financial_provenance_missing", "exact claim revision is missing"
                )
            claim = session.get(Claim, revision.claim_id)
            if claim is None or claim.case_id != case_id:
                raise NormalizedMetricError(
                    "normalized_financial_provenance_invalid",
                    "claim does not belong to the exact research case",
                )
            if data["observation_state"] == "supported" and revision.claim_status != "supported":
                raise NormalizedMetricError(
                    "normalized_financial_provenance_invalid",
                    "supported observation requires supported claim revisions",
                )
            require_visible(
                revision, data["information_cutoff_date"], data["recorded_at_utc"]
            )
            claims[claim_id] = revision

        for item in data["evidence_links"]:
            link = session.get(ClaimEvidenceLink, item["claim_evidence_link_id"])
            evidence = session.get(EvidenceItem, item["evidence_id"])
            if (
                link is None
                or evidence is None
                or link.claim_revision_id != item["claim_revision_id"]
                or link.evidence_id != item["evidence_id"]
                or evidence.case_id != case_id
            ):
                raise NormalizedMetricError(
                    "normalized_financial_provenance_invalid",
                    "claim-evidence link does not match the exact research case",
                )
            if data["observation_state"] == "supported" and link.relation != "supports":
                raise NormalizedMetricError(
                    "normalized_financial_provenance_invalid",
                    "supported observation requires supporting claim-evidence links",
                )
            require_visible(
                evidence, data["information_cutoff_date"], data["recorded_at_utc"]
            )
