"use strict";

(() => {
  const WORKFLOW_STEPS = ["研究主题", "确认范围", "候选公司", "人工审核", "研究结果"];
  const WORKFLOW_INDEX = {
    draft: 1,
    candidate_build_ready: 2,
    awaiting_review: 3,
    reviewed_plan_ready: 4,
  };
  const WORKFLOW_COPY = {
    draft: {
      happened: "研究主题已经记录，范围仍需要确认。",
      important: "未确认范围时不能安全构建完整候选池。",
      next: "继续确认市场、产业链、排除项和精确种子。",
    },
    candidate_build_ready: {
      happened: "研究范围已经准备好构建候选公司。",
      important: "候选来源必须精确选择，不能从名称或热度推断。",
      next: "检查来源并构建完整本地范围候选池。",
    },
    awaiting_review: {
      happened: "完整候选池已经构建，仍需逐条完成三态审核。",
      important: "任何显示过滤都不能把未审阅候选从提交宇宙中删除。",
      next: "为每条路径选择纳入、排除或待确认，并填写理由与不确定性。",
    },
    reviewed_plan_ready: {
      happened: "完整审阅计划已经生成。",
      important: "结果可以复现，但尚未写入正式领域所有者，也不是投资建议。",
      next: "查看精确研究结果、来源和双时间边界。",
    },
    reviewed_local_scope: {
      happened: "当前确认的本地范围已经完整审阅。",
      important: "完整只针对已确认本地范围，不等于全市场覆盖。",
      next: "阅读结果并保留范围说明。",
    },
    partial_local_coverage: {
      happened: "当前本地来源不能覆盖已声明范围。",
      important: "不完整覆盖可能遗漏受益路径，不能标记为完整成功。",
      next: "缩小范围、补充精确来源，或保留覆盖警告。",
    },
    coverage_unknown: {
      happened: "系统无法证明当前范围是否完整。",
      important: "未知不能当作完整或中性状态。",
      next: "检查范围与来源后再继续。",
    },
    selected_for_acceptance: {
      happened: "该候选路径被纳入后续研究计划。",
      important: "这里只是审阅计划，不是正式受益公司或投资候选认定。",
      next: "补全理由、暴露类型和不确定性，并完成其余候选审阅。",
    },
    rejected_by_user: {
      happened: "该候选路径在本次审阅中暂不纳入。",
      important: "路径、来源和理由仍保留在历史中，不会被删除。",
      next: "记录明确排除理由，或在保存前重新选择状态。",
    },
    unresolved: {
      happened: "该候选路径仍待验证。",
      important: "证据、身份或受益路径不充分时不能强行得出结论。",
      next: "记录缺口与不确定性，后续获得证据后再创建新修订。",
    },
    partial: {
      happened: "返回的数据不完整或不足以形成该视图。",
      important: "缺失值不能被当作零、正常或成功。",
      next: "查看缺失原因，并调整明确范围或等待受控数据补充阶段。",
    },
    insufficient_data: {
      happened: "返回的数据不足以形成该视图。",
      important: "缺失值不能被当作零、正常或成功。",
      next: "查看缺失原因，并调整明确范围或等待受控数据补充阶段。",
    },
    different_cutoff: {
      happened: "参与记录的信息截止日不同。",
      important: "混合截止日会影响可比性和复现。",
      next: "返回精确边界，选择一致记录或保留明确警告。",
    },
    different_session: {
      happened: "参与数据来自不同有效交易日或研究会话。",
      important: "不能把未对齐状态描述为同一时点结论。",
      next: "查看有效日期并使用精确对齐记录。",
    },
    stale: {
      happened: "链接中的精确记录不在当前双时间边界内。",
      important: "自动换成新记录会改变历史含义。",
      next: "返回历史页并明确选择当前可见的精确记录。",
    },
    not_visible: {
      happened: "链接中的精确记录当前不可见。",
      important: "自动换成其他修订会改变历史含义。",
      next: "返回历史页并明确选择当前可见的精确记录。",
    },
    database_unavailable: {
      happened: "本地数据库当前无法读取。",
      important: "页面不能用空值或示例数据伪装成功。",
      next: "检查本地数据库配置和迁移状态后，重复同一读取。",
    },
    unsupported_capability: {
      happened: "当前阶段没有可靠契约支持该功能。",
      important: "推测值会混淆事实、分析和产品承诺。",
      next: "使用已开放能力；等待该功能单独治理。",
    },
    malformed_metadata: {
      happened: "返回状态缺少受支持的精确展示字段。",
      important: "猜测状态可能改变领域含义。",
      next: "保持当前记录可见，展开技术代码并从历史页重新选择。",
    },
    conflict: {
      happened: "精确研究或候选版本在提交前发生变化，本次写入未完成。",
      important: "静默重试或自动换到新版本可能把决定写入不同研究历史。",
      next: "保留当前页面中的未保存决定，重新读取精确页面，对比后再次确认。",
    },
  };

  const nativeFetch = window.fetch.bind(window);
  let scopeValidated = false;

  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  }

  function currentSurface() {
    const path = window.location.pathname;
    if (path === "/industry-analysis") return "history";
    if (path === "/industry-analysis/new") return "scope";
    if (/\/industry-analysis\/sessions\/[0-9a-f-]+\/revisions\/[0-9a-f-]+\/review$/i.test(path)) return "review";
    if (/\/industry-analysis\/sessions\/[0-9a-f-]+\/revisions\/[0-9a-f-]+\/result$/i.test(path)) return "result";
    return "other";
  }

  function workflowStateForSurface(state) {
    if (currentSurface() === "scope") {
      const params = new URLSearchParams(window.location.search);
      return params.has("session_revision_id") ? "draft" : "research_topic";
    }
    if (currentSurface() === "result") return "reviewed_plan_ready";
    return state;
  }

  function workflowIndex(state) {
    if (state === "research_topic") return 0;
    return Object.prototype.hasOwnProperty.call(WORKFLOW_INDEX, state) ? WORKFLOW_INDEX[state] : null;
  }

  function renderWorkflow(state) {
    const container = document.querySelector("#phase2b-workflow");
    if (!container) return;
    const normalized = workflowStateForSurface(state);
    const current = workflowIndex(normalized);
    const list = el("ol", null, "phase2b-workflow-list");
    WORKFLOW_STEPS.forEach((label, index) => {
      const item = el("li", null, "phase2b-workflow-step");
      let status = "尚不可用";
      if (current !== null && index < current) {
        item.classList.add("is-complete");
        status = "已完成";
      } else if (current !== null && index === current) {
        item.classList.add("is-current");
        item.setAttribute("aria-current", "step");
        status = "当前";
      } else {
        item.classList.add("is-unavailable");
        item.setAttribute("aria-disabled", "true");
      }
      item.append(el("strong", label), el("small", status));
      list.append(item);
    });
    container.replaceChildren(list);
  }

  function copyFor(code) {
    return WORKFLOW_COPY[code] || WORKFLOW_COPY.malformed_metadata;
  }

  function renderState(code, target = "#phase2b-state") {
    const container = document.querySelector(target);
    if (!container) return;
    const copy = copyFor(code);
    const grid = el("div", null, "phase2b-state-grid");
    [
      ["发生了什么", copy.happened],
      ["为什么重要", copy.important],
      ["现在可以做什么", copy.next],
    ].forEach(([heading, body]) => {
      const article = el("article");
      article.append(el("h3", heading), el("p", body));
      grid.append(article);
    });
    container.replaceChildren(grid);
  }

  function demotePrimaryActions() {
    document.querySelectorAll(".button.button-primary").forEach((node) => {
      node.classList.remove("button-primary");
      node.classList.add("button-secondary", "phase2b-secondary-primary");
    });
  }

  function makePrimary(node) {
    if (!node) return;
    demotePrimaryActions();
    node.classList.remove("button-secondary", "phase2b-secondary-primary");
    node.classList.add("button-primary");
  }

  function safeContinuation(continuation) {
    if (!continuation || typeof continuation !== "object") return null;
    const kind = continuation.kind;
    const label = continuation.label;
    const path = continuation.path;
    if (kind === "unavailable") return path === null ? { ...continuation, path: null } : null;
    if (!["scope", "candidate_review", "result"].includes(kind)) return null;
    if (typeof label !== "string" || typeof path !== "string") return null;
    let parsed;
    try {
      parsed = new URL(path, window.location.origin);
    } catch (_error) {
      return null;
    }
    if (parsed.origin !== window.location.origin) return null;
    const valid = kind === "scope"
      ? parsed.pathname === "/industry-analysis/new"
      : kind === "candidate_review"
        ? /^\/industry-analysis\/sessions\/[0-9a-f-]+\/revisions\/[0-9a-f-]+\/review$/i.test(parsed.pathname)
        : /^\/industry-analysis\/sessions\/[0-9a-f-]+\/revisions\/[0-9a-f-]+\/result$/i.test(parsed.pathname);
    return valid ? { ...continuation, path: `${parsed.pathname}${parsed.search}` } : null;
  }

  function localTime(value) {
    const date = new Date(value);
    return Number.isNaN(date.valueOf()) ? "时间不可用" : date.toLocaleString("zh-CN", { hour12: false });
  }

  function currentStepLabel(workflowState) {
    const index = workflowIndex(workflowState);
    return index === null ? "状态不可识别" : WORKFLOW_STEPS[index];
  }

  function recentTechnical(item) {
    const details = document.createElement("details");
    details.append(el("summary", "技术详情与双时间边界"));
    const grid = el("div", null, "phase2b-technical-grid");
    const advanced = item.advanced_details || {};
    [
      ["Session ID", item.session_id],
      ["Revision ID", item.visible_latest_revision_id],
      ["Revision number", item.visible_latest_revision_number],
      ["Information cutoff", item.information_cutoff_date],
      ["Recorded UTC", item.recorded_at_utc],
      ["Input fingerprint", advanced.input_fingerprint_sha256 || "不可用"],
      ["Continuation reason", item.continuation && item.continuation.reason_code],
    ].forEach(([label, value]) => grid.append(el("span", `${label}: ${value ?? "不可用"}`)));
    details.append(grid);
    return details;
  }

  function firstUseGuide(container) {
    const wrapper = el("div", null, "phase2b-first-use");
    wrapper.append(
      el("h3", "从一个明确问题开始"),
      el("p", "当前双时间边界内没有可见的精确研究历史；这不等同于数据库不可用。"),
    );
    const list = el("ol");
    [
      ["描述研究主题", "用普通中文写下行业、产业链、技术、政策或利润池问题。"],
      ["确认研究范围", "明确市场、时间、产业链边界、排除项和已知种子。"],
      ["审核完整候选池", "构建本地范围全量候选，并逐条选择纳入、排除或待确认。"],
    ].forEach(([heading, body]) => {
      const item = el("li");
      item.append(el("strong", heading), el("span", body));
      list.append(item);
    });
    const action = el("a", "发起新研究", "button button-primary");
    action.href = "/industry-analysis/new";
    wrapper.append(list, action);
    container.replaceChildren(wrapper);
    makePrimary(action);
  }

  function renderRecent(payload) {
    const container = document.querySelector("#recent-research-content");
    const panel = document.querySelector("#recent-research-panel");
    if (!container || !panel || !payload || !Array.isArray(payload.sessions)) return;
    panel.hidden = false;
    if (payload.sessions.length === 0) {
      firstUseGuide(container);
      const empty = document.querySelector("#history-empty");
      if (empty) empty.hidden = true;
      return;
    }

    const item = payload.sessions[0];
    const continuation = safeContinuation(item.continuation);
    const card = el("article", null, "phase2b-recent-card");
    const copy = el("div", null, "phase2b-recent-copy");
    copy.append(
      el("h3", item.thesis_title || "未命名研究"),
      el("p", item.thesis_text_preview || "没有可显示的摘要。"),
    );
    const meta = el("div", null, "phase2b-recent-meta");
    meta.append(
      el("span", currentStepLabel(item.workflow_state), "meta-chip"),
      el("span", item.coverage_state || "coverage_unknown", `meta-chip${item.coverage_state === "reviewed_local_scope" ? "" : " is-warning"}`),
      el("span", `更新于 ${localTime(item.recorded_at_utc)}`, "meta-chip"),
    );
    copy.append(meta, recentTechnical(item));

    const side = el("div", null, "phase2b-recent-action");
    if (continuation && continuation.path) {
      const action = el("a", continuation.label, "button button-primary");
      action.href = continuation.path;
      side.append(action);
      makePrimary(action);
    } else {
      side.append(el("p", "这条最新精确记录当前不可继续；系统没有跳到更旧记录。"));
      const action = el("a", "发起新研究", "button button-primary");
      action.href = "/industry-analysis/new";
      side.append(action);
      makePrimary(action);
    }
    card.append(copy, side);
    container.replaceChildren(card);
    renderState(item.workflow_state, "#recent-research-state");
  }

  function renderHistoryFailure(code) {
    const panel = document.querySelector("#recent-research-panel");
    const container = document.querySelector("#recent-research-content");
    if (!panel || !container) return;
    panel.hidden = false;
    const mapped = code && code.includes("database") ? "database_unavailable" : "malformed_metadata";
    container.replaceChildren(el("p", copyFor(mapped).happened, "status-message is-error"));
    renderState(mapped, "#recent-research-state");
    const empty = document.querySelector("#history-empty");
    if (empty) empty.hidden = true;
    const retry = document.querySelector("#history-form button[type='submit']");
    if (retry) makePrimary(retry);
  }

  function renderFlowState(state, coverageState) {
    renderWorkflow(state);
    renderState(state);
    const coverage = coverageState && coverageState !== "reviewed_local_scope"
      ? document.querySelector("#phase2b-coverage-state")
      : null;
    if (coverage) {
      coverage.hidden = false;
      renderState(coverageState, "#phase2b-coverage-state");
    }
  }

  function scopePrimary(validated) {
    const check = document.querySelector("#scope-check-button");
    const save = document.querySelector("#scope-save-button");
    if (!check || !save) return;
    scopeValidated = validated;
    save.disabled = !validated;
    if (validated) {
      check.textContent = "重新检查研究范围";
      makePrimary(save);
    } else {
      check.textContent = "确认研究范围";
      save.classList.remove("button-primary");
      save.classList.add("button-secondary", "phase2b-secondary-primary");
      makePrimary(check);
    }
  }

  function candidatePrimary(state) {
    const selectors = state === "draft"
      ? ["#prepare-button"]
      : state === "candidate_build_ready"
        ? ["#candidate-build-button"]
        : state === "awaiting_review"
          ? ["#review-check-button"]
          : [];
    const action = selectors.map((selector) => document.querySelector(selector)).find(Boolean);
    if (action) makePrimary(action);
  }

  async function inspectResponse(response, requestUrl, method) {
    let payload = null;
    try {
      payload = await response.clone().json();
    } catch (_error) {
      payload = null;
    }
    const parsed = new URL(requestUrl, window.location.origin);
    const path = parsed.pathname;

    if (method === "GET" && path === "/industry-analysis/api/sessions") {
      window.setTimeout(() => {
        if (response.ok) renderRecent(payload);
        else renderHistoryFailure(payload && payload.detail && payload.detail.code);
      }, 0);
      return;
    }

    if (response.status === 409) {
      window.setTimeout(() => renderState("conflict"), 0);
    }

    if (method === "GET" && path.endsWith("/candidate-source-options") && response.ok && payload) {
      window.setTimeout(() => {
        renderFlowState(payload.workflow_state, payload.coverage_state);
        candidatePrimary(payload.workflow_state);
      }, 0);
      return;
    }

    if (method === "GET" && path.includes("/reviewed-plans/") && response.ok) {
      window.setTimeout(() => {
        renderFlowState("reviewed_plan_ready", payload && payload.coverage_state);
        makePrimary(document.querySelector(".topbar-actions a[href='/industry-analysis']"));
      }, 0);
      return;
    }

    if (currentSurface() === "scope" && method === "POST" && path.startsWith("/industry-analysis/api/sessions")) {
      const dryRun = parsed.searchParams.get("dry_run") === "true";
      window.setTimeout(() => {
        if (response.ok && dryRun) scopePrimary(true);
        if (response.ok && !dryRun) {
          const history = document.querySelector("#scope-success a[href='/industry-analysis']");
          if (history) makePrimary(history);
        }
      }, 0);
      return;
    }

    if (currentSurface() === "review" && method === "POST" && path.endsWith("/reviews")) {
      const dryRun = parsed.searchParams.get("dry_run") === "true";
      window.setTimeout(() => {
        if (response.ok && dryRun) makePrimary(document.querySelector("#review-save-button"));
      }, 0);
    }
  }

  window.fetch = async (...args) => {
    const input = args[0];
    const init = args[1] || {};
    const requestUrl = typeof input === "string" ? input : input.url;
    const method = String(init.method || (typeof input === "object" && input.method) || "GET").toUpperCase();
    const response = await nativeFetch(...args);
    inspectResponse(response, requestUrl, method).catch(() => {});
    return response;
  };

  function initializeScope() {
    renderFlowState(workflowStateForSurface(), "coverage_unknown");
    scopePrimary(false);
    const form = document.querySelector("#scope-form");
    if (!form) return;
    form.addEventListener("input", () => scopePrimary(false));
    form.addEventListener("submit", (event) => {
      if (scopeValidated) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      document.querySelector("#scope-check-button")?.click();
    }, true);
  }

  function initializeReview() {
    renderWorkflow(null);
    renderState("malformed_metadata");
    const form = document.querySelector("#review-form");
    if (form) {
      form.addEventListener("input", () => {
        const check = document.querySelector("#review-check-button");
        if (check) makePrimary(check);
      });
    }
  }

  function initializeResult() {
    renderFlowState("reviewed_plan_ready", null);
    makePrimary(document.querySelector(".topbar-actions a[href='/industry-analysis']"));
  }

  function initializeHistory() {
    demotePrimaryActions();
    const panel = document.querySelector("#recent-research-panel");
    if (panel) panel.hidden = false;
  }

  const surface = currentSurface();
  if (surface === "history") initializeHistory();
  if (surface === "scope") initializeScope();
  if (surface === "review") initializeReview();
  if (surface === "result") initializeResult();

  window.AQuantAIPhase2B = Object.freeze({
    workflowSteps: [...WORKFLOW_STEPS],
    workflowCopy: WORKFLOW_COPY,
    safeContinuation,
    renderWorkflow,
    renderState,
  });
})();
