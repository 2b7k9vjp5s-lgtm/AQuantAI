"use strict";

const routeMatch = window.location.pathname.match(
  /^\/industry-analysis\/sessions\/([0-9a-f-]+)\/revisions\/([0-9a-f-]+)\/review$/i,
);
const route = routeMatch ? { sessionId: routeMatch[1], sessionRevisionId: routeMatch[2] } : null;
const query = new URLSearchParams(window.location.search);
const boundary = {
  cutoff: query.get("as_of_cutoff"),
  recordedAtUtc: query.get("as_of_recorded_at_utc"),
};
const ACCEPTANCE_PLAN_VERSION = "aquantai.industry-thesis-acceptance-plan.v1";
const UNCERTAINTY_OPTIONS = [
  ["confirmed_scope", "范围与信息已确认"],
  ["limited_evidence", "证据有限"],
  ["awaiting_verification", "等待进一步验证"],
  ["source_conflict", "来源存在冲突"],
  ["other", "其他不确定性"],
];
let sourceOptions = null;
let reviewView = null;
let busy = false;
let lastCheckedPayload = null;

function node(tag, value, className) {
  const element = document.createElement(tag);
  if (value !== undefined && value !== null) element.textContent = String(value);
  if (className) element.className = className;
  return element;
}

function setStatus(id, message, kind = "") {
  const element = document.querySelector(id);
  if (!element) return;
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
  throw error;
}

function exactQuery(extra = {}) {
  return new URLSearchParams({
    session_id: route.sessionId,
    as_of_cutoff: boundary.cutoff,
    as_of_recorded_at_utc: boundary.recordedAtUtc,
    ...extra,
  });
}

function reviewPath(result) {
  const params = new URLSearchParams({
    as_of_cutoff: result.information_cutoff_date,
    as_of_recorded_at_utc: result.recorded_at_utc,
  });
  return `/industry-analysis/sessions/${result.session_id}/revisions/${result.session_revision_id}/review?${params.toString()}`;
}

function setBusy(value, label = "") {
  busy = value;
  [
    "#prepare-button",
    "#candidate-check-button",
    "#candidate-build-button",
    "#review-check-button",
  ].forEach((selector) => {
    const button = document.querySelector(selector);
    if (button) button.disabled = value;
  });
  const save = document.querySelector("#review-save-button");
  if (save) save.disabled = value || !lastCheckedPayload;
  const form = document.querySelector("#review-form");
  if (form) form.setAttribute("aria-busy", value ? "true" : "false");
  if (label) document.querySelector("#page-state").textContent = label;
}

function summaryItem(label, value) {
  const item = node("div", null, "summary-item");
  item.append(node("strong", label), node("span", value || "未填写"));
  return item;
}

function renderResearchSummary(options) {
  const container = document.querySelector("#research-summary");
  container.replaceChildren(
    summaryItem("研究修订", `Revision ${options.session_revision_number}`),
    summaryItem("工作流状态", options.workflow_state),
    summaryItem("覆盖状态", options.coverage_state),
    summaryItem("信息截止", options.information_cutoff_date),
    summaryItem("公司种子", `${options.company_seed_count} 个`),
    summaryItem("产业地图", `${options.map_count} 个`),
  );
  const editParams = new URLSearchParams({
    session_id: route.sessionId,
    session_revision_id: route.sessionRevisionId,
    revision_number: String(options.session_revision_number),
    as_of_cutoff: boundary.cutoff,
    as_of_recorded_at_utc: boundary.recordedAtUtc,
  });
  document.querySelector("#edit-scope-link").href = `/industry-analysis/new?${editParams.toString()}`;
}

