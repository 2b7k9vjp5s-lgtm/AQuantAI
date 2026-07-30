"""Deterministic Today Market Slice B rules.

All functions are pure and source-neutral. No database, network, credential, runtime,
UI, AI, research-mutation, recommendation, portfolio, or trading path exists here.
"""

from __future__ import annotations

from collections import defaultdict
from math import isfinite
from statistics import median

from market_cockpit.today_market_rule_contracts import (
    ANOMALY_RULE_ORDER,
    ANOMALY_RULE_VERSION,
    CONSTITUENT_MA20_COVERAGE_MIN,
    CONSTITUENT_RETURN_COVERAGE_MIN,
    MARKET_RULE_VERSION,
    MINIMUM_RANKED_SECTOR_COUNT,
    RETURN_EPSILON,
    SECTOR_RULE_VERSION,
    STRONG_PRIOR_STATES,
    HotspotState,
    MarketOverviewInput,
    MarketOverviewResult,
    SectorHotspotResult,
    SectorRuleInput,
    StockAnomaly,
    StockAnomalyResult,
    StockRuleDiagnostics,
    StockRuleInput,
    TodayMarketRuleInputError,
)


def calculate_market_overview(value: MarketOverviewInput) -> MarketOverviewResult:
    """Apply the frozen Market Overview v1 contract."""
    if value.expected_active_count <= 0:
        raise TodayMarketRuleInputError("expected_active_count must be positive")
    if not 0 <= value.accounted_count <= value.expected_active_count:
        raise TodayMarketRuleInputError("accounted_count must be within the expected universe")
    if value.identity_conflict_count < 0:
        raise TodayMarketRuleInputError("identity_conflict_count must be nonnegative")

    returns = tuple(_finite_required(item, "valid_returns") for item in value.valid_returns)
    if len(returns) > value.accounted_count:
        raise TodayMarketRuleInputError("valid returns cannot exceed accounted instruments")

    eligible_20_count = len(value.above_ma20_flags)
    if value.new_high_20_flags and len(value.new_high_20_flags) != eligible_20_count:
        raise TodayMarketRuleInputError("new_high_20_flags must use the same 20-session universe")
    if value.new_low_20_flags and len(value.new_low_20_flags) != eligible_20_count:
        raise TodayMarketRuleInputError("new_low_20_flags must use the same 20-session universe")

    valid_return_count = len(returns)
    return_coverage_ratio = valid_return_count / value.expected_active_count
    advancing = sum(item > RETURN_EPSILON for item in returns)
    declining = sum(item < -RETURN_EPSILON for item in returns)
    unchanged = valid_return_count - advancing - declining
    advance_ratio = advancing / valid_return_count if valid_return_count else None
    breadth_balance = (
        (advancing - declining) / valid_return_count if valid_return_count else None
    )
    median_return = float(median(returns)) if returns else None
    above_ma20_ratio = (
        sum(value.above_ma20_flags) / eligible_20_count if eligible_20_count else None
    )
    new_high_20_ratio = (
        sum(value.new_high_20_flags) / eligible_20_count
        if eligible_20_count and value.new_high_20_flags
        else None
    )
    new_low_20_ratio = (
        sum(value.new_low_20_flags) / eligible_20_count
        if eligible_20_count and value.new_low_20_flags
        else None
    )

    missing: list[str] = []
    if value.calendar_conflict:
        missing.append("calendar_conflict")
    if value.identity_conflict_count:
        missing.append("identity_conflict")
    if return_coverage_ratio < 0.90:
        missing.append("return_coverage_below_0.90")
    if above_ma20_ratio is None:
        missing.append("above_ma20_ratio_unavailable")

    market_amount_current = _finite_optional_checked(
        value.market_amount_current, "market_amount_current"
    )
    market_amount_ratio_20: float | None = None
    if market_amount_current is None:
        missing.append("market_amount_current_unavailable")
    elif market_amount_current < 0:
        raise TodayMarketRuleInputError("market_amount_current must be nonnegative")
    elif len(value.market_amount_previous_20) != 20:
        missing.append("market_amount_previous_20_incomplete")
    else:
        prior_amounts = tuple(
            _finite_required(item, "market_amount_previous_20")
            for item in value.market_amount_previous_20
        )
        if any(item < 0 for item in prior_amounts):
            raise TodayMarketRuleInputError("market amount history must be nonnegative")
        baseline = float(median(prior_amounts))
        if baseline <= 0:
            missing.append("market_amount_previous_20_nonpositive_baseline")
        else:
            market_amount_ratio_20 = market_amount_current / baseline

    core_failure = any(
        reason in {
            "calendar_conflict",
            "identity_conflict",
            "return_coverage_below_0.90",
            "above_ma20_ratio_unavailable",
        }
        for reason in missing
    )
    if core_failure or breadth_balance is None or median_return is None or above_ma20_ratio is None:
        market_state = "insufficient_coverage"
    elif breadth_balance >= 0.20 and median_return > 0 and above_ma20_ratio >= 0.55:
        market_state = "strong"
    elif breadth_balance <= -0.20 and median_return < 0 and above_ma20_ratio <= 0.45:
        market_state = "weak"
    else:
        market_state = "mixed"

    return MarketOverviewResult(
        rule_version=MARKET_RULE_VERSION,
        market_state=market_state,
        expected_active_count=value.expected_active_count,
        accounted_count=value.accounted_count,
        missing_source_count=value.expected_active_count - value.accounted_count,
        identity_conflict_count=value.identity_conflict_count,
        valid_return_count=valid_return_count,
        return_coverage_ratio=return_coverage_ratio,
        advancing_count=advancing,
        declining_count=declining,
        unchanged_count=unchanged,
        advance_ratio=advance_ratio,
        breadth_balance=breadth_balance,
        median_return=median_return,
        eligible_20_count=eligible_20_count,
        above_ma20_ratio=above_ma20_ratio,
        new_high_20_ratio=new_high_20_ratio,
        new_low_20_ratio=new_low_20_ratio,
        market_amount_current=market_amount_current,
        market_amount_ratio_20=market_amount_ratio_20,
        missing_inputs=tuple(sorted(set(missing))),
    )


