"use strict";

const form = document.getElementById("comparison-form");
const poolInput = document.getElementById("pool-revision-id");
const cutoffInput = document.getElementById("as-of-cutoff");
const recordedInput = document.getElementById("as-of-recorded");
const statusNode = document.getElementById("status");
const universePanel = document.getElementById("universe-panel");
const universeSummary = document.getElementById("universe-summary");
const matrixPanel = document.getElementById("matrix-panel");
const matrixBody = document.getElementById("matrix-body");
const submitButton = form.querySelector("button[type='submit']");

const urlParams = new URLSearchParams(window.location.search);
poolInput.value = urlParams.get("candidate_pool_revision_id") || "";
cutoffInput.value = urlParams.get("as_of_cutoff") || "";
recordedInput.value = urlParams.get("as_of_recorded_at_utc") || "";

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const poolRevisionId = poolInput.value.trim();
  const cutoff = cutoffInput.value;
  const recordedAt = recordedInput.value.trim();

  setStatus("正在读取冻结候选池与研究组件……", "loading");
  submitButton.disabled = true;
  universePanel.hidden = true;
  matrixPanel.hidden = true;
  universeSummary.replaceChildren();
  matrixBody.replaceChildren();

  try {
    const query = new URLSearchParams({
      as_of_cutoff: cutoff,
      as_of_recorded_at_utc: recordedAt,
    });
    const response = await fetch(
      `/company-comparison/candidate-pool-revisions/${encodeURIComponent(poolRevisionId)}?${query.toString()}`,
      { headers: { Accept: "application/json" } },
    );
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(publicErrorMessage(payload, response.status));
    }
    renderUniverse(payload.universe, payload.selector, payload.query_count);
    renderRows(payload.rows || []);
    updateLocation(payload.selector);
    universePanel.hidden = false;
    matrixPanel.hidden = false;
    setStatus(`已读取 ${payload.rows.length} 个候选池成员。`, "success");
  } catch (error) {
    const message = error instanceof Error ? error.message : "读取失败，请检查选择条件。";
    setStatus(message, "error");
  } finally {
    submitButton.disabled = false;
  }
});

function setStatus(message, kind) {
  statusNode.textContent = message;
  statusNode.dataset.kind = kind;
}

function publicErrorMessage(payload, status) {
  const detail = payload && payload.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (detail && typeof detail.message === "string") {
    return detail.message;
  }
  if (status === 422) {
    return "选择条件无效。请确认 UUID、日期和 UTC 时间格式。";
  }
  if (status === 409) {
    return "冻结研究边界不一致，系统已停止生成对比矩阵。";
  }
  return "读取失败，请检查本地数据库配置与记录边界。";
}

function updateLocation(selector) {
  const next = new URL(window.location.href);
  next.searchParams.set("candidate_pool_revision_id", selector.candidate_pool_revision_id);
  next.searchParams.set("as_of_cutoff", selector.as_of_cutoff);
  next.searchParams.set("as_of_recorded_at_utc", selector.as_of_recorded_at_utc);
  window.history.replaceState(null, "", next);
}

function renderUniverse(universe, selector, queryCount) {
  const entries = [
    ["候选池标题", universe.title],
    ["候选池范围", universe.scope],
    ["成员数量", String(universe.member_count)],
    ["候选池修订", `r${universe.candidate_pool_revision_no}`],
    ["候选池修订 ID", universe.candidate_pool_revision_id],
    ["行业地图", universe.map_title],
    ["地图修订", `r${universe.map_revision_no}`],
    ["信息截止日", selector.as_of_cutoff],
    ["记录时间上限", selector.as_of_recorded_at_utc],
    ["集合查询数量", String(queryCount)],
  ];
  universeSummary.replaceChildren(...entries.map(([label, value]) => summaryItem(label, value)));
}

function summaryItem(label, value) {
  const wrapper = element("div", "summary-item");
  const term = document.createElement("dt");
  term.textContent = label;
  const description = document.createElement("dd");
  description.textContent = value || "—";
  wrapper.append(term, description);
  return wrapper;
}

function renderRows(rows) {
  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 9;
    td.className = "empty-value";
    td.textContent = "所选候选池修订没有可展示的成员。";
    tr.append(td);
    matrixBody.replaceChildren(tr);
    return;
  }
  matrixBody.replaceChildren(...rows.map(renderRow));
}

function renderRow(row) {
  const tr = document.createElement("tr");
  tr.append(
    cell(identityBlock(row.identity)),
    cell(stage1Block(row.legacy_stage1)),
    cell(typedSemanticsBlock(row.typed_semantics)),
    cell(companyResearchBlock(row.company_research)),
    cell(componentBlock(row.company_research.components.hypotheses, "财务假设")),
    cell(expectationValuationBlock(row.company_research.components)),
    cell(catalystRiskBlock(row.company_research.components)),
    cell(judgmentsBlock(row.company_research.components)),
    cell(detailBlock(row.detail_routes)),
  );
  return tr;
}

function cell(content) {
  const td = document.createElement("td");
  td.append(content);
  return td;
}

function identityBlock(identity) {
  const stack = element("div", "cell-stack");
  stack.append(
    textNode(identity.stock_name || identity.stock_code, "primary-value"),
    textNode(`${identity.source} · ${identity.stock_code}`, "secondary-value"),
    textNode(`beneficiary ${identity.beneficiary_id}`, "id-value"),
    textNode(`membership ${identity.candidate_pool_membership_id}`, "id-value"),
  );
  return stack;
}

