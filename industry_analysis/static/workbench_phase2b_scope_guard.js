"use strict";

(() => {
  const form = document.querySelector("#scope-form");
  if (!form) return;

  const invalidate = () => {
    form.dispatchEvent(new Event("input", { bubbles: true }));
  };

  ["#selected-maps", "#selected-companies"].forEach((selector) => {
    const container = document.querySelector(selector);
    if (!container) return;
    new MutationObserver(invalidate).observe(container, {
      childList: true,
      subtree: true,
    });
  });
})();
