"use strict";

function phase1cValue(rows, prefix) {
  const row = rows.find((item) => item.textContent.startsWith(prefix));
  return row ? row.textContent.slice(prefix.length).trim() : null;
}

function phase1cReviewPath(sessionId, revisionId, cutoff, recordedAt) {
  const query = new URLSearchParams({
    as_of_cutoff: cutoff,
    as_of_recorded_at_utc: recordedAt,
  });
  return `/industry-analysis/sessions/${sessionId}/revisions/${revisionId}/review?${query.toString()}`;
}

function enhanceHistoryCards() {
  document.querySelectorAll(".history-card").forEach((card) => {
    if (card.querySelector("[data-phase1c-link]")) return;
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
    const link = document.createElement("a");
    link.className = "button button-secondary history-action";
    link.dataset.phase1cLink = "true";
    link.href = phase1cReviewPath(sessionId, revisionId, cutoffText, recordedAt);
    link.textContent = "候选公司池";
    side.appendChild(link);
  });
}

function enhanceSaveSuccess() {
  const panel = document.querySelector("#scope-success");
  if (!panel || panel.hidden || panel.querySelector("[data-phase1c-link]")) return;
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
  const link = document.createElement("a");
  link.className = "button button-primary";
  link.dataset.phase1cLink = "true";
  link.href = phase1cReviewPath(sessionId, revisionId, cutoff, recordedAt);
  link.textContent = "准备或查看候选公司池";
  actions.appendChild(link);
}

function enhancePhase1CSurfaces() {
  enhanceHistoryCards();
  enhanceSaveSuccess();
}

const phase1cObserver = new MutationObserver(enhancePhase1CSurfaces);
phase1cObserver.observe(document.body, { childList: true, subtree: true, attributes: true });
enhancePhase1CSurfaces();