def calculate_sector_hotspots(values: tuple[SectorRuleInput, ...]) -> tuple[SectorHotspotResult, ...]:
    """Rank within exact taxonomy/level groups and apply ordered hotspot states."""
    seen: set[tuple[str, str | None, str]] = set()
    groups: dict[tuple[str, str | None], list[SectorRuleInput]] = defaultdict(list)
    for value in values:
        _require_text(value.sector_code, "sector_code")
        _require_text(value.sector_name, "sector_name")
        _require_text(value.taxonomy, "taxonomy")
        identity = (value.taxonomy, value.classification_level, value.sector_code)
        if identity in seen:
            raise TodayMarketRuleInputError(f"duplicate sector identity: {identity}")
        seen.add(identity)
        _validate_sector_input(value)
        groups[(value.taxonomy, value.classification_level)].append(value)

    results: list[SectorHotspotResult] = []
    for group_key in sorted(groups, key=lambda item: (item[0], item[1] or "")):
        group = sorted(groups[group_key], key=lambda item: item.sector_code)
        r1_pct = _percentiles(
            [(item.sector_code, item.sector_r1) for item in group],
            minimum_count=MINIMUM_RANKED_SECTOR_COUNT,
        )
        r5_pct = _percentiles(
            [(item.sector_code, item.sector_r5) for item in group],
            minimum_count=MINIMUM_RANKED_SECTOR_COUNT,
        )
        r20_pct = _percentiles(
            [(item.sector_code, item.sector_r20) for item in group],
            minimum_count=MINIMUM_RANKED_SECTOR_COUNT,
        )
        for item in group:
            results.append(
                _sector_result(
                    item,
                    ranked_sector_count=len(group),
                    r1_pct=r1_pct.get(item.sector_code),
                    r5_pct=r5_pct.get(item.sector_code),
                    r20_pct=r20_pct.get(item.sector_code),
                )
            )
    return tuple(results)


