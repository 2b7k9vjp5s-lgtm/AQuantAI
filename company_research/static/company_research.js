"use strict";

const researchSelect = document.querySelector("#researchSelect");
const cutoffInput = document.querySelector("#cutoffInput");
const loadButton = document.querySelector("#loadButton");
const selectorStatus = document.querySelector("#selectorStatus");
const workspaceState = document.querySelector("#workspaceState");
const workspace = document.querySelector("#workspace");
const detailOutput = document.querySelector("#detailOutput");
const researchDetailButton = document.querySelector("#researchDetailButton");
const aiPreviewButton = document.querySelector("#aiPreviewButton");
const aiConfirmCheckbox = document.querySelector("#aiConfirmCheckbox");
const aiGenerateButton = document.querySelector("#aiGenerateButton");
const aiStatus = document.querySelector("#aiStatus");
const aiPreviewContent = document.querySelector("#aiPreviewContent");
const aiDraftOutput = document.querySelector("#aiDraftOutput");

let selectorRows = [];
let activeWorkspace = null;
let activeAIPreview = null;

const aiSectionLabels = {
  evidence_grounded_summary: "证据约束摘要",
  supporting_evidence: "支持性证据",
  conflicting_evidence: "冲突证据",
  missing_evidence: "缺失证据",
  revision_and_provenance_warnings: "修订与来源提醒",
  research_questions: "后续研究问题",
  human_review_checklist: "人工核验清单",
  limitations: "限制说明",
};

function apiUrl(path) {
  const url = new URL(path, window.location.origin);
  if (cutoffInput.value) url.searchParams.set("as_of_cutoff", cutoffInput.value);
  return url;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, { credentials: "same-origin", ...options });
  if (!response.ok) {
    let message = `请求失败（${response.status}）`;
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") message = payload.detail;
      else if (payload.detail && typeof payload.detail.message === "string") message = payload.detail.message;
    } catch (_error) {
      // Keep the credential-safe generic message.
    }
    throw new Error(message);
  }
  return response.json();
}

function fetchJson(url) {
  return requestJson(url, { method: "GET" });
}

function clear(node) {
  node.replaceChildren();
}

function text(tag, value, className) {
  const node = document.createElement(tag);
  node.textContent = value === null || value === undefined || value === "" ? "—" : String(value);
  if (className) node.className = className;
  return node;
}

function dataGrid(values) {
  const grid = document.createElement("dl");
  grid.className = "data-grid";
  Object.entries(values).forEach(([label, value]) => {
    const item = document.createElement("div");
    item.className = "data-item";
    item.append(text("dt", label), text("dd", value));
    grid.append(item);
  });
  return grid;
}

function appendGrid(target, values) {
  clear(target);
  target.append(dataGrid(values));
}

function section(target, title, values) {
  const wrapper = document.createElement("div");
  wrapper.className = "subsection";
  wrapper.append(text("h3", title), dataGrid(values));
  target.append(wrapper);
}

function latest(item) {
  return item.latest_revision || {};
}

function moduleCard(moduleName, item) {
  const revision = latest(item);
  const card = document.createElement("article");
  card.className = "card";
  card.append(text("h3", item.key || moduleName));
  card.append(text("p", `ID：${item.hypothesis_id || item.expectation_id || item.valuation_id || item.catalyst_id || item.risk_id || item.judgment_id}`, "meta"));
  card.append(dataGrid({
    "修订": revision.revision_no,
    "修订 ID": revision.revision_id,
    "信息截止日": revision.information_cutoff_date,
    "记录 UTC": revision.recorded_at_utc,
    "状态": revision.status || revision.hypothesis_status || revision.outcome,
    "置信度": revision.confidence,
    "主题/问题": revision.subject || revision.mechanism || revision.rationale,
    "冻结公司研究修订": revision.company_research_revision_id || (revision.frozen_company_research_revision_ids || []).join(", "),
    "冲突数量": revision.evidence_summary ? revision.evidence_summary.conflict_count : 0,
    "缺失证据数量": revision.evidence_summary ? revision.evidence_summary.missing_evidence_count : 0,
  }));
  if (revision.historical_revision_mismatch) {
    card.append(text("p", "历史修订不一致：该记录冻结于较早公司研究修订，未自动重绑。", "mismatch"));
  }
  if (revision.price_reference) {
    const price = revision.price_reference;
    card.append(dataGrid({
      "本地价格语义": price.semantic_level,
      "交易日": price.trade_date,
      "收盘记录": price.close,
      "价格来源": price.source,
      "价格导入批次": price.ingestion_run_id,
    }));
  }
  const button = text("button", "按需查看完整详情", "secondary");
  button.type = "button";
  button.addEventListener("click", () => loadDetail(item.detail_path, `${moduleName} · ${item.key}`));
  card.append(button);
  return card;
}

