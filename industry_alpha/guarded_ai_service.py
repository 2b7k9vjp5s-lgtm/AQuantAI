"""Application service for local preview and one guarded AI request."""

from __future__ import annotations

import hmac
import json
import re
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from industry_alpha.guarded_ai_adapter import (
    GuardedAIAdapter,
    GuardedAIProviderConfig,
    OpenAICompatibleGuardedAIAdapter,
)
from industry_alpha.guarded_ai_contracts import (
    ADAPTER_VERSION,
    ALLOWED_SECTION_NAMES,
    DRAFT_SCHEMA_VERSION,
    MAX_CANONICAL_INPUT_CHARS,
    MAX_OUTPUT_TOKENS,
    PROMPT_TEMPLATE_VERSION,
    PROJECTION_VERSION,
    GuardedAIConflictError,
    GuardedAIDraftContract,
    GuardedAIPreviewContract,
    GuardedAIResponseValidationError,
)
from industry_alpha.guarded_ai_manifest import build_guarded_ai_manifest

_MAX_SECTION_ENTRIES = 20
_MAX_ENTRY_TEXT_CHARS = 8_000
_MAX_ENTRY_CITATIONS = 50
_MAX_VALIDATION_WARNINGS = 20
_MAX_WARNING_CHARS = 500

_PROHIBITED_OUTPUT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"建议.{0,8}(买入|卖出|持有)",
        r"(买入|卖出|持有).{0,8}建议",
        r"目标价\s*[:：为]",
        r"预期收益\s*[:：为]",
        r"上涨空间\s*[:：为]",
        r"下跌空间\s*[:：为]",
        r"公允价值\s*[:：为]",
        r"\b(buy|sell|hold)\s+(recommendation|rating)\b",
        r"\btarget\s+price\s*[:=]",
        r"\bexpected\s+return\s*[:=]",
        r"\b(upside|downside)\s*(of|:|=)",
    )
)


