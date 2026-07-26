"use strict";

const routeMatch = window.location.pathname.match(
  /^\/industry-analysis\/sessions\/([0-9a-f-]+)\/revisions\/([0-9a-f-]+)\/acceptance$/i,
);
const route = routeMatch
  ? { sessionId: routeMatch[1], reviewedRevisionId: routeMatch[2] }
  : null;
const query = new URLSearchParams(window.location.search);
const boundary = {
  cutoff: query.get("as_of_cutoff"),
  recordedAtUtc: query.get("as_of_recorded_at_utc"),
};

const state = { view: null, preview: null };

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined && text !== null) element.textContent = String(text);
  if (className) element.className = className;
  return element;
}

function setStatus(message, kind = "") {
  const element = document.querySelector("#acceptance-status");
  element.textContent = message;
  element.className = `status-message${kind ? ` is-${kind}` : ""}`;
}

function showErrors(messages) {
  const summary = document.querySelector("#error-summary");
  const list = document.querySelector("#error-list");
  list.replaceChildren(...messages.map((message) => node("li", message)));
  summary.hidden = messages.length === 0;
  if (messages.length) summary.focus();
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
  const error = new Error(
    detail && typeof detail === "object"
      ? detail.message || detail.technical_message
      : detail || `请求失败（${response.status}）`,
  );
  error.code = detail && typeof detail === "object" ? detail.code : null;
  error.recovery = detail && typeof detail === "object" ? detail.recovery_action : null;
  error.preserveForm = Boolean(detail && detail.preserve_form);
  throw error;
}

function apiParams() {
  return new URLSearchParams({
    session_id: route.sessionId,
    as_of_cutoff: boundary.cutoff,
    as_of_recorded_at_utc: boundary.recordedAtUtc,
  });
}

function invalidatePreview() {
  state.preview = null;
  document.querySelector("#preview-section").hidden = true;
  document.querySelector("#commit-button").hidden = true;
  document.querySelector("#preview-state").textContent = "表单已修改";
}

function latestReuse(member) {
  const options = member.stage1_reuse_options || [];
  return [...options].sort((a, b) => b.revision_number - a.revision_number)[0] || null;
}

function selectedReuse(member) {
  const select = document.querySelector(`[data-reuse-for="${member.reviewed_candidate_revision_id}"]`);
  if (!select || !select.value) return null;
  return (member.stage1_reuse_options || []).find(
    (item) => item.beneficiary_revision_id === select.value,
  ) || null;
}

function renderSemanticSelect(member, reuse) {
  const select = document.querySelector(`[data-semantic-for="${member.reviewed_candidate_revision_id}"]`);
  select.replaceChildren(new Option("暂不绑定类型化语义", "none"));
  for (const item of (reuse && reuse.semantic_reuse_options) || []) {
    const option = new Option(
      `${item.summary || "精确语义版本"} · ${item.overall_status}`,
      item.profile_revision_id,
    );
    option.dataset.profileId = item.profile_id;
    select.add(option);
  }
}