function renderModule(targetId, moduleName, items) {
  const target = document.querySelector(targetId);
  clear(target);
  if (!Array.isArray(items) || items.length === 0) {
    target.append(text("p", "当前截止条件下无已持久化记录。不会自动补全或推断。", "empty"));
    return;
  }
  const cards = document.createElement("div");
  cards.className = "cards";
  items.forEach((item) => cards.append(moduleCard(moduleName, item)));
  target.append(cards);
}

function resetGuardedAI() {
  activeAIPreview = null;
  aiConfirmCheckbox.checked = false;
  aiConfirmCheckbox.disabled = true;
  aiGenerateButton.disabled = true;
  aiPreviewButton.disabled = activeWorkspace === null;
  aiStatus.className = "status";
  aiStatus.textContent = "尚未生成本地输入预览。页面加载和普通读取不会调用模型。";
  clear(aiPreviewContent);
  clear(aiDraftOutput);
}

function renderWorkspace(payload) {
  activeWorkspace = payload;
  workspaceState.hidden = true;
  workspace.hidden = false;
  detailOutput.textContent = "尚未加载完整详情。";
  resetGuardedAI();

  appendGrid(document.querySelector("#identityGrid"), {
    "公司研究 ID": payload.identity.company_research_id,
    "股票": `${payload.identity.stock_code} ${payload.identity.stock_name}`,
    "来源": payload.identity.source,
    "交易所": payload.identity.exchange,
    "Provider 行业": payload.identity.provider_industry,
    "Case ID": payload.identity.case_id,
    "Map ID": payload.identity.map_id,
    "创建 UTC": payload.identity.created_at_utc,
    "请求截止日": payload.as_of_cutoff,
  });

  const stage1 = document.querySelector("#stage1Content");
  clear(stage1);
  section(stage1, "候选池", {
    "候选池 ID": payload.frozen_stage1.candidate_pool.candidate_pool_id,
    "候选池 Key": payload.frozen_stage1.candidate_pool.pool_key,
    "冻结候选池修订 ID": payload.frozen_stage1.candidate_pool_revision.revision_id,
    "修订号": payload.frozen_stage1.candidate_pool_revision.revision_no,
    "范围": payload.frozen_stage1.candidate_pool_revision.scope,
  });
  section(stage1, "Stage 1 受益公司", {
    "Beneficiary ID": payload.frozen_stage1.beneficiary.beneficiary_id,
    "冻结受益修订 ID": payload.frozen_stage1.beneficiary_revision.revision_id,
    "原始受益类型": payload.frozen_stage1.beneficiary_revision.beneficiary_kind,
    "原始评估状态": payload.frozen_stage1.beneficiary_revision.assessment_status,
    "分析理由": payload.frozen_stage1.beneficiary_revision.rationale_summary,
    "冻结地图修订 ID": payload.frozen_stage1.selected_map_revision.revision_id,
  });
  section(stage1, "数据来源", {
    "Stock Basic ID": payload.frozen_stage1.stock.stock_basic_record_id,
    "导入 Run ID": payload.frozen_stage1.ingestion_run.ingestion_run_id,
    "Provider": payload.frozen_stage1.ingestion_run.provider,
    "Dataset": payload.frozen_stage1.ingestion_run.dataset,
    "数据截止日": payload.frozen_stage1.ingestion_run.information_cutoff_date,
    "完成 UTC": payload.frozen_stage1.ingestion_run.completed_at_utc,
    "Handoff assertion / claim / evidence": `${payload.frozen_stage1.handoff.assertion_count} / ${payload.frozen_stage1.handoff.claim_count} / ${payload.frozen_stage1.handoff.evidence_count}`,
  });

  const research = document.querySelector("#researchContent");
  clear(research);
  section(research, "当前最新可见修订", {
    "修订 ID": payload.company_research.latest_revision.revision_id,
    "修订号": payload.company_research.latest_revision.revision_no,
    "工作流状态": payload.company_research.latest_revision.workflow_state,
    "结论状态": payload.company_research.latest_revision.conclusion_status,
    "研究问题": payload.company_research.latest_revision.research_question,
    "摘要": payload.company_research.latest_revision.summary,
    "信息截止日": payload.company_research.latest_revision.information_cutoff_date,
    "记录 UTC": payload.company_research.latest_revision.recorded_at_utc,
  });
  section(research, "历史与验证", {
    "可见修订数量": payload.company_research.revision_history.length,
    "验证项数量": payload.company_research.verification_count,
    "可见修订 ID": payload.company_research.revision_history.map((item) => item.revision_id).join(", "),
  });

  const evidence = payload.evidence_summary;
  appendGrid(document.querySelector("#evidenceSummary"), {
    "证据等级 A / B / C / D": ["A", "B", "C", "D"].map((grade) => evidence.evidence_grade_counts[grade] || 0).join(" / "),
    "冲突数量": evidence.conflict_count,
    "缺失证据数量": evidence.missing_evidence_count,
    "说明": "这些是确定性统计，不是评分或排名。",
  });

  renderModule("#hypotheses", "财务传导假设", payload.hypotheses);
  renderModule("#expectations", "市场预期", payload.expectations);
  renderModule("#valuations", "估值观察", payload.valuation_observations);
  renderModule("#catalysts", "催化剂", payload.catalysts);
  renderModule("#risks", "风险", payload.risks);
  renderModule("#industryJudgments", "产业质量判断", payload.industry_judgments);
  renderModule("#companyJudgments", "公司质量判断", payload.company_judgments);
}

