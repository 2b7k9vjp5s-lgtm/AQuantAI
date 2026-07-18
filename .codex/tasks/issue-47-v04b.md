# Issue #47 — v0.4B Acceptance Handoff

## Task identity

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#47 [v0.4B] Benchmark index persistence and Market Cockpit context`
- Pull request: `#48 [v0.4B] Add benchmark index context`
- Branch: `feat/v04b-benchmark-index-context`
- Exact accepted implementation head: `11ea7d771442ea85408bbd68015ee7da8e934d8e`
- Passing GitHub Actions run: `29641613898`
- Accepting COMMENT review: `4728360480`
- Project version remains `0.2.0`

Read `.codex/WORKFLOW.md`, this file, Issue #47, PR #48, and accepting review `4728360480` before acting.

## Acceptance status

The v0.4B implementation is accepted for Ready-for-Review handoff. No code blocker remains.

Accepted behavior includes:

- dedicated benchmark-index persistence and Alembic `20260718_0003`;
- separate equity and benchmark complete-snapshot series, explicit selectors, one physical run, and no stitching;
- one bounded AKShare `index_zh_a_hist` endpoint with explicit network authorization and no fallback;
- selected-equity persisted open-session calendar as the only benchmark expected-session reference;
- exact consecutive 2/20/60/21-session benchmark windows with bounded deterministic diagnostics;
- explicit requested/available/aligned code counts, sorted missing codes, and separate session/cutoff alignment;
- effective benchmark session derived only from eligible per-code latest sessions;
- JSON `null` in context and provenance when no requested benchmark code is eligible;
- provider-attributed, non-official, selected-code, read-only wording;
- unchanged equity-only v0.4A and Dashboard behavior;
- offline/no-network tests and fixture demos.

The accepted implementation head passed GitHub Actions run `29641613898`, including `Run tests` and `Run local fixture demo`. The PR records `213 passed, 9 skipped` for the full PostgreSQL suite and successful focused, migration, Alembic, demo, no-network, compile and diff checks.

## Authorized actions

Perform only this acceptance handoff:

1. Fetch current remote state without rewriting history.
2. Confirm exact accepted head `11ea7d771442ea85408bbd68015ee7da8e934d8e` is an ancestor of the branch Head.
3. Confirm every commit after the accepted head is an authorized task/status synchronization commit only. There must be no code, test, migration, dependency, provider, documentation or product change after the accepted head.
4. Confirm the latest Head CI is successful. If it is pending, stop and report; do not mark Ready yet. If it fails, stop and report; do not repair or rerun unless separately authorized.
5. Mark PR #48 Ready for Review.
6. Add a concise PR #48 comment recording:
   - accepted implementation head;
   - accepting review ID;
   - accepted implementation CI run;
   - latest task-only Head and successful CI run;
   - PR changed from Draft to Ready;
   - no merge was performed.
7. Add a concise Issue #47 comment with the same Ready-handoff record.
8. Stop for explicit project-owner merge authorization.

## Prohibited actions

Do not:

- modify application code, tests, migrations, dependencies, provider logic, docs or page assets;
- amend, rebase, squash, force-push or rewrite any reviewed commit;
- merge or close PR #48;
- close Issue #47;
- create a release or tag;
- change version `0.2.0`;
- start v0.5 or any later stage;
- add sectors, style, valuation, crowding, relative performance, signals, recommendations, LLM execution, authentication, deployment, brokers, orders or trading;
- modify, close, rebase or merge PR #38.

If ancestry, post-acceptance diff or latest CI cannot be proven clean, keep PR #48 Draft and stop with the exact discrepancy. Do not improvise a fix.
