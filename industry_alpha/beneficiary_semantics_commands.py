"""Atomic local command boundary for typed beneficiary evidence semantics v1."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.beneficiary_semantics_contracts import (
    CLAIM_RELATIONS,
    EVIDENCE_STATES,
    FIELD_STATE_CODES,
    OVERALL_STATUSES,
    SINGLETON_FIELDS,
    TAXONOMY_VERSION,
)
from industry_alpha.beneficiary_semantics_models import (
    Stage1BeneficiarySemanticAssertion,
    Stage1BeneficiarySemanticAssertionClaimLink,
    Stage1BeneficiarySemanticProfile,
    Stage1BeneficiarySemanticProfileRevision,
    Stage1BeneficiarySemanticVerificationItem,
)
from industry_alpha.chain_map_models import (
    IndustryMapObservation,
    IndustryMapObservationRevision,
    IndustryMapRevision,
)
from industry_alpha.errors import (
    EvidenceLedgerConflictError,
    EvidenceLedgerNotFound,
    EvidenceLedgerValidationError,
)
from industry_alpha.models import ClaimEvidenceLink, ClaimRevision, EvidenceItem
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryAssertionLink,
    Stage1BeneficiaryClaimLink,
    Stage1BeneficiaryRevision,
)


class BeneficiarySemanticCommandService:
    """Validate and append one complete semantic profile revision."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def validate(self, raw: dict[str, Any]) -> dict[str, Any]:
        normalized = _normalize_input(raw)
        with self._session_factory() as session:
            context = self._validate_database(session, normalized, lock=False)
        return _preview(normalized, context)

    def record(self, raw: dict[str, Any]) -> dict[str, Any]:
        normalized = _normalize_input(raw)
        try:
            with self._session_factory.begin() as session:
                context = self._validate_database(session, normalized, lock=True)
                profile = context["profile"]
                latest = context["latest_revision"]
                recorded = normalized["recorded_at_utc"]
                if profile is None:
                    profile = Stage1BeneficiarySemanticProfile(
                        beneficiary_id=normalized["beneficiary_id"],
                        created_at_utc=recorded,
                    )
                    session.add(profile)
                    session.flush()
                revision = Stage1BeneficiarySemanticProfileRevision(
                    profile_id=profile.id,
                    revision_no=1 if latest is None else latest.revision_no + 1,
                    beneficiary_revision_id=normalized["beneficiary_revision_id"],
                    selected_map_revision_id=normalized["selected_map_revision_id"],
                    taxonomy_version=TAXONOMY_VERSION,
                    overall_status=normalized["overall_status"],
                    summary=normalized["summary"],
                    recorded_by=normalized["recorded_by"],
                    information_cutoff_date=normalized["information_cutoff_date"],
                    recorded_at_utc=recorded,
                    supersedes_revision_id=None if latest is None else latest.id,
                )
                session.add(revision)
                session.flush()

                assertion_by_key: dict[str, Stage1BeneficiarySemanticAssertion] = {}
                claim_link_count = 0
                for item in normalized["assertions"]:
                    assertion = Stage1BeneficiarySemanticAssertion(
                        profile_revision_id=revision.id,
                        assertion_key=item["assertion_key"],
                        field_kind=item["field_kind"],
                        state_code=item["state_code"],
                        evidence_state=item["evidence_state"],
                        subject_text=item["subject_text"],
                        rationale=item["rationale"],
                        map_observation_revision_id=item["map_observation_revision_id"],
                        position=item["position"],
                    )
                    session.add(assertion)
                    session.flush()
                    assertion_by_key[item["assertion_key"]] = assertion
                    for claim_link in item["claim_links"]:
                        session.add(
                            Stage1BeneficiarySemanticAssertionClaimLink(
                                assertion_id=assertion.id,
                                claim_revision_id=claim_link["claim_revision_id"],
                                relation=claim_link["relation"],
                                recorded_at_utc=recorded,
                            )
                        )
                        claim_link_count += 1

                for item in normalized["verification_items"]:
                    assertion = (
                        None
                        if item["assertion_key"] is None
                        else assertion_by_key[item["assertion_key"]]
                    )
                    session.add(
                        Stage1BeneficiarySemanticVerificationItem(
                            profile_revision_id=revision.id,
                            assertion_id=None if assertion is None else assertion.id,
                            verification_question=item["verification_question"],
                            expected_evidence_type=item["expected_evidence_type"],
                            status="open",
                            recorded_at_utc=recorded,
                        )
                    )
                session.flush()
                result = {
                    "profile_id": str(profile.id),
                    "profile_revision_id": str(revision.id),
                    "revision_no": revision.revision_no,
                    "beneficiary_id": str(normalized["beneficiary_id"]),
                    "beneficiary_revision_id": str(normalized["beneficiary_revision_id"]),
                    "selected_map_revision_id": str(normalized["selected_map_revision_id"]),
                    "taxonomy_version": TAXONOMY_VERSION,
                    "overall_status": normalized["overall_status"],
                    "assertion_count": len(normalized["assertions"]),
                    "claim_link_count": claim_link_count,
                    "verification_item_count": len(normalized["verification_items"]),
                }
        except IntegrityError as exc:
            raise EvidenceLedgerConflictError(
                "typed beneficiary semantic revision conflicts with accepted history"
            ) from exc
        return result

    def _validate_database(
        self, session: Session, normalized: dict[str, Any], *, lock: bool
    ) -> dict[str, Any]:
        beneficiary = session.get(Stage1Beneficiary, normalized["beneficiary_id"])
        if beneficiary is None:
            raise EvidenceLedgerNotFound("selected Stage 1 beneficiary was not found")
        beneficiary_revision = session.get(
            Stage1BeneficiaryRevision, normalized["beneficiary_revision_id"]
        )
        if beneficiary_revision is None or beneficiary_revision.beneficiary_id != beneficiary.id:
            raise EvidenceLedgerValidationError(
                "beneficiary_revision_id does not belong to the selected beneficiary"
            )
        if beneficiary_revision.selected_map_revision_id != normalized["selected_map_revision_id"]:
            raise EvidenceLedgerValidationError(
                "selected_map_revision_id must equal the frozen Stage 1 map revision"
            )
        map_revision = session.get(IndustryMapRevision, normalized["selected_map_revision_id"])
        if map_revision is None or map_revision.map_id != beneficiary.map_id:
            raise EvidenceLedgerValidationError(
                "selected map revision does not belong to the beneficiary map"
            )
        _require_visible(
            "beneficiary revision",
            beneficiary_revision.information_cutoff_date,
            beneficiary_revision.recorded_at_utc,
            normalized,
        )
        _require_visible(
            "selected map revision",
            map_revision.information_cutoff_date,
            map_revision.recorded_at_utc,
            normalized,
        )

        frozen_claim_ids = set(
            session.scalars(
                select(Stage1BeneficiaryClaimLink.claim_revision_id).where(
                    Stage1BeneficiaryClaimLink.beneficiary_revision_id
                    == beneficiary_revision.id
                )
            )
        )
        frozen_observation_ids = set(
            session.scalars(
                select(Stage1BeneficiaryAssertionLink.observation_revision_id).where(
                    Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                    == beneficiary_revision.id,
                    Stage1BeneficiaryAssertionLink.observation_revision_id.is_not(None),
                )
            )
        )
        requested_claim_ids = {
            item["claim_revision_id"]
            for assertion in normalized["assertions"]
            for item in assertion["claim_links"]
        }
        if not requested_claim_ids.issubset(frozen_claim_ids):
            raise EvidenceLedgerValidationError(
                "every semantic claim must already be frozen by the beneficiary revision"
            )

        claim_rows = {
            row.id: row
            for row in session.scalars(
                select(ClaimRevision).where(ClaimRevision.id.in_(requested_claim_ids))
            )
        } if requested_claim_ids else {}
        if set(claim_rows) != requested_claim_ids:
            raise EvidenceLedgerValidationError("one or more selected claim revisions were not found")
        for claim in claim_rows.values():
            _require_visible(
                "claim revision",
                claim.information_cutoff_date,
                claim.recorded_at_utc,
                normalized,
            )

        evidence_paths = _load_evidence_paths(session, requested_claim_ids, normalized)
        for assertion in normalized["assertions"]:
            if assertion["field_kind"] == "driver":
                observation_id = assertion["map_observation_revision_id"]
                if observation_id not in frozen_observation_ids:
                    raise EvidenceLedgerValidationError(
                        "driver observation must already be frozen by the beneficiary revision"
                    )
                revision = session.get(IndustryMapObservationRevision, observation_id)
                observation = (
                    None
                    if revision is None
                    else session.get(IndustryMapObservation, revision.observation_id)
                )
                if (
                    revision is None
                    or observation is None
                    or observation.map_id != beneficiary.map_id
                    or observation.observation_kind != "driver"
                ):
                    raise EvidenceLedgerValidationError(
                        "driver observation must be an exact driver revision for the selected map"
                    )
                _require_visible(
                    "driver observation revision",
                    revision.information_cutoff_date,
                    revision.recorded_at_utc,
                    normalized,
                )
            _validate_evidence_paths(assertion, evidence_paths)

        profile_stmt = select(Stage1BeneficiarySemanticProfile).where(
            Stage1BeneficiarySemanticProfile.beneficiary_id == beneficiary.id
        )
        if lock:
            profile_stmt = profile_stmt.with_for_update()
        profile = session.scalar(profile_stmt)
        latest = None
        if profile is not None:
            latest_stmt = (
                select(Stage1BeneficiarySemanticProfileRevision)
                .where(Stage1BeneficiarySemanticProfileRevision.profile_id == profile.id)
                .order_by(Stage1BeneficiarySemanticProfileRevision.revision_no.desc())
                .limit(1)
            )
            if lock:
                latest_stmt = latest_stmt.with_for_update()
            latest = session.scalar(latest_stmt)
        expected = normalized["expected_latest_revision_id"]
        if latest is None and expected is not None:
            raise EvidenceLedgerConflictError(
                "expected_latest_revision_id must be null for the first semantic revision"
            )
        if latest is not None and expected != latest.id:
            raise EvidenceLedgerConflictError(
                "expected_latest_revision_id does not match accepted semantic history"
            )
        if latest is not None:
            if normalized["recorded_at_utc"] < _stored_utc(latest.recorded_at_utc):
                raise EvidenceLedgerValidationError(
                    "recorded_at_utc cannot precede the latest semantic revision"
                )
            if normalized["information_cutoff_date"] < latest.information_cutoff_date:
                raise EvidenceLedgerValidationError(
                    "information_cutoff_date cannot precede the latest semantic revision"
                )
        return {
            "beneficiary": beneficiary,
            "beneficiary_revision": beneficiary_revision,
            "map_revision": map_revision,
            "profile": profile,
            "latest_revision": latest,
        }