function renderSeeds(seeds) {
  const container = document.querySelector("#company-seeds");
  container.replaceChildren();
  if (!seeds.length) {
    container.append(node("p", "当前范围没有精确公司种子。", "option-empty"));
    return;
  }
  seeds.forEach((seed) => {
    const card = node("article", null, "source-card");
    const header = node("header");
    const copy = node("div");
    copy.append(node("strong", `${seed.label} · ${seed.code}`));
    copy.append(node("p", `${seed.source_kind} · ${seed.exact_id}`));
    header.append(copy, node("span", "已由范围修订确认", "locked-source"));
    card.append(header);
    container.append(card);
  });
}

function renderMapPools(maps) {
  const container = document.querySelector("#map-pools");
  container.replaceChildren();
  if (!maps.length) {
    container.append(node("p", "当前范围没有精确产业地图。", "option-empty"));
    return;
  }
  maps.forEach((map, mapIndex) => {
    const card = node("article", null, `map-card${map.eligible_candidate_pool_count ? "" : " source-unavailable"}`);
    const header = node("header");
    const copy = node("div");
    copy.append(node("strong", `${map.title} · revision ${map.revision_number}`));
    copy.append(node("p", map.scope));
    header.append(copy, node("span", `${map.eligible_candidate_pool_count} 个冻结 pool`, "meta-chip"));
    card.append(header);
    const list = node("div", null, "pool-list");
    if (!map.eligible_candidate_pools.length) {
      list.append(node("p", "当前双时间边界内没有与该精确地图修订绑定的冻结候选池；系统不会回退到其他版本。", "option-empty"));
    } else {
      map.eligible_candidate_pools.forEach((pool) => {
        const row = node("div", null, "pool-option");
        const label = node("label");
        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = `map-pool-${mapIndex}`;
        radio.value = pool.candidate_pool_revision_id;
        radio.dataset.poolRevisionId = pool.candidate_pool_revision_id;
        const text = node("span");
        text.append(node("strong", `${pool.title} · revision ${pool.revision_number}`));
        text.append(node("p", `${pool.member_count} 个冻结成员 · ${pool.pool_key}`));
        label.append(radio, text);
        row.append(label);
        list.append(row);
      });
    }
    card.append(list);
    container.append(card);
  });
}

function selectedPoolRevisionIds() {
  return Array.from(document.querySelectorAll("input[data-pool-revision-id]:checked"))
    .map((input) => input.dataset.poolRevisionId);
}

function renderBuildPreview(result) {
  const preview = document.querySelector("#build-preview");
  preview.hidden = false;
  preview.replaceChildren(
    summaryItem("检查方式", result.dry_run ? "Dry-run；没有写入" : "已写入"),
    summaryItem("候选总数", result.candidate_count),
    summaryItem("公司种子来源", result.composition.company_seed_proposal_count),
    summaryItem("Stage 1 来源", result.composition.stage1_proposal_count),
    summaryItem("审阅状态", "全部为 proposed"),
    summaryItem("暴露类型", "未推断；全部待审阅"),
  );
}

async function prepareScope() {
  if (busy) return;
  if (!sourceOptions || sourceOptions.company_seed_count + sourceOptions.map_count === 0) {
    setStatus("#prepare-status", "当前范围没有精确公司种子或产业地图，请先返回范围页面补充。", "error");
    return;
  }
  setBusy(true, "正在准备候选池");
  setStatus("#prepare-status", "正在追加 candidate_build_ready 范围修订……");
  try {
    const response = await fetch(
      `/industry-analysis/api/sessions/${encodeURIComponent(route.sessionId)}/revisions?dry_run=false`,
      {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({
          expected_latest_revision_number: sourceOptions.session_revision_number,
          changes: { workflow_state: "candidate_build_ready" },
          revision_note: "确认精确本地范围并准备候选池",
        }),
      },
    );
    const result = await readJson(response);
    setStatus("#prepare-status", "准备完成，正在打开新的精确修订。", "success");
    window.location.assign(reviewPath(result));
  } catch (error) {
    const guidance = error.status === 409
      ? " 请返回研究历史重新打开最新精确修订。"
      : " 页面不会自动重试；请先回研究历史确认是否已写入。";
    setStatus("#prepare-status", `${error.message}${guidance}`, "error");
    setBusy(false, "准备失败");
  }
}

