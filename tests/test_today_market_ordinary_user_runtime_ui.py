from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

from backend.main import app as default_app
from backend.today_market_refresh.read_model import (
    READ_MODEL_VERSION,
    TodayMarketRuleProjectionInputs,
    build_today_market_read_model,
)
from market_cockpit.today_market_rule_contracts import (
    MarketOverviewInput,
    SectorRuleInput,
    StockRuleInput,
)

ROOT = Path(__file__).parents[1]


def _projected_snapshot() -> dict:
    return {
        "status": "complete_selected_scope",
        "scope_and_freshness": {
            "coverage_label": "明确选择的本地股票范围",
            "scope_coverage_status": "unverified_selected_scope",
            "universe_stock_count": 10,
            "available_stock_count": 10,
            "completeness_status": "ready",
            "warnings": [],
        },
        "supported_analysis": {
            "benchmark": {
                "status": "ready",
                "metrics": [
                    {
                        "index_code": "SYNTHETIC-BROAD",
                        "latest_close": 1234.0,
                        "latest_return": 0.01,
                        "above_sma20": True,
                        "realized_volatility_20": 0.15,
                    }
                ],
            },
            "sector": {
                "status": "ready",
                "requested_sector_count": 10,
            },
            "data_completeness": {
                "status": "ready",
                "latest_data_diagnostics": {
                    "stale_or_missing_latest_count": 0,
                    "no_trade_latest_count": 0,
                    "latest_return_unavailable_count": 0,
                },
            },
        },
        "technical_details": {
            "raw_market_cockpit_snapshot": {
                "provenance": {"provider": "synthetic-test"},
                "metrics": {
                    "latest_session": {
                        "advancing_count": 8,
                        "declining_count": 2,
                        "unchanged_count": 0,
                        "advance_ratio": 0.8,
                        "breadth_balance": 0.6,
                        "median_return": 0.02,
                    },
                    "amount_participation": {
                        "ratio_to_prior_20_session_median": 1.5,
                    },
                },
            }
        },
    }


def _runtime_status(*, enabled: bool = False, phase: str | None = None) -> dict:
    resolved_phase = phase or ("prior_snapshot_ready" if enabled else "mock_not_enabled")
    return {
        "phase": resolved_phase,
        "mock_enabled": enabled,
        "source_mode": "synthetic_mock" if enabled else "none",
        "is_synthetic": False,
        "runtime_scope_revision_id": "scope-1",
        "runtime_status_fingerprint": "status-1",
        "allowed_actions": ["automatic_first_entry"] if enabled else [],
    }


def _market_input() -> MarketOverviewInput:
    return MarketOverviewInput(
        expected_active_count=10,
        accounted_count=10,
        identity_conflict_count=0,
        calendar_conflict=False,
        valid_returns=(0.03, 0.02, 0.02, 0.01, 0.01, 0.01, 0.005, 0.004, -0.01, -0.02),
        above_ma20_flags=(True, True, True, True, True, True, False, False, False, False),
        new_high_20_flags=(True, False, False, False, False, False, False, False, False, False),
        new_low_20_flags=(False,) * 10,
        market_amount_current=150.0,
        market_amount_previous_20=(100.0,) * 20,
    )


def _sector_inputs(*, membership: bool = True) -> tuple[SectorRuleInput, ...]:
    values: list[SectorRuleInput] = []
    for index in range(10):
        target = index == 0
        values.append(
            SectorRuleInput(
                sector_code=f"S{index:02d}",
                sector_name=f"合成行业 {index:02d}",
                taxonomy="synthetic-taxonomy",
                classification_level="L1",
                sector_r1=0.20 if target else 0.09 - index * 0.01,
                sector_r5=0.30 if target else 0.18 - index * 0.01,
                sector_r20=0.08 if target else 0.30 - index * 0.015,
                broad_market_benchmark_r5=0.02,
                dated_membership_revision_id="membership-v1" if membership else None,
                constituent_return_coverage=1.0 if membership else None,
                constituent_ma20_coverage=1.0 if membership else None,
                breadth_up_1=0.60 if membership else None,
                breadth_above_ma20=0.50 if membership else None,
                activity_ratio_20=1.30 if membership else None,
                new_high_20_share=0.02 if membership else None,
                strong_rank_sessions_5=1 if membership else None,
                prior_state="neutral" if membership else None,
                representative_positive_share_5=0.60 if membership else None,
            )
        )
    return tuple(values)


