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
    renderEmpty(container, "本区块暂无本地样例数据。");
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
    renderEmpty(container, "本表暂无本地样例数据行。");
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
    block.append(createElement("p", "暂无本地样例数据。"));
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
    renderEmpty(container, "暂无本地样例研究报告。");
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
  document.getElementById("research-disclaimer").textContent = overview.disclaimer || "暂无研究免责声明。";
  renderSources(document.getElementById("source-references"), overview.source_refs);
}

function renderReportPayload(report) {
  const sections = report.sections || {};
  renderReport(document.getElementById("research-report"), sections.research_report_summary);

  const highlights = document.getElementById("report-highlights");
  highlights.replaceChildren();
  renderList(highlights, "因子重点", sections.factor_highlights);
  renderList(highlights, "回测重点", sections.backtest_highlights);
  renderList(highlights, "机器学习重点", sections.ml_highlights);

  const riskSection = sections.risk_and_disclaimer || {};
  const risks = document.getElementById("research-risks");
  risks.replaceChildren();
  renderList(risks, "风险", riskSection.risks);
  renderList(risks, "限制", riskSection.limitations);
}

function renderSources(container, sources) {
  container.replaceChildren();
  if (!Array.isArray(sources) || sources.length === 0) {
    renderEmpty(container, "暂无本地样例来源引用。");
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
    throw new Error("无法加载本地看板数据。");
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
    status.textContent = "正在显示本地固定样例研究数据。页面只读，不含实时市场数据。";
  } catch (loadError) {
    error.textContent = "无法加载本地看板数据，仍可通过上方原始 JSON 链接检查响应。";
    error.hidden = false;
    status.textContent = "本地看板数据不可用。";
  }
}

loadDashboard();
