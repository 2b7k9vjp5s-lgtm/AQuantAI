"use strict";

const routeMatch = window.location.pathname.match(
  /^\/industry-analysis\/sessions\/([0-9a-f-]+)\/revisions\/([0-9a-f-]+)\/result$/i,
);
const route = routeMatch
  ? { sessionId: routeMatch[1], reviewedSessionRevisionId: routeMatch[2] }
  : null;
const query = new URLSearchParams(window.location.search);
const boundary = {
  cutoff: query.get("as_of_cutoff"),
  recordedAtUtc: query.get("as_of_recorded_at_utc"),
};

function node(tag, value, className) {
  const element = document.createElement(tag);
  if (value !== undefined && value !== null) element.textContent = String(value);
  if (className) element.className = className;
  return element;
}

function setStatus(message, kind = "") {
  const element = document.querySelector("#result-status");
  element.textContent = message;
  element.className = `status-message${kind ? ` is-${kind}` : ""}`;
}

async function readJson(response) {
  let payload = null;
  try {
    payload = await response.json();
  } catch (_error) {
    payload = null;
  }
  if (response.ok) return payload;
  const detail = payload && payload.detail;
  const error = new Error(
    detail && typeof detail === "object"
      ? detail.message || detail.technical_message
      : detail || `请求失败（${response.status}）`,
  );
  error.status = response.status;
  error.code = detail && typeof detail === "object" ? detail.code : null;
  throw error;
}

function summaryItem(label, value) {
  const item = node("div", null, "summary-item");
  item.append(node("strong", label), node("span", value || "未提供"));
  return item;
}

function resultCell(label, value, detail = "") {
  const item = node("div", null, "result-cell");
  item.append(node("strong", label), node("span", value || "未提供"));
  if (detail) item.append(node("small", detail));
  return item;
}

