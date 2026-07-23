"use strict";

function phase1cValue(rows, prefix) {
  const row = rows.find((item) => item.textContent.startsWith(prefix));
  return row ? row.textContent.slice(prefix.length).trim() : null;
}

function phase1dPath(kind, sessionId, revisionId, cutoff, recordedAt) {
  const query = new URLSearchParams({
    as_of_cutoff: cutoff,
    as_of_recorded_at_utc: recordedAt,
  });
  return `/industry-analysis/sessions/${sessionId}/revisions/${revisionId}/${kind}?${query.toString()}`;
}

function currentHistoryBoundary(fallbackCutoff, fallbackRecordedAt) {
  const cutoffInput = document.querySelector("#as-of-cutoff");
  const recordedInput = document.querySelector("#as-of-recorded-at");
  const cutoff = cutoffInput && cutoffInput.value ? cutoffInput.value : fallbackCutoff;
  let recordedAt = fallbackRecordedAt;
  if (recordedInput && recordedInput.value) {
    const parsed = new Date(recordedInput.value);
    if (!Number.isNaN(parsed.valueOf())) recordedAt = parsed.toISOString();
  }
  return { cutoff, recordedAt };
}

function updateCandidatePlaceholder() {
  const button = document.querySelector(".preview-panel .button-disabled");
  if (!button || button.dataset.phase1cUpdated) return;
  button.dataset.phase1cUpdated = "true";
  button.textContent = "保存研究主题后进入候选公司池";
}

function removeObsoletePlaceholder(side) {
  Array.from(side.querySelectorAll("small")).forEach((item) => {
    if (item.textContent.includes("将在后续切片开放")) item.remove();
  });
}

function enhanceHistoryCards() {
  document.querySelectorAll(".history-card").forEach((card) => {
    if (card.querySelector("[data-phase1d-link]")) return;
    const technical = Array.from(card.querySelectorAll(".technical-grid span"));
    const sessionId = phase1cValue(technical, "Session ID:");
    const revisionId = phase1cValue(technical, "Revision ID:");
    const side = card.querySelector(".history-side");
    const cutoffText = side && side.querySelector("strong")
      ? side.querySelector("strong").textContent.replace(/^信息截止\s*/, "").trim()
      : null;
    const recorded = Array.from(side ? side.querySelectorAll("small") : [])
      .map((item) => item.textContent)
      .find((value) => value.startsWith("记录于 "));
    const recordedAt = recorded ? recorded.replace(/^记录于\s*/, "").trim() : null;
    if (!sessionId || !revisionId || !cutoffText || !recordedAt || !side) return;

    const workflow = card.querySelector(".history-meta .meta-chip");
    const isResult = workflow && workflow.textContent.trim() === "审阅计划已就绪";
    const boundary = currentHistoryBoundary(cutoffText, recordedAt);
    const existing = side.querySelector("[data-phase1c-link]");
    if (existing) existing.remove();
    removeObsoletePlaceholder(side);

    const link = document.createElement("a");
    link.className = `button ${isResult ? "button-primary" : "button-secondary"} history-action`;
    link.dataset.phase1dLink = "true";
    link.href = phase1dPath(
      isResult ? "result" : "review",
      sessionId,
      revisionId,
      boundary.cutoff,
      boundary.recordedAt,
    );
    link.textContent = isResult ? "查看审阅结果" : "准备或继续候选审阅";
    side.appendChild(link);
  });
}

function enhanceSaveSuccess() {
  const panel = document.querySelector("#scope-success");
  if (!panel || panel.hidden || panel.querySelector("[data-phase1d-link]")) return;
  const technical = Array.from(panel.querySelectorAll(".technical-grid span"));
  const sessionId = phase1cValue(technical, "Session ID:");
  const revisionId = phase1cValue(technical, "Revision ID:");
  const recordedAt = phase1cValue(technical, "Recorded UTC:");
  const continueEdit = Array.from(panel.querySelectorAll("a"))
    .find((item) => item.textContent.includes("继续编辑"));
  if (!sessionId || !revisionId || !recordedAt || !continueEdit) return;
  const editQuery = new URL(continueEdit.href, window.location.origin).searchParams;
  const cutoff = editQuery.get("as_of_cutoff");
  if (!cutoff) return;
  let actions = panel.querySelector(".button-row");
  if (!actions) {
    actions = document.createElement("div");
    actions.className = "button-row";
    panel.appendChild(actions);
  }
  const oldLink = actions.querySelector("[data-phase1c-link]");
  if (oldLink) oldLink.remove();
  const link = document.createElement("a");
  link.className = "button button-primary";
  link.dataset.phase1dLink = "true";
  link.href = phase1dPath("review", sessionId, revisionId, cutoff, recordedAt);
  link.textContent = "准备或查看候选公司池";
  actions.appendChild(link);
}

function enhancePhase1DSurfaces() {
  updateCandidatePlaceholder();
  enhanceHistoryCards();
  enhanceSaveSuccess();
}

const phase1dObserver = new MutationObserver(enhancePhase1DSurfaces);
phase1dObserver.observe(document.body, { childList: true, subtree: true, attributes: true });
enhancePhase1DSurfaces();
