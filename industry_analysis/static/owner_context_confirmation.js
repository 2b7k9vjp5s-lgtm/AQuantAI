"use strict";

(function installOwnerContextConfirmation() {
  const form = document.querySelector("#acceptance-form");
  const membersPanel = form && form.querySelector("section");
  const technical = document.querySelector("#acceptance-technical");
  if (!form || !membersPanel || !technical) return;

  function node(tag, value, className) {
    const element = document.createElement(tag);
    if (value !== undefined && value !== null) element.textContent = String(value);
    if (className) element.className = className;
    return element;
  }

  const panel = node("section", null, "panel");
  panel.setAttribute("aria-labelledby", "owner-context-title");
  panel.id = "owner-context-panel";

  const heading = node("div", null, "panel-heading");
  const headingCopy = node("div");
  const title = node("h2", "确认研究案例与产业地图");
  title.id = "owner-context-title";
  headingCopy.append(
    title,
    node(
      "p",
      "本次接受只能绑定页面读取到的唯一精确 Research Case、Industry Map 和地图修订；不能在提交时更换或按名称猜测。",
    ),
  );
  heading.append(headingCopy);

  const identity = node("div", null, "identity-box");
  identity.append(
    node("strong", "正在读取精确 owner context"),
    node("p", "尚未完成案例和地图校验。", "muted-copy"),
  );
  identity.id = "owner-context-summary";

  const confirmation = document.createElement("label");
  confirmation.className = "checkbox-row";
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.id = "owner-context-confirm";
  checkbox.disabled = true;
  checkbox.setAttribute(
    "aria-describedby",
    "owner-context-confirm-copy",
  );
  const confirmationCopy = node(
    "span",
    "我确认使用上述精确研究案例、产业地图和地图修订，不在成果接受阶段更换 owner context。",
  );
  confirmationCopy.id = "owner-context-confirm-copy";
  confirmation.append(checkbox, confirmationCopy);

  panel.append(heading, identity, confirmation);
  form.insertBefore(panel, membersPanel);

  function showBlocking(message) {
    const summary = document.querySelector("#error-summary");
    const list = document.querySelector("#error-list");
    if (summary && list) {
      list.replaceChildren(node("li", message));
      summary.hidden = false;
      summary.focus();
    }
    const status = document.querySelector("#acceptance-status");
    if (status) {
      status.textContent = "请先明确确认精确研究案例与产业地图。";
      status.className = "status-message is-error";
    }
  }

  function renderContext() {
    let payload;
    try {
      payload = JSON.parse(technical.textContent || "");
    } catch (_error) {
      return;
    }
    const researchCase = payload && payload.research_case;
    const industryMap = payload && payload.industry_map;
    if (
      !researchCase ||
      !researchCase.id ||
      !industryMap ||
      !industryMap.id ||
      !industryMap.revision_id
    ) {
      checkbox.disabled = true;
      identity.className = "blocking-box";
      identity.replaceChildren(
        node("strong", "精确 owner context 不完整"),
        node(
          "p",
          "页面没有获得可验证的 Research Case、Industry Map 或地图修订；不能生成接受预览。",
        ),
      );
      return;
    }
    checkbox.disabled = false;
    identity.className = "identity-box";
    identity.replaceChildren(
      node("strong", industryMap.title || "精确产业地图"),
      node(
        "p",
        `${researchCase.case_key || "本地研究案例"} · ${industryMap.map_key || "本地产业地图"} · 第 ${industryMap.revision_number || "?"} 版`,
      ),
      node("p", industryMap.scope || "未提供地图范围说明", "muted-copy"),
    );
  }

  const observer = new MutationObserver(renderContext);
  observer.observe(technical, {
    childList: true,
    characterData: true,
    subtree: true,
  });
  renderContext();

  form.addEventListener(
    "submit",
    (event) => {
      if (checkbox.disabled || !checkbox.checked) {
        event.preventDefault();
        event.stopImmediatePropagation();
        showBlocking(
          checkbox.disabled
            ? "精确研究案例或产业地图不可用，不能生成接受预览。"
            : "请明确确认页面展示的精确研究案例、产业地图和地图修订。",
        );
      }
    },
    true,
  );
})();
