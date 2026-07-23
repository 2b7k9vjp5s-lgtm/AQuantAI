"""Local-only Today Market API for the Personal Research Workbench."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from backend.database.benchmark_data import BENCHMARK_DATASET
from backend.database.models import IngestionRun
from backend.database.sector_data import SECTOR_DATASET
from backend.database.series import (
    BENCHMARK_SERIES_SCHEMA,
    SECTOR_SERIES_SCHEMA,
    SERIES_SCHEMA,
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

router = APIRouter(prefix="/today-market/api", tags=["today-market"])
_CATALOG_LIMIT = 20
_ALLOWED_DATASETS = {MARKET_DATASET, BENCHMARK_DATASET, SECTOR_DATASET}


class TodayMarketIdentityConflict(ValueError):
    """Raised when an exact persisted identity conflicts with its dataset family."""


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


class _RecordedMarketCockpitRepository:
    def __init__(self, repository: MarketCockpitRepository, recorded_at: datetime) -> None:
        self._repository = repository
        self._recorded_at = recorded_at

    def load_snapshot(self, **kwargs: Any):
        return self._repository.load_snapshot(
            **kwargs,
            as_of_recorded_at_utc=self._recorded_at,
        )


class _RecordedBenchmarkRepository:
    def __init__(self, repository: BenchmarkRepository, recorded_at: datetime) -> None:
        self._repository = repository
        self._recorded_at = recorded_at

    def load_snapshot(self, **kwargs: Any):
        return self._repository.load_snapshot(
            **kwargs,
            as_of_recorded_at_utc=self._recorded_at,
        )


class _RecordedSectorRepository:
    def __init__(self, repository: SectorRepository, recorded_at: datetime) -> None:
        self._repository = repository
        self._recorded_at = recorded_at

    def load_snapshot(self, **kwargs: Any):
        return self._repository.load_snapshot(
            **kwargs,
            as_of_recorded_at_utc=self._recorded_at,
        )


def require_today_market_boundaries(
    as_of_cutoff: str | None = Query(default=None),
    as_of_recorded_at_utc: str | None = Query(default=None),
) -> TodayMarketBoundaries:
    """Validate both reproducibility boundaries before opening the database."""
    if as_of_cutoff is None:
        raise _http_error(
            422,
            "today_market_cutoff_required",
            "请选择信息截止日。",
        )
    if as_of_recorded_at_utc is None:
        raise _http_error(
            422,
            "today_market_recorded_at_required",
            "请选择系统记录时间。",
        )
    try:
        cutoff = datetime.strptime(
            str(as_of_cutoff).strip().replace("-", ""), "%Y%m%d"
        ).date()
    except ValueError as exc:
        raise _http_error(
            422,
            "today_market_cutoff_invalid",
            "信息截止日必须使用 YYYY-MM-DD 格式。",
        ) from exc
    try:
        recorded_at = datetime.fromisoformat(
            str(as_of_recorded_at_utc).strip().replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise _http_error(
            422,
            "today_market_recorded_at_invalid",
            "系统记录时间必须使用带时区的 ISO-8601 格式。",
        ) from exc
    if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
        raise _http_error(
            422,
            "today_market_recorded_at_timezone_required",
            "系统记录时间必须包含明确时区。",
        )
    recorded_utc = recorded_at.astimezone(timezone.utc)
    return TodayMarketBoundaries(
        cutoff=cutoff,
        cutoff_compact=cutoff.strftime("%Y%m%d"),
        recorded_at=recorded_utc,
        recorded_at_iso=_utc_iso(recorded_utc),
    )


def require_today_market_snapshot_request(
    equity_series_key: str | None = Query(default=None),
    benchmark_series_key: str | None = Query(default=None),
    sector_series_key: str | None = Query(default=None),
    boundaries: TodayMarketBoundaries = Depends(require_today_market_boundaries),
) -> TodayMarketSnapshotRequest:
    if equity_series_key is None:
        raise _http_error(
            422,
            "today_market_equity_selection_required",
            "请先选择一个本地股票数据范围。",
        )
    try:
        equity_key = validate_series_key(equity_series_key)
        benchmark_key = (
            validate_series_key(benchmark_series_key)
            if benchmark_series_key is not None
            else None
        )
        sector_key = (
            validate_series_key(sector_series_key)
            if sector_series_key is not None
            else None
        )
    except SnapshotSeriesError as exc:
        raise _http_error(
            422,
            "today_market_series_key_invalid",
            "所选本地数据标识无效，请重新读取本地数据列表。",
            technical_message=str(exc),
        ) from exc
    return TodayMarketSnapshotRequest(
        equity_series_key=equity_key,
        benchmark_series_key=benchmark_key,
        sector_series_key=sector_key,
        boundaries=boundaries,
    )


def get_today_market_session_factory(
    _boundaries: TodayMarketBoundaries = Depends(require_today_market_boundaries),
) -> sessionmaker[Session]:
    """Construct local database resources only after request validation succeeds."""
    try:
        engine = build_engine()
    except RuntimeError as exc:
        raise _http_error(
            503,
            "today_market_database_unavailable",
            "本地数据库不可用，请检查数据库配置和迁移状态。",
        ) from exc
    return build_session_factory(engine)


@router.get("/local-series")
def today_market_local_series(
    boundaries: TodayMarketBoundaries = Depends(require_today_market_boundaries),
    session_factory: sessionmaker[Session] = Depends(get_today_market_session_factory),
) -> dict[str, Any]:
    try:
        with session_factory() as session:
            catalog = _build_catalog(session, boundaries)
        return catalog
    except SnapshotSeriesError as exc:
        raise _http_error(
            409,
            "today_market_catalog_identity_conflict",
            "本地数据身份校验失败，未展示不可信的选项。",
            technical_message=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        raise _http_error(
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
                _RecordedMarketCockpitRepository(
                    MarketCockpitRepository(session), request.boundaries.recorded_at
                ),
                benchmark_repository=_RecordedBenchmarkRepository(
                    BenchmarkRepository(session), request.boundaries.recorded_at
                ),
                sector_repository=_RecordedSectorRepository(
                    SectorRepository(session), request.boundaries.recorded_at
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
        raise _http_error(
            404,
            "today_market_snapshot_not_visible",
            "所选数据在当前截止日和系统记录时间内不可见。",
            technical_message=str(exc),
        ) from exc
    except SnapshotSeriesError as exc:
        raise _http_error(
            409,
            "today_market_snapshot_identity_conflict",
            "所选本地数据身份发生冲突，请重新读取数据列表。",
            technical_message=str(exc),
        ) from exc
    except (
        TodayMarketIdentityConflict,
        MarketCockpitSelectionError,
        BenchmarkSelectionError,
        SectorSelectionError,
        MarketCockpitCalculationError,
        BenchmarkCalculationError,
        SectorCalculationError,
        ValueError,
    ) as exc:
        raise _http_error(
            422,
            "today_market_selection_incompatible",
            "所选本地数据无法在当前边界下组合，请调整明确选择。",
            technical_message=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        raise _http_error(
            503,
            "today_market_database_query_failed",
            "本地市场快照读取失败，请检查数据库状态。",
        ) from exc


def _build_catalog(
    session: Session,
    boundaries: TodayMarketBoundaries,
) -> dict[str, Any]:
    rows = session.scalars(
        select(IngestionRun)
        .where(
            IngestionRun.dataset.in_(_ALLOWED_DATASETS),
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
    for run in rows:
        family = _dataset_family(run.dataset)
        dedupe = (family, run.series_key)
        if dedupe in seen:
            continue
        seen.add(dedupe)
        try:
            option = _catalog_option(run, family)
        except SnapshotSeriesError:
            continue
        families[family].append(option)
    for family, values in families.items():
        values.sort(key=lambda item: item["series_key"])
        values.sort(key=lambda item: item["label"])
        values.sort(key=lambda item: item["recorded_at_utc"], reverse=True)
        values.sort(key=lambda item: item["information_cutoff_date"], reverse=True)
        families[family] = values[:_CATALOG_LIMIT]
    total = sum(len(values) for values in families.values())
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
        "read_only": True,
        "allowed_actions": ["select", "view"],
    }


def _dataset_family(dataset: str) -> str:
    if dataset == MARKET_DATASET:
        return "equity"
    if dataset == BENCHMARK_DATASET:
        return "benchmark"
    if dataset == SECTOR_DATASET:
        return "sector"
    raise TodayMarketIdentityConflict(f"Unsupported Today Market dataset: {dataset}")


def _catalog_option(run: IngestionRun, family: str) -> dict[str, Any]:
    canonical = dict(run.series_identity or {})
    if family == "equity":
        identity = validate_snapshot_series_identity(
            SnapshotSeriesIdentity(run.series_key, canonical)
        ).canonical
        if identity.get("series_schema") != SERIES_SCHEMA:
            raise SnapshotSeriesError("equity catalog identity uses the wrong schema")
        codes = list(identity["stock_codes"])
        label = (
            f"股票范围 · {len(codes)}家公司 · "
            f"{_iso_date(identity['requested_start_date'])} 至 "
            f"{_iso_date(identity['requested_end_date'])} · "
            f"{_adjust_label(identity['adjust_type'])} · {identity['provider']}"
        )
        scope = {
            "count": len(codes),
            "code_preview": codes[:5],
            "adjust_type": identity["adjust_type"],
        }
    elif family == "benchmark":
        identity = validate_benchmark_series_identity(
            BenchmarkSeriesIdentity(run.series_key, canonical)
        ).canonical
        if identity.get("series_schema") != BENCHMARK_SERIES_SCHEMA:
            raise SnapshotSeriesError("benchmark catalog identity uses the wrong schema")
        codes = list(identity["index_codes"])
        label = (
            f"基准指数 · {', '.join(codes[:4])} · "
            f"{_iso_date(identity['requested_start_date'])} 至 "
            f"{_iso_date(identity['requested_end_date'])} · {identity['provider']}"
        )
        scope = {"count": len(codes), "code_preview": codes[:5]}
    else:
        identity = validate_sector_series_identity(
            SectorSeriesIdentity(run.series_key, canonical)
        ).canonical
        if identity.get("series_schema") != SECTOR_SERIES_SCHEMA:
            raise SnapshotSeriesError("sector catalog identity uses the wrong schema")
        codes = list(identity["sector_codes"])
        level = identity.get("classification_level") or "未分级"
        label = (
            f"行业范围 · {identity['classification_system']} / {level} · "
            f"{len(codes)}个行业 · "
            f"{_iso_date(identity['requested_start_date'])} 至 "
            f"{_iso_date(identity['requested_end_date'])} · {identity['provider']}"
        )
        scope = {
            "count": len(codes),
            "code_preview": codes[:5],
            "classification_system": identity["classification_system"],
            "classification_level": identity.get("classification_level"),
        }
    return {
        "family": family,
        "series_key": run.series_key,
        "label": label,
        "provider": run.provider,
        "information_cutoff_date": run.information_cutoff_date.isoformat(),
        "recorded_at_utc": _utc_iso(run.completed_at),
        "requested_start_date": _iso_date(identity["requested_start_date"]),
        "requested_end_date": _iso_date(identity["requested_end_date"]),
        "scope": scope,
    }


def _project_snapshot(
    raw: dict[str, Any],
    request: TodayMarketSnapshotRequest,
) -> dict[str, Any]:
    provenance = dict(raw["provenance"])
    calculation_status = str(raw["calculation_status"])
    completeness_status = str(raw["completeness_status"])
    if calculation_status == "insufficient_data":
        status = "insufficient_data"
        message = "所选范围的数据不足，部分确定性指标无法计算。"
        why = "数据不足会限制结果含义，不能把缺失值解释为市场判断。"
        action = "查看数据完整性和技术来源，或明确选择其他本地数据。"
    elif completeness_status == "partial" or calculation_status == "partial":
        status = "partial_selected_scope"
        message = "已读取所选本地范围，但结果包含缺失或不一致状态。"
        why = "当前结果只描述明确选择的本地范围，并且需要保留全部警告。"
        action = "先查看范围、新鲜度和对齐警告，再阅读具体指标。"
    else:
        status = "complete_selected_scope"
        message = "已读取明确选择的本地市场快照。"
        why = "结果可在当前双时间边界内复现，但不代表全市场覆盖。"
        action = "阅读价格行为、流动性以及可选的基准和行业背景。"
    benchmark_context = raw.get("benchmark_context")
    sector_context = raw.get("sector_context")
    return {
        "status": status,
        "state_explanation": {
            "what_happened": message,
            "why_it_matters": why,
            "available_action": action,
        },
        "requested_boundaries": {
            "as_of_cutoff": request.boundaries.cutoff.isoformat(),
            "as_of_recorded_at_utc": request.boundaries.recorded_at_iso,
        },
        "scope_and_freshness": {
            "local_only": True,
            "coverage_label": "明确选择的本地股票范围",
            "coverage_notice": "不是全市场覆盖",
            "equity_series_key": request.equity_series_key,
            "benchmark_selected": request.benchmark_series_key is not None,
            "sector_selected": request.sector_series_key is not None,
            "universe_stock_count": raw["universe_stock_count"],
            "available_stock_count": raw["available_stock_count"],
            "requested_information_cutoff": request.boundaries.cutoff.isoformat(),
            "source_information_cutoff": _iso_date(provenance["information_cutoff_date"]),
            "requested_recorded_at_utc": request.boundaries.recorded_at_iso,
            "ingestion_imported_at_utc": provenance["ingestion_imported_at_utc"],
            "ingestion_completed_at_utc": provenance["ingestion_completed_at_utc"],
            "effective_equity_session": _iso_date(provenance["effective_as_of_session"]),
            "scope_coverage_status": raw["scope_coverage_status"],
            "calculation_status": calculation_status,
            "completeness_status": completeness_status,
            "warnings": list(raw["warnings"]),
        },
        "supported_analysis": {
            "price_behavior": raw["price_behavior_context"],
            "liquidity": raw["liquidity_context"],
            "data_completeness": {
                "status": completeness_status,
                "latest_data_diagnostics": raw["latest_data_diagnostics"],
            },
            "benchmark": (
                benchmark_context
                if benchmark_context is not None
                else {
                    "status": "not_selected",
                    "message": "未选择本地基准数据。",
                }
            ),
            "sector": (
                sector_context
                if sector_context is not None
                else {
                    "status": "not_selected",
                    "message": "未选择本地行业数据。",
                }
            ),
        },
        "unavailable_sections": _unavailable_sections(),
        "technical_details": {
            "collapsed_by_default": True,
            "exact_equity_series_key": request.equity_series_key,
            "exact_benchmark_series_key": request.benchmark_series_key,
            "exact_sector_series_key": request.sector_series_key,
            "equity_ingestion_run_id": provenance["ingestion_run_id"],
            "provider": provenance["provider"],
            "contract_version": provenance["contract_version"],
            "adapter_version": provenance["adapter_version"],
            "raw_market_cockpit_snapshot": raw,
        },
        "read_only": True,
        "allowed_actions": ["view", "inspect", "reread_same_local_snapshot"],
        "disclaimer": raw["disclaimer"],
    }


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


def _http_error(
    status: int,
    code: str,
    message: str,
    *,
    technical_message: str | None = None,
) -> HTTPException:
    detail: dict[str, str] = {"code": code, "message": message}
    if technical_message is not None:
        detail["technical_message"] = technical_message
    return HTTPException(status_code=status, detail=detail)


def _adjust_label(value: str) -> str:
    return {"": "不复权", "qfq": "前复权", "hfq": "后复权"}.get(value, value)


def _iso_date(value: str | date) -> str:
    if isinstance(value, date):
        return value.isoformat()
    normalized = str(value).strip().replace("-", "")
    return datetime.strptime(normalized, "%Y%m%d").date().isoformat()


def _utc_iso(value: datetime | None) -> str:
    if value is None:
        return ""
    parsed = value
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
