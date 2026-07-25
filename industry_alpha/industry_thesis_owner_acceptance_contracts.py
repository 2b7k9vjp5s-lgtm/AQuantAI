"""Strict deterministic contracts for Industry Thesis owner acceptance."""

from __future__ import annotations

from hashlib import sha256
import re
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from industry_alpha.beneficiary_semantics_contracts import TAXONOMY_VERSION
from industry_alpha.industry_thesis_rules import (
    IndustryThesisError,
    bounded_text,
    enum_text,
    fingerprint,
    parse_date,
    parse_integer,
    parse_uuid,
    require_keys,
)

OWNER_ACCEPTANCE_PLAN_VERSION = "aquantai.industry-thesis-owner-acceptance-plan.v1"
OUTPUT_CONTRACT_VERSION = "aquantai.industry-thesis-output-links.v1"
MAP_MODE = "reuse_exact_existing_map_revision"

STAGE1_OPERATIONS = (
    "reuse_exact_beneficiary_revision",
    "create_beneficiary_identity_and_revision",
    "append_beneficiary_revision",
)
SEMANTIC_OPERATIONS = (
    "none",
    "reuse_exact_semantic_revision",
    "append_complete_semantic_profile",
)
CANDIDATE_POOL_MODES = (
    "create_supported_handoff",
    "append_supported_handoff",
    "reuse_exact_supported_handoff",
    "none_no_supported_members",
)
LEGACY_BENEFICIARY_KINDS = ("direct", "secondary", "potential")
ACCEPTANCE_STATUSES = ("draft", "supported", "disputed")
ASSERTION_KINDS = ("node", "relationship", "observation")

TRANSACTION_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "aquantai.industry-thesis-owner-acceptance.transaction.v1",
)

REASON_MESSAGES_ZH = {
    "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_NOT_READY": "该研究尚未完成候选审核，不能接受成果。",
    "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE": "研究结果已发生变化，请重新检查后再提交。",
    "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_FINGERPRINT_MISMATCH": "审核结果校验失败，请重新打开该研究。",
    "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED": "必须选择一个精确的既有产业地图版本。",
    "INDUSTRY_THESIS_ACCEPTANCE_MAP_REVISION_MISMATCH": "所选产业地图版本与研究或公司绑定不一致。",
    "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE": "并非所有已选公司都已补齐接受字段。",
    "INDUSTRY_THESIS_ACCEPTANCE_STOCK_IDENTITY_REQUIRED": "必须选择精确的本地股票基础信息记录。",
    "INDUSTRY_THESIS_ACCEPTANCE_LISTED_INSTRUMENT_ONLY": "仅有上市证券身份不足以建立正式受益公司记录。",
    "INDUSTRY_THESIS_ACCEPTANCE_STAGE1_BINDINGS_REQUIRED": "必须补齐产业地图断言和研究主张绑定。",
    "INDUSTRY_THESIS_ACCEPTANCE_DUPLICATE_OWNER_IDENTITY": "多个候选指向同一个正式受益公司身份。",
    "INDUSTRY_THESIS_ACCEPTANCE_LEGACY_KIND_REQUIRED": "必须明确选择原有受益类型。",
    "INDUSTRY_THESIS_ACCEPTANCE_STATUS_REQUIRED": "必须明确选择证据评估状态。",
    "INDUSTRY_THESIS_ACCEPTANCE_STATUS_REJECTED": "被拒绝的受益公司状态不能进入已接受成果。",
    "INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_PAYLOAD_INCOMPLETE": "类型化受益语义资料不完整。",
    "INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_REVISION_MISMATCH": "类型化受益语义版本与受益公司版本不一致。",
    "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH": "支持状态成员与候选池交接内容不一致。",
    "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT": "正式记录已被更新，请重新预览。",
    "INDUSTRY_THESIS_ACCEPTANCE_CHRONOLOGY_INVALID": "所选资料超出本次研究的时间边界。",
    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_ALREADY_EXISTS": "该研究成果已经接受。",
    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_CONFLICT": "该审核结果已存在另一份不一致的接受方案。",
    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE": "已接受成果的精确链接不完整或已损坏。",
}
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")


