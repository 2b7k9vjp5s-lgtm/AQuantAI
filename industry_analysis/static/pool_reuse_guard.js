"use strict";

(function installExactPoolReuseGuard() {
  const originalFetch = window.fetch.bind(window);
  let acceptanceView = null;
  let scheduled = false;

  function sorted(values) {
    return [...values].map(String).sort();
  }

  function equalMembers(left, right) {
    const a = sorted(left);
    const b = sorted(right);
    return a.length === b.length && a.every((value, index) => value === b[index]);
  }

  function currentCompatibility() {
    if (!acceptanceView || !Array.isArray(acceptanceView.members)) {
      return { eligible: false, allowedIndexes: [] };
    }
    const supportedRevisionIds = [];
    for (const member of acceptanceView.members) {
      const sequence = member.sequence;
      const operation = document.querySelector(`#stage1-operation-${sequence}`)?.value || "";
      if (!operation) return { eligible: false, allowedIndexes: [] };
      if (operation.startsWith("reuse:")) {
        const index = Number(operation.split(":")[1]);
        const option = member.stage1_reuse_options[index];
        if (!option) return { eligible: false, allowedIndexes: [] };
        if (option.assessment_status === "supported") {
          supportedRevisionIds.push(option.beneficiary_revision_id);
        }
        continue;
      }
      const status = document.querySelector(`#assessment-status-${sequence}`)?.value || "";
      if (!status) return { eligible: false, allowedIndexes: [] };
      if (status === "supported") {
        return { eligible: false, allowedIndexes: [] };
      }
    }
    if (!supportedRevisionIds.length) {
      return { eligible: false, allowedIndexes: [] };
    }
    const options =
      acceptanceView.candidate_pool_operation_contract?.reuse_options || [];
    const allowedIndexes = [];
    options.forEach((option, index) => {
      if (equalMembers(option.beneficiary_revision_ids || [], supportedRevisionIds)) {
        allowedIndexes.push(index);
      }
    });
    return { eligible: allowedIndexes.length > 0, allowedIndexes };
  }

  function refresh() {
    scheduled = false;
    const mode = document.querySelector("#pool-mode");
    if (!mode) return;
    const reuseMode = [...mode.options].find(
      (option) => option.value === "reuse_exact_supported_handoff",
    );
    if (!reuseMode) return;
    const compatibility = currentCompatibility();
    reuseMode.disabled = !compatibility.eligible;
    reuseMode.hidden = !compatibility.eligible;
    if (!compatibility.eligible && mode.value === reuseMode.value) {
      mode.value = "";
      mode.dispatchEvent(new Event("change", { bubbles: true }));
    }
    const poolOption = document.querySelector("#pool-option");
    if (poolOption && mode.value === reuseMode.value) {
      [...poolOption.options].forEach((option) => {
        if (option.value === "") return;
        const allowed = compatibility.allowedIndexes.includes(Number(option.value));
        option.disabled = !allowed;
        option.hidden = !allowed;
      });
      if (
        poolOption.value &&
        !compatibility.allowedIndexes.includes(Number(poolOption.value))
      ) {
        poolOption.value = "";
      }
    }
    const help = document.querySelector("#pool-help");
    if (help && !compatibility.eligible && mode.value !== reuseMode.value) {
      help.dataset.reuseGuard =
        "精确复用仅在 supported 成员全部复用正式修订且成员集合完全匹配时可用。";
    }
  }

  function scheduleRefresh() {
    if (scheduled) return;
    scheduled = true;
    queueMicrotask(refresh);
  }

  window.fetch = async (...args) => {
    const response = await originalFetch(...args);
    const target = String(args[0] || "");
    if (response.ok && target.includes("/owner-acceptance-view")) {
      response
        .clone()
        .json()
        .then((payload) => {
          acceptanceView = payload;
          scheduleRefresh();
        })
        .catch(() => {
          acceptanceView = null;
          scheduleRefresh();
        });
    }
    return response;
  };

  const form = document.querySelector("#acceptance-form");
  if (form) {
    form.addEventListener("change", scheduleRefresh, true);
    form.addEventListener("input", scheduleRefresh, true);
  }
  const observer = new MutationObserver(scheduleRefresh);
  observer.observe(document.body, { childList: true, subtree: true });
  scheduleRefresh();
})();
