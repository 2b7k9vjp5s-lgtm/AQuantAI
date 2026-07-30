from __future__ import annotations

from dataclasses import replace

import pytest

from market_cockpit.today_market_rule_contracts import (
    MarketOverviewInput,
    SectorRuleInput,
    StockRuleInput,
)
from market_cockpit.today_market_rules import (
    calculate_market_overview,
    calculate_sector_hotspots,
    calculate_stock_anomalies,
)


def _market(
    returns: tuple[float, ...],
    *,
    expected: int = 10,
    accounted: int = 10,
    above: tuple[bool, ...] | None = None,
    calendar_conflict: bool = False,
    identity_conflicts: int = 0,
) -> MarketOverviewInput:
    if above is None:
        above = tuple(index < 6 for index in range(expected))
    return MarketOverviewInput(
        expected_active_count=expected,
        accounted_count=accounted,
        identity_conflict_count=identity_conflicts,
        calendar_conflict=calendar_conflict,
        valid_returns=returns,
        above_ma20_flags=above,
        new_high_20_flags=tuple(index == 0 for index in range(len(above))),
        new_low_20_flags=tuple(index == len(above) - 1 for index in range(len(above))),
        market_amount_current=200.0,
        market_amount_previous_20=(100.0,) * 20,
    )


def test_market_overview_states_and_exact_coverage_boundary() -> None:
    strong = calculate_market_overview(
        _market((0.03, 0.02, 0.02, 0.01, 0.01, 0.01, 0.0, -0.005, -0.005, -0.005))
    )
    assert strong.market_state == "strong"
    assert strong.breadth_balance == pytest.approx(0.3)
    assert strong.above_ma20_ratio == pytest.approx(0.6)
    assert strong.market_amount_ratio_20 == pytest.approx(2.0)
    assert strong.new_high_20_ratio == pytest.approx(0.1)

    weak = calculate_market_overview(
        _market(
            (-0.03, -0.02, -0.02, -0.01, -0.01, -0.01, 0.0, 0.005, 0.005, 0.005),
            above=(True, True, True, True, False, False, False, False, False, False),
        )
    )
    assert weak.market_state == "weak"
    assert weak.breadth_balance == pytest.approx(-0.3)

    mixed = calculate_market_overview(
        _market((0.02, 0.01, 0.01, 0.0, 0.0, -0.01, -0.01, -0.02, 0.005, -0.005))
    )
    assert mixed.market_state == "mixed"

    exact_ninety = calculate_market_overview(
        _market((0.03, 0.02, 0.01, 0.01, 0.01, 0.0, -0.001, -0.002, -0.003), accounted=9)
    )
    assert exact_ninety.return_coverage_ratio == pytest.approx(0.90)
    assert exact_ninety.market_state != "insufficient_coverage"

    below = calculate_market_overview(
        _market((0.03, 0.02, 0.01, 0.01, 0.0, -0.001, -0.002, -0.003), accounted=8)
    )
    assert below.return_coverage_ratio == pytest.approx(0.80)
    assert below.market_state == "insufficient_coverage"


def _sector(
    code: str,
    *,
    r1: float,
    r5: float,
    r20: float,
    breadth_up: float = 0.55,
    breadth_ma20: float = 0.55,
    activity: float = 1.0,
    new_high_share: float = 0.05,
    strong_sessions: int = 1,
    prior_state: str | None = None,
    membership: str | None = "membership-20260728-v1",
    return_coverage: float = 0.95,
    ma20_coverage: float = 0.90,
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
        new_high_20_share=new_high_share,
        strong_rank_sessions_5=strong_sessions,
        prior_state=prior_state,  # type: ignore[arg-type]
        representative_positive_share_5=0.67,
    )


def _sector_group(target: SectorRuleInput) -> tuple[SectorRuleInput, ...]:
    fillers = [
        _sector(
            f"S{index:02d}",
            r1=0.09 - index * 0.01,
            r5=0.18 - index * 0.02,
            r20=0.27 - index * 0.03,
            breadth_up=0.52,
            breadth_ma20=0.52,
            activity=0.9,
            new_high_share=0.03,
        )
        for index in range(10)
        if f"S{index:02d}" != target.sector_code
    ]
    return tuple(sorted((target, *fillers), key=lambda value: value.sector_code))


def _result_for(target: SectorRuleInput):
    results = calculate_sector_hotspots(_sector_group(target))
    return next(item for item in results if item.sector_code == target.sector_code)


def test_sector_percentile_tie_break_is_deterministic() -> None:
    values = tuple(
        _sector(f"S{index:02d}", r1=0.05, r5=0.05 - index * 0.001, r20=0.10 - index * 0.001)
        for index in range(10)
    )
    results = {item.sector_code: item for item in calculate_sector_hotspots(values)}
    assert results["S00"].r1_pct == pytest.approx(1.0)
    assert results["S09"].r1_pct == pytest.approx(0.0)
    assert results["S00"].fingerprint == calculate_sector_hotspots(values)[0].fingerprint


