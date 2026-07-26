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
const selectedSnapshotId = query.get("investment_candidate_snapshot_revision_id");

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
  card.append(node(
    "small",
    item.source_layer === "current_candidate_overlay" ? "来源：当前候选覆盖层" : "来源：已接受研究快照",
  ));
  return card;
}

function readinessText(member) {
  const readiness = member.readiness || {};
  const semantic = readiness.typed_semantics || {};
  const company = readiness.company_research || {};
  return `语义：${semantic.state || "missing"} · Company Research：${company.state || "missing"}`;
}

function overlaySummary(member) {
  const candidate = member.candidate_overlay;
  if (!candidate) return "候选覆盖：本快照无该精确 Beneficiary Revision";
  const score = candidate.final_score === null ? "无聚合分" : `最终分 ${candidate.final_score}`;
  return `候选覆盖：${candidate.candidate_status} · ${score}`;
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
  if (member.candidate_overlay) {
    meta.append(node("span", member.candidate_overlay.candidate_status, "meta-chip"));
  }
  const details = document.createElement("details");
  details.append(node("summary", "查看精确绑定、准备度和候选覆盖"));
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
          candidate_overlay: member.candidate_overlay,
        },
        null,
        2,
      ),
      "json-block",
    ),
  );
  card.append(
    header,
    meta,
    node("p", member.rationale_summary),
    node("p", readinessText(member), "muted-copy"),
    node("p", overlaySummary(member), "muted-copy"),
    details,
  );
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

function mapItem(title, subtitle, description) {
  const item = node("article", null, "map-item");
  item.append(node("strong", title), node("span", subtitle, "meta-chip"));
  if (description) item.append(node("p", description, "muted-copy"));
  return item;
}

function renderMap(industryMap) {
  document.querySelector("#map-revision-label").textContent = `Revision ${industryMap.revision_no}`;
  document.querySelector("#map-summary").replaceChildren(
    node("span", industryMap.title, "meta-chip"),
    node("span", `节点 ${industryMap.counts.nodes}`, "meta-chip"),
    node("span", `关系 ${industryMap.counts.relationships}`, "meta-chip"),
    node("span", `观察 ${industryMap.counts.observations}`, "meta-chip"),
    node("span", "精确 Revision ID，无 latest 回退", "meta-chip"),
  );
  const nodes = industryMap.nodes.map((item) => mapItem(
    item.label,
    `${item.node_kind} · ${item.assertion_status}`,
    item.description,
  ));
  const relationships = industryMap.relationships.map((item) => mapItem(
    `${item.source_node_key} → ${item.target_node_key}`,
    `${item.relation_kind} · ${item.assertion_status}`,
    item.description,
  ));
  const observations = industryMap.observations.map((item) => mapItem(
    item.title,
    `${item.observation_kind} · ${item.assertion_status}`,
    item.description,
  ));
  document.querySelector("#map-nodes").replaceChildren(...(nodes.length ? nodes : [node("p", "该精确版本没有节点。", "muted-copy")]));
  document.querySelector("#map-relationships").replaceChildren(...(relationships.length ? relationships : [node("p", "该精确版本没有关系。", "muted-copy")]));
  document.querySelector("#map-observations").replaceChildren(...(observations.length ? observations : [node("p", "该精确版本没有观察。", "muted-copy")]));
}

function snapshotOptionLabel(option) {
  const counts = Object.entries(option.candidate_status_counts)
    .map(([key, value]) => `${key} ${value}`)
    .join(" · ");
  return `${option.recorded_at_utc} · 截止 ${option.information_cutoff_date} · ${counts || "无状态"}`;
}

function applySnapshotSelection(snapshotId) {
  const next = new URL(window.location.href);
  if (snapshotId) {
    next.searchParams.set("investment_candidate_snapshot_revision_id", snapshotId);
  } else {
    next.searchParams.delete("investment_candidate_snapshot_revision_id");
  }
  window.location.assign(next.toString());
}

function renderSnapshotPicker(result) {
  const picker = document.querySelector("#snapshot-select");
  const apply = document.querySelector("#apply-snapshot");
  const clear = document.querySelector("#clear-snapshot");
  picker.replaceChildren(node("option", "不显示候选覆盖层"));
  picker.firstElementChild.value = "";
  for (const option of result.candidate_snapshot_options.options) {
    const element = node("option", snapshotOptionLabel(option));
    element.value = option.snapshot_revision_id;
    picker.append(element);
  }
  picker.value = result.candidate_overlay.snapshot_revision_id || "";
  picker.disabled = result.candidate_snapshot_options.options.length === 0;
  apply.disabled = picker.disabled;
  clear.disabled = !result.candidate_overlay.snapshot_revision_id;
  apply.addEventListener("click", () => applySnapshotSelection(picker.value), { once: true });
  clear.addEventListener("click", () => applySnapshotSelection(""), { once: true });
  const messages = {
    unavailable_zero_supported: "接受结果没有 supported 后续研究池，因此不存在候选快照覆盖层。",
    unavailable: "该精确候选池在当前双时间边界下没有可用候选快照。",
    not_selected: `找到 ${result.candidate_snapshot_options.options.length} 个精确快照；系统没有自动选择。`,
    selected: "正在显示用户显式选择的精确候选快照。",
    blocked_exact_pool_mismatch: "所选快照属于另一个精确候选池；已接受研究仍保持可读，未执行回退。",
    blocked_candidate_snapshot_unavailable: "所选快照不存在或不在当前双时间边界内；未执行回退。",
    blocked_candidate_graph_incomplete: "所选候选快照图不完整；未执行回退。",
    blocked_candidate_contract_mismatch: "所选候选快照不属于 v1 精确用途/规则合同；未执行回退。",
  };
  const state = result.candidate_overlay.state;
  document.querySelector("#snapshot-help").textContent = messages[state] || `候选覆盖状态：${state}`;
  document.querySelector("#overlay-state").textContent = state;
}