class IndustryThesisOwnerAcceptanceError(IndustryThesisError):
    """Stable owner-acceptance failure with an ordinary-Chinese message."""

    def __init__(self, code: str, detail: str | None = None) -> None:
        message = REASON_MESSAGES_ZH.get(code, "研究成果接受失败。")
        super().__init__(code, message)
        self.detail = detail


def reason_payload(code: str, *, detail: str | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "message_zh": REASON_MESSAGES_ZH.get(code, "研究成果接受失败。"),
        "detail": detail,
    }


def normalize_owner_acceptance_plan(
    raw: dict[str, Any],
    *,
    require_preview_fingerprint: bool = False,
) -> dict[str, Any]:
    allowed = {
        "reviewed_session_revision_id",
        "expected_session_latest_revision_number",
        "reviewed_plan_fingerprint_sha256",
        "research_case_id",
        "map_mode",
        "industry_map_id",
        "industry_map_revision_id",
        "candidate_owner_bindings",
        "candidate_pool_operation",
        "output_title",
        "output_scope",
        "information_cutoff_date",
        "revision_note",
        "owner_acceptance_plan_version",
        "preview_fingerprint_sha256",
    }
    required = allowed - {"preview_fingerprint_sha256"}
    require_keys(raw, allowed, required, field="owner_acceptance")
    if require_preview_fingerprint and "preview_fingerprint_sha256" not in raw:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE",
            "commit requires the exact preview fingerprint",
        )
    version = bounded_text(
        raw["owner_acceptance_plan_version"],
        "owner_acceptance_plan_version",
        128,
    )
    if version != OWNER_ACCEPTANCE_PLAN_VERSION:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE",
            "unsupported owner-acceptance plan version",
        )
    if raw["map_mode"] != MAP_MODE:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED"
        )
    bindings_raw = raw["candidate_owner_bindings"]
    if not isinstance(bindings_raw, list) or not bindings_raw:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE"
        )
    bindings = [
        _normalize_binding(item, index)
        for index, item in enumerate(bindings_raw)
    ]
    sequence_values = [item["sequence"] for item in bindings]
    candidate_ids = [item["reviewed_candidate_revision_id"] for item in bindings]
    if len(sequence_values) != len(set(sequence_values)) or len(candidate_ids) != len(
        set(candidate_ids)
    ):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_DUPLICATE_OWNER_IDENTITY"
        )
    bindings.sort(
        key=lambda item: (item["sequence"], item["reviewed_candidate_revision_id"])
    )
    if [item["sequence"] for item in bindings] != list(range(len(bindings))):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE",
            "candidate owner binding sequence must be dense from zero",
        )
    canonical = {
        "reviewed_session_revision_id": str(
            parse_uuid(
                raw["reviewed_session_revision_id"],
                "reviewed_session_revision_id",
            )
        ),
        "expected_session_latest_revision_number": parse_integer(
            raw["expected_session_latest_revision_number"],
            "expected_session_latest_revision_number",
            minimum=1,
        ),
        "reviewed_plan_fingerprint_sha256": _sha256_text(
            raw["reviewed_plan_fingerprint_sha256"],
            "reviewed_plan_fingerprint_sha256",
        ),
        "research_case_id": str(parse_uuid(raw["research_case_id"], "research_case_id")),
        "map_mode": MAP_MODE,
        "industry_map_id": str(
            parse_uuid(raw["industry_map_id"], "industry_map_id")
        ),
        "industry_map_revision_id": str(
            parse_uuid(raw["industry_map_revision_id"], "industry_map_revision_id")
        ),
        "candidate_owner_bindings": bindings,
        "candidate_pool_operation": _normalize_candidate_pool_operation(
            raw["candidate_pool_operation"]
        ),
        "output_title": bounded_text(raw["output_title"], "output_title", 300),
        "output_scope": bounded_text(raw["output_scope"], "output_scope", 4000),
        "information_cutoff_date": parse_date(
            raw["information_cutoff_date"],
            "information_cutoff_date",
        ).isoformat(),
        "revision_note": bounded_text(raw["revision_note"], "revision_note", 1000),
        "owner_acceptance_plan_version": OWNER_ACCEPTANCE_PLAN_VERSION,
    }
    plan_fingerprint = fingerprint(canonical)
    preview = raw.get("preview_fingerprint_sha256")
    if preview is not None:
        preview = _sha256_text(preview, "preview_fingerprint_sha256")
    return {
        **canonical,
        "owner_acceptance_plan_fingerprint_sha256": plan_fingerprint,
        "preview_fingerprint_sha256": preview,
    }


