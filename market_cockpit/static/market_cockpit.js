"use strict";

function createElement(tagName, text, className) {
  const element = document.createElement(tagName);
  if (className) {
    element.className = className;
  }
  if (text !== undefined && text !== null) {
    element.textContent = String(text);
  }
  return element;
}

function formatValue(value, kind) {
  if (value === null || value === undefined) {
    return "Unavailable";
  }
  if (kind === "percent") {
    const percentValue = Number(value);
    return Number.isFinite(percentValue) ? (percentValue * 100).toFixed(2) + "%" : "Unavailable";
  }
  if (kind === "ratio") {
    const ratioValue = Number(value);
    return Number.isFinite(ratioValue) ? ratioValue.toFixed(3) + "x" : "Unavailable";
  }
  if (typeof value === "number") {
    return Number.isFinite(value) ? Number(value).toFixed(4) : "Unavailable";
  }
  return String(value);
}

function formatLiquidityWindow(window) {
  if (!window) {
    return "Unavailable";
  }
  return String(window.reason) +
    "; matched=" + String(window.matched_cohort_count) +
    "; sessions=" + String(window.observed_session_count) + "/" + String(window.required_session_count) +
    "; unavailable count=" + String(window.unavailable_stock_count) +
    "; sample=" + formatIdentifierSample(
      window.unavailable_stock_codes,
      window.unavailable_stock_codes_truncated,
      window.unavailable_stock_codes_omitted_count
    );
}

function formatIdentifierSample(values, truncated, omittedCount) {
  const sample = (values || []).join(", ") || "None";
  return sample +
    "; truncated=" + String(Boolean(truncated)) +
    "; omitted=" + String(omittedCount || 0) +
    (truncated ? " (+" + String(omittedCount) + " more)" : "");
}

function renderLiquidityContext(payload) {
  const context = payload.liquidity_context;
  const status = document.getElementById("liquidity-status");
  if (!context) {
    status.textContent = "Liquidity context unavailable for this response.";
    renderMetrics(document.getElementById("liquidity-summary"), []);
    renderMetrics(document.getElementById("liquidity-windows"), []);
    renderList(document.getElementById("liquidity-latest-issues"), [], "No liquidity context was returned.");
    renderList(document.getElementById("liquidity-source-exclusions"), [], "No liquidity source-exclusion diagnostics were returned.");
    renderList(document.getElementById("liquidity-warnings"), [], "No liquidity context was returned.");
    return;
  }
  const activity5 = context.activity_5 || {};
  const activity20 = context.activity_20 || {};
  const diagnostics = context.diagnostics || {};
  status.textContent = String(context.interpretation || "Descriptive selected-universe liquidity distribution.");
  renderMetrics(document.getElementById("liquidity-summary"), [
    ["Effective session", context.effective_session],
    ["Requested stocks", context.requested_stock_count],
    ["Latest eligible", context.latest_eligible_count],
    ["Latest unavailable", context.latest_unavailable_count],
    ["Latest total amount", context.latest_total_amount],
    ["Latest median amount", context.latest_median_amount],
    ["Latest aggregate reason", context.latest_aggregate_reason],
    ["Top-5 concentration", context.top5_concentration_share, "percent"],
    ["Top-5 members", context.top5_member_count],
    ["Top-decile concentration", context.top_decile_concentration_share, "percent"],
    ["Top-decile members", context.top_decile_member_count],
    ["Top-decile member sample", formatIdentifierSample(
      context.top_decile_stock_codes,
      context.top_decile_stock_codes_truncated,
      context.top_decile_stock_codes_omitted_count
    )],
    ["Above prior-20 median", context.latest_above_20_session_baseline_share, "percent"],
    ["Above prior-20 count", context.latest_above_20_session_baseline_count],
    ["Calculation status", context.calculation_status],
    ["Amount unit", context.amount_unit]
  ]);
  renderMetrics(document.getElementById("liquidity-windows"), [
    ["5-prior-session activity", activity5.activity_ratio, "ratio"],
    ["5-session matched cohort", activity5.matched_cohort_count],
    ["5-session baseline total", activity5.baseline_total_amount],
    ["5-session diagnostic", formatLiquidityWindow(activity5)],
    ["20-prior-session activity", activity20.activity_ratio, "ratio"],
    ["20-session matched cohort", activity20.matched_cohort_count],
    ["20-session baseline total", activity20.baseline_total_amount],
    ["20-session diagnostic", formatLiquidityWindow(activity20)]
  ]);
  const latestIssueLines = (diagnostics.latest_issues || []).map(function (item) {
      return String(item.stock_code) + ": " + String(item.reason) + "; session=" + String(item.session);
    });
  latestIssueLines.unshift(
    "Latest issue count=" + String(diagnostics.latest_issue_count || 0) +
    "; sample truncated=" + String(Boolean(diagnostics.latest_issues_truncated)) +
    "; omitted=" + String(diagnostics.latest_issues_omitted_count || 0) +
    (diagnostics.latest_issues_truncated ?
      " (+" + String(diagnostics.latest_issues_omitted_count) + " more)." : ".")
  );
  renderList(
    document.getElementById("liquidity-latest-issues"),
    latestIssueLines,
    "No latest-session liquidity eligibility issues."
  );
  renderList(
    document.getElementById("liquidity-source-exclusions"),
    (diagnostics.source_exclusions || []).map(function (item) {
      return String(item.reason) + ": rows=" + String(item.excluded_row_count) +
        "; identifier count=" + String(item.identifier_count) +
        "; sample=" + formatIdentifierSample(
          item.identifiers,
          item.identifiers_truncated,
          item.identifiers_omitted_count
        );
    }),
    "No liquidity source rows were excluded after accepted equity filtering."
  );
  renderList(
    document.getElementById("liquidity-warnings"),
    context.warnings || [],
    "No liquidity availability warnings."
  );
}

