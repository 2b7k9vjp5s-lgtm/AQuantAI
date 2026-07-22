"use strict";

const endpoints = {
  observation: {
    input: "observationId",
    output: "observationOutput",
    path: "financial-observation-revisions",
    title: "结构化财务观察",
  },
  metric: {
    input: "metricId",
    output: "metricOutput",
    path: "metric-revisions",
    title: "标准化估值指标",
  },
  comparison: {
    input: "comparisonId",
    output: "comparisonOutput",
    path: "comparison-set-revisions",
    title: "历史或同业比较上下文",
  },
  gap: {
    input: "gapId",
    output: "gapOutput",
    path: "expectation-gap-revisions",
    title: "标准化预期差",
  },
};

function text(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.join("、") : "—";
  return String(value);
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function row(label, value) {
  const wrapper = document.createElement("div");
  wrapper.className = "data-item";
  const heading = document.createElement("strong");
  heading.textContent = label;
  const content = document.createElement("span");
  content.textContent = text(value);
  wrapper.append(heading, content);
  return wrapper;
}

function grid(entries) {
  const wrapper = document.createElement("div");
  wrapper.className = "data-grid";
  entries.forEach(([label, value]) => wrapper.appendChild(row(label, value)));
  return wrapper;
}

function table(headers, rows) {
  const wrapper = document.createElement("div");
  wrapper.className = "table-wrap";
  const element = document.createElement("table");
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  headers.forEach((header) => {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = header;
    headRow.appendChild(cell);
  });
  head.appendChild(headRow);
  const body = document.createElement("tbody");
  rows.forEach((values) => {
    const bodyRow = document.createElement("tr");
    values.forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = text(value);
      bodyRow.appendChild(cell);
    });
    body.appendChild(bodyRow);
  });
  element.append(head, body);
  wrapper.appendChild(element);
  return wrapper;
}

function renderObservation(output, data) {
  output.appendChild(grid([
    ["指标", data.metric_code],
    ["来源类型", data.source_kind],
    ["状态", data.observation_state],
    ["标准化数值", data.standardized_value_text],
    ["币种 / 单位", `${text(data.currency_code)} / ${text(data.unit_code)}`],
    ["目标期间", data.target_period_key],
    ["期间口径", data.period_basis],
    ["会计口径", data.accounting_scope],
    ["期间结束", data.period_end_date],
    ["观察日期", data.observation_as_of_date],
    ["公司研究修订", data.company_research_revision_id],
    ["证券修订", data.instrument_revision_id],
    ["信息截止", data.information_cutoff_date],
    ["记录时间", data.recorded_at_utc],
  ]));
  const note = document.createElement("p");
  note.textContent = `理由：${text(data.rationale)}；证伪条件：${text(data.falsification_condition)}`;
  output.appendChild(note);
  output.appendChild(table(
    ["位置", "Claim 修订", "证据链接", "Evidence"],
    (data.evidence_links || []).map((item) => [
      item.position,
      item.claim_revision_id,
      item.claim_evidence_link_id,
      item.evidence_id,
    ]),
  ));
}

function renderMetric(output, data) {
  output.appendChild(grid([
    ["指标", data.metric_code],
    ["计算状态", data.calculation_state],
    ["标准化结果", data.normalized_value_text],
    ["输出单位", data.output_unit_code],
    ["股权价值", data.equity_value_text],
    ["企业价值", data.enterprise_value_text],
    ["币种", data.currency_code],
    ["估值日", data.valuation_as_of_date],
    ["价格交易日", data.price_trade_date],
    ["财务期间结束", data.financial_period_end_date],
    ["公式版本", data.formula_version],
    ["原因代码", data.reason_codes],
    ["信息截止", data.information_cutoff_date],
    ["记录时间", data.recorded_at_utc],
  ]));
  output.appendChild(table(
    ["位置", "输入角色", "目标字段", "精确修订 ID"],
    (data.inputs || []).map((item) => [
      item.position,
      item.input_role,
      item.target_field,
      item.revision_id,
    ]),
  ));
}