function stage1Block(stage1) {
  const stack = element("div", "cell-stack");
  stack.append(
    valueChip(`类型：${stage1.beneficiary_kind}`),
    stateChip(stage1.assessment_status, stage1.assessment_status),
    textNode(`修订 r${stage1.revision_no}`, "secondary-value"),
    textNode(stage1.information_cutoff_date, "secondary-value"),
  );
  return stack;
}

function typedSemanticsBlock(semantics) {
  const stack = element("div", "cell-stack");
  stack.append(stateChip(semantics.state, stateLabel(semantics.state)));
  if (!semantics.profile_revision) {
    stack.append(textNode("没有匹配冻结受益修订的类型化语义。", "empty-value"));
    return stack;
  }
  stack.append(
    textNode(`语义修订 r${semantics.profile_revision.revision_no}`, "secondary-value"),
    valueChip(`总体：${semantics.profile_revision.overall_status}`),
  );
  const assertions = semantics.assertions || {};
  for (const field of ["exposure", "driver", "offering", "customer", "certification", "capacity", "production", "order"]) {
    const values = assertions[field] || [];
    if (!values.length) {
      continue;
    }
    const group = element("div", "chip-group");
    group.append(textNode(`${fieldLabel(field)}：`, "secondary-value"));
    for (const item of values) {
      group.append(valueChip(`${item.state_code} · ${item.evidence_state}`));
    }
    stack.append(group);
  }
  return stack;
}

function companyResearchBlock(research) {
  const stack = element("div", "cell-stack");
  stack.append(stateChip(research.state, stateLabel(research.state)));
  if (!research.latest_revision) {
    stack.append(textNode("当前边界下没有可见公司研究修订。", "empty-value"));
    return stack;
  }
  stack.append(
    valueChip(`流程：${research.latest_revision.workflow_state}`),
    valueChip(`结论：${research.latest_revision.conclusion_status}`),
    textNode(`修订 r${research.latest_revision.revision_no}`, "secondary-value"),
    textNode(research.latest_revision.information_cutoff_date, "secondary-value"),
  );
  return stack;
}

function componentBlock(component, label) {
  const stack = element("div", "cell-stack");
  stack.append(stateChip(component.state, stateLabel(component.state)));
  if (!component.items.length) {
    stack.append(textNode(`${label}缺失`, "empty-value"));
    return stack;
  }
  for (const item of component.items) {
    const parts = [item.item_key, item.hypothesis_status, item.direction, item.confidence].filter(Boolean);
    stack.append(valueChip(parts.join(" · ")));
  }
  return stack;
}

function expectationValuationBlock(components) {
  const stack = element("div", "cell-stack");
  stack.append(textNode("预期", "primary-value"));
  appendItems(stack, components.expectations, ["item_key", "direction", "status", "confidence"]);
  stack.append(textNode("估值语境", "primary-value"));
  appendItems(stack, components.valuation_contexts, ["valuation_method", "metric_context", "status", "confidence"]);
  return stack;
}

function catalystRiskBlock(components) {
  const stack = element("div", "cell-stack");
  stack.append(textNode("催化剂", "primary-value"));
  appendItems(stack, components.catalysts, ["subject", "status", "confidence"]);
  stack.append(textNode("风险", "primary-value"));
  appendItems(stack, components.risks, ["subject", "status", "confidence"]);
  return stack;
}

function judgmentsBlock(components) {
  const stack = element("div", "cell-stack");
  stack.append(textNode("行业判断", "primary-value"));
  appendItems(stack, components.industry_judgments, ["outcome", "evidence_state", "confidence"]);
  stack.append(textNode("公司判断", "primary-value"));
  appendItems(stack, components.company_judgments, ["outcome", "evidence_state", "confidence"]);
  return stack;
}

function appendItems(stack, component, fields) {
  stack.append(stateChip(component.state, stateLabel(component.state)));
  if (!component.items.length) {
    stack.append(textNode("没有可见记录", "empty-value"));
    return;
  }
  for (const item of component.items) {
    stack.append(valueChip(fields.map((field) => item[field]).filter(Boolean).join(" · ")));
  }
}

function detailBlock(routes) {
  const links = element("div", "detail-links");
  if (routes.company_research_page) {
    links.append(anchor(routes.company_research_page, "打开公司研究"));
  } else {
    links.append(textNode("公司研究缺失", "empty-value"));
  }
  links.append(anchor(routes.beneficiary_semantics_api, "查看类型化语义 JSON"));
  return links;
}

function anchor(href, label) {
  const link = document.createElement("a");
  link.className = "detail-link";
  link.href = href;
  link.textContent = label;
  return link;
}

function stateChip(state, label) {
  const chip = element("span", "state-chip");
  chip.dataset.state = state;
  chip.textContent = label;
  return chip;
}

function valueChip(value) {
  const chip = element("span", "value-chip");
  chip.textContent = value || "—";
  return chip;
}

function textNode(value, className) {
  const node = element("span", className);
  node.textContent = value || "—";
  return node;
}

function element(tagName, className) {
  const node = document.createElement(tagName);
  if (className) {
    node.className = className;
  }
  return node;
}

function stateLabel(state) {
  const labels = {
    available: "可用",
    missing: "缺失",
    missing_at_as_of: "截止边界内缺失",
    historical_mismatch: "冻结版本不匹配",
    disputed: "存在争议",
    not_applicable: "不适用",
  };
  return labels[state] || state;
}

function fieldLabel(field) {
  const labels = {
    exposure: "受益暴露",
    driver: "产业驱动",
    offering: "产品/能力",
    customer: "客户阶段",
    certification: "认证阶段",
    capacity: "产能阶段",
    production: "生产阶段",
    order: "订单阶段",
  };
  return labels[field] || field;
}
