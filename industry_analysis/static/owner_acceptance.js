"use strict";

const routeMatch = window.location.pathname.match(
  /^\/industry-analysis\/sessions\/([0-9a-f-]+)\/revisions\/([0-9a-f-]+)\/acceptance$/i,
);
const route = routeMatch
  ? { sessionId: routeMatch[1], reviewedSessionRevisionId: routeMatch[2] }
  : null;
const query = new URLSearchParams(window.location.search);
const boundary = {
  cutoff: query.get("as_of_cutoff"),
  recordedAtUtc: query.get("as_of_recorded_at_utc"),
};

const state = {
  view: null,
  preview: null,
  previewPlan: null,
  suppressInvalidation: false,
};

function node(tag, value, className) {
  const element = document.createElement(tag);
  if (value !== undefined && value !== null) element.textContent = String(value);
  if (className) element.className = className;
  return element;
}

function setStatus(message, kind = "") {
  const element = document.querySelector("#acceptance-status");
  element.textContent = message;
  element.className = `status-message${kind ? ` is-${kind}` : ""}`;
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
  error.status = response.status;
  error.code = detail && typeof detail === "object" ? detail.code : null;
  error.recoveryAction = detail && typeof detail === "object" ? detail.recovery_action : null;
  error.preserveForm = Boolean(detail && typeof detail === "object" && detail.preserve_form);
  throw error;
}

function showErrors(messages) {
  const summary = document.querySelector("#error-summary");
  const list = document.querySelector("#error-list");
  list.replaceChildren();
  messages.forEach((message) => list.append(node("li", message)));
  summary.hidden = false;
  summary.focus();
}

function clearErrors() {
  document.querySelector("#error-summary").hidden = true;
  document.querySelector("#error-list").replaceChildren();
}

function summaryItem(label, value) {
  const item = node("div", null, "fact-card");
  item.append(node("strong", label), node("span", value));
  return item;
}

function labeledSelect(label, id, options, placeholder = "请选择") {
  const wrapper = node("label", null, "form-field");
  wrapper.append(node("span", label));
  const select = document.createElement("select");
  select.id = id;
  select.required = true;
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = placeholder;
  select.append(empty);
  options.forEach((option) => {
    const item = document.createElement("option");
    item.value = option.value;
    item.textContent = option.label;
    select.append(item);
  });
  wrapper.append(select);
  return wrapper;
}

function optionChecklist(label, id, options, valueBuilder) {
  const wrapper = node("fieldset", null, "form-field");
  const legend = node("legend", label);
  const list = node("div", null, "option-list");
  list.id = id;
  if (!options.length) {
    list.append(node("p", "没有可用的精确选项。", "muted-copy"));
  } else {
    options.forEach((option, index) => {
      const row = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = JSON.stringify(valueBuilder(option));
      input.id = `${id}-${index}`;
      row.append(input, node("span", option.ordinary_label || option.label || "精确记录"));
      list.append(row);
    });
  }
  wrapper.append(legend, list);
  return wrapper;
}

function textField(label, id, { textarea = false, maxLength = 1000, placeholder = "" } = {}) {
  const wrapper = node("label", null, "form-field");
  wrapper.append(node("span", label));
  const input = document.createElement(textarea ? "textarea" : "input");
  input.id = id;
  input.maxLength = maxLength;
  input.required = true;
  input.placeholder = placeholder;
  wrapper.append(input);
  return wrapper;
}

function stage1Choices(member) {
  const choices = [];
  member.stage1_reuse_options.forEach((option, index) => {
    choices.push({
      value: `reuse:${index}`,
      label: `复用正式记录 · ${option.ordinary_label}`,
    });
  });
  member.stage1_append_options.forEach((option, index) => {
    choices.push({
      value: `append:${index}`,
      label: `追加正式修订 · ${option.ordinary_label}`,
    });
  });
  if (member.stage1_create_contract.available) {
    choices.push({ value: "create", label: "创建正式 Stage 1 身份和首版记录" });
  }
  return choices;
}