function reviewText(value, fallback) {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function resultCard(candidate, index) {
  const card = node("article", null, "result-card");
  const header = node("header");
  const title = node("div", null, "result-card-title");
  title.append(node("strong", candidate.company_label_original));
  title.append(node("small", `${candidate.source_label} · 精确路径 ${index + 1}`));
  header.append(title, node("span", candidate.decision_label, "meta-chip"));

  const grid = node("div", null, "result-card-grid");
  grid.append(
    resultCell("审阅状态", candidate.decision_label, candidate.review_state),
    resultCell("最终受益类型", candidate.exposure_label, candidate.proposed_exposure_type),
    resultCell("精确身份", candidate.identity_state),
    resultCell("来源", candidate.source_label, candidate.source_kind),
    resultCell("受益路径", candidate.benefit_path_text),
    resultCell("原候选置信度", candidate.proposal_confidence),
  );

  const rationale = candidate.rationale || {};
  const uncertainty = candidate.uncertainty || {};
  const copy = node("div", null, "review-copy");
  const rationaleBox = node("article");
  rationaleBox.append(
    node("h3", "审阅理由"),
    node("p", reviewText(rationale.user_review_rationale, "未提供审阅理由")),
  );
  const uncertaintyBox = node("article");
  uncertaintyBox.append(
    node("h3", `不确定性 · ${reviewText(uncertainty.state, "未标记")}`),
    node("p", reviewText(uncertainty.note, "未提供不确定性说明")),
  );
  copy.append(rationaleBox, uncertaintyBox);

  const details = document.createElement("details");
  details.append(node("summary", "来源与技术详情"));
  details.append(node("pre", JSON.stringify({
    candidate_id: candidate.candidate_id,
    candidate_revision_id: candidate.candidate_revision_id,
    revision_number: candidate.revision_number,
    source_kind: candidate.source_kind,
    source_reference: candidate.source_reference,
    proposed_stock_basic_record_id: candidate.proposed_stock_basic_record_id,
    proposed_listed_instrument_id: candidate.proposed_listed_instrument_id,
    manifest_fingerprint_sha256: candidate.manifest_fingerprint_sha256,
    recorded_at_utc: candidate.recorded_at_utc,
  }, null, 2), "json-block"));
  card.append(header, grid, copy, details);
  return card;
}

function renderGroup(selector, countSelector, candidates, emptyText) {
  const container = document.querySelector(selector);
  container.replaceChildren();
  document.querySelector(countSelector).textContent = String(candidates.length);
  if (!candidates.length) {
    container.append(node("p", emptyText, "result-empty"));
    return;
  }
  candidates.forEach((candidate, index) => container.append(resultCard(candidate, index)));
}

function renderResult(result) {
  document.querySelector("#result-title").textContent = result.thesis_title;
  document.querySelector("#result-thesis").textContent = result.thesis_text_original;
  document.querySelector("#ownership-notice").textContent = result.ownership_notice;
  document.querySelector("#result-summary").replaceChildren(
    summaryItem("工作流状态", result.workflow_state),
    summaryItem("覆盖状态", result.coverage_state),
    summaryItem("候选总数", result.candidate_count),
    summaryItem("纳入后续研究", result.selected_count),
    summaryItem("待确认", result.unresolved_count),
    summaryItem("暂不纳入", result.rejected_count),
    summaryItem("信息截止", result.information_cutoff_date),
    summaryItem("完整记录边界", result.complete_result_recorded_at_utc),
  );
  const coverage = document.querySelector("#coverage-notice");
  coverage.replaceChildren(
    node("strong", "覆盖说明"),
    node(
      "p",
      result.coverage_state === "reviewed_local_scope"
        ? "结果覆盖已确认的本地研究范围，不代表全市场完整覆盖。"
        : "当前结果的本地覆盖不完整或未知，不能使用全市场完整性表述。",
    ),
  );

  renderGroup(
    "#selected-list",
    "#selected-count",
    result.selected_candidates,
    "本次审阅没有纳入后续研究的候选路径。",
  );
  renderGroup(
    "#unresolved-list",
    "#unresolved-count",
    result.unresolved_candidates,
    "本次审阅没有待确认的候选路径。",
  );
  renderGroup(
    "#rejected-list",
    "#rejected-count",
    result.rejected_candidates,
    "本次审阅没有暂不纳入的候选路径。",
  );
  document.querySelector("#result-technical").textContent = JSON.stringify({
    session_id: result.session_id,
    reviewed_session_revision_id: result.reviewed_session_revision_id,
    reviewed_session_revision_number: result.reviewed_session_revision_number,
    acceptance_plan_version: result.acceptance_plan_version,
    acceptance_plan_fingerprint_sha256: result.acceptance_plan_fingerprint_sha256,
    information_cutoff_date: result.information_cutoff_date,
    session_recorded_at_utc: result.session_recorded_at_utc,
    complete_result_recorded_at_utc: result.complete_result_recorded_at_utc,
    as_of_cutoff: result.as_of_cutoff,
    as_of_recorded_at_utc: result.as_of_recorded_at_utc,
    candidate_sources: result.candidate_sources,
    notices: result.notices,
  }, null, 2);
}

async function initialize() {
  if (!route || !boundary.cutoff || !boundary.recordedAtUtc) {
    document.querySelector("#page-state").textContent = "精确链接无效";
    document.querySelector("#page-state").classList.add("is-unavailable");
    setStatus("缺少精确 session、reviewed revision 或双时间边界。请从研究历史重新打开。", "error");
    return;
  }
  const params = new URLSearchParams({
    session_id: route.sessionId,
    as_of_cutoff: boundary.cutoff,
    as_of_recorded_at_utc: boundary.recordedAtUtc,
  });
  setStatus("正在验证计划指纹、候选绑定和双时间边界……");
  try {
    const response = await fetch(
      `/industry-analysis/api/reviewed-plans/${encodeURIComponent(route.reviewedSessionRevisionId)}?${params.toString()}`,
      { headers: { Accept: "application/json" } },
    );
    const result = await readJson(response);
    renderResult(result);
    document.querySelector("#page-state").textContent = "精确计划已验证";
    document.querySelector("#page-state").classList.add("is-ready");
    setStatus("精确审阅结果读取完成；没有执行正式 owner 写入。", "success");
  } catch (error) {
    document.querySelector("#page-state").textContent = "精确计划不可用";
    document.querySelector("#page-state").classList.add("is-unavailable");
    const guidance = error.status === 404
      ? " 请确认当前历史时间边界已包含完整审阅候选，或从研究历史重新打开。"
      : " 页面不会回退到其他版本。";
    setStatus(`${error.message}${guidance}`, "error");
  }
}

initialize();
