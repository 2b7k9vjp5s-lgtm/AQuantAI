"use strict";

const state = { cases: [], evidence: [], selectedCase: null, csrf: null, aiFingerprint: null };
const contentLabels = {
  industry: {
    driver_type: "驱动类型", demand_change: "需求变化", supply_change: "供给变化",
    technology_route: "技术路线", process_bottlenecks: "工艺瓶颈", chain_position: "产业链位置",
    related_companies: "相关公司", customers_certifications: "客户 / 认证",
    research_conclusion: "研究结论", risks: "风险", watch_items: "Watch Items"
  },
  company: {
    company_profile: "公司基本资料", business_structure: "业务结构", products: "产品",
    chain_position: "产业链位置", customers: "客户", certifications: "认证",
    competitive_advantages: "竞争优势", financial_research: "财务研究", major_events: "重大事件",
    research_conclusion: "研究结论", risks: "风险", watch_items: "Watch Items"
  }
};

function node(tag, text, className) {
  const value = document.createElement(tag);
  if (text !== undefined && text !== null) value.textContent = String(text);
  if (className) value.className = className;
  return value;
}

function clear(target) { target.replaceChildren(); }
function today() { return new Date().toISOString().slice(0, 10); }

async function api(path, options = {}) {
  const settings = { ...options, headers: { ...(options.headers || {}) } };
  if (settings.method && settings.method !== "GET") {
    if (!state.csrf) {
      const token = await api("/api/document-import/csrf");
      state.csrf = token.csrf_token;
    }
    settings.headers["Content-Type"] = "application/json";
    settings.headers["X-AQuantAI-CSRF"] = state.csrf;
    settings.headers.Origin = window.location.origin;
  }
  const response = await fetch(path, settings);
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      const detail = payload.detail;
      message = typeof detail === "string" ? detail : (detail.message || detail.code || message);
    } catch (_error) { /* use status text */ }
    throw new Error(message);
  }
  return response.json();
}

function setStatus(message, error = false) {
  const target = document.getElementById("global-status");
  target.textContent = message;
  target.classList.toggle("error", error);
}

function showView(name) {
  document.querySelectorAll(".view").forEach((item) => item.classList.toggle("active", item.id === `view-${name}`));
  document.querySelectorAll(".sidebar button[data-view]").forEach((item) => item.classList.toggle("active", item.dataset.view === name));
  if (name === "feed") loadFeed();
  if (name === "evidence") loadEvidence();
  if (name === "documents" || name === "sources") loadDocumentsAndSources();
}

function renderTimeline(target, items) {
  clear(target);
  if (!items.length) { target.append(node("p", "暂无真实系统事件。", "muted")); return; }
  items.forEach((item) => {
    const article = node("article");
    article.append(node("strong", item.title || item.event_type));
    article.append(node("p", item.detail || ""));
    article.append(node("time", item.recorded_at_utc || ""));
    target.append(article);
  });
}

async function loadDashboard() {
  try {
    const payload = await api("/api/v1/workspace/dashboard");
    const metrics = document.getElementById("metrics"); clear(metrics);
    [
      [payload.case_count, "Research Cases"], [payload.industry_case_count, "Industry"],
      [payload.company_case_count, "Company"], [payload.pending_evidence_count, "Pending Evidence"],
      [payload.accepted_evidence_count, "Accepted Evidence"]
    ].forEach(([value, label]) => { const card = node("div", null, "metric"); card.append(node("strong", value)); card.append(node("span", label)); metrics.append(card); });
    renderTimeline(document.getElementById("dashboard-feed"), payload.recent_changes);
    setStatus("本地数据库已连接。所有研究写入均为追加式记录。");
  } catch (error) { setStatus(`工作区不可用：${error.message}`, true); }
}

function caseCard(item, compact = false) {
  const card = node(compact ? "button" : "article", null, compact ? "item" : "card");
  card.append(node("strong", item.title));
  card.append(node("p", [item.company_name, item.stock_code, item.industry_theme].filter(Boolean).join(" · ") || item.case_type));
  card.append(node("small", `Revision ${item.latest_revision_no} · ${item.workflow_state} · ${item.conclusion_status}`));
  if (compact) card.addEventListener("click", () => loadCase(item.case_id));
  else { const open = node("button", "打开"); open.addEventListener("click", () => { showView("cases"); loadCase(item.case_id); }); card.append(open); }
  return card;
}