function renderStage1Controls(member, sequence) {
  const container = document.querySelector(`#member-operation-controls-${sequence}`);
  container.replaceChildren();
  const selection = document.querySelector(`#stage1-operation-${sequence}`).value;
  if (!selection) return;

  if (selection.startsWith("reuse:")) {
    const index = Number(selection.split(":")[1]);
    const option = member.stage1_reuse_options[index];
    container.append(
      summaryItem("正式受益类型", option.legacy_beneficiary_kind),
      summaryItem("证据评估状态", option.assessment_status),
      summaryItem("正式说明", option.rationale_summary),
    );
    const semanticOptions = [
      { value: "none", label: "暂不绑定类型化语义" },
      ...option.semantic_reuse_options.map((item, itemIndex) => ({
        value: `reuse:${itemIndex}`,
        label: `复用类型化语义 · ${item.overall_status} · ${item.ordinary_label}`,
      })),
    ];
    container.append(
      labeledSelect(
        "类型化语义",
        `semantic-operation-${sequence}`,
        semanticOptions,
        "请选择是否复用类型化语义",
      ),
    );
    return;
  }

  const contract = member.stage1_create_contract;
  container.append(
    labeledSelect(
      "正式受益类型",
      `legacy-kind-${sequence}`,
      contract.legacy_beneficiary_kind_options,
    ),
    labeledSelect(
      "证据评估状态",
      `assessment-status-${sequence}`,
      contract.assessment_status_options,
    ),
    textField("正式受益说明", `rationale-summary-${sequence}`, {
      textarea: true,
      maxLength: 4000,
      placeholder: "说明产品、链条位置和证据支持下的受益路径",
    }),
    optionChecklist(
      "产业地图断言（至少一项）",
      `assertions-${sequence}`,
      contract.map_assertion_options,
      (item) => ({
        assertion_kind: item.assertion_kind,
        assertion_revision_id: item.assertion_revision_id,
      }),
    ),
    optionChecklist(
      "研究主张（至少一项）",
      `claims-${sequence}`,
      contract.claim_revision_options,
      (item) => item.claim_revision_id,
    ),
  );
  const semanticNotice = node(
    "p",
    "新建或追加 Stage 1 修订时，本页面不自动创作或迁移类型化语义；本次明确选择 none。",
    "muted-copy",
  );
  semanticNotice.id = `semantic-none-${sequence}`;
  container.append(semanticNotice);
}

function renderMember(member) {
  const sequence = member.sequence;
  const card = node("article", null, "acceptance-member");
  card.dataset.sequence = String(sequence);
  const header = document.createElement("header");
  const title = node("div");
  title.append(
    node("strong", member.ordinary_identity_label),
    node("p", `${member.source_label} · 冻结顺序 ${sequence + 1}`, "muted-copy"),
  );
  const blocked = member.blocking_reasons.length > 0;
  header.append(
    title,
    node("span", blocked ? "存在阻断" : "可检查", `member-status${blocked ? " is-disputed" : " is-supported"}`),
  );
  card.append(header);

  const identity = node("div", null, blocked ? "blocking-box" : "identity-box");
  identity.append(
    node("strong", "冻结的唯一正式股票记录"),
    node("p", member.frozen_stock_binding.ordinary_label),
  );
  if (member.frozen_stock_binding.state === "available") {
    identity.append(
      node(
        "p",
        `${member.frozen_stock_binding.source} · ${member.frozen_stock_binding.exchange || "交易所未标记"} · ${member.frozen_stock_binding.industry || "行业未标记"}`,
        "muted-copy",
      ),
    );
    const confirm = document.createElement("label");
    confirm.className = "checkbox-row";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = `identity-confirm-${sequence}`;
    confirm.append(
      checkbox,
      node("span", "我确认使用该冻结记录，不在成果接受阶段更换公司身份。"),
    );
    identity.append(confirm);
  }
  card.append(identity);

  if (member.blocking_reasons.length) {
    const blocking = node("div", null, "blocking-box");
    blocking.append(node("strong", "必须先修正"));
    const list = document.createElement("ul");
    member.blocking_reasons.forEach((reason) => list.append(node("li", reason.message)));
    blocking.append(list);
    card.append(blocking);
    return card;
  }

  const grid = node("div", null, "acceptance-member-grid");
  grid.append(
    labeledSelect(
      "Stage 1 正式操作",
      `stage1-operation-${sequence}`,
      stage1Choices(member),
    ),
    textField("准备度说明", `readiness-note-${sequence}`, {
      textarea: true,
      maxLength: 1000,
      placeholder: "记录仍缺少的语义、公司研究或其他后续核验事项",
    }),
  );
  card.append(grid);

  const controls = node("div", null, "acceptance-member-grid");
  controls.id = `member-operation-controls-${sequence}`;
  card.append(controls);

  const operationSelect = grid.querySelector(`#stage1-operation-${sequence}`);
  operationSelect.addEventListener("change", () => renderStage1Controls(member, sequence));

  const details = document.createElement("details");
  details.className = "technical-details";
  details.append(node("summary", "查看冻结身份和候选技术详情"));
  details.append(
    node(
      "pre",
      JSON.stringify(
        {
          reviewed_candidate_revision_id: member.reviewed_candidate_revision_id,
          frozen_stock_binding: member.frozen_stock_binding,
          technical_details: member.technical_details,
        },
        null,
        2,
      ),
      "json-block",
    ),
  );
  card.append(details);
  return card;
}

