"""Zero-network synthetic demo for Today Market deterministic Slice B rules."""

from __future__ import annotations

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


def main() -> None:
    market = calculate_market_overview(
        MarketOverviewInput(
            expected_active_count=10,
            accounted_count=10,
            identity_conflict_count=0,
            calendar_conflict=False,
            valid_returns=(0.03, 0.02, 0.02, 0.01, 0.01, 0.01, 0.0, -0.005, -0.005, -0.005),
            above_ma20_flags=(True, True, True, True, True, True, False, False, False, False),
            new_high_20_flags=(True, False, False, False, False, False, False, False, False, False),
            new_low_20_flags=(False, False, False, False, False, False, False, False, False, True),
            market_amount_current=200.0,
            market_amount_previous_20=(100.0,) * 20,
        )
    )
    assert market.market_state == "strong"

    sectors = tuple(
        SectorRuleInput(
            sector_code=f"S{index:02d}",
            sector_name=f"Synthetic Sector {index:02d}",
            taxonomy="synthetic-industry",
            classification_level="L1",
            sector_r1=0.10 - index * 0.01,
            sector_r5=0.20 - index * 0.015,
            sector_r20=0.30 - index * 0.02,
            broad_market_benchmark_r5=0.01,
            dated_membership_revision_id="synthetic-membership-20260728-v1",
            constituent_return_coverage=0.95,
            constituent_ma20_coverage=0.90,
            breadth_up_1=0.70 if index == 0 else 0.50,
            breadth_above_ma20=0.65 if index == 0 else 0.50,
            activity_ratio_20=1.10 if index == 0 else 0.80,
            new_high_20_share=0.20 if index == 0 else 0.02,
            strong_rank_sessions_5=4 if index == 0 else 1,
            prior_state=None,
        )
        for index in range(10)
    )
    hotspot = calculate_sector_hotspots(sectors)
    assert hotspot[0].state == "spreading"

    stocks = tuple(
        StockRuleInput(
            stock_code=f"A{index:02d}",
            r1=(0.10 if index == 0 else -0.01 + index * 0.002),
            r5=(0.20 if index == 0 else 0.01 + index * 0.005),
            broad_market_benchmark_r5=0.02,
            volume_current=300.0 if index == 0 else 100.0,
            volume_previous_20=(100.0,) * 20,
            analysis_closes_60=tuple(100.0 + step * 0.01 for step in range(60)),
            open_current=103.0 if index == 0 else 100.0,
            reference_close_previous=100.0,
            return_semantics_valid=True,
            reference_close_semantics_valid=True,
            sector_code="SEC-A",
            dated_membership_revision_id="synthetic-membership-20260728-v1",
        )
        for index in range(10)
    )
    anomalies = calculate_stock_anomalies(stocks)
    first_types = [item.anomaly_type for item in anomalies.anomalies if item.stock_code == "A00"]
    assert "large_move" in first_types
    assert "unusual_volume" in first_types
    assert "gap" in first_types
    assert "persistent_relative_strength" in first_types
    assert "sector_relative_outlier" in first_types

    print(
        "Today Market deterministic rules demo OK:",
        market.market_state,
        hotspot[0].state,
        len(anomalies.anomalies),
    )


if __name__ == "__main__":
    main()