function renderComparison(output, data) {
  output.appendChild(grid([
    ["比较类型", data.comparison_kind],
    ["比较状态", data.comparison_state],
    ["指标", data.metric_code],
    ["目标期间", data.target_period_key],
    ["规则版本", data.rule_version],
    ["成员总数", data.total_member_count],
    ["可计算成员", data.eligible_member_count],
    ["保留但排除成员", data.excluded_member_count],
    ["最小 / 中位 / 最大", `${text(data.minimum_value_text)} / ${text(data.median_value_text)} / ${text(data.maximum_value_text)}`],
    ["主体百分位", data.subject_percentile_text],
    ["集合理由", data.rationale],
    ["信息截止", data.information_cutoff_date],
    ["记录时间", data.recorded_at_utc],
  ]));
  output.appendChild(table(
    ["位置", "成员", "主体", "资格", "数值", "估值日", "原因代码"],
    (data.members || []).map((item) => [
      item.position,
      item.member_key,
      item.is_subject ? "是" : "否",
      item.eligibility_state,
      item.normalized_value_text,
      item.valuation_date,
      item.reason_codes,
    ]),
  ));
}

function renderGap(output, data) {
  output.appendChild(grid([
    ["指标", data.metric_code],
    ["目标期间", data.target_period_key],
    ["预期来源", data.expected_source_kind],
    ["差异状态", data.gap_state],
    ["绝对差", data.absolute_gap_text],
    ["百分比差", data.percentage_gap_text],
    ["方向", data.direction],
    ["预期观察修订", data.expected_observation_revision_id],
    ["实际观察修订", data.actual_observation_revision_id],
    ["规则版本", data.rule_version],
    ["原因代码", data.reason_codes],
    ["计算日期", data.calculation_as_of_date],
    ["信息截止", data.information_cutoff_date],
    ["记录时间", data.recorded_at_utc],
  ]));
}

function render(kind, data) {
  const output = document.getElementById(endpoints[kind].output);
  clear(output);
  if (kind === "observation") renderObservation(output, data);
  if (kind === "metric") renderMetric(output, data);
  if (kind === "comparison") renderComparison(output, data);
  if (kind === "gap") renderGap(output, data);
}

async function load(kind) {
  const status = document.getElementById("globalStatus");
  const revisionId = document.getElementById(endpoints[kind].input).value.trim();
  const cutoff = document.getElementById("cutoffInput").value;
  const recorded = document.getElementById("recordedInput").value.trim();
  if (!revisionId || !cutoff || !recorded) {
    status.textContent = "必须明确填写修订 ID、信息截止日和 UTC 记录时间。";
    return;
  }
  const params = new URLSearchParams({
    as_of_cutoff: cutoff,
    as_of_recorded_at_utc: recorded,
  });
  status.textContent = `正在读取${endpoints[kind].title}……`;
  try {
    const response = await fetch(
      `/normalized-valuation/${endpoints[kind].path}/${encodeURIComponent(revisionId)}?${params.toString()}`,
      { headers: { Accept: "application/json" } },
    );
    const payload = await response.json();
    if (!response.ok) {
      const detail = payload.detail || payload;
      throw new Error(detail.message || detail.code || `HTTP ${response.status}`);
    }
    const expectedResearch = document.getElementById("companyResearchId").value.trim();
    if (expectedResearch && payload.company_research_id && payload.company_research_id !== expectedResearch) {
      throw new Error("返回记录不属于页面中明确填写的 company_research_id。没有自动替换记录。");
    }
    render(kind, payload);
    status.textContent = `${endpoints[kind].title}读取完成。`;
  } catch (error) {
    const output = document.getElementById(endpoints[kind].output);
    clear(output);
    const message = document.createElement("p");
    message.textContent = `读取失败：${error instanceof Error ? error.message : "未知错误"}`;
    output.appendChild(message);
    status.textContent = "读取失败；页面不会自动回退到其他记录。";
  }
}

document.querySelectorAll("button[data-kind]").forEach((button) => {
  button.addEventListener("click", () => load(button.dataset.kind));
});