def calculate_stock_anomalies(values: tuple[StockRuleInput, ...]) -> StockAnomalyResult:
    """Apply all Stock Anomaly v1 rules with deterministic ordering."""
    seen: set[str] = set()
    for value in values:
        _require_text(value.stock_code, "stock_code")
        if value.stock_code in seen:
            raise TodayMarketRuleInputError(f"duplicate stock_code: {value.stock_code}")
        seen.add(value.stock_code)
        _validate_stock_input(value)

    abs_r1_pct = _percentiles(
        [
            (item.stock_code, abs(float(item.r1)) if item.return_semantics_valid and item.r1 is not None else None)
            for item in values
        ],
        minimum_count=1,
    )
    r5_pct = _percentiles(
        [
            (item.stock_code, float(item.r5) if item.return_semantics_valid and item.r5 is not None else None)
            for item in values
        ],
        minimum_count=1,
    )

    sector_groups: dict[tuple[str, str], list[StockRuleInput]] = defaultdict(list)
    for item in values:
        if (
            item.return_semantics_valid
            and not item.sector_identity_ambiguous
            and item.r1 is not None
            and item.sector_code
            and item.dated_membership_revision_id
        ):
            sector_groups[(item.sector_code, item.dated_membership_revision_id)].append(item)

    anomalies: list[StockAnomaly] = []
    diagnostics: list[StockRuleDiagnostics] = []
    for item in sorted(values, key=lambda value: value.stock_code):
        stock_anomalies, unavailable = _stock_anomalies_for_one(
            item,
            abs_r1_pct=abs_r1_pct,
            r5_pct=r5_pct,
            sector_groups=sector_groups,
        )
        anomalies.extend(stock_anomalies)
        diagnostics.append(
            StockRuleDiagnostics(item.stock_code, tuple(unavailable))
        )

    order = {rule: index for index, rule in enumerate(ANOMALY_RULE_ORDER)}
    anomalies.sort(
        key=lambda anomaly: (
            order[anomaly.anomaly_type],
            -abs(anomaly.primary_metric),
            anomaly.stock_code,
        )
    )
    return StockAnomalyResult(
        rule_version=ANOMALY_RULE_VERSION,
        anomalies=tuple(anomalies),
        diagnostics=tuple(diagnostics),
    )