async function loadCases() {
  try {
    const payload = await api("/api/v1/research-cases"); state.cases = payload.items;
    const list = document.getElementById("case-list"); clear(list);
    payload.items.forEach((item) => list.append(caseCard(item, true)));
    if (!payload.items.length) list.append(node("p", "尚未创建 Research Case。", "muted"));
    ["industry", "company"].forEach((kind) => {
      const target = document.getElementById(`${kind}-list`); clear(target);
      payload.items.filter((item) => item.case_type === kind).forEach((item) => target.append(caseCard(item)));
      if (!target.children.length) target.append(node("p", `尚无${kind === "industry" ? "行业" : "公司"}研究。`, "muted"));
    });
  } catch (error) { setStatus(`读取 Case 失败：${error.message}`, true); }
}

function detailRow(label, value) { const row = node("p"); row.append(node("strong", `${label}：`)); row.append(document.createTextNode(value === null || value === undefined || value === "" ? "Unavailable" : String(value))); return row; }

function renderRevision(revision) {
  const article = node("article", null, "revision");
  article.append(node("h3", `Revision ${revision.revision_no} · ${revision.workflow_state} / ${revision.conclusion_status}`));
  article.append(detailRow("研究问题", revision.research_question));
  Object.entries(revision.content).forEach(([key, value]) => article.append(detailRow(key.replaceAll("_", " "), value)));
  article.append(detailRow("变化摘要", revision.change_summary));
  article.append(node("small", `${revision.information_cutoff_date} · ${revision.recorded_at_utc}`));
  if (revision.evidence_references.length) {
    article.append(node("h3", "Evidence citations"));
    revision.evidence_references.forEach((citation) => article.append(node("div", `${citation.citation_order}. ${citation.source} · Document ${citation.document_id || "n/a"} · Page ${citation.page || "n/a"} · Evidence ${citation.evidence_id}`, "citation")));
  }
  return article;
}

async function loadCase(caseId) {
  try {
    const payload = await api(`/api/v1/research-cases/${caseId}`); state.selectedCase = payload;
    const target = document.getElementById("case-detail"); clear(target);
    const heading = node("div", null, "page-heading"); const title = node("div"); title.append(node("h2", payload.current_revision.title)); title.append(node("small", `${payload.case.case_type} · ${payload.case.case_key}`)); heading.append(title);
    const actions = node("div");
    const revise = node("button", "保存新 Revision"); revise.addEventListener("click", openRevisionDialog); actions.append(revise);
    const md = node("a", "Markdown", "button"); md.href = `/api/v1/research-cases/${caseId}/reports/markdown`; actions.append(md);
    const html = node("a", "HTML", "button"); html.href = `/api/v1/research-cases/${caseId}/reports/html`; actions.append(html); heading.append(actions); target.append(heading);
    target.append(detailRow("Case ID", payload.case.case_id));
    target.append(detailRow("当前修订", payload.current_revision.revision_no));
    target.append(detailRow("权威修订", payload.authoritative_revision ? payload.authoritative_revision.revision_no : "尚未形成 completed + supported 修订"));
    const aiBox = node("section", null, "notice"); aiBox.append(node("strong", "AI Research Assistant")); aiBox.append(node("p", "仅使用当前修订绑定的 Accepted Evidence；预览不会联网，生成必须显式确认。"));
    const preview = node("button", "预览 AI 输入"); preview.addEventListener("click", () => previewAI(aiBox)); aiBox.append(preview); target.append(aiBox);
    payload.revision_history.slice().reverse().forEach((revision) => target.append(renderRevision(revision)));
  } catch (error) { setStatus(`读取 Case 失败：${error.message}`, true); }
}

async function previewAI(container) {
  try {
    const payload = await api(`/api/v1/research-cases/${state.selectedCase.case.case_id}/ai-preview`); state.aiFingerprint = payload.manifest_fingerprint;
    container.append(detailRow("Evidence references", payload.evidence_reference_count));
    container.append(detailRow("Provider", payload.provider.available ? `${payload.provider.provider_id} / ${payload.provider.model_id}` : "未配置，核心工作流不受影响"));
    const manifest = node("pre"); manifest.textContent = JSON.stringify(payload.manifest, null, 2); container.append(manifest);
    if (payload.provider.available) {
      const confirm = node("label"); const checkbox = document.createElement("input"); checkbox.type = "checkbox"; confirm.append(checkbox, document.createTextNode(" 我确认将该 evidence-only manifest 发送给已配置 Provider")); container.append(confirm);
      const generate = node("button", "生成临时草稿"); generate.addEventListener("click", async () => {
        if (!checkbox.checked) { setStatus("必须先明确确认远程传输。", true); return; }
        try {
          const draft = await api(`/api/v1/research-cases/${state.selectedCase.case.case_id}/ai-drafts`, { method: "POST", body: JSON.stringify({ expected_manifest_fingerprint: state.aiFingerprint, confirm_remote_transmission: true }) });
          const output = node("pre"); output.textContent = JSON.stringify(draft.sections, null, 2); container.append(output);
        } catch (error) { setStatus(`AI Provider 调用失败，研究数据未改变：${error.message}`, true); }
      }); container.append(generate);
    }
  } catch (error) { setStatus(`AI 输入不可用：${error.message}`, true); }
}

