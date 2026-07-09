"""Read-only dashboard payload builders."""

from __future__ import annotations

from typing import Any

from dashboard.schemas import DashboardCard, DashboardMetric, DashboardPage, DashboardReportView, DashboardTable


def build_dashboard_overview(
    factor_rows: list[dict[str, Any]] | None = None,
    backtest_metrics: dict[str, Any] | None = None,
    ml_rows: list[dict[str, Any]] | None = None,
    report: dict[str, Any] | None = None,
    source_refs: list[str] | None = None,
) -> DashboardPage:
    """Build a read-only dashboard overview payload."""
    factor_rows = factor_rows or _sample_factor_rows()
    backtest_metrics = backtest_metrics or _sample_backtest_metrics()
    ml_rows = ml_rows or _sample_ml_rows()
    report = report or _sample_report()
    source_refs = source_refs or ["docs/factors.md", "docs/backtesting.md", "docs/ml.md", "docs/agent.md"]

    sections = {
        "project_overview": DashboardCard(
            title="AQuantAI",
            body="Research-only quantitative platform foundation frozen for the v0.1 baseline.",
            metrics=[DashboardMetric("phase", "v0.1 baseline"), DashboardMetric("mode", "read-only")],
        ).to_dict(),
        "factor_summary": DashboardTable(
            title="Factor Summary",
            columns=["score_date", "stock_code", "factor_name", "score", "rank"],
            rows=factor_rows,
        ).to_dict(),
        "backtest_summary": DashboardCard(
            title="Backtest Summary",
            body="Deterministic fixture metrics for read-only inspection.",
            metrics=[DashboardMetric(key, value) for key, value in backtest_metrics.items()],
        ).to_dict(),
        "ml_summary": DashboardTable(
            title="ML Prediction Summary",
            columns=["prediction_date", "stock_code", "model_name", "prediction_score", "prediction_rank"],
            rows=ml_rows,
        ).to_dict(),
        "research_report_summary": DashboardReportView(
            title=report["title"],
            summary=report["summary"],
            risks=report.get("risks", []),
            limitations=report.get("limitations", []),
            source_refs=report.get("source_refs", []),
        ).to_dict(),
        "risk_and_disclaimer": {
            "risks": report.get("risks", []),
            "limitations": report.get("limitations", []),
        },
    }
    return DashboardPage(page_id="dashboard_overview", title="AQuantAI Dashboard Overview", sections=sections, source_refs=source_refs)


def build_dashboard_report(report: dict[str, Any] | None = None) -> DashboardPage:
    """Build a read-only dashboard report payload."""
    report = report or _sample_report()
    sections = {
        "research_report_summary": DashboardReportView(
            title=report["title"],
            summary=report["summary"],
            risks=report.get("risks", []),
            limitations=report.get("limitations", []),
            source_refs=report.get("source_refs", []),
        ).to_dict(),
        "factor_highlights": report.get("factor_highlights", []),
        "backtest_highlights": report.get("backtest_highlights", []),
        "ml_highlights": report.get("ml_highlights", []),
        "risk_and_disclaimer": {
            "risks": report.get("risks", []),
            "limitations": report.get("limitations", []),
        },
    }
    return DashboardPage(
        page_id="dashboard_report",
        title=report["title"],
        sections=sections,
        source_refs=report.get("source_refs", []),
    )


def _sample_factor_rows() -> list[dict[str, Any]]:
    return [
        {"score_date": "20260709", "stock_code": "000001", "factor_name": "composite:total", "score": 88.0, "rank": 1},
        {"score_date": "20260709", "stock_code": "000002", "factor_name": "composite:total", "score": 77.0, "rank": 2},
    ]


def _sample_backtest_metrics() -> dict[str, Any]:
    return {"total_return": 0.12, "max_drawdown": -0.05, "sharpe_ratio": 1.2}


def _sample_ml_rows() -> list[dict[str, Any]]:
    return [
        {"prediction_date": "20260709", "stock_code": "000001", "model_name": "baseline", "prediction_score": 0.8, "prediction_rank": 1},
        {"prediction_date": "20260709", "stock_code": "000002", "model_name": "baseline", "prediction_score": 0.6, "prediction_rank": 2},
    ]


def _sample_report() -> dict[str, Any]:
    return {
        "title": "AQuantAI Research Report - Dashboard Fixture",
        "summary": "Read-only dashboard fixture assembled from local research outputs.",
        "factor_highlights": ["000001 ranked 1 for composite:total with score 88.0000."],
        "backtest_highlights": ["total_return: 0.1200", "max_drawdown: -0.0500"],
        "ml_highlights": ["baseline ranked 000001 at 1 with prediction score 0.8000."],
        "risks": ["Research outputs depend on local fixture quality."],
        "limitations": ["This dashboard payload does not use live data."],
        "source_refs": ["docs/agent.md", "docs/dashboard.md"],
    }