async function buildCandidates(dryRun) {
  if (busy) return;
  const selected = selectedPoolRevisionIds();
  setBusy(true, dryRun ? "正在检查候选" : "正在构建候选");
  setStatus("#build-status", dryRun ? "正在执行无写入检查……" : "正在写入追加式候选历史……");
  try {
    const params = exactQuery({ dry_run: dryRun ? "true" : "false" });
    const response = await fetch(
      `/industry-analysis/api/session-revisions/${encodeURIComponent(route.sessionRevisionId)}/candidate-builds?${params.toString()}`,
      {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({
          expected_session_latest_revision_number: sourceOptions.session_revision_number,
          selected_candidate_pool_revision_ids: selected,
        }),
      },
    );
    const result = await readJson(response);
    renderBuildPreview(result);
    if (dryRun) {
      setStatus("#build-status", "检查通过。没有创建候选记录。", "success");
      setBusy(false, "本地数据可用");
      return;
    }
    setStatus("#build-status", "候选池已写入，正在重新打开精确完整宇宙。", "success");
    window.location.assign(result.review_path);
  } catch (error) {
    let guidance = " 已保留你明确选择的冻结 pool。";
    if (error.status === 409) {
      guidance += " 请重新打开最新精确修订后再确认。";
    } else if (!error.status || error.status >= 500) {
      guidance += " 页面不会自动重试；请先重新打开本页确认候选是否已写入。";
    }
    setStatus("#build-status", `${error.message}${guidance}`, "error");
    setBusy(false, "候选处理失败");
  }
}

function sourceLabel(candidate) {
  if (candidate.source_kind === "user_seed") return "明确公司种子";
  if (candidate.source_kind === "existing_industry_map_revision") return "冻结 Stage 1 候选池";
  return candidate.source_kind;
}

function factCell(label, value, detail = "") {
  const cell = node("div", null, "fact-cell");
  cell.append(node("strong", label), node("span", value || "未提供"));
  if (detail) cell.append(node("small", detail));
  return cell;
}

function renderUniverse(payload) {
  const empty = document.querySelector("#universe-empty");
  const list = document.querySelector("#universe-list");
  const summary = document.querySelector("#universe-summary");
  list.replaceChildren();
  empty.hidden = payload.candidate_count !== 0;
  list.hidden = payload.candidate_count === 0;
  summary.textContent = payload.candidate_count
    ? `完整显示 ${payload.candidate_count} 条精确候选路径；不同来源的同一公司不会合并。`
    : "当前精确修订尚未写入候选记录。";
  payload.candidates.forEach((candidate) => {
    const rationale = candidate.rationale || {};
    const uncertainty = candidate.uncertainty || {};
    const card = node("article", null, "candidate-card");
    const header = node("header");
    const copy = node("div");
    copy.append(node("strong", candidate.company_label_original));
    copy.append(node("p", rationale.stock_code || "代码未单独显示"));
    header.append(copy, node("span", sourceLabel(candidate), "meta-chip"));
    const grid = node("div", null, "candidate-card-grid");
    grid.append(
      factCell("身份状态", candidate.identity_state),
      factCell("Stage 1 类型", rationale.stage1_beneficiary_kind || "不适用 / 待审阅"),
      factCell("候选暴露", candidate.proposed_exposure_type, `置信度 ${candidate.proposal_confidence}`),
      factCell("审阅状态", candidate.review_state),
    );
    card.append(header, node("p", candidate.benefit_path_text), grid);
    const details = document.createElement("details");
    details.append(node("summary", "技术详情"));
    details.append(node("pre", JSON.stringify({
      candidate_id: candidate.candidate_id,
      candidate_revision_id: candidate.candidate_revision_id,
      candidate_key: candidate.candidate_key,
      source_reference: candidate.source_reference,
      rationale,
      uncertainty,
      recorded_at_utc: candidate.recorded_at_utc,
    }, null, 2), "json-block"));
    card.append(details);
    list.append(card);
  });
}

