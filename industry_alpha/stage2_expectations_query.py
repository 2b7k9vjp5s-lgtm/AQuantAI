"""Cutoff-aware v0.6B expectation and valuation read models."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerNotVisible
from industry_alpha.stage2_expectations_contracts import (
    Stage2ExpectationDetailContract,
    Stage2ExpectationListContract,
    Stage2ValuationDetailContract,
    Stage2ValuationListContract,
)
from industry_alpha.stage2_expectations_repository import (
    Stage2ExpectationRepository,
    Stage2ExpectationRows,
    Stage2ValuationRows,
)

V06B_NOTICES = {
    "read_only": True,
    "research_only": True,
    "fixture_or_local_data": True,
    "not_investment_advice": True,
    "no_scores_weights_rankings_or_recommendations": True,
    "no_target_price_fair_value_expected_return_or_upside": True,
    "description": (
        "v0.6B stores append-only expectation and valuation observations bound to "
        "exact Stage 2 research, claim, evidence and optional local price provenance. "
        "It is not a target-price, fair-value, ranking, signal, or recommendation engine."
    ),
}


class Stage2ExpectationQueryService:
    def __init__(self, repository: Stage2ExpectationRepository) -> None:
        self._repository = repository

    def list_expectations(
        self, *, company_research_id: UUID | None = None, as_of_cutoff: date | None = None
    ) -> Stage2ExpectationListContract:
        payload = []
        for identity in self._repository.list_expectations(company_research_id):
            if not _recorded_visible(identity.created_at_utc, as_of_cutoff):
                continue
            rows = self._repository.load_expectation(identity.id)
            if rows is None:
                continue
            revisions = _visible_revisions(rows.revisions, as_of_cutoff)
            if not revisions:
                continue
            payload.append(
                {
                    "expectation_id": str(identity.id),
                    "company_research_id": str(identity.company_research_id),
                    "expectation_key": identity.expectation_key,
                    "created_at_utc": _timestamp(identity.created_at_utc),
                    "latest_revision": self._revision_payload(rows, revisions[-1], as_of_cutoff),
                }
            )
        payload.sort(key=lambda item: (item["expectation_key"], item["expectation_id"]))
        return Stage2ExpectationListContract(_date(as_of_cutoff), tuple(payload), V06B_NOTICES)

    def get_expectation(
        self, expectation_id: UUID, *, as_of_cutoff: date | None = None
    ) -> Stage2ExpectationDetailContract:
        rows = self._repository.load_expectation(expectation_id)
        if rows is None:
            raise EvidenceLedgerNotFound(f"Stage 2 expectation {expectation_id} was not found.")
        if not _recorded_visible(rows.expectation.created_at_utc, as_of_cutoff):
            raise EvidenceLedgerNotVisible("expectation is not visible at the requested cutoff.")
        history = tuple(
            self._revision_payload(rows, item, as_of_cutoff)
            for item in _visible_revisions(rows.revisions, as_of_cutoff)
        )
        if not history:
            raise EvidenceLedgerNotVisible("expectation has no visible revision.")
        conflicts = tuple(
            sorted(
                (
                    conflict
                    for revision in history
                    for conflict in revision["conflicts"]
                ),
                key=lambda item: (item["claim_key"], item["evidence_id"]),
            )
        )
        missing = tuple(
            sorted(
                (
                    item
                    for revision in history
                    for item in revision["missing_evidence"]
                ),
                key=lambda item: (item["claim_key"], item["claim_revision_id"]),
            )
        )
        return Stage2ExpectationDetailContract(
            expectation={
                "expectation_id": str(rows.expectation.id),
                "company_research_id": str(rows.expectation.company_research_id),
                "expectation_key": rows.expectation.expectation_key,
                "created_at_utc": _timestamp(rows.expectation.created_at_utc),
            },
            as_of_cutoff=_date(as_of_cutoff),
            latest_revision=history[-1],
            revision_history=history,
            conflicts=conflicts,
            missing_evidence=missing,
            notices=V06B_NOTICES,
        )

    @staticmethod
    def _revision_payload(
        rows: Stage2ExpectationRows, revision: Any, cutoff: date | None
    ) -> dict[str, Any]:
        evidence = _evidence_payload(rows, revision.id, "expectation", cutoff)
        return {
            "revision_id": str(revision.id),
            "company_research_revision_id": str(revision.company_research_revision_id),
            "revision_no": revision.revision_no,
            "subject": revision.subject,
            "period_horizon": revision.period_horizon,
            "expectation_kind": revision.expectation_kind,
            "direction": revision.direction,
            "status": revision.status,
            "confidence": revision.confidence,
            "basis": revision.basis,
            "information_cutoff_date": _date(revision.information_cutoff_date),
            "recorded_at_utc": _timestamp(revision.recorded_at_utc),
            "supersedes_revision_id": _uuid(revision.supersedes_revision_id),
            "frozen_hypothesis_revision_ids": _ids(
                link.hypothesis_revision_id
                for link in rows.hypothesis_links
                if link.expectation_revision_id == revision.id and _recorded_visible(link.recorded_at_utc, cutoff)
            ),
            "claims": evidence["claims"],
            "evidence_grade_counts": evidence["evidence_grade_counts"],
            "conflicts": evidence["conflicts"],
            "missing_evidence": evidence["missing_evidence"],
        }


class Stage2ValuationQueryService:
    def __init__(self, repository: Stage2ExpectationRepository) -> None:
        self._repository = repository

    def list_valuations(
        self, *, company_research_id: UUID | None = None, as_of_cutoff: date | None = None
    ) -> Stage2ValuationListContract:
        payload = []
        for identity in self._repository.list_valuations(company_research_id):
            if not _recorded_visible(identity.created_at_utc, as_of_cutoff):
                continue
            rows = self._repository.load_valuation(identity.id)
            if rows is None:
                continue
            revisions = _visible_revisions(rows.revisions, as_of_cutoff)
            if not revisions:
                continue
            payload.append(
                {
                    "valuation_id": str(identity.id),
                    "company_research_id": str(identity.company_research_id),
                    "valuation_key": identity.valuation_key,
                    "created_at_utc": _timestamp(identity.created_at_utc),
                    "latest_revision": self._revision_payload(rows, revisions[-1], as_of_cutoff),
                }
            )
        payload.sort(key=lambda item: (item["valuation_key"], item["valuation_id"]))
        return Stage2ValuationListContract(_date(as_of_cutoff), tuple(payload), V06B_NOTICES)

    def get_valuation(
        self, valuation_id: UUID, *, as_of_cutoff: date | None = None
    ) -> Stage2ValuationDetailContract:
        rows = self._repository.load_valuation(valuation_id)
        if rows is None:
            raise EvidenceLedgerNotFound(f"Stage 2 valuation {valuation_id} was not found.")
        if not _recorded_visible(rows.valuation.created_at_utc, as_of_cutoff):
            raise EvidenceLedgerNotVisible("valuation snapshot is not visible at the requested cutoff.")
        history = tuple(
            self._revision_payload(rows, item, as_of_cutoff)
            for item in _visible_revisions(rows.revisions, as_of_cutoff)
        )
        if not history:
            raise EvidenceLedgerNotVisible("valuation snapshot has no visible revision.")
        conflicts = tuple(
            sorted(
                (conflict for revision in history for conflict in revision["conflicts"]),
                key=lambda item: (item["claim_key"], item["evidence_id"]),
            )
        )
        missing = tuple(
            sorted(
                (item for revision in history for item in revision["missing_evidence"]),
                key=lambda item: (item["claim_key"], item["claim_revision_id"]),
            )
        )
        return Stage2ValuationDetailContract(
            valuation={
                "valuation_id": str(rows.valuation.id),
                "company_research_id": str(rows.valuation.company_research_id),
                "valuation_key": rows.valuation.valuation_key,
                "created_at_utc": _timestamp(rows.valuation.created_at_utc),
            },
            as_of_cutoff=_date(as_of_cutoff),
            latest_revision=history[-1],
            revision_history=history,
            conflicts=conflicts,
            missing_evidence=missing,
            notices=V06B_NOTICES,
        )

    @staticmethod
    def _revision_payload(
        rows: Stage2ValuationRows, revision: Any, cutoff: date | None
    ) -> dict[str, Any]:
        evidence = _evidence_payload(rows, revision.id, "valuation", cutoff)
        return {
            "revision_id": str(revision.id),
            "company_research_revision_id": str(revision.company_research_revision_id),
            "revision_no": revision.revision_no,
            "valuation_method": revision.valuation_method,
            "metric_context": revision.metric_context,
            "observed_value": revision.observed_value,
            "missing_data_reason": revision.missing_data_reason,
            "unit": revision.unit,
            "currency": revision.currency,
            "comparison_basis": revision.comparison_basis,
            "assumptions": revision.assumptions,
            "status": revision.status,
            "confidence": revision.confidence,
            "information_cutoff_date": _date(revision.information_cutoff_date),
            "recorded_at_utc": _timestamp(revision.recorded_at_utc),
            "supersedes_revision_id": _uuid(revision.supersedes_revision_id),
            "frozen_hypothesis_revision_ids": _ids(
                link.hypothesis_revision_id
                for link in rows.hypothesis_links
                if link.valuation_revision_id == revision.id and _recorded_visible(link.recorded_at_utc, cutoff)
            ),
            "price_reference": _price_reference(rows, revision.daily_price_id),
            "claims": evidence["claims"],
            "evidence_grade_counts": evidence["evidence_grade_counts"],
            "conflicts": evidence["conflicts"],
            "missing_evidence": evidence["missing_evidence"],
        }


def _evidence_payload(rows: Any, revision_id: UUID, kind: str, cutoff: date | None) -> dict[str, Any]:
    claim_by_id = {item.id: item for item in rows.claim_revisions}
    claim_identity = {item.id: item for item in rows.claims}
    source_links = {item.id: item for item in rows.claim_evidence_links}
    evidence_by_id = {item.id: item for item in rows.evidence}
    claim_attr = f"{kind}_revision_id"
    claim_links = [
        item
        for item in rows.claim_links
        if getattr(item, claim_attr) == revision_id and _recorded_visible(item.recorded_at_utc, cutoff)
    ]
    evidence_links = [
        item
        for item in rows.evidence_links
        if getattr(item, claim_attr) == revision_id and _recorded_visible(item.recorded_at_utc, cutoff)
    ]
    claims: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    grades: Counter[str] = Counter()
    for link in sorted(claim_links, key=lambda item: str(item.claim_revision_id)):
        claim_revision = claim_by_id[link.claim_revision_id]
        claim = claim_identity[claim_revision.claim_id]
        evidence_payload = []
        for boundary in evidence_links:
            if boundary.claim_revision_id != claim_revision.id:
                continue
            source_link = source_links[boundary.claim_evidence_link_id]
            evidence = evidence_by_id[boundary.evidence_id]
            item = {
                "claim_evidence_link_id": str(source_link.id),
                "evidence_id": str(evidence.id),
                "evidence_grade": evidence.evidence_grade,
                "relation": source_link.relation,
                "source_title": evidence.source_title,
                "information_date": _date(evidence.information_date),
                "recorded_at_utc": _timestamp(evidence.recorded_at_utc),
            }
            evidence_payload.append(item)
            grades[evidence.evidence_grade] += 1
            if source_link.relation == "contradicts":
                conflicts.append(
                    {
                        "claim_revision_id": str(claim_revision.id),
                        "claim_key": claim.claim_key,
                        "evidence_id": str(evidence.id),
                        "evidence_grade": evidence.evidence_grade,
                        "source_title": evidence.source_title,
                    }
                )
        evidence_payload.sort(key=lambda item: (item["relation"], item["evidence_grade"], item["evidence_id"]))
        if not evidence_payload:
            missing.append(
                {
                    "claim_revision_id": str(claim_revision.id),
                    "claim_key": claim.claim_key,
                    "reason": "no evidence was frozen at this v0.6B snapshot boundary",
                }
            )
        claims.append(
            {
                "claim_id": str(claim.id),
                "claim_key": claim.claim_key,
                "claim_revision_id": str(claim_revision.id),
                "revision_no": claim_revision.revision_no,
                "statement": claim_revision.statement,
                "claim_status": claim_revision.claim_status,
                "information_cutoff_date": _date(claim_revision.information_cutoff_date),
                "evidence": evidence_payload,
            }
        )
    claims.sort(key=lambda item: (item["claim_key"], item["claim_revision_id"]))
    conflicts.sort(key=lambda item: (item["claim_key"], item["evidence_id"]))
    missing.sort(key=lambda item: (item["claim_key"], item["claim_revision_id"]))
    return {
        "claims": tuple(claims),
        "conflicts": tuple(conflicts),
        "missing_evidence": tuple(missing),
        "evidence_grade_counts": {grade: grades[grade] for grade in ("A", "B", "C", "D")},
    }


def _price_reference(rows: Stage2ValuationRows, price_id: int | None) -> dict[str, Any] | None:
    if price_id is None:
        return None
    price = next((item for item in rows.prices if item.id == price_id), None)
    if price is None:
        return None
    run = next((item for item in rows.ingestion_runs if item.id == price.ingestion_run_id), None)
    if run is None:
        return None
    return {
        "daily_price_id": price.id,
        "ingestion_run_id": run.id,
        "provider": run.provider,
        "series_key": run.series_key,
        "information_cutoff_date": _date(run.information_cutoff_date),
        "trade_date": _date(price.trade_date),
        "stock_code": price.stock_code,
        "source": price.source,
        "adjust_type": price.adjust_type,
        "close": price.close,
        "imported_at_utc": _timestamp(run.imported_at),
        "completed_at_utc": _timestamp(run.completed_at),
    }


def _visible_revisions(revisions: tuple[Any, ...], cutoff: date | None) -> list[Any]:
    return [
        item
        for item in revisions
        if cutoff is None
        or (
            item.information_cutoff_date <= cutoff
            and _stored_utc(item.recorded_at_utc).date() <= cutoff
        )
    ]


def _recorded_visible(recorded_at: datetime, cutoff: date | None) -> bool:
    return cutoff is None or _stored_utc(recorded_at).date() <= cutoff


def _stored_utc(value: datetime | None) -> datetime:
    if value is None:
        raise EvidenceLedgerNotVisible("required UTC timestamp is unavailable.")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime | None) -> str:
    return _stored_utc(value).isoformat().replace("+00:00", "Z")


def _date(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def _uuid(value: UUID | None) -> str | None:
    return None if value is None else str(value)


def _ids(values: Any) -> list[str]:
    return sorted(str(item) for item in values)
