# Issue #49 — v0.4C Acceptance Handoff

## Task identity

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#49 [v0.4C] Sector market data foundation and descriptive rotation context`
- Pull request: `#50 [v0.4C] Add sector market context`
- Branch: `feat/v04c-sector-market-context`
- Required product ancestor: v0.4B squash merge `50147ecd7b796167d52a04e2ecc774010b8956b8`
- Original task sync: `9eb00d830737f7c4f622b3d9bf295a4ab8de89eb`
- Initial implementation: `6c9969a8d5570f67dbcef660747d9417bf672c79`
- Audit task sync: `b7a1fbd48d1a8c13ad9d2f91ada43eba0922cb36`
- Accepted implementation Head: `9e7fcf175b342910d6959f9ffe81bf07da2f66b5`
- Accepted implementation CI: `29644708323`
- Original blocking COMMENT review: `4728479274`
- Accepting COMMENT review: `4728531164`
- Project version remains `0.2.0`

Read `.codex/WORKFLOW.md`, this task, Issue #49, PR #50, review `4728479274`, accepting review `4728531164`, and the current PR body before taking any action.

## Accepted state

The implementation at `9e7fcf175b342910d6959f9ffe81bf07da2f66b5` is accepted for Ready-for-review handoff.

Accepted behavior includes:

- separate sector definition and daily persistence in migration `20260718_0004`;
- stable Eastmoney `BK` identifiers, exact selected scope, and no display-name/provider fallback;
- one reviewed taxonomy endpoint and one bounded daily-history endpoint;
- separate canonical sector series and one physical successful snapshot with no stitching;
- exact equity-calendar latest/5-session/20-session return, SMA20, volatility, and drawdown windows;
- bounded missing/invalid/duplicate/future diagnostics and no filling or shortened windows;
- deterministic selected-scope cross-section denominators and rankings;
- explicit coverage, session, cutoff, and overall alignment;
- nullable effective sector session when no requested code is eligible;
- optional read-only Market Cockpit API/page integration;
- fixed 19-field provider metadata allowlist with unknown/missing/nested rejection and canonical consistency checks;
- exact sector AKShare `1.18.64` runtime gate, distinct from the unchanged generic equity/benchmark range;
- canonical sector compatibility `aquantai.akshare-sector-endpoints.v1.18.64`;
- offline fixture/injected behavior, PostgreSQL tests, and prior equity/benchmark compatibility.

Do not edit application code, tests, migrations, documentation, dependencies, Docker/Compose, CI, or version files during this handoff. The only permitted branch commit before Ready is this task-file synchronization commit.

## Required verification

1. Fetch the latest remote branch and verify the accepted implementation Head `9e7fcf175b342910d6959f9ffe81bf07da2f66b5` is an ancestor of the current Head.
2. Compare the accepted implementation Head to the current Head. The only changed path must be `.codex/tasks/issue-49-v04c.md`.
3. Verify Actions run `29644708323` for the accepted implementation completed successfully.
4. Verify the latest Actions run for the task-only handoff Head completes successfully, including both tests and the local fixture demo.
5. Reconfirm PR #50 is open, Draft, mergeable, and unmerged before the transition.
6. Reconfirm Issue #49 remains open.
7. Reconfirm PR #38 remains open, Draft, and untouched.
8. Reconfirm no release, tag, version change, v0.5 work, or unrelated branch change occurred.

If any verification fails, keep PR #50 Draft, record the exact mismatch on PR #50 and Issue #49, and stop for ChatGPT review. Do not attempt an unrelated repair.

## Ready-for-review transition

After every verification passes:

1. Mark PR #50 Ready for review.
2. Update the PR body status section to distinguish:
   - accepted implementation Head `9e7fcf175b342910d6959f9ffe81bf07da2f66b5` and CI `29644708323`;
   - latest task-only handoff Head and its successful CI run.
3. Add a concise PR #50 comment recording:
   - accepting review `4728531164`;
   - accepted implementation Head and CI;
   - task-only handoff Head and CI;
   - comparison proving only `.codex/tasks/issue-49-v04c.md` changed after acceptance;
   - Ready/open/mergeable/unmerged state;
   - explicit stop for owner merge authorization.
4. Add the same bounded acceptance record to Issue #49.
5. Stop. Do not merge.

## Prohibited actions

- Do not merge PR #50.
- Do not close Issue #49.
- Do not create a release or tag.
- Do not change project version `0.2.0`.
- Do not begin v0.5 or create its implementation branch.
- Do not modify PR #38.
- Do not amend, rebase, force-push, or rewrite the accepted implementation history.
- Do not add any application, test, migration, documentation, dependency, Docker, CI, or version change.

The next product action requires explicit owner authorization to merge PR #50 and close Issue #49.