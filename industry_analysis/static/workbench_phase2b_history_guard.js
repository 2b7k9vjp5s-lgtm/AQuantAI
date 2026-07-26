"use strict";

(() => {
  if (window.location.pathname !== "/industry-analysis") return;
  const delegatedFetch = window.fetch.bind(window);
  const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

  function text(tag, value, className) {
    const node = document.createElement(tag);
    node.textContent = value;
    if (className) node.className = className;
    return node;
  }

  function exactAcceptedContinuation(item) {
    if (!item || item.workflow_state !== "accepted_outputs_linked") return null;
    const sessionId = String(item.session_id || "");
    const revisionId = String(item.visible_latest_revision_id || "");
    const cutoff = String(item.information_cutoff_date || "");
    const recorded = String(item.recorded_at_utc || "");
    if (!UUID_PATTERN.test(sessionId) || !UUID_PATTERN.test(revisionId)) return null;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(cutoff)) return null;
    const recordedDate = new Date(recorded);
    if (!recorded || Number.isNaN(recordedDate.valueOf())) return null;
    const query = new URLSearchParams({
      as_of_cutoff: cutoff,
      as_of_recorded_at_utc: recorded,
    });
    return {
      kind: "accepted_result",
      label: "查看已接受成果",
      path:
        `/industry-analysis/sessions/${encodeURIComponent(sessionId)}/revisions/`
        + `${encodeURIComponent(revisionId)}/accepted-result?${query}`,
      reason_code: "exact_accepted_outputs_linked",
    };
  }

  function renderExactHistoryActions(payload) {
    if (!payload || !Array.isArray(payload.sessions)) return;
    const cards = Array.from(document.querySelectorAll(".history-card"));
    payload.sessions.forEach((item, index) => {
      const card = cards[index];
      const side = card && card.querySelector(".history-side");
      if (!card || !side) return;

      side.querySelectorAll(".history-action, [data-phase1d-link]").forEach((node) => node.remove());
      Array.from(side.querySelectorAll("small")).forEach((node) => {
        if (node.textContent.includes("将在后续切片开放")) node.remove();
      });

      const continuation = exactAcceptedContinuation(item)
        || window.AQuantAIPhase2B.safeContinuation(item.continuation);
      if (continuation && continuation.path) {
        const link = text("a", continuation.label, "button button-secondary history-action");
        link.href = continuation.path;
        link.dataset.phase1dLink = "true";
        link.dataset.phase2bExactContinuation = "true";
        if (continuation.kind === "accepted_result") {
          link.dataset.ownerContextV2AcceptedResult = "true";
        }
        side.append(link);
        return;
      }

      const unavailable = text(
        "small",
        "当前精确记录不可继续；不会跳到其他记录。",
      );
      unavailable.dataset.phase1dLink = "true";
      unavailable.dataset.phase2bExactContinuation = "true";
      side.append(unavailable);
    });
  }

  window.fetch = async (...args) => {
    const input = args[0];
    const requestUrl = typeof input === "string" ? input : input.url;
    const response = await delegatedFetch(...args);
    const parsed = new URL(requestUrl, window.location.origin);
    if (parsed.pathname !== "/industry-analysis/api/sessions") return response;

    let payload = null;
    try {
      payload = await response.clone().json();
    } catch (_error) {
      payload = null;
    }
    if (response.ok) {
      window.setTimeout(() => renderExactHistoryActions(payload), 0);
    }
    return response;
  };
})();
