"use strict";

const SETTINGS_KEY = "aquantai.workbench.preferences.v1";
const DEFAULT_SETTINGS = {
  appearance: "system",
  density: "comfortable",
  marketColors: "red-up",
};

const workflowLabels = {
  draft: "范围草稿",
  candidate_build_ready: "待构建候选",
  awaiting_review: "待完成审阅",
  reviewed_plan_ready: "审阅计划已就绪",
  accepted_outputs_linked: "已关联正式输出",
  superseded: "已被后续版本替代",
  abandoned: "已停止",
};

const coverageLabels = {
  reviewed_local_scope: "当前已审阅本地范围全量",
  partial_local_coverage: "本地覆盖不完整",
  coverage_unknown: "覆盖范围未知",
};

const driverLabels = {
  demand_expansion: "需求扩张",
  supply_contraction_or_pricing: "供给收缩或涨价",
  policy_or_institutional_change: "政策或制度变化",
  technology_substitution: "技术替代",
  event_shock: "事件冲击",
  mixed: "混合驱动",
  other: "其他",
  unknown: "待确认",
};

const horizonLabels = {
  near_term: "短期",
  medium_term: "中期",
  long_term: "长期",
  custom: "自定义",
  unknown: "待确认",
};

const selectedMaps = new Map();
const selectedCompanies = new Map();
let editContext = null;
let formBusy = false;

function loadSettings() {
  try {
    const raw = window.localStorage.getItem(SETTINGS_KEY);
    if (!raw) return { ...DEFAULT_SETTINGS };
    const parsed = JSON.parse(raw);
    return {
      appearance: ["system", "light", "dark"].includes(parsed.appearance)
        ? parsed.appearance
        : DEFAULT_SETTINGS.appearance,
      density: ["comfortable", "compact"].includes(parsed.density)
        ? parsed.density
        : DEFAULT_SETTINGS.density,
      marketColors: ["red-up", "green-up"].includes(parsed.marketColors)
        ? parsed.marketColors
        : DEFAULT_SETTINGS.marketColors,
    };
  } catch (_error) {
    return { ...DEFAULT_SETTINGS };
  }
}

function applySettings(settings) {
  if (settings.appearance === "system") {
    document.documentElement.removeAttribute("data-appearance");
  } else {
    document.documentElement.dataset.appearance = settings.appearance;
  }
  document.documentElement.dataset.density = settings.density;
  document.documentElement.dataset.marketColors = settings.marketColors;
}

function saveSettings(settings) {
  window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  applySettings(settings);
}

function pad(value) {
  return String(value).padStart(2, "0");
}