function metricCard(label, value, kind) {
  const card = createElement("article", null, "metric-card");
  card.append(
    createElement("p", label, "metric-label"),
    createElement("p", formatValue(value, kind), "metric-value")
  );
  return card;
}

function renderMetrics(container, metrics) {
  container.replaceChildren();
  for (const metric of metrics) {
    container.append(metricCard(metric[0], metric[1], metric[2]));
  }
}

function renderList(container, values, emptyMessage) {
  container.replaceChildren();
  if (!Array.isArray(values) || values.length === 0) {
    container.append(createElement("p", emptyMessage, "empty-state"));
    return;
  }
  const list = document.createElement("ul");
  for (const value of values) {
    list.append(createElement("li", value));
  }
  container.append(list);
}

function renderProvenance(payload) {
  const provenance = payload.provenance || {};
  const rows = [
    ["Series key", provenance.series_key],
    ["Ingestion run", provenance.ingestion_run_id],
    ["Provider", provenance.provider],
    ["Contract / adapter", String(provenance.contract_version || "") + " / " + String(provenance.adapter_version || "")],
    ["Imported UTC", provenance.ingestion_imported_at_utc],
    ["Completed UTC", provenance.ingestion_completed_at_utc],
    ["Collected UTC", provenance.collection_timestamp_utc],
    ["Selected run information cutoff", provenance.information_cutoff_date],
    ["Effective information cutoff", provenance.effective_information_cutoff_date],
    ["Requested historical cutoff", provenance.requested_as_of_cutoff],
    ["Calculated trading session", provenance.effective_as_of_session],
    ["Requested date range", String(provenance.requested_start_date || "") + " to " + String(provenance.requested_end_date || "")],
    ["Adjustment", provenance.adjust_type || "unadjusted"],
    ["AKShare package", provenance.akshare_package_version],
    ["Stock-basic endpoint", provenance.stock_basic_endpoint],
    ["Daily-price endpoint", provenance.daily_price_endpoint],
    ["Trade-calendar endpoint", provenance.trade_calendar_endpoint],
    ["Frequency", provenance.frequency],
    ["Adapter compatibility", provenance.adapter_compatibility_version],
    ["Exact stock codes", (payload.stock_codes || []).join(", ")],
    ["View generated UTC", provenance.generated_at_utc]
  ];
  const container = document.getElementById("provenance");
  container.replaceChildren();
  for (const row of rows) {
    const item = createElement("div", null, "data-row");
    item.append(createElement("dt", row[0]), createElement("dd", row[1]));
    container.append(item);
  }
}

function appendDataRows(container, rows) {
  container.replaceChildren();
  for (const row of rows) {
    const item = createElement("div", null, "data-row");
    item.append(createElement("dt", row[0]), createElement("dd", formatValue(row[1], row[2])));
    container.append(item);
  }
}

