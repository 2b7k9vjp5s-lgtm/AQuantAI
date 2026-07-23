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
    renderPriceBehavior(priceBehavior, payload.supported_analysis.price_behavior);
    renderLiquidity(liquidity, payload.supported_analysis.liquidity);
    renderBenchmark(benchmark, payload.supported_analysis.benchmark);
    renderSector(sector, payload.supported_analysis.sector);
    renderCompleteness(completeness, payload.supported_analysis.data_completeness);
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
      if (key === "warnings") return;
      const wrapper = document.createElement("dl");
      wrapper.className = "summary-item";
      const term = document.createElement("dt");
      term.textContent = labelFor(key);
      const description = document.createElement("dd");
      description.textContent = displayValue(item, key);
      wrapper.append(term, description);
      container.append(wrapper);
    });
  }

  function renderPriceBehavior(container, value) {
    container.replaceChildren();
    if (!value) {
      container.append(dataCard("状态", "当前没有可显示的价格行为数据。"));
      return;
    }
    container.append(
      dataCard("有效交易日", formatDate(value.effective_session)),
      dataCard("整体计算状态", statusLabel(value.calculation_status)),
      metricCard("近 20 个交易日", value.return_20, "median_return"),
      metricCard("近 60 个交易日", value.return_60, "median_return"),
      metricCard("近 20 个交易日波动", value.volatility_20, "median_annualized_volatility"),
      dataCard(
        "可比较样本",
        lines([
          ["匹配公司数", value.matched_cohort?.matched_cohort_count],
          ["请求公司数", value.matched_cohort?.requested_stock_count],
          ["中位年化波动", formatPercent(value.matched_cohort?.matched_median_annualized_volatility)],
          ["状态", statusLabel(value.matched_cohort?.calculation_status)],
          ["说明", reasonLabel(value.matched_cohort?.reason)],
        ]),
      ),
      dataCard("价格行为警告", warningText(value.warnings)),
    );
  }

  function metricCard(title, metric, valueKey) {
    if (!metric) return dataCard(title, "当前没有可显示的数据。");
    return dataCard(
      title,
      lines([
        [valueKey === "median_return" ? "中位收益" : "中位年化波动", formatPercent(metric[valueKey])],
        ["可用公司数", metric.eligible_stock_count],
        ["请求公司数", metric.requested_stock_count],
        ["正收益占比", formatPercent(metric.positive_share)],
        ["状态", statusLabel(metric.calculation_status)],
        ["说明", reasonLabel(metric.reason)],
      ]),
    );
  }

  function renderLiquidity(container, value) {
    container.replaceChildren();
    if (!value) {
      container.append(dataCard("状态", "当前没有可显示的流动性数据。"));
      return;
    }
    container.append(
      dataCard("有效交易日", formatDate(value.effective_session)),
      dataCard("整体计算状态", statusLabel(value.calculation_status)),
      dataCard(
        "最新成交额分布",
        lines([
          ["可用公司数", value.latest_eligible_count],
          ["不可用公司数", value.latest_unavailable_count],
          ["合计成交额（来源原始单位）", formatNumber(value.latest_total_amount)],
          ["中位成交额（来源原始单位）", formatNumber(value.latest_median_amount)],
          ["说明", reasonLabel(value.latest_aggregate_reason)],
        ]),
      ),
      dataCard(
        "成交集中度",
        lines([
          ["前 5 家占比", formatPercent(value.top5_concentration_share)],
          ["前 10% 公司占比", formatPercent(value.top_decile_concentration_share)],
          ["前 10% 公司数", value.top_decile_member_count],
        ]),
      ),
      activityCard("近 5 个交易日活跃度", value.activity_5),
      activityCard("近 20 个交易日活跃度", value.activity_20),
      dataCard(
        "高于 20 日基准的公司",
        lines([
          ["公司数", value.latest_above_20_session_baseline_count],
          ["占比", formatPercent(value.latest_above_20_session_baseline_share)],
        ]),
      ),
      dataCard("流动性警告", warningText(value.warnings)),
    );
  }

  function activityCard(title, activity) {
    if (!activity) return dataCard(title, "当前没有可显示的数据。");
    return dataCard(
      title,
      lines([
        ["活跃度比值", formatRatio(activity.activity_ratio)],
        ["匹配公司数", activity.matched_cohort_count],
        ["最新合计成交额（来源原始单位）", formatNumber(activity.latest_matched_total_amount)],
        ["历史基准成交额（来源原始单位）", formatNumber(activity.baseline_total_amount)],
        ["状态", statusLabel(activity.calculation_status)],
        ["说明", reasonLabel(activity.reason)],
      ]),
    );
  }

  function renderBenchmark(container, value) {
    container.replaceChildren();
    if (!value || value.status === "not_selected") {
      container.append(dataCard("状态", value?.message || "未选择本地基准数据。"));
      return;
    }
    container.append(
      dataCard(
        "范围与对齐",
        lines([
          ["整体对齐", statusLabel(value.alignment_status)],
          ["交易日对齐", statusLabel(value.session_alignment_status)],
          ["截止日对齐", statusLabel(value.cutoff_alignment_status)],
          ["请求指数数", value.requested_code_count],
          ["可用指数数", value.available_code_count],
          ["有效交易日", formatDate(value.effective_benchmark_session)],
        ]),
      ),
      dataCard("基准警告", warningText(value.warnings)),
    );
    const visibleMetrics = (value.metrics || []).slice(0, 12);
    visibleMetrics.forEach((metric) => {
      container.append(dataCard(
        `指数 ${metric.index_code}`,
        lines([
          ["最新收盘", formatNumber(metric.latest_close)],
          ["最新日收益", formatPercent(metric.latest_return)],
          ["高于 20 日均线", displayValue(metric.above_sma20)],
          ["高于 60 日均线", displayValue(metric.above_sma60)],
          ["近 20 日年化波动", formatPercent(metric.realized_volatility_20)],
          ["近 20 日最大回撤", formatPercent(metric.max_drawdown_20)],
        ]),
      ));
    });
    if ((value.metrics || []).length > visibleMetrics.length) {
      container.append(dataCard(
        "其余基准指标",
        `还有 ${(value.metrics || []).length - visibleMetrics.length} 项，请在技术详情中查看。`,
      ));
    }
  }

  function renderSector(container, value) {
    container.replaceChildren();
    if (!value || value.status === "not_selected") {
      container.append(dataCard("状态", value?.message || "未选择本地行业数据。"));
      return;
    }
    const cross = value.cross_section || {};
    container.append(
      dataCard(
        "范围与对齐",
        lines([
          ["覆盖状态", statusLabel(value.coverage_status)],
          ["整体对齐", statusLabel(value.alignment_status)],
          ["交易日对齐", statusLabel(value.session_alignment_status)],
          ["截止日对齐", statusLabel(value.cutoff_alignment_status)],
          ["请求行业数", value.requested_sector_count],
          ["可用行业数", value.available_sector_count],
          ["有效交易日", formatDate(value.effective_sector_session)],
        ]),
      ),
      dataCard(
        "行业横截面",
        lines([
          ["日收益为正的行业占比", formatPercent(cross.positive_latest_return_share)],
          ["高于 20 日均线的行业占比", formatPercent(cross.above_sma20_share)],
          ["有效日收益行业数", cross.valid_latest_return_count],
          ["有效均线行业数", cross.valid_sma20_count],
        ]),
      ),
      dataCard("当日表现靠前", rankedSectorText(cross.top_latest_return)),
      dataCard("当日表现靠后", rankedSectorText(cross.bottom_latest_return)),
      dataCard("近 20 日表现靠前", rankedSectorText(cross.top_return_20)),
      dataCard("近 20 日表现靠后", rankedSectorText(cross.bottom_return_20)),
      dataCard("行业警告", warningText(value.warnings)),
    );
  }

  function renderCompleteness(container, value) {
    container.replaceChildren();
    const diagnostics = value?.latest_data_diagnostics || {};
    container.append(
      dataCard("完整性状态", statusLabel(value?.status)),
      dataCard(
        "最新数据诊断",
        lines([
          ["最新数据陈旧或缺失", diagnostics.stale_or_missing_latest_count],
          ["最新交易日无成交", diagnostics.no_trade_latest_count],
          ["最新收益不可用", diagnostics.latest_return_unavailable_count],
        ]),
      ),
    );
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

  function warningText(values) {
    return Array.isArray(values) && values.length ? values.join("\n") : "无额外警告";
  }

  function rankedSectorText(values) {
    if (!Array.isArray(values) || !values.length) return "暂无可用排名";
    return values.map((item, index) => (
      `${index + 1}. ${item.sector_name}（${item.sector_code}）：${formatPercent(item.value)}`
    )).join("\n");
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
    if (typeof value === "object") return "详细内容请在下方技术详情中查看";
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
      ready: "可用",
      aligned: "已对齐",
      different_session: "交易日不同",
      different_cutoff: "截止日不同",
      unverified_selected_scope: "仅验证所选范围",
      no_eligible_local_data: "无可见本地数据",
      not_selected: "未选择",
    }[status] || reasonLabel(status);
  }

  function reasonLabel(reason) {
    return {
      available: "可用",
      complete: "完整",
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
    }[reason] || (reason ? String(reason) : "暂无");
  }

  function labelFor(key) {
    const labels = {
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
    };
    return labels[key] || key.replaceAll("_", " ");
  }
})();
