(() => {
  "use strict";
  const fileInput = document.querySelector("#pdf-file");
  const button = document.querySelector("#import-button");
  const status = document.querySelector("#status");
  const detail = document.querySelector("#import-detail");
  const pages = document.querySelector("#pages");
  const pagesMore = document.querySelector("#pages-more");
  const reviewButton = document.querySelector("#review-button");
  const previewButton = document.querySelector("#preview-button");
  const acceptButton = document.querySelector("#accept-button");
  const selectionStatus = document.querySelector("#selection-status");
  const acceptanceResult = document.querySelector("#acceptance-result");
  let csrf = "";
  let importedState = null;
  let selectedSpan = null;
  let acceptanceState = null;
  let nextAfterPage = null;

  const safe = (value) => String(value ?? "—");
  const setDetail = (data) => {
    const entries = [
      ["状态", data.admission_state],
      ["内容指纹", data.content_sha256],
      ["页数", data.page_count],
      ["提取合同", data.extractor_contract_version],
    ];
    detail.replaceChildren(...entries.map(([label, value]) => {
      const box = document.createElement("div");
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = label;
      dd.textContent = safe(value);
      box.append(dt, dd);
      return box;
    }));
  };

  const loadPages = async (contentId, afterPage = 0) => {
    const response = await fetch(`/api/document-contents/${contentId}/pages?after_page=${afterPage}&limit=30`);
    if (!response.ok) throw new Error("逐页文本读取失败");
    const data = await response.json();
    const rendered = data.pages.map((page) => {
      const article = document.createElement("article");
      const heading = document.createElement("h3");
      const text = document.createElement("pre");
      heading.textContent = `第 ${page.page_number} 页`;
      text.textContent = page.extracted_text || "（本页没有可用的内嵌文本）";
      text.addEventListener("mouseup", () => {
        const selected = window.getSelection();
        if (!selected || selected.rangeCount !== 1 || selected.isCollapsed) return;
        const range = selected.getRangeAt(0);
        if (!text.contains(range.commonAncestorContainer)) return;
        const prefix = range.cloneRange();
        prefix.selectNodeContents(text);
        prefix.setEnd(range.startContainer, range.startOffset);
        const quote = range.toString();
        const encoder = new TextEncoder();
        const start = encoder.encode(prefix.toString()).length;
        selectedSpan = {page_number: page.page_number, start_utf8_byte: start,
          end_utf8_byte: start + encoder.encode(quote).length, quote_text: quote};
        selectionStatus.textContent = `已选择第 ${page.page_number} 页原文：${quote}`;
        reviewButton.disabled = false;
      });
      article.append(heading, text);
      return article;
    });
    if (afterPage === 0) pages.replaceChildren(...rendered);
    else pages.append(...rendered);
    nextAfterPage = data.next_after_page;
    pagesMore.hidden = nextAfterPage === null;
  };

  pagesMore.addEventListener("click", async () => {
    if (!importedState?.content_id || nextAfterPage === null) return;
    pagesMore.disabled = true;
    try { await loadPages(importedState.content_id, nextAfterPage); }
    catch (error) { status.textContent = `后续页面读取失败：${error.message}`; }
    finally { pagesMore.disabled = false; }
  });

  fileInput.addEventListener("change", () => {
    button.disabled = !fileInput.files.length;
    status.textContent = fileInput.files.length ? `已选择：${fileInput.files[0].name}` : "尚未选择文件。";
  });

  button.addEventListener("click", async () => {
    const file = fileInput.files[0];
    if (!file) return;
    button.disabled = true;
    importedState = null;
    selectedSpan = null;
    acceptanceState = null;
    nextAfterPage = null;
    pagesMore.hidden = true;
    reviewButton.disabled = true;
    previewButton.disabled = true;
    acceptButton.disabled = true;
    selectionStatus.textContent = "尚未选择逐页原文。";
    acceptanceResult.textContent = "等待审核快照。";
    status.textContent = "正在本地校验并提取内嵌文本……";
    try {
      if (!csrf) {
        const tokenResponse = await fetch("/api/document-import/csrf");
        csrf = (await tokenResponse.json()).csrf_token;
      }
      const url = `/api/document-imports?original_filename=${encodeURIComponent(file.name)}`;
      const response = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {"Content-Type": file.type || "application/pdf", "X-AQuantAI-CSRF": csrf},
        body: file,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "导入失败");
      importedState = data;
      const detailResponse = await fetch(`/api/document-imports/${data.import_attempt_id}`);
      const imported = await detailResponse.json();
      setDetail(imported);
      status.textContent = data.admission_state === "rejected" ? `已拒绝：${data.admission_reason}` : "导入完成。请逐页核对文本。";
      if (data.content_id) await loadPages(data.content_id);
    } catch (error) {
      status.textContent = `导入未完成：${error.message}`;
    } finally {
      button.disabled = false;
    }
  });

  const field = (id) => document.querySelector(`#${id}`).value;
  const postJson = async (url, body) => {
    const response = await fetch(url, {method: "POST", credentials: "same-origin",
      headers: {"Content-Type": "application/json", "X-AQuantAI-CSRF": csrf},
      body: JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "操作失败");
    return data;
  };
  const quoteSha = async (quote) => {
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(quote));
    return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, "0")).join("");
  };

  reviewButton.addEventListener("click", async () => {
    reviewButton.disabled = true;
    try {
      const recorded = new Date().toISOString();
      const review = await postJson("/api/document-reviews", {import_attempt_id: importedState.import_attempt_id,
        target_research_case_id: field("case-id"), created_at_utc: recorded});
      const base = `/api/document-reviews/${review.review_session_id}`;
      const documentCandidate = await postJson(`${base}/candidates`, {candidate_kind: "document_identity",
        payload: {identity_namespace: "user_defined_document", identity_key: field("document-key"),
          document_title: field("document-title"), publisher_or_author: field("publisher"),
          document_date: field("document-date"), document_kind: "announcement"}, recorded_at_utc: recorded});
      const subject = await postJson(`${base}/candidates`, {candidate_kind: "company_identity",
        payload: {subject_kind: "not_company_specific", display_label: field("subject-label")}, recorded_at_utc: recorded});
      const fact = await postJson(`${base}/candidates`, {candidate_kind: "fact", payload: {}, ...selectedSpan,
        quote_sha256: await quoteSha(selectedSpan.quote_text), statement: field("fact-statement"), recorded_at_utc: recorded});
      const revision = await postJson(`${base}/revisions`, {expected_previous_revision_number: 0, review_state: "draft",
        source_kind: field("source-kind"), evidence_grade: field("evidence-grade"),
        document_identity_candidate_id: documentCandidate.candidate_id, subject_candidate_id: subject.candidate_id,
        information_date: field("information-date"), recorded_at_utc: recorded, decisions: [
          {candidate_id: documentCandidate.candidate_id, decision: "selected"},
          {candidate_id: subject.candidate_id, decision: "selected"},
          {candidate_id: fact.candidate_id, decision: "selected", claim_status: field("claim-status"),
            evidence_relation: field("evidence-relation")}]});
      const exact = await (await fetch(`${base}?review_revision_id=${revision.review_revision_id}`)).json();
      const decision = exact.revisions[0].candidate_decisions.find((row) => row.candidate_id === fact.candidate_id);
      acceptanceState = {reviewId: review.review_session_id, body: {source_review_revision_id: revision.review_revision_id,
        expected_source_review_revision_number: revision.revision_number,
        expected_source_review_fingerprint_sha256: revision.review_fingerprint_sha256,
        expected_session_latest_revision_number: revision.revision_number, target_research_case_id: field("case-id"),
        selected_candidate_ids: [fact.candidate_id], selected_decision_fingerprints: [decision.decision_fingerprint_sha256],
        recorded_at_utc: new Date().toISOString(), acceptance_plan_fingerprint_sha256: "0".repeat(64)}};
      previewButton.disabled = false;
      acceptanceResult.textContent = "审核快照已保存；请先执行零写入预览。";
    } catch (error) {
      acceptanceResult.textContent = `审核未完成：${error.message}`;
      reviewButton.disabled = false;
    }
  });

  previewButton.addEventListener("click", async () => {
    try {
      const preview = await postJson(`/api/document-reviews/${acceptanceState.reviewId}/acceptance-preview`, acceptanceState.body);
      acceptanceState.body.acceptance_plan_fingerprint_sha256 = preview.acceptance_plan_fingerprint_sha256;
      acceptanceResult.textContent = JSON.stringify(preview, null, 2);
      acceptButton.disabled = false;
    } catch (error) { acceptanceResult.textContent = `预览失败：${error.message}`; }
  });

  acceptButton.addEventListener("click", async () => {
    try {
      const result = await postJson(`/api/document-reviews/${acceptanceState.reviewId}/acceptance-commit`, acceptanceState.body);
      const query = new URLSearchParams({information_cutoff_date: field("information-date"),
        recorded_at_utc: acceptanceState.body.recorded_at_utc});
      const reopenResponse = await fetch(`/api/document-acceptances/${result.receipt_id}?${query}`);
      const reopened = await reopenResponse.json();
      if (!reopenResponse.ok) throw new Error(reopened.detail || "精确回执重开失败");
      acceptanceResult.textContent = JSON.stringify({commit: result, exact_reopen: reopened}, null, 2);
      acceptButton.disabled = true;
    } catch (error) { acceptanceResult.textContent = `接受失败：${error.message}`; }
  });
})();