function formatBenchmarkWindow(window) {
  if (!window) {
    return "Unavailable";
  }
  return String(window.reason) +
    "; valid=" + String(window.present_valid_session_count) + "/" + String(window.required_session_count) +
    "; range=" + formatValue(window.window_start_session) + " to " + formatValue(window.window_end_session) +
    "; missing=" + String(window.missing_session_count) + " [" + (window.missing_sessions || []).join(", ") + "]" +
    "; invalid=" + String(window.invalid_session_count) + " [" + (window.invalid_sessions || []).join(", ") + "]";
}

function renderBenchmarkContext(payload) {
  const context = payload.benchmark_context;
  const status = document.getElementById("benchmark-status");
  const metricsContainer = document.getElementById("benchmark-metrics");
  if (!context) {
    status.textContent = "Benchmark context unavailable: no explicit benchmark series key was supplied. Equity selected-universe monitoring remains unchanged.";
    renderMetrics(document.getElementById("benchmark-summary"), []);
    metricsContainer.replaceChildren();
    appendDataRows(document.getElementById("benchmark-provenance"), []);
    renderList(document.getElementById("benchmark-warnings"), [], "No benchmark series was requested.");
    return;
  }
  const provenance = context.provenance || {};
  status.textContent = "Showing provider-attributed benchmark index context from one separate complete snapshot. It is not an official exchange statement or a full-market coverage claim.";
  renderMetrics(document.getElementById("benchmark-summary"), [
    ["Requested benchmark codes", context.requested_code_count],
    ["Available benchmark codes", context.available_code_count],
    ["Codes aligned to equity session", context.aligned_code_count],
    ["Overall alignment", context.alignment_status],
    ["Session alignment", context.session_alignment_status],
    ["Cutoff alignment", context.cutoff_alignment_status],
    ["Effective benchmark session", provenance.effective_benchmark_session],
    ["Expected persisted sessions", context.expected_session_count]
  ]);
  metricsContainer.replaceChildren();
  for (const metric of context.metrics || []) {
    const article = createElement("article", null, "benchmark-item");
    article.append(createElement("h3", String(metric.index_code)));
    const list = createElement("dl", null, "data-list");
    appendDataRows(list, [
      ["Latest close", metric.latest_close],
      ["Latest session", metric.latest_session],
      ["Latest return", metric.latest_return, "percent"],
      ["SMA20", metric.sma20],
      ["Above SMA20", metric.above_sma20],
      ["SMA60", metric.sma60],
      ["Above SMA60", metric.above_sma60],
      ["Realized volatility (20)", metric.realized_volatility_20, "percent"],
      ["Maximum drawdown (20)", metric.max_drawdown_20, "percent"],
      ["Available sessions", metric.available_session_count],
      ["Latest-return window", formatBenchmarkWindow(metric.latest_return_window)],
      ["SMA20 window", formatBenchmarkWindow(metric.sma20_window)],
      ["SMA60 window", formatBenchmarkWindow(metric.sma60_window)],
      ["Risk window", formatBenchmarkWindow(metric.risk_window)],
      [
        "Required sessions (return / SMA20 / SMA60 / risk)",
        [
          metric.latest_return_required_sessions,
          metric.sma20_required_sessions,
          metric.sma60_required_sessions,
          metric.risk_required_sessions
        ].join(" / ")
      ]
    ]);
    article.append(list);
    metricsContainer.append(article);
  }
  appendDataRows(document.getElementById("benchmark-provenance"), [
    ["Benchmark series key", provenance.series_key],
    ["Benchmark ingestion run", provenance.ingestion_run_id],
    ["Provider / source", String(provenance.provider || "") + " / " + String(provenance.source || "")],
    ["Endpoint", provenance.endpoint],
    ["Contract / adapter", String(provenance.contract_version || "") + " / " + String(provenance.adapter_version || "")],
    ["Adapter compatibility", provenance.adapter_compatibility_version],
    ["Frequency", provenance.frequency],
    ["Exact codes", (provenance.index_codes || []).join(", ")],
    ["Requested date range", String(provenance.requested_start_date || "") + " to " + String(provenance.requested_end_date || "")],
    ["Requested historical cutoff", provenance.requested_as_of_cutoff],
    ["Equity information cutoff", context.equity_information_cutoff_date],
    ["Benchmark information cutoff", context.benchmark_information_cutoff_date],
    ["Equity effective session", context.equity_effective_session],
    ["Missing exact codes", (context.missing_codes || []).join(", ") || "None"],
    ["Expected-session source", context.expected_session_source],
    ["Expected-session range", String(context.expected_session_start || "") + " to " + String(context.expected_session_end || "")],
    ["Collected UTC", provenance.collection_timestamp_utc],
    ["Imported UTC", provenance.ingestion_imported_at_utc],
    ["Completed UTC", provenance.ingestion_completed_at_utc],
    ["AKShare package", provenance.akshare_package_version],
    ["Network mode", provenance.network_mode],
    ["Timeout seconds", provenance.timeout_seconds],
    ["Max retries", provenance.max_retries],
    ["View generated UTC", provenance.generated_at_utc]
  ]);
  renderList(
    document.getElementById("benchmark-warnings"),
    context.warnings || [],
    "No benchmark alignment or window warnings."
  );
}

