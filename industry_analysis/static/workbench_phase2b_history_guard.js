"use strict";

(() => {
  if (window.location.pathname !== "/industry-analysis") return;
  const delegatedFetch = window.fetch.bind(window);

  function text(tag, value, className) {
    const node = document.createElement(tag);
    node.textContent = value;
    if (className) node.className = className;
    return node;
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

      const continuation = window.AQuantAIPhase2B.safeContinuation(item.continuation);
      if (continuation && continuation.path) {
        const link = text("a", continuation.label, "button button-secondary history-action");
        link.href = continuation.path;
        link.dataset.phase1dLink = "true";
        link.dataset.phase2bExactContinuation = "true";
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