function candidateTitle(candidate) {
  return candidate.stock_name || candidate.stock_code || candidate.beneficiary_revision_id;
}

function candidateCard(candidate, compact = false) {
  const card = node("article", null, compact ? "candidate-highlight" : "candidate-detail");
  card.append(node("h3", candidateTitle(candidate)));
  card.append(node("span", candidate.candidate_status, "candidate-status"));
  const score = candidate.final_score === null ? "无聚合分" : `最终分 ${candidate.final_score}`;
  card.append(node("p", `${score}${candidate.priority_ordinal ? ` · 优先序 ${candidate.priority_ordinal}` : ""}`, "muted-copy"));
  if (!compact) {
    card.append(node("p", `原因：${candidate.reason_codes.join(" · ") || "无"}`, "muted-copy"));
    const details = document.createElement("details");
    details.append(node("summary", "查看组件与精确下游 Revision"));
    details.append(node("pre", JSON.stringify({
      beneficiary_revision_id: candidate.beneficiary_revision_id,
      company_research_revision_id: candidate.company_research_revision_id,
      typed_beneficiary_revision_id: candidate.typed_beneficiary_revision_id,
      canonical_price_revision_id: candidate.canonical_price_revision_id,
      comparison_eligibility_revision_id: candidate.comparison_eligibility_revision_id,
      components: candidate.components,
    }, null, 2), "json-block"));
    card.append(details);
  }
  return card;
}

function renderOverlay(overlay) {
  const highlights = document.querySelector("#candidate-highlights");
  const details = document.querySelector("#candidate-overlay-details");
  highlights.replaceChildren();
  details.replaceChildren();
  if (!overlay.snapshot) {
    if (overlay.state.startsWith("blocked")) {
      details.append(node("p", `候选覆盖已阻止：${overlay.blocked_reason}`, "overlay-blocked"));
    }
    return;
  }
  const priority = overlay.snapshot.members
    .filter((item) => ["priority_candidate", "watch_candidate"].includes(item.candidate_status))
    .sort((a, b) => (a.priority_ordinal || 9999) - (b.priority_ordinal || 9999))
    .slice(0, 3);
  highlights.append(...priority.map((item) => candidateCard(item, true)));
  details.append(...overlay.snapshot.members.map((item) => candidateCard(item)));
}

function render(result) {
  const accepted = result.accepted_snapshot;
  document.querySelector("#result-title").textContent = accepted.title;
  document.querySelector("#coverage-notice").textContent = result.coverage_notice;
  document.querySelector("#facts-grid").replaceChildren(...result.conclusion_cards.map(factCard));
  document.querySelector("#largest-gap").textContent = `最大准备度缺口：${result.largest_missing_prerequisite}`;
  renderMap(result.industry_map);
  renderSnapshotPicker(result);
  renderOverlay(result.candidate_overlay);
  renderList("#complete-members", "#complete-count", accepted.members, "没有完整成员；该输出图不应被视为有效成果。");
  renderList("#supported-members", "#supported-count", accepted.supported_handoff_members, "本次没有 supported 后续研究成员；完整成果仍保持可读。");
  document.querySelector("#result-technical").textContent = JSON.stringify({
    result_contract_version: result.result_contract_version,
    output_link_revision_id: accepted.output_link_revision_id,
    accepted_session_revision_id: accepted.accepted_session_revision_id,
    industry_map_revision_id: accepted.industry_map_revision_id,
    accepted_candidate_pool_revision_id: accepted.accepted_candidate_pool_revision_id,
    selected_snapshot_revision_id: result.candidate_overlay.snapshot_revision_id,
    as_of_cutoff: boundary.cutoff,
    as_of_recorded_at_utc: boundary.recordedAtUtc,
    writes_performed: result.writes_performed,
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
  const acceptedParams = new URLSearchParams({
    session_id: route.sessionId,
    as_of_cutoff: boundary.cutoff,
    as_of_recorded_at_utc: boundary.recordedAtUtc,
  });
  setStatus("正在验证 accepted session、精确 Output Link、Map Revision 和候选快照……");
  try {
    const acceptedResponse = await fetch(
      `/industry-analysis/api/session-revisions/${encodeURIComponent(route.acceptedRevisionId)}/accepted-result-view?${acceptedParams}`,
      { headers: { Accept: "application/json" } },
    );
    const accepted = await readJson(acceptedResponse);
    const outputLinkRevisionId = accepted.technical_details.output_link_revision_id;
    const assemblyParams = new URLSearchParams({
      as_of_cutoff: boundary.cutoff,
      as_of_recorded_at_utc: boundary.recordedAtUtc,
    });
    if (selectedSnapshotId) {
      assemblyParams.set("investment_candidate_snapshot_revision_id", selectedSnapshotId);
    }
    const response = await fetch(
      `/industry-analysis/api/output-link-revisions/${encodeURIComponent(outputLinkRevisionId)}/assembled-result?${assemblyParams}`,
      { headers: { Accept: "application/json" } },
    );
    render(await readJson(response));
    setStatus("精确已接受成果和显式候选覆盖层读取完成；页面只读且不会移动版本。", "success");
  } catch (error) {
    document.querySelector("#page-state").textContent = "精确成果不可用";
    setStatus(`${error.message}${error.recovery ? ` ${error.recovery}` : ""}`, "error");
  }
}

initialize();