function dateInputValue(value) {
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`;
}

function dateTimeInputValue(value) {
  return `${dateInputValue(value)}T${pad(value.getHours())}:${pad(value.getMinutes())}:${pad(value.getSeconds())}`;
}

function text(tag, value, className) {
  const node = document.createElement(tag);
  node.textContent = value;
  if (className) node.className = className;
  return node;
}

function setStatus(element, message, kind = "") {
  if (!element) return;
  element.textContent = message;
  element.className = `status-message${kind ? ` is-${kind}` : ""}`;
}

function selectPage() {
  const path = window.location.pathname;
  const page = path === "/workbench/settings"
    ? "settings"
    : path === "/industry-analysis/new"
      ? "new"
      : "history";
  document.querySelectorAll("[data-page]").forEach((node) => {
    node.hidden = node.dataset.page !== page;
  });
  const context = document.querySelector("#page-context");
  if (context) {
    context.textContent = page === "settings"
      ? "系统设置"
      : page === "new"
        ? "发起新研究"
        : "产业研究";
  }
  document.querySelectorAll(".nav-item[href]").forEach((node) => {
    const active = (page === "settings" && node.getAttribute("href") === "/workbench/settings")
      || (page !== "settings" && node.getAttribute("href") === "/industry-analysis");
    node.classList.toggle("nav-active", active);
    if (active) node.setAttribute("aria-current", "page");
    else node.removeAttribute("aria-current");
  });
  return page;
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
  const message = detail && typeof detail === "object"
    ? detail.message || detail.technical_message
    : detail;
  const error = new Error(message || `请求失败（${response.status}）`);
  error.status = response.status;
  error.code = detail && typeof detail === "object" ? detail.code : null;
  throw error;
}

async function loadBootstrap() {
  const state = document.querySelector("#database-state");
  try {
    const response = await fetch("/industry-analysis/api/bootstrap", {
      headers: { Accept: "application/json" },
    });
    const payload = await readJson(response);
    if (payload.database_available) {
      state.textContent = "本地数据可用";
      state.classList.add("is-ready");
    } else {
      state.textContent = "本地数据库未连接";
      state.classList.add("is-unavailable");
    }
  } catch (_error) {
    state.textContent = "工作台状态不可用";
    state.classList.add("is-unavailable");
  }
}

function technicalDetails(item) {
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "技术详情";
  details.appendChild(summary);
  const grid = document.createElement("div");
  grid.className = "technical-grid";
  const values = [
    ["Session ID", item.session_id],
    ["Revision ID", item.visible_latest_revision_id],
    ["Revision number", String(item.visible_latest_revision_number)],
    ["Input fingerprint", item.advanced_details.input_fingerprint_sha256],
    ["Supersedes", item.advanced_details.supersedes_revision_id || "无"],
  ];
  values.forEach(([label, value]) => {
    const row = document.createElement("span");
    row.textContent = `${label}: ${value}`;
    grid.appendChild(row);
  });
  details.appendChild(grid);
  return details;
}

function exactEditPath(item) {
  const query = new URLSearchParams({
    session_id: item.session_id,
    session_revision_id: item.visible_latest_revision_id,
    revision_number: String(item.visible_latest_revision_number),
    as_of_cutoff: item.information_cutoff_date,
    as_of_recorded_at_utc: item.recorded_at_utc,
  });
  return `/industry-analysis/new?${query.toString()}`;
}

function renderHistory(payload) {
  const list = document.querySelector("#history-list");
  const empty = document.querySelector("#history-empty");
  const summary = document.querySelector("#history-summary");
  list.replaceChildren();
  empty.hidden = payload.sessions.length !== 0;
  summary.textContent = payload.sessions.length === 0
    ? `在 ${payload.as_of_cutoff} / ${payload.as_of_recorded_at_utc} 边界内没有可见记录。`
    : `显示 ${payload.session_count} 条本地研究${payload.has_more ? "，仍有更多记录未显示" : ""}。`;

  payload.sessions.forEach((item) => {
    const card = document.createElement("article");
    card.className = "history-card";
    const body = document.createElement("div");
    body.appendChild(text("h3", item.thesis_title));
    body.appendChild(text("p", item.thesis_text_preview));

    const meta = document.createElement("div");
    meta.className = "history-meta";
    const workflow = text("span", workflowLabels[item.workflow_state] || item.workflow_state, "meta-chip");
    const coverage = text("span", coverageLabels[item.coverage_state] || item.coverage_state, "meta-chip");
    if (item.coverage_state !== "reviewed_local_scope") coverage.classList.add("is-warning");
    meta.append(
      workflow,
      coverage,
      text("span", driverLabels[item.driver_type] || item.driver_type, "meta-chip"),
      text("span", `可见修订 ${item.visible_revision_count}`, "meta-chip"),
    );
    body.appendChild(meta);
    body.appendChild(technicalDetails(item));

    const side = document.createElement("div");
    side.className = "history-side";
    side.appendChild(text("strong", `信息截止 ${item.information_cutoff_date}`));
    side.appendChild(text("small", `记录于 ${item.recorded_at_utc}`));
    if (item.next_surface === "scope") {
      const link = document.createElement("a");
      link.className = "button button-secondary history-action";
      link.href = exactEditPath(item);
      link.textContent = "继续编辑范围";
      side.appendChild(link);
    } else {
      const nextLabel = item.next_surface === "result"
        ? "精确结果页将在后续切片开放"
        : "候选审阅页将在后续切片开放";
      side.appendChild(text("small", nextLabel));
    }

    card.append(body, side);
    list.appendChild(card);
  });
}

async function loadHistory() {
  const status = document.querySelector("#history-status");
  const cutoff = document.querySelector("#as-of-cutoff").value;
  const localRecordedAt = document.querySelector("#as-of-recorded-at").value;
  const limit = document.querySelector("#history-limit").value;
  if (!cutoff || !localRecordedAt) {
    setStatus(status, "请填写两个读取边界。", "error");
    return;
  }
  const recordedAt = new Date(localRecordedAt);
  if (Number.isNaN(recordedAt.valueOf())) {
    setStatus(status, "系统记录时间格式无效。", "error");
    return;
  }
  setStatus(status, "正在读取本地研究历史……");
  const query = new URLSearchParams({
    as_of_cutoff: cutoff,
    as_of_recorded_at_utc: recordedAt.toISOString(),
    limit,
  });
  try {
    const response = await fetch(`/industry-analysis/api/sessions?${query.toString()}`, {
      headers: { Accept: "application/json" },
    });
    const payload = await readJson(response);
    renderHistory(payload);
    setStatus(status, "读取完成。", "success");
  } catch (error) {
    renderHistory({ sessions: [], session_count: 0, has_more: false, as_of_cutoff: cutoff, as_of_recorded_at_utc: recordedAt.toISOString() });
    setStatus(status, error.message || "本地研究历史读取失败。", "error");
  }
}

function setupHistory() {
  const now = new Date();
  document.querySelector("#as-of-cutoff").value = dateInputValue(now);
  document.querySelector("#as-of-recorded-at").value = dateTimeInputValue(now);
  document.querySelector("#history-form").addEventListener("submit", (event) => {
    event.preventDefault();
    loadHistory();
  });
  loadHistory();
}

function linesFrom(id) {
  return document.querySelector(id).value
    .split(/\r?\n/)
    .map((value) => value.trim())
    .filter(Boolean);
}

function optionBoundary() {
  const cutoff = document.querySelector("#scope-cutoff").value;
  const recordedAt = new Date();
  return new URLSearchParams({
    as_of_cutoff: cutoff,
    as_of_recorded_at_utc: recordedAt.toISOString(),
    limit: "20",
  });
}

function renderSelectedOptions(containerSelector, collection, emptyText) {
  const container = document.querySelector(containerSelector);
  container.replaceChildren();
  if (collection.size === 0) {
    container.appendChild(text("p", emptyText, "option-empty"));
    return;
  }
  collection.forEach((item, key) => {
    const chip = document.createElement("span");
    chip.className = "selected-chip";
    chip.appendChild(text("span", `${item.label || item.title}${item.code ? ` · ${item.code}` : ""}`));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.setAttribute("aria-label", `移除 ${item.label || item.title}`);
    remove.textContent = "×";
    remove.addEventListener("click", () => {
      collection.delete(key);
      renderSelectedOptions(containerSelector, collection, emptyText);
    });
    chip.appendChild(remove);
    container.appendChild(chip);
  });
}

function renderOptionResults(containerSelector, options, onSelect, emptyMessage) {
  const container = document.querySelector(containerSelector);
  container.replaceChildren();
  if (options.length === 0) {
    container.appendChild(text("p", emptyMessage, "option-empty"));
    return;
  }
  options.forEach((item) => {
    const row = document.createElement("div");
    row.className = "option-row";
    const description = document.createElement("div");
    description.appendChild(text("strong", item.label || item.title));
    const detail = item.code
      ? `${item.code} · ${item.market || "市场未知"}${item.industry ? ` · ${item.industry}` : ""}`
      : `${item.map_key} · 修订 ${item.revision_number}`;
    description.appendChild(text("small", detail));
    const select = document.createElement("button");
    select.type = "button";
    select.className = "button button-secondary";
    select.textContent = "明确选择";
    select.addEventListener("click", () => onSelect(item));
    row.append(description, select);
    container.appendChild(row);
  });
}

async function searchMaps() {
  const status = document.querySelector("#scope-status");
  if (!document.querySelector("#scope-cutoff").value) {
    setStatus(status, "请先填写信息截止日。", "error");
    return;
  }
  const query = optionBoundary();
  const value = document.querySelector("#map-query").value.trim();
  if (value) query.set("q", value);
  setStatus(status, "正在读取本地产业地图……");
  try {
    const response = await fetch(`/industry-analysis/api/local-options/maps?${query.toString()}`, {
      headers: { Accept: "application/json" },
    });
    const payload = await readJson(response);
    renderOptionResults("#map-results", payload.options, (item) => {
      selectedMaps.set(item.map_revision_id, item);
      renderSelectedOptions("#selected-maps", selectedMaps, "尚未选择产业地图。仍可保存为范围草稿。");
    }, "当前边界内没有匹配的本地产业地图。");
    setStatus(status, `找到 ${payload.option_count} 个精确地图选项。`, "success");
  } catch (error) {
    setStatus(status, error.message || "本地产业地图读取失败。", "error");
  }
}

async function searchCompanies() {
  const status = document.querySelector("#scope-status");
  const value = document.querySelector("#company-query").value.trim();
  if (!value) {
    setStatus(status, "请输入公司名称或完整证券代码。", "error");
    return;
  }
  if (!document.querySelector("#scope-cutoff").value) {
    setStatus(status, "请先填写信息截止日。", "error");
    return;
  }
  const query = optionBoundary();
  query.set("q", value);
  setStatus(status, "正在读取本地公司身份……");
  try {
    const response = await fetch(`/industry-analysis/api/local-options/companies?${query.toString()}`, {
      headers: { Accept: "application/json" },
    });
    const payload = await readJson(response);
    renderOptionResults("#company-results", payload.options, (item) => {
      selectedCompanies.set(`${item.source_kind}:${item.exact_id}`, item);
      renderSelectedOptions("#selected-companies", selectedCompanies, "尚未选择精确公司种子。仍可保存为范围草稿。");
    }, "当前边界内没有匹配的本地公司身份。");
    setStatus(status, `找到 ${payload.option_count} 个精确公司选项；系统未自动选择。`, "success");
  } catch (error) {
    setStatus(status, error.message || "本地公司身份读取失败。", "error");
  }
}

function buildScopePayload() {
  const thesis = document.querySelector("#thesis-text").value.trim();
  const cutoff = document.querySelector("#scope-cutoff").value;
  if (!thesis) throw new Error("请填写研究主题或判断。");
  if (!document.querySelector("#market-confirmed").checked) {
    throw new Error("请明确确认中国 A 股市场范围。");
  }
  if (!cutoff) throw new Error("请填写信息截止日。");

  const mapReferences = Array.from(selectedMaps.values()).map((item) => ({
    source_kind: "industry_map_revision",
    map_id: item.map_id,
    map_revision_id: item.map_revision_id,
    revision_number: item.revision_number,
    title: item.title,
  }));
  const companyReferences = Array.from(selectedCompanies.values()).map((item) => ({
    source_kind: item.source_kind,
    exact_id: item.exact_id,
    stock_basic_record_id: item.stock_basic_record_id,
    listed_instrument_id: item.listed_instrument_id,
    label: item.label,
    code: item.code,
  }));
  const chainText = document.querySelector("#chain-boundary").value.trim();
  const hasExactSource = mapReferences.length > 0 || companyReferences.length > 0;
  return {
    thesis_text_original: thesis,
    thesis_title_reviewed: document.querySelector("#thesis-title").value.trim() || null,
    driver_type: document.querySelector("#driver-type").value,
    analysis_horizon_kind: document.querySelector("#analysis-horizon").value,
    analysis_start_date: null,
    analysis_end_date: null,
    market_scope: [{
      market_namespace: "CN_A",
      exchange_namespace: null,
      security_type: "common_equity",
      include_status: "active",
      listed_instrument_ids: companyReferences
        .filter((item) => item.listed_instrument_id)
        .map((item) => item.listed_instrument_id),
    }],
    chain_boundary: {
      kind: "user_confirmed_text",
      text: chainText,
    },
    exclusions: linesFrom("#exclusions"),
    seed_companies: companyReferences,
    seed_products: linesFrom("#seed-products"),
    seed_technologies: linesFrom("#seed-technologies"),
    seed_bottlenecks: linesFrom("#seed-bottlenecks"),
    draft_graph: {
      exact_industry_map_references: mapReferences,
      nodes: [],
      relationships: [],
    },
    coverage_state: hasExactSource ? "partial_local_coverage" : "coverage_unknown",
    workflow_state: "draft",
    information_cutoff_date: cutoff,
    revision_note: document.querySelector("#revision-note").value.trim() || "通过个人研究工作台保存范围",
  };
}

function previewItem(label, value) {
  const item = document.createElement("div");
  item.className = "preview-item";
  item.append(text("strong", label), text("span", value || "未填写"));
  return item;
}

function renderScopePreview(payload, result) {
  const preview = document.querySelector("#scope-preview");
  preview.className = "preview-list";
  const maps = payload.draft_graph.exact_industry_map_references.map((item) => item.title).join("、") || "未选择";
  const companies = payload.seed_companies.map((item) => `${item.label}（${item.code}）`).join("、") || "未选择";
  preview.replaceChildren(
    previewItem("研究判断", payload.thesis_text_original),
    previewItem("研究标题", payload.thesis_title_reviewed),
    previewItem("市场范围", "中国 A 股普通股（已明确确认）"),
    previewItem("驱动类型", driverLabels[payload.driver_type] || payload.driver_type),
    previewItem("研究周期", horizonLabels[payload.analysis_horizon_kind] || payload.analysis_horizon_kind),
    previewItem("产业链边界", payload.chain_boundary.text),
    previewItem("精确产业地图", maps),
    previewItem("精确公司种子", companies),
    previewItem("信息截止日", payload.information_cutoff_date),
    previewItem("覆盖声明", payload.coverage_state === "coverage_unknown" ? "覆盖范围未知；当前只有文字草稿" : "本地覆盖不完整；只使用已明确选择的本地范围"),
    previewItem("检查结果", result ? `可生成修订 ${result.revision_number}；指纹 ${result.input_fingerprint_sha256}` : "尚未执行服务端检查"),
  );
}

function setFormBusy(busy, label = "") {
  formBusy = busy;
  const check = document.querySelector("#scope-check-button");
  const save = document.querySelector("#scope-save-button");
  check.disabled = busy;
  save.disabled = busy;
  check.textContent = busy ? label || "正在处理……" : "检查研究范围";
  save.textContent = busy ? label || "正在处理……" : editContext ? "保存范围修订" : "保存研究主题";
}

function commandRequest(payload, dryRun) {
  if (editContext) {
    return {
      path: `/industry-analysis/api/sessions/${encodeURIComponent(editContext.sessionId)}/revisions?dry_run=${dryRun ? "true" : "false"}`,
      body: {
        expected_latest_revision_number: editContext.revisionNumber,
        changes: payload,
        revision_note: payload.revision_note,
      },
    };
  }
  return {
    path: `/industry-analysis/api/sessions?dry_run=${dryRun ? "true" : "false"}`,
    body: payload,
  };
}

async function submitScope(dryRun) {
  if (formBusy) return;
  const status = document.querySelector("#scope-status");
  const success = document.querySelector("#scope-success");
  success.hidden = true;
  try {
    const payload = buildScopePayload();
    renderScopePreview(payload, null);
    const request = commandRequest(payload, dryRun);
    setFormBusy(true, dryRun ? "正在检查……" : "正在保存……");
    setStatus(status, dryRun ? "正在执行服务端范围检查……" : "正在写入本地追加式研究历史……");
    const response = await fetch(request.path, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request.body),
    });
    const result = await readJson(response);
    renderScopePreview(payload, result);
    if (dryRun) {
      setStatus(status, "检查通过。尚未创建或修改任何本地记录。", "success");
      return;
    }
    editContext = {
      sessionId: result.session_id,
      sessionRevisionId: result.session_revision_id,
      revisionNumber: result.revision_number,
      asOfCutoff: result.information_cutoff_date,
      asOfRecordedAtUtc: result.recorded_at_utc,
    };
    success.hidden = false;
    success.replaceChildren(
      text("h3", result.revision_number === 1 ? "研究主题已保存" : "研究范围修订已保存"),
      text("p", "该记录已写入本地追加式历史。候选公司池尚未构建。"),
    );
    const actions = document.createElement("div");
    actions.className = "button-row";
    const history = document.createElement("a");
    history.className = "button button-secondary";
    history.href = result.history_path;
    history.textContent = "返回研究历史";
    const continueEdit = document.createElement("a");
    continueEdit.className = "button button-secondary";
    continueEdit.href = result.edit_scope_path;
    continueEdit.textContent = "继续编辑当前范围";
    actions.append(history, continueEdit);
    success.appendChild(actions);
    const details = document.createElement("details");
    details.appendChild(text("summary", "技术详情"));
    const technical = document.createElement("div");
    technical.className = "technical-grid";
    [
      ["Session ID", result.session_id],
      ["Revision ID", result.session_revision_id],
      ["Revision number", String(result.revision_number)],
      ["Recorded UTC", result.recorded_at_utc],
      ["Input fingerprint", result.input_fingerprint_sha256],
    ].forEach(([label, value]) => technical.appendChild(text("span", `${label}: ${value}`)));
    details.appendChild(technical);
    success.appendChild(details);
    setStatus(status, "保存完成。不会自动构建候选或接受任何公司。", "success");
  } catch (error) {
    const conflict = error.status === 409
      ? " 页面已保留你的输入；请返回历史重新读取精确版本后再确认。"
      : " 页面已保留你的输入。";
    setStatus(status, `${error.message || "研究范围处理失败。"}${conflict}`, "error");
  } finally {
    setFormBusy(false);
  }
}

function fillScopeForm(revision) {
  document.querySelector("#thesis-text").value = revision.thesis_text_original;
  document.querySelector("#thesis-title").value = revision.thesis_title_reviewed || "";
  document.querySelector("#market-confirmed").checked = true;
  document.querySelector("#driver-type").value = revision.driver_type;
  document.querySelector("#analysis-horizon").value = revision.analysis_horizon_kind;
  document.querySelector("#scope-cutoff").value = revision.information_cutoff_date;
  document.querySelector("#chain-boundary").value = revision.chain_boundary && revision.chain_boundary.text
    ? revision.chain_boundary.text
    : "";
  document.querySelector("#seed-products").value = Array.isArray(revision.seed_products) ? revision.seed_products.join("\n") : "";
  document.querySelector("#seed-technologies").value = Array.isArray(revision.seed_technologies) ? revision.seed_technologies.join("\n") : "";
  document.querySelector("#seed-bottlenecks").value = Array.isArray(revision.seed_bottlenecks) ? revision.seed_bottlenecks.join("\n") : "";
  document.querySelector("#exclusions").value = Array.isArray(revision.exclusions) ? revision.exclusions.join("\n") : "";
  document.querySelector("#revision-note").value = `修订本地研究范围（基于 revision ${revision.revision_number}）`;

  selectedMaps.clear();
  const mapReferences = revision.draft_graph && Array.isArray(revision.draft_graph.exact_industry_map_references)
    ? revision.draft_graph.exact_industry_map_references
    : [];
  mapReferences.forEach((item) => selectedMaps.set(item.map_revision_id, item));
  selectedCompanies.clear();
  if (Array.isArray(revision.seed_companies)) {
    revision.seed_companies.forEach((item) => {
      const exactId = item.listed_instrument_id || String(item.stock_basic_record_id);
      selectedCompanies.set(`${item.source_kind}:${exactId}`, { ...item, exact_id: exactId });
    });
  }
  renderSelectedOptions("#selected-maps", selectedMaps, "尚未选择产业地图。仍可保存为范围草稿。");
  renderSelectedOptions("#selected-companies", selectedCompanies, "尚未选择精确公司种子。仍可保存为范围草稿。");
}

async function loadEditContext() {
  const params = new URLSearchParams(window.location.search);
  const required = ["session_id", "session_revision_id", "revision_number", "as_of_cutoff", "as_of_recorded_at_utc"];
  const hasAny = required.some((name) => params.has(name));
  if (!hasAny) return;
  if (!required.every((name) => params.has(name))) {
    throw new Error("编辑链接不完整。请从研究历史重新进入。 ");
  }
  const revisionNumber = Number(params.get("revision_number"));
  if (!Number.isInteger(revisionNumber) || revisionNumber < 1) {
    throw new Error("编辑链接中的修订编号无效。 ");
  }
  const context = {
    sessionId: params.get("session_id"),
    sessionRevisionId: params.get("session_revision_id"),
    revisionNumber,
    asOfCutoff: params.get("as_of_cutoff"),
    asOfRecordedAtUtc: params.get("as_of_recorded_at_utc"),
  };
  const query = new URLSearchParams({
    as_of_cutoff: context.asOfCutoff,
    as_of_recorded_at_utc: context.asOfRecordedAtUtc,
  });
  const response = await fetch(`/industry-analysis/api/session-revisions/${encodeURIComponent(context.sessionRevisionId)}?${query.toString()}`, {
    headers: { Accept: "application/json" },
  });
  const revision = await readJson(response);
  if (revision.session_id !== context.sessionId
      || revision.session_revision_id !== context.sessionRevisionId
      || revision.revision_number !== context.revisionNumber) {
    throw new Error("编辑链接与精确研究修订不匹配。 ");
  }
  editContext = context;
  fillScopeForm(revision);
  document.querySelector("#scope-page-title").textContent = "编辑研究范围";
  document.querySelector("#scope-mode-notice").hidden = false;
  document.querySelector("#scope-mode-notice").replaceChildren(
    text("strong", `正在编辑 revision ${revision.revision_number}`),
    text("p", "保存将追加新的修订，不会覆盖已有历史。浏览器不会自动切换到更新版本。"),
  );
  document.querySelector("#scope-save-button").textContent = "保存范围修订";
}

async function setupScopeForm() {
  document.querySelector("#scope-cutoff").value = dateInputValue(new Date());
  renderSelectedOptions("#selected-maps", selectedMaps, "尚未选择产业地图。仍可保存为范围草稿。");
  renderSelectedOptions("#selected-companies", selectedCompanies, "尚未选择精确公司种子。仍可保存为范围草稿。");
  document.querySelector("#map-search-button").addEventListener("click", searchMaps);
  document.querySelector("#company-search-button").addEventListener("click", searchCompanies);
  document.querySelector("#scope-check-button").addEventListener("click", () => submitScope(true));
  document.querySelector("#scope-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submitScope(false);
  });
  try {
    await loadEditContext();
  } catch (error) {
    setStatus(document.querySelector("#scope-status"), error.message || "精确研究修订读取失败。", "error");
    document.querySelector("#scope-save-button").disabled = true;
  }
}

function setupSettings() {
  const settings = loadSettings();
  document.querySelector("#appearance-setting").value = settings.appearance;
  document.querySelector("#density-setting").value = settings.density;
  document.querySelector("#market-colors-setting").value = settings.marketColors;
  document.querySelector("#settings-form").addEventListener("submit", (event) => {
    event.preventDefault();
    saveSettings({
      appearance: document.querySelector("#appearance-setting").value,
      density: document.querySelector("#density-setting").value,
      marketColors: document.querySelector("#market-colors-setting").value,
    });
    setStatus(document.querySelector("#settings-status"), "显示偏好已保存到当前浏览器。", "success");
  });
}

const settings = loadSettings();
applySettings(settings);
const currentPage = selectPage();
loadBootstrap();
if (currentPage === "history") setupHistory();
if (currentPage === "new") setupScopeForm();
if (currentPage === "settings") setupSettings();
