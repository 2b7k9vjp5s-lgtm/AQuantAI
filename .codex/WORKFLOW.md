# Codex Repository Workflow

This file defines the standing execution rules for Codex work in AQuantAI.

## Authority order

1. The linked GitHub Issue is the authoritative source for product scope, acceptance criteria, exclusions, and status.
2. The matching file under `.codex/tasks/` is the executable task snapshot for the current implementation or review cycle.
3. The active Draft PR contains the implementation and validation record.
4. A chat message only starts execution; it does not override GitHub scope.

If the Issue, task file, branch state, or PR instructions conflict, stop without changing code and report the conflict in the Issue and PR.

## Start protocol

Before editing:

1. Fetch `origin` and inspect the Issue, task file, Draft PR, latest review, and latest CI result.
2. Confirm the repository, branch, base commit, and required ancestor SHA from the task file.
3. Confirm there are no unexpected commits after the reviewed code head. Task-synchronization commits that only change `.codex/` are allowed when the task file explicitly identifies them.
4. Keep the existing branch and Draft PR unless the task file explicitly requires a new branch.
5. Do not modify unrelated branches or pull requests, including PR #38.

## Implementation rules

- Preserve the local-first, personal-use, research-only and non-advisory product boundary.
- Keep deterministic calculations outside LLM ownership.
- Do not add broker connectivity, real orders, trading buttons, automated trading, or investment recommendations.
- Do not access external networks during imports, FastAPI startup, tests, CI, fixture demos, or ordinary page use.
- Never put credentials, tokens, connection strings, or secrets in source, logs, fixtures, Issues, PRs, or task files.
- Use explicit selectors, cutoff dates, provenance, missing-data behavior, and fail-closed semantics where required by the Issue.
- Do not silently broaden scope or begin a later roadmap phase.

## Validation and reporting

1. Run every command listed in the task file.
2. Record exact pass/skip/warning counts and any environment limitations.
3. Update the Draft PR body and linked Issue with:
   - base and head SHA;
   - architecture and data-contract decisions;
   - changed files;
   - exact validation results;
   - demonstration output;
   - known limitations and exclusions.
4. Keep the PR Draft unless the task file explicitly authorizes Ready status.
5. Stop after synchronization and wait for ChatGPT review.

## Prohibited completion actions

Unless the project owner explicitly authorizes them in chat and the authorization is synchronized to GitHub:

- do not merge a PR;
- do not close the implementation Issue;
- do not create a release or tag;
- do not change the project version;
- do not start the next roadmap phase;
- do not rebase or force-push reviewed history.
