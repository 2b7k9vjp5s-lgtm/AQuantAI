"""Optional, citation-bound AI drafting for the V1 product workspace."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from industry_alpha.guarded_ai_adapter import (
    GuardedAIAdapter,
    GuardedAIProviderConfig,
    OpenAICompatibleGuardedAIAdapter,
)
from industry_alpha.guarded_ai_contracts import (
    MAX_OUTPUT_TOKENS,
    PROMPT_TEMPLATE_VERSION,
)
from industry_alpha.guarded_ai_service import _validate_draft_response
from industry_alpha.product_workspace import ProductWorkspaceError


class ProductWorkspaceAIService:
    def __init__(
        self,
        config: GuardedAIProviderConfig,
        *,
        adapter: GuardedAIAdapter | None = None,
    ) -> None:
        self._config = config
        self._adapter = adapter

    @classmethod
    def from_environment(cls) -> "ProductWorkspaceAIService":
        return cls(GuardedAIProviderConfig.from_environment())

    def preview(self, case_payload: dict[str, Any]) -> dict[str, Any]:
        manifest, canonical, fingerprint, item_ids = self._manifest(case_payload)
        return {
            "schema_version": "aquantai.product-research-ai-preview.v1",
            "manifest": manifest,
            "manifest_fingerprint": fingerprint,
            "evidence_reference_count": len(item_ids),
            "provider": self._config.public_profile().to_dict(),
            "notices": _notices(),
        }

    def generate(
        self,
        case_payload: dict[str, Any],
        *,
        expected_manifest_fingerprint: str,
        confirm_remote_transmission: bool,
    ) -> dict[str, Any]:
        if confirm_remote_transmission is not True:
            raise ProductWorkspaceError(
                "remote_transmission_not_confirmed",
                "Explicit remote transmission confirmation is required",
            )
        _manifest, canonical, fingerprint, item_ids = self._manifest(case_payload)
        if fingerprint != expected_manifest_fingerprint:
            raise ProductWorkspaceError(
                "ai_manifest_conflict",
                "The research case changed after preview; generate a new preview",
                status_code=409,
            )
        self._config.require_enabled()
        adapter = self._adapter or OpenAICompatibleGuardedAIAdapter(self._config)
        result = adapter.generate(
            canonical_manifest=canonical,
            manifest_fingerprint=fingerprint,
            prompt_template_version=PROMPT_TEMPLATE_VERSION,
            maximum_output_tokens=MAX_OUTPUT_TOKENS,
        )
        sections, warnings = _validate_draft_response(
            result.raw_content,
            expected_fingerprint=fingerprint,
            allowed_item_ids=frozenset(item_ids),
        )
        return {
            "schema_version": "aquantai.product-research-ai-draft.v1",
            "manifest_fingerprint": fingerprint,
            "sections": sections,
            "validation_warnings": warnings,
            "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "ephemeral_only": True,
            "notices": _notices(),
        }

    @staticmethod
    def _manifest(
        case_payload: dict[str, Any]
    ) -> tuple[dict[str, Any], str, str, set[str]]:
        revision = case_payload["current_revision"]
        references = revision["evidence_references"]
        if not references:
            raise ProductWorkspaceError(
                "insufficient_evidence",
                "AI drafting requires at least one accepted evidence reference",
                status_code=409,
            )
        item_ids = {f"evidence:{item['evidence_id']}" for item in references}
        manifest = {
            "schema_version": "aquantai.product-research-ai-manifest.v1",
            "case": case_payload["case"],
            "revision": {
                key: revision[key]
                for key in (
                    "revision_id",
                    "revision_no",
                    "title",
                    "research_question",
                    "workflow_state",
                    "conclusion_status",
                    "information_cutoff_date",
                    "content",
                )
            },
            "accepted_evidence": [
                {
                    "manifest_item_id": f"evidence:{item['evidence_id']}",
                    "evidence_id": item["evidence_id"],
                    "source": item["source"],
                    "document_id": item["document_id"],
                    "page": item["page"],
                    "grade": item["evidence_grade"],
                    "content_fragment": item["content_fragment"],
                }
                for item in references
            ],
            "instructions": {
                "evidence_only": True,
                "insufficient_evidence_must_be_explicit": True,
                "no_investment_advice": True,
                "no_evidence_mutation": True,
            },
        }
        canonical = json.dumps(
            manifest,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        fingerprint = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return manifest, canonical, fingerprint, item_ids


def _notices() -> dict[str, bool]:
    return {
        "draft_only": True,
        "evidence_references_required": True,
        "ai_cannot_accept_or_reject_evidence": True,
        "ai_cannot_select_authoritative_revision": True,
        "ai_output_is_not_investment_advice": True,
    }
