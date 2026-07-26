"use strict";

(function attachOwnerAcceptancePool(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.OwnerAcceptancePool = api;
  if (
    typeof window !== "undefined"
    && typeof document !== "undefined"
    && typeof state !== "undefined"
    && typeof renderPoolOptions === "function"
    && typeof renderPoolFields === "function"
    && typeof buildPoolOperation === "function"
    && typeof buildPayload === "function"
  ) {
    api.installBrowserBindings();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function poolFactory() {
  const MODE_NONE = "none_no_supported_members";
  const MODE_CREATE = "create_supported_handoff";
  const MODE_APPEND = "append_supported_handoff";
  const MODE_REUSE = "reuse_exact_supported_handoff";

  function canonicalRevisionIds(values) {
    return [...new Set((values || []).map((value) => String(value)))].sort();
  }

  function exactIdSetEqual(left, right) {
    const a = canonicalRevisionIds(left);
    const b = canonicalRevisionIds(right);
    return a.length === b.length && a.every((value, index) => value === b[index]);
  }

  function exactSupportedRevisionIds(selections) {
    const revisionIds = [];
    for (const item of selections || []) {
      if (item.assessment_status !== "supported") continue;
      if (
        item.stage1_operation !== "reuse_exact_beneficiary_revision"
        || !item.beneficiary_revision_id
      ) {
        return null;
      }
      revisionIds.push(item.beneficiary_revision_id);
    }
    return canonicalRevisionIds(revisionIds);
  }

  function eligibleReuseOptions(reuseOptions, supportedRevisionIds) {
    if (!Array.isArray(supportedRevisionIds) || supportedRevisionIds.length === 0) {
      return [];
    }
    return (reuseOptions || []).filter((option) => exactIdSetEqual(
      option.beneficiary_revision_ids || [],
      supportedRevisionIds,
    ));
  }

  function appendValue(option) {
    return `append:${option.candidate_pool_id}:${option.expected_latest_revision_id}`;
  }

  function reuseValue(option) {
    return `reuse:${option.candidate_pool_id}:${option.candidate_pool_revision_id}`;
  }

  function parseValue(value) {
    if (value === MODE_NONE || value === MODE_CREATE) return { mode: value };
    const [prefix, candidatePoolId, revisionId, extra] = String(value || "").split(":");
    if (extra !== undefined || !candidatePoolId || !revisionId) return null;
    if (prefix === "append") {
      return {
        mode: MODE_APPEND,
        candidate_pool_id: candidatePoolId,
        expected_latest_revision_id: revisionId,
      };
    }
    if (prefix === "reuse") {
      return {
        mode: MODE_REUSE,
        candidate_pool_id: candidatePoolId,
        candidate_pool_revision_id: revisionId,
      };
    }
    return null;
  }

  function resolveSelection(contract, value) {
    const parsed = parseValue(value);
    if (!parsed) return null;
    if (parsed.mode === MODE_NONE) return parsed;
    if (parsed.mode === MODE_CREATE) {
      const create = contract.create_contract || {};
      return {
        ...parsed,
        pool_key: create.pool_key,
        title: create.title_default || "",
        scope: create.scope_default || "",
      };
    }
    if (parsed.mode === MODE_APPEND) {
      const option = (contract.append_options || []).find((item) => (
        item.candidate_pool_id === parsed.candidate_pool_id
        && item.expected_latest_revision_id === parsed.expected_latest_revision_id
      ));
      return option ? { ...parsed, option, title: option.title, scope: option.scope } : null;
    }
    const option = (contract.reuse_options || []).find((item) => (
      item.candidate_pool_id === parsed.candidate_pool_id
      && item.candidate_pool_revision_id === parsed.candidate_pool_revision_id
    ));
    return option ? { ...parsed, option } : null;
  }

  function installBrowserBindings() {
    const originalBuildPayload = buildPayload;

    function pageSelections() {
      if (!state.view) return [];
      return state.view.members.map((member) => {
        const operation = selectedOperation(member);
        if (operation === OP_REUSE) {
          const reuse = selectedReuse(member);
          return {
            stage1_operation: operation,
            assessment_status: reuse ? reuse.assessment_status : null,
            beneficiary_revision_id: reuse ? reuse.beneficiary_revision_id : null,
          };
        }
        if ([OP_APPEND, OP_CREATE].includes(operation)) {
          const status = memberControl("data-status-for", member);
          return {
            stage1_operation: operation,
            assessment_status: status ? status.value : null,
            beneficiary_revision_id: null,
          };
        }
        return {
          stage1_operation: operation,
          assessment_status: null,
          beneficiary_revision_id: null,
        };
      });
    }

    renderPoolOptions = function renderExactPoolOptions() {
      if (!state.view) return;
      const select = document.querySelector("#pool-mode");
      const titleInput = document.querySelector("#pool-title-input");
      const scopeInput = document.querySelector("#pool-scope-input");
      const previousValue = select.value;
      const previousTitle = titleInput.value;
      const previousScope = scopeInput.value;
      const selections = pageSelections();
      const hasSupported = selections.some(
        (item) => item.assessment_status === "supported",
      );
      const contract = state.view.candidate_pool_operation_contract;
      select.replaceChildren();

      if (!hasSupported) {
        select.add(new Option("不创建后续研究池（没有 supported 成员）", MODE_NONE));
      } else {
        select.add(new Option("新建 supported 后续研究池", MODE_CREATE));
        const supportedRevisionIds = exactSupportedRevisionIds(selections);
        for (const option of eligibleReuseOptions(
          contract.reuse_options,
          supportedRevisionIds,
        )) {
          select.add(new Option(
            `复用精确候选池 ${option.title} · 第 ${option.revision_number} 版`,
            reuseValue(option),
          ));
        }
        for (const option of contract.append_options || []) {
          select.add(new Option(
            `追加到 ${option.title} · 第 ${option.revision_number} 版`,
            appendValue(option),
          ));
        }
      }

      const preserved = [...select.options].some(
        (option) => option.value === previousValue,
      );
      if (preserved) select.value = previousValue;
      renderPoolFields({
        preserveCurrent: preserved,
        previousTitle,
        previousScope,
      });
    };

    renderPoolFields = function renderExplicitPoolFields({
      preserveCurrent = false,
      previousTitle = null,
      previousScope = null,
    } = {}) {
      const select = document.querySelector("#pool-mode");
      const titleField = document.querySelector("#pool-title-field");
      const scopeField = document.querySelector("#pool-scope-field");
      const titleInput = document.querySelector("#pool-title-input");
      const scopeInput = document.querySelector("#pool-scope-input");
      const optionField = document.querySelector("#pool-option-field");
      const help = document.querySelector("#pool-help");
      const contract = state.view.candidate_pool_operation_contract;
      const selection = resolveSelection(contract, select.value);
      const editsMetadata = selection && [MODE_CREATE, MODE_APPEND].includes(selection.mode);

      optionField.hidden = true;
      titleField.hidden = !editsMetadata;
      scopeField.hidden = !editsMetadata;
      titleInput.required = Boolean(editsMetadata);
      scopeInput.required = Boolean(editsMetadata);
      if (editsMetadata) {
        if (preserveCurrent) {
          titleInput.value = previousTitle === null ? titleInput.value : previousTitle;
          scopeInput.value = previousScope === null ? scopeInput.value : previousScope;
        } else {
          titleInput.value = selection.title || "";
          scopeInput.value = selection.scope || "";
        }
      }

      if (!selection || selection.mode === MODE_NONE) {
        help.textContent = "完整成果仍保留 draft/disputed 成员，只是不创建后续研究池。";
      } else if (selection.mode === MODE_CREATE) {
        help.textContent = "只会写入最终 assessment_status 为 supported 的精确成员。";
      } else if (selection.mode === MODE_APPEND) {
        help.textContent = (
          `已从所选候选池第 ${selection.option.revision_number} 版精确预填标题和范围；`
          + "如修改，将作为新 Revision 的显式元数据写入。"
        );
      } else {
        help.textContent = (
          "仅当最终 supported Stage 1 Revision UUID 集合与该池冻结成员集合完全相等时显示；"
          + "复用不会写入新的候选池 Revision。"
        );
      }
    };

    buildPoolOperation = function buildExactPoolOperation() {
      const contract = state.view.candidate_pool_operation_contract;
      const selection = resolveSelection(
        contract,
        document.querySelector("#pool-mode").value,
      );
      if (!selection) return { mode: "invalid_candidate_pool_selection" };
      if (selection.mode === MODE_NONE) return { mode: MODE_NONE };
      if (selection.mode === MODE_REUSE) {
        return {
          mode: MODE_REUSE,
          candidate_pool_id: selection.candidate_pool_id,
          candidate_pool_revision_id: selection.candidate_pool_revision_id,
        };
      }
      const title = document.querySelector("#pool-title-input").value.trim();
      const scope = document.querySelector("#pool-scope-input").value.trim();
      if (selection.mode === MODE_CREATE) {
        return {
          mode: MODE_CREATE,
          pool_key: selection.pool_key,
          title,
          scope,
        };
      }
      return {
        mode: MODE_APPEND,
        candidate_pool_id: selection.candidate_pool_id,
        expected_latest_revision_id: selection.expected_latest_revision_id,
        title,
        scope,
      };
    };

    buildPayload = function buildPayloadWithExplicitPoolMetadata() {
      const payload = originalBuildPayload();
      if (!payload) return null;
      const pool = payload.candidate_pool_operation;
      if (
        [MODE_CREATE, MODE_APPEND].includes(pool.mode)
        && (!pool.title || !pool.scope)
      ) {
        showErrors(["新建或追加候选池时，必须明确确认候选池标题和范围。"]);
        return null;
      }
      return payload;
    };

    if (state.view) renderPoolOptions();
  }

  return {
    MODE_NONE,
    MODE_CREATE,
    MODE_APPEND,
    MODE_REUSE,
    canonicalRevisionIds,
    exactIdSetEqual,
    exactSupportedRevisionIds,
    eligibleReuseOptions,
    appendValue,
    reuseValue,
    parseValue,
    resolveSelection,
    installBrowserBindings,
  };
});
