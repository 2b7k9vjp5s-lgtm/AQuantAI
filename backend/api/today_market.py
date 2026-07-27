"""Read-only FastAPI boundary for the Personal Research Workbench Today Market slice."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from backend.database.benchmark_data import BENCHMARK_DATASET
from backend.database.models import IngestionRun
from backend.database.sector_data import SECTOR_DATASET
from backend.database.series import (
    BenchmarkSeriesIdentity,
    SectorSeriesIdentity,
    SnapshotSeriesError,
    SnapshotSeriesIdentity,
    validate_benchmark_series_identity,
    validate_sector_series_identity,
    validate_series_key,
    validate_snapshot_series_identity,
)
from market_cockpit.benchmark_calculator import BenchmarkCalculationError
from market_cockpit.benchmark_repository import (
    BenchmarkRepository,
    BenchmarkSelectionError,
    BenchmarkSnapshotNotFound,
)
from market_cockpit.calculator import MarketCockpitCalculationError
from market_cockpit.repository import (
    MARKET_DATASET,
    MarketCockpitRepository,
    MarketCockpitSelectionError,
    MarketCockpitSnapshotNotFound,
)
from market_cockpit.sector_calculator import SectorCalculationError
from market_cockpit.sector_repository import (
    SectorRepository,
    SectorSelectionError,
    SectorSnapshotNotFound,
)
from market_cockpit.service import MarketCockpitService

from backend.today_market_refresh.contracts import RefreshTrigger, SnapshotReference
from backend.today_market_refresh.fingerprint import canonical_sha256
from backend.today_market_refresh.runtime import (
    RUNTIME_SCOPE_VERSION,
    RuntimeScopeConflict,
    RuntimeStatusConflict,
    TodayMarketMockRuntimeConfigurationV1,
    TodayMarketPriorSnapshotContext,
    TodayMarketRuntimeCoordinator,
    TodayMarketRuntimeScopeV1,
    build_runtime_scope,
)

router = APIRouter(prefix="/today-market/api", tags=["today-market"])
_CATALOG_LIMIT = 20
_FAMILY_BY_DATASET = {
    MARKET_DATASET: "equity",
    BENCHMARK_DATASET: "benchmark",
    SECTOR_DATASET: "sector",
}

SNAPSHOT_IDENTITY_VERSION = "aquantai.today-market-local-snapshot-identity.v1"
SNAPSHOT_CONTENT_VERSION = "aquantai.today-market-local-snapshot-content.v1"
_DATASET_BY_RUNTIME_FAMILY = {
    "equity": MARKET_DATASET,
    "benchmark": BENCHMARK_DATASET,
    "sector": SECTOR_DATASET,
}
_ALLOWED_RUNTIME_COMMAND_FIELDS = {
    "runtime_scope_version",
    "runtime_scope_revision_id",
    "prior_snapshot_id",
    "prior_snapshot_content_fingerprint",
    "as_of_cutoff",
    "as_of_recorded_at_utc",
    "equity_series_key",
    "benchmark_series_key",
    "sector_series_key",
    "trigger",
    "expected_runtime_status_fingerprint",
}
_DOMAIN_SNAPSHOT_KEYS = (
    "provenance",
    "universe_stock_count",
    "available_stock_count",
    "scope_coverage_status",
    "calculation_status",
    "completeness_status",
    "warnings",
    "price_behavior_context",
    "liquidity_context",
    "benchmark_context",
    "sector_context",
    "latest_data_diagnostics",
)


@dataclass(frozen=True)
class TodayMarketBoundaries:
    cutoff: date
    cutoff_compact: str
    recorded_at: datetime
    recorded_at_iso: str


@dataclass(frozen=True)
class TodayMarketSnapshotRequest:
    equity_series_key: str
    benchmark_series_key: str | None
    sector_series_key: str | None
    boundaries: TodayMarketBoundaries


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def require_today_market_boundaries(
    as_of_cutoff: str | None = Query(default=None),
    as_of_recorded_at_utc: str | None = Query(default=None),
) -> TodayMarketBoundaries:
    """Validate both boundaries before any database resource is constructed."""
    if as_of_cutoff is None:
        raise _error(422, "today_market_cutoff_required", "请选择信息截止日。")
    if as_of_recorded_at_utc is None:
        raise _error(422, "today_market_recorded_at_required", "请选择系统记录时间。")
    try:
        cutoff = datetime.strptime(as_of_cutoff.strip().replace("-", ""), "%Y%m%d").date()
    except ValueError as exc:
        raise _error(
            422,
            "today_market_cutoff_invalid",
            "信息截止日必须使用 YYYY-MM-DD 格式。",
        ) from exc
    try:
        recorded = datetime.fromisoformat(
            as_of_recorded_at_utc.strip().replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise _error(
            422,
            "today_market_recorded_at_invalid",
            "系统记录时间必须使用带时区的 ISO-8601 格式。",
        ) from exc
    if recorded.tzinfo is None or recorded.utcoffset() is None:
        raise _error(
            422,
            "today_market_recorded_at_timezone_required",
            "系统记录时间必须包含明确时区。",
        )
    recorded_utc = recorded.astimezone(timezone.utc)
    return TodayMarketBoundaries(
        cutoff=cutoff,
        cutoff_compact=cutoff.strftime("%Y%m%d"),
        recorded_at=recorded_utc,
        recorded_at_iso=_utc_iso(recorded_utc),
    )


def require_today_market_snapshot_request(
    boundaries: TodayMarketBoundaries = Depends(require_today_market_boundaries),
    equity_series_key: str | None = Query(default=None),
    benchmark_series_key: str | None = Query(default=None),
    sector_series_key: str | None = Query(default=None),
) -> TodayMarketSnapshotRequest:
    """Validate exact keys before the database dependency is constructed."""
    if equity_series_key is None:
        raise _error(
            422,
            "today_market_equity_selection_required",
            "请先选择一个本地股票数据范围。",
        )
    try:
        equity = validate_series_key(equity_series_key)
        benchmark = (
            validate_series_key(benchmark_series_key)
            if benchmark_series_key is not None
            else None
        )
        sector = (
            validate_series_key(sector_series_key)
            if sector_series_key is not None
            else None
        )
    except SnapshotSeriesError as exc:
        raise _error(
            422,
            "today_market_series_key_invalid",
            "所选本地数据标识无效，请重新读取本地数据列表。",
        ) from exc
    return TodayMarketSnapshotRequest(equity, benchmark, sector, boundaries)


def get_today_market_session_factory(
    _boundaries: TodayMarketBoundaries = Depends(require_today_market_boundaries),
) -> Iterator[sessionmaker[Session]]:
    """Open local database resources only after boundary validation."""
    try:
        engine = build_engine()
    except RuntimeError as exc:
        raise _error(
            503,
            "today_market_database_unavailable",
            "本地数据库不可用，请检查数据库配置和迁移状态。",
        ) from exc
    try:
        yield build_session_factory(engine)
    finally:
        engine.dispose()


@router.get("/local-series")
def today_market_local_series(
    boundaries: TodayMarketBoundaries = Depends(require_today_market_boundaries),
    session_factory: sessionmaker[Session] = Depends(get_today_market_session_factory),
) -> dict[str, Any]:
    try:
        with session_factory() as session:
            return _build_catalog(session, boundaries)
    except SQLAlchemyError as exc:
        raise _error(
            503,
            "today_market_database_query_failed",
            "本地数据列表读取失败，请检查数据库状态。",
        ) from exc


@router.get("/snapshot")
def today_market_snapshot(
    request: TodayMarketSnapshotRequest = Depends(require_today_market_snapshot_request),
    session_factory: sessionmaker[Session] = Depends(get_today_market_session_factory),
) -> dict[str, Any]:
    try:
        with session_factory() as session:
            snapshot = MarketCockpitService(
                _RecordedEquityRepository(session, request.boundaries.recorded_at),
                benchmark_repository=_RecordedBenchmarkRepository(
                    session, request.boundaries.recorded_at
                ),
                sector_repository=_RecordedSectorRepository(
                    session, request.boundaries.recorded_at
                ),
            ).build_snapshot(
                series_key=request.equity_series_key,
                benchmark_series_key=request.benchmark_series_key,
                sector_series_key=request.sector_series_key,
                as_of_cutoff=request.boundaries.cutoff_compact,
            )
        return _project_snapshot(snapshot.to_dict(), request)
    except (
        MarketCockpitSnapshotNotFound,
        BenchmarkSnapshotNotFound,
        SectorSnapshotNotFound,
    ) as exc:
        raise _error(
            404,
            "today_market_snapshot_not_visible",
            "所选数据在当前截止日和系统记录时间内不可见。",
        ) from exc
    except SnapshotSeriesError as exc:
        raise _error(
            409,
            "today_market_snapshot_identity_conflict",
            "所选本地数据身份发生冲突，请重新读取数据列表。",
        ) from exc
    except (
        MarketCockpitSelectionError,
        BenchmarkSelectionError,
        SectorSelectionError,
        MarketCockpitCalculationError,
        BenchmarkCalculationError,
        SectorCalculationError,
        ValueError,
    ) as exc:
        raise _error(
            422,
            "today_market_selection_incompatible",
            "所选本地数据无法在当前边界下组合，请调整明确选择。",
        ) from exc
    except SQLAlchemyError as exc:
        raise _error(
            503,
            "today_market_database_query_failed",
            "本地市场快照读取失败，请检查数据库状态。",
        ) from exc


class _RecordedEquityRepository(MarketCockpitRepository):
    def __init__(self, session: Session, recorded_at: datetime) -> None:
        super().__init__(session)
        self._recorded_at = recorded_at

    def load_snapshot(self, **kwargs: Any):
        return super().load_snapshot(
            **kwargs, as_of_recorded_at_utc=self._recorded_at
        )


class _RecordedBenchmarkRepository(BenchmarkRepository):
    def __init__(self, session: Session, recorded_at: datetime) -> None:
        super().__init__(session)
        self._recorded_at = recorded_at

    def load_snapshot(self, **kwargs: Any):
        return super().load_snapshot(
            **kwargs, as_of_recorded_at_utc=self._recorded_at
        )


class _RecordedSectorRepository(SectorRepository):
    def __init__(self, session: Session, recorded_at: datetime) -> None:
        super().__init__(session)
        self._recorded_at = recorded_at

    def load_snapshot(self, **kwargs: Any):
        return super().load_snapshot(
            **kwargs, as_of_recorded_at_utc=self._recorded_at
        )


def _build_catalog(
    session: Session, boundaries: TodayMarketBoundaries
) -> dict[str, Any]:
    runs = session.scalars(
        select(IngestionRun)
        .where(
            IngestionRun.dataset.in_(tuple(_FAMILY_BY_DATASET)),
            IngestionRun.status == "succeeded",
            IngestionRun.snapshot_mode == "complete",
            IngestionRun.information_cutoff_date <= boundaries.cutoff,
            IngestionRun.imported_at <= boundaries.recorded_at,
            IngestionRun.completed_at.is_not(None),
            IngestionRun.completed_at <= boundaries.recorded_at,
        )
        .order_by(
            IngestionRun.information_cutoff_date.desc(),
            IngestionRun.completed_at.desc(),
            IngestionRun.id.desc(),
        )
    ).all()
    families: dict[str, list[dict[str, Any]]] = {
        "equity": [],
        "benchmark": [],
        "sector": [],
    }
    seen: set[tuple[str, str]] = set()
    excluded = 0
    for run in runs:
        family = _FAMILY_BY_DATASET[run.dataset]
        identity = (family, run.series_key)
        if identity in seen:
            continue
        seen.add(identity)
        try:
            families[family].append(_catalog_option(run, family))
        except (SnapshotSeriesError, TypeError, ValueError, KeyError):
            excluded += 1
    for family, options in families.items():
        options.sort(key=lambda item: (item["label"], item["series_key"]))
        options.sort(key=lambda item: item["recorded_at_utc"], reverse=True)
        options.sort(key=lambda item: item["information_cutoff_date"], reverse=True)
        families[family] = options[:_CATALOG_LIMIT]
    total = sum(len(options) for options in families.values())
    return {
        "status": "ready" if total else "no_eligible_local_data",
        "message": (
            "请选择一个明确的本地股票数据范围。"
            if total
            else "当前时间边界内没有可用的本地市场数据。"
        ),
        "requested_boundaries": {
            "as_of_cutoff": boundaries.cutoff.isoformat(),
            "as_of_recorded_at_utc": boundaries.recorded_at_iso,
        },
        "families": families,
        "selected": {
            "equity_series_key": None,
            "benchmark_series_key": None,
            "sector_series_key": None,
        },
        "auto_selected": False,
        "warnings": (
            ["部分本地记录未通过精确身份校验，已从列表中排除。"]
            if excluded
            else []
        ),
        "read_only": True,
        "allowed_actions": ["select", "view"],
    }


def _catalog_option(run: IngestionRun, family: str) -> dict[str, Any]:
    if run.completed_at is None:
        raise ValueError("successful complete run has no completion timestamp")
    if family == "equity":
        canonical = validate_snapshot_series_identity(
            SnapshotSeriesIdentity(run.series_key, dict(run.series_identity))
        ).canonical
        codes = list(canonical["stock_codes"])
        adjust = {"": "不复权", "qfq": "前复权", "hfq": "后复权"}.get(
            canonical["adjust_type"], canonical["adjust_type"]
        )
        label = (
            f"股票范围 · {len(codes)}家公司 · "
            f"{_iso_date(canonical['requested_start_date'])} 至 "
            f"{_iso_date(canonical['requested_end_date'])} · {adjust} · "
            f"{canonical['provider']}"
        )
        summary = {"count": len(codes), "code_preview": codes[:5]}
    elif family == "benchmark":
        canonical = validate_benchmark_series_identity(
            BenchmarkSeriesIdentity(run.series_key, dict(run.series_identity))
        ).canonical
        codes = list(canonical["index_codes"])
        label = (
            f"基准指数 · {', '.join(codes[:4])} · "
            f"{_iso_date(canonical['requested_start_date'])} 至 "
            f"{_iso_date(canonical['requested_end_date'])} · "
            f"{canonical['provider']}"
        )
        summary = {"count": len(codes), "code_preview": codes[:5]}
    else:
        canonical = validate_sector_series_identity(
            SectorSeriesIdentity(run.series_key, dict(run.series_identity))
        ).canonical
        codes = list(canonical["sector_codes"])
        level = canonical.get("classification_level") or "未分级"
        label = (
            f"行业范围 · {canonical['classification_system']} / {level} · "
            f"{len(codes)}个行业 · "
            f"{_iso_date(canonical['requested_start_date'])} 至 "
            f"{_iso_date(canonical['requested_end_date'])} · "
            f"{canonical['provider']}"
        )
        summary = {"count": len(codes), "code_preview": codes[:5]}
    return {
        "family": family,
        "series_key": run.series_key,
        "label": label,
        "provider": run.provider,
        "information_cutoff_date": run.information_cutoff_date.isoformat(),
        "recorded_at_utc": _utc_iso(run.completed_at),
        "requested_start_date": _iso_date(canonical["requested_start_date"]),
        "requested_end_date": _iso_date(canonical["requested_end_date"]),
        "scope": summary,
    }


def _project_snapshot(
    raw: dict[str, Any], request: TodayMarketSnapshotRequest
) -> dict[str, Any]:
    provenance = raw["provenance"]
    state = _snapshot_state(raw)
    copy = {
        "complete_selected_scope": (
            "已读取明确选择的本地市场快照。",
            "结果可在当前双时间边界内复现，但不代表全市场覆盖。",
            "阅读价格行为、流动性以及可选的基准和行业背景。",
        ),
        "partial_selected_scope": (
            "已读取所选本地范围，但结果包含缺失或不一致状态。",
            "当前结果只描述明确选择的本地范围，并且需要保留全部警告。",
            "先查看范围、新鲜度和对齐警告，再阅读具体指标。",
        ),
        "insufficient_data": (
            "所选范围的数据不足，部分确定性指标无法计算。",
            "数据不足会限制结果含义，不能把缺失值解释为市场判断。",
            "查看数据完整性，或明确选择其他本地数据。",
        ),
    }[state]
    benchmark = raw.get("benchmark_context")
    sector = raw.get("sector_context")
    return {
        "status": state,
        "state_explanation": {
            "what_happened": copy[0],
            "why_it_matters": copy[1],
            "available_action": copy[2],
        },
        "requested_boundaries": {
            "as_of_cutoff": request.boundaries.cutoff.isoformat(),
            "as_of_recorded_at_utc": request.boundaries.recorded_at_iso,
        },
        "scope_and_freshness": {
            "local_only": True,
            "coverage_label": "明确选择的本地股票范围",
            "coverage_notice": "不是全市场覆盖",
            "benchmark_selected": request.benchmark_series_key is not None,
            "sector_selected": request.sector_series_key is not None,
            "universe_stock_count": raw["universe_stock_count"],
            "available_stock_count": raw["available_stock_count"],
            "requested_information_cutoff": request.boundaries.cutoff.isoformat(),
            "source_information_cutoff": _iso_date(
                provenance["information_cutoff_date"]
            ),
            "requested_recorded_at_utc": request.boundaries.recorded_at_iso,
            "ingestion_imported_at_utc": provenance["ingestion_imported_at_utc"],
            "ingestion_completed_at_utc": provenance["ingestion_completed_at_utc"],
            "effective_equity_session": _iso_date(
                provenance["effective_as_of_session"]
            ),
            "scope_coverage_status": raw["scope_coverage_status"],
            "calculation_status": raw["calculation_status"],
            "completeness_status": raw["completeness_status"],
            "warnings": list(raw["warnings"]),
        },
        "supported_analysis": {
            "price_behavior": raw["price_behavior_context"],
            "liquidity": raw["liquidity_context"],
            "data_completeness": {
                "status": raw["completeness_status"],
                "latest_data_diagnostics": raw["latest_data_diagnostics"],
            },
            "benchmark": (
                benchmark
                if benchmark is not None
                else {"status": "not_selected", "message": "未选择本地基准数据。"}
            ),
            "sector": (
                sector
                if sector is not None
                else {"status": "not_selected", "message": "未选择本地行业数据。"}
            ),
        },
        "unavailable_sections": _unavailable_sections(),
        "technical_details": {
            "collapsed_by_default": True,
            "exact_equity_series_key": request.equity_series_key,
            "exact_benchmark_series_key": request.benchmark_series_key,
            "exact_sector_series_key": request.sector_series_key,
            "raw_market_cockpit_snapshot": raw,
        },
        "read_only": True,
        "allowed_actions": ["view", "inspect", "reread_same_local_snapshot"],
        "disclaimer": raw["disclaimer"],
    }


def _snapshot_state(raw: dict[str, Any]) -> str:
    if raw["calculation_status"] == "insufficient_data":
        return "insufficient_data"
    if (
        raw["calculation_status"] == "partial"
        or raw["completeness_status"] == "partial"
        or raw["available_stock_count"] != raw["universe_stock_count"]
    ):
        return "partial_selected_scope"
    for context in (raw.get("benchmark_context"), raw.get("sector_context")):
        if context is not None and context.get("alignment_status") != "aligned":
            return "partial_selected_scope"
    return "complete_selected_scope"


def _unavailable_sections() -> list[dict[str, str]]:
    return [
        {
            "key": "full_market_breadth",
            "label": "全市场宽度与涨跌停",
            "status": "unsupported",
            "message": "当前本地契约不能证明全市场成员范围，因此不展示推测值。",
        },
        {
            "key": "stock_anomalies",
            "label": "个股异动",
            "status": "unsupported",
            "message": "当前阶段没有经过审核的异动定义和完整比较范围。",
        },
        {
            "key": "events_and_causes",
            "label": "新闻、公告与涨跌原因",
            "status": "unsupported",
            "message": "当前页面不读取新闻，也不根据价格变化推断原因。",
        },
        {
            "key": "attention_and_fund_flow",
            "label": "市场关注度与资金流",
            "status": "unsupported",
            "message": "尚无已授权的本地数据契约。",
        },
        {
            "key": "live_intraday",
            "label": "实时与盘中数据",
            "status": "unsupported",
            "message": "当前页面只读取已持久化的本地日频快照。",
        },
        {
            "key": "remote_refresh",
            "label": "远程刷新",
            "status": "unsupported",
            "message": "重新读取只会在相同选择和时间边界下读取本地数据库。",
        },
    ]


def _iso_date(value: str | date) -> str:
    if isinstance(value, date):
        return value.isoformat()
    normalized = str(value).strip().replace("-", "")
    return datetime.strptime(normalized, "%Y%m%d").date().isoformat()


def _utc_iso(value: datetime) -> str:
    parsed = value
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_prior_snapshot_context(
    request: TodayMarketSnapshotRequest,
    session_factory: sessionmaker[Session],
) -> TodayMarketPriorSnapshotContext:
    projected = today_market_snapshot(
        request=request,
        session_factory=session_factory,
    )
    raw = projected["technical_details"]["raw_market_cockpit_snapshot"]
    components: list[dict[str, Any] | None] = []
    with session_factory() as session:
        for family, series_key in (
            ("equity", request.equity_series_key),
            ("benchmark", request.benchmark_series_key),
            ("sector", request.sector_series_key),
        ):
            components.append(
                None
                if series_key is None
                else _authoritative_component(
                    session,
                    family=family,
                    series_key=series_key,
                    boundaries=request.boundaries,
                )
            )
    equity_component = components[0]
    if equity_component is None:
        raise RuntimeError("equity component is required")
    components[0] = _bind_component_to_service(
        equity_component,
        raw.get("provenance"),
        effective_session_key="effective_as_of_session",
    )
    benchmark_component = components[1]
    benchmark_context = raw.get("benchmark_context")
    if benchmark_component is not None:
        components[1] = _bind_component_to_service(
            benchmark_component,
            (
                benchmark_context.get("provenance")
                if isinstance(benchmark_context, Mapping)
                else None
            ),
            effective_session_key="effective_benchmark_session",
        )
    sector_component = components[2]
    sector_context = raw.get("sector_context")
    if sector_component is not None:
        components[2] = _bind_component_to_service(
            sector_component,
            (
                sector_context.get("provenance")
                if isinstance(sector_context, Mapping)
                else None
            ),
            effective_session_key="effective_sector_session",
        )

    identity_payload = {
        "snapshot_identity_version": SNAPSHOT_IDENTITY_VERSION,
        "as_of_cutoff": request.boundaries.cutoff.isoformat(),
        "as_of_recorded_at_utc": request.boundaries.recorded_at_iso,
        "selected_components": components,
        "market_snapshot_contract_version": raw.get(
            "snapshot_contract_version",
            raw.get("contract_version", "market-cockpit-domain-snapshot"),
        ),
    }
    content_payload = {
        "snapshot_content_version": SNAPSHOT_CONTENT_VERSION,
        "identity_payload": identity_payload,
        "market_cockpit_domain_snapshot": (
            _canonical_market_cockpit_domain_snapshot(raw)
        ),
    }
    effective_session = date.fromisoformat(
        projected["scope_and_freshness"]["effective_equity_session"]
    )
    return TodayMarketPriorSnapshotContext(
        snapshot_reference=SnapshotReference(
            snapshot_id=(
                "today-market-local-v1:" + canonical_sha256(identity_payload)
            ),
            data_through_session=effective_session,
            content_fingerprint=canonical_sha256(content_payload),
        ),
        identity_payload=identity_payload,
        content_payload=content_payload,
        projected_snapshot=projected,
    )


@router.get("/runtime-status")
def today_market_runtime_status(
    http_request: Request,
    snapshot_request: TodayMarketSnapshotRequest = Depends(
        require_today_market_snapshot_request
    ),
    session_factory: sessionmaker[Session] = Depends(
        get_today_market_session_factory
    ),
) -> dict[str, Any]:
    try:
        prior = build_prior_snapshot_context(snapshot_request, session_factory)
        configuration, _, coordinator = _app_runtime_dependencies(http_request)
        scope = build_runtime_scope(
            request=snapshot_request,
            prior=prior,
            configuration=configuration,
        )
        return coordinator.get_status(scope, configuration)
    except RuntimeScopeConflict as exc:
        raise _error(
            409,
            "runtime_scope_identity_conflict",
            "本地快照身份与权威读取结果不一致，请重新读取。",
        ) from exc


@router.post("/runtime-refresh")
def today_market_runtime_refresh(
    http_request: Request,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    command = _validate_command(payload)
    snapshot_request = _snapshot_request_from_command(command)
    try:
        engine = build_engine()
    except RuntimeError as exc:
        raise _error(
            503,
            "runtime_database_unavailable",
            "本地数据库不可用，模拟更新未执行。",
        ) from exc
    try:
        session_factory = build_session_factory(engine)
        prior = build_prior_snapshot_context(snapshot_request, session_factory)
        configuration, fixture_root, coordinator = _app_runtime_dependencies(
            http_request
        )
        scope = build_runtime_scope(
            request=snapshot_request,
            prior=prior,
            configuration=configuration,
        )
        _compare_command_scope(command, scope, prior)
        try:
            trigger = RefreshTrigger(str(command["trigger"]))
        except ValueError as exc:
            raise _error(
                422,
                "runtime_trigger_not_allowed",
                "当前触发方式未获授权。",
            ) from exc
        try:
            return coordinator.execute(
                scope=scope,
                configuration=configuration,
                expected_runtime_status_fingerprint=str(
                    command["expected_runtime_status_fingerprint"]
                ),
                trigger=trigger,
                fixture_root=fixture_root,
            )
        except RuntimeStatusConflict as exc:
            current = coordinator.get_status(scope, configuration)
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "runtime_status_conflict",
                    "message": "运行状态已变化，请使用最新状态重试。",
                    "current_status": current,
                },
            ) from exc
        except RuntimeScopeConflict as exc:
            raise _error(
                409,
                "runtime_mock_not_enabled",
                "当前应用未启用模拟更新。",
            ) from exc
        except ValueError as exc:
            raise _error(
                422,
                "runtime_trigger_not_allowed",
                "当前状态不允许此操作。",
            ) from exc
    except RuntimeScopeConflict as exc:
        raise _error(
            409,
            "runtime_scope_identity_conflict",
            "本地快照身份与权威读取结果不一致，请重新读取。",
        ) from exc
    except SQLAlchemyError as exc:
        raise _error(
            503,
            "runtime_database_unavailable",
            "本地数据库读取失败，模拟更新未执行。",
        ) from exc
    except RuntimeError as exc:
        raise _error(
            500,
            "runtime_internal_validation_failed",
            "模拟更新内部校验失败，先前本地快照保持不变。",
        ) from exc
    finally:
        engine.dispose()


def _canonical_market_cockpit_domain_snapshot(
    raw: Mapping[str, Any],
) -> dict[str, Any]:
    """Exclude request-time clocks without mutating the projected snapshot."""

    domain = {key: raw.get(key) for key in _DOMAIN_SNAPSHOT_KEYS}
    domain["provenance"] = _canonical_domain_provenance(
        domain.get("provenance")
    )
    domain["benchmark_context"] = _canonical_domain_context(
        domain.get("benchmark_context")
    )
    domain["sector_context"] = _canonical_domain_context(
        domain.get("sector_context")
    )
    return domain


def _canonical_domain_context(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    context = dict(value)
    context["provenance"] = _canonical_domain_provenance(
        context.get("provenance")
    )
    return context


def _canonical_domain_provenance(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    return {
        key: item
        for key, item in value.items()
        if key != "generated_at_utc"
    }


def _authoritative_component(
    session: Session,
    *,
    family: str,
    series_key: str,
    boundaries: TodayMarketBoundaries,
) -> dict[str, Any]:
    dataset = _DATASET_BY_RUNTIME_FAMILY[family]
    run = session.scalar(
        select(IngestionRun)
        .where(
            IngestionRun.dataset == dataset,
            IngestionRun.series_key == series_key,
            IngestionRun.status == "succeeded",
            IngestionRun.snapshot_mode == "complete",
            IngestionRun.information_cutoff_date <= boundaries.cutoff,
            IngestionRun.imported_at <= boundaries.recorded_at,
            IngestionRun.completed_at.is_not(None),
            IngestionRun.completed_at <= boundaries.recorded_at,
        )
        .order_by(
            IngestionRun.information_cutoff_date.desc(),
            IngestionRun.completed_at.desc(),
            IngestionRun.id.desc(),
        )
        .limit(1)
    )
    if run is None or run.completed_at is None:
        raise RuntimeScopeConflict("authoritative ingestion run is unavailable")
    raw_identity = dict(run.series_identity)
    if family == "equity":
        canonical_identity = dict(
            validate_snapshot_series_identity(
                SnapshotSeriesIdentity(run.series_key, raw_identity)
            ).canonical
        )
    elif family == "benchmark":
        canonical_identity = dict(
            validate_benchmark_series_identity(
                BenchmarkSeriesIdentity(run.series_key, raw_identity)
            ).canonical
        )
    elif family == "sector":
        canonical_identity = dict(
            validate_sector_series_identity(
                SectorSeriesIdentity(run.series_key, raw_identity)
            ).canonical
        )
    else:
        raise RuntimeScopeConflict("unsupported authoritative snapshot family")
    return {
        "family_key": family,
        "ingestion_run_id": run.id,
        "dataset": run.dataset,
        "provider": run.provider,
        "series_key": run.series_key,
        "information_cutoff_date": run.information_cutoff_date.isoformat(),
        "imported_at_utc": _utc_iso(run.imported_at),
        "completed_at_utc": _utc_iso(run.completed_at),
        "snapshot_mode": run.snapshot_mode,
        "effective_session": None,
        "canonical_series_identity": canonical_identity,
    }


def _bind_component_to_service(
    component: dict[str, Any],
    provenance: Mapping[str, Any] | None,
    *,
    effective_session_key: str,
) -> dict[str, Any]:
    if not isinstance(provenance, Mapping):
        raise RuntimeScopeConflict("service provenance is unavailable")
    expected = {
        "ingestion_run_id": component["ingestion_run_id"],
        "provider": component["provider"],
        "series_key": component["series_key"],
    }
    for field, value in expected.items():
        if provenance.get(field) != value:
            raise RuntimeScopeConflict(
                f"service/repository {field} disagreement"
            )
    effective_session = provenance.get(effective_session_key)
    if effective_session is None:
        raise RuntimeScopeConflict("service effective session is unavailable")
    return {**component, "effective_session": str(effective_session)}


def _validate_command(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise _error(
            422,
            "runtime_request_unknown_field",
            "运行请求必须是封闭的 JSON 对象。",
        )
    unknown = sorted(set(payload) - _ALLOWED_RUNTIME_COMMAND_FIELDS)
    missing = sorted(_ALLOWED_RUNTIME_COMMAND_FIELDS - set(payload))
    if unknown:
        raise _error(
            422,
            "runtime_request_unknown_field",
            f"运行请求包含未授权字段：{', '.join(unknown)}。",
        )
    if missing:
        raise _error(
            422,
            "runtime_request_missing_field",
            f"运行请求缺少字段：{', '.join(missing)}。",
        )
    return payload


def _snapshot_request_from_command(
    command: Mapping[str, Any],
) -> TodayMarketSnapshotRequest:
    try:
        cutoff = date.fromisoformat(str(command["as_of_cutoff"]))
        recorded = _parse_utc(str(command["as_of_recorded_at_utc"]))
        equity = validate_series_key(str(command["equity_series_key"]))
        benchmark_raw = command["benchmark_series_key"]
        sector_raw = command["sector_series_key"]
        benchmark = (
            None
            if benchmark_raw is None
            else validate_series_key(str(benchmark_raw))
        )
        sector = (
            None if sector_raw is None else validate_series_key(str(sector_raw))
        )
    except (ValueError, TypeError, SnapshotSeriesError) as exc:
        raise _error(
            422,
            "runtime_scope_stale",
            "运行请求中的边界或数据选择无效。",
        ) from exc
    return TodayMarketSnapshotRequest(
        equity_series_key=equity,
        benchmark_series_key=benchmark,
        sector_series_key=sector,
        boundaries=TodayMarketBoundaries(
            cutoff=cutoff,
            cutoff_compact=cutoff.strftime("%Y%m%d"),
            recorded_at=recorded,
            recorded_at_iso=_utc_iso(recorded),
        ),
    )


def _compare_command_scope(
    command: Mapping[str, Any],
    scope: TodayMarketRuntimeScopeV1,
    prior: TodayMarketPriorSnapshotContext,
) -> None:
    if str(command["runtime_scope_version"]) != RUNTIME_SCOPE_VERSION:
        raise _error(
            409,
            "runtime_scope_stale",
            "运行范围版本已变化，请重新读取状态。",
        )
    if str(command["prior_snapshot_id"]) != prior.snapshot_reference.snapshot_id:
        raise _error(
            409,
            "runtime_prior_snapshot_moved",
            "先前本地快照已变化，请重新读取。",
        )
    if (
        str(command["prior_snapshot_content_fingerprint"])
        != prior.snapshot_reference.content_fingerprint
    ):
        raise _error(
            409,
            "runtime_prior_snapshot_moved",
            "先前本地快照内容已变化，请重新读取。",
        )
    if (
        str(command["runtime_scope_revision_id"])
        != scope.runtime_scope_revision_id
    ):
        raise _error(
            409,
            "runtime_scope_stale",
            "运行范围已变化，请重新读取状态。",
        )


def _app_runtime_dependencies(
    request: Request,
) -> tuple[
    TodayMarketMockRuntimeConfigurationV1,
    Path | None,
    TodayMarketRuntimeCoordinator,
]:
    configuration = getattr(
        request.app.state,
        "today_market_runtime_configuration",
        TodayMarketMockRuntimeConfigurationV1(),
    )
    fixture_root = getattr(
        request.app.state,
        "today_market_runtime_fixture_root",
        None,
    )
    coordinator = getattr(
        request.app.state,
        "today_market_runtime_coordinator",
        None,
    )
    if coordinator is None:
        coordinator = TodayMarketRuntimeCoordinator()
        request.app.state.today_market_runtime_coordinator = coordinator
    return configuration, fixture_root, coordinator




def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)