function updatePoolFields() {
  const mode = document.querySelector("#pool-mode").value;
  const optionField = document.querySelector("#pool-option-field");
  const titleField = document.querySelector("#pool-title-field");
  const scopeField = document.querySelector("#pool-scope-field");
  const optionSelect = document.querySelector("#pool-option");
  const help = document.querySelector("#pool-help");
  optionField.hidden = true;
  titleField.hidden = true;
  scopeField.hidden = true;
  optionSelect.replaceChildren();

  if (!state.view) return;
  const contract = state.view.candidate_pool_operation_contract;
  if (mode === "create_supported_handoff") {
    titleField.hidden = false;
    scopeField.hidden = false;
    document.querySelector("#pool-title-input").value = contract.create_contract.title_default;
    document.querySelector("#pool-scope-input").value = contract.create_contract.scope_default;
    help.textContent = "创建一个只包含最终 supported 成员的精确候选池版本。";
  } else if (mode === "append_supported_handoff") {
    optionField.hidden = false;
    titleField.hidden = false;
    scopeField.hidden = false;
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "请选择精确候选池最新版本";
    optionSelect.append(empty);
    contract.append_options.forEach((option, index) => {
      const item = document.createElement("option");
      item.value = String(index);
      item.textContent = `${option.ordinary_label} · 第 ${option.revision_number} 版`;
      optionSelect.append(item);
    });
    help.textContent = "提交时会核对所选候选池的 expected-latest 修订。";
  } else if (mode === "reuse_exact_supported_handoff") {
    optionField.hidden = false;
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "请选择成员完全一致的精确候选池版本";
    optionSelect.append(empty);
    contract.reuse_options.forEach((option, index) => {
      const item = document.createElement("option");
      item.value = String(index);
      item.textContent = `${option.ordinary_label} · 第 ${option.revision_number} 版`;
      optionSelect.append(item);
    });
    help.textContent = "仅当该版本成员与本次最终 supported 修订集合完全一致时核心才会接受。";
  } else if (mode === "none_no_supported_members") {
    help.textContent = contract.zero_supported_contract.notice;
  } else {
    help.textContent = "必须明确选择一次全局候选池操作。";
  }
}

