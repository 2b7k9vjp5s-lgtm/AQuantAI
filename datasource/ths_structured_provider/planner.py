"""Deterministic, non-executable request planning for THS Stage C0."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import INDEX_DAILY_HISTORY_CONTRACT, PublicEndpointContract
from .fingerprint import canonical_sha256
from .readiness import BLOCKED_REASON_MESSAGES_ZH, BlockedReasonCode, CapabilityReadiness
from .selectors import IndexHistorySelector

TRANSPORT_POLICY_VERSION = "aquantai.ths-c0-no-transport.v1"
PAGINATION_CEILING = 1
RECORD_CEILING = 2000
RAW_BYTE_CEILING = 10 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class DryRunRequestPlan:
    source_key: str
    capability_key: str
    contract_key: str
    contract_fingerprint: str
    host_key: str
    https_host: str
    http_method: str
    path_key: str
    ordered_query_items: tuple[tuple[str, str], ...]
    selector_fingerprint: str
    pagination_ceiling: int
    record_ceiling: int
    raw_byte_ceiling: int
    transport_policy_version: str
    readiness_snapshot: tuple[tuple[str, str], ...]
    blocked_reason_codes: tuple[str, ...]
    blocked_messages_zh: tuple[str, ...]
    live_readiness_candidate: str
    request_fingerprint: str
    synthetic_only: bool = True
    remote_executable: bool = False

    def public_summary(self) -> dict[str, object]:
        return {
            "source_key": self.source_key,
            "capability_key": self.capability_key,
            "contract_key": self.contract_key,
            "contract_fingerprint": self.contract_fingerprint,
            "host_key": self.host_key,
            "https_host": self.https_host,
            "http_method": self.http_method,
            "path_key": self.path_key,
            "ordered_query_items": self.ordered_query_items,
            "selector_fingerprint": self.selector_fingerprint,
            "pagination_ceiling": self.pagination_ceiling,
            "record_ceiling": self.record_ceiling,
            "raw_byte_ceiling": self.raw_byte_ceiling,
            "transport_policy_version": self.transport_policy_version,
            "readiness_snapshot": self.readiness_snapshot,
            "blocked_reason_codes": self.blocked_reason_codes,
            "blocked_messages_zh": self.blocked_messages_zh,
            "live_readiness_candidate": self.live_readiness_candidate,
            "request_fingerprint": self.request_fingerprint,
            "synthetic_only": self.synthetic_only,
            "remote_executable": self.remote_executable,
        }


def _request_fingerprint_payload(
    contract: PublicEndpointContract,
    selector: IndexHistorySelector,
) -> dict[str, object]:
    return {
        "source_key": contract.source_key,
        "capability_key": contract.capability_key,
        "contract_key": contract.contract_key,
        "contract_fingerprint": contract.contract_fingerprint,
        "host_key": contract.host_key,
        "http_method": contract.http_method,
        "path_key": contract.path_template,
        "ordered_query_items": selector.ordered_query_items(),
        "pagination_ceiling": PAGINATION_CEILING,
        "record_ceiling": RECORD_CEILING,
        "raw_byte_ceiling": RAW_BYTE_CEILING,
        "transport_policy_version": TRANSPORT_POLICY_VERSION,
        "selector_schema_version": contract.selector_schema_version,
    }


def build_index_history_plan(
    selector: IndexHistorySelector,
    readiness: CapabilityReadiness,
    *,
    contract: PublicEndpointContract = INDEX_DAILY_HISTORY_CONTRACT,
) -> DryRunRequestPlan:
    if contract != INDEX_DAILY_HISTORY_CONTRACT:
        raise ValueError("Stage C0 accepts only the frozen index-history contract")
    if readiness.source_key != contract.source_key or readiness.capability_key != contract.capability_key:
        raise ValueError("Readiness does not match the frozen contract")

    reason_codes: tuple[BlockedReasonCode, ...] = readiness.blocked_reason_codes()
    return DryRunRequestPlan(
        source_key=contract.source_key,
        capability_key=contract.capability_key,
        contract_key=contract.contract_key,
        contract_fingerprint=contract.contract_fingerprint,
        host_key=contract.host_key,
        https_host=contract.https_host,
        http_method=contract.http_method,
        path_key=contract.path_template,
        ordered_query_items=selector.ordered_query_items(),
        selector_fingerprint=selector.selector_fingerprint,
        pagination_ceiling=PAGINATION_CEILING,
        record_ceiling=RECORD_CEILING,
        raw_byte_ceiling=RAW_BYTE_CEILING,
        transport_policy_version=TRANSPORT_POLICY_VERSION,
        readiness_snapshot=readiness.snapshot(),
        blocked_reason_codes=tuple(code.value for code in reason_codes),
        blocked_messages_zh=tuple(BLOCKED_REASON_MESSAGES_ZH[code] for code in reason_codes),
        live_readiness_candidate=readiness.live_readiness_candidate,
        request_fingerprint=canonical_sha256(_request_fingerprint_payload(contract, selector)),
        synthetic_only=True,
        remote_executable=False,
    )