function renderMember(member) {
  const card = node("article", null, "acceptance-card");
  const header = node("header");
  const heading = node("div");
  heading.append(
    node("h3", member.ordinary_identity_label),
    node("p", member.frozen_stock_binding.ordinary_label, "muted-copy"),
  );
  const meta = node("div", null, "member-meta");
  meta.append(
    node("span", member.reviewed_proposal_exposure, "meta-chip"),
    node("span", `顺序 ${member.sequence + 1}`, "meta-chip"),
  );
  header.append(heading, meta);

  const reuse = document.createElement("select");
  reuse.dataset.reuseFor = member.reviewed_candidate_revision_id;
  reuse.required = true;
  reuse.append(new Option("请选择精确 Stage 1 版本", ""));
  for (const item of member.stage1_reuse_options || []) {
    reuse.add(
      new Option(
        `第 ${item.revision_number} 版 · ${item.legacy_beneficiary_kind} · ${item.assessment_status}`,
        item.beneficiary_revision_id,
      ),
    );
  }
  const defaultReuse = latestReuse(member);
  if (defaultReuse) reuse.value = defaultReuse.beneficiary_revision_id;

  const semantic = document.createElement("select");
  semantic.dataset.semanticFor = member.reviewed_candidate_revision_id;
  renderSemanticSelectPlaceholder(semantic);

  const grid = node("div", null, "form-grid");
  const reuseLabel = node("label", null, "form-field");
  reuseLabel.append(node("span", "精确 Stage 1 版本"), reuse);
  const semanticLabel = node("label", null, "form-field");
  semanticLabel.append(node("span", "类型化语义"), semantic);
  grid.append(reuseLabel, semanticLabel);

  const blocking = member.blocking_reasons || [];
  if (!(member.stage1_reuse_options || []).length) {
    blocking.push({ message: "当前精确 Context 中没有可复用 Stage 1 版本；页面不会自动新建或推断。" });
  }
  const notices = node("div");
  for (const item of blocking) notices.append(node("p", item.message, "is-error"));

  card.append(header, grid, notices);
  reuse.addEventListener("change", () => {
    renderSemanticSelect(member, selectedReuse(member));
    renderPoolOptions();
    invalidatePreview();
  });
  semantic.addEventListener("change", invalidatePreview);
  queueMicrotask(() => renderSemanticSelect(member, defaultReuse));
  return card;
}

function renderSemanticSelectPlaceholder(select) {
  select.replaceChildren(new Option("暂不绑定类型化语义", "none"));
}

function selectedStatuses() {
  if (!state.view) return [];
  return state.view.members
    .map((member) => selectedReuse(member))
    .filter(Boolean)
    .map((item) => item.assessment_status);
}

function renderPoolOptions() {
  if (!state.view) return;
  const select = document.querySelector("#pool-mode");
  const previous = select.value;
  select.replaceChildren();
  const hasSupported = selectedStatuses().includes("supported");
  const contract = state.view.candidate_pool_operation_contract;
  if (!hasSupported) {
    select.add(new Option("不创建后续研究池（没有 supported 成员）", "none_no_supported_members"));
  } else {
    select.add(new Option("新建 supported 后续研究池", "create_supported_handoff"));
    for (const option of contract.append_options || []) {
      const element = new Option(
        `追加到 ${option.title} · 第 ${option.revision_number} 版`,
        `append:${option.candidate_pool_id}:${option.expected_latest_revision_id}`,
      );
      select.add(element);
    }
  }
  if ([...select.options].some((option) => option.value === previous)) select.value = previous;
  renderPoolFields();
}

function renderPoolFields() {
  const value = document.querySelector("#pool-mode").value;
  const create = value === "create_supported_handoff";
  document.querySelector("#pool-title-field").hidden = !create;
  document.querySelector("#pool-scope-field").hidden = !create;
  document.querySelector("#pool-option-field").hidden = true;
  document.querySelector("#pool-help").textContent = create
    ? "只会写入最终 assessment_status 为 supported 的精确成员。"
    : value.startsWith("append:")
      ? "追加目标来自当前精确 Case / Map / Map Revision。"
      : "完整成果仍保留 draft/disputed 成员，只是不创建后续研究池。";
}

function renderView(view) {
  state.view = view;
  document.querySelector("#acceptance-title").textContent = view.thesis_title;
  document.querySelector("#acceptance-thesis").textContent = `共 ${view.members.length} 家已选公司；请逐家确认正式版本。`;
  document.querySelector("#member-count").textContent = String(view.members.length);
  document.querySelector("#context-summary").textContent =
    `${view.research_case.case_key} / ${view.industry_map.map_key} / 第 ${view.industry_map.revision_number} 版`;
  const list = document.querySelector("#acceptance-members");
  list.replaceChildren(...view.members.map(renderMember));
  const defaults = view.output_metadata_defaults;
  document.querySelector("#output-title").value = defaults.output_title;
  document.querySelector("#output-scope").value = defaults.output_scope;
  const create = view.candidate_pool_operation_contract.create_contract;
  document.querySelector("#pool-title-input").value = create.title_default;
  document.querySelector("#pool-scope-input").value = create.scope_default;
  renderPoolOptions();
  document.querySelector("#acceptance-technical").textContent = JSON.stringify({
    owner_context: view.owner_context,
    reviewed_session_revision_id: view.reviewed_session_revision_id,
    reviewed_plan_fingerprint_sha256: view.reviewed_plan_fingerprint_sha256,
    information_cutoff_date: view.information_cutoff_date,
    as_of_recorded_at_utc: view.as_of_recorded_at_utc,
    owner_acceptance_plan_version: view.owner_acceptance_plan_version,
  }, null, 2);
  document.querySelector("#page-state").textContent = "精确 Context 已验证";
  document.querySelector("#page-state").classList.add("is-ready");
}

