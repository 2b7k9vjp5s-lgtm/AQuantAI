from __future__ import annotations

import inspect

import pytest

from market_cockpit import today_market_rule_contracts, today_market_rules
from market_cockpit.today_market_rule_contracts import (
    MarketOverviewInput,
    SectorRuleInput,
    StockRuleInput,
    TodayMarketRuleInputError,
)
from market_cockpit.today_market_rules import (
    calculate_market_overview,
    calculate_sector_hotspots,
    calculate_stock_anomalies,
)


def _sector(
    code: str,
    *,
    r1: float,
    r5: float,
    r20: float,
    membership: str | None = "dated-membership-v1",
    return_coverage: float = 0.95,
    ma20_coverage: float = 0.90,
    breadth_up: float | None = 0.70,
    breadth_ma20: float = 0.65,
    activity: float | None = 1.1,
    new_high: float | None = 0.20,
    strong_sessions: int | None = 4,
    prior_state: str | None = None,
    ambiguous: bool = False,
) -> SectorRuleInput:
    return SectorRuleInput(
        sector_code=code,
        sector_name=f"Synthetic {code}",
        taxonomy="synthetic-industry",
        classification_level="L1",
        sector_r1=r1,
        sector_r5=r5,
        sector_r20=r20,
        broad_market_benchmark_r5=0.01,
        dated_membership_revision_id=membership,
        constituent_return_coverage=return_coverage,
        constituent_ma20_coverage=ma20_coverage,
        breadth_up_1=breadth_up,
        breadth_above_ma20=breadth_ma20,
        activity_ratio_20=activity,
        new_high_20_share=new_high,
        strong_rank_sessions_5=strong_sessions,
        prior_state=prior_state,  # type: ignore[arg-type]
        identity_ambiguous=ambiguous,
    )


def _ten_sectors(target: SectorRuleInput) -> tuple[SectorRuleInput, ...]:
    values = [target]
    for index in range(1, 10):
        code = f"F{index:02d}"
        values.append(
            _sector(
                code,
                r1=0.09 - index * 0.01,
                r5=0.18 - index * 0.015,
                r20=0.27 - index * 0.02,
                breadth_up=0.50,
                breadth_ma20=0.50,
                activity=0.8,
                new_high=0.02,
            )
        )
    return tuple(values)


def _target_result(target: SectorRuleInput):
    return next(
        item
        for item in calculate_sector_hotspots(_ten_sectors(target))
        if item.sector_code == target.sector_code
    )


def test_missing_dated_membership_is_insufficient_but_price_metrics_remain_visible() -> None:
    target = _sector("TARGET", r1=0.20, r5=0.30, r20=0.40, membership=None)
    result = _target_result(target)
    assert result.state == "insufficient_coverage"
    assert result.r1_pct is not None
    assert result.r5_pct is not None
    assert result.r20_pct is not None
    assert result.sector_relative_5 == pytest.approx(0.29)
    assert "dated_membership_unavailable" in result.missing_inputs


def test_fewer_than_ten_ranked_sectors_and_low_return_coverage_fail_closed() -> None:
    short = tuple(
        _sector(f"S{index}", r1=0.10 - index * 0.01, r5=0.20, r20=0.30)
        for index in range(9)
    )
    results = calculate_sector_hotspots(short)
    assert all(item.state == "insufficient_coverage" for item in results)
    assert all(item.r1_pct is None for item in results)

    target = _sector(
        "TARGET", r1=0.20, r5=0.30, r20=0.40, return_coverage=0.899999
    )
    result = _target_result(target)
    assert result.state == "insufficient_coverage"
    assert "constituent_return_coverage_below_0.90" in result.missing_inputs


def test_ma20_coverage_below_080_blocks_ma20_dependent_state_without_imputation() -> None:
    target = _sector(
        "TARGET",
        r1=0.20,
        r5=0.30,
        r20=0.40,
        ma20_coverage=0.79,
        breadth_up=0.70,
        breadth_ma20=0.90,
        activity=0.8,
        new_high=0.20,
    )
    result = _target_result(target)
    assert result.breadth_above_ma20 is None
    assert result.state == "neutral"
    assert "constituent_ma20_state_input_unavailable" in result.missing_inputs


def test_state_specific_missing_inputs_are_explicit_without_forcing_priority_one() -> None:
    missing_breadth = _target_result(
        _sector(
            "TARGET",
            r1=0.20,
            r5=0.30,
            r20=0.08,
            breadth_up=None,
            breadth_ma20=0.50,
            activity=1.3,
            new_high=0.02,
            strong_sessions=1,
            prior_state="neutral",
        )
    )
    assert missing_breadth.state == "neutral"
    assert "breadth_up_1_unavailable" in missing_breadth.missing_inputs

    missing_activity = _target_result(
        _sector(
            "TARGET",
            r1=0.20,
            r5=0.30,
            r20=0.08,
            breadth_up=0.60,
            breadth_ma20=0.50,
            activity=None,
            new_high=0.02,
            strong_sessions=1,
            prior_state="neutral",
        )
    )
    assert missing_activity.state == "neutral"
    assert "activity_ratio_20_unavailable" in missing_activity.missing_inputs

    missing_new_high = _target_result(
        _sector(
            "TARGET",
            r1=0.20,
            r5=0.30,
            r20=0.40,
            breadth_up=0.70,
            breadth_ma20=0.65,
            activity=1.1,
            new_high=None,
            strong_sessions=4,
        )
    )
    assert missing_new_high.state == "persistent_strong"
    assert "new_high_20_share_unavailable" in missing_new_high.missing_inputs

    missing_persistence = _target_result(
        _sector(
            "TARGET",
            r1=0.20,
            r5=0.30,
            r20=0.40,
            breadth_up=0.60,
            breadth_ma20=0.65,
            activity=1.1,
            new_high=0.02,
            strong_sessions=None,
        )
    )
    assert missing_persistence.state == "strengthening"
    assert "strong_rank_sessions_5_unavailable" in missing_persistence.missing_inputs

    for result in (
        missing_breadth,
        missing_activity,
        missing_new_high,
        missing_persistence,
    ):
        assert result.state != "insufficient_coverage"