function renderView(view) {
  state.view = view;
  document.querySelector("#acceptance-title").textContent = view.thesis_title;
  document.querySelector("#acceptance-thesis").textContent = view.thesis_text_original;
  document.querySelector("#member-count").textContent = String(view.members.length);
  document.querySelector("#output-title").value = view.output_metadata_defaults.output_title;
  document.querySelector("#output-scope").value = view.output_metadata_defaults.output_scope;

  const members = document.querySelector("#acceptance-members");
  members.replaceChildren();
  view.members.forEach((member) => members.append(renderMember(member)));

  const poolMode = document.querySelector("#pool-mode");
  poolMode.replaceChildren();
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "请选择";
  poolMode.append(empty);
  [
    ["create_supported_handoff", "创建 supported 后续研究池"],
    ["append_supported_handoff", "追加到精确候选池最新版本"],
    ["reuse_exact_supported_handoff", "复用成员完全一致的精确候选池版本"],
    ["none_no_supported_members", "本次没有 supported 成员，不创建候选池"],
  ].forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    poolMode.append(option);
  });
  poolMode.addEventListener("change", updatePoolFields);

  const resultQuery = new URLSearchParams({
    as_of_cutoff: view.as_of_cutoff,
    as_of_recorded_at_utc: view.as_of_recorded_at_utc,
  });
  document.querySelector("#back-result-link").href =
    `/industry-analysis/sessions/${encodeURIComponent(view.session_id)}/revisions/` +
    `${encodeURIComponent(view.reviewed_session_revision_id)}/result?${resultQuery.toString()}`;

  document.querySelector("#acceptance-technical").textContent = JSON.stringify(
    {
      session_id: view.session_id,
      reviewed_session_revision_id: view.reviewed_session_revision_id,
      reviewed_session_revision_number: view.reviewed_session_revision_number,
      reviewed_plan_fingerprint_sha256: view.reviewed_plan_fingerprint_sha256,
      research_case: view.research_case,
      industry_map: view.industry_map,
      information_cutoff_date: view.information_cutoff_date,
      recorded_at_utc: view.recorded_at_utc,
      as_of_cutoff: view.as_of_cutoff,
      as_of_recorded_at_utc: view.as_of_recorded_at_utc,
      map_mode: view.map_mode,
      owner_acceptance_plan_version: view.owner_acceptance_plan_version,
      technical_details: view.technical_details,
    },
    null,
    2,
  );

  if (view.blocking_reasons.length) {
    showErrors(view.blocking_reasons.map((reason) => reason.message));
    document.querySelector("#preview-button").disabled = true;
    document.querySelector("#page-state").textContent = "存在前置阻断";
    document.querySelector("#page-state").classList.add("is-unavailable");
    setStatus("必须先返回前置审核修正冻结身份；本页没有执行任何写入。", "error");
  } else {
    document.querySelector("#page-state").textContent = "等待明确检查";
    document.querySelector("#page-state").classList.add("is-ready");
    setStatus("精确准备状态已读取。请选择每个正式操作并生成预览。", "success");
  }
}

function selectedChecklistValues(selector) {
  return [...document.querySelectorAll(`${selector} input[type="checkbox"]:checked`)].map(
    (input) => JSON.parse(input.value),
  );
}

