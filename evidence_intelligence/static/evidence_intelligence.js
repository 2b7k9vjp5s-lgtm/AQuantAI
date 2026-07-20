"use strict";

const API_PATH = "/evidence-intelligence/feed";
const EVENT_LABELS = Object.freeze({
  evidence: "新增证据",
  case_revision: "研究案例修订",
  industry_map_revision: "产业地图修订",
  company_research_revision: "公司研究修订",
});

const $ = (selector) => document.querySelector(selector);
const form = $("#feed-filters");
const resetButton = $("#reset-filters");
const loadMoreButton = $("#load-more");
const feedList = $("#feed-list");
const emptyState = $("#empty-state");
const statusBadge = $("#status-badge");
const loadStatus = $("#load-status");
const loadError = $("#load-error");
const queryMetadata = $("#query-metadata");

let nextCursor = null;
let activeRequestId = 0;

form.addEventListener("submit", (event) => {
  event.preventDefault();
  void loadFeed(false);
});

resetButton.addEventListener("click", () => {
  form.reset();
  $("#limit").value = "50";
  void loadFeed(false);
});

loadMoreButton.addEventListener("click", () => {
  if (nextCursor) {
    void loadFeed(true);
  }
});

void loadFeed(false);

async function loadFeed(append) {
  const requestId = ++activeRequestId;
  setBusy(true, append ? "正在加载更多研究变化。" : "正在读取本地研究变化。");
  clearError();
  if (!append) {
    nextCursor = null;
    feedList.replaceChildren();
    emptyState.hidden = true;
    queryMetadata.replaceChildren();
  }

  try {
    const response = await fetch(buildRequestUrl(append ? nextCursor : null), {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    const payload = await readPayload(response);
    if (!response.ok) {
      throw new Error(errorMessage(payload, response.status));
    }
    if (requestId !== activeRequestId) {
      return;
    }

    renderMetadata(payload);
    renderEvents(Array.isArray(payload.events) ? payload.events : [], append);
    nextCursor = typeof payload.next_cursor === "string" ? payload.next_cursor : null;
    loadMoreButton.hidden = !nextCursor;
    statusBadge.dataset.state = "ready";
    statusBadge.textContent = "已就绪";
    const count = Array.isArray(payload.events) ? payload.events.length : 0;
    loadStatus.textContent = append
      ? `已追加 ${count} 条记录。`
      : `当前页读取 ${count} 条记录。变化记录仅表示研究时间线。`;
  } catch (error) {
    if (requestId === activeRequestId) {
      showError(error instanceof Error ? error.message : "无法读取研究变化。");
    }
  } finally {
    if (requestId === activeRequestId) {
      setBusy(false);
    }
  }
}

function buildRequestUrl(cursor) {
  const params = new URLSearchParams();
  const values = {
    event_type: $("#event-type").value,
    recorded_from: $("#recorded-from").value,
    recorded_to: $("#recorded-to").value,
    as_of_cutoff: $("#as-of-cutoff").value,
    limit: $("#limit").value || "50",
  };

  if (values.event_type) {
    params.set("event_type", values.event_type);
  }
  if (values.recorded_from) {
    params.set("recorded_from", localInputToIso(values.recorded_from, "记录起点"));
  }
  if (values.recorded_to) {
    params.set("recorded_to", localInputToIso(values.recorded_to, "记录终点"));
  }
  if (values.as_of_cutoff) {
    params.set("as_of_cutoff", values.as_of_cutoff);
  }
  params.set("limit", values.limit);
  if (cursor) {
    params.set("cursor", cursor);
  }
  return `${API_PATH}?${params.toString()}`;
}

function localInputToIso(value, label) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error(`${label}不是有效时间。`);
  }
  return parsed.toISOString();
}

async function readPayload(response) {
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json")
    ? response.json()
    : { detail: await response.text() };
}

function errorMessage(payload, status) {
  return payload && typeof payload.detail === "string" && payload.detail.trim()
    ? payload.detail
    : `读取失败（HTTP ${status}）。`;
}

function renderMetadata(payload) {
  const entries = [
    ["请求评估时间", formatDateTime(payload.evaluated_at_utc)],
    ["记录窗口起点", formatDateTime(payload.recorded_from)],
    ["记录窗口终点（不含）", formatDateTime(payload.recorded_to)],
    ["研究截止日期", payload.as_of_cutoff || "未限定"],
  ];
  queryMetadata.replaceChildren(...entries.map(([term, value]) => metadataPair(term, value)));
}

