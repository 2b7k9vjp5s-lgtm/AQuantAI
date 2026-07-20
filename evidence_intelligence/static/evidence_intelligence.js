"use strict";

const API_PATH = "/evidence-intelligence/feed";
const EVENT_LABELS = Object.freeze({
  evidence: "新增证据",
  case_revision: "研究案例修订",
  industry_map_revision: "产业地图修订",
  company_research_revision: "公司研究修订",
});

const form = document.querySelector("#feed-filters");
const resetButton = document.querySelector("#reset-filters");
const loadMoreButton = document.querySelector("#load-more");
const feedList = document.querySelector("#feed-list");
const emptyState = document.querySelector("#empty-state");
const statusBadge = document.querySelector("#status-badge");
const loadStatus = document.querySelector("#load-status");
const loadError = document.querySelector("#load-error");
const queryMetadata = document.querySelector("#query-metadata");

let nextCursor = null;
let activeRequestId = 0;

form.addEventListener("submit", (event) => {
  event.preventDefault();
  void loadFeed({ append: false });
});

resetButton.addEventListener("click", () => {
  form.reset();
  document.querySelector("#limit").value = "50";
  void loadFeed({ append: false });
});

loadMoreButton.addEventListener("click", () => {
  if (nextCursor) {
    void loadFeed({ append: true });
  }
});

void loadFeed({ append: false });

async function loadFeed({ append }) {
  const requestId = ++activeRequestId;
  setLoading(true, append ? "正在加载更多研究变化。" : "正在读取本地研究变化。");
  clearError();
  if (!append) {
    nextCursor = null;
    feedList.replaceChildren();
    emptyState.hidden = true;
    queryMetadata.replaceChildren();
  }

  try {
    const url = buildRequestUrl(append ? nextCursor : null);
    const response = await fetch(url, {
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
    renderEvents(payload.events || [], { append });
    nextCursor = payload.next_cursor || null;
    loadMoreButton.hidden = !nextCursor;
    loadMoreButton.disabled = false;
    statusBadge.dataset.state = "ready";
    statusBadge.textContent = "已就绪";
    const pageCount = Array.isArray(payload.events) ? payload.events.length : 0;
    loadStatus.textContent = append
      ? `已追加 ${pageCount} 条记录。`
      : `当前页读取 ${pageCount} 条记录。变化记录仅表示研究时间线。`;
  } catch (error) {
    if (requestId !== activeRequestId) {
      return;
    }
    showError(error instanceof Error ? error.message : "无法读取研究变化。");
  } finally {
    if (requestId === activeRequestId) {
      setLoading(false);
    }
  }
}

function buildRequestUrl(cursor) {
  const params = new URLSearchParams();
  const eventType = document.querySelector("#event-type").value;
  const recordedFrom = document.querySelector("#recorded-from").value;
  const recordedTo = document.querySelector("#recorded-to").value;
  const cutoff = document.querySelector("#as-of-cutoff").value;
  const limit = document.querySelector("#limit").value;

  if (eventType) {
    params.set("event_type", eventType);
  }
  if (recordedFrom) {
    params.set("recorded_from", localInputToIso(recordedFrom, "记录起点"));
  }
  if (recordedTo) {
    params.set("recorded_to", localInputToIso(recordedTo, "记录终点"));
  }
  if (cutoff) {
    params.set("as_of_cutoff", cutoff);
  }
  params.set("limit", limit || "50");
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
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return { detail: await response.text() };
}

function errorMessage(payload, status) {
  if (payload && typeof payload.detail === "string" && payload.detail.trim()) {
    return payload.detail;
  }
  return `读取失败（HTTP ${status}）。`;
}

function renderMetadata(payload) {
  const entries = [
    ["请求评估时间", formatDateTime(payload.evaluated_at_utc)],
    ["记录窗口起点", formatDateTime(payload.recorded_from)],
    ["记录窗口终点（不含）", formatDateTime(payload.recorded_to)],
    ["研究截止日期", payload.as_of_cutoff || "未限定"],
  ];
  queryMetadata.replaceChildren(
    ...entries.map(([term, description]) => {
      const wrapper = document.createElement("div");
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = term;
      dd.textContent = description;
      wrapper.append(dt, dd);
      return wrapper;
    })
  );
}

function renderEvents(events, { append }) {
  if (!append && events.length === 0) {
    emptyState.hidden = false;
    return;
  }
  emptyState.hidden = true;
  const fragment = document.createDocumentFragment();
  for (const event of events) {
    fragment.append(createEventItem(event));
  }
  feedList.append(fragment);
}

function createEventItem(event) {
  const item = document.createElement("li");
  item.className = "feed-item";

  const body = document.createElement("article");
  const topLine = document.createElement("div");
  topLine.className = "feed-topline";
  topLine.append(createBadge(EVENT_LABELS[event.event_type] || event.event_type, "event-type-badge"));
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
  if (actions.childElementCount > 0) {
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

function addMetadata(list, term, description) {
  const wrapper = document.createElement("div");
  const dt = document.createElement("dt");
  const dd = document.createElement("dd");
  dt.textContent = term;
  dd.textContent = description;
  wrapper.append(dt, dd);
  list.append(wrapper);
}

function safeHttpUrl(value) {
  if (typeof value !== "string" || !value.trim()) {
    return null;
  }
  try {
    const url = new URL(value, window.location.origin);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return null;
    }
    return url.href;
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

function setLoading(isLoading, message) {
  const controls = form.querySelectorAll("input, select, button");
  controls.forEach((control) => {
    control.disabled = isLoading;
  });
  resetButton.disabled = isLoading;
  loadMoreButton.disabled = isLoading;
  if (isLoading) {
    statusBadge.dataset.state = "loading";
    statusBadge.textContent = "读取中";
    if (message) {
      loadStatus.textContent = message;
    }
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