def _stock_inputs(*, exact_price_semantics: bool = True) -> tuple[StockRuleInput, ...]:
    return (
        StockRuleInput(
            stock_code="000001",
            r1=0.08 if exact_price_semantics else None,
            r5=0.12 if exact_price_semantics else None,
            broad_market_benchmark_r5=0.02 if exact_price_semantics else None,
            volume_current=300.0,
            volume_previous_20=(100.0,) * 20,
            analysis_closes_60=(
                tuple(float(100 + index) for index in range(59)) + (170.0,)
                if exact_price_semantics
                else ()
            ),
            open_current=103.0 if exact_price_semantics else None,
            reference_close_previous=100.0 if exact_price_semantics else None,
            return_semantics_valid=exact_price_semantics,
            reference_close_semantics_valid=exact_price_semantics,
        ),
    )


def _build(inputs: TodayMarketRuleProjectionInputs, runtime: dict | None = None) -> dict:
    return build_today_market_read_model(
        snapshot_id="today-market-local-v1:synthetic",
        snapshot_content_fingerprint="a" * 64,
        data_date=date(2026, 7, 30).isoformat(),
        projected_snapshot=_projected_snapshot(),
        runtime_status=runtime or _runtime_status(),
        rule_inputs=inputs,
    )


def test_exact_rule_inputs_project_slice_b_results_and_replay_deterministically() -> None:
    inputs = TodayMarketRuleProjectionInputs(
        market_overview=_market_input(),
        sectors=_sector_inputs(),
        stocks=_stock_inputs(),
    )
    first = _build(inputs)
    second = _build(inputs)

    assert first == second
    assert first["read_model_version"] == READ_MODEL_VERSION
    assert first["market_state"] == "strong"
    assert first["market_overview"]["status"] == "ready"
    assert first["sector_groups"]["groups"]["new"][0]["sector_code"] == "S00"
    anomaly_types = [item["anomaly_type"] for item in first["stock_anomalies"]["items"]]
    assert "large_move" in anomaly_types
    assert "unusual_volume" in anomaly_types
    assert "gap" in anomaly_types
    assert first["research_link_summary"]["mutation_performed"] is False
    assert len(first["read_model_fingerprint"]) == 64


def test_default_production_projection_is_blocked_source_and_retains_local_context() -> None:
    result = _build(
        TodayMarketRuleProjectionInputs(
            market_unavailable_reason="full_market_universe_not_proven",
            sector_unavailable_reason="dated_membership_unavailable",
            stock_unavailable_reasons=("reference_close_semantics_unavailable",),
        )
    )
    assert result["refresh_state"] == "blocked_source_contract"
    assert result["market_state"] == "insufficient_coverage"
    assert result["market_overview"]["status"] == "unavailable"
    assert result["market_overview"]["selected_scope_context"]["advancing_count"] == 8
    assert result["source_summary"]["live_network_authorized"] is False
    assert result["source_summary"]["dominant_action"]["code"] == "reread_local_snapshot"
    assert result["technical_details"]["network_used"] is False


def test_missing_dated_membership_keeps_price_metrics_but_fails_closed() -> None:
    result = _build(
        TodayMarketRuleProjectionInputs(
            market_overview=_market_input(),
            sectors=_sector_inputs(membership=False),
            stock_unavailable_reasons=("stock_rule_inputs_unavailable",),
        )
    )
    insufficient = result["sector_groups"]["groups"]["insufficient_coverage"]
    assert len(insufficient) == 10
    assert all("dated_membership_unavailable" in item["missing_inputs"] for item in insufficient)
    assert any(item["r1_pct"] is not None for item in insufficient)
    assert result["sector_groups"]["constituent_confirmed_count"] == 0


def test_missing_price_and_reference_semantics_blocks_affected_stock_rules_only() -> None:
    result = _build(
        TodayMarketRuleProjectionInputs(
            market_overview=_market_input(),
            stocks=_stock_inputs(exact_price_semantics=False),
            stock_unavailable_reasons=(
                "analysis_price_semantics_unavailable",
                "reference_close_semantics_unavailable",
            ),
        )
    )
    anomaly_types = [item["anomaly_type"] for item in result["stock_anomalies"]["items"]]
    assert anomaly_types == ["unusual_volume"]
    diagnostics = result["stock_anomalies"]["diagnostics"][0]["unavailable_rules"]
    unavailable_types = {item[0] for item in diagnostics}
    assert {"large_move", "new_high", "new_low", "gap", "persistent_relative_strength"} <= unavailable_types


def test_refresh_projection_exposes_one_action_without_polling_contract() -> None:
    result = _build(
        TodayMarketRuleProjectionInputs(market_overview=_market_input()),
        _runtime_status(enabled=True),
    )
    assert result["refresh_state"] == "refresh_required"
    action = result["source_summary"]["dominant_action"]
    assert action == {
        "code": "automatic_first_entry",
        "label": "系统将执行一次有界模拟更新",
        "enabled": False,
        "automatic": True,
    }