async function loadEvidence(status = "") {
  try {
    const payload = await api(`/api/v1/evidence${status ? `?status=${encodeURIComponent(status)}` : ""}`); state.evidence = payload.items;
    const target = document.getElementById("evidence-list"); clear(target);
    payload.items.forEach((item) => { const card = node("article", null, "card"); card.append(node("strong", item.source || `Review ${item.review_session_id}`)); card.append(node("p", item.content_fragment || `Document ${item.document_id || ""}`)); card.append(node("small", `${item.status} · ${item.grade || "ungraded"} · ${item.recorded_at_utc || item.reviewed_at_utc || ""}`)); if (item.case_id) card.append(node("small", `Case ${item.case_id} · Document ${item.document_id || "n/a"} · Page ${item.page ?? "n/a"}`)); if (item.reviewer) card.append(node("small", `Reviewer ${item.reviewer}${item.review_note ? ` · ${item.review_note}` : ""}`)); if (item.source_locator || item.source_url) card.append(node("small", `Provenance ${item.source_locator || "local document"}${item.source_url ? ` · ${item.source_url}` : ""}`)); target.append(card); });
    if (!payload.items.length) target.append(node("p", "当前筛选没有记录。", "muted"));
  } catch (error) { setStatus(`读取 Evidence 失败：${error.message}`, true); }
}

async function loadDocumentsAndSources() {
  try {
    const [documents, sources] = await Promise.all([api("/api/v1/documents"), api("/api/v1/sources")]);
    const docs = document.getElementById("document-list"); clear(docs);
    documents.items.forEach((item) => { const card = node("article", null, "card"); card.append(node("strong", item.display_name)); card.append(node("p", `SHA256 ${item.sha256}`)); card.append(node("small", `${item.admission_state} · ${item.page_count ?? "n/a"} pages · ${item.imported_at_utc}`)); docs.append(card); });
    if (!documents.items.length) docs.append(node("p", "尚无本地文档记录。", "muted"));
    const sourceTarget = document.getElementById("source-list"); clear(sourceTarget);
    sources.items.forEach((item) => { const card = node("article", null, "card"); card.append(node("strong", item.title)); card.append(node("p", item.publisher || "Publisher unavailable")); card.append(node("small", `${item.accepted_evidence_count} accepted evidence records`)); sourceTarget.append(card); });
    if (!sources.items.length) sourceTarget.append(node("p", "尚无已接受来源。", "muted"));
  } catch (error) { setStatus(`读取 Documents/Sources 失败：${error.message}`, true); }
}

async function loadFeed() { try { const payload = await api("/api/v1/change-feed"); renderTimeline(document.getElementById("change-feed"), payload.items); } catch (error) { setStatus(`读取变化流失败：${error.message}`, true); } }

function openCaseDialog(type = "industry") { const dialog = document.getElementById("case-dialog"); document.getElementById("case-type").value = type; updateCaseType(); document.getElementById("case-cutoff").value = today(); document.getElementById("case-form-error").textContent = ""; dialog.showModal(); }
function updateCaseType() { const company = document.getElementById("case-type").value === "company"; document.getElementById("industry-theme-field").hidden = company; document.getElementById("company-name-field").hidden = !company; document.getElementById("stock-code-field").hidden = !company; }

async function submitCase(event) {
  event.preventDefault(); const type = document.getElementById("case-type").value;
  const body = { case_key: document.getElementById("case-key").value, case_type: type, title: document.getElementById("case-title").value, research_question: document.getElementById("case-question").value, created_by: document.getElementById("case-author").value, information_cutoff_date: document.getElementById("case-cutoff").value, content: {}, industry_theme: type === "industry" ? document.getElementById("industry-theme").value || null : null, company_name: type === "company" ? document.getElementById("company-name").value || null : null, stock_code: type === "company" ? document.getElementById("stock-code").value || null : null };
  try { const payload = await api("/api/v1/research-cases", { method: "POST", body: JSON.stringify(body) }); document.getElementById("case-dialog").close(); event.target.reset(); await loadCases(); await loadDashboard(); showView("cases"); loadCase(payload.case.case_id); } catch (error) { document.getElementById("case-form-error").textContent = error.message; }
}