def test_duplicate_or_ambiguous_sector_identity_fails_closed() -> None:
    duplicate = _sector("DUP", r1=0.1, r5=0.2, r20=0.3)
    with pytest.raises(TodayMarketRuleInputError, match="duplicate sector identity"):
        calculate_sector_hotspots((duplicate, duplicate))

    target = _sector("TARGET", r1=0.20, r5=0.30, r20=0.40, ambiguous=True)
    result = _target_result(target)
    assert result.state == "insufficient_coverage"
    assert "ambiguous_sector_identity" in result.missing_inputs


def _stock(
    code: str,
    *,
    r1: float = 0.08,
    r5: float = 0.12,
    return_semantics: bool = True,
    reference_semantics: bool = True,
    membership: str | None = "dated-membership-v1",
    closes: tuple[float, ...] | None = None,
    volumes: tuple[float, ...] | None = None,
) -> StockRuleInput:
    return StockRuleInput(
        stock_code=code,
        r1=r1,
        r5=r5,
        broad_market_benchmark_r5=0.02,
        volume_current=300.0,
        volume_previous_20=(100.0,) * 20 if volumes is None else volumes,
        analysis_closes_60=(tuple(100.0 + index for index in range(60)) if closes is None else closes),
        open_current=103.0,
        reference_close_previous=100.0,
        return_semantics_valid=return_semantics,
        reference_close_semantics_valid=reference_semantics,
        sector_code="SEC",
        dated_membership_revision_id=membership,
    )


def _diagnostics(result, code: str) -> dict[str, str]:
    row = next(item for item in result.diagnostics if item.stock_code == code)
    return dict(row.unavailable_rules)


def test_missing_return_or_reference_semantics_blocks_only_affected_rules() -> None:
    result = calculate_stock_anomalies(
        (_stock("A", return_semantics=False, reference_semantics=False),)
    )
    types = [item.anomaly_type for item in result.anomalies]
    assert types == ["unusual_volume"]
    diagnostics = _diagnostics(result, "A")
    assert diagnostics["large_move"] == "return_semantics_unavailable"
    assert diagnostics["new_high"] == "return_semantics_unavailable"
    assert diagnostics["gap"] == "reference_close_semantics_unavailable"
    assert diagnostics["persistent_relative_strength"] == "five_session_return_semantics_unavailable"
    assert diagnostics["sector_relative_outlier"] == "return_semantics_unavailable"


def test_incomplete_lookback_and_missing_membership_do_not_truncate_or_guess() -> None:
    result = calculate_stock_anomalies(
        (
            _stock("A", closes=(100.0,) * 59, volumes=(100.0,) * 19, membership=None),
        )
    )
    diagnostics = _diagnostics(result, "A")
    assert diagnostics["unusual_volume"] == "exact_20_session_volume_window_unavailable"
    assert diagnostics["new_high"] == "exact_60_session_analysis_close_window_unavailable"
    assert diagnostics["new_low"] == "exact_60_session_analysis_close_window_unavailable"
    assert diagnostics["sector_relative_outlier"] == "dated_membership_unavailable"


def test_sector_relative_outlier_requires_nonzero_mad() -> None:
    stocks = tuple(_stock(f"A{index:02d}", r1=0.01) for index in range(10))
    result = calculate_stock_anomalies(stocks)
    assert not any(item.anomaly_type == "sector_relative_outlier" for item in result.anomalies)
    assert all(
        _diagnostics(result, stock.stock_code).get("sector_relative_outlier") == "sector_mad_zero"
        for stock in stocks
    )


def test_market_overview_never_imputes_missing_ma20_or_invalid_amount() -> None:
    value = MarketOverviewInput(
        expected_active_count=10,
        accounted_count=10,
        identity_conflict_count=0,
        calendar_conflict=False,
        valid_returns=(0.01,) * 10,
        above_ma20_flags=(),
        market_amount_current=None,
        market_amount_previous_20=(),
    )
    result = calculate_market_overview(value)
    assert result.market_state == "insufficient_coverage"
    assert result.above_ma20_ratio is None
    assert result.market_amount_ratio_20 is None

    with pytest.raises(TodayMarketRuleInputError):
        calculate_market_overview(
            MarketOverviewInput(
                expected_active_count=10,
                accounted_count=10,
                identity_conflict_count=0,
                calendar_conflict=False,
                valid_returns=(float("nan"),),
                above_ma20_flags=(True,),
            )
        )


def test_rule_modules_have_no_network_database_runtime_ai_or_research_mutation_path() -> None:
    source = (inspect.getsource(today_market_rule_contracts) + inspect.getsource(today_market_rules)).lower()
    for forbidden in (
        "import requests",
        "import httpx",
        "urllib.request",
        "import socket",
        "from socket",
        "import sqlalchemy",
        "from sqlalchemy",
        "backend.database",
        "backend.today_market_refresh",
        "from datasource",
        "import datasource",
        "os.environ",
        "getenv(",
        "from openai",
        "import openai",
        "recommendation.",
        "portfolio.",
        "trading.",
        "accepted_evidence",
        "investment_candidate_service",
        "limit_up",
        "limit_down",
    ):
        assert forbidden not in source