function renderAIPreview(payload) {
  clear(aiPreviewContent);
  const provider = payload.provider || {};
  aiPreviewContent.append(dataGrid({
    "公司研究 ID": payload.company_research_id,
    "截止日": payload.as_of_cutoff,
    "输入指纹": payload.manifest_fingerprint,
    "输入字符数 / 上限": `${payload.input_character_count} / ${payload.maximum_input_characters}`,
    "已包含部分": (payload.included_sections || []).join(", "),
    "不可用部分": (payload.unavailable_sections || []).join(", ") || "无",
    "远程功能已启用": provider.enabled,
    "配置可用": provider.available,
    "Provider": provider.provider_id,
    "Model": provider.model_id,
    "数据使用说明": provider.data_use_notice,
    "费用提示": provider.cost_estimate,
  }));
  const manifestTitle = text("h3", "本次将发送的确定性清单");
  const manifestOutput = document.createElement("pre");
  manifestOutput.tabIndex = 0;
  manifestOutput.textContent = JSON.stringify(payload.manifest, null, 2);
  aiPreviewContent.append(manifestTitle, manifestOutput);
}

async function previewGuardedAIInput() {
  if (!activeWorkspace) return;
  const researchId = activeWorkspace.identity.company_research_id;
  aiPreviewButton.disabled = true;
  aiGenerateButton.disabled = true;
  aiConfirmCheckbox.checked = false;
  aiConfirmCheckbox.disabled = true;
  aiStatus.className = "status";
  aiStatus.textContent = "正在本地重建确定性输入，不会调用模型……";
  clear(aiDraftOutput);
  try {
    const payload = await fetchJson(apiUrl(`/company-research/research/${researchId}/ai-draft-input`));
    activeAIPreview = payload;
    renderAIPreview(payload);
    const available = Boolean(payload.provider && payload.provider.available);
    aiConfirmCheckbox.disabled = !available;
    aiStatus.textContent = available
      ? "本地输入预览完成。请检查清单、模型和数据使用说明后再确认传输。"
      : "本地输入预览完成，但 Guarded AI 未启用或配置不完整；没有发送任何数据。";
  } catch (error) {
    activeAIPreview = null;
    aiStatus.className = "status error";
    aiStatus.textContent = `AI 输入预览失败：${error.message}`;
  } finally {
    aiPreviewButton.disabled = false;
  }
}