def _sector_result(
    item: SectorRuleInput,
    *,
    ranked_sector_count: int,
    r1_pct: float | None,
    r5_pct: float | None,
    r20_pct: float | None,
) -> SectorHotspotResult:
    missing: list[str] = []
    if ranked_sector_count < MINIMUM_RANKED_SECTOR_COUNT:
        missing.append("ranked_sector_count_below_10")
    if item.identity_ambiguous:
        missing.append("ambiguous_sector_identity")
    if not item.dated_membership_revision_id:
        missing.append("dated_membership_unavailable")
    if item.constituent_return_coverage is None:
        missing.append("constituent_return_coverage_unavailable")
    elif item.constituent_return_coverage < CONSTITUENT_RETURN_COVERAGE_MIN:
        missing.append("constituent_return_coverage_below_0.90")
    if r1_pct is None:
        missing.append("r1_cross_section_unavailable")
    if r5_pct is None:
        missing.append("r5_cross_section_unavailable")
    if r20_pct is None:
        missing.append("r20_cross_section_unavailable")

    ma20_available = (
        item.constituent_ma20_coverage is not None
        and item.constituent_ma20_coverage >= CONSTITUENT_MA20_COVERAGE_MIN
        and item.breadth_above_ma20 is not None
    )
    breadth_above_ma20 = item.breadth_above_ma20 if ma20_available else None
    if not ma20_available:
        missing.append("constituent_ma20_state_input_unavailable")
    if item.prior_state is None:
        missing.append("prior_state_unavailable")

    core_failure = any(
        reason in {
            "ranked_sector_count_below_10",
            "ambiguous_sector_identity",
            "dated_membership_unavailable",
            "constituent_return_coverage_unavailable",
            "constituent_return_coverage_below_0.90",
            "r1_cross_section_unavailable",
            "r5_cross_section_unavailable",
            "r20_cross_section_unavailable",
        }
        for reason in missing
    )

    if core_failure:
        state: HotspotState = "insufficient_coverage"
        matched_rule = "priority_1_insufficient_coverage"
    elif _gte(r20_pct, 0.75) and (
        _lt(r1_pct, 0.40) or _lt(item.breadth_up_1, 0.45)
    ) and _gte(item.activity_ratio_20, 1.00):
        state = "high_level_divergence"
        matched_rule = "priority_2_high_level_divergence"
    elif item.prior_state in STRONG_PRIOR_STATES and _lt(r5_pct, 0.50) and _lt(item.breadth_up_1, 0.50):
        state = "cooling"
        matched_rule = "priority_3_cooling"
    elif (
        _gte(r5_pct, 0.70)
        and _gte(r20_pct, 0.65)
        and _gte(item.breadth_up_1, 0.65)
        and _gte(breadth_above_ma20, 0.60)
        and _gte(item.new_high_20_share, 0.10)
    ):
        state = "spreading"
        matched_rule = "priority_4_spreading"
    elif (
        item.prior_state is not None
        and item.prior_state not in STRONG_PRIOR_STATES
        and _gte(r1_pct, 0.80)
        and _gte(r5_pct, 0.70)
        and _lt(r20_pct, 0.60)
        and _gte(item.breadth_up_1, 0.55)
        and _gte(item.activity_ratio_20, 1.20)
    ):
        state = "new"
        matched_rule = "priority_5_new"
    elif (
        _gte(r5_pct, 0.70)
        and _gte(r20_pct, 0.70)
        and _gte(breadth_above_ma20, 0.60)
        and item.strong_rank_sessions_5 is not None
        and item.strong_rank_sessions_5 >= 3
    ):
        state = "persistent_strong"
        matched_rule = "priority_6_persistent_strong"
    elif (
        _gte(r5_pct, 0.70)
        and _gte(r20_pct, 0.50)
        and _gte(item.breadth_up_1, 0.55)
        and (_gte(item.activity_ratio_20, 1.20) or _gte(breadth_above_ma20, 0.55))
    ):
        state = "strengthening"
        matched_rule = "priority_7_strengthening"
    else:
        state = "neutral"
        matched_rule = "priority_8_neutral"

    sector_relative_5 = (
        item.sector_r5 - item.broad_market_benchmark_r5
        if item.sector_r5 is not None and item.broad_market_benchmark_r5 is not None
        else None
    )
    thresholds: tuple[tuple[str, float | int | str], ...] = (
        ("minimum_ranked_sector_count", MINIMUM_RANKED_SECTOR_COUNT),
        ("constituent_return_coverage_min", CONSTITUENT_RETURN_COVERAGE_MIN),
        ("constituent_ma20_coverage_min", CONSTITUENT_MA20_COVERAGE_MIN),
        ("high_level_divergence_r20_pct", 0.75),
        ("new_r1_pct", 0.80),
        ("strong_r5_pct", 0.70),
    )
    return SectorHotspotResult(
        rule_version=SECTOR_RULE_VERSION,
        sector_code=item.sector_code,
        sector_name=item.sector_name,
        taxonomy=item.taxonomy,
        classification_level=item.classification_level,
        sector_r1=item.sector_r1,
        sector_r5=item.sector_r5,
        sector_r20=item.sector_r20,
        sector_relative_5=sector_relative_5,
        r1_pct=r1_pct,
        r5_pct=r5_pct,
        r20_pct=r20_pct,
        breadth_up_1=item.breadth_up_1,
        breadth_above_ma20=breadth_above_ma20,
        activity_ratio_20=item.activity_ratio_20,
        new_high_20_share=item.new_high_20_share,
        representative_positive_share_5=item.representative_positive_share_5,
        constituent_return_coverage=item.constituent_return_coverage,
        constituent_ma20_coverage=item.constituent_ma20_coverage,
        strong_rank_sessions_5=item.strong_rank_sessions_5,
        prior_state=item.prior_state,
        state=state,
        matched_rule=matched_rule,
        dated_membership_revision_id=item.dated_membership_revision_id,
        missing_inputs=tuple(sorted(set(missing))),
        component_thresholds=thresholds,
    )