def _normalize_input(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise EvidenceLedgerValidationError("input must be a JSON object")
    normalized = {
        "beneficiary_id": _uuid(raw.get("beneficiary_id"), "beneficiary_id"),
        "beneficiary_revision_id": _uuid(
            raw.get("beneficiary_revision_id"), "beneficiary_revision_id"
        ),
        "selected_map_revision_id": _uuid(
            raw.get("selected_map_revision_id"), "selected_map_revision_id"
        ),
        "expected_latest_revision_id": _optional_uuid(
            raw.get("expected_latest_revision_id"), "expected_latest_revision_id"
        ),
        "overall_status": _choice(
            raw.get("overall_status"), OVERALL_STATUSES, "overall_status"
        ),
        "summary": _text(raw.get("summary"), "summary", 4000),
        "recorded_by": _text(raw.get("recorded_by"), "recorded_by", 100),
        "information_cutoff_date": _date_value(
            raw.get("information_cutoff_date"), "information_cutoff_date"
        ),
        "recorded_at_utc": _datetime_value(raw.get("recorded_at_utc")),
    }
    if raw.get("taxonomy_version", TAXONOMY_VERSION) != TAXONOMY_VERSION:
        raise EvidenceLedgerValidationError("taxonomy_version is not the accepted v1 value")
    if normalized["information_cutoff_date"] > normalized["recorded_at_utc"].date():
        raise EvidenceLedgerValidationError(
            "information_cutoff_date cannot be later than recorded_at_utc"
        )

    assertions_raw = raw.get("assertions")
    if not isinstance(assertions_raw, list):
        raise EvidenceLedgerValidationError("assertions must be a JSON array")
    assertions: list[dict[str, Any]] = []
    keys: set[str] = set()
    for index, item in enumerate(assertions_raw):
        if not isinstance(item, dict):
            raise EvidenceLedgerValidationError(f"assertions[{index}] must be an object")
        key = _text(item.get("assertion_key"), f"assertions[{index}].assertion_key", 96)
        if key in keys:
            raise EvidenceLedgerValidationError("assertion_key values must be unique")
        keys.add(key)
        field_kind = item.get("field_kind")
        if field_kind not in FIELD_STATE_CODES:
            raise EvidenceLedgerValidationError(
                f"assertions[{index}].field_kind is not part of the v1 vocabulary"
            )
        state_code = _choice(
            item.get("state_code"),
            FIELD_STATE_CODES[field_kind],
            f"assertions[{index}].state_code",
        )
        evidence_state = _choice(
            item.get("evidence_state"),
            EVIDENCE_STATES,
            f"assertions[{index}].evidence_state",
        )
        subject = _optional_text(
            item.get("subject_text"), f"assertions[{index}].subject_text", 500
        )
        if field_kind == "offering" and subject is None:
            raise EvidenceLedgerValidationError("offering assertions require subject_text")
        observation_id = _optional_uuid(
            item.get("map_observation_revision_id"),
            f"assertions[{index}].map_observation_revision_id",
        )
        if (field_kind == "driver") != (observation_id is not None):
            raise EvidenceLedgerValidationError(
                "only driver assertions require map_observation_revision_id"
            )
        position = item.get("position")
        if not isinstance(position, int) or isinstance(position, bool) or position < 0:
            raise EvidenceLedgerValidationError(
                f"assertions[{index}].position must be a non-negative integer"
            )
        claim_links_raw = item.get("claim_links", [])
        if not isinstance(claim_links_raw, list):
            raise EvidenceLedgerValidationError(
                f"assertions[{index}].claim_links must be an array"
            )
        claim_links: list[dict[str, Any]] = []
        claim_keys: set[tuple[UUID, str]] = set()
        for link_index, link in enumerate(claim_links_raw):
            if not isinstance(link, dict):
                raise EvidenceLedgerValidationError("claim link must be an object")
            claim_id = _uuid(
                link.get("claim_revision_id"),
                f"assertions[{index}].claim_links[{link_index}].claim_revision_id",
            )
            relation = _choice(
                link.get("relation"),
                CLAIM_RELATIONS,
                f"assertions[{index}].claim_links[{link_index}].relation",
            )
            pair = (claim_id, relation)
            if pair in claim_keys:
                raise EvidenceLedgerValidationError("duplicate assertion claim relation")
            claim_keys.add(pair)
            claim_links.append({"claim_revision_id": claim_id, "relation": relation})
        assertion = {
            "assertion_key": key,
            "field_kind": field_kind,
            "state_code": state_code,
            "evidence_state": evidence_state,
            "subject_text": subject,
            "rationale": _text(
                item.get("rationale"), f"assertions[{index}].rationale", 4000
            ),
            "map_observation_revision_id": observation_id,
            "position": position,
            "claim_links": tuple(claim_links),
        }
        _validate_assertion_shape(assertion)
        assertions.append(assertion)

    counts = Counter(item["field_kind"] for item in assertions)
    for field in SINGLETON_FIELDS:
        if counts[field] != 1:
            raise EvidenceLedgerValidationError(f"exactly one {field} assertion is required")
    for field in ("driver", "offering"):
        if counts[field] < 1:
            raise EvidenceLedgerValidationError(f"at least one {field} assertion is required")

    verification_raw = raw.get("verification_items", [])
    if not isinstance(verification_raw, list):
        raise EvidenceLedgerValidationError("verification_items must be an array")
    verification_items: list[dict[str, Any]] = []
    verification_keys: set[str] = set()
    for index, item in enumerate(verification_raw):
        if not isinstance(item, dict):
            raise EvidenceLedgerValidationError("verification item must be an object")
        assertion_key = item.get("assertion_key")
        if assertion_key is not None:
            assertion_key = _text(
                assertion_key, f"verification_items[{index}].assertion_key", 96
            )
            if assertion_key not in keys:
                raise EvidenceLedgerValidationError(
                    "verification item assertion_key must reference this revision"
                )
            verification_keys.add(assertion_key)
        verification_items.append(
            {
                "assertion_key": assertion_key,
                "verification_question": _text(
                    item.get("verification_question"),
                    f"verification_items[{index}].verification_question",
                    2000,
                ),
                "expected_evidence_type": _text(
                    item.get("expected_evidence_type"),
                    f"verification_items[{index}].expected_evidence_type",
                    500,
                ),
            }
        )
    missing_keys = {
        item["assertion_key"]
        for item in assertions
        if item["evidence_state"] == "missing"
    }
    if not missing_keys.issubset(verification_keys):
        raise EvidenceLedgerValidationError(
            "every missing assertion requires a linked verification item"
        )
    _validate_overall_status(normalized["overall_status"], assertions)
    normalized["assertions"] = tuple(assertions)
    normalized["verification_items"] = tuple(verification_items)
    return normalized


def _validate_assertion_shape(assertion: dict[str, Any]) -> None:
    state = assertion["evidence_state"]
    code = assertion["state_code"]
    relations = {item["relation"] for item in assertion["claim_links"]}
    if state == "supported":
        if code in {"unknown", "not_applicable"} or "support" not in relations:
            raise EvidenceLedgerValidationError(
                "supported assertions require a positive state and support claim"
            )
        if "contradict" in relations:
            raise EvidenceLedgerValidationError(
                "supported assertions cannot include a contradiction link"
            )
    elif state == "disputed":
        if code in {"unknown", "not_applicable"} or not {
            "support",
            "contradict",
        }.issubset(relations):
            raise EvidenceLedgerValidationError(
                "disputed assertions require a positive state plus support and contradiction claims"
            )
    elif state == "missing":
        if code != "unknown" or assertion["claim_links"]:
            raise EvidenceLedgerValidationError(
                "missing assertions require state_code=unknown and no claim links"
            )
    elif state == "not_applicable":
        if code != "not_applicable" or not relations.intersection({"support", "context"}):
            raise EvidenceLedgerValidationError(
                "not_applicable requires state_code=not_applicable and support or context"
            )


def _validate_overall_status(
    overall_status: str, assertions: list[dict[str, Any]]
) -> None:
    if overall_status == "supported":
        if any(item["evidence_state"] == "disputed" for item in assertions):
            raise EvidenceLedgerValidationError(
                "overall supported cannot contain disputed assertions"
            )
        for field in ("exposure", "driver", "offering"):
            if not any(
                item["field_kind"] == field and item["evidence_state"] == "supported"
                for item in assertions
            ):
                raise EvidenceLedgerValidationError(
                    f"overall supported requires a supported {field} assertion"
                )
    if overall_status == "disputed" and not any(
        item["evidence_state"] == "disputed" for item in assertions
    ):
        raise EvidenceLedgerValidationError(
            "overall disputed requires at least one disputed assertion"
        )


def _load_evidence_paths(
    session: Session, claim_ids: set[UUID], normalized: dict[str, Any]
) -> dict[UUID, dict[str, set[str]]]:
    result = {
        claim_id: {"supports": set(), "contradicts": set(), "context": set()}
        for claim_id in claim_ids
    }
    if not claim_ids:
        return result
    links = tuple(
        session.scalars(
            select(ClaimEvidenceLink).where(
                ClaimEvidenceLink.claim_revision_id.in_(claim_ids)
            )
        )
    )
    evidence_by_id = {
        item.id: item
        for item in session.scalars(
            select(EvidenceItem).where(
                EvidenceItem.id.in_({link.evidence_id for link in links})
            )
        )
    } if links else {}
    for link in links:
        evidence = evidence_by_id.get(link.evidence_id)
        if evidence is None:
            continue
        if _stored_utc(link.recorded_at_utc) > normalized["recorded_at_utc"]:
            continue
        if evidence.information_date > normalized["information_cutoff_date"]:
            continue
        if _stored_utc(evidence.recorded_at_utc) > normalized["recorded_at_utc"]:
            continue
        result[link.claim_revision_id][link.relation].add(evidence.evidence_grade)
    return result


def _validate_evidence_paths(
    assertion: dict[str, Any], paths: dict[UUID, dict[str, set[str]]]
) -> None:
    if assertion["evidence_state"] not in {"supported", "disputed"}:
        return
    support_ids = {
        item["claim_revision_id"]
        for item in assertion["claim_links"]
        if item["relation"] == "support"
    }
    if not any(paths[item]["supports"].intersection({"A", "B", "C"}) for item in support_ids):
        raise EvidenceLedgerValidationError(
            "supported semantic state requires at least one A/B/C support evidence path"
        )
    if assertion["evidence_state"] == "supported" and any(
        paths[item]["contradicts"] for item in support_ids
    ):
        raise EvidenceLedgerValidationError(
            "supported semantic state cannot retain a visible contradiction path"
        )
    if assertion["evidence_state"] == "disputed":
        contradict_ids = {
            item["claim_revision_id"]
            for item in assertion["claim_links"]
            if item["relation"] == "contradict"
        }
        if not any(paths[item]["contradicts"] for item in contradict_ids):
            raise EvidenceLedgerValidationError(
                "disputed semantic state requires a visible contradiction evidence path"
            )


def _require_visible(
    label: str,
    cutoff: date,
    recorded_at: datetime,
    normalized: dict[str, Any],
) -> None:
    if cutoff > normalized["information_cutoff_date"]:
        raise EvidenceLedgerValidationError(f"{label} is later than the semantic cutoff")
    if _stored_utc(recorded_at) > normalized["recorded_at_utc"]:
        raise EvidenceLedgerValidationError(
            f"{label} was recorded after the semantic revision boundary"
        )


def _preview(normalized: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {
        "dry_run": True,
        "beneficiary_id": str(normalized["beneficiary_id"]),
        "beneficiary_revision_id": str(normalized["beneficiary_revision_id"]),
        "selected_map_revision_id": str(normalized["selected_map_revision_id"]),
        "expected_latest_revision_id": _uuid_text(
            normalized["expected_latest_revision_id"]
        ),
        "next_revision_no": (
            1
            if context["latest_revision"] is None
            else context["latest_revision"].revision_no + 1
        ),
        "taxonomy_version": TAXONOMY_VERSION,
        "overall_status": normalized["overall_status"],
        "assertion_count": len(normalized["assertions"]),
        "claim_link_count": sum(
            len(item["claim_links"]) for item in normalized["assertions"]
        ),
        "verification_item_count": len(normalized["verification_items"]),
    }


def _choice(value: Any, choices: frozenset[str], label: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise EvidenceLedgerValidationError(f"{label} is not part of the accepted vocabulary")
    return value


def _text(value: Any, label: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise EvidenceLedgerValidationError(f"{label} must be text")
    result = value.strip()
    if not result or len(result) > maximum:
        raise EvidenceLedgerValidationError(
            f"{label} must contain 1 to {maximum} trimmed characters"
        )
    return result


def _optional_text(value: Any, label: str, maximum: int) -> str | None:
    if value is None:
        return None
    return _text(value, label, maximum)


def _uuid(value: Any, label: str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise EvidenceLedgerValidationError(f"{label} must be a UUID") from exc


def _optional_uuid(value: Any, label: str) -> UUID | None:
    return None if value is None else _uuid(value, label)


def _date_value(value: Any, label: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise EvidenceLedgerValidationError(f"{label} must use YYYY-MM-DD") from exc


def _datetime_value(value: Any) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise EvidenceLedgerValidationError(
            "recorded_at_utc must be an ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvidenceLedgerValidationError("recorded_at_utc must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _stored_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _uuid_text(value: UUID | None) -> str | None:
    return None if value is None else str(value)