function rankedSectorList(title, values) {
  const section = createElement("div");
  section.append(createElement("h4", title));
  const list = document.createElement("ol");
  for (const item of values || []) {
    list.append(createElement(
      "li",
      String(item.sector_code) + " " + String(item.sector_name) + ": " + formatValue(item.value, "percent")
    ));
  }
  if (!values || values.length === 0) {
    section.append(createElement("p", "Unavailable", "empty-state"));
  } else {
    section.append(list);
  }
  return section;
}

function renderSectorContext(payload) {
  const context = payload.sector_context;
  const status = document.getElementById("sector-status");
  const metricsContainer = document.getElementById("sector-metrics");
  const rankings = document.getElementById("sector-rankings");
  if (!context) {
    status.textContent = "Sector context unavailable: no explicit sector series key was supplied. Equity and benchmark monitoring remain unchanged.";
    renderMetrics(document.getElementById("sector-summary"), []);
    renderMetrics(document.getElementById("sector-cross-section"), []);
    rankings.replaceChildren();
    metricsContainer.replaceChildren();
    appendDataRows(document.getElementById("sector-provenance"), []);
    renderList(document.getElementById("sector-warnings"), [], "No sector series was requested.");
    return;
  }
  const provenance = context.provenance || {};
  const cross = context.cross_section || {};
  status.textContent = "Showing provider-attributed selected-sector context from one separate complete snapshot. It is descriptive, non-official, read-only, and non-advisory.";
  renderMetrics(document.getElementById("sector-summary"), [
    ["Requested sectors", context.requested_sector_count],
    ["Available sectors", context.available_sector_count],
    ["Sectors aligned to equity session", context.aligned_sector_count],
    ["Scope coverage", context.coverage_status],
    ["Overall alignment", context.alignment_status],
    ["Session alignment", context.session_alignment_status],
    ["Cutoff alignment", context.cutoff_alignment_status],
    ["Effective sector session", provenance.effective_sector_session],
    ["Expected persisted sessions", context.expected_session_count]
  ]);
  renderMetrics(document.getElementById("sector-cross-section"), [
    ["Valid latest returns", cross.valid_latest_return_count],
    ["Positive latest returns", cross.positive_latest_return_count],
    ["Positive latest-return share", cross.positive_latest_return_share, "percent"],
    ["Valid SMA20 values", cross.valid_sma20_count],
    ["Above SMA20", cross.above_sma20_count],
    ["Above-SMA20 share", cross.above_sma20_share, "percent"]
  ]);
  rankings.replaceChildren(
    rankedSectorList("Top latest-session return", cross.top_latest_return),
    rankedSectorList("Bottom latest-session return", cross.bottom_latest_return),
    rankedSectorList("Top 20-session return", cross.top_return_20),
    rankedSectorList("Bottom 20-session return", cross.bottom_return_20)
  );
  metricsContainer.replaceChildren();
  for (const metric of context.metrics || []) {
    const article = createElement("article", null, "benchmark-item");
    article.append(createElement("h3", String(metric.sector_code) + " " + String(metric.sector_name)));
    const list = createElement("dl", null, "data-list");
    appendDataRows(list, [
      ["Latest close", metric.latest_close],
      ["Latest session", metric.latest_session],
      ["Latest return", metric.latest_return, "percent"],
      ["Five-session return", metric.return_5, "percent"],
      ["Twenty-session return", metric.return_20, "percent"],
      ["SMA20", metric.sma20],
      ["SMA20 distance", metric.sma20_distance, "percent"],
      ["Above SMA20", metric.above_sma20],
      ["Realized volatility (20)", metric.realized_volatility_20, "percent"],
      ["Maximum drawdown (20)", metric.max_drawdown_20, "percent"],
      ["Available sessions", metric.available_session_count],
      ["Latest-return window", formatBenchmarkWindow(metric.latest_return_window)],
      ["Five-session window", formatBenchmarkWindow(metric.return_5_window)],
      ["Twenty-session window", formatBenchmarkWindow(metric.return_20_window)],
      ["SMA20 window", formatBenchmarkWindow(metric.sma20_window)],
      ["Risk window", formatBenchmarkWindow(metric.risk_window)]
    ]);
    article.append(list);
    metricsContainer.append(article);
  }
  appendDataRows(document.getElementById("sector-provenance"), [
    ["Sector series key", provenance.series_key],
    ["Sector ingestion run", provenance.ingestion_run_id],
    ["Provider / source", String(provenance.provider || "") + " / " + String(provenance.source || "")],
    ["Taxonomy endpoint", provenance.taxonomy_endpoint],
    ["History endpoint", provenance.history_endpoint],
    ["Taxonomy", provenance.taxonomy],
    ["Classification level", provenance.classification_level],
    ["Definition / daily contracts", String(provenance.definition_contract_version || "") + " / " + String(provenance.daily_contract_version || "")],
    ["Adapter / compatibility", String(provenance.adapter_version || "") + " / " + String(provenance.adapter_compatibility_version || "")],
    ["Exact stable sector codes", (provenance.sector_codes || []).join(", ")],
    ["Requested date range", String(provenance.requested_start_date || "") + " to " + String(provenance.requested_end_date || "")],
    ["Requested historical cutoff", provenance.requested_as_of_cutoff],
    ["Equity information cutoff", context.equity_information_cutoff_date],
    ["Sector information cutoff", context.sector_information_cutoff_date],
    ["Equity effective session", context.equity_effective_session],
    ["Missing exact sector codes", (context.missing_sector_codes || []).join(", ") || "None"],
    ["Expected-session source", context.expected_session_source],
    ["Expected-session range", String(context.expected_session_start || "") + " to " + String(context.expected_session_end || "")],
    ["Frequency / adjustment", String(provenance.frequency || "") + " / " + (provenance.adjust_type || "unadjusted")],
    ["Collected UTC", provenance.collection_timestamp_utc],
    ["Imported UTC", provenance.ingestion_imported_at_utc],
    ["Completed UTC", provenance.ingestion_completed_at_utc],
    ["AKShare package", provenance.akshare_package_version],
    ["Network mode", provenance.network_mode],
    ["Timeout seconds", provenance.timeout_seconds],
    ["Max retries", provenance.max_retries],
    ["View generated UTC", provenance.generated_at_utc]
  ]);
  renderList(
    document.getElementById("sector-warnings"),
    context.warnings || [],
    "No sector alignment or exact-window warnings."
  );
}

