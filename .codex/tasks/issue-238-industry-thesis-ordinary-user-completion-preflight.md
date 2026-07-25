# Issue #238 Task Snapshot — Industry Thesis Ordinary-User Completion v1

## Authority

- Authoritative Architecture Preflight Issue: #238.
- Product Roadmap: #137.
- Accepted owner-acceptance architecture: Issue #234 / merged PR #235.
- Accepted owner-acceptance implementation: completed Issue #236 / merged PR #237.
- Accepted ordinary-user workbench foundation: #215/#216 and #217/#218.
- Today Market automatic-refresh architecture: #221 / merged PR #222.
- THS Stage C1 remains blocked by Issue #225.
- Project-owner authorization on 2026-07-25:

```text
批准，基于规划进去下一步开发
```

- Exact architecture base: `a6da9bc8483606a67b7ca5f1329e46232d5b47be`.
- Branch: `docs/industry-thesis-ordinary-user-completion-preflight`.
- Workflow authority: `.codex/WORKFLOW.md`.
- Risk tier: **Strict Architecture Preflight**.

## Phase boundary

This task is architecture-only.

Authorized files:

```text
.codex/tasks/issue-238-industry-thesis-ordinary-user-completion-preflight.md
docs/industry_thesis_ordinary_user_completion_preflight.md
```

No production code, API, browser UI, schema, migration, fixture, executable test, dependency, Provider, credential, network access, AI call, release, tag or version change is authorized.

## Objective

Define the smallest production-reachable ordinary-user slice that completes the accepted Industry Thesis workflow:

```text
reviewed_plan_ready
  -> 查看研究结果
  -> 检查并接受研究成果
  -> exact owner-binding review in ordinary Chinese
  -> deterministic dry-run preview
  -> explicit confirmation
  -> accepted_outputs_linked
  -> 查看已接受成果、完整成员和准备度
  -> exact history reopening
```

The architecture must reuse the accepted owner-acceptance core and make no accepted decision by hidden inference.

## Locked product meaning

1. The complete accepted result is the complete frozen member set for this accepted research result.
2. The supported candidate-pool handoff is a separate supported-only downstream handoff.
3. Draft and disputed accepted members remain visible.
4. Zero-supported acceptance is valid and creates no fake pool.
5. Readiness is an exact read of existing accepted owners and missing states; it creates no Company Research or Investment Candidate state.
6. Accepted research is not a recommendation, target price, expected return, position instruction or trading action.

## Required architecture decisions

### 1. Exact routes and state mapping

Define deterministic local routes for:

- exact acceptance preparation from one `reviewed_plan_ready` revision;
- exact preview;
- explicit commit;
- exact accepted-result read;
- exact readiness read;
- exact history reopening.

Every route and request must use response-owned exact IDs and both as-of boundaries. No latest fallback, fuzzy lookup or browser-local identity reconstruction.

### 2. Ordinary-language selectors over exact owners

For each selected reviewed candidate, define an ordinary-language representation of:

- exact company/instrument identity and `stock_basic` readiness;
- Stage 1 reuse/create/append operation;
- legacy beneficiary kind and assessment status;
- assertion/claim prerequisites;
- typed-semantics none/reuse/append operation;
- supported-handoff inclusion/exclusion and reason;
- missing and blocking states.

Selectors may expose only exact persisted compatible options or explicit owner payload fields already accepted by the core. Internal IDs remain progressive technical details.

No automatic mapping among reviewed exposure, legacy Stage 1 kind and typed semantics.

### 3. API/application adapter boundary

Define the minimum future local adapter for:

- one bounded prerequisite/selector response;
- deterministic preview;
- explicit commit with matching fingerprint and expected-latest values;
- exact accepted output/result/readiness response.

The adapter must reuse existing application services and must not duplicate owner validation or directly create ORM rows.

### 4. Preview and commit

Preview must disclose:

- complete frozen member ordering;
- owner reuse/create/append operations;
- semantic operations or explicit absence;
- supported handoff membership;
- zero-supported state;
- blocking and readiness gaps;
- cutoff and visible data date.

Commit occurs only after explicit confirmation and only with the exact preview fingerprint. Page load, navigation, preview and retry never commit automatically.

### 5. Conflict behavior

For stale expected-latest, moved owner boundaries, duplicate submit, conflicting replay and HTTP `409`:

- no silent retry or rebase;
- preserve selections, rationale and revision note in page memory;
- require explicit reload/re-preview;
- identical replay resolves to the same output;
- conflicting replay never overwrites the original accepted result.

### 6. Accepted-result presentation

Define first-render ordering:

1. concise accepted-state summary;
2. complete frozen member list;
3. supported-only handoff as a separate section;
4. readiness and missing/disputed/pending/failed states;
5. evidence and owner-operation details;
6. IDs, fingerprints, rule versions and chronology under technical details.