async function loadUniverse() {
  try {
    const params = exactQuery();
    const response = await fetch(
      `/industry-analysis/api/session-revisions/${encodeURIComponent(route.sessionRevisionId)}/candidates?${params.toString()}`,
      { headers: { Accept: "application/json" } },
    );
    const payload = await readJson(response);
    renderUniverse(payload);
    setStatus("#universe-status", payload.candidate_count ? "完整候选宇宙读取完成。" : "尚无候选写入。", "success");
    return payload;
  } catch (error) {
    setStatus("#universe-status", error.message || "完整候选池读取失败。", "error");
    renderUniverse({ candidate_count: 0, candidates: [] });
    return null;
  }
}

function reviewCard(candidate, index) {
  const card = node("article", null, "review-card is-incomplete");
  card.dataset.candidateRevisionId = candidate.candidate_revision_id;
  card.dataset.revisionNumber = String(candidate.revision_number);
  card.dataset.index = String(index);

  const header = node("header");
  const title = node("div", null, "review-card-title");
  title.append(node("strong", candidate.company_label_original));
  title.append(node("small", `${candidate.source_label} · 路径 ${index + 1}`));
  const identity = node(
    "span",
    candidate.can_select_for_acceptance ? "精确身份可纳入" : "身份仅可拒绝或待确认",
    `meta-chip${candidate.can_select_for_acceptance ? "" : " is-warning"}`,
  );
  header.append(title, identity);

  const sourceGrid = node("div", null, "review-source-grid");
  sourceGrid.append(
    factCell("来源", candidate.source_label, candidate.source_kind),
    factCell("身份", candidate.identity_state),
    factCell("原候选暴露", candidate.exposure_label, `置信度 ${candidate.proposal_confidence}`),
    factCell("受益路径", candidate.benefit_path_text),
  );

  const controls = node("div", null, "review-controls");
  const fieldset = node("fieldset", null, "decision-fieldset");
  const legend = node("legend", "审阅决定");
  const options = node("div", null, "decision-options");
  reviewView.decision_options.forEach((option) => {
    const label = node("label", null, "decision-option");
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = `decision-${candidate.candidate_revision_id}`;
    radio.value = option.value;
    radio.disabled = option.value === "selected_for_acceptance" && !candidate.can_select_for_acceptance;
    label.append(radio, node("span", option.label));
    options.append(label);
  });
  fieldset.append(legend, options);

  const exposureField = node("div", null, "review-field");
  const exposureLabel = node("label", "最终受益类型");
  exposureLabel.htmlFor = `exposure-${index}`;
  const exposure = document.createElement("select");
  exposure.id = `exposure-${index}`;
  exposure.dataset.role = "exposure";
  exposure.disabled = true;
  exposure.append(new Option("请选择", ""));
  reviewView.exposure_options.forEach((option) => exposure.append(new Option(option.label, option.value)));
  exposureField.append(exposureLabel, exposure, node("small", "仅“纳入后续研究”需要明确选择；不会自动沿用候选值。"));
  controls.append(fieldset, exposureField);

  const textGrid = node("div", null, "review-text-grid");
  const rationaleField = node("div", null, "review-field");
  const rationaleLabel = node("label", "审阅理由");
  rationaleLabel.htmlFor = `rationale-${index}`;
  const rationale = document.createElement("textarea");
  rationale.id = `rationale-${index}`;
  rationale.dataset.role = "rationale";
  rationale.maxLength = 2000;
  rationale.required = true;
  rationale.placeholder = "写明纳入、暂不纳入或待确认的具体理由";
  rationaleField.append(rationaleLabel, rationale);

  const uncertaintyField = node("div", null, "review-field");
  const uncertaintyLabel = node("label", "不确定性状态");
  uncertaintyLabel.htmlFor = `uncertainty-state-${index}`;
  const uncertainty = document.createElement("select");
  uncertainty.id = `uncertainty-state-${index}`;
  uncertainty.dataset.role = "uncertainty-state";
  uncertainty.required = true;
  uncertainty.append(new Option("请选择", ""));
  UNCERTAINTY_OPTIONS.forEach(([value, label]) => uncertainty.append(new Option(label, value)));
  uncertaintyField.append(uncertaintyLabel, uncertainty);

  const noteField = node("div", null, "review-field");
  const noteLabel = node("label", "不确定性说明");
  noteLabel.htmlFor = `uncertainty-note-${index}`;
  const note = document.createElement("textarea");
  note.id = `uncertainty-note-${index}`;
  note.dataset.role = "uncertainty-note";
  note.maxLength = 2000;
  note.required = true;
  note.placeholder = "说明仍需验证、存在冲突或不确定的具体事项";
  noteField.append(noteLabel, note);
  textGrid.append(rationaleField, uncertaintyField, noteField);

  const details = document.createElement("details");
  details.append(node("summary", "来源与技术详情"));
  details.append(node("pre", JSON.stringify({
    candidate_id: candidate.candidate_id,
    candidate_revision_id: candidate.candidate_revision_id,
    revision_number: candidate.revision_number,
    source_kind: candidate.source_kind,
    source_reference: candidate.source_reference,
    proposed_stock_basic_record_id: candidate.proposed_stock_basic_record_id,
    proposed_listed_instrument_id: candidate.proposed_listed_instrument_id,
    rationale: candidate.rationale,
    uncertainty: candidate.uncertainty,
  }, null, 2), "json-block"));
  card.append(header, sourceGrid, controls, textGrid, details);
  return card;
}