function renderAIDraft(payload) {
  clear(aiDraftOutput);
  aiDraftOutput.append(text("h3", payload.notices && payload.notices.draft_label
    ? payload.notices.draft_label
    : "AI 研究草稿（D3，需人工核验，不构成投资建议）"));
  aiDraftOutput.append(dataGrid({
    "输入指纹": payload.manifest_fingerprint,
    "Provider": payload.provider_id,
    "Model": payload.model_id,
    "Adapter": payload.adapter_version,
    "Prompt 模板": payload.prompt_template_version,
    "生成 UTC": payload.generated_at_utc,
  }));
  Object.entries(aiSectionLabels).forEach(([sectionName, label]) => {
    const wrapper = document.createElement("div");
    wrapper.className = "subsection";
    wrapper.append(text("h3", label));
    const entries = payload.sections && Array.isArray(payload.sections[sectionName])
      ? payload.sections[sectionName]
      : [];
    if (entries.length === 0) {
      wrapper.append(text("p", "本节无草稿内容。", "empty"));
    } else {
      const cards = document.createElement("div");
      cards.className = "cards";
      entries.forEach((entry) => {
        const card = document.createElement("article");
        card.className = "card";
        card.append(text("p", entry.text));
        card.append(text("p", `引用清单项：${(entry.manifest_item_ids || []).join(", ") || "无"}`, "meta"));
        cards.append(card);
      });
      wrapper.append(cards);
    }
    aiDraftOutput.append(wrapper);
  });
}

async function generateGuardedAIDraft() {
  if (!activeWorkspace || !activeAIPreview || !aiConfirmCheckbox.checked) return;
  const researchId = activeWorkspace.identity.company_research_id;
  aiPreviewButton.disabled = true;
  aiGenerateButton.disabled = true;
  aiConfirmCheckbox.disabled = true;
  aiStatus.className = "status";
  aiStatus.textContent = "正在向已显示的单一模型配置发送一次请求；不会重试或回退……";
  try {
    const payload = await requestJson(apiUrl(`/company-research/research/${researchId}/ai-drafts`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        expected_manifest_fingerprint: activeAIPreview.manifest_fingerprint,
        confirm_remote_transmission: true,
      }),
    });
    renderAIDraft(payload);
    aiStatus.textContent = "AI 研究草稿已通过结构、指纹和引用校验。结果仅存在于当前页面。";
  } catch (error) {
    clear(aiDraftOutput);
    aiStatus.className = "status error";
    aiStatus.textContent = `AI 草稿生成失败：${error.message}`;
  } finally {
    aiPreviewButton.disabled = false;
    aiConfirmCheckbox.disabled = !(activeAIPreview.provider && activeAIPreview.provider.available);
    aiGenerateButton.disabled = !aiConfirmCheckbox.checked || aiConfirmCheckbox.disabled;
  }
}

async function loadDetail(path, label) {
  detailOutput.textContent = `正在加载：${label}……`;
  try {
    const payload = await fetchJson(apiUrl(path));
    detailOutput.textContent = JSON.stringify(payload, null, 2);
  } catch (error) {
    detailOutput.textContent = `详情加载失败：${error.message}`;
  }
}

