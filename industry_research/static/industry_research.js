"use strict";

const form = document.getElementById("workspace-form");
const mapSelect = document.getElementById("map-select");
const cutoffInput = document.getElementById("cutoff-input");
const statusBadge = document.getElementById("status-badge");
const loadStatus = document.getElementById("load-status");
const loadError = document.getElementById("load-error");
const mapSummaryPanel = document.getElementById("map-summary-panel");
const mapSummary = document.getElementById("map-summary");
const observationsPanel = document.getElementById("observations-panel");
const observations = document.getElementById("observations");
const mapEvidenceSummary = document.getElementById("map-evidence-summary");
const beneficiariesPanel = document.getElementById("beneficiaries-panel");
const beneficiaryBody = document.getElementById("beneficiary-body");
const beneficiaryCount = document.getElementById("beneficiary-count");
const emptyState = document.getElementById("empty-state");
const detailPanel = document.getElementById("detail-panel");
const detailStatus = document.getElementById("detail-status");
const beneficiaryDetail = document.getElementById("beneficiary-detail");
const semanticDetail = document.getElementById("semantic-detail");
const companyDetail = document.getElementById("company-detail");
const closeDetail = document.getElementById("close-detail");

let currentCutoff = "";

function node(tag, text, className) {
  const item = document.createElement(tag);
  if (text !== undefined && text !== null) {
    item.textContent = String(text);
  }
  if (className) {
    item.className = className;
  }
  return item;
}

function setStatus(state, message) {
  statusBadge.dataset.state = state;
  statusBadge.textContent = {
    idle: "等待选择",
    loading: "读取中",
    ready: "已读取",
    error: "读取失败",
  }[state] || state;
  loadStatus.textContent = message;
}

function showError(message) {
  loadError.textContent = message;
  loadError.hidden = false;
  setStatus("error", "本地研究数据读取失败。");
}

function clearError() {
  loadError.textContent = "";
  loadError.hidden = true;
}

function addDefinition(list, label, value) {
  const wrapper = document.createElement("div");
  wrapper.append(node("dt", label));
  wrapper.append(
    node(
      "dd",
      value === null || value === undefined || value === "" ? "不可用" : value
    )
  );
  list.append(wrapper);
}

function cutoffQuery() {
  return currentCutoff
    ? `?as_of_cutoff=${encodeURIComponent(currentCutoff)}`
    : "";
}