async function openRevisionDialog() {
  const current = state.selectedCase.current_revision; document.getElementById("revision-title").value = current.title; document.getElementById("revision-question").value = current.research_question; document.getElementById("revision-cutoff").value = today(); document.getElementById("revision-change").value = ""; document.getElementById("revision-form-error").textContent = "";
  const fields = document.getElementById("content-fields"); clear(fields);
  Object.entries(contentLabels[state.selectedCase.case.case_type]).forEach(([key, label]) => { const wrapper = node("label", null, "wide"); wrapper.append(document.createTextNode(label)); const input = node("textarea"); input.dataset.contentKey = key; input.value = current.content[key] || ""; wrapper.append(input); fields.append(wrapper); });
  const evidenceTarget = document.getElementById("revision-evidence"); clear(evidenceTarget);
  const payload = await api("/api/v1/evidence?status=accepted"); const relevant = payload.items.filter((item) => item.case_id === state.selectedCase.case.case_id);
  relevant.forEach((item) => { const label = node("label"); const input = document.createElement("input"); input.type = "checkbox"; input.value = item.evidence_id; if (current.evidence_references.some((ref) => ref.evidence_id === item.evidence_id)) input.checked = true; label.append(input, document.createTextNode(`${item.source} · ${item.grade} · ${item.content_fragment}`)); evidenceTarget.append(label); });
  if (!relevant.length) evidenceTarget.append(node("p", "尚无 Accepted Evidence。可先前往 Import / Review Queue。", "muted"));
  document.getElementById("revision-dialog").showModal();
}

async function submitRevision(event) {
  event.preventDefault(); const content = {}; document.querySelectorAll("[data-content-key]").forEach((input) => { if (input.value.trim()) content[input.dataset.contentKey] = input.value; });
  const evidenceIds = Array.from(document.querySelectorAll("#revision-evidence input:checked"), (item) => item.value);
  const body = { expected_latest_revision_no: state.selectedCase.current_revision.revision_no, title: document.getElementById("revision-title").value, research_question: document.getElementById("revision-question").value, created_by: document.getElementById("revision-author").value, information_cutoff_date: document.getElementById("revision-cutoff").value, workflow_state: document.getElementById("revision-workflow").value, conclusion_status: document.getElementById("revision-conclusion").value, content, evidence_ids: evidenceIds, change_summary: document.getElementById("revision-change").value || null };
  try { const payload = await api(`/api/v1/research-cases/${state.selectedCase.case.case_id}/revisions`, { method: "POST", body: JSON.stringify(body) }); document.getElementById("revision-dialog").close(); state.selectedCase = payload; await loadCases(); await loadDashboard(); loadCase(payload.case.case_id); } catch (error) { document.getElementById("revision-form-error").textContent = error.message; }
}

async function submitSearch(event) { event.preventDefault(); const q = document.getElementById("search-query").value; const target = document.getElementById("search-results"); clear(target); try { const payload = await api(`/api/v1/search?q=${encodeURIComponent(q)}`); payload.items.forEach((item) => { const card = node("article", null, "card"); card.append(node("strong", `${item.kind}: ${item.title}`)); card.append(node("p", item.snippet)); if (item.kind === "research_case") { const open = node("button", "打开 Case"); open.addEventListener("click", () => { showView("cases"); loadCase(item.id); }); card.append(open); } target.append(card); }); if (!payload.items.length) target.append(node("p", "未找到匹配记录。", "muted")); } catch (error) { setStatus(`搜索失败：${error.message}`, true); } }

document.querySelectorAll(".sidebar button[data-view]").forEach((button) => button.addEventListener("click", () => showView(button.dataset.view)));
document.getElementById("refresh-dashboard").addEventListener("click", loadDashboard);
document.getElementById("new-case-button").addEventListener("click", () => openCaseDialog());
document.querySelectorAll(".create-type").forEach((button) => button.addEventListener("click", () => openCaseDialog(button.dataset.caseType)));
document.getElementById("case-type").addEventListener("change", updateCaseType);
document.getElementById("case-form").addEventListener("submit", submitCase);
document.getElementById("revision-form").addEventListener("submit", submitRevision);
document.getElementById("search-form").addEventListener("submit", submitSearch);
document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => document.getElementById(button.dataset.close).close()));
document.querySelectorAll(".evidence-filter").forEach((button) => button.addEventListener("click", () => { document.querySelectorAll(".evidence-filter").forEach((item) => item.classList.toggle("active", item === button)); loadEvidence(button.dataset.status); }));

Promise.all([loadDashboard(), loadCases(), loadEvidence(), loadDocumentsAndSources(), loadFeed()]);
