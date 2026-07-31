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

  const ordinarySentence = document.querySelector("#ordinary-market-sentence");
  const ordinaryDataDate = document.querySelector("#ordinary-data-date");
  const ordinaryMarketState = document.querySelector("#ordinary-market-state");
  const ordinaryRefreshState = document.querySelector("#ordinary-refresh-state");
  const ordinaryAction = document.querySelector("#ordinary-primary-action");
  const ordinarySource = document.querySelector("#ordinary-source-summary");
  const ordinaryCore = document.querySelector("#ordinary-core-grid");
  const ordinarySectorFocus = document.querySelector("#ordinary-sector-focus-grid");
  const ordinarySectorRisk = document.querySelector("#ordinary-sector-risk-grid");
  const ordinaryAnomalies = document.querySelector("#ordinary-anomaly-list");
  const ordinaryCoverage = document.querySelector("#ordinary-coverage-grid");
  const ordinaryWarnings = document.querySelector("#ordinary-warnings");
  const ordinaryTechnical = document.querySelector("#ordinary-technical-content");

  const runtimePanel = document.querySelector("#runtime-panel");
  const runtimePill = document.querySelector("#runtime-state-pill");
  const runtimeExplanation = document.querySelector("#runtime-explanation");
  const runtimeCandidate = document.querySelector("#runtime-candidate");
  const runtimeRetry = document.querySelector("#runtime-retry");
  const runtimeTechnical = document.querySelector("#runtime-technical");

  let activeBoundaries = null;
  let catalogRequestVersion = 0;
  let snapshotRequestVersion = 0;
  let readModelRequestVersion = 0;
  let runtimeRequestVersion = 0;
  let currentRuntimeStatus = null;
  const automaticScopes = new Set();

  function setStatus(element, message, isError = false) {
    element.textContent = message;
    element.classList.toggle("error", isError);
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
    return new URLSearchParams({
      as_of_cutoff: boundary.cutoff,
      as_of_recorded_at_utc: boundary.recorded,
      ...extra,
    }).toString();
  }

  function selectedScopeQuery() {
    if (!activeBoundaries || !equitySelect.value) return null;
    const params = new URLSearchParams({
      as_of_cutoff: activeBoundaries.cutoff,
      as_of_recorded_at_utc: activeBoundaries.recorded,
      equity_series_key: equitySelect.value,
    });
    if (benchmarkSelect.value) params.set("benchmark_series_key", benchmarkSelect.value);
    if (sectorSelect.value) params.set("sector_series_key", sectorSelect.value);
    return params;
  }

  async function jsonRequest(url, options = {}) {
    const response = await fetch(url, {
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
      },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = payload.detail || {};
      const error = new Error(detail.message || "本地读取失败。");
      error.code = detail.code || `http_${response.status}`;
      error.currentStatus = detail.current_status || null;
      throw error;
    }
    return payload;
  }

  function showPendingSnapshot(title, message) {
    emptyTitle.textContent = title;
    emptyMessage.textContent = message;
    emptyState.hidden = false;
    snapshotContent.hidden = true;
  }

  function resetSelect(select, firstLabel) {
    select.replaceChildren();
    const option = document.createElement("option");
    option.value = "";
    option.textContent = firstLabel;
    select.append(option);
  }

  function appendOptions(select, values) {
    (values || []).forEach((item) => {
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
    const visible = (items, key) => (items || []).some((item) => item.series_key === key);
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
    readModelRequestVersion += 1;
    runtimeRequestVersion += 1;
    activeBoundaries = null;
    selectionPanel.hidden = true;
    snapshotButton.disabled = true;
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
    readModelRequestVersion += 1;
    runtimeRequestVersion += 1;
    activeBoundaries = null;
    snapshotButton.disabled = true;
    selectionPanel.hidden = true;
    showPendingSnapshot("正在读取本地数据列表", "系统只会读取当前明确设置的双时间边界。");
    setStatus(catalogStatus, "正在读取本地数据列表……");
    databaseState.textContent = "正在读取本地数据库";
    try {
      const payload = await jsonRequest(`/today-market/api/local-series?${queryString(boundary)}`);
      if (requestVersion !== catalogRequestVersion || !sameBoundaries(boundary, boundaries())) return;
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
        "明确选择一个股票数据范围后，点击“查看本地市场快照”。",
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
      readModelRequestVersion += 1;
      runtimeRequestVersion += 1;
      saveSelections();
      snapshotButton.textContent = "查看本地市场快照";
      showPendingSnapshot(
        equitySelect.value ? "数据选择已更改" : "尚未选择本地市场数据",
        equitySelect.value ? "请重新点击“查看本地市场快照”，旧结果不会继续显示。" : "请明确选择一个股票数据范围。",
      );
      updateSnapshotAvailability();
    });
  });

  snapshotButton.addEventListener("click", async () => {
    if (!activeBoundaries || !equitySelect.value) return;
    saveSelections();
    const requestVersion = ++snapshotRequestVersion;
    readModelRequestVersion += 1;
    runtimeRequestVersion += 1;
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
      await loadReadModel();
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
    (payload.scope_and_freshness.warnings || []).forEach((message) => appendWarning(warnings, message));
    renderObjectCards(priceBehavior, payload.supported_analysis.price_behavior, "价格行为");
    renderObjectCards(liquidity, payload.supported_analysis.liquidity, "流动性");
    renderObjectCards(benchmark, payload.supported_analysis.benchmark, "基准");
    renderObjectCards(sector, payload.supported_analysis.sector, "行业");
    renderObjectCards(completeness, payload.supported_analysis.data_completeness, "完整性");
    unavailable.replaceChildren();
    (payload.unavailable_sections || []).forEach((section) => {
      unavailable.append(dataCard(section.label, section.message));
    });
    technical.textContent = JSON.stringify(payload.technical_details, null, 2);
  }

  async function loadReadModel() {
    const params = selectedScopeQuery();
    if (!params || snapshotContent.hidden) return;
    const version = ++readModelRequestVersion;
    ordinarySentence.textContent = "正在读取确定性市场投影……";
    try {
      const payload = await jsonRequest(`/today-market/api/read-model?${params.toString()}`);
      if (version !== readModelRequestVersion || snapshotContent.hidden) return;
      renderReadModel(payload);
    } catch (error) {
      if (version !== readModelRequestVersion) return;
      ordinaryMarketState.textContent = "投影不可用";
      ordinaryRefreshState.textContent = "状态未知";
      ordinarySentence.textContent = error.message;
      ordinaryAction.disabled = false;
      ordinaryAction.textContent = "重新读取本地快照";
      ordinaryAction.dataset.actionCode = "reread_local_snapshot";
      ordinarySource.textContent = "系统没有对未知状态作推断。";
    }
  }

  function renderReadModel(payload) {
    ordinaryMarketState.textContent = statusLabel(payload.market_state);
    ordinaryRefreshState.textContent = statusLabel(payload.refresh_state);
    ordinaryDataDate.textContent = `最新完整交易日：${formatDate(payload.data_date)}`;
    ordinarySentence.textContent = marketSentence(payload);
    ordinarySource.textContent = [
      payload.source_summary?.source_label,
      payload.source_summary?.coverage_label,
      payload.source_summary?.refresh_label,
    ].filter(Boolean).join(" · ");

    const action = payload.source_summary?.dominant_action || {};
    ordinaryAction.textContent = action.label || "重新读取本地快照";
    ordinaryAction.disabled = action.enabled === false;
    ordinaryAction.dataset.actionCode = action.code || "reread_local_snapshot";

    renderCore(payload);
    renderSectorGroups(ordinarySectorFocus, payload.sector_groups, payload.sector_groups?.focus_states || []);
    renderSectorGroups(ordinarySectorRisk, payload.sector_groups, payload.sector_groups?.risk_states || []);
    renderAnomalies(payload.stock_anomalies);
    renderCoverage(payload.coverage);

    ordinaryWarnings.replaceChildren();
    (payload.warnings || []).forEach((message) => appendWarning(ordinaryWarnings, message));
    ordinaryTechnical.textContent = JSON.stringify({
      read_model_version: payload.read_model_version,
      read_model_fingerprint: payload.read_model_fingerprint,
      snapshot_id: payload.snapshot_id,
      data_status: payload.data_status,
      technical_details: payload.technical_details,
    }, null, 2);
  }

  function marketSentence(payload) {
    if (payload.market_overview?.status !== "ready") {
      return "完整市场范围尚未被当前本地契约证明；先展示可验证的本地范围背景，不对全市场状态作外推。";
    }
    return {
      strong: "市场宽度与趋势条件同时偏强。",
      weak: "市场宽度与趋势条件同时偏弱。",
      mixed: "市场内部信号分化，当前为混合状态。",
      insufficient_coverage: "市场覆盖不足，暂不生成完整市场状态。",
    }[payload.market_state] || "当前市场状态需要查看覆盖说明。";
  }

  function renderCore(payload) {
    ordinaryCore.replaceChildren();
    const overview = payload.market_overview || {};
    const context = overview.status === "ready" ? overview.result : overview.selected_scope_context || {};
    ordinaryCore.append(
      dataCard("市场状态", statusLabel(payload.market_state)),
      dataCard("上涨 / 下跌 / 平盘", `${displayValue(context.advancing_count)} / ${displayValue(context.declining_count)} / ${displayValue(context.unchanged_count)}`),
      dataCard("上涨占比", formatPercent(context.advance_ratio)),
      dataCard("市场宽度平衡", formatPercent(context.breadth_balance)),
      dataCard("收益中位数", formatPercent(context.median_return)),
      dataCard("成交活跃度", formatRatio(context.market_amount_ratio_20 ?? context.amount_ratio_20)),
    );
    (payload.core_indices || []).forEach((item) => {
      ordinaryCore.append(dataCard(
        `指数 ${item.index_code}`,
        lines([
          ["最新收盘", formatNumber(item.latest_close)],
          ["最新日收益", formatPercent(item.latest_return)],
          ["高于 20 日均线", displayValue(item.above_sma20)],
          ["近 20 日年化波动", formatPercent(item.realized_volatility_20)],
        ]),
      ));
    });
    if (overview.status !== "ready") {
      ordinaryCore.append(dataCard("完整市场状态不可用原因", reasonLabel(overview.reason)));
    }
  }

  function renderSectorGroups(container, projection, states) {
    container.replaceChildren();
    if (!projection || projection.status !== "ready") {
      container.append(dataCard("当前不可用", reasonLabel(projection?.reason)));
      return;
    }
    let count = 0;
    states.forEach((state) => {
      const items = projection.groups?.[state] || [];
      if (!items.length) return;
      count += items.length;
      const body = items.map((item) => (
        `${item.sector_name}（${item.sector_code}） · 1日 ${formatPercent(item.sector_r1)} · 5日 ${formatPercent(item.sector_r5)} · 20日 ${formatPercent(item.sector_r20)}`
      )).join("\n");
      container.append(dataCard(statusLabel(state), body));
    });
    if (!count) container.append(dataCard("当前没有匹配方向", "没有板块满足这一组确定性状态条件。"));
  }

  function renderAnomalies(projection) {
    ordinaryAnomalies.replaceChildren();
    if (!projection || projection.status !== "ready") {
      ordinaryAnomalies.append(dataCard("当前不可用", (projection?.reasons || []).map(reasonLabel).join("\n") || "输入不足"));
      return;
    }
    if (!(projection.items || []).length) {
      ordinaryAnomalies.append(dataCard("没有触发的异动", "当前可证明规则没有触发异动；不可评估规则请查看技术详情。"));
      return;
    }
    (projection.items || []).forEach((item) => {
      ordinaryAnomalies.append(dataCard(
        `${item.stock_code} · ${statusLabel(item.anomaly_type)}`,
        `主指标：${formatNumber(item.primary_metric)}`,
      ));
    });
  }

  function renderCoverage(value) {
    ordinaryCoverage.replaceChildren();
    if (!value) return;
    const entries = [
      ["预期证券数", value.expected_instruments],
      ["已计入证券数", value.accounted_instruments],
      ["有效收益数", value.valid_returns],
      ["无成交证券数", value.no_trade_instruments],
      ["缺失来源行", value.missing_source_rows],
      ["身份冲突", value.identity_conflicts],
      ["行业数量", value.sector_count],
      ["历史生效成分覆盖", statusLabel(value.sector_membership_coverage)],
      ["历史窗口覆盖", statusLabel(value.history_window_coverage)],
      ["范围覆盖状态", statusLabel(value.scope_coverage_status)],
      ["不可用原因", (value.unsupported_metric_reasons || []).map(reasonLabel).join("、") || "无"],
    ];
    entries.forEach(([label, item]) => ordinaryCoverage.append(summaryItem(label, item)));
  }

  ordinaryAction.addEventListener("click", () => {
    const code = ordinaryAction.dataset.actionCode;
    if (code === "explicit_user_retry") {
      runtimeRetry.click();
      return;
    }
    if (code === "reread_local_snapshot") snapshotButton.click();
  });

  function renderSummary(container, value) {
    container.replaceChildren();
    Object.entries(value || {}).forEach(([key, item]) => {
      if (key === "warnings") return;
      container.append(summaryItem(labelFor(key), displayValue(item, key)));
    });
  }

  function summaryItem(label, value) {
    const wrapper = document.createElement("dl");
    wrapper.className = "summary-item";
    const term = document.createElement("dt");
    term.textContent = label;
    const description = document.createElement("dd");
    description.textContent = displayValue(value);
    wrapper.append(term, description);
    return wrapper;
  }

  function explanationCard(title, text) {
    const card = document.createElement("div");
    card.className = "explanation-item";
    const heading = document.createElement("strong");
    heading.textContent = title;
    const content = document.createElement("span");
    content.textContent = text || "暂无";
    card.append(heading, content);
    return card;
  }

  function appendWarning(container, message) {
    const item = document.createElement("div");
    item.className = "warning-item";
    item.textContent = message;
    container.append(item);
  }

  function renderObjectCards(container, value, label) {
    container.replaceChildren();
    if (!value) {
      container.append(dataCard("状态", "当前没有可显示的数据。"));
      return;
    }
    if (value.status === "not_selected") {
      container.append(dataCard("状态", value.message || "未选择。"));
      return;
    }
    container.append(dataCard(label, JSON.stringify(value, null, 2)));
  }

  function dataCard(label, value) {
    const card = document.createElement("div");
    card.className = "data-card";
    const heading = document.createElement("div");
    heading.className = "data-label";
    heading.textContent = label;
    const body = document.createElement("pre");
    body.textContent = displayValue(value);
    card.append(heading, body);
    return card;
  }

  function lines(entries) {
    return entries
      .filter(([, value]) => value !== undefined)
      .map(([label, value]) => `${label}：${displayValue(value)}`)
      .join("\n");
  }

  function formatDate(value) {
    if (!value) return "暂无";
    const normalized = String(value).replaceAll("-", "");
    if (!/^\d{8}$/.test(normalized)) return String(value);
    return `${normalized.slice(0, 4)}-${normalized.slice(4, 6)}-${normalized.slice(6, 8)}`;
  }

  function formatNumber(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "暂无";
    return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(Number(value));
  }

  function formatPercent(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "暂无";
    return new Intl.NumberFormat("zh-CN", {
      style: "percent",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Number(value));
  }

  function formatRatio(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "暂无";
    return `${Number(value).toFixed(2)} 倍`;
  }

  function displayValue(value, key = null) {
    if (key && key.endsWith("_status")) return statusLabel(value);
    if (value === true) return "是";
    if (value === false) return "否";
    if (value === null || value === undefined || value === "") return "暂无";
    if (Array.isArray(value)) return value.length ? value.join("、") : "无";
    if (typeof value === "object") return JSON.stringify(value, null, 2);
    return String(value);
  }

  function statusLabel(status) {
    return {
      complete_selected_scope: "已读取所选范围",
      partial_selected_scope: "所选范围包含警告",
      insufficient_data: "数据不足",
      complete: "完整",
      partial: "部分可用",
      unavailable: "不可用",
      available: "可用",
      ready: "可用",
      aligned: "已对齐",
      different_session: "交易日不同",
      different_cutoff: "截止日不同",
      unverified_selected_scope: "仅验证所选范围",
      no_eligible_local_data: "无可见本地数据",
      not_selected: "未选择",
      strong: "偏强",
      weak: "偏弱",
      mixed: "分化",
      insufficient_coverage: "覆盖不足",
      strengthening: "正在增强",
      new: "新出现",
      spreading: "扩散",
      persistent_strong: "持续强势",
      high_level_divergence: "高位分化",
      cooling: "降温",
      neutral: "中性",
      current: "当前",
      checking: "检查中",
      refresh_required: "需要更新",
      refreshing: "更新中",
      refreshed: "已完成更新",
      not_initialized: "未初始化",
      manual_catchup_required: "需要手动补齐",
      blocked_source_contract: "真实数据源未授权",
      failed_retained_prior: "更新失败，已保留旧快照",
      cancelled_retained_prior: "更新取消，已保留旧快照",
      large_move: "大幅波动",
      unusual_volume: "成交量异常",
      new_high: "阶段新高",
      new_low: "阶段新低",
      gap: "跳空",
      persistent_relative_strength: "持续相对强势",
      sector_relative_outlier: "板块相对异常",
    }[status] || reasonLabel(status);
  }

  function reasonLabel(reason) {
    const labels = {
      full_market_universe_not_proven: "完整市场证券范围尚未被证明",
      market_rule_inputs_unavailable: "完整市场规则输入不可用",
      sector_rule_inputs_unavailable: "板块规则输入不可用",
      stock_rule_inputs_unavailable: "个股规则输入不可用",
      dated_membership_unavailable: "缺少历史生效的板块成分",
      dated_sector_membership_unavailable: "缺少历史生效的板块成分",
      reference_close_semantics_unavailable: "缺少精确参考收盘语义",
      analysis_price_semantics_unavailable: "缺少精确分析价格语义",
      full_market_cross_section_not_proven: "完整市场横截面尚未被证明",
      return_semantics_unavailable: "收益语义不可用",
      five_session_return_semantics_unavailable: "五日收益语义不可用",
      exact_20_session_volume_window_unavailable: "精确 20 个前序交易日成交量窗口不可用",
      exact_60_session_analysis_close_window_unavailable: "精确 60 个交易日分析价格窗口不可用",
      fewer_than_10_eligible_sector_members: "板块有效成员不足 10 个",
      sector_mad_zero: "板块离差基准为零",
      available: "可用",
      partial_eligible_cohort: "可用样本不完整",
      partial_matched_cohort: "匹配样本不完整",
      insufficient_open_session_history: "交易日历史不足",
      empty_eligible_cohort: "没有可用样本",
      empty_matched_cohort: "没有匹配样本",
      non_finite_aggregate: "聚合结果无效",
      no_eligible_observations: "没有可用观测",
      invalid_baseline: "历史基准无效",
      missing_expected_session: "缺少预期交易日",
      invalid_close: "收盘价无效",
    };
    return labels[reason] || (reason ? String(reason) : "暂无");
  }

  function labelFor(key) {
    return {
      local_only: "仅本地读取",
      coverage_label: "覆盖范围",
      coverage_notice: "覆盖提示",
      benchmark_selected: "已选择基准",
      sector_selected: "已选择行业范围",
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
    }[key] || key.replaceAll("_", " ");
  }

  function phaseLabel(phase) {
    return {
      prior_snapshot_ready: "模拟更新已准备",
      mock_not_enabled: "模拟更新未启用",
      refresh_in_progress: "模拟更新进行中",
      demo_published: "完整模拟结果已发布",
      no_refresh_needed: "无需模拟补齐",
      not_initialized: "本地快照未初始化",
      manual_catchup_required: "需要手动补齐",
      failed_retained_prior: "模拟失败，已保留原快照",
      cancelled_retained_prior: "模拟取消，已保留原快照",
      scope_stale: "运行范围已失效",
    }[phase] || phase;
  }

  function renderRuntimeStatus(status) {
    currentRuntimeStatus = status;
    runtimePanel.hidden = false;
    runtimePill.textContent = phaseLabel(status.phase);
    const explanation = status.state_explanation || {};
    runtimeExplanation.replaceChildren(
      explanationCard("发生了什么", explanation.what_happened),
      explanationCard("为什么重要", explanation.why_it_matters),
      explanationCard("现在可以做什么", explanation.available_action),
    );
    runtimeCandidate.replaceChildren();
    if (status.candidate_projection) {
      const heading = document.createElement("h3");
      heading.textContent = "模拟候选结果（不写入本地历史）";
      const message = document.createElement("p");
      message.textContent = status.candidate_projection.message_zh;
      runtimeCandidate.append(heading, message);
    } else {
      const message = document.createElement("p");
      message.textContent = status.mock_enabled
        ? "尚未发布完整模拟候选。"
        : "默认应用未启用模拟更新，不会发送自动获取请求。";
      runtimeCandidate.append(message);
    }
    runtimeRetry.hidden = !(status.allowed_actions || []).includes("explicit_user_retry");
    runtimeTechnical.textContent = JSON.stringify({
      runtime_scope_revision_id: status.runtime_scope_revision_id,
      runtime_status_revision: status.runtime_status_revision,
      runtime_status_fingerprint: status.runtime_status_fingerprint,
      mock_enabled: status.mock_enabled,
      mock_scenario_id: status.mock_scenario_id,
      plan_fingerprint: status.plan_fingerprint,
      failure: status.failure,
      technical_details: status.technical_details,
    }, null, 2);
  }

  function commandBody(status, trigger) {
    const scope = status.runtime_scope;
    return {
      runtime_scope_version: scope.runtime_scope_version,
      runtime_scope_revision_id: status.runtime_scope_revision_id,
      prior_snapshot_id: scope.prior_snapshot_id,
      prior_snapshot_content_fingerprint: scope.prior_snapshot_content_fingerprint,
      as_of_cutoff: scope.as_of_cutoff,
      as_of_recorded_at_utc: scope.as_of_recorded_at_utc,
      equity_series_key: scope.equity_series_key,
      benchmark_series_key: scope.benchmark_series_key,
      sector_series_key: scope.sector_series_key,
      trigger,
      expected_runtime_status_fingerprint: status.runtime_status_fingerprint,
    };
  }

  async function executeRuntime(status, trigger) {
    const version = ++runtimeRequestVersion;
    try {
      renderRuntimeStatus({
        ...status,
        phase: "refresh_in_progress",
        state_explanation: {
          what_happened: "正在执行一次同步、有限的模拟更新。",
          why_it_matters: "先前本地快照仍是当前权威内容。",
          available_action: "等待本次请求返回，不会后台轮询。",
        },
      });
      await loadReadModel();
      const next = await jsonRequest("/today-market/api/runtime-refresh", {
        method: "POST",
        body: JSON.stringify(commandBody(status, trigger)),
      });
      if (version !== runtimeRequestVersion) return;
      renderRuntimeStatus(next);
      await loadReadModel();
    } catch (error) {
      if (version !== runtimeRequestVersion) return;
      if (error.currentStatus) {
        renderRuntimeStatus(error.currentStatus);
      } else {
        renderRuntimeStatus({
          ...status,
          phase: "scope_stale",
          state_explanation: {
            what_happened: error.message,
            why_it_matters: "系统已在规划和获取前停止。",
            available_action: "重新读取本地快照和运行状态。",
          },
        });
      }
      await loadReadModel();
    }
  }

  async function loadRuntimeStatus() {
    const params = selectedScopeQuery();
    if (!params || snapshotContent.hidden) return;
    const version = ++runtimeRequestVersion;
    try {
      const status = await jsonRequest(`/today-market/api/runtime-status?${params.toString()}`);
      if (version !== runtimeRequestVersion || snapshotContent.hidden) return;
      renderRuntimeStatus(status);
      if (
        status.mock_enabled
        && status.automatic_attempt_state === "not_attempted"
        && !automaticScopes.has(status.runtime_scope_revision_id)
      ) {
        automaticScopes.add(status.runtime_scope_revision_id);
        await executeRuntime(status, "first_today_market_entry");
      }
    } catch (error) {
      if (version !== runtimeRequestVersion) return;
      runtimePanel.hidden = false;
      runtimePill.textContent = "运行状态不可用";
      runtimeExplanation.replaceChildren(
        explanationCard("发生了什么", error.message),
        explanationCard("为什么重要", "系统没有对未知或失效状态作推断。"),
        explanationCard("现在可以做什么", "重新读取本地快照后再试。"),
      );
      runtimeCandidate.replaceChildren();
      runtimeRetry.hidden = true;
      runtimeTechnical.textContent = JSON.stringify({ code: error.code }, null, 2);
    }
  }

  runtimeRetry.addEventListener("click", () => {
    if (currentRuntimeStatus) executeRuntime(currentRuntimeStatus, "explicit_user_retry");
  });

  new MutationObserver(() => {
    if (!snapshotContent.hidden) loadRuntimeStatus();
  }).observe(snapshotContent, { attributes: true, attributeFilter: ["hidden"] });
})();