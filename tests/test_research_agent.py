import pandas as pd
import pytest

from agent import RESEARCH_DISCLAIMER, AgentRunConfig, ResearchContext
from agent.base import REPORT_FIELDS
from agent.research_agent import DeterministicResearchReportBuilder, LLMAdapter


def _factor_scores() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"score_date": "20260630", "stock_code": "000001", "factor_name": "composite:total", "score": 88.0, "rank": 1},
            {"score_date": "20260630", "stock_code": "000002", "factor_name": "composite:total", "score": 77.0, "rank": 2},
        ]
    )


def _ml_predictions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"prediction_date": "20260630", "stock_code": "000001", "model_name": "baseline", "prediction_score": 0.8, "prediction_rank": 1},
            {"prediction_date": "20260630", "stock_code": "000002", "model_name": "baseline", "prediction_score": 0.6, "prediction_rank": 2},
        ]
    )


def _context() -> ResearchContext:
    return ResearchContext(
        report_date="20260709",
        scope="Phase 5 local fixture research",
        factor_scores=_factor_scores(),
        backtest_metrics={"total_return": 0.12, "annual_return": 0.18, "max_drawdown": -0.05, "sharpe_ratio": 1.2},
        ml_predictions=_ml_predictions(),
        source_refs=["docs/factors.md", "docs/backtesting.md", "docs/ml.md"],
    )


def test_report_output_fields_and_disclaimer_are_present() -> None:
    report = DeterministicResearchReportBuilder().build_report(_context())
    payload = report.to_dict()

    assert list(payload.keys()) == REPORT_FIELDS
    assert report.disclaimer == RESEARCH_DISCLAIMER
    assert report.factor_highlights
    assert report.backtest_highlights
    assert report.ml_highlights
    assert report.risks
    assert report.limitations


def test_report_builder_works_without_llm_or_network_dependencies() -> None:
    result = DeterministicResearchReportBuilder().run(_context())

    assert result.config.agent_name == "deterministic_research_agent"
    assert "local inputs" in result.report.summary


def test_missing_optional_inputs_produce_documented_empty_sections() -> None:
    context = ResearchContext(report_date="20260709", scope="empty input fixture", source_refs=["issue-12"])

    report = DeterministicResearchReportBuilder().build_report(context)

    assert report.factor_highlights == ["No factor score inputs were provided."]
    assert report.backtest_highlights == ["No backtest metrics were provided."]
    assert report.ml_highlights == ["No ML prediction inputs were provided."]
    assert report.source_refs == ["issue-12"]


def test_missing_required_input_columns_fail_clearly() -> None:
    context = ResearchContext(
        report_date="20260709",
        scope="bad fixture",
        factor_scores=pd.DataFrame([{"stock_code": "000001"}]),
    )

    with pytest.raises(ValueError, match="factor_scores is missing required columns"):
        DeterministicResearchReportBuilder().build_report(context)


def test_report_text_avoids_investment_advice_wording() -> None:
    report = DeterministicResearchReportBuilder().build_report(_context())
    text = " ".join(str(value) for value in report.to_dict().values()).lower()

    assert "guaranteed return" not in text
    assert "place order" not in text
    assert "recommendation to buy" not in text
    assert "recommendation to sell" not in text
    assert "not an instruction to buy, sell, or hold" in text


def test_llm_adapter_is_lazy_and_mockable() -> None:
    adapter = LLMAdapter()

    assert not adapter.is_available()
    with pytest.raises(RuntimeError, match="No LLM client is configured"):
        _ = adapter.client

    class FakeClient:
        def summarize_sections(self, sections: list[str]) -> list[str]:
            return [f"summary:{section}" for section in sections]

    mocked = LLMAdapter(FakeClient())
    assert mocked.is_available()
    assert mocked.summarize_sections(["factor", "backtest"]) == ["summary:factor", "summary:backtest"]


def test_report_builder_rejects_llm_enabled_config() -> None:
    with pytest.raises(ValueError, match="does not call LLM adapters"):
        DeterministicResearchReportBuilder(AgentRunConfig(include_llm=True))