function memberBinding(member, errors) {
  const sequence = member.sequence;
  const confirmation = document.querySelector(`#identity-confirm-${sequence}`);
  if (!confirmation || !confirmation.checked) {
    errors.push(`${member.ordinary_identity_label}：必须明确确认冻结的唯一正式股票记录。`);
  }
  const operationElement = document.querySelector(`#stage1-operation-${sequence}`);
  const operationValue = operationElement ? operationElement.value : "";
  if (!operationValue) {
    errors.push(`${member.ordinary_identity_label}：请选择 Stage 1 正式操作。`);
    return null;
  }

  let stage1Operation;
  let stage1;
  let semanticOperation = "none";
  let semantic = null;
  if (operationValue.startsWith("reuse:")) {
    stage1Operation = "reuse_exact_beneficiary_revision";
    const index = Number(operationValue.split(":")[1]);
    const option = member.stage1_reuse_options[index];
    stage1 = {
      beneficiary_id: option.beneficiary_id,
      beneficiary_revision_id: option.beneficiary_revision_id,
      stock_basic_record_id: option.stock_basic_record_id,
    };
    const semanticElement = document.querySelector(`#semantic-operation-${sequence}`);
    const semanticValue = semanticElement ? semanticElement.value : "";
    if (!semanticValue) {
      errors.push(`${member.ordinary_identity_label}：请选择是否复用类型化语义。`);
    } else if (semanticValue.startsWith("reuse:")) {
      semanticOperation = "reuse_exact_semantic_revision";
      const semanticIndex = Number(semanticValue.split(":")[1]);
      const selected = option.semantic_reuse_options[semanticIndex];
      semantic = {
        profile_id: selected.profile_id,
        profile_revision_id: selected.profile_revision_id,
      };
    }
  } else {
    const contract = member.stage1_create_contract;
    const kind = document.querySelector(`#legacy-kind-${sequence}`)?.value || "";
    const status = document.querySelector(`#assessment-status-${sequence}`)?.value || "";
    const rationale = document.querySelector(`#rationale-summary-${sequence}`)?.value.trim() || "";
    const assertions = selectedChecklistValues(`#assertions-${sequence}`);
    const claims = selectedChecklistValues(`#claims-${sequence}`);
    if (!kind) errors.push(`${member.ordinary_identity_label}：请选择正式受益类型。`);
    if (!status) errors.push(`${member.ordinary_identity_label}：请选择证据评估状态。`);
    if (!rationale) errors.push(`${member.ordinary_identity_label}：请填写正式受益说明。`);
    if (!assertions.length) errors.push(`${member.ordinary_identity_label}：至少选择一条产业地图断言。`);
    if (!claims.length) errors.push(`${member.ordinary_identity_label}：至少选择一条研究主张。`);
    const common = {
      stock_basic_record_id: contract.stock_basic_record_id,
      source: contract.source,
      stock_code: contract.stock_code,
      legacy_beneficiary_kind: kind,
      assessment_status: status,
      rationale_summary: rationale,
      map_assertion_revisions: assertions,
      claim_revision_ids: claims,
    };
    if (operationValue === "create") {
      stage1Operation = "create_beneficiary_identity_and_revision";
      stage1 = common;
    } else {
      stage1Operation = "append_beneficiary_revision";
      const index = Number(operationValue.split(":")[1]);
      const option = member.stage1_append_options[index];
      stage1 = {
        ...common,
        beneficiary_id: option.beneficiary_id,
        expected_latest_revision_id: option.expected_latest_revision_id,
      };
    }
  }

  const readinessNote = document.querySelector(`#readiness-note-${sequence}`)?.value.trim() || "";
  if (!readinessNote) {
    errors.push(`${member.ordinary_identity_label}：请填写准备度说明。`);
  }
  return {
    reviewed_candidate_revision_id: member.reviewed_candidate_revision_id,
    sequence,
    stage1_operation: stage1Operation,
    stage1,
    semantic_operation: semanticOperation,
    semantic,
    readiness_note: readinessNote,
  };
}

function candidatePoolOperation(errors) {
  const mode = document.querySelector("#pool-mode").value;
  const contract = state.view.candidate_pool_operation_contract;
  if (!mode) {
    errors.push("请选择一次全局后续研究池操作。");
    return null;
  }
  if (mode === "none_no_supported_members") return { mode };
  if (mode === "create_supported_handoff") {
    const title = document.querySelector("#pool-title-input").value.trim();
    const scope = document.querySelector("#pool-scope-input").value.trim();
    if (!title) errors.push("请填写候选池标题。");
    if (!scope) errors.push("请填写候选池范围。");
    return {
      mode,
      pool_key: contract.create_contract.pool_key,
      title,
      scope,
    };
  }
  const selectedValue = document.querySelector("#pool-option").value;
  if (selectedValue === "") {
    errors.push("请选择一个精确候选池版本。");
    return null;
  }
  const index = Number(selectedValue);
  if (mode === "append_supported_handoff") {
    const option = contract.append_options[index];
    const title = document.querySelector("#pool-title-input").value.trim();
    const scope = document.querySelector("#pool-scope-input").value.trim();
    if (!title) errors.push("请填写追加后的候选池标题。");
    if (!scope) errors.push("请填写追加后的候选池范围。");
    return {
      mode,
      candidate_pool_id: option.candidate_pool_id,
      expected_latest_revision_id: option.expected_latest_revision_id,
      title,
      scope,
    };
  }
  const option = contract.reuse_options[index];
  return {
    mode,
    candidate_pool_id: option.candidate_pool_id,
    candidate_pool_revision_id: option.candidate_pool_revision_id,
  };
}