def owner_plan_canonical_value(normalized: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in normalized.items()
        if key
        not in {
            "owner_acceptance_plan_fingerprint_sha256",
            "preview_fingerprint_sha256",
        }
    }


def owner_transaction_id(normalized: dict[str, Any]) -> UUID:
    return uuid5(
        TRANSACTION_NAMESPACE,
        (
            f"{normalized['reviewed_session_revision_id']}:"
            f"{normalized['owner_acceptance_plan_fingerprint_sha256']}:"
            f"{OUTPUT_CONTRACT_VERSION}"
        ),
    )


def output_key(normalized: dict[str, Any]) -> str:
    payload = (
        f"{OUTPUT_CONTRACT_VERSION}:"
        f"{normalized['reviewed_session_revision_id']}:"
        f"{normalized['owner_acceptance_plan_fingerprint_sha256']}"
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _normalize_binding(raw: Any, index: int) -> dict[str, Any]:
    allowed = {
        "reviewed_candidate_revision_id",
        "sequence",
        "stage1_operation",
        "stage1",
        "semantic_operation",
        "semantic",
        "readiness_note",
    }
    require_keys(raw, allowed, allowed, field=f"candidate_owner_bindings[{index}]")
    stage1_operation = enum_text(
        raw["stage1_operation"],
        f"candidate_owner_bindings[{index}].stage1_operation",
        STAGE1_OPERATIONS,
    )
    semantic_operation = enum_text(
        raw["semantic_operation"],
        f"candidate_owner_bindings[{index}].semantic_operation",
        SEMANTIC_OPERATIONS,
    )
    binding = {
        "reviewed_candidate_revision_id": str(
            parse_uuid(
                raw["reviewed_candidate_revision_id"],
                f"candidate_owner_bindings[{index}].reviewed_candidate_revision_id",
            )
        ),
        "sequence": parse_integer(
            raw["sequence"],
            f"candidate_owner_bindings[{index}].sequence",
            minimum=0,
        ),
        "stage1_operation": stage1_operation,
        "stage1": _normalize_stage1(
            raw["stage1"],
            stage1_operation,
            index,
        ),
        "semantic_operation": semantic_operation,
        "semantic": _normalize_semantic(
            raw["semantic"],
            semantic_operation,
            index,
        ),
        "readiness_note": bounded_text(
            raw["readiness_note"],
            f"candidate_owner_bindings[{index}].readiness_note",
            1000,
        ),
    }
    binding["operation_key_sha256"] = fingerprint(binding)
    return binding


def _normalize_stage1(raw: Any, operation: str, index: int) -> dict[str, Any]:
    prefix = f"candidate_owner_bindings[{index}].stage1"
    if operation == "reuse_exact_beneficiary_revision":
        allowed = {
            "beneficiary_id",
            "beneficiary_revision_id",
            "stock_basic_record_id",
        }
        require_keys(raw, allowed, allowed, field=prefix)
        return {
            "beneficiary_id": str(parse_uuid(raw["beneficiary_id"], f"{prefix}.beneficiary_id")),
            "beneficiary_revision_id": str(
                parse_uuid(raw["beneficiary_revision_id"], f"{prefix}.beneficiary_revision_id")
            ),
            "stock_basic_record_id": parse_integer(
                raw["stock_basic_record_id"],
                f"{prefix}.stock_basic_record_id",
                minimum=1,
            ),
        }
    common = {
        "stock_basic_record_id",
        "source",
        "stock_code",
        "legacy_beneficiary_kind",
        "assessment_status",
        "rationale_summary",
        "map_assertion_revisions",
        "claim_revision_ids",
    }
    if operation == "create_beneficiary_identity_and_revision":
        require_keys(raw, common, common, field=prefix)
        identity: dict[str, Any] = {}
    else:
        append_keys = common | {"beneficiary_id", "expected_latest_revision_id"}
        require_keys(raw, append_keys, append_keys, field=prefix)
        identity = {
            "beneficiary_id": str(
                parse_uuid(raw["beneficiary_id"], f"{prefix}.beneficiary_id")
            ),
            "expected_latest_revision_id": str(
                parse_uuid(
                    raw["expected_latest_revision_id"],
                    f"{prefix}.expected_latest_revision_id",
                )
            ),
        }
    status = bounded_text(raw["assessment_status"], f"{prefix}.assessment_status", 32)
    if status == "rejected":
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_STATUS_REJECTED"
        )
    if status not in ACCEPTANCE_STATUSES:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_STATUS_REQUIRED"
        )
    kind = bounded_text(
        raw["legacy_beneficiary_kind"],
        f"{prefix}.legacy_beneficiary_kind",
        32,
    )
    if kind not in LEGACY_BENEFICIARY_KINDS:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_LEGACY_KIND_REQUIRED"
        )
    assertions_raw = raw["map_assertion_revisions"]
    if not isinstance(assertions_raw, list) or not assertions_raw:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_STAGE1_BINDINGS_REQUIRED"
        )
    assertions: list[dict[str, str]] = []
    for assertion_index, item in enumerate(assertions_raw):
        allowed = {"assertion_kind", "assertion_revision_id"}
        require_keys(
            item,
            allowed,
            allowed,
            field=f"{prefix}.map_assertion_revisions[{assertion_index}]",
        )
        kind_value = enum_text(
            item["assertion_kind"],
            f"{prefix}.map_assertion_revisions[{assertion_index}].assertion_kind",
            ASSERTION_KINDS,
        )
        assertions.append(
            {
                "assertion_kind": kind_value,
                "assertion_revision_id": str(
                    parse_uuid(
                        item["assertion_revision_id"],
                        f"{prefix}.map_assertion_revisions[{assertion_index}].assertion_revision_id",
                    )
                ),
            }
        )
    assertion_keys = [
        (item["assertion_kind"], item["assertion_revision_id"])
        for item in assertions
    ]
    if len(assertion_keys) != len(set(assertion_keys)):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_STAGE1_BINDINGS_REQUIRED",
            "duplicate map assertion revision",
        )
    assertions.sort(key=lambda item: (item["assertion_kind"], item["assertion_revision_id"]))
    claim_raw = raw["claim_revision_ids"]
    if not isinstance(claim_raw, list) or not claim_raw:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_STAGE1_BINDINGS_REQUIRED"
        )
    claim_ids = sorted(
        {
            str(parse_uuid(value, f"{prefix}.claim_revision_ids"))
            for value in claim_raw
        }
    )
    if len(claim_ids) != len(claim_raw):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_STAGE1_BINDINGS_REQUIRED",
            "duplicate claim revision",
        )
    return {
        **identity,
        "stock_basic_record_id": parse_integer(
            raw["stock_basic_record_id"],
            f"{prefix}.stock_basic_record_id",
            minimum=1,
        ),
        "source": bounded_text(raw["source"], f"{prefix}.source", 64),
        "stock_code": bounded_text(raw["stock_code"], f"{prefix}.stock_code", 16),
        "legacy_beneficiary_kind": kind,
        "assessment_status": status,
        "rationale_summary": bounded_text(
            raw["rationale_summary"],
            f"{prefix}.rationale_summary",
            4000,
        ),
        "map_assertion_revisions": assertions,
        "claim_revision_ids": claim_ids,
    }