function selectedDecision(card) {
  return card.querySelector('input[type="radio"]:checked');
}

function updateReviewCard(card) {
  const selected = selectedDecision(card);
  const exposure = card.querySelector('[data-role="exposure"]');
  card.classList.remove("is-selected", "is-rejected", "is-unresolved");
  if (!selected) {
    exposure.disabled = true;
    exposure.value = "";
    return;
  }
  if (selected.value === "selected_for_acceptance") {
    card.classList.add("is-selected");
    exposure.disabled = false;
  } else {
    exposure.value = "";
    exposure.disabled = true;
    card.classList.add(selected.value === "rejected_by_user" ? "is-rejected" : "is-unresolved");
  }
}

function updateReviewCounts() {
  const cards = Array.from(document.querySelectorAll(".review-card"));
  const counts = { selected: 0, rejected: 0, unresolved: 0, undecided: 0 };
  cards.forEach((card) => {
    const decision = selectedDecision(card);
    if (!decision) counts.undecided += 1;
    else if (decision.value === "selected_for_acceptance") counts.selected += 1;
    else if (decision.value === "rejected_by_user") counts.rejected += 1;
    else counts.unresolved += 1;
  });
  const strip = document.querySelector("#review-counts");
  strip.replaceChildren(
    node("span", `总数 ${cards.length}`, "count-chip"),
    node("span", `纳入 ${counts.selected}`, "count-chip"),
    node("span", `暂不纳入 ${counts.rejected}`, "count-chip"),
    node("span", `待确认 ${counts.unresolved}`, "count-chip"),
    node("span", `未决定 ${counts.undecided}`, `count-chip${counts.undecided ? " is-warning" : ""}`),
  );
  return counts;
}

function invalidateReviewPreview() {
  lastCheckedPayload = null;
  document.querySelector("#review-save-button").disabled = true;
  document.querySelector("#review-preview").hidden = true;
  document.querySelectorAll(".review-card").forEach(updateReviewCard);
  updateReviewCounts();
}

function renderReview(view) {
  reviewView = view;
  const panel = document.querySelector("#review-panel");
  const rows = document.querySelector("#review-rows");
  rows.replaceChildren();
  view.candidates.forEach((candidate, index) => rows.append(reviewCard(candidate, index)));
  panel.hidden = false;
  rows.addEventListener("input", invalidateReviewPreview);
  document.querySelector("#review-revision-note").addEventListener("input", invalidateReviewPreview);
  updateReviewCounts();
}