class GuardedAIService:
    """Coordinates deterministic projection, one adapter call, and validation."""

    def __init__(
        self,
        config: GuardedAIProviderConfig,
        *,
        adapter: GuardedAIAdapter | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._config = config
        self._adapter = adapter
        self._now_factory = now_factory or (lambda: datetime.now(timezone.utc))

    @classmethod
    def from_environment(cls) -> "GuardedAIService":
        return cls(GuardedAIProviderConfig.from_environment())

    def preview(
        self,
        workspace: Mapping[str, Any],
        *,
        company_research_id: str,
        as_of_cutoff: str | None,
    ) -> GuardedAIPreviewContract:
        manifest = build_guarded_ai_manifest(
            workspace,
            company_research_id=company_research_id,
            as_of_cutoff=as_of_cutoff,
        )
        return GuardedAIPreviewContract(
            schema_version="guarded-ai-preview-v1",
            projection_version=PROJECTION_VERSION,
            company_research_id=company_research_id,
            as_of_cutoff=as_of_cutoff,
            manifest_fingerprint=manifest.fingerprint,
            input_character_count=manifest.input_character_count,
            maximum_input_characters=MAX_CANONICAL_INPUT_CHARS,
            included_sections=manifest.included_sections,
            unavailable_sections=manifest.unavailable_sections,
            manifest=manifest.content,
            provider=self._config.public_profile(),
            generated_at_utc=_timestamp(self._now_factory()),
            notices=_notices(),
        )

    def generate(
        self,
        workspace: Mapping[str, Any],
        *,
        company_research_id: str,
        as_of_cutoff: str | None,
        expected_manifest_fingerprint: str,
        confirm_remote_transmission: bool,
    ) -> GuardedAIDraftContract:
        if confirm_remote_transmission is not True:
            raise ValueError("explicit remote transmission confirmation is required")
        manifest = build_guarded_ai_manifest(
            workspace,
            company_research_id=company_research_id,
            as_of_cutoff=as_of_cutoff,
        )
        if not hmac.compare_digest(
            manifest.fingerprint,
            expected_manifest_fingerprint,
        ):
            raise GuardedAIConflictError()

        self._config.require_enabled()
        adapter = self._adapter or OpenAICompatibleGuardedAIAdapter(self._config)
        result = adapter.generate(
            canonical_manifest=manifest.canonical_json,
            manifest_fingerprint=manifest.fingerprint,
            prompt_template_version=PROMPT_TEMPLATE_VERSION,
            maximum_output_tokens=MAX_OUTPUT_TOKENS,
        )
        sections, warnings = _validate_draft_response(
            result.raw_content,
            expected_fingerprint=manifest.fingerprint,
            allowed_item_ids=manifest.manifest_item_ids,
        )
        provider_id = self._config.provider_id
        model_id = self._config.model_id
        assert provider_id is not None and model_id is not None
        return GuardedAIDraftContract(
            schema_version=DRAFT_SCHEMA_VERSION,
            manifest_fingerprint=manifest.fingerprint,
            provider_id=provider_id,
            model_id=model_id,
            adapter_version=getattr(adapter, "adapter_version", ADAPTER_VERSION),
            prompt_template_version=PROMPT_TEMPLATE_VERSION,
            generated_at_utc=_timestamp(self._now_factory()),
            sections=sections,
            validation_warnings=warnings,
            notices=_notices(),
        )


def _validate_draft_response(
    raw_content: str,
    *,
    expected_fingerprint: str,
    allowed_item_ids: frozenset[str],
) -> tuple[dict[str, tuple[dict[str, Any], ...]], tuple[str, ...]]:
    try:
        payload = json.loads(raw_content)
    except (json.JSONDecodeError, TypeError):
        raise GuardedAIResponseValidationError() from None
    if not isinstance(payload, dict):
        raise GuardedAIResponseValidationError()
    if set(payload) != {
        "schema_version",
        "manifest_fingerprint",
        "sections",
        "validation_warnings",
    }:
        raise GuardedAIResponseValidationError()
    if payload["schema_version"] != DRAFT_SCHEMA_VERSION:
        raise GuardedAIResponseValidationError()
    if payload["manifest_fingerprint"] != expected_fingerprint:
        raise GuardedAIResponseValidationError()

    raw_sections = payload["sections"]
    if not isinstance(raw_sections, dict) or set(raw_sections) != set(ALLOWED_SECTION_NAMES):
        raise GuardedAIResponseValidationError()
    sections: dict[str, tuple[dict[str, Any], ...]] = {}
    for section_name in ALLOWED_SECTION_NAMES:
        raw_entries = raw_sections[section_name]
        if not isinstance(raw_entries, list) or len(raw_entries) > _MAX_SECTION_ENTRIES:
            raise GuardedAIResponseValidationError()
        entries: list[dict[str, Any]] = []
        for raw_entry in raw_entries:
            entries.append(_validate_entry(raw_entry, allowed_item_ids))
        sections[section_name] = tuple(entries)

    raw_warnings = payload["validation_warnings"]
    if not isinstance(raw_warnings, list) or len(raw_warnings) > _MAX_VALIDATION_WARNINGS:
        raise GuardedAIResponseValidationError()
    warnings: list[str] = []
    for warning in raw_warnings:
        if not isinstance(warning, str) or not warning.strip() or len(warning) > _MAX_WARNING_CHARS:
            raise GuardedAIResponseValidationError()
        warnings.append(warning.strip())
    return sections, tuple(warnings)


def _validate_entry(
    raw_entry: Any,
    allowed_item_ids: frozenset[str],
) -> dict[str, Any]:
    if not isinstance(raw_entry, dict) or set(raw_entry) != {"text", "manifest_item_ids"}:
        raise GuardedAIResponseValidationError()
    text = raw_entry["text"]
    citations = raw_entry["manifest_item_ids"]
    if (
        not isinstance(text, str)
        or not text.strip()
        or len(text) > _MAX_ENTRY_TEXT_CHARS
        or any(pattern.search(text) for pattern in _PROHIBITED_OUTPUT_PATTERNS)
    ):
        raise GuardedAIResponseValidationError()
    if not isinstance(citations, list) or len(citations) > _MAX_ENTRY_CITATIONS:
        raise GuardedAIResponseValidationError()
    normalized: list[str] = []
    for item_id in citations:
        if not isinstance(item_id, str) or item_id not in allowed_item_ids:
            raise GuardedAIResponseValidationError()
        if item_id in normalized:
            raise GuardedAIResponseValidationError()
        normalized.append(item_id)
    return {"text": text.strip(), "manifest_item_ids": tuple(normalized)}


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _notices() -> dict[str, Any]:
    return {
        "draft_label": "AI 研究草稿（D3，需人工核验，不构成投资建议）",
        "d3_draft_only": True,
        "ephemeral_only": True,
        "not_investment_advice": True,
        "no_accepted_state_mutation": True,
        "no_browsing_search_tools_or_retrieval": True,
        "no_provider_or_model_fallback": True,
        "explicit_confirmation_required": True,
    }
