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

function renderEmpty(container, message) {
  container.replaceChildren(createElement("p", message, "empty-state"));
}

function renderMetricCards(container, metrics) {
  container.replaceChildren();
  if (!Array.isArray(metrics) || metrics.length === 0) {
    renderEmpty(container, "No local fixture data is available for this section.");
    return;
  }
  for (const metric of metrics) {
    const card = createElement("article", null, "metric-card");
    card.append(
      createElement("p", metric.label, "metric-label"),
      createElement("p", metric.value, "metric-value")
    );
    container.append(card);
  }
}

function renderTable(container, section) {
  container.replaceChildren();
  const columns = Array.isArray(section.columns) ? section.columns : [];
  const rows = Array.isArray(section.rows) ? section.rows : [];
  if (columns.length === 0 || rows.length === 0) {
    renderEmpty(container, "No local fixture rows are available for this table.");
    return;
  }

  const wrapper = createElement("div", null, "table-wrap");
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  const tbody = document.createElement("tbody");

  for (const column of columns) {
    const header = createElement("th", column);
    header.scope = "col";
    headerRow.append(header);
  }
  thead.append(headerRow);

  for (const row of rows) {
    const tableRow = document.createElement("tr");
    for (const column of columns) {
      tableRow.append(createElement("td", row[column]));
    }
    tbody.append(tableRow);
  }
  table.append(thead, tbody);
  wrapper.append(table);
  container.append(wrapper);
}

function renderList(container, title, values) {
  const block = createElement("section", null, "content-block");
  block.append(createElement("h3", title));
  if (!Array.isArray(values) || values.length === 0) {
    block.append(createElement("p", "No local fixture data is available."));
  } else {
    const list = document.createElement("ul");
    for (const value of values) {
      list.append(createElement("li", value));
    }
    block.append(list);
  }
  container.append(block);
}

function renderReport(container, report) {
  container.replaceChildren();
  if (!report || (!report.title && !report.summary)) {
    renderEmpty(container, "No local fixture report is available.");
    return;
  }
  const block = createElement("article", null, "content-block");
  block.append(createElement("h3", report.title), createElement("p", report.summary));
  container.append(block);
}

function renderOverview(overview) {
  const sections = overview.sections || {};
  const project = sections.project_overview || {};
  renderMetricCards(document.getElementById("project-status"), project.metrics);
  renderTable(document.getElementById("factor-summary"), sections.factor_summary || {});
  renderMetricCards(document.getElementById("backtest-summary"), (sections.backtest_summary || {}).metrics);
  renderTable(document.getElementById("ml-summary"), sections.ml_summary || {});
  document.getElementById("research-disclaimer").textContent = overview.disclaimer || "Research-only disclaimer is unavailable.";
  renderSources(document.getElementById("source-references"), overview.source_refs);
}

function renderReportPayload(report) {
  const sections = report.sections || {};
  renderReport(document.getElementById("research-report"), sections.research_report_summary);

  const highlights = document.getElementById("report-highlights");
  highlights.replaceChildren();
  renderList(highlights, "Factor highlights", sections.factor_highlights);
  renderList(highlights, "Backtest highlights", sections.backtest_highlights);
  renderList(highlights, "ML highlights", sections.ml_highlights);

  const riskSection = sections.risk_and_disclaimer || {};
  const risks = document.getElementById("research-risks");
  risks.replaceChildren();
  renderList(risks, "Risks", riskSection.risks);
  renderList(risks, "Limitations", riskSection.limitations);
}

function renderSources(container, sources) {
  container.replaceChildren();
  if (!Array.isArray(sources) || sources.length === 0) {
    renderEmpty(container, "No local fixture source references are available.");
    return;
  }
  const list = document.createElement("ul");
  for (const source of sources) {
    list.append(createElement("li", source));
  }
  container.append(list);
}

async function fetchJson(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error("The local dashboard data could not be loaded.");
  }
  return response.json();
}

async function loadDashboard() {
  const status = document.getElementById("load-status");
  const error = document.getElementById("load-error");
  try {
    const results = await Promise.all([
      fetchJson("/dashboard/overview"),
      fetchJson("/dashboard/report")
    ]);
    renderOverview(results[0]);
    renderReportPayload(results[1]);
    status.textContent = "Showing local fixture/sample research data. Read-only; no live market data.";
  } catch (loadError) {
    error.textContent = "Unable to load the local dashboard data. The raw JSON links remain available for inspection.";
    error.hidden = false;
    status.textContent = "Local dashboard data is unavailable.";
  }
}

loadDashboard();
