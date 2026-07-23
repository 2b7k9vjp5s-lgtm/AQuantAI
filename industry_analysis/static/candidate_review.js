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
let sourceOptions = null;
let busy = false;

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
  ["#prepare-button", "#candidate-check-button", "#candidate-build-button"].forEach((selector) => {
    const button = document.querySelector(selector);
    if (button) button.disabled = value;
  });
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

function renderUniverse(payload) {
  const empty = document.querySelector("#universe-empty");
  const wrap = document.querySelector("#universe-table-wrap");
  const rows = document.querySelector("#candidate-rows");
  const summary = document.querySelector("#universe-summary");
  rows.replaceChildren();
  empty.hidden = payload.candidate_count !== 0;
  wrap.hidden = payload.candidate_count === 0;
  summary.textContent = payload.candidate_count
    ? `完整显示 ${payload.candidate_count} 条精确候选路径；不同来源的同一公司不会合并。`
    : "当前精确修订尚未写入候选记录。";
  payload.candidates.forEach((candidate) => {
    const rationale = candidate.rationale || {};
    const uncertainty = candidate.uncertainty || {};
    const tr = document.createElement("tr");
    const company = document.createElement("td");
    company.append(node("strong", candidate.company_label_original));
    company.append(node("small", rationale.stock_code || "代码未单独显示"));
    const source = document.createElement("td");
    source.append(node("strong", sourceLabel(candidate)));
    source.append(node("small", candidate.source_kind));
    const identity = node("td", candidate.identity_state);
    const stage1 = node("td", rationale.stage1_beneficiary_kind || "不适用 / 待审阅");
    const path = node("td", candidate.benefit_path_text);
    const pending = document.createElement("td");
    pending.append(node("strong", `暴露：${candidate.proposed_exposure_type}`));
    pending.append(node("small", `置信度：${candidate.proposal_confidence}`));
    pending.append(node("small", `审阅：${candidate.review_state}`));
    const detail = document.createElement("td");
    const details = document.createElement("details");
    details.append(node("summary", "技术详情"));
    const pre = node("pre", JSON.stringify({
      candidate_id: candidate.candidate_id,
      candidate_revision_id: candidate.candidate_revision_id,
      candidate_key: candidate.candidate_key,
      source_reference: candidate.source_reference,
      rationale,
      uncertainty,
      recorded_at_utc: candidate.recorded_at_utc,
    }, null, 2), "json-block");
    details.append(pre);
    detail.append(details);
    tr.append(company, source, identity, stage1, path, pending, detail);
    rows.append(tr);
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
    throw new Error("当前链接不是该研究的最新精确修订，只允许读取，不允许构建候选。请返回研究历史。");
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
  try {
    await loadSourceOptions();
    await loadUniverse();
    document.querySelector("#page-state").textContent = "本地精确数据可用";
    document.querySelector("#page-state").classList.add("is-ready");
  } catch (error) {
    document.querySelector("#page-state").textContent = "精确候选来源不可用";
    document.querySelector("#page-state").classList.add("is-unavailable");
    setStatus("#universe-status", error.message || "候选页面初始化失败。", "error");
  }
}

initialize();