function buildPoolOperation() {
  const value = document.querySelector("#pool-mode").value;
  if (value === "none_no_supported_members") return { mode: value };
  if (value === "create_supported_handoff") {
    const create = state.view.candidate_pool_operation_contract.create_contract;
    return {
      mode: value,
      pool_key: create.pool_key,
      title: document.querySelector("#pool-title-input").value.trim(),
      scope: document.querySelector("#pool-scope-input").value.trim(),
    };
  }
  const [, candidatePoolId, expectedLatestRevisionId] = value.split(":");
  return {
    mode: "append_supported_handoff",
    candidate_pool_id: candidatePoolId,
    expected_latest_revision_id: expectedLatestRevisionId,
    title: document.querySelector("#pool-title-input").value.trim() || state.view.thesis_title,
    scope: document.querySelector("#pool-scope-input").value.trim() || state.view.industry_map.scope,
  };
}

function buildPayload() {
  const errors = [];
  const bindings = state.view.members.map((member) => {
    const reuse = selectedReuse(member);
    if (!reuse) {
      errors.push(`${member.ordinary_identity_label} 缺少精确 Stage 1 版本。`);
      return null;
    }
    const semanticSelect = document.querySelector(
      `[data-semantic-for="${member.reviewed_candidate_revision_id}"]`,
    );
    const semanticOption = semanticSelect.selectedOptions[0];
    const semanticOperation = semanticSelect.value === "none"
      ? "none"
      : "reuse_exact_semantic_revision";
    return {
      reviewed_candidate_revision_id: member.reviewed_candidate_revision_id,
      sequence: member.sequence,
      stage1_operation: "reuse_exact_beneficiary_revision",
      stage1: {
        beneficiary_id: reuse.beneficiary_id,
        beneficiary_revision_id: reuse.beneficiary_revision_id,
        stock_basic_record_id: reuse.stock_basic_record_id,
      },
      semantic_operation: semanticOperation,
      semantic: semanticOperation === "none" ? null : {
        profile_id: semanticOption.dataset.profileId,
        profile_revision_id: semanticSelect.value,
      },
      readiness_note: "普通用户在精确 Owner Context 中确认复用。",
    };
  });
  const title = document.querySelector("#output-title").value.trim();
  const scope = document.querySelector("#output-scope").value.trim();
  const note = document.querySelector("#revision-note").value.trim();
  if (!title) errors.push("请填写成果标题。");
  if (!scope) errors.push("请填写成果范围。");
  if (!note) errors.push("请填写本次接受说明。");
  showErrors(errors);
  if (errors.length) return null;
  return {
    reviewed_session_revision_id: state.view.reviewed_session_revision_id,
    expected_session_latest_revision_number: state.view.expected_session_latest_revision_number,
    reviewed_plan_fingerprint_sha256: state.view.reviewed_plan_fingerprint_sha256,
    research_case_id: state.view.owner_context.research_case_id,
    map_mode: state.view.owner_context.map_mode,
    industry_map_id: state.view.owner_context.industry_map_id,
    industry_map_revision_id: state.view.owner_context.industry_map_revision_id,
    candidate_owner_bindings: bindings,
    candidate_pool_operation: buildPoolOperation(),
    output_title: title,
    output_scope: scope,
    information_cutoff_date: state.view.information_cutoff_date,
    revision_note: note,
    owner_acceptance_plan_version: state.view.owner_acceptance_plan_version,
  };
}

