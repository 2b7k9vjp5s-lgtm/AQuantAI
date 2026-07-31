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

const SOURCE_LAYER_LABELS = {
  accepted_snapshot: "已接受研究快照",
  accepted_fact: "已接受事实/精确观察",
  accepted_research_judgment: "已接受研究判断",
  deterministic_candidate: "确定性候选计算",
  missing_or_unavailable: "缺失或当前不可用",
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
  card.append(node(
    "small",
    item.source_layer === "current_candidate_overlay" ? "来源：当前候选覆盖层" : "来源：已接受研究快照",
  ));
  return card;
}

function sourceBadge(sourceLayer) {
  return node(
    "span",
    SOURCE_LAYER_LABELS[sourceLayer] || sourceLayer || "来源未标注",
    `source-layer source-${sourceLayer || "unknown"}`,
  );
}

function readinessText(member) {
  const readiness = member.readiness || {};
  const semantic = readiness.typed_semantics || {};
  const company = readiness.company_research || {};
  return `语义：${semantic.state || "missing"} · Company Research：${company.state || "missing"}`;
}

function overlaySummary(member) {
  const candidate = member.candidate_overlay;
  if (!candidate) return "候选覆盖：本精确快照未包含该 Beneficiary Revision";
  return `候选覆盖：${candidate.candidate_status} · 原因 ${candidate.reason_codes.join(" · ") || "无"}`;
}

function textOrMissing(value) {
  return value === undefined || value === null || value === "" ? "未记录" : String(value);
}

function explanationItem(item) {
  const card = node("article", null, "explanation-item");
  const kind = item.kind || item.field_kind || "research";
  const titles = {
    financial_hypothesis: "业绩传导",
    market_expectation: "市场预期",
    valuation: "估值观察",
    canonical_price: "精确价格上下文",
    comparison_eligibility: "比较可用性",
    catalyst: "催化剂",
    risk: "风险/证伪",
    industry_judgment: "行业判断",
    company_judgment: "公司判断",
    claim: "事实/推断声明",
    evidence: "证据来源",
  };
  card.append(node("strong", titles[kind] || kind), sourceBadge(item.source_layer));
  const lines = [];
  if (kind === "financial_hypothesis") {
    lines.push(item.mechanism, `经营指标：${item.operating_metric}`, `财务科目：${item.financial_statement_line}`, `兑现时滞：${item.expected_lag_horizon}`, `状态/置信度：${item.hypothesis_status} / ${item.confidence}`, item.basis);
  } else if (kind === "market_expectation") {
    lines.push(item.subject, `区间：${item.period_horizon}`, `类型：${item.expectation_kind}`, `方向/状态：${item.direction} / ${item.status}`, item.basis);
  } else if (kind === "valuation") {
    lines.push(`${item.valuation_method} · ${item.metric_context}`, `观察值：${textOrMissing(item.observed_value)} ${item.currency || ""} ${item.unit || ""}`.trim(), `比较基础：${item.comparison_basis}`, `状态/置信度：${item.status} / ${item.confidence}`, item.assumptions, item.missing_data_reason);
  } else if (kind === "canonical_price") {
    lines.push(`交易日：${item.trade_date}`, `价格：${item.standardized_value_text} ${item.currency_code}/${item.unit_code}`, `状态：${item.canonical_status}`, item.conflict_summary);
  } else if (kind === "comparison_eligibility") {
    lines.push(`状态：${item.state}`, `规则：${item.rule_version}`, `原因：${(item.reason_codes || []).join(" · ") || "无"}`);
  } else if (kind === "catalyst") {
    lines.push(`${item.catalyst_category} · ${item.subject}`, `观察窗口：${item.expected_observation_window}`, `触发条件：${item.trigger_observation_criteria}`, `状态/置信度：${item.status} / ${item.confidence}`, item.basis, `不确定性：${item.uncertainty}`);
  } else if (kind === "risk") {
    lines.push(`${item.risk_category} · ${item.subject}`, `下行路径：${item.downside_path}`, `证伪条件：${item.thesis_invalidation_condition}`, `缓释因素：${item.mitigants}`, `状态/置信度：${item.status} / ${item.confidence}`, item.basis, `不确定性：${item.uncertainty}`);
  } else if (kind === "industry_judgment") {
    lines.push(`结论：${item.outcome} · 证据：${item.evidence_state} · 置信度：${item.confidence}`, `驱动持续性：${item.driver_durability}`, `价值池：${item.value_pool_direction}`, `瓶颈支持：${item.chain_bottleneck_support}`, item.rationale, `待验证：${item.follow_up_verification}`);
  } else if (kind === "company_judgment") {
    lines.push(`结论：${item.outcome} · 证据：${item.evidence_state} · 置信度：${item.confidence}`, `受益可信度：${item.beneficiary_credibility}`, `业绩传导可信度：${item.financial_transmission_credibility}`, `执行风险：${item.execution_risks}`, item.rationale, `待验证：${item.follow_up_verification}`);
  } else if (kind === "claim") {
    lines.push(item.statement, `类型/状态：${item.claim_kind} / ${item.claim_status}`, item.inference_basis);
  } else if (kind === "evidence") {
    lines.push(`${item.evidence_grade}级 · ${item.source_kind} · ${item.source_title}`, item.summary);
  } else {
    lines.push(JSON.stringify(item));
  }
  for (const line of lines.filter(Boolean)) card.append(node("p", line, "muted-copy"));
  return card;
}