function renderEvents(events, append) {
  if (!append && events.length === 0) {
    emptyState.hidden = false;
    return;
  }
  emptyState.hidden = true;
  const fragment = document.createDocumentFragment();
  events.forEach((event) => fragment.append(createEventItem(event)));
  feedList.append(fragment);
}

function createEventItem(event) {
  const item = document.createElement("li");
  item.className = "feed-item";

  const body = document.createElement("article");
  const topLine = document.createElement("div");
  topLine.className = "feed-topline";
  topLine.append(createBadge(EVENT_LABELS[event.event_type] || event.event_type || "未知变化", "event-type-badge"));
  if (Number.isInteger(event.revision_no)) {
    topLine.append(createBadge(`修订 ${event.revision_no}`, "data-badge"));
  }
  if (event.evidence_grade) {
    topLine.append(createBadge(`证据等级 ${event.evidence_grade}`, "data-badge"));
  }
  if (event.supersedes_id) {
    topLine.append(createBadge("替代既有记录", "data-badge"));
  }

  const title = document.createElement("h3");
  title.textContent = event.primary_text || "未提供标题";
  const summary = document.createElement("p");
  summary.className = "feed-summary";
  summary.textContent = event.summary || "未提供摘要。";
  body.append(topLine, title, summary);

  const actions = document.createElement("div");
  actions.className = "feed-actions";
  if (isLocalDetailPath(event.detail_path)) {
    actions.append(createLink(event.detail_path, "查看已有上下文"));
  }
  const sourceUrl = safeHttpUrl(event.source_locator);
  if (sourceUrl) {
    const sourceLink = createLink(sourceUrl, "打开来源");
    sourceLink.target = "_blank";
    sourceLink.rel = "noopener noreferrer";
    actions.append(sourceLink);
  }
  if (actions.childElementCount) {
    body.append(actions);
  }

  const meta = document.createElement("aside");
  meta.className = "feed-meta";
  meta.setAttribute("aria-label", "记录元数据");
  const metadata = document.createElement("dl");
  addMetadata(metadata, "系统记录时间", formatDateTime(event.recorded_at_utc));
  addMetadata(
    metadata,
    event.information_date ? "信息日期" : "研究截止",
    event.information_date || event.information_cutoff_date || "不可用"
  );
  if (event.source_kind) {
    addMetadata(metadata, "来源类型", event.source_kind);
  }
  if (typeof event.source_locator === "string" && event.source_locator.trim()) {
    addMetadata(metadata, "来源定位", event.source_locator.trim());
  }
  addMetadata(metadata, "对象 ID", event.object_id || "不可用");
  addMetadata(metadata, "展示字段", event.primary_text_source_field || "不可用");
  meta.append(metadata);

  item.append(body, meta);
  return item;
}

function createBadge(text, className) {
  const badge = document.createElement("span");
  badge.className = className;
  badge.textContent = text;
  return badge;
}

function createLink(href, text) {
  const link = document.createElement("a");
  link.href = href;
  link.textContent = text;
  return link;
}

function metadataPair(term, value) {
  const wrapper = document.createElement("div");
  const dt = document.createElement("dt");
  const dd = document.createElement("dd");
  dt.textContent = term;
  dd.textContent = value;
  wrapper.append(dt, dd);
  return wrapper;
}

function addMetadata(list, term, value) {
  list.append(metadataPair(term, value));
}

function safeHttpUrl(value) {
  if (typeof value !== "string") {
    return null;
  }
  const normalized = value.trim();
  if (!/^https?:\/\//i.test(normalized)) {
    return null;
  }
  try {
    const url = new URL(normalized);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function isLocalDetailPath(value) {
  return typeof value === "string" && value.startsWith("/industry-alpha/") && !value.startsWith("//");
}

function formatDateTime(value) {
  if (typeof value !== "string" || !value) {
    return "不可用";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZoneName: "short",
  }).format(parsed);
}

function setBusy(isBusy, message) {
  form.querySelectorAll("input, select, button").forEach((control) => {
    control.disabled = isBusy;
  });
  resetButton.disabled = isBusy;
  loadMoreButton.disabled = isBusy;
  if (isBusy) {
    statusBadge.dataset.state = "loading";
    statusBadge.textContent = "读取中";
    loadStatus.textContent = message;
  }
}

function clearError() {
  loadError.hidden = true;
  loadError.textContent = "";
}

function showError(message) {
  statusBadge.dataset.state = "error";
  statusBadge.textContent = "读取失败";
  loadStatus.textContent = "未能完成当前查询。";
  loadError.textContent = message;
  loadError.hidden = false;
  loadMoreButton.hidden = true;
}