function collectReviewPayload() {
  const cards = Array.from(document.querySelectorAll(".review-card"));
  const decisions = [];
  let firstInvalid = null;
  cards.forEach((card) => {
    card.classList.remove("is-incomplete");
    const decision = selectedDecision(card);
    const exposure = card.querySelector('[data-role="exposure"]');
    const rationale = card.querySelector('[data-role="rationale"]').value.trim();
    const uncertaintyState = card.querySelector('[data-role="uncertainty-state"]').value;
    const uncertaintyNote = card.querySelector('[data-role="uncertainty-note"]').value.trim();
    const invalid = !decision
      || !rationale
      || !uncertaintyState
      || !uncertaintyNote
      || (decision && decision.value === "selected_for_acceptance" && !exposure.value);
    if (invalid) {
      card.classList.add("is-incomplete");
      if (!firstInvalid) firstInvalid = card;
      return;
    }
    decisions.push({
      candidate_revision_id: card.dataset.candidateRevisionId,
      expected_latest_revision_number: Number(card.dataset.revisionNumber),
      decision: decision.value,
      final_proposed_exposure_type: decision.value === "selected_for_acceptance" ? exposure.value : null,
      rationale_text: rationale,
      uncertainty_state: uncertaintyState,
      uncertainty_note: uncertaintyNote,
    });
  });
  const revisionNote = document.querySelector("#review-revision-note").value.trim();
  if (!revisionNote) {
    document.querySelector("#review-revision-note").focus();
    setStatus("#review-status", "请填写本次审阅说明。", "error");
    return null;
  }
  if (firstInvalid || decisions.length !== cards.length) {
    if (firstInvalid) firstInvalid.scrollIntoView({ behavior: "smooth", block: "center" });
    setStatus("#review-status", "仍有候选缺少决定、最终受益类型、理由或不确定性说明。", "error");
    updateReviewCounts();
    return null;
  }
  return {
    expected_session_latest_revision_number: reviewView.session_revision_number,
    acceptance_plan_version: ACCEPTANCE_PLAN_VERSION,
    decisions,
    revision_note: revisionNote,
  };
}

function renderReviewPreview(result) {
  document.querySelector("#review-preview").hidden = false;
  document.querySelector("#review-preview-summary").replaceChildren(
    summaryItem("检查方式", result.dry_run ? "Dry-run；零写入" : "已保存"),
    summaryItem("候选总数", result.candidate_count),
    summaryItem("纳入后续研究", result.selected_count),
    summaryItem("暂不纳入", result.rejected_count),
    summaryItem("待确认", result.unresolved_count),
    summaryItem("工作流结果", result.workflow_state),
  );
  document.querySelector("#review-preview-technical").textContent = JSON.stringify({
    reviewed_session_revision_id: result.reviewed_session_revision_id,
    acceptance_plan_fingerprint_sha256: result.acceptance_plan_fingerprint_sha256,
    information_cutoff_date: result.information_cutoff_date,
    session_recorded_at_utc: result.session_recorded_at_utc,
    candidate_recorded_at_utc: result.candidate_recorded_at_utc,
    ownership_notice: result.ownership_notice,
  }, null, 2);
}