async function fetchJson(path) {
  const response = await fetch(path, {
    method: "GET",
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  let payload = null;
  try {
    payload = await response.json();
  } catch (_error) {
    payload = null;
  }
  if (!response.ok) {
    const detail =
      payload && payload.detail ? payload.detail : `HTTP ${response.status}`;
    throw new Error(String(detail));
  }
  return payload;
}

function resetWorkspace() {
  mapSummary.replaceChildren();
  observations.replaceChildren();
  mapEvidenceSummary.replaceChildren();
  beneficiaryBody.replaceChildren();
  beneficiaryCount.textContent = "0 家";
  mapSummaryPanel.hidden = true;
  observationsPanel.hidden = true;
  beneficiariesPanel.hidden = true;
  emptyState.hidden = true;
  closeDetails();
}

async function loadMaps() {
  clearError();
  setStatus("loading", "正在读取可选产业地图。");
  const cutoff = cutoffInput.value;
  const query = cutoff
    ? `?as_of_cutoff=${encodeURIComponent(cutoff)}`
    : "";
  try {
    const payload = await fetchJson(`/industry-research/maps${query}`);
    const selectedBefore = mapSelect.value;
    mapSelect.replaceChildren(node("option", "请选择产业地图"));
    mapSelect.firstElementChild.value = "";
    for (const item of payload.maps || []) {
      const revision = item.latest_revision || {};
      const option = node(
        "option",
        `${revision.title || item.map_key} · r${
          revision.revision_no || "?"
        } · ${item.map_key}`
      );
      option.value = item.map_id;
      mapSelect.append(option);
    }
    const requestedMapId = new URLSearchParams(window.location.search).get(
      "map_id"
    );
    const preferred = requestedMapId || selectedBefore;
    if (
      preferred &&
      Array.from(mapSelect.options).some(
        (option) => option.value === preferred
      )
    ) {
      mapSelect.value = preferred;
    }
    setStatus(
      "idle",
      payload.maps && payload.maps.length
        ? `已读取 ${payload.maps.length} 张产业地图，请明确选择后打开工作台。`
        : "当前截止日期没有可见产业地图。"
    );
    if (requestedMapId && mapSelect.value === requestedMapId) {
      await loadWorkspace();
    }
  } catch (error) {
    showError(error.message);
  }
}

function renderMapSummary(payload) {
  const map = payload.industry_map || {};
  const revision = payload.latest_revision || {};
  mapSummary.replaceChildren();
  addDefinition(mapSummary, "map_key", map.map_key);
  addDefinition(mapSummary, "map_id", map.map_id);
  addDefinition(mapSummary, "case_id", map.case_id);
  addDefinition(mapSummary, "标题", revision.title);
  addDefinition(mapSummary, "范围", revision.scope);
  addDefinition(
    mapSummary,
    "修订",
    `${revision.revision_no || "?"} · ${revision.revision_id || "不可用"}`
  );
  addDefinition(mapSummary, "研究截止", revision.information_cutoff_date);
  addDefinition(mapSummary, "系统记录时间", revision.recorded_at_utc);
  mapSummaryPanel.hidden = false;
}

function renderObservations(payload) {
  observations.replaceChildren();
  const items =
    (payload.frozen_snapshot && payload.frozen_snapshot.observations) || [];
  for (const item of items) {
    const revision = item.revision || {};
    const card = node("article", null, "card");
    card.append(node("span", item.observation_kind, "raw-value"));
    card.append(node("h3", revision.title || item.observation_key));
    card.append(node("p", revision.description || "没有结构化描述。"));
    card.append(
      node("p", `状态：${revision.assertion_status || "不可用"}`, "muted")
    );
    card.append(
      node(
        "p",
        `研究截止：${revision.information_cutoff_date || "不可用"}`,
        "muted"
      )
    );
    card.append(
      node(
        "p",
        `系统记录：${revision.recorded_at_utc || "不可用"}`,
        "muted"
      )
    );
    observations.append(card);
  }
  if (!items.length) {
    observations.append(
      node(
        "p",
        "当前冻结地图没有可见的 driver / bottleneck / value_pool_shift 观察。",
        "muted"
      )
    );
  }
  const evidence = payload.map_evidence_summary || {};
  const grades = evidence.evidence_grade_summary || {};
  mapEvidenceSummary.replaceChildren();
  addDefinition(
    mapEvidenceSummary,
    "A / B / C / D 证据数",
    `${grades.A || 0} / ${grades.B || 0} / ${grades.C || 0} / ${
      grades.D || 0
    }`
  );
  addDefinition(
    mapEvidenceSummary,
    "冲突证据",
    (evidence.conflicts || []).length
  );
  addDefinition(
    mapEvidenceSummary,
    "缺失证据",
    (evidence.missing_evidence || []).length
  );
  observationsPanel.hidden = false;
}

function appendCell(row, content) {
  const cell = document.createElement("td");
  if (content instanceof Node) {
    cell.append(content);
  } else {
    cell.textContent = String(content ?? "不可用");
  }
  row.append(cell);
}

function renderBeneficiaries(payload) {
  beneficiaryBody.replaceChildren();
  const rows = payload.beneficiaries || [];
  beneficiaryCount.textContent = `${rows.length} 家`;
  emptyState.hidden = rows.length !== 0;

  for (const item of rows) {
    const revision = item.latest_revision || {};
    const stock = item.stock || {};
    const research = item.company_research;
    const row = document.createElement("tr");

    const companyBox = document.createElement("div");
    companyBox.append(
      node("p", `${stock.stock_name || "名称不可用"} · ${item.stock_code}`)
    );
    companyBox.append(
      node("p", `${stock.exchange || "交易所不可用"} · ${item.source}`, "muted")
    );
    companyBox.append(
      node(
        "p",
        `stock_basic #${stock.stock_basic_record_id ?? "不可用"}`,
        "muted"
      )
    );
    const ingestion = stock.ingestion_run || {};
    companyBox.append(
      node(
        "p",
        `ingestion #${ingestion.ingestion_run_id ?? "不可用"} · ${
          ingestion.provider || "来源不可用"
        }`,
        "muted"
      )
    );
    companyBox.append(
      node(
        "p",
        `来源截止：${ingestion.information_cutoff_date || "不可用"}`,
        "muted"
      )
    );
    appendCell(row, companyBox);

    const kindBox = document.createElement("div");
    kindBox.append(node("span", revision.beneficiary_kind, "raw-value"));
    kindBox.append(node("p", "现有 Stage 1 分析性研究状态", "muted"));
    appendCell(row, kindBox);

    const statusBox = document.createElement("div");
    statusBox.append(node("span", revision.assessment_status, "raw-value"));
    statusBox.append(node("p", `r${revision.revision_no || "?"}`, "muted"));
    statusBox.append(
      node("p", `当前修订：${revision.revision_id || "不可用"}`, "muted")
    );
    appendCell(row, statusBox);

    appendCell(row, node("p", revision.rationale_summary || "不可用"));

    const timeBox = document.createElement("div");
    timeBox.append(node("p", revision.information_cutoff_date || "不可用"));
    timeBox.append(node("p", revision.recorded_at_utc || "不可用", "muted"));
    appendCell(row, timeBox);

    const stage2Box = document.createElement("div");
    if (research) {
      stage2Box.append(
        node("span", research.latest_revision.workflow_state, "raw-value")
      );
      stage2Box.append(
        node("p", research.latest_revision.conclusion_status || "不可用")
      );
      stage2Box.append(node("p", research.history_notice, "muted"));
      stage2Box.append(
        node(
          "p",
          `当前 Stage 1 修订：${research.current_overview_beneficiary_revision_id}`,
          "muted"
        )
      );
      stage2Box.append(
        node(
          "p",
          `Stage 2 冻结修订：${research.frozen_beneficiary_revision_id}`,
          "muted"
        )
      );
    } else {
      stage2Box.append(node("p", "尚无冻结的公司财务传导研究"));
    }
    appendCell(row, stage2Box);

    const detailsButton = node(
      "button",
      "打开 Stage 1 / Stage 2 详情",
      "button button-secondary"
    );
    detailsButton.type = "button";
    detailsButton.addEventListener("click", () => openDetails(item));
    appendCell(row, detailsButton);

    const semanticsButton = node(
      "button",
      "查看类型化证据语义",
      "button button-secondary"
    );
    semanticsButton.type = "button";
    semanticsButton.addEventListener("click", () => openSemanticDetails(item));
    appendCell(row, semanticsButton);

    beneficiaryBody.append(row);
  }
  beneficiariesPanel.hidden = false;
}

async function loadWorkspace() {
  const mapId = mapSelect.value;
  if (!mapId) {
    showError("请先明确选择一张产业地图。");
    mapSelect.focus();
    return;
  }
  currentCutoff = cutoffInput.value;
  clearError();
  resetWorkspace();
  setStatus("loading", "正在读取产业地图与已录入受益公司全量。");
  try {
    const payload = await fetchJson(
      `/industry-research/maps/${encodeURIComponent(
        mapId
      )}/workspace${cutoffQuery()}`
    );
    renderMapSummary(payload);
    renderObservations(payload);
    renderBeneficiaries(payload);
    setStatus(
      "ready",
      `已读取 ${payload.beneficiaries.length} 家截止可见的已录入受益公司。`
    );
    const url = new URL(window.location.href);
    url.searchParams.set("map_id", mapId);
    if (currentCutoff) {
      url.searchParams.set("as_of_cutoff", currentCutoff);
    } else {
      url.searchParams.delete("as_of_cutoff");
    }
    window.history.replaceState(null, "", url);
  } catch (error) {
    showError(error.message);
  }
}

function prepareDetailPanel(message) {
  detailPanel.hidden = false;
  beneficiaryDetail.textContent = "";
  semanticDetail.textContent = "";
  companyDetail.textContent = "";
  detailStatus.textContent = message;
  detailPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function openDetails(item) {
  const name = item.stock.stock_name || item.stock_code;
  prepareDetailPanel(`正在按需读取 ${name} 的 Stage 1 / Stage 2 精确研究图。`);
  semanticDetail.textContent =
    "本次操作未读取类型化语义；请使用表格中的独立按钮明确加载。";

  const beneficiaryPath = `${item.beneficiary_detail_path}${cutoffQuery()}`;
  try {
    const stage1 = await fetchJson(beneficiaryPath);
    beneficiaryDetail.textContent = JSON.stringify(stage1, null, 2);
  } catch (error) {
    beneficiaryDetail.textContent = `Stage 1 详情读取失败：${error.message}`;
  }

  if (!item.company_research) {
    companyDetail.textContent =
      "尚无冻结的公司财务传导研究。系统不会从 Stage 1 文本生成假设。";
    detailStatus.textContent = "Stage 1 详情已读取；Stage 2 不可用。";
    return;
  }

  try {
    const stage2 = await fetchJson(
      `${item.company_research.detail_path}${cutoffQuery()}`
    );
    companyDetail.textContent = JSON.stringify(stage2, null, 2);
    detailStatus.textContent = item.company_research.history_notice;
  } catch (error) {
    companyDetail.textContent = `Stage 2 详情读取失败：${error.message}`;
    detailStatus.textContent =
      "Stage 1 详情已读取；Stage 2 详情读取失败。";
  }
}

async function openSemanticDetails(item) {
  const name = item.stock.stock_name || item.stock_code;
  prepareDetailPanel(`正在按需读取 ${name} 的类型化证据语义。`);
  beneficiaryDetail.textContent =
    "本次操作未读取 Stage 1 完整图；类型化记录会显示其精确冻结的 Stage 1 修订。";
  companyDetail.textContent =
    "本次操作未读取 Stage 2；类型化语义不会自动重绑既有 Stage 2 研究。";
  try {
    const payload = await fetchJson(
      `/industry-alpha/beneficiary-semantics/${encodeURIComponent(
        item.beneficiary_id
      )}${cutoffQuery()}`
    );
    semanticDetail.textContent = JSON.stringify(payload, null, 2);
    detailStatus.textContent =
      "已读取分析人员明确记录的类型化语义；旧分类与新分类保持独立。";
  } catch (error) {
    semanticDetail.textContent = `类型化语义不可用：${error.message}`;
    detailStatus.textContent =
      "该公司当前截止日期可能尚无类型化语义记录。系统不会从文本自动生成。";
  }
}

function closeDetails() {
  detailPanel.hidden = true;
  detailStatus.textContent = "";
  beneficiaryDetail.textContent = "";
  semanticDetail.textContent = "";
  companyDetail.textContent = "";
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  loadWorkspace();
});

cutoffInput.addEventListener("change", () => {
  resetWorkspace();
  loadMaps();
});

closeDetail.addEventListener("click", closeDetails);

const initialParams = new URLSearchParams(window.location.search);
cutoffInput.value = initialParams.get("as_of_cutoff") || "";
currentCutoff = cutoffInput.value;
loadMaps();