async function loadSelector() {
  selectorStatus.className = "status";
  selectorStatus.textContent = "正在加载可选研究身份……";
  loadButton.disabled = true;
  activeWorkspace = null;
  resetGuardedAI();
  try {
    const payload = await fetchJson(apiUrl("/company-research/research"));
    selectorRows = Array.isArray(payload.research) ? payload.research : [];
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "请选择公司研究";
    const options = selectorRows.map((row) => {
      const option = document.createElement("option");
      option.value = row.company_research_id;
      option.textContent = `${row.source} · ${row.stock_code} ${row.stock_name} · 研究修订 ${row.latest_revision.revision_no}`;
      return option;
    });
    researchSelect.replaceChildren(placeholder, ...options);
    researchSelect.value = "";

    const preferred = new URL(window.location.href).searchParams.get("company_research_id");
    if (preferred && selectorRows.some((row) => row.company_research_id === preferred)) {
      researchSelect.value = preferred;
      selectorStatus.textContent = `已按 URL 中明确指定的 company_research_id 选择记录，共 ${selectorRows.length} 条可选记录。`;
      await loadWorkspace();
    } else {
      selectorStatus.textContent = selectorRows.length
        ? `已加载 ${selectorRows.length} 条可选研究身份，请明确选择。`
        : "当前截止条件下无可选研究身份。";
    }
  } catch (error) {
    selectorStatus.className = "status error";
    selectorStatus.textContent = `选择器加载失败：${error.message}`;
  } finally {
    loadButton.disabled = false;
  }
}

async function loadWorkspace() {
  const researchId = researchSelect.value;
  if (!researchId) {
    selectorStatus.className = "status error";
    selectorStatus.textContent = "请选择公司研究后再加载。";
    researchSelect.focus();
    return;
  }
  selectorStatus.className = "status";
  selectorStatus.textContent = "正在加载单公司工作台……";
  loadButton.disabled = true;
  activeWorkspace = null;
  resetGuardedAI();
  workspace.hidden = true;
  workspaceState.hidden = false;
  workspaceState.replaceChildren(text("h2", "正在读取持久化研究记录"), text("p", "只读取明确选择的 company_research_id。"));
  try {
    const payload = await fetchJson(apiUrl(`/company-research/research/${researchId}/workspace`));
    renderWorkspace(payload);
    selectorStatus.textContent = "工作台加载完成。";
    const url = new URL(window.location.href);
    url.searchParams.set("company_research_id", researchId);
    if (cutoffInput.value) url.searchParams.set("as_of_cutoff", cutoffInput.value);
    else url.searchParams.delete("as_of_cutoff");
    window.history.replaceState({}, "", url);
  } catch (error) {
    workspaceState.hidden = false;
    workspaceState.replaceChildren(text("h2", "工作台加载失败"), text("p", error.message));
    selectorStatus.className = "status error";
    selectorStatus.textContent = `加载失败：${error.message}`;
  } finally {
    loadButton.disabled = false;
  }
}

loadButton.addEventListener("click", loadWorkspace);
cutoffInput.addEventListener("change", loadSelector);
researchSelect.addEventListener("change", () => {
  activeWorkspace = null;
  resetGuardedAI();
});
researchDetailButton.addEventListener("click", () => {
  if (activeWorkspace) loadDetail(activeWorkspace.company_research.detail_path, "完整公司研究图");
});
aiPreviewButton.addEventListener("click", previewGuardedAIInput);
aiConfirmCheckbox.addEventListener("change", () => {
  aiGenerateButton.disabled = !aiConfirmCheckbox.checked || !activeAIPreview;
});
aiGenerateButton.addEventListener("click", generateGuardedAIDraft);

const initialCutoff = new URL(window.location.href).searchParams.get("as_of_cutoff");
if (initialCutoff) cutoffInput.value = initialCutoff;
resetGuardedAI();
loadSelector();
