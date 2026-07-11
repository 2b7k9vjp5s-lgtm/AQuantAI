"""End-to-end local fixture demo for the AQuantAI research flow."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from agent import ResearchContext
from agent.research_agent import DeterministicResearchReportBuilder
from dashboard import build_dashboard_overview


def build_demo_payload() -> dict[str, Any]:
    factor_scores = pd.DataFrame(
        [
            {"score_date": "20260709", "stock_code": "000001", "factor_name": "composite:total", "score": 88.0, "rank": 1},
            {"score_date": "20260709", "stock_code": "000002", "factor_name": "composite:total", "score": 77.0, "rank": 2},
        ]
    )
    backtest_metrics = {"total_return": 0.12, "annual_return": 0.18, "max_drawdown": -0.05, "sharpe_ratio": 1.2}
    ml_predictions = pd.DataFrame(
        [
            {"prediction_date": "20260709", "stock_code": "000001", "model_name": "baseline", "prediction_score": 0.8, "prediction_rank": 1},
            {"prediction_date": "20260709", "stock_code": "000002", "model_name": "baseline", "prediction_score": 0.6, "prediction_rank": 2},
        ]
    )
    source_refs = ["docs/factors.md", "docs/backtesting.md", "docs/ml.md", "docs/agent.md", "docs/dashboard.md"]
    report = DeterministicResearchReportBuilder().build_report(
        ResearchContext(
            report_date="20260709",
            scope="v0.2 local Dashboard baseline fixture demo",
            factor_scores=factor_scores,
            backtest_metrics=backtest_metrics,
            ml_predictions=ml_predictions,
            source_refs=source_refs,
        )
    )
    dashboard = build_dashboard_overview(
        factor_rows=factor_scores.to_dict(orient="records"),
        backtest_metrics=backtest_metrics,
        ml_rows=ml_predictions.to_dict(orient="records"),
        report=report.to_dict(),
        source_refs=source_refs,
    ).to_dict()
    return {"report": report.to_dict(), "dashboard": dashboard}


def main() -> None:
    print(json.dumps(build_demo_payload(), indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