### 7. One primary action and accessibility

Define exactly one visually dominant action per tested page/state, including:

- `reviewed_plan_ready` -> `检查并接受研究成果`;
- commit-ready preview -> `确认接受研究成果`;
- `accepted_outputs_linked` -> `查看已接受成果`;
- blocked state -> one exact corrective action.

Use Chinese-first copy, keyboard navigation, explicit text states, focus management, error summaries, `aria-current` and non-color-only meaning.

### 8. Query and response budget

Define deterministic ceilings:

- no per-row HTTP request;
- no N+1 database access;
- one bounded acceptance-prerequisite response per page load;
- one preview request;
- one explicit commit request;
- one exact accepted-result response for first render.

Complete-universe meaning must not be lost through convenience pagination or first-record skipping.

### 9. Migration and persistence

Preferred architecture decision:

```text
schema migration = none
new persisted UI workflow state = none
browser-local accepted research identity = none
```

Temporary unsaved form state may remain in page memory only. If a new persistent field or owner is required, stop and return for project-owner review.

### 10. Security and locality

- no external origins or arbitrary redirects;
- no free-text path construction;
- server-side validation of exact IDs, fingerprints and boundaries;
- strict JSON write contracts with unknown-field rejection;
- no Provider, credential, network, AI or remote transmission path.

## Production-realistic offline golden path

Use one exact `reviewed_plan_ready` session with three selected companies:

- A reuses a supported Stage 1 revision and compatible semantic revision and enters supported handoff;
- B reuses/appends a draft or disputed Stage 1 revision, remains in complete result and is excluded from handoff;
- C produces/reuses a supported Stage 1 revision, enters handoff and retains readiness gaps.

The user reviews ordinary-language bindings, generates preview, explicitly confirms, receives one exact `accepted_outputs_linked` result and reopens all three in frozen order under both as-of boundaries.

No Company Research, Investment Candidate, recommendation, portfolio or trading state is automatically created.

Also define one valid zero-supported ordinary-user path.

## Primary blocked path

One selected candidate lacks an exact compatible `stock_basic` or Stage 1 assertion/claim binding.

Required behavior:

- identify the exact candidate and missing prerequisite;
- return no commit-ready fingerprint;
- expose one explicit corrective/review action;
- perform zero owner/session/output writes;
- preserve the reviewed plan;
- do not fill the gap from free text, name, ticker, Provider or AI inference.

## Future implementation validation contract

The architecture must require zero-network fixture-backed coverage for:

- route/state mapping and exact-ID construction;
- selector compatibility and no hidden inference;
- three-company golden path;
- zero-supported path;
- blocked missing-owner path;
- preview/commit fingerprint match;
- conflict and form preservation;
- identical/conflicting replay behavior;
- exact result/readiness rendering;
- dual-as-of negative visibility;
- graph-integrity failure presentation;
- one-primary-action and accessibility semantics;
- query ceilings and no N+1;
- no migration/new persistence;
- no Provider/network/credential/AI path;
- no recommendation, price target, expected return, portfolio or trading semantics.

## Locked exclusions

No production API/UI, Provider/THS/CNINFO/iFinD/Tushare/AKShare access, credentials, automatic refresh, scheduler, background worker, retry loop, notification, external network, AI call, new Industry Map facts, draft-graph promotion, fuzzy identity bridge, automatic legacy/typed classification mapping, automatic Company Research, automatic Investment Candidate snapshot, recommendation, target price, expected return, position sizing, research holdings, portfolio, broker, order, trading, release, tag or version change.

## Stop conditions

Stop and return for project-owner review if:

- the success path requires hidden inference;
- raw IDs must become mandatory primary inputs;
- selector options cannot come from exact persisted owners or explicit allowed payloads;
- a second workflow owner or new persistence is required;
- the adapter must duplicate validation or directly write ORM rows;
- a migration is required;
- exact reopening requires latest fallback;
- the scope expands into Today Market source activation, announcements, Follow/Track or Research Portfolio;
- any Provider, network, AI, recommendation, portfolio or trading behavior appears.

## Delivery gates

1. Keep one architecture branch from exact base `a6da9bc8483606a67b7ca5f1329e46232d5b47be`.
2. Change only the two authorized documentation files.
3. Open one Draft architecture PR linked to #238, #137, #234/#235, #236/#237 and #215–#218.
4. Run repository checks on one exact immutable HEAD.
5. Obtain a process-independent fixed-head architecture review containing exactly:

```text
AUTHORIZED INDUSTRY THESIS ORDINARY-USER COMPLETION PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

6. Resolve every review thread.
7. Await separate explicit project-owner authorization before merge.
8. Any new commit invalidates prior exact-head validation and review.

Architecture approval does not authorize production implementation, merge, Issue closure, release or the next roadmap phase.