function buildPlan() {
  const errors = [];
  const bindings = state.view.members.map((member) => memberBinding(member, errors));
  const poolOperation = candidatePoolOperation(errors);
  const outputTitle = document.querySelector("#output-title").value.trim();
  const outputScope = document.querySelector("#output-scope").value.trim();
  const revisionNote = document.querySelector("#revision-note").value.trim();
  if (!outputTitle) errors.push("请填写成果标题。");
  if (!outputScope) errors.push("请填写成果范围。");
  if (!revisionNote) errors.push("请填写本次接受说明。");
  if (errors.length) throw new Error(errors.join("\n"));
  return {
    reviewed_session_revision_id: state.view.reviewed_session_revision_id,
    expected_session_latest_revision_number:
      state.view.expected_session_latest_revision_number,
    reviewed_plan_fingerprint_sha256: state.view.reviewed_plan_fingerprint_sha256,
    research_case_id: state.view.research_case.id,
    map_mode: state.view.map_mode,
    industry_map_id: state.view.industry_map.id,
    industry_map_revision_id: state.view.industry_map.revision_id,
    candidate_owner_bindings: bindings.filter(Boolean),
    candidate_pool_operation: poolOperation,
    output_title: outputTitle,
    output_scope: outputScope,
    information_cutoff_date: state.view.information_cutoff_date,
    revision_note: revisionNote,
    owner_acceptance_plan_version: state.view.owner_acceptance_plan_version,
  };
}

function invalidatePreview() {
  if (state.suppressInvalidation || !state.preview) return;
  state.preview = null;
  state.previewPlan = null;
  document.querySelector("#preview-section").hidden = true;
  document.querySelector("#commit-button").hidden = true;
  const previewButton = document.querySelector("#preview-button");
  previewButton.hidden = false;
  previewButton.classList.add("button-primary");
  setStatus("表单已修改，旧预览已失效；请重新生成预览。", "error");
}

function renderPreview(preview) {
  const section = document.querySelector("#preview-section");
  section.hidden = false;
  document.querySelector("#preview-state").textContent = preview.commit_ready ? "可以明确提交" : "存在阻断";
  document.querySelector("#preview-summary").replaceChildren(
    summaryItem("完整成员", preview.complete_universe_count),
    summaryItem("supported 后续研究", preview.supported_handoff_count),
    summaryItem("候选池操作", preview.candidate_pool_mode),
    summaryItem("是否可提交", preview.commit_ready ? "是" : "否"),
  );
  const operations = document.querySelector("#preview-operations");
  operations.replaceChildren();
  (preview.operation_summaries || []).forEach((item, index) => {
    const card = node("article", null, "preview-box");
    card.append(
      node("strong", `成员 ${index + 1}`),
      node("pre", JSON.stringify(item, null, 2), "json-block"),
    );
    operations.append(card);
  });
  document.querySelector("#preview-technical").textContent = JSON.stringify(
    {
      preview_fingerprint_sha256: preview.preview_fingerprint_sha256,
      owner_acceptance_plan_fingerprint_sha256:
        preview.owner_acceptance_plan_fingerprint_sha256,
      owner_transaction_id: preview.owner_transaction_id,
      reviewed_session_revision_id: preview.reviewed_session_revision_id,
      recorded_at_utc: preview.recorded_at_utc,
      blocked_reasons: preview.blocked_reasons,
    },
    null,
    2,
  );
  const previewButton = document.querySelector("#preview-button");
  const commitButton = document.querySelector("#commit-button");
  if (preview.commit_ready) {
    previewButton.hidden = true;
    previewButton.classList.remove("button-primary");
    commitButton.hidden = false;
    commitButton.focus();
  } else {
    commitButton.hidden = true;
    previewButton.hidden = false;
  }
  section.scrollIntoView({ block: "start", behavior: "smooth" });
}

