"""Closed read-only rules for assembled industry research results."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any

from industry_alpha.investment_candidate_models import CANDIDATE_STATUSES

RESULT_CONTRACT_VERSION = "aquantai.industry-research-result-assembly.v1"
EXPLAINED_RESULT_CONTRACT_VERSION = "aquantai.industry-research-explained-result.v1"
DEFAULT_OPTION_LIMIT = 20
MAX_OPTION_LIMIT = 100
STAGE1_STATUS_ORDER = ("supported", "draft", "disputed", "rejected")
MISSING_REASON_ORDER = (
    "typed_semantics_missing",
    "company_research_missing",
    "investment_candidate_not_created_by_acceptance",
    "canonical_price_not_evaluated_by_acceptance",
    "structured_valuation_not_evaluated_by_acceptance",
)


class IndustryResearchResultError(RuntimeError):
    """Stable local read error for assembled industry research results."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def stored_utc(value: datetime) -> datetime:
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def recorded_boundary(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise IndustryResearchResultError(
            "industry_research_result_boundary_invalid",
            "as_of_recorded_at_utc must be an explicit UTC timestamp",
        )
    return value.astimezone(timezone.utc)


def explained_result_fingerprint(value: dict[str, Any]) -> str:
    """Fingerprint only the deterministic read projection; no clocks or hidden state."""
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def counter_text(counter: Counter[str], order: tuple[str, ...]) -> str:
    values = [f"{key} {counter[key]}" for key in order if counter[key]]
    return " · ".join(values) if values else "暂无"


def conclusion_cards(
    accepted_members: list[dict[str, Any]],
    supported_members: list[dict[str, Any]],
    *,
    exact_map: dict[str, Any],
    overlay: dict[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    stage_counts = Counter(item["assessment_status"] for item in accepted_members)
    semantic_count = sum(
        item["readiness"]["typed_semantics"]["state"] != "missing"
        for item in accepted_members
    )
    company_count = sum(
        item["readiness"]["company_research"]["state"] != "missing"
        for item in accepted_members
    )
    reasons = Counter(
        reason
        for item in accepted_members
        for reason in item["readiness"].get("reason_codes", [])
    )
    reason_order = {
        reason: index for index, reason in enumerate(MISSING_REASON_ORDER)
    }
    largest_gap = "暂无"
    if reasons:
        largest_gap = min(
            reasons,
            key=lambda reason: (
                -reasons[reason],
                reason_order.get(reason, len(reason_order)),
                reason,
            ),
        )
    candidate_value = {
        "unavailable_zero_supported": "无 supported 后续研究池",
        "unavailable": "尚无精确候选快照",
        "not_selected": "有可用快照，尚未选择",
    }.get(overlay["state"], overlay["state"])
    if overlay.get("snapshot") is not None:
        candidate_counts = Counter(
            row["candidate_status"] for row in overlay["snapshot"]["members"]
        )
        candidate_value = counter_text(candidate_counts, CANDIDATE_STATUSES)
    return (
        [
            {
                "label": "研究范围",
                "value": exact_map["title"],
                "source_layer": "accepted_snapshot",
            },
            {
                "label": "完整受益公司",
                "value": len(accepted_members),
                "source_layer": "accepted_snapshot",
            },
            {
                "label": "进入后续研究",
                "value": len(supported_members),
                "source_layer": "accepted_snapshot",
            },
            {
                "label": "受益状态",
                "value": counter_text(stage_counts, STAGE1_STATUS_ORDER),
                "source_layer": "accepted_snapshot",
            },
            {
                "label": "证据语义覆盖",
                "value": f"{semantic_count}/{len(accepted_members)}",
                "source_layer": "accepted_snapshot",
            },
            {
                "label": "公司研究准备度",
                "value": f"{company_count}/{len(accepted_members)}",
                "source_layer": "accepted_snapshot",
            },
            {
                "label": "当前候选状态",
                "value": candidate_value,
                "source_layer": "current_candidate_overlay",
            },
            {
                "label": "最大缺口",
                "value": largest_gap,
                "source_layer": "accepted_snapshot",
            },
        ],
        largest_gap,
    )


__all__ = (
    "DEFAULT_OPTION_LIMIT",
    "EXPLAINED_RESULT_CONTRACT_VERSION",
    "IndustryResearchResultError",
    "MAX_OPTION_LIMIT",
    "RESULT_CONTRACT_VERSION",
    "conclusion_cards",
    "explained_result_fingerprint",
    "recorded_boundary",
    "stored_utc",
)