async function submitReview(dryRun) {
  if (busy) return;
  const payload = collectReviewPayload();
  if (!payload) return;
  const signature = JSON.stringify(payload);
  if (!dryRun && signature !== lastCheckedPayload) {
    setStatus("#review-status", "审阅内容自上次检查后已变化，请重新执行“检查审阅结果”。", "error");
    return;
  }
  setBusy(true, dryRun ? "正在检查审阅计划" : "正在保存审阅计划");
  setStatus("#review-status", dryRun ? "正在执行完整零写入检查……" : "正在原子写入追加式审阅历史……");
  try {
    const params = exactQuery({ dry_run: dryRun ? "true" : "false" });
    const response = await fetch(
      `/industry-analysis/api/session-revisions/${encodeURIComponent(route.sessionRevisionId)}/reviews?${params.toString()}`,
      {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: signature,
      },
    );
    const result = await readJson(response);
    renderReviewPreview(result);
    if (dryRun) {
      lastCheckedPayload = signature;
      setStatus("#review-status", "检查通过。没有写入；当前完整表单可保存。", "success");
      setBusy(false, "审阅检查通过");
      document.querySelector("#review-save-button").disabled = false;
      return;
    }
    setStatus("#review-status", "审阅计划已保存，正在打开精确结果页。", "success");
    if (!result.result_path) throw new Error("写入成功但未返回精确结果链接，请从研究历史重新打开。 ");
    window.location.assign(result.result_path);
  } catch (error) {
    let guidance = " 已保留当前页面中的全部选择和文字。";
    if (error.status === 409) {
      guidance += " 请在确认无未保存内容后，从研究历史重新打开最新精确修订。";
    } else if (!error.status || error.status >= 500) {
      guidance += " 页面不会自动重试；请先从研究历史检查是否已经写入。";
    }
    setStatus("#review-status", `${error.message}${guidance}`, "error");
    setBusy(false, "审阅处理失败");
  }
}

async function loadReviewView() {
  const params = exactQuery();
  const response = await fetch(
    `/industry-analysis/api/session-revisions/${encodeURIComponent(route.sessionRevisionId)}/review-view?${params.toString()}`,
    { headers: { Accept: "application/json" } },
  );
  const view = await readJson(response);
  renderReview(view);
  return view;
}

async function loadSourceOptions() {
  const params = exactQuery();
  const response = await fetch(
    `/industry-analysis/api/session-revisions/${encodeURIComponent(route.sessionRevisionId)}/candidate-source-options?${params.toString()}`,
    { headers: { Accept: "application/json" } },
  );
  sourceOptions = await readJson(response);
  renderResearchSummary(sourceOptions);
  renderSeeds(sourceOptions.company_seeds);
  renderMapPools(sourceOptions.maps);
  document.querySelector("#prepare-panel").hidden = sourceOptions.workflow_state !== "draft";
  document.querySelector("#build-panel").hidden = !sourceOptions.build_allowed;
  if (!sourceOptions.is_exact_latest_revision) {
    throw new Error("当前链接不是该研究的最新精确修订，只允许读取。请从研究历史重新打开。 ");
  }
}

async function initialize() {
  if (!route || !boundary.cutoff || !boundary.recordedAtUtc) {
    document.querySelector("#page-state").textContent = "精确链接无效";
    setStatus("#universe-status", "缺少精确 session、revision 或双时间边界。请从研究历史重新打开。", "error");
    return;
  }
  document.querySelector("#prepare-button").addEventListener("click", prepareScope);
  document.querySelector("#candidate-check-button").addEventListener("click", () => buildCandidates(true));
  document.querySelector("#candidate-build-button").addEventListener("click", () => buildCandidates(false));
  document.querySelector("#review-check-button").addEventListener("click", () => submitReview(true));
  document.querySelector("#review-save-button").addEventListener("click", () => submitReview(false));
  try {
    await loadSourceOptions();
    const universe = await loadUniverse();
    if (universe && universe.candidate_count > 0) {
      document.querySelector("#prepare-panel").hidden = true;
      document.querySelector("#build-panel").hidden = true;
      await loadReviewView();
    }
    document.querySelector("#page-state").textContent = "本地精确数据可用";
    document.querySelector("#page-state").classList.add("is-ready");
  } catch (error) {
    document.querySelector("#page-state").textContent = "精确候选审阅不可用";
    document.querySelector("#page-state").classList.add("is-unavailable");
    setStatus("#universe-status", error.message || "候选审阅页面初始化失败。", "error");
  }
}

initialize();