def _stock_anomalies_for_one(
    item: StockRuleInput,
    *,
    abs_r1_pct: dict[str, float],
    r5_pct: dict[str, float],
    sector_groups: dict[tuple[str, str], list[StockRuleInput]],
) -> tuple[list[StockAnomaly], list[tuple[str, str]]]:
    anomalies: list[StockAnomaly] = []
    unavailable: list[tuple[str, str]] = []

    if not item.return_semantics_valid or item.r1 is None:
        unavailable.append(("large_move", "return_semantics_unavailable"))
    else:
        pct = abs_r1_pct[item.stock_code]
        if abs(item.r1) >= 0.07 or (pct >= 0.975 and abs(item.r1) >= 0.04):
            anomalies.append(
                StockAnomaly(item.stock_code, "large_move", item.r1, ANOMALY_RULE_VERSION, (("abs_return_percentile", pct),))
            )

    if item.volume_current is None or len(item.volume_previous_20) != 20:
        unavailable.append(("unusual_volume", "exact_20_session_volume_window_unavailable"))
    else:
        history = tuple(float(value) for value in item.volume_previous_20)
        baseline = float(median(history))
        if baseline <= 0:
            unavailable.append(("unusual_volume", "volume_baseline_nonpositive"))
        else:
            volume_ratio = float(item.volume_current) / baseline
            if volume_ratio >= 2.00:
                anomalies.append(
                    StockAnomaly(item.stock_code, "unusual_volume", volume_ratio, ANOMALY_RULE_VERSION, (("volume_baseline_20", baseline),))
                )

    if not item.return_semantics_valid or len(item.analysis_closes_60) != 60:
        reason = "return_semantics_unavailable" if not item.return_semantics_valid else "exact_60_session_analysis_close_window_unavailable"
        unavailable.extend((("new_high", reason), ("new_low", reason)))
    else:
        current = item.analysis_closes_60[-1]
        if current >= max(item.analysis_closes_60) - RETURN_EPSILON:
            anomalies.append(StockAnomaly(item.stock_code, "new_high", current, ANOMALY_RULE_VERSION))
        if current <= min(item.analysis_closes_60) + RETURN_EPSILON:
            anomalies.append(StockAnomaly(item.stock_code, "new_low", current, ANOMALY_RULE_VERSION))

    if not item.reference_close_semantics_valid or item.open_current is None or item.reference_close_previous is None:
        unavailable.append(("gap", "reference_close_semantics_unavailable"))
    else:
        gap_return = item.open_current / item.reference_close_previous - 1.0
        if abs(gap_return) >= 0.025:
            anomalies.append(StockAnomaly(item.stock_code, "gap", gap_return, ANOMALY_RULE_VERSION))

    if not item.return_semantics_valid or item.r5 is None or item.broad_market_benchmark_r5 is None:
        unavailable.append(("persistent_relative_strength", "five_session_return_semantics_unavailable"))
    else:
        relative_return_5 = item.r5 - item.broad_market_benchmark_r5
        pct = r5_pct[item.stock_code]
        if relative_return_5 >= 0.05 and pct >= 0.90:
            anomalies.append(
                StockAnomaly(item.stock_code, "persistent_relative_strength", relative_return_5, ANOMALY_RULE_VERSION, (("stock_r5_percentile", pct),))
            )

    if not item.return_semantics_valid:
        unavailable.append(("sector_relative_outlier", "return_semantics_unavailable"))
    elif item.sector_identity_ambiguous:
        unavailable.append(("sector_relative_outlier", "ambiguous_sector_identity"))
    elif not item.sector_code or not item.dated_membership_revision_id:
        unavailable.append(("sector_relative_outlier", "dated_membership_unavailable"))
    elif item.r1 is None:
        unavailable.append(("sector_relative_outlier", "one_session_return_unavailable"))
    else:
        members = sector_groups.get((item.sector_code, item.dated_membership_revision_id), [])
        if len(members) < 10:
            unavailable.append(("sector_relative_outlier", "fewer_than_10_eligible_sector_members"))
        else:
            member_returns = [float(member.r1) for member in members if member.r1 is not None]
            sector_median = float(median(member_returns))
            mad = float(median(abs(value - sector_median) for value in member_returns))
            if mad <= 0:
                unavailable.append(("sector_relative_outlier", "sector_mad_zero"))
            else:
                deviation = item.r1 - sector_median
                robust_z = 0.6745 * deviation / mad
                if abs(deviation) >= 0.04 and abs(robust_z) >= 2.50:
                    anomalies.append(
                        StockAnomaly(
                            item.stock_code,
                            "sector_relative_outlier",
                            deviation,
                            ANOMALY_RULE_VERSION,
                            (("robust_z", robust_z), ("sector_median_r1", sector_median)),
                        )
                    )

    return anomalies, unavailable


