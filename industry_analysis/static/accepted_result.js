"use strict";

const routeMatch = window.location.pathname.match(
  /^\/industry-analysis\/sessions\/([0-9a-f-]+)\/revisions\/([0-9a-f-]+)\/accepted-result$/i,
);
const route = routeMatch
  ? { sessionId: routeMatch[1], acceptedSessionRevisionId: routeMatch[2] }
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
  const element = document.querySelector("#accepted-status");
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
  error.recoveryAction = detail && typeof detail === "object" ? detail.recovery_action : null;
  throw error;
}

function showErrors(messages) {
  const summary = document.querySelector("#error-summary");
  const list = document.querySelector("#error-list");
  list.replaceChildren();
  messages.forEach((message) => list.append(node("li", message)));
  summary.hidden = false;
  summary.focus();
}

function factCard(item) {
  const card = node("article", null, "fact-card");
  card.append(node("strong", item.label), node("span", item.value));
  return card;
}

function valueCell(label, value, detail = "") {
  const cell = node("div", null, "result-cell");
  cell.append(node("strong", label), node("span", value ?? "未提供"));
  if (detail) cell.append(node("small", detail));
  return cell;
}

function readinessText(member) {
  if (member.ready_for_later_explicit_handoff) return "已具备后续明确交接条件";
  const reasons = member.readiness_reason_codes || [];
  if (!reasons.length) return "暂无额外准备度说明";
  return reasons.join("、");
}

function memberCard(member, { compact = false } = {}) {
  const card = node("article", null, "accepted-member");
  const header = document.createElement("header");
  const title = node("div");
  title.append(
    node("strong", member.company_label_original),
    node("p", `${member.source} · ${member.stock_code} · 冻结顺序 ${member.sequence + 1}`, "muted-copy"),
  );
  header.append(
    title,
    node(
      "span",
      member.assessment_status,
      `member-status is-${member.assessment_status}`,
    ),
  );
  card.append(header);

  const grid = node("div", null, "accepted-member-grid");
  grid.append(
    valueCell("正式受益类型", member.legacy_beneficiary_kind),
    valueCell("证据评估状态", member.assessment_status),
    valueCell(
      "supported 后续研究池",
      member.included_in_supported_handoff ? "已进入" : "未进入",
      member.supported_handoff_reason || "",
    ),
    valueCell("类型化语义", member.semantic.state),
    valueCell(
      "Company Research",
      member.company_research.state,
      member.company_research.workflow_state || member.company_research.reason || "",
    ),
    valueCell("后续准备度", readinessText(member)),
  );
  card.append(grid);

  if (!compact) {
    const rationale = node("div", null, "preview-box");
    rationale.append(
      node("strong", "正式受益说明"),
      node("p", member.rationale_summary),
      node("strong", "本次准备度说明"),
      node("p", member.readiness_note || "未提供"),
    );
    card.append(rationale);
  }

  const details = document.createElement("details");
  details.className = "technical-details";
  details.append(node("summary", "查看精确 owner 绑定和技术状态"));
  details.append(
    node(
      "pre",
      JSON.stringify(
        {
          reviewed_candidate_revision_id: member.reviewed_candidate_revision_id,
          beneficiary_id: member.beneficiary_id,
          beneficiary_revision_id: member.beneficiary_revision_id,
          stock_basic_record_id: member.stock_basic_record_id,
          semantic: member.semantic,
          company_research: member.company_research,
          investment_candidate: member.investment_candidate,
          canonical_price_and_eligibility: member.canonical_price_and_eligibility,
          structured_financial_and_valuation: member.structured_financial_and_valuation,
          readiness_reason_codes: member.readiness_reason_codes,
        },
        null,
        2,
      ),
      "json-block",
    ),
  );
  card.append(details);
  return card;
}

function renderList(selector, countSelector, members, emptyText, options = {}) {
  const container = document.querySelector(selector);
  container.replaceChildren();
  document.querySelector(countSelector).textContent = String(members.length);
  if (!members.length) {
    container.append(node("p", emptyText, "result-empty"));
    return;
  }
  members.forEach((member) => container.append(memberCard(member, options)));
}

function renderResult(result) {
  document.querySelector("#accepted-title").textContent = result.title;
  document.querySelector("#accepted-scope").textContent = result.scope;
  const facts = document.querySelector("#accepted-facts");
  facts.replaceChildren();
  result.facts.forEach((item) => facts.append(factCard(item)));

  const zero = document.querySelector("#zero-supported");
  if (result.zero_supported_notice) {
    zero.hidden = false;
    zero.replaceChildren(
      node("strong", "零 supported 成员是有效结果"),
      node("p", result.zero_supported_notice),
    );
  } else {
    zero.hidden = true;
  }

  renderList(
    "#complete-members",
    "#complete-count",
    result.members,
    "该精确成果没有完整成员，图完整性校验本应阻断此状态。",
  );
  renderList(
    "#handoff-members",
    "#handoff-count",
    result.supported_handoff_members,
    "本次研究成果已接受，但没有成员进入 supported 后续研究池。",
    { compact: true },
  );

  document.querySelector("#accepted-technical").textContent = JSON.stringify(
    {
      session_id: result.session_id,
      reviewed_session_revision_id: result.reviewed_session_revision_id,
      accepted_session_revision_id: result.accepted_session_revision_id,
      output_link_id: result.output_link_id,
      output_link_revision_id: result.output_link_revision_id,
      owner_transaction_id: result.owner_transaction_id,
      candidate_pool_mode: result.candidate_pool_mode,
      accepted_candidate_pool_revision_id: result.accepted_candidate_pool_revision_id,
      coverage_state: result.coverage_state,
      accepted_at_utc: result.accepted_at_utc,
      information_cutoff_date: result.information_cutoff_date,
      as_of_cutoff: result.as_of_cutoff,
      as_of_recorded_at_utc: result.as_of_recorded_at_utc,
      technical_details: result.technical_details,
    },
    null,
    2,
  );
}

async function initialize() {
  if (!route || !boundary.cutoff || !boundary.recordedAtUtc) {
    document.querySelector("#page-state").textContent = "精确链接无效";
    document.querySelector("#page-state").classList.add("is-unavailable");
    showErrors(["缺少精确 session、accepted revision 或双时间边界。请从研究历史重新打开。"]);
    setStatus("页面不会尝试读取最新或相似结果。", "error");
    return;
  }
  const params = new URLSearchParams({
    session_id: route.sessionId,
    as_of_cutoff: boundary.cutoff,
    as_of_recorded_at_utc: boundary.recordedAtUtc,
  });
  setStatus("正在验证精确输出链接、完整成员和准备度图……");
  try {
    const response = await fetch(
      `/industry-analysis/api/session-revisions/${encodeURIComponent(route.acceptedSessionRevisionId)}/accepted-result-view?${params.toString()}`,
      { headers: { Accept: "application/json" } },
    );
    const result = await readJson(response);
    renderResult(result);
    document.querySelector("#page-state").textContent = "精确成果已验证";
    document.querySelector("#page-state").classList.add("is-ready");
    setStatus("精确已接受成果读取完成；没有创建新的公司研究、投资候选或交易状态。", "success");
  } catch (error) {
    document.querySelector("#page-state").textContent = "精确成果不可用";
    document.querySelector("#page-state").classList.add("is-unavailable");
    const messages = [error.message];
    if (error.recoveryAction) messages.push(error.recoveryAction);
    showErrors(messages);
    setStatus("结果图校验失败时整页关闭，不会回退到最新或部分结果。", "error");
  }
}

initialize();