def test_static_page_is_chinese_first_and_browser_does_not_own_rule_thresholds() -> None:
    html = (ROOT / "today_market" / "static" / "today_market.html").read_text(encoding="utf-8")
    script = (ROOT / "today_market" / "static" / "today_market.js").read_text(encoding="utf-8")

    ordered_ids = [
        'id="ordinary-market-panel"',
        'id="ordinary-core"',
        'id="ordinary-sector-focus"',
        'id="ordinary-sector-risk"',
        'id="ordinary-anomalies"',
        'id="ordinary-coverage"',
        'id="ordinary-technical"',
    ]
    positions = [html.index(value) for value in ordered_ids]
    assert positions == sorted(positions)
    assert "/today-market/api/read-model" in script
    assert "setInterval" not in script
    assert script.count("localStorage.setItem") == 1
    assert "aquantai.today-market.runtime" not in script
    for frozen_formula_fragment in (
        "0.975",
        "0.6745",
        "breadth_balance >=",
        "activity_ratio_20 >=",
        "strong_rank_sessions_5 >=",
    ):
        assert frozen_formula_fragment not in script


def test_read_model_layer_has_no_provider_database_network_or_mutation_import_path() -> None:
    path = ROOT / "backend" / "today_market_refresh" / "read_model.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    forbidden_import_prefixes = (
        "backend.database",
        "datasource",
        "sqlalchemy",
        "requests",
        "httpx",
        "openai",
        "recommendation",
        "portfolio",
        "trading",
    )
    assert not any(
        imported.startswith(prefix)
        for imported in imports
        for prefix in forbidden_import_prefixes
    )
    assert not ({"commit", "flush", "execute", "post", "put", "delete"} & calls)


def test_read_model_route_is_installed_on_default_application() -> None:
    assert "/today-market/api/read-model" in set(default_app.openapi()["paths"])


# Integration-level proof that the real read-model boundary stays read-only and
# fail-closed while reusing the existing local snapshot owners.
from types import SimpleNamespace

from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from backend.api.today_market import (
    TodayMarketSnapshotRequest,
    today_market_read_model,
)
from backend.database.engine import build_session_factory
from backend.database.models import Base, IngestionRun
from backend.today_market_refresh.runtime import (
    TodayMarketMockRuntimeConfigurationV1,
    install_today_market_runtime,
)
from scripts.demo_today_market import (
    VISIBLE_AT,
    _boundaries,
    _fix_recorded_times,
    _ingest_benchmark,
    _ingest_equity,
    _ingest_sector,
)


def test_real_read_model_boundary_is_zero_write_and_volume_only_fail_closed() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)
    try:
        equity = _ingest_equity(session_factory)
        benchmark = _ingest_benchmark(session_factory)
        sector = _ingest_sector(session_factory)
        _fix_recorded_times(
            session_factory,
            equity.ingestion_run_id,
            benchmark.ingestion_run_id,
            sector.ingestion_run_id,
        )
        with session_factory() as session:
            before = session.scalar(select(func.count()).select_from(IngestionRun))

        request = TodayMarketSnapshotRequest(
            equity_series_key=equity.series_key,
            benchmark_series_key=benchmark.series_key,
            sector_series_key=sector.series_key,
            boundaries=_boundaries(VISIBLE_AT),
        )
        app = SimpleNamespace(state=SimpleNamespace())
        install_today_market_runtime(
            app,
            configuration=TodayMarketMockRuntimeConfigurationV1(),
        )
        result = today_market_read_model(
            http_request=SimpleNamespace(app=app),
            snapshot_request=request,
            session_factory=session_factory,
        )

        with session_factory() as session:
            after = session.scalar(select(func.count()).select_from(IngestionRun))

        assert before == after == 3
        assert result["refresh_state"] == "blocked_source_contract"
        assert result["market_overview"]["status"] == "unavailable"
        assert result["market_overview"]["reason"] == "full_market_universe_not_proven"
        assert result["sector_groups"]["status"] == "unavailable"
        assert result["sector_groups"]["reason"] == "dated_membership_unavailable"
        assert result["technical_details"]["network_used"] is False
        anomaly_types = {
            item["anomaly_type"] for item in result["stock_anomalies"]["items"]
        }
        assert anomaly_types == {"unusual_volume"}
        assert all(
            item["anomaly_type"] != "sector_relative_outlier"
            for item in result["stock_anomalies"]["items"]
        )
    finally:
        engine.dispose()