def _normalize_semantic(raw: Any, operation: str, index: int) -> dict[str, Any] | None:
    prefix = f"candidate_owner_bindings[{index}].semantic"
    if operation == "none":
        if raw is not None:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_PAYLOAD_INCOMPLETE",
                "semantic must be null when semantic_operation is none",
            )
        return None
    if operation == "reuse_exact_semantic_revision":
        allowed = {"profile_id", "profile_revision_id"}
        require_keys(raw, allowed, allowed, field=prefix)
        return {
            "profile_id": str(parse_uuid(raw["profile_id"], f"{prefix}.profile_id")),
            "profile_revision_id": str(
                parse_uuid(raw["profile_revision_id"], f"{prefix}.profile_revision_id")
            ),
        }
    allowed = {
        "expected_latest_revision_id",
        "taxonomy_version",
        "overall_status",
        "summary",
        "recorded_by",
        "assertions",
        "verification_items",
    }
    require_keys(raw, allowed, allowed, field=prefix)
    if raw["taxonomy_version"] != TAXONOMY_VERSION:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_PAYLOAD_INCOMPLETE",
            "unsupported semantic taxonomy version",
        )
    assertions_raw = raw["assertions"]
    verification_raw = raw["verification_items"]
    if not isinstance(assertions_raw, list) or not isinstance(verification_raw, list):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_PAYLOAD_INCOMPLETE"
        )
    assertions = [
        _normalize_semantic_assertion(item, prefix, assertion_index)
        for assertion_index, item in enumerate(assertions_raw)
    ]
    assertions.sort(key=lambda item: (item["position"], item["assertion_key"]))
    verification = [
        _normalize_verification_item(item, prefix, verification_index)
        for verification_index, item in enumerate(verification_raw)
    ]
    verification.sort(
        key=lambda item: (
            item["assertion_key"] or "",
            item["verification_question"],
            item["expected_evidence_type"],
        )
    )
    expected_latest = parse_uuid(
        raw["expected_latest_revision_id"],
        f"{prefix}.expected_latest_revision_id",
        optional=True,
    )
    return {
        "expected_latest_revision_id": (
            None if expected_latest is None else str(expected_latest)
        ),
        "taxonomy_version": TAXONOMY_VERSION,
        "overall_status": bounded_text(
            raw["overall_status"],
            f"{prefix}.overall_status",
            32,
        ),
        "summary": bounded_text(raw["summary"], f"{prefix}.summary", 4000),
        "recorded_by": bounded_text(
            raw["recorded_by"],
            f"{prefix}.recorded_by",
            100,
        ),
        "assertions": assertions,
        "verification_items": verification,
    }