def test_sector_hotspot_priority_states() -> None:
    divergence = _result_for(
        _sector("S09", r1=-0.02, r5=0.06, r20=0.40, breadth_up=0.40, activity=1.1)
    )
    assert divergence.state == "high_level_divergence"

    cooling = _result_for(
        _sector(
            "S09",
            r1=0.0,
            r5=-0.10,
            r20=-0.10,
            breadth_up=0.40,
            activity=0.8,
            prior_state="strengthening",
        )
    )
    assert cooling.state == "cooling"

    spreading = _result_for(
        _sector(
            "S00",
            r1=0.20,
            r5=0.30,
            r20=0.40,
            breadth_up=0.70,
            breadth_ma20=0.65,
            activity=1.1,
            new_high_share=0.20,
            strong_sessions=4,
        )
    )
    assert spreading.state == "spreading"

    new_state = _result_for(
        _sector(
            "S00",
            r1=0.20,
            r5=0.30,
            r20=0.08,
            breadth_up=0.60,
            breadth_ma20=0.50,
            activity=1.3,
            new_high_share=0.02,
            strong_sessions=1,
            prior_state="neutral",
        )
    )
    assert new_state.state == "new"

    persistent = _result_for(
        _sector(
            "S00",
            r1=0.20,
            r5=0.30,
            r20=0.40,
            breadth_up=0.55,
            breadth_ma20=0.65,
            activity=0.9,
            new_high_share=0.02,
            strong_sessions=4,
        )
    )
    assert persistent.state == "persistent_strong"

    strengthening = _result_for(
        _sector(
            "S00",
            r1=-0.05,
            r5=0.30,
            r20=0.16,
            breadth_up=0.60,
            breadth_ma20=0.50,
            activity=1.3,
            new_high_share=0.01,
            strong_sessions=1,
        )
    )
    assert strengthening.state == "strengthening"

    neutral = _result_for(
        _sector(
            "S05",
            r1=0.035,
            r5=0.075,
            r20=0.105,
            breadth_up=0.52,
            breadth_ma20=0.52,
            activity=0.9,
        )
    )
    assert neutral.state == "neutral"


def test_sector_new_requires_explicit_prior_state() -> None:
    result = _result_for(
        _sector(
            "S00",
            r1=0.20,
            r5=0.30,
            r20=0.08,
            breadth_up=0.60,
            breadth_ma20=0.50,
            activity=1.3,
            new_high_share=0.02,
            strong_sessions=1,
            prior_state=None,
        )
    )
    assert result.state != "new"
    assert "prior_state_unavailable" in result.missing_inputs


def _stock(
    code: str,
    *,
    r1: float,
    r5: float,
    closes: tuple[float, ...] | None = None,
    volume_current: float = 100.0,
    open_current: float = 100.0,
    reference_close: float = 100.0,
    return_semantics: bool = True,
    reference_semantics: bool = True,
    membership: str | None = "membership-20260728-v1",
) -> StockRuleInput:
    if closes is None:
        closes = tuple(100.0 + index * 0.01 for index in range(60))
    return StockRuleInput(
        stock_code=code,
        r1=r1,
        r5=r5,
        broad_market_benchmark_r5=0.02,
        volume_current=volume_current,
        volume_previous_20=(100.0,) * 20,
        analysis_closes_60=closes,
        open_current=open_current,
        reference_close_previous=reference_close,
        return_semantics_valid=return_semantics,
        reference_close_semantics_valid=reference_semantics,
        sector_code="SEC-A",
        dated_membership_revision_id=membership,
    )


def test_stock_anomalies_cover_every_rule_and_stable_order() -> None:
    members = [
        _stock("A00", r1=0.10, r5=0.20, volume_current=300.0, open_current=103.0),
        _stock("A01", r1=-0.01, r5=0.01),
        _stock("A02", r1=-0.008, r5=0.015),
        _stock("A03", r1=-0.006, r5=0.02),
        _stock("A04", r1=-0.004, r5=0.025),
        _stock("A05", r1=-0.002, r5=0.03),
        _stock("A06", r1=0.002, r5=0.035),
        _stock("A07", r1=0.004, r5=0.04),
        _stock("A08", r1=0.006, r5=0.045),
        _stock(
            "A09",
            r1=-0.08,
            r5=-0.10,
            closes=tuple(160.0 - index for index in range(60)),
        ),
    ]
    result = calculate_stock_anomalies(tuple(members))
    a00_types = [item.anomaly_type for item in result.anomalies if item.stock_code == "A00"]
    assert a00_types == [
        "large_move",
        "unusual_volume",
        "new_high",
        "gap",
        "persistent_relative_strength",
        "sector_relative_outlier",
    ]
    assert any(
        item.stock_code == "A09" and item.anomaly_type == "new_low"
        for item in result.anomalies
    )
    global_types = [item.anomaly_type for item in result.anomalies]
    type_positions = {
        name: min(index for index, value in enumerate(global_types) if value == name)
        for name in set(global_types)
    }
    assert type_positions["large_move"] < type_positions["unusual_volume"]
    assert type_positions["unusual_volume"] < type_positions["new_high"]
    assert type_positions["gap"] < type_positions["persistent_relative_strength"]
    assert result.fingerprint == calculate_stock_anomalies(tuple(members)).fingerprint


def test_result_fingerprints_change_when_rule_relevant_input_changes() -> None:
    first = calculate_market_overview(_market((0.02,) * 7 + (-0.01,) * 3))
    second = calculate_market_overview(_market((0.02,) * 6 + (-0.01,) * 4))
    assert first.fingerprint != second.fingerprint

    sector = _sector_group(_sector("S00", r1=0.20, r5=0.30, r20=0.40))
    changed = tuple(
        replace(item, activity_ratio_20=1.5) if item.sector_code == "S00" else item
        for item in sector
    )
    assert calculate_sector_hotspots(sector)[0].fingerprint != calculate_sector_hotspots(changed)[0].fingerprint