function renderLatestDiagnostics(payload) {
  const diagnostics = payload.latest_data_diagnostics || {};
  renderMetrics(document.getElementById("diagnostic-summary"), [
    ["Current-session stale, invalid, or missing", diagnostics.stale_or_missing_latest_count],
    ["Current-session no-trade", diagnostics.no_trade_latest_count],
    ["Latest-return unavailable", diagnostics.latest_return_unavailable_count]
  ]);
  renderList(
    document.getElementById("latest-return-issues"),
    (diagnostics.latest_return_issues || []).map(function (item) {
      return String(item.stock_code) + ": " + latestReturnReasonLabel(item.reason) +
        "; blocking session=" + formatValue(item.blocking_session) +
        "; last valid traded session=" + formatValue(item.last_valid_traded_session) +
        "; open-session gap=" + formatValue(item.open_session_gap);
    }),
    "No latest-return eligibility issues."
  );
}

function latestReturnReasonLabel(reason) {
  const labels = {
    missing_effective_session_row: "Missing effective-session row",
    invalid_effective_session_row: "Invalid effective-session row",
    no_trade_effective_session_row: "No-trade effective-session row",
    missing_previous_session_row: "Missing previous-session row",
    invalid_previous_session_row: "Invalid previous-session row",
    no_trade_previous_session_row: "No-trade previous-session row"
  };
  return labels[reason] || String(reason || "Unknown latest-return issue");
}

