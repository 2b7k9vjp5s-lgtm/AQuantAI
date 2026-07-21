# Issue #160 — Guarded AI Research Assistance v1

## Authority

- Work type: application implementation.
- Required base: `dfbaa119d90eb9d4f034f54eb16500ef11ed631c`.
- Architecture authority: `docs/guarded_ai_research_assistance_preflight.md`.
- Linked Issue: #160.
- Roadmap: #137.

## Objective

Implement one company-scoped, user-invoked Guarded AI draft flow over an explicitly selected persisted `company_research_id` and optional explicit cutoff.

The user must preview the deterministic manifest locally, inspect provider/model/data-use information, explicitly confirm one remote transmission, and receive one ephemeral validated D3 draft. No persistent state may be created.

## Exact scope

Authorized files only:

1. `.codex/tasks/issue-160-guarded-ai-research-assistance.md`
2. `industry_alpha/guarded_ai_contracts.py`
3. `industry_alpha/guarded_ai_manifest.py`
4. `industry_alpha/guarded_ai_adapter.py`
5. `industry_alpha/guarded_ai_service.py`
6. `backend/api/company_research.py`
7. `company_research/static/company_research.html`
8. `company_research/static/company_research.js`
9. `tests/test_guarded_ai_manifest.py`
10. `tests/test_guarded_ai_adapter.py`
11. `tests/test_guarded_ai_service.py`
12. `tests/test_company_research_api.py`

No other file may change.

## Implementation contract

- Reuse `CompanyResearchWorkspaceQueryService.get_workspace()` as the only database read source.
- Preserve its fixed 14 SQL statement behavior.
- Build the AI manifest from the returned contract without database access.
- Canonically serialize and SHA-256 fingerprint deterministic content.
- Exclude generated/request time from the content fingerprint.
- Preview performs no network access.
- Generation requires `confirm_remote_transmission=true` and exact expected fingerprint.
- Rebuild and compare the fingerprint before invoking the adapter.
- Use one explicit, disabled-by-default, HTTPS OpenAI-compatible profile.
- Standard-library HTTPS only; no dependency changes.
- One remote request, timeout 60 seconds, no retry, no fallback, no streaming/tools/retrieval.
- Validate strict output shape, request fingerprint, allowed sections and known manifest item IDs.
- Reject malformed output, unknown citations, recommendation/target-price language and fingerprint mismatch.
- All output remains ephemeral D3 draft assistance.

## Limits

- maximum canonical input: 60,000 UTF-8 characters;
- maximum model output: 2,000 tokens;
- automatic retries: zero;
- one request per explicit user action;
- no silent truncation.

## Validation

Run:

```text
pytest -q tests/test_guarded_ai_manifest.py tests/test_guarded_ai_adapter.py tests/test_guarded_ai_service.py tests/test_company_research_api.py
pytest -q
python scripts/run_local_fixture_demo.py
```

Record exact results, base/head SHA and changed-file inventory in the Draft PR and Issue.

## Stop conditions

Stop without expanding scope if another file, schema/migration/dependency, model database access, multiple provider profiles, live AI call in tests/CI, silent fallback/truncation, accepted-state mutation, ranking, recommendation or price-judgment semantics become necessary.

## Completion gate

Keep the implementation PR Draft/Open/unmerged. Stop after author review and independent fixed-head review. Do not merge or close Issue #160 without explicit owner authorization.
