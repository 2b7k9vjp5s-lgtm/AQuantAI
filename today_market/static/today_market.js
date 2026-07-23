(() => {
  "use strict";

  const storageKey = "aquantai.today-market.selection.v1";
  const catalogForm = document.querySelector("#catalog-form");
  const cutoffInput = document.querySelector("#as-of-cutoff");
  const recordedInput = document.querySelector("#as-of-recorded-at");
  const catalogStatus = document.querySelector("#catalog-status");
  const databaseState = document.querySelector("#database-state");
  const selectionPanel = document.querySelector("#selection-panel");
  const equitySelect = document.querySelector("#equity-series");
  const benchmarkSelect = document.querySelector("#benchmark-series");
  const sectorSelect = document.querySelector("#sector-series");
  const snapshotButton = document.querySelector("#snapshot-button");
  const snapshotStatus = document.querySelector("#snapshot-status");
  const emptyState = document.querySelector("#empty-state");
  const emptyTitle = document.querySelector("#empty-title");
  const emptyMessage = emptyState.querySelector("p");
  const snapshotContent = document.querySelector("#snapshot-content");

  const statePill = document.querySelector("#snapshot-state-pill");
  const stateExplanation = document.querySelector("#state-explanation");
  const scopeSummary = document.querySelector("#scope-summary");
  const warnings = document.querySelector("#warnings");
  const priceBehavior = document.querySelector("#price-behavior");
  const liquidity = document.querySelector("#liquidity");
  const benchmark = document.querySelector("#benchmark");
  const sector = document.querySelector("#sector");
  const completeness = document.querySelector("#data-completeness");
  const unavailable = document.querySelector("#unavailable-sections");
  const technical = document.querySelector("#technical-details");

  let activeBoundaries = null;
  let catalogRequestVersion = 0;
  let snapshotRequestVersion = 0;

  function setStatus(element, message, isError = false) {
    element.textContent = message;
    element.classList.toggle("error", isError);
  }

  function showPendingSnapshot(title, message) {
    emptyTitle.textContent = title;
    emptyMessage.textContent = message;
    emptyState.hidden = false;
    snapshotContent.hidden = true;
  }

  function recordedUtc() {
    const value = recordedInput.value;
    if (!value) return null;
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return null;
    return parsed.toISOString();
  }

  function boundaries() {
    const cutoff = cutoffInput.value;
    const recorded = recordedUtc();
    if (!cutoff || !recorded) return null;
    return { cutoff, recorded };
  }

  function sameBoundaries(left, right) {
    return Boolean(
      left
      && right
      && left.cutoff === right.cutoff
      && left.recorded === right.recorded
    );
  }

  function currentSelection() {
    return {
      equity: equitySelect.value,
      benchmark: benchmarkSelect.value,
      sector: sectorSelect.value,
    };
  }

  function sameSelection(left, right) {
    return Boolean(
      left
      && right
      && left.equity === right.equity
      && left.benchmark === right.benchmark
      && left.sector === right.sector
    );
  }

  function queryString(boundary, extra = {}) {
    const params = new URLSearchParams({
      as_of_cutoff: boundary.cutoff,
      as_of_recorded_at_utc: boundary.recorded,
      ...extra,
    });
    return params.toString();
  }

  async function jsonRequest(url) {
    const response = await fetch(url, {
      method: "GET",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = payload.detail || {};
      const error = new Error(detail.message || "本地读取失败。");
      error.code = detail.code || `http_${response.status}`;
      throw error;
    }
    return payload;
  }

  function resetSelect(select, firstLabel) {
    select.replaceChildren();
    const option = document.createElement("option");
    option.value = "";
    option.textContent = firstLabel;
    select.append(option);
  }

  function appendOptions(select, values) {
    values.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.series_key;
      option.textContent = item.label;
      select.append(option);
    });
  }

  function restoreExactSelections(families) {
    let saved = null;
    try {
      saved = JSON.parse(localStorage.getItem(storageKey) || "null");
    } catch (_) {
      saved = null;
    }
    if (!saved) return;
    const visible = (items, key) => items.some((item) => item.series_key === key);
    if (visible(families.equity, saved.equity)) equitySelect.value = saved.equity;
    if (visible(families.benchmark, saved.benchmark)) benchmarkSelect.value = saved.benchmark;
    if (visible(families.sector, saved.sector)) sectorSelect.value = saved.sector;
  }

  function saveSelections() {
    localStorage.setItem(storageKey, JSON.stringify(currentSelection()));
  }

  function updateSnapshotAvailability() {
    const ready = Boolean(activeBoundaries && equitySelect.value);
    snapshotButton.disabled = !ready;
    setStatus(snapshotStatus, ready ? "可以读取明确选择的本地快照。" : "请选择股票数据范围。");
  }

  function invalidateCatalogForBoundaryChange() {
    catalogRequestVersion += 1;
    snapshotRequestVersion += 1;
    if (!activeBoundaries && selectionPanel.hidden) {
      if (databaseState.textContent === "正在读取本地数据库") {
        databaseState.textContent = "读取边界已更改";
        setStatus(catalogStatus, "读取边界已更改，请重新读取本地数据列表。");
      }
      return;
    }
    activeBoundaries = null;
    selectionPanel.hidden = true;
    snapshotButton.disabled = true;
    snapshotButton.textContent = "查看本地市场快照";
    databaseState.textContent = "读取边界已更改";
    setStatus(catalogStatus, "读取边界已更改，请重新读取本地数据列表。");
    setStatus(snapshotStatus, "请先按新边界读取本地数据列表。");
    showPendingSnapshot(
      "读取边界已更改",
      "旧的数据列表和快照已失效。请按新的双时间边界重新读取本地数据列表。",
    );
  }

  [cutoffInput, recordedInput].forEach((input) => {
    input.addEventListener("input", invalidateCatalogForBoundaryChange);
  });

  catalogForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const boundary = boundaries();
    if (!boundary) {
      setStatus(catalogStatus, "请填写有效的双时间边界。", true);
      return;
    }
    const requestVersion = ++catalogRequestVersion;
    snapshotRequestVersion += 1;
    activeBoundaries = null;
    snapshotButton.disabled = true;
    selectionPanel.hidden = true;
    showPendingSnapshot(
      "正在读取本地数据列表",
      "系统只会读取当前明确设置的双时间边界。",
    );
    setStatus(catalogStatus, "正在读取本地数据列表……");
    databaseState.textContent = "正在读取本地数据库";
    try {
      const payload = await jsonRequest(`/today-market/api/local-series?${queryString(boundary)}`);
      if (
        requestVersion !== catalogRequestVersion
        || !sameBoundaries(boundary, boundaries())
      ) return;
      activeBoundaries = boundary;
      resetSelect(equitySelect, "请选择股票数据范围");
      resetSelect(benchmarkSelect, "不选择本地基准数据");
      resetSelect(sectorSelect, "不选择本地行业数据");
      appendOptions(equitySelect, payload.families.equity);
      appendOptions(benchmarkSelect, payload.families.benchmark);
      appendOptions(sectorSelect, payload.families.sector);
      restoreExactSelections(payload.families);
      selectionPanel.hidden = false;
      showPendingSnapshot(
        "尚未读取本地市场快照",
        "明确选择一个股票数据范围后，点击“查看本地市场快照”。选择前不会显示指标。",
      );
      databaseState.textContent = payload.status === "ready" ? "本地数据列表已读取" : "当前边界内没有本地数据";
      setStatus(catalogStatus, payload.message);
      updateSnapshotAvailability();
    } catch (error) {
      if (requestVersion !== catalogRequestVersion) return;
      databaseState.textContent = "本地数据库读取失败";
      setStatus(catalogStatus, error.message, true);
      showPendingSnapshot("本地数据列表读取失败", error.message);
    }
  });

  [equitySelect, benchmarkSelect, sectorSelect].forEach((select) => {
    select.addEventListener("change", () => {
      snapshotRequestVersion += 1;
      saveSelections();
      snapshotButton.textContent = "查看本地市场快照";
      showPendingSnapshot(
        equitySelect.value ? "数据选择已更改" : "尚未选择本地市场数据",
        equitySelect.value
          ? "请重新点击“查看本地市场快照”，旧结果不会继续显示。"
          : "请明确选择一个股票数据范围。",
      );
      updateSnapshotAvailability();
    });
  });

  snapshotButton.addEventListener("click", async () => {
    if (!activeBoundaries || !equitySelect.value) return;
    saveSelections();
    const requestVersion = ++snapshotRequestVersion;
    const requestBoundaries = { ...activeBoundaries };
    const requestSelection = currentSelection();
    snapshotButton.disabled = true;
    setStatus(snapshotStatus, "正在读取明确选择的本地市场快照……");
    const extra = { equity_series_key: requestSelection.equity };
    if (requestSelection.benchmark) extra.benchmark_series_key = requestSelection.benchmark;
    if (requestSelection.sector) extra.sector_series_key = requestSelection.sector;
    try {
      const payload = await jsonRequest(`/today-market/api/snapshot?${queryString(requestBoundaries, extra)}`);
      if (
        requestVersion !== snapshotRequestVersion
        || !sameBoundaries(requestBoundaries, activeBoundaries)
        || !sameSelection(requestSelection, currentSelection())
      ) return;
      renderSnapshot(payload);
      emptyState.hidden = true;
      snapshotContent.hidden = false;
      snapshotButton.textContent = "重新读取本地快照";
      setStatus(snapshotStatus, payload.state_explanation.what_happened);
      databaseState.textContent = "本地快照已读取";
    } catch (error) {
      if (requestVersion !== snapshotRequestVersion) return;
      setStatus(snapshotStatus, error.message, true);
      databaseState.textContent = "本地快照读取失败";
      showPendingSnapshot("本地快照读取失败", error.message);
    } finally {
      if (requestVersion === snapshotRequestVersion) {
        snapshotButton.disabled = !(activeBoundaries && equitySelect.value);
      }
    }
  });

  function renderSnapshot(payload) {
    statePill.textContent = statusLabel(payload.status);
    stateExplanation.replaceChildren(
      explanationCard("发生了什么", payload.state_explanation.what_happened),
      explanationCard("为什么重要", payload.state_explanation.why_it_matters),
      explanationCard("现在可以做什么", payload.state_explanation.available_action),
    );
    renderSummary(scopeSummary, payload.scope_and_freshness);
    warnings.replaceChildren();
    (payload.scope_and_freshness.warnings || []).forEach((message) => {
      const item = document.createElement("div");
      item.className = "warning-item";
      item.textContent = message;
      warnings.append(item);
    });
    renderData(priceBehavior, payload.supported_analysis.price_behavior);
    renderData(liquidity, payload.supported_analysis.liquidity);
    renderData(benchmark, payload.supported_analysis.benchmark);
    renderData(sector, payload.supported_analysis.sector);
    renderData(completeness, payload.supported_analysis.data_completeness);
    unavailable.replaceChildren();
    payload.unavailable_sections.forEach((section) => {
      const card = document.createElement("article");
      card.className = "unavailable-card";
      const title = document.createElement("h3");
      title.textContent = section.label;
      const text = document.createElement("p");
      text.textContent = section.message;
      card.append(title, text);
      unavailable.append(card);
    });
    technical.textContent = JSON.stringify(payload.technical_details, null, 2);
  }

  function explanationCard(title, text) {
    const card = document.createElement("div");
    card.className = "explanation-item";
    const heading = document.createElement("strong");
    heading.textContent = title;
    const content = document.createElement("span");
    content.textContent = text;
    card.append(heading, content);
    return card;
  }

  function renderSummary(container, value) {
    container.replaceChildren();
    Object.entries(value).forEach(([key, item]) => {
      const wrapper = document.createElement("dl");
      wrapper.className = "summary-item";
      const term = document.createElement("dt");
      term.textContent = labelFor(key);
      const description = document.createElement("dd");
      description.textContent = displayValue(item);
      wrapper.append(term, description);
      container.append(wrapper);
    });
  }

  function renderData(container, value) {
    container.replaceChildren();
    if (value === null || value === undefined) {
      container.append(dataCard("状态", "当前没有可显示的数据。"));
      return;
    }
    if (typeof value !== "object" || Array.isArray(value)) {
      container.append(dataCard("结果", displayValue(value)));
      return;
    }
    Object.entries(value).forEach(([key, item]) => {
      container.append(dataCard(labelFor(key), item));
    });
  }

  function dataCard(label, value) {
    const card = document.createElement("div");
    card.className = "data-card";
    const heading = document.createElement("div");
    heading.className = "data-label";
    heading.textContent = label;
    const body = document.createElement("pre");
    body.textContent = typeof value === "object" && value !== null
      ? JSON.stringify(value, null, 2)
      : displayValue(value);
    card.append(heading, body);
    return card;
  }

  function displayValue(value) {
    if (value === true) return "是";
    if (value === false) return "否";
    if (value === null || value === undefined || value === "") return "暂无";
    if (Array.isArray(value)) return value.length ? value.join("、") : "无";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  function statusLabel(status) {
    return {
      complete_selected_scope: "已读取所选范围",
      partial_selected_scope: "所选范围包含警告",
      insufficient_data: "数据不足",
    }[status] || status;
  }

  function labelFor(key) {
    const labels = {
      local_only: "仅本地读取",
      coverage_label: "覆盖范围",
      coverage_notice: "覆盖提示",
      universe_stock_count: "范围内公司数",
      available_stock_count: "可用公司数",
      requested_information_cutoff: "请求信息截止日",
      source_information_cutoff: "来源信息截止日",
      requested_recorded_at_utc: "请求系统记录时间",
      ingestion_imported_at_utc: "本地导入时间",
      ingestion_completed_at_utc: "本地完成时间",
      effective_equity_session: "有效股票交易日",
      scope_coverage_status: "范围状态",
      calculation_status: "计算状态",
      completeness_status: "完整性状态",
      warnings: "警告",
      status: "状态",
      message: "说明",
      metrics: "指标",
      provenance: "来源",
      alignment_status: "对齐状态",
      coverage_status: "覆盖状态",
      session_alignment_status: "交易日对齐",
      cutoff_alignment_status: "截止日对齐",
      latest_data_diagnostics: "最新数据诊断",
    };
    return labels[key] || key.replaceAll("_", " ");
  }
})();
