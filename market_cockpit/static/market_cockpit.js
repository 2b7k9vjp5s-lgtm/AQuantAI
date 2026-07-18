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
    return (Number(value) * 100).toFixed(2) + "%";
  }
  if (kind === "ratio") {
    return Number(value).toFixed(3) + "x";
  }
  if (typeof value === "number") {
    return Number(value).toFixed(4);
  }
  return String(value);
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
    ["Information cutoff", provenance.information_cutoff_date],
    ["As-of trading session", provenance.effective_as_of_session],
    ["Requested date range", String(provenance.requested_start_date || "") + " to " + String(provenance.requested_end_date || "")],
    ["Adjustment", provenance.adjust_type || "unadjusted"],
    ["Exact stock codes", (payload.stock_codes || []).join(", ")],
    ["Generated UTC", provenance.generated_at_utc]
  ];
  const container = document.getElementById("provenance");
  container.replaceChildren();
  for (const row of rows) {
    const item = createElement("div", null, "data-row");
    item.append(createElement("dt", row[0]), createElement("dd", row[1]));
    container.append(item);
  }
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
    ["Completeness", payload.completeness_status]
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
  renderProvenance(payload);
  renderList(document.getElementById("warnings"), payload.warnings, "No completeness warnings for this snapshot.");
  renderList(
    document.getElementById("unsupported"),
    (payload.unsupported_sections || []).map(function (section) {
      return String(section.label) + ": " + String(section.reason);
    }),
    "No unsupported-section metadata is available."
  );
  document.getElementById("research-disclaimer").textContent = payload.disclaimer;
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
    error.textContent = "Open this page with ?series_key=<64-character series key> and optional &as_of_cutoff=YYYYMMDD.";
    error.hidden = false;
    return;
  }
  const apiParams = new URLSearchParams({ series_key: seriesKey });
  const cutoff = params.get("as_of_cutoff");
  if (cutoff) {
    apiParams.set("as_of_cutoff", cutoff);
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
