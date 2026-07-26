"use strict";

const routeMatch = window.location.pathname.match(
  /^\/industry-analysis\/sessions\/([0-9a-f-]+)\/revisions\/([0-9a-f-]+)\/accepted-result$/i,
);
const route = routeMatch
  ? { sessionId: routeMatch[1], acceptedRevisionId: routeMatch[2] }
  : null;
const query = new URLSearchParams(window.location.search);
const boundary = {
  cutoff: query.get("as_of_cutoff"),
  recordedAtUtc: query.get("as_of_recorded_at_utc"),
};

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined && text !== null) element.textContent = String(text);
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
  error.recovery = detail && typeof detail === "object" ? detail.recovery_action : null;
  throw error;
}

function factCard(item) {
  const card = node("div", null, "fact-card");
  card.append(node("strong", item.label), node("span", item.value));
  return card;
}

function readinessText(member) {
  const readiness = member.readiness || {};
  const semantic = readiness.typed_semantics || {};
  const company = readiness.company_research || {};
  return `语义：${semantic.state || "missing"} · Company Research：${company.state || "missing"}`;
}

function memberCard(member) {
  const card = node("article", null, "accepted-member");
  const header = node("div");
  header.append(
    node("h3", member.company_label_original),
    node("p", `${member.source} · ${member.stock_code}`, "muted-copy"),
  );
  const meta = node("div", null, "member-meta");
  meta.append(
    node("span", member.legacy_beneficiary_kind, "meta-chip"),
    node("span", member.assessment_status, "meta-chip"),
    node(
      "span",
      member.included_in_supported_handoff ? "进入 supported 后续研究" : "保留在完整成果",
      "meta-chip",
    ),
  );
  const rationale = node("p", member.rationale_summary);
  const readiness = node("p", readinessText(member), "muted-copy");
  const details = document.createElement("details");
  details.append(node("summary", "查看精确绑定和准备度原因"));
  details.append(
    node(
      "pre",
      JSON.stringify(
        {
          reviewed_candidate_revision_id: member.reviewed_candidate_revision_id,
          beneficiary_id: member.beneficiary_id,
          beneficiary_revision_id: member.beneficiary_revision_id,
          semantic_profile_revision_id: member.semantic_profile_revision_id,
          included_in_supported_handoff: member.included_in_supported_handoff,
          readiness: member.readiness,
        },
        null,
        2,
      ),
      "json-block",
    ),
  );
  card.append(header, meta, rationale, readiness, details);
  return card;
}

function renderList(selector, countSelector, members, emptyText) {
  const container = document.querySelector(selector);
  document.querySelector(countSelector).textContent = String(members.length);
  container.replaceChildren();
  if (!members.length) {
    container.append(node("p", emptyText, "muted-copy"));
    return;
  }
  container.append(...members.map(memberCard));
}

function render(result) {
  document.querySelector("#result-title").textContent = result.title;
  document.querySelector("#coverage-notice").textContent = result.coverage_notice;
  document.querySelector("#facts-grid").replaceChildren(...result.facts.map(factCard));
  document.querySelector("#largest-gap").textContent =
    `最大准备度缺口：${result.largest_missing_prerequisite}`;
  renderList(
    "#complete-members",
    "#complete-count",
    result.members,
    "没有完整成员；该输出图不应被视为有效成果。",
  );
  renderList(
    "#supported-members",
    "#supported-count",
    result.supported_handoff_members,
    "本次没有 supported 后续研究成员；draft/disputed 成员仍保留在完整成果中。",
  );
  document.querySelector("#result-technical").textContent = JSON.stringify({
    session_id: result.session_id,
    reviewed_session_revision_id: result.reviewed_session_revision_id,
    accepted_session_revision_id: result.accepted_session_revision_id,
    research_case_id: result.research_case_id,
    industry_map_id: result.industry_map_id,
    industry_map_revision_id: result.industry_map_revision_id,
    accepted_candidate_pool_revision_id: result.accepted_candidate_pool_revision_id,
    information_cutoff_date: result.information_cutoff_date,
    recorded_at_utc: result.recorded_at_utc,
    technical_details: result.technical_details,
  }, null, 2);
  document.querySelector("#page-state").textContent = "精确成果已验证";
  document.querySelector("#page-state").classList.add("is-ready");
}

async function initialize() {
  if (!route || !boundary.cutoff || !boundary.recordedAtUtc) {
    document.querySelector("#page-state").textContent = "精确链接无效";
    setStatus("缺少 accepted revision 或双时间边界。请从研究历史重新打开。", "error");
    return;
  }
  const params = new URLSearchParams({
    session_id: route.sessionId,
    as_of_cutoff: boundary.cutoff,
    as_of_recorded_at_utc: boundary.recordedAtUtc,
  });
  setStatus("正在验证 accepted session、output link 和 readiness……");
  try {
    const response = await fetch(
      `/industry-analysis/api/session-revisions/${encodeURIComponent(route.acceptedRevisionId)}/accepted-result-view?${params}`,
      { headers: { Accept: "application/json" } },
    );
    render(await readJson(response));
    setStatus("精确已接受成果读取完成；页面只读且不会移动版本。", "success");
  } catch (error) {
    document.querySelector("#page-state").textContent = "精确成果不可用";
    setStatus(`${error.message}${error.recovery ? ` ${error.recovery}` : ""}`, "error");
  }
}

initialize();
