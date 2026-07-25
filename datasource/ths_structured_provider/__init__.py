"""Offline-only THS Stage C0 contract and request-planning foundation."""

from .contracts import (
    ADAPTER_FAMILY,
    CONTRACT_REGISTRY,
    INDEX_DAILY_HISTORY_CONTRACT,
    INDEX_HISTORY_CAPABILITY,
    SOURCE_KEY,
    PublicEndpointContract,
    get_contract,
)
from .fingerprint import canonical_json_bytes, canonical_sha256
from .planner import DryRunRequestPlan, build_index_history_plan
from .readiness import (
    BLOCKED_REASON_MESSAGES_ZH,
    BlockedReasonCode,
    CapabilityReadiness,
    ReadinessStatus,
)
from .redaction import assert_safe_display_url, redact_mapping, redact_text
from .schemas import (
    ErrorEnvelope,
    IndexHistoryEnvelope,
    SchemaValidationError,
    index_history_schema_fingerprint,
    load_synthetic_fixture,
    validate_error_envelope,
    validate_index_history_envelope,
)
from .selectors import IndexHistorySelector, SelectorValidationError

__all__ = [
    "ADAPTER_FAMILY",
    "BLOCKED_REASON_MESSAGES_ZH",
    "CONTRACT_REGISTRY",
    "DryRunRequestPlan",
    "ErrorEnvelope",
    "INDEX_DAILY_HISTORY_CONTRACT",
    "INDEX_HISTORY_CAPABILITY",
    "IndexHistoryEnvelope",
    "IndexHistorySelector",
    "PublicEndpointContract",
    "SOURCE_KEY",
    "BlockedReasonCode",
    "CapabilityReadiness",
    "ReadinessStatus",
    "SchemaValidationError",
    "SelectorValidationError",
    "assert_safe_display_url",
    "build_index_history_plan",
    "canonical_json_bytes",
    "canonical_sha256",
    "get_contract",
    "index_history_schema_fingerprint",
    "load_synthetic_fixture",
    "redact_mapping",
    "redact_text",
    "validate_error_envelope",
    "validate_index_history_envelope",
]