def _normalize_semantic_assertion(raw: Any, prefix: str, index: int) -> dict[str, Any]:
    field = f"{prefix}.assertions[{index}]"
    allowed = {
        "assertion_key",
        "field_kind",
        "state_code",
        "evidence_state",
        "subject_text",
        "rationale",
        "map_observation_revision_id",
        "position",
        "claim_links",
    }
    require_keys(raw, allowed, allowed, field=field)
    claim_links_raw = raw["claim_links"]
    if not isinstance(claim_links_raw, list):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_PAYLOAD_INCOMPLETE"
        )
    links: list[dict[str, str]] = []
    for link_index, item in enumerate(claim_links_raw):
        require_keys(
            item,
            {"claim_revision_id", "relation"},
            {"claim_revision_id", "relation"},
            field=f"{field}.claim_links[{link_index}]",
        )
        links.append(
            {
                "claim_revision_id": str(
                    parse_uuid(
                        item["claim_revision_id"],
                        f"{field}.claim_links[{link_index}].claim_revision_id",
                    )
                ),
                "relation": bounded_text(
                    item["relation"],
                    f"{field}.claim_links[{link_index}].relation",
                    16,
                ),
            }
        )
    links.sort(key=lambda item: (item["claim_revision_id"], item["relation"]))
    observation = parse_uuid(
        raw["map_observation_revision_id"],
        f"{field}.map_observation_revision_id",
        optional=True,
    )
    subject = raw["subject_text"]
    if subject is not None:
        subject = bounded_text(subject, f"{field}.subject_text", 500)
    return {
        "assertion_key": bounded_text(raw["assertion_key"], f"{field}.assertion_key", 96),
        "field_kind": bounded_text(raw["field_kind"], f"{field}.field_kind", 24),
        "state_code": bounded_text(raw["state_code"], f"{field}.state_code", 96),
        "evidence_state": bounded_text(
            raw["evidence_state"], f"{field}.evidence_state", 24
        ),
        "subject_text": subject,
        "rationale": bounded_text(raw["rationale"], f"{field}.rationale", 4000),
        "map_observation_revision_id": (
            None if observation is None else str(observation)
        ),
        "position": parse_integer(raw["position"], f"{field}.position", minimum=0),
        "claim_links": links,
    }


