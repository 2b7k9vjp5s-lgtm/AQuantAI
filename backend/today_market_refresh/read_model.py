"""Source-neutral ordinary-user Today Market read model.

This module is pure projection logic. It performs no database access, network access,
credential lookup, persistence, runtime command, Provider selection, AI call, research
mutation, recommendation, portfolio action, or trading action.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from backend.today_market_refresh.fingerprint import canonical_sha256
from market_cockpit.today_market_rule_contracts import (
    ANOMALY_RULE_VERSION,
    MARKET_RULE_VERSION,
    SECTOR_RULE_VERSION,
    MarketOverviewInput,
    SectorRuleInput,
    StockRuleInput,
)
from market_cockpit.today_market_rules import (
    calculate_market_overview,
    calculate_sector_hotspots,
    calculate_stock_anomalies,
)

READ_MODEL_VERSION = "aquantai.today-market-read-model.v1"
ALLOWED_REFRESH_STATES = frozenset(
    {
        "current",
        "checking",
        "refresh_required",
        "refreshing",
        "refreshed",
        "not_initialized",
        "manual_catchup_required",
        "blocked_source_contract",
        "failed_retained_prior",
        "cancelled_retained_prior",
    }
)

_FOCUS_SECTOR_STATES = (
    "strengthening",
    "new",
    "spreading",
    "persistent_strong",
)
_RISK_SECTOR_STATES = ("high_level_divergence", "cooling")
_SECTOR_STATE_ORDER = (
    "strengthening",
    "new",
    "spreading",
    "persistent_strong",
    "high_level_divergence",
    "cooling",
    "insufficient_coverage",
    "neutral",
)
_REFRESH_LABELS = {
    "current": "本地数据已是当前范围内最新完整状态",
    "checking": "正在检查本地数据新鲜度",
    "refresh_required": "存在可执行的一次有界更新",
    "refreshing": "正在执行一次有界更新，旧快照继续有效",
    "refreshed": "完整候选已生成；模拟结果不会写入生产历史",
    "not_initialized": "尚未完成本地初始化",
    "manual_catchup_required": "缺失交易日超过自动更新上限，需要明确手动补齐",
    "blocked_source_contract": "真实数据源尚未获授权，未执行联网更新",
    "failed_retained_prior": "更新失败，上一份完整快照保持有效",
    "cancelled_retained_prior": "更新取消，上一份完整快照保持有效",
}


@dataclass(frozen=True, slots=True)
class TodayMarketRuleProjectionInputs:
    """Explicit exact Slice B inputs available to the projection boundary."""

    market_overview: MarketOverviewInput | None = None
    sectors: tuple[SectorRuleInput, ...] = ()
    stocks: tuple[StockRuleInput, ...] = ()
    market_unavailable_reason: str | None = None
    sector_unavailable_reason: str | None = None
    stock_unavailable_reasons: tuple[str, ...] = ()


def build_today_market_read_model(
    *,
    snapshot_id: str,
    snapshot_content_fingerprint: str,
    data_date: str,
    projected_snapshot: Mapping[str, Any],
    runtime_status: Mapping[str, Any],
    rule_inputs: TodayMarketRuleProjectionInputs | None = None,
) -> dict[str, Any]:
    """Build the deterministic source-neutral ordinary-user projection."""

    inputs = rule_inputs or TodayMarketRuleProjectionInputs(
        market_unavailable_reason="market_rule_inputs_unavailable",
        sector_unavailable_reason="sector_rule_inputs_unavailable",
        stock_unavailable_reasons=("stock_rule_inputs_unavailable",),
    )
    refresh_state = _project_refresh_state(runtime_status)
    raw = _raw_snapshot(projected_snapshot)

    market_result = (
        calculate_market_overview(inputs.market_overview)
        if inputs.market_overview is not None
        else None
    )
    sector_results = (
        calculate_sector_hotspots(inputs.sectors) if inputs.sectors else ()
    )
    stock_result = calculate_stock_anomalies(inputs.stocks) if inputs.stocks else None

    market_projection = _market_projection(
        market_result,
        raw,
        unavailable_reason=(
            inputs.market_unavailable_reason
            or "market_rule_inputs_unavailable"
        ),
    )
    sector_projection = _sector_projection(
        sector_results,
        unavailable_reason=(
            inputs.sector_unavailable_reason
            or "sector_rule_inputs_unavailable"
        ),
    )
    stock_projection = _stock_projection(
        stock_result,
        inputs.stock_unavailable_reasons,
    )

    warnings = _stable_unique(
        [
            *_snapshot_warnings(projected_snapshot),
            *_projection_warnings(
                refresh_state,
                market_projection,
                sector_projection,
                stock_projection,
            ),
        ]
    )

    payload: dict[str, Any] = {
        "read_model_version": READ_MODEL_VERSION,
        "snapshot_id": snapshot_id,
        "data_date": data_date,
        "data_status": str(projected_snapshot.get("status", "unknown")),
        "source_summary": _source_summary(
            raw=raw,
            projected_snapshot=projected_snapshot,
            runtime_status=runtime_status,
            refresh_state=refresh_state,
            data_date=data_date,
        ),
        "coverage": _coverage(projected_snapshot, raw, sector_projection),
        "refresh_state": refresh_state,
        "market_state": (
            market_result.market_state
            if market_result is not None
            else "insufficient_coverage"
        ),
        "core_indices": _core_indices(projected_snapshot),
        "market_overview": market_projection,
        "sector_groups": sector_projection,
        "stock_anomalies": stock_projection,
        "research_link_summary": {
            "status": "not_resolved",
            "message": (
                "当前 Slice 只读取市场事实；没有精确已接受研究链接时，"
                "不会生成或推断研究解释。"
            ),
            "mutation_performed": False,
        },
        "warnings": warnings,
        "technical_details": {
            "collapsed_by_default": True,
            "snapshot_content_fingerprint": snapshot_content_fingerprint,
            "runtime_scope_revision_id": runtime_status.get(
                "runtime_scope_revision_id"
            ),
            "runtime_status_fingerprint": runtime_status.get(
                "runtime_status_fingerprint"
            ),
            "runtime_phase": runtime_status.get("phase"),
            "runtime_source_mode": runtime_status.get("source_mode"),
            "runtime_is_synthetic": bool(runtime_status.get("is_synthetic")),
            "market_rule_version": MARKET_RULE_VERSION,
            "sector_rule_version": SECTOR_RULE_VERSION,
            "anomaly_rule_version": ANOMALY_RULE_VERSION,
            "market_rule_input_available": inputs.market_overview is not None,
            "sector_rule_input_count": len(inputs.sectors),
            "stock_rule_input_count": len(inputs.stocks),
            "network_used": False,
            "read_only": True,
        },
    }
    payload["read_model_fingerprint"] = canonical_sha256(payload)
    return payload


def _project_refresh_state(runtime_status: Mapping[str, Any]) -> str:
    phase = str(runtime_status.get("phase") or "")
    mock_enabled = bool(runtime_status.get("mock_enabled"))
    mapping = {
        "no_refresh_needed": "current",
        "refresh_in_progress": "refreshing",
        "demo_published": "refreshed",
        "not_initialized": "not_initialized",
        "manual_catchup_required": "manual_catchup_required",
        "failed_retained_prior": "failed_retained_prior",
        "cancelled_retained_prior": "cancelled_retained_prior",
        "scope_stale": "checking",
    }
    if phase == "mock_not_enabled":
        state = "blocked_source_contract"
    elif phase == "prior_snapshot_ready":
        state = "refresh_required" if mock_enabled else "blocked_source_contract"
    else:
        state = mapping.get(phase, "checking")
    if state not in ALLOWED_REFRESH_STATES:
        return "checking"
    return state


def _source_summary(
    *,
    raw: Mapping[str, Any],
    projected_snapshot: Mapping[str, Any],
    runtime_status: Mapping[str, Any],
    refresh_state: str,
    data_date: str,
) -> dict[str, Any]:
    provenance = raw.get("provenance")
    provider = provenance.get("provider") if isinstance(provenance, Mapping) else None
    scope = projected_snapshot.get("scope_and_freshness")
    coverage_label = (
        scope.get("coverage_label")
        if isinstance(scope, Mapping)
        else "明确选择的本地范围"
    )
    return {
        "source_label": (
            f"本地已持久化数据 · {provider}"
            if provider
            else "本地已持久化数据"
        ),
        "last_complete_data_date": data_date,
        "coverage_label": coverage_label,
        "refresh_label": _REFRESH_LABELS[refresh_state],
        "dominant_action": _dominant_action(refresh_state, runtime_status),
        "live_network_authorized": False,
    }


def _dominant_action(
    refresh_state: str,
    runtime_status: Mapping[str, Any],
) -> dict[str, Any]:
    allowed = set(runtime_status.get("allowed_actions") or [])
    if refresh_state in {"failed_retained_prior", "cancelled_retained_prior"} and (
        "explicit_user_retry" in allowed
    ):
        return {
            "code": "explicit_user_retry",
            "label": "重新运行一次模拟更新",
            "enabled": True,
            "automatic": False,
        }
    if refresh_state == "refresh_required" and (
        "automatic_first_entry" in allowed
    ):
        return {
            "code": "automatic_first_entry",
            "label": "系统将执行一次有界模拟更新",
            "enabled": False,
            "automatic": True,
        }
    if refresh_state == "refreshing":
        return {
            "code": "refresh_in_progress",
            "label": "正在更新，继续显示上一份完整快照",
            "enabled": False,
            "automatic": True,
        }
    return {
        "code": "reread_local_snapshot",
        "label": "重新读取本地快照",
        "enabled": True,
        "automatic": False,
    }


def _market_projection(
    result: Any,
    raw: Mapping[str, Any],
    *,
    unavailable_reason: str,
) -> dict[str, Any]:
    metrics = raw.get("metrics") if isinstance(raw, Mapping) else None
    selected_scope = {}
    if isinstance(metrics, Mapping):
        latest = metrics.get("latest_session")
        amount = metrics.get("amount_participation")
        if isinstance(latest, Mapping):
            selected_scope.update(
                {
                    "advancing_count": latest.get("advancing_count"),
                    "declining_count": latest.get("declining_count"),
                    "unchanged_count": latest.get("unchanged_count"),
                    "advance_ratio": latest.get("advance_ratio"),
                    "breadth_balance": latest.get("breadth_balance"),
                    "median_return": latest.get("median_return"),
                }
            )
        if isinstance(amount, Mapping):
            selected_scope["amount_ratio_20"] = amount.get(
                "ratio_to_prior_20_session_median"
            )
    if result is None:
        return {
            "status": "unavailable",
            "reason": unavailable_reason,
            "selected_scope_context": selected_scope,
            "message": (
                "当前本地范围不能证明完整的 Market Overview v1 权威输入；"
                "所选范围的已有确定性指标仅作为范围内背景展示。"
            ),
        }
    return {
        "status": "ready",
        "result": asdict(result),
        "result_fingerprint": result.fingerprint,
        "selected_scope_context": selected_scope,
    }


def _sector_projection(
    results: tuple[Any, ...],
    *,
    unavailable_reason: str,
) -> dict[str, Any]:
    if not results:
        return {
            "status": "unavailable",
            "reason": unavailable_reason,
            "groups": {state: [] for state in _SECTOR_STATE_ORDER},
            "focus_states": list(_FOCUS_SECTOR_STATES),
            "risk_states": list(_RISK_SECTOR_STATES),
        }
    groups: dict[str, list[dict[str, Any]]] = {
        state: [] for state in _SECTOR_STATE_ORDER
    }
    for result in results:
        item = asdict(result)
        item["result_fingerprint"] = result.fingerprint
        groups[result.state].append(item)
    for state in groups:
        groups[state].sort(key=lambda item: item["sector_code"])
    return {
        "status": "ready",
        "groups": groups,
        "focus_states": list(_FOCUS_SECTOR_STATES),
        "risk_states": list(_RISK_SECTOR_STATES),
        "result_count": len(results),
        "constituent_confirmed_count": sum(
            result.dated_membership_revision_id is not None
            and result.state != "insufficient_coverage"
            for result in results
        ),
    }


def _stock_projection(
    result: Any,
    unavailable_reasons: tuple[str, ...],
) -> dict[str, Any]:
    if result is None:
        return {
            "status": "unavailable",
            "reasons": list(
                unavailable_reasons or ("stock_rule_inputs_unavailable",)
            ),
            "items": [],
            "diagnostics": [],
        }
    return {
        "status": "ready",
        "rule_version": result.rule_version,
        "items": [asdict(item) for item in result.anomalies],
        "diagnostics": [asdict(item) for item in result.diagnostics],
        "result_fingerprint": result.fingerprint,
        "additional_unavailable_reasons": list(unavailable_reasons),
    }


def _core_indices(projected_snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    supported = projected_snapshot.get("supported_analysis")
    if not isinstance(supported, Mapping):
        return []
    benchmark = supported.get("benchmark")
    if not isinstance(benchmark, Mapping) or benchmark.get("status") == "not_selected":
        return []
    metrics = benchmark.get("metrics")
    if not isinstance(metrics, list):
        return []
    values: list[dict[str, Any]] = []
    for item in metrics:
        if not isinstance(item, Mapping):
            continue
        values.append(
            {
                "index_code": item.get("index_code"),
                "latest_close": item.get("latest_close"),
                "latest_return": item.get("latest_return"),
                "above_sma20": item.get("above_sma20"),
                "realized_volatility_20": item.get("realized_volatility_20"),
            }
        )
    return values


def _coverage(
    projected_snapshot: Mapping[str, Any],
    raw: Mapping[str, Any],
    sector_projection: Mapping[str, Any],
) -> dict[str, Any]:
    scope = projected_snapshot.get("scope_and_freshness")
    supported = projected_snapshot.get("supported_analysis")
    scope_map = scope if isinstance(scope, Mapping) else {}
    supported_map = supported if isinstance(supported, Mapping) else {}
    diagnostics_container = supported_map.get("data_completeness")
    diagnostics = (
        diagnostics_container.get("latest_data_diagnostics")
        if isinstance(diagnostics_container, Mapping)
        else None
    )
    diagnostics_map = diagnostics if isinstance(diagnostics, Mapping) else {}
    metrics = raw.get("metrics") if isinstance(raw, Mapping) else None
    latest = metrics.get("latest_session") if isinstance(metrics, Mapping) else None
    latest_map = latest if isinstance(latest, Mapping) else {}
    valid_returns = sum(
        int(latest_map.get(key) or 0)
        for key in ("advancing_count", "declining_count", "unchanged_count")
    )
    sector_context = supported_map.get("sector")
    sector_count = (
        int(sector_context.get("requested_sector_count") or 0)
        if isinstance(sector_context, Mapping)
        and sector_context.get("status") != "not_selected"
        else 0
    )
    unsupported = [
        "full_market_universe_not_proven"
        if scope_map.get("scope_coverage_status") == "unverified_selected_scope"
        else None,
        "dated_sector_membership_unavailable"
        if sector_projection.get("constituent_confirmed_count", 0) == 0
        else None,
        "reference_close_semantics_unavailable",
    ]
    return {
        "expected_instruments": scope_map.get("universe_stock_count"),
        "accounted_instruments": scope_map.get("available_stock_count"),
        "valid_returns": valid_returns,
        "no_trade_instruments": diagnostics_map.get("no_trade_latest_count"),
        "missing_source_rows": diagnostics_map.get(
            "stale_or_missing_latest_count"
        ),
        "identity_conflicts": None,
        "sector_count": sector_count,
        "sector_membership_coverage": (
            "unavailable"
            if sector_projection.get("constituent_confirmed_count", 0) == 0
            else "available"
        ),
        "history_window_coverage": scope_map.get("completeness_status"),
        "scope_coverage_status": scope_map.get("scope_coverage_status"),
        "unsupported_metric_reasons": [item for item in unsupported if item],
    }


def _projection_warnings(
    refresh_state: str,
    market_projection: Mapping[str, Any],
    sector_projection: Mapping[str, Any],
    stock_projection: Mapping[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if refresh_state == "blocked_source_contract":
        warnings.append(
            "真实数据源合同条件尚未满足；页面未执行联网更新，继续显示本地快照。"
        )
    if market_projection.get("status") != "ready":
        warnings.append("完整市场范围尚未被证明，Market Overview v1 不作外推。")
    if sector_projection.get("constituent_confirmed_count", 0) == 0:
        warnings.append(
            "缺少历史生效的板块成分权威数据，成分确认型热点结论保持不可用。"
        )
    if stock_projection.get("status") != "ready":
        warnings.append("个股异动输入不足时只显示明确不可用原因，不补推测值。")
    return warnings


def _snapshot_warnings(projected_snapshot: Mapping[str, Any]) -> list[str]:
    scope = projected_snapshot.get("scope_and_freshness")
    if not isinstance(scope, Mapping):
        return []
    warnings = scope.get("warnings")
    return [str(item) for item in warnings] if isinstance(warnings, list) else []


def _raw_snapshot(projected_snapshot: Mapping[str, Any]) -> Mapping[str, Any]:
    technical = projected_snapshot.get("technical_details")
    if not isinstance(technical, Mapping):
        return {}
    raw = technical.get("raw_market_cockpit_snapshot")
    return raw if isinstance(raw, Mapping) else {}


def _stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