def _percentiles(
    values: list[tuple[str, float | None]], *, minimum_count: int
) -> dict[str, float]:
    clean = [(key, float(value)) for key, value in values if value is not None]
    if len(clean) < minimum_count:
        return {}
    ordered = sorted(clean, key=lambda item: (-item[1], item[0]))
    if len(ordered) == 1:
        return {ordered[0][0]: 1.0}
    denominator = len(ordered) - 1
    return {key: 1.0 - index / denominator for index, (key, _) in enumerate(ordered)}


def _validate_sector_input(value: SectorRuleInput) -> None:
    for field_name in (
        "sector_r1",
        "sector_r5",
        "sector_r20",
        "broad_market_benchmark_r5",
        "breadth_up_1",
        "breadth_above_ma20",
        "activity_ratio_20",
        "new_high_20_share",
        "representative_positive_share_5",
    ):
        _finite_optional_checked(getattr(value, field_name), field_name)
    for field_name in (
        "constituent_return_coverage",
        "constituent_ma20_coverage",
        "breadth_up_1",
        "breadth_above_ma20",
        "new_high_20_share",
        "representative_positive_share_5",
    ):
        item = getattr(value, field_name)
        if item is not None and not 0 <= item <= 1:
            raise TodayMarketRuleInputError(f"{field_name} must be within [0, 1]")
    if value.activity_ratio_20 is not None and value.activity_ratio_20 < 0:
        raise TodayMarketRuleInputError("activity_ratio_20 must be nonnegative")
    if value.strong_rank_sessions_5 is not None and not 0 <= value.strong_rank_sessions_5 <= 5:
        raise TodayMarketRuleInputError("strong_rank_sessions_5 must be within [0, 5]")


def _validate_stock_input(value: StockRuleInput) -> None:
    for field_name in (
        "r1",
        "r5",
        "broad_market_benchmark_r5",
        "volume_current",
        "open_current",
        "reference_close_previous",
    ):
        _finite_optional_checked(getattr(value, field_name), field_name)
    if value.volume_current is not None and value.volume_current < 0:
        raise TodayMarketRuleInputError("volume_current must be nonnegative")
    for item in value.volume_previous_20:
        if not isfinite(float(item)) or float(item) < 0:
            raise TodayMarketRuleInputError("volume_previous_20 must contain finite nonnegative values")
    for item in value.analysis_closes_60:
        if not isfinite(float(item)) or float(item) <= 0:
            raise TodayMarketRuleInputError("analysis_closes_60 must contain finite positive values")
    if value.open_current is not None and value.open_current <= 0:
        raise TodayMarketRuleInputError("open_current must be positive")
    if value.reference_close_previous is not None and value.reference_close_previous <= 0:
        raise TodayMarketRuleInputError("reference_close_previous must be positive")


def _finite_required(value: float, field_name: str) -> float:
    converted = float(value)
    if not isfinite(converted):
        raise TodayMarketRuleInputError(f"{field_name} must contain finite values")
    return converted


def _finite_optional_checked(value: float | None, field_name: str) -> float | None:
    if value is None:
        return None
    converted = float(value)
    if not isfinite(converted):
        raise TodayMarketRuleInputError(f"{field_name} must be finite when provided")
    return converted


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise TodayMarketRuleInputError(f"{field_name} must be a non-empty string")


def _gte(value: float | None, threshold: float) -> bool:
    return value is not None and value >= threshold


def _lt(value: float | None, threshold: float) -> bool:
    return value is not None and value < threshold
