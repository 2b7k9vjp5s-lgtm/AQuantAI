"""Secret-free readiness values and fail-closed reason projection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

from .contracts import INDEX_HISTORY_CAPABILITY, SOURCE_KEY


class ReadinessStatus(str, Enum):
    CONFIRMED = "confirmed"
    UNSUPPORTED = "unsupported"
    NOT_ENTITLED = "not_entitled"
    UNRESOLVED = "unresolved"
    BLOCKED = "blocked"


class BlockedReasonCode(str, Enum):
    QUOTA_CONTRACT_UNRESOLVED = "THS_C0_QUOTA_CONTRACT_UNRESOLVED"
    COMPLETION_CONTRACT_UNRESOLVED = "THS_C0_COMPLETION_CONTRACT_UNRESOLVED"
    REVISION_CONTRACT_UNRESOLVED = "THS_C0_REVISION_CONTRACT_UNRESOLVED"
    KEY_LIFECYCLE_UNRESOLVED = "THS_C0_KEY_LIFECYCLE_UNRESOLVED"
    CAPABILITY_NOT_ENTITLED = "THS_C0_CAPABILITY_NOT_ENTITLED"
    CAPABILITY_UNSUPPORTED = "THS_C0_CAPABILITY_UNSUPPORTED"
    HISTORICAL_MEMBERSHIP_UNSUPPORTED = "THS_C0_HISTORICAL_MEMBERSHIP_UNSUPPORTED"
    CORPORATE_ACTION_NOT_VALIDATED = "THS_C0_CORPORATE_ACTION_NOT_VALIDATED"
    SELECTOR_INVALID = "THS_C0_SELECTOR_INVALID"
    SELECTOR_OUT_OF_BOUNDS = "THS_C0_SELECTOR_OUT_OF_BOUNDS"
    CONTRACT_NOT_REVIEWED = "THS_C0_CONTRACT_NOT_REVIEWED"
    SCHEMA_MISMATCH = "THS_C0_SCHEMA_MISMATCH"
    UNREACHABLE_FIXTURE_FIELD = "THS_C0_UNREACHABLE_FIXTURE_FIELD"
    NETWORK_PROHIBITED = "THS_C0_NETWORK_PROHIBITED"


BLOCKED_REASON_MESSAGES_ZH: dict[BlockedReasonCode, str] = {
    BlockedReasonCode.QUOTA_CONTRACT_UNRESOLVED: "数据源额度或调用规则尚未确认",
    BlockedReasonCode.COMPLETION_CONTRACT_UNRESOLVED: "无法确认数据何时完整",
    BlockedReasonCode.REVISION_CONTRACT_UNRESOLVED: "数据更正与迟到规则尚未确认",
    BlockedReasonCode.KEY_LIFECYCLE_UNRESOLVED: "凭据过期与轮换规则尚未确认",
    BlockedReasonCode.CAPABILITY_NOT_ENTITLED: "当前账户没有该能力",
    BlockedReasonCode.CAPABILITY_UNSUPPORTED: "当前数据源不支持该能力",
    BlockedReasonCode.HISTORICAL_MEMBERSHIP_UNSUPPORTED: "缺少历史成分，历史板块宽度不可用",
    BlockedReasonCode.CORPORATE_ACTION_NOT_VALIDATED: "公司行为能力尚未验证，复权分析不可用",
    BlockedReasonCode.SELECTOR_INVALID: "请求参数不符合离线合同",
    BlockedReasonCode.SELECTOR_OUT_OF_BOUNDS: "请求范围不符合已审核合同",
    BlockedReasonCode.CONTRACT_NOT_REVIEWED: "数据源合同尚未完成审核",
    BlockedReasonCode.SCHEMA_MISMATCH: "响应结构与已审核合同不一致",
    BlockedReasonCode.UNREACHABLE_FIXTURE_FIELD: "合成样本包含生产合同不可达字段",
    BlockedReasonCode.NETWORK_PROHIBITED: "离线基础层禁止联网",
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class CapabilityReadiness:
    source_key: str = SOURCE_KEY
    capability_key: str = INDEX_HISTORY_CAPABILITY
    public_contract_status: ReadinessStatus = ReadinessStatus.CONFIRMED
    entitlement_status: ReadinessStatus = ReadinessStatus.CONFIRMED
    retention_status: ReadinessStatus = ReadinessStatus.CONFIRMED
    fixture_status: ReadinessStatus = ReadinessStatus.CONFIRMED
    quota_status: ReadinessStatus = ReadinessStatus.UNRESOLVED
    completion_status: ReadinessStatus = ReadinessStatus.UNRESOLVED
    revision_status: ReadinessStatus = ReadinessStatus.UNRESOLVED
    credential_lifecycle_status: ReadinessStatus = ReadinessStatus.UNRESOLVED
    historical_membership_status: ReadinessStatus = ReadinessStatus.UNSUPPORTED
    corporate_action_status: ReadinessStatus = ReadinessStatus.BLOCKED
    reviewed_evidence_fingerprints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.source_key != SOURCE_KEY:
            raise ValueError("Stage C0 readiness must use the reviewed THS source key")
        if self.capability_key != INDEX_HISTORY_CAPABILITY:
            raise ValueError("Stage C0 readiness is limited to index daily history")
        for fingerprint in self.reviewed_evidence_fingerprints:
            if not _SHA256_RE.fullmatch(fingerprint):
                raise ValueError("Evidence fingerprints must be lowercase SHA-256 hex")

    def blocked_reason_codes(
        self,
        *,
        require_historical_membership: bool = False,
        require_corporate_action: bool = False,
    ) -> tuple[BlockedReasonCode, ...]:
        reasons: list[BlockedReasonCode] = []

        if self.public_contract_status is not ReadinessStatus.CONFIRMED:
            reasons.append(BlockedReasonCode.CONTRACT_NOT_REVIEWED)

        if self.entitlement_status is ReadinessStatus.NOT_ENTITLED:
            reasons.append(BlockedReasonCode.CAPABILITY_NOT_ENTITLED)
        elif self.entitlement_status is ReadinessStatus.UNSUPPORTED:
            reasons.append(BlockedReasonCode.CAPABILITY_UNSUPPORTED)
        elif self.entitlement_status is not ReadinessStatus.CONFIRMED:
            reasons.append(BlockedReasonCode.CONTRACT_NOT_REVIEWED)

        if self.retention_status is not ReadinessStatus.CONFIRMED:
            reasons.append(BlockedReasonCode.CONTRACT_NOT_REVIEWED)
        if self.fixture_status is not ReadinessStatus.CONFIRMED:
            reasons.append(BlockedReasonCode.CONTRACT_NOT_REVIEWED)
        if self.quota_status is not ReadinessStatus.CONFIRMED:
            reasons.append(BlockedReasonCode.QUOTA_CONTRACT_UNRESOLVED)
        if self.completion_status is not ReadinessStatus.CONFIRMED:
            reasons.append(BlockedReasonCode.COMPLETION_CONTRACT_UNRESOLVED)
        if self.revision_status is not ReadinessStatus.CONFIRMED:
            reasons.append(BlockedReasonCode.REVISION_CONTRACT_UNRESOLVED)
        if self.credential_lifecycle_status is not ReadinessStatus.CONFIRMED:
            reasons.append(BlockedReasonCode.KEY_LIFECYCLE_UNRESOLVED)

        if require_historical_membership and self.historical_membership_status is not ReadinessStatus.CONFIRMED:
            reasons.append(BlockedReasonCode.HISTORICAL_MEMBERSHIP_UNSUPPORTED)
        if require_corporate_action and self.corporate_action_status is not ReadinessStatus.CONFIRMED:
            reasons.append(BlockedReasonCode.CORPORATE_ACTION_NOT_VALIDATED)

        return tuple(dict.fromkeys(reasons))

    def blocked_messages_zh(self) -> tuple[str, ...]:
        return tuple(BLOCKED_REASON_MESSAGES_ZH[code] for code in self.blocked_reason_codes())

    @property
    def live_readiness_candidate(self) -> str:
        return "ready" if not self.blocked_reason_codes() else "blocked"

    def snapshot(self) -> tuple[tuple[str, str], ...]:
        return (
            ("public_contract_status", self.public_contract_status.value),
            ("entitlement_status", self.entitlement_status.value),
            ("retention_status", self.retention_status.value),
            ("fixture_status", self.fixture_status.value),
            ("quota_status", self.quota_status.value),
            ("completion_status", self.completion_status.value),
            ("revision_status", self.revision_status.value),
            ("credential_lifecycle_status", self.credential_lifecycle_status.value),
            ("historical_membership_status", self.historical_membership_status.value),
            ("corporate_action_status", self.corporate_action_status.value),
        )