function renderPreview(preview) {
  state.preview = preview;
  document.querySelector("#preview-section").hidden = false;
  document.querySelector("#preview-state").textContent = preview.commit_ready ? "可提交" : "需要修正";
  document.querySelector("#preview-summary").replaceChildren(
    fact("完整成员", preview.complete_universe_count),
    fact("supported 后续研究", preview.supported_handoff_count),
    fact("候选池操作", preview.candidate_pool_mode),
    fact("写入状态", "尚未写入"),
  );
  document.querySelector("#preview-technical").textContent = JSON.stringify(preview, null, 2);
  document.querySelector("#commit-button").hidden = !preview.commit_ready;
}

function fact(label, value) {
  const item = node("div", null, "fact-card");
  item.append(node("strong", label), node("span", value));
  return item;
}

async function submitPreview(event) {
  event.preventDefault();
  const payload = buildPayload();
  if (!payload) return;
  document.querySelector("#preview-button").disabled = true;
  setStatus("正在生成零写入变更预览……");
  try {
    const response = await fetch(
      `/industry-analysis/api/session-revisions/${encodeURIComponent(route.reviewedRevisionId)}/owner-acceptance/preview?${apiParams()}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
      },
    );
    renderPreview(await readJson(response));
    setStatus("预览已生成，尚未写入。请检查后再次明确确认。", "success");
  } catch (error) {
    showErrors([error.message, error.recovery].filter(Boolean));
    setStatus("预览失败；页面不会自动重试或移动版本。", "error");
  } finally {
    document.querySelector("#preview-button").disabled = false;
  }
}

async function commit() {
  if (!state.preview || !state.preview.commit_ready) return;
  if (!window.confirm("确认写入本次研究成果？该操作会追加不可变本地历史。")) return;
  const payload = buildPayload();
  if (!payload) return;
  document.querySelector("#commit-button").disabled = true;
  setStatus("正在提交精确成果……");
  try {
    const response = await fetch(
      `/industry-analysis/api/session-revisions/${encodeURIComponent(route.reviewedRevisionId)}/owner-acceptance/commit?${apiParams()}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          ...payload,
          preview_fingerprint_sha256: state.preview.preview_fingerprint_sha256,
        }),
      },
    );
    const result = await readJson(response);
    setStatus("成果已接受，正在打开精确结果。", "success");
    window.location.assign(result.accepted_result_path);
  } catch (error) {
    showErrors([error.message, error.recovery].filter(Boolean));
    setStatus("提交失败；请先确认是否已经写入，不会自动重试。", "error");
    document.querySelector("#commit-button").disabled = false;
  }
}

async function initialize() {
  if (!route || !boundary.cutoff || !boundary.recordedAtUtc) {
    showErrors(["缺少精确 session、reviewed revision 或双时间边界。请从审阅结果重新打开。"]);
    document.querySelector("#page-state").textContent = "精确链接无效";
    return;
  }
  document.querySelector("#back-result-link").href =
    `/industry-analysis/sessions/${route.sessionId}/revisions/${route.reviewedRevisionId}/result?${query}`;
  document.querySelector("#acceptance-form").addEventListener("submit", submitPreview);
  document.querySelector("#commit-button").addEventListener("click", commit);
  document.querySelector("#pool-mode").addEventListener("change", () => {
    renderPoolFields();
    invalidatePreview();
  });
  document.querySelectorAll("#output-title,#output-scope,#revision-note,#pool-title-input,#pool-scope-input")
    .forEach((element) => element.addEventListener("input", invalidatePreview));
  setStatus("正在验证 reviewed plan、Owner Context 和双时间边界……");
  try {
    const response = await fetch(
      `/industry-analysis/api/session-revisions/${encodeURIComponent(route.reviewedRevisionId)}/owner-acceptance-view?${apiParams()}`,
      { headers: { Accept: "application/json" } },
    );
    renderView(await readJson(response));
    setStatus("精确接受准备已读取；尚未执行任何写入。", "success");
  } catch (error) {
    showErrors([error.message, error.recovery].filter(Boolean));
    document.querySelector("#page-state").textContent = "当前不可接受";
    setStatus("页面不会回退到其他版本或推断研究归属。", "error");
  }
}

initialize();