function renderSnapshot(payload) {
  const metrics = payload.metrics || {};
  const latest = metrics.latest_session || {};
  const breadth20 = metrics.breadth_20 || {};
  const breadth60 = metrics.breadth_60 || {};
  const volume = metrics.volume_participation || {};
  const amount = metrics.amount_participation || {};
  const risk = metrics.equal_weight_risk || {};

  renderMetrics(document.getElementById("scope-summary"), [
    ["Universe stocks", payload.universe_stock_count],
    ["Available latest returns", payload.available_stock_count],
    ["Effective session", payload.provenance.effective_as_of_session],
    ["Calculation status", payload.calculation_status],
    ["Scope coverage", payload.scope_coverage_status],
    ["Overall completeness", payload.completeness_status]
  ]);
  renderMetrics(document.getElementById("latest-metrics"), [
    ["Equal-weight mean return", latest.equal_weight_mean_return, "percent"],
    ["Median return", latest.median_return, "percent"],
    ["Advancing", latest.advancing_count],
    ["Declining", latest.declining_count],
    ["Unchanged", latest.unchanged_count],
    ["Unavailable", latest.unavailable_count],
    ["Advance ratio", latest.advance_ratio, "percent"],
    ["Breadth balance", latest.breadth_balance, "percent"],
    ["Return dispersion", latest.return_dispersion, "percent"]
  ]);
  renderMetrics(document.getElementById("window-metrics"), [
    ["Above 20-session SMA", breadth20.above_sma_ratio, "percent"],
    ["20-session new highs", breadth20.new_high_count],
    ["20-session new lows", breadth20.new_low_count],
    ["20-session coverage", breadth20.eligible_stock_count],
    ["Above 60-session SMA", breadth60.above_sma_ratio, "percent"],
    ["60-session new highs", breadth60.new_high_count],
    ["60-session new lows", breadth60.new_low_count],
    ["60-session coverage", breadth60.eligible_stock_count]
  ]);
  renderMetrics(document.getElementById("participation-metrics"), [
    ["Volume participation", volume.ratio_to_prior_20_session_median, "ratio"],
    ["Volume coverage", volume.eligible_stock_count],
    ["Amount participation", amount.ratio_to_prior_20_session_median, "ratio"],
    ["Amount coverage", amount.eligible_stock_count],
    ["Realized volatility (20)", risk.realized_volatility_20, "percent"],
    ["Maximum drawdown (20)", risk.max_drawdown_20, "percent"],
    ["Risk return sessions", risk.eligible_return_sessions]
  ]);
  renderLatestDiagnostics(payload);
  renderLiquidityContext(payload);
  renderProvenance(payload);
  renderBenchmarkContext(payload);
  renderSectorContext(payload);
  renderList(document.getElementById("warnings"), payload.warnings, "No completeness warnings for this snapshot.");
  renderList(
    document.getElementById("unsupported"),
    (payload.unsupported_sections || []).map(function (section) {
      return String(section.label) + ": " + String(section.reason);
    }),
    "No unsupported-section metadata is available."
  );
  document.getElementById("research-disclaimer").textContent = payload.disclaimer;
  document.getElementById("scope-coverage-note").textContent = payload.scope_coverage_note;
  const badge = document.getElementById("completeness-badge");
  badge.textContent = payload.completeness_status;
  badge.className = "badge badge-" + payload.completeness_status;
}

async function loadMarketCockpit() {
  const status = document.getElementById("load-status");
  const error = document.getElementById("load-error");
  const params = new URLSearchParams(window.location.search);
  const seriesKey = params.get("series_key");
  if (!seriesKey) {
    status.textContent = "No series selected.";
    error.textContent = "Open this page with ?series_key=<64-character equity series key>, optional &benchmark_series_key=<64-character benchmark series key>, optional &sector_series_key=<64-character sector series key>, and optional &as_of_cutoff=YYYYMMDD.";
    error.hidden = false;
    return;
  }
  const apiParams = new URLSearchParams({ series_key: seriesKey });
  const cutoff = params.get("as_of_cutoff");
  if (cutoff) {
    apiParams.set("as_of_cutoff", cutoff);
  }
  const benchmarkSeriesKey = params.get("benchmark_series_key");
  if (benchmarkSeriesKey) {
    apiParams.set("benchmark_series_key", benchmarkSeriesKey);
  }
  const sectorSeriesKey = params.get("sector_series_key");
  if (sectorSeriesKey) {
    apiParams.set("sector_series_key", sectorSeriesKey);
  }
  try {
    const response = await fetch("/market-cockpit/snapshot?" + apiParams.toString(), {
      headers: { Accept: "application/json" }
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Market Cockpit data is unavailable.");
    }
    renderSnapshot(payload);
    status.textContent = "Showing one persisted selected-universe snapshot. Read-only; no automatic refresh.";
  } catch (loadError) {
    status.textContent = "Market Cockpit data is unavailable.";
    error.textContent = String(loadError.message || loadError);
    error.hidden = false;
  }
}

loadMarketCockpit();
