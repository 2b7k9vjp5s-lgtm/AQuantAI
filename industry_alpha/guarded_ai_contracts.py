"""Contracts and stable failures for Guarded AI Research Assistance v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


MANIFEST_SCHEMA_VERSION = "guarded-ai-manifest-v1"
PROJECTION_VERSION = "guarded-ai-company-research-projection-v1"
DRAFT_SCHEMA_VERSION = "guarded-ai-draft-v1"
PROMPT_TEMPLATE_VERSION = "guarded-ai-company-research-v1"
ADAPTER_VERSION = "openai-compatible-https-v1"
MAX_CANONICAL_INPUT_CHARS = 60_000
MAX_OUTPUT_TOKENS = 2_000
REQUEST_TIMEOUT_SECONDS = 60

ALLOWED_SECTION_NAMES = (
    "evidence_grounded_summary",
    "supporting_evidence",
    "conflicting_evidence",
    "missing_evidence",
    "revision_and_provenance_warnings",
    "research_questions",
    "human_review_checklist",
    "limitations",
)


class GuardedAIError(RuntimeError):
    """Base class carrying a stable public failure code."""

    status_code = 503
    failure_code = "guarded_ai_unavailable"
    public_message = "Guarded AI is unavailable. Verify local configuration and try again."


class GuardedAIConfigurationError(GuardedAIError):
    failure_code = "guarded_ai_configuration_unavailable"


class GuardedAIConflictError(GuardedAIError):
    status_code = 409
    failure_code = "guarded_ai_manifest_changed"
    public_message = "The research input changed after preview. Preview it again before generating."


class GuardedAIInputTooLargeError(GuardedAIError):
    status_code = 413
    failure_code = "guarded_ai_input_too_large"
    public_message = "The research input exceeds the Guarded AI v1 limit and was not transmitted."


class GuardedAIRateLimitError(GuardedAIError):
    status_code = 429
    failure_code = "guarded_ai_rate_limited"
    public_message = "The configured AI service rate limit was reached. No fallback was attempted."


class GuardedAIProviderError(GuardedAIError):
    failure_code = "guarded_ai_provider_unavailable"
    public_message = "The configured AI service is unavailable. No fallback was attempted."


class GuardedAITimeoutError(GuardedAIError):
    status_code = 504
    failure_code = "guarded_ai_provider_timeout"
    public_message = "The configured AI service timed out. No retry or fallback was attempted."


class GuardedAIResponseValidationError(GuardedAIError):
    status_code = 502
    failure_code = "guarded_ai_response_invalid"
    public_message = "The AI response failed strict validation and was discarded."


@dataclass(frozen=True)
class GuardedAIProviderPublicProfile:
    enabled: bool
    available: bool
    provider_id: str | None
    model_id: str | None
    data_use_notice: str | None
    cost_estimate: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GuardedAIManifest:
    content: dict[str, Any]
    canonical_json: str
    fingerprint: str
    manifest_item_ids: frozenset[str]
    input_character_count: int
    included_sections: tuple[str, ...]
    unavailable_sections: tuple[str, ...]


@dataclass(frozen=True)
class GuardedAIPreviewContract:
    schema_version: str
    projection_version: str
    company_research_id: str
    as_of_cutoff: str | None
    manifest_fingerprint: str
    input_character_count: int
    maximum_input_characters: int
    included_sections: tuple[str, ...]
    unavailable_sections: tuple[str, ...]
    manifest: dict[str, Any]
    provider: GuardedAIProviderPublicProfile
    generated_at_utc: str
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GuardedAIAdapterResult:
    raw_content: str
    provider_request_id: str | None = None


@dataclass(frozen=True)
class GuardedAIDraftContract:
    schema_version: str
    manifest_fingerprint: str
    provider_id: str
    model_id: str
    adapter_version: str
    prompt_template_version: str
    generated_at_utc: str
    sections: dict[str, tuple[dict[str, Any], ...]]
    validation_warnings: tuple[str, ...]
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