async function previewAcceptance(event) {
  event.preventDefault();
  clearErrors();
  let plan;
  try {
    plan = buildPlan();
  } catch (error) {
    showErrors(error.message.split("\n"));
    setStatus("请补齐明确选择后再生成预览。", "error");
    return;
  }
  const params = new URLSearchParams({
    session_id: route.sessionId,
    as_of_cutoff: boundary.cutoff,
    as_of_recorded_at_utc: boundary.recordedAtUtc,
  });
  const button = document.querySelector("#preview-button");
  button.disabled = true;
  setStatus("正在生成无持久化写入的确定性预览……");
  try {
    const response = await fetch(
      `/industry-analysis/api/session-revisions/${encodeURIComponent(route.reviewedSessionRevisionId)}/owner-acceptance/preview?${params.toString()}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(plan),
      },
    );
    const preview = await readJson(response);
    state.preview = preview;
    state.previewPlan = JSON.parse(JSON.stringify(plan));
    renderPreview(preview);
    setStatus("预览已生成；尚未写入。请核对后明确确认。", "success");
  } catch (error) {
    const messages = [error.message];
    if (error.recoveryAction) messages.push(error.recoveryAction);
    showErrors(messages);
    setStatus("预览失败；页面不会自动重试，当前填写内容已保留。", "error");
  } finally {
    button.disabled = false;
  }
}

async function commitAcceptance() {
  if (!state.preview || !state.previewPlan || !state.preview.preview_fingerprint_sha256) {
    showErrors(["当前没有有效预览，请重新生成。"]);
    return;
  }
  clearErrors();
  const params = new URLSearchParams({
    session_id: route.sessionId,
    as_of_cutoff: boundary.cutoff,
    as_of_recorded_at_utc: boundary.recordedAtUtc,
  });
  const button = document.querySelector("#commit-button");
  button.disabled = true;
  setStatus("正在提交与预览完全一致的接受方案……");
  try {
    const response = await fetch(
      `/industry-analysis/api/session-revisions/${encodeURIComponent(route.reviewedSessionRevisionId)}/owner-acceptance/commit?${params.toString()}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          ...state.previewPlan,
          preview_fingerprint_sha256: state.preview.preview_fingerprint_sha256,
        }),
      },
    );
    const result = await readJson(response);
    setStatus(result.idempotent_replay ? "相同方案已存在，正在打开同一精确成果。" : "研究成果已接受，正在打开精确结果。", "success");
    window.location.assign(result.accepted_result_path);
  } catch (error) {
    const messages = [error.message];
    if (error.recoveryAction) messages.push(error.recoveryAction);
    showErrors(messages);
    setStatus("提交未完成；页面不会自动重试或覆盖既有结果，当前填写内容已保留。", "error");
    button.disabled = false;
  }
}

async function initialize() {
  if (!route || !boundary.cutoff || !boundary.recordedAtUtc) {
    document.querySelector("#page-state").textContent = "精确链接无效";
    document.querySelector("#page-state").classList.add("is-unavailable");
    showErrors(["缺少精确 session、reviewed revision 或双时间边界。请从研究历史重新打开。"]);
    return;
  }
  const params = new URLSearchParams({
    session_id: route.sessionId,
    as_of_cutoff: boundary.cutoff,
    as_of_recorded_at_utc: boundary.recordedAtUtc,
  });
  setStatus("正在读取冻结身份、正式记录和候选池目录……");
  try {
    const response = await fetch(
      `/industry-analysis/api/session-revisions/${encodeURIComponent(route.reviewedSessionRevisionId)}/owner-acceptance-view?${params.toString()}`,
      { headers: { Accept: "application/json" } },
    );
    const view = await readJson(response);
    state.suppressInvalidation = true;
    renderView(view);
    state.suppressInvalidation = false;
    document.querySelector("#acceptance-form").addEventListener("input", invalidatePreview);
    document.querySelector("#acceptance-form").addEventListener("change", invalidatePreview);
    document.querySelector("#acceptance-form").addEventListener("submit", previewAcceptance);
    document.querySelector("#commit-button").addEventListener("click", commitAcceptance);
  } catch (error) {
    document.querySelector("#page-state").textContent = "准备状态不可用";
    document.querySelector("#page-state").classList.add("is-unavailable");
    const messages = [error.message];
    if (error.recoveryAction) messages.push(error.recoveryAction);
    showErrors(messages);
    setStatus("页面不会回退到其他版本，也没有执行任何写入。", "error");
  }
}

initialize();
