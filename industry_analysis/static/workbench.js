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

async function loadBootstrap() {
  const state = document.querySelector("#database-state");
  try {
    const response = await fetch("/industry-analysis/api/bootstrap", {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error("bootstrap unavailable");
    const payload = await response.json();
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
    const nextLabel = item.next_surface === "result"
      ? "精确结果页将在后续切片开放"
      : item.next_surface === "review"
        ? "候选审阅页将在后续切片开放"
        : "可在范围页面继续整理";
    side.appendChild(text("small", nextLabel));

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
    const payload = await response.json();
    if (!response.ok) {
      const detail = payload.detail && typeof payload.detail === "object"
        ? payload.detail.message
        : payload.detail;
      throw new Error(detail || "本地研究历史读取失败");
    }
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

function previewItem(label, value) {
  const item = document.createElement("div");
  item.className = "preview-item";
  item.append(text("strong", label), text("span", value || "未填写"));
  return item;
}

function setupScopePreview() {
  document.querySelector("#scope-cutoff").value = dateInputValue(new Date());
  document.querySelector("#scope-preview-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const thesis = document.querySelector("#thesis-text").value.trim();
    if (!thesis) return;
    const preview = document.querySelector("#scope-preview");
    preview.className = "preview-list";
    preview.replaceChildren(
      previewItem("研究判断", thesis),
      previewItem("市场范围", document.querySelector("#market-scope").value),
      previewItem("驱动类型", document.querySelector("#driver-type").value),
      previewItem("研究周期", document.querySelector("#analysis-horizon").value),
      previewItem("产业链边界", document.querySelector("#chain-boundary").value.trim()),
      previewItem("明确排除", document.querySelector("#exclusions").value.trim()),
      previewItem("信息截止日", document.querySelector("#scope-cutoff").value),
      previewItem("覆盖声明", "尚未选择精确本地产业地图或公司身份，不能声明全市场覆盖。"),
    );
  });
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
if (currentPage === "new") setupScopePreview();
if (currentPage === "settings") setupSettings();