def _normalize_verification_item(raw: Any, prefix: str, index: int) -> dict[str, Any]:
    field = f"{prefix}.verification_items[{index}]"
    allowed = {
        "assertion_key",
        "verification_question",
        "expected_evidence_type",
    }
    require_keys(raw, allowed, allowed, field=field)
    assertion_key = raw["assertion_key"]
    if assertion_key is not None:
        assertion_key = bounded_text(assertion_key, f"{field}.assertion_key", 96)
    return {
        "assertion_key": assertion_key,
        "verification_question": bounded_text(
            raw["verification_question"],
            f"{field}.verification_question",
            2000,
        ),
        "expected_evidence_type": bounded_text(
            raw["expected_evidence_type"],
            f"{field}.expected_evidence_type",
            500,
        ),
    }


def _normalize_candidate_pool_operation(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH"
        )
    mode = enum_text(
        raw.get("mode"),
        "candidate_pool_operation.mode",
        CANDIDATE_POOL_MODES,
    )
    if mode == "none_no_supported_members":
        require_keys(raw, {"mode"}, {"mode"}, field="candidate_pool_operation")
        return {"mode": mode}
    if mode == "create_supported_handoff":
        allowed = {"mode", "pool_key", "title", "scope"}
        require_keys(raw, allowed, allowed, field="candidate_pool_operation")
        return {
            "mode": mode,
            "pool_key": bounded_text(raw["pool_key"], "candidate_pool_operation.pool_key", 96),
            "title": bounded_text(raw["title"], "candidate_pool_operation.title", 300),
            "scope": bounded_text(raw["scope"], "candidate_pool_operation.scope", 4000),
        }
    if mode == "append_supported_handoff":
        allowed = {
            "mode",
            "candidate_pool_id",
            "expected_latest_revision_id",
            "title",
            "scope",
        }
        require_keys(raw, allowed, allowed, field="candidate_pool_operation")
        return {
            "mode": mode,
            "candidate_pool_id": str(
                parse_uuid(raw["candidate_pool_id"], "candidate_pool_operation.candidate_pool_id")
            ),
            "expected_latest_revision_id": str(
                parse_uuid(
                    raw["expected_latest_revision_id"],
                    "candidate_pool_operation.expected_latest_revision_id",
                )
            ),
            "title": bounded_text(raw["title"], "candidate_pool_operation.title", 300),
            "scope": bounded_text(raw["scope"], "candidate_pool_operation.scope", 4000),
        }
    allowed = {"mode", "candidate_pool_id", "candidate_pool_revision_id"}
    require_keys(raw, allowed, allowed, field="candidate_pool_operation")
    return {
        "mode": mode,
        "candidate_pool_id": str(
            parse_uuid(raw["candidate_pool_id"], "candidate_pool_operation.candidate_pool_id")
        ),
        "candidate_pool_revision_id": str(
            parse_uuid(
                raw["candidate_pool_revision_id"],
                "candidate_pool_operation.candidate_pool_revision_id",
            )
        ),
    }


def _sha256_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_FINGERPRINT_MISMATCH",
            f"{field} must be a lowercase SHA-256 value",
        )
    normalized = value.strip().lower()
    if _HEX_64.fullmatch(normalized) is None:
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_FINGERPRINT_MISMATCH",
            f"{field} must be a lowercase SHA-256 value",
        )
    return normalized