function semanticItem(item) {
  const card = node("article", null, "explanation-item");
  card.append(
    node("strong", `${item.field_kind} · ${item.subject_text || item.state_code}`),
    sourceBadge(item.source_layer),
    node("p", `状态：${item.state_code} · 证据：${item.evidence_state}`, "muted-copy"),
    node("p", item.rationale, "muted-copy"),
  );
  return card;
}

function explanationSection(title, items, renderer = explanationItem) {
  const section = node("section", null, "explanation-section");
  section.append(node("h4", title));
  if (!items || !items.length) {
    section.append(node("p", "当前精确绑定中没有可展示内容。", "muted-copy"));
    return section;
  }
  const grid = node("div", null, "explanation-grid");
  grid.append(...items.map(renderer));
  section.append(grid);
  return section;
}

function componentItem(component) {
  const card = node("article", null, "component-explanation");
  card.append(
    node("strong", component.component_code),
    sourceBadge(component.source_layer),
    node("p", `状态：${component.assessment_state} · 验证：${component.verification_state} · 证伪：${component.falsification_state}`, "muted-copy"),
    node("p", component.rationale, "muted-copy"),
  );
  if (component.verification_question) card.append(node("p", `待验证：${component.verification_question}`, "muted-copy"));
  if (component.falsification_condition) card.append(node("p", `证伪条件：${component.falsification_condition}`, "muted-copy"));
  if (component.inputs && component.inputs.length) {
    card.append(node("p", `精确输入：${component.inputs.map((item) => `${item.kind}:${item.state || "available"}`).join(" · ")}`, "muted-copy"));
  }
  return card;
}

function explainedResearchPanel(member) {
  const explanation = member.explained_research;
  const panel = node("div", null, "explained-research");
  panel.append(node("h4", "为什么受益 / 为什么是当前研究状态"));
  if (!explanation) {
    panel.append(node("p", "解释投影不可用；完整已接受成员仍保留。", "muted-copy"));
    return panel;
  }
  const status = node("div", null, "explanation-status");
  status.append(node("span", explanation.overall_state, "meta-chip"));
  for (const layer of explanation.source_layers || []) status.append(sourceBadge(layer));
  panel.append(status);

  if (explanation.company_research) {
    const company = node("article", null, "company-research-summary");
    company.append(
      node("strong", "精确 Company Research"),
      sourceBadge(companyLayer(explanation.company_research)),
      node("p", explanation.company_research.summary || explanation.company_research.research_question, "muted-copy"),
      node("p", `状态：${explanation.company_research.conclusion_status} · 工作流：${explanation.company_research.workflow_state}`, "muted-copy"),
    );
    panel.append(company);
  }

  panel.append(
    explanationSection("产品 / 产业链位置", explanation.product_and_chain, semanticItem),
    explanationSection("客户 / 认证 / 产能 / 生产 / 订单", explanation.customer_certification_capacity_order, semanticItem),
    explanationSection("业绩传导", explanation.earnings_transmission),
    explanationSection("预期", explanation.expectation),
    explanationSection("估值与价格上下文", explanation.valuation),
    explanationSection("催化剂", explanation.catalysts),
    explanationSection("风险与证伪", explanation.risks),
    explanationSection("行业判断", explanation.industry_judgments),
    explanationSection("公司判断", explanation.company_judgments),
  );

  if (explanation.candidate_explanation) {
    const candidate = explanation.candidate_explanation;
    const candidateSection = node("section", null, "explanation-section candidate-reasoning");
    candidateSection.append(
      node("h4", "当前候选状态解释"),
      sourceBadge(candidate.source_layer),
      node("p", `状态：${candidate.candidate_status} · 原因：${candidate.reason_codes.join(" · ") || "无"}`, "muted-copy"),
    );
    const componentGrid = node("div", null, "explanation-grid");
    componentGrid.append(...candidate.components.map(componentItem));
    candidateSection.append(componentGrid);
    panel.append(candidateSection);
  } else {
    panel.append(node("p", "未显式选择包含该公司的候选快照，因此不推断当前候选状态。", "muted-copy"));
  }

  if (explanation.missing_inputs && explanation.missing_inputs.length) {
    const missing = node("div", null, "missing-inputs");
    missing.append(node("strong", "明确缺失 / 不可用"));
    for (const item of explanation.missing_inputs) missing.append(node("span", item, "meta-chip"));
    panel.append(missing);
  }
  return panel;
}

function companyLayer(companyResearch) {
  return companyResearch.source_layer || "accepted_research_judgment";
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
  details.append(node("summary", "查看精确绑定、准备度和技术详情"));
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
          explained_research: member.explained_research,
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
    explainedResearchPanel(member),
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
    selected: "正在显示用户显式选择的精确候选快照及其冻结解释输入。",
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
  const score = candidate.final_score === null ? "无聚合分" : `持久化分值 ${candidate.final_score}`;
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
    explained_result_contract_version: result.explained_result.contract_version,
    explained_result_content_sha256: result.explained_result.content_sha256,
    explained_result_uses_latest_fallback: result.explained_result.uses_latest_fallback,
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
  setStatus("正在验证 accepted session、精确 Output Link、Map Revision、候选快照和解释输入……");
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
    setStatus("精确已接受成果、显式候选覆盖层和冻结解释输入读取完成；页面只读且不会移动版本。", "success");
  } catch (error) {
    document.querySelector("#page-state").textContent = "精确成果不可用";
    setStatus(`${error.message}${error.recovery ? ` ${error.recovery}` : ""}`, "error");
  }
}

initialize();
