# Issue #47 — v0.4B Final Effective-Session Audit Fix

## Task identity

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#47 [v0.4B] Benchmark index persistence and Market Cockpit context`
- Draft PR: `#48 [v0.4B] Add benchmark index context`
- Branch: `feat/v04b-benchmark-index-context`
- Required base/task ancestor: `5420da2e28b52e9410ca1216c1b8feb7652978ce`
- Accepted foundation head: `6402762f1af6723b7a473a779edf9587598dcd91`
- First review task sync: `6bbb049e23980bb812055ec7264f27072beff262`
- Reviewed correctness head: `57062eeaf6f87d15cb696ed17b2fdbec2a43b410`
- Passing CI for reviewed correctness head: `29641216572`
- Current blocking COMMENT review: `4728341522`
- Project version remains `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #47, PR #48, review `4728341522`, `docs/benchmark_context.md`, `market_cockpit/benchmark_calculator.py`, `market_cockpit/benchmark_contracts.py`, `market_cockpit/service.py`, the benchmark page code, and this file before editing.

Keep PR #48 Draft. This is one bounded correctness/auditability fix. Do not redesign the accepted implementation.

## Accepted implementation that must not regress

The following are accepted:

- dedicated `benchmark_index_daily` persistence and Alembic `20260718_0003`;
- separate equity and benchmark complete-snapshot series;
- explicit benchmark selector, one physical successful run, no stitching or fallback;
- one bounded AKShare `index_zh_a_hist` endpoint with explicit network authorization;
- provider-attributed provenance and non-official/non-full-market wording;
- the selected equity snapshot's persisted `is_open=true` calendar as the only benchmark expected-session reference;
- exact consecutive 2/20/60/21-session windows;
- deterministic per-window required/present counts, ranges, missing/invalid lists and stable reasons;
- requested/available/aligned code counts, exact missing-code list, separate session and cutoff alignment states;
- optional benchmark context with unchanged equity-only v0.4A behavior;
- local read-only DOM-safe page and offline/no-network validation;
- no relative performance, alpha, beta, signals, recommendations, brokers, orders or trading.

## Remaining blocker

`calculate_benchmark_metrics()` correctly excludes benchmark rows outside the selected equity open-session sequence. But `MarketCockpitService._build_benchmark_context()` currently uses `persisted.effective_benchmark_session` when no per-code eligible latest session exists.

That persisted value is the maximum stored row date before repository bounds, not the maximum eligible session after expected-calendar filtering. If every requested code has rows only on a persisted closed/non-open date, the response can report:

- `available_code_count = 0`;
- every exact code in `missing_codes`;
- all per-code `latest_session = null`;
- session/overall status `partial`;
- but a non-null effective benchmark session copied from an excluded row.

Warnings, counts, status, provenance and metrics must not contradict one another.

## Required correction

1. Define the public effective benchmark session only from eligible per-code latest sessions after expected-calendar filtering.
2. If at least one requested code is eligible, use the deterministic maximum eligible latest session.
3. If no requested code is eligible, expose no effective benchmark session. Prefer `null` in both benchmark context and benchmark provenance.
4. Do not fall back to the maximum persisted row date.
5. Do not silently replace the field with `expected_session_end`, equity effective session, benchmark cutoff or another synthetic date.
6. A physical persisted maximum may remain internal. If exposed for debugging, it must use a separate explicit name and must not be described as an effective eligible session; avoid adding it unless necessary.
7. Keep `session_alignment_status = partial`, `alignment_status = partial`, zero available/aligned counts and the complete sorted missing-code list when no code is eligible.
8. Add one bounded warning stating that no requested benchmark code has an eligible row in the selected persisted open-session sequence.
9. Existing bounded outside-calendar warnings must remain deterministic and must not leak unbounded data.

## Contracts and serialization

Update only what is needed:

- make benchmark effective-session fields optional where the public response may legitimately have no eligible session;
- keep context and provenance values identical;
- ensure `to_dict()` serializes the unavailable value as JSON `null`;
- ensure API validation/error behavior remains unchanged;
- ensure the page renders the unavailable value neutrally, such as `Unavailable`, and never prints the excluded row date as effective;
- preserve additive/backward-compatible benchmark context behavior and unchanged equity-only payload semantics.

## Documentation

Update `docs/benchmark_context.md` to state:

- effective benchmark session means the maximum eligible per-code latest session after expected-calendar filtering;
- it is unavailable/null when no exact requested code has an eligible row;
- persisted rows excluded by the selected equity calendar cannot become an effective session;
- all-ineligible scope remains partial with zero available/aligned codes and all exact codes listed as missing.

Do not broaden documentation into later roadmap areas.

## Required regression tests

Add deterministic coverage that would fail at `57062eeaf6f87d15cb696ed17b2fdbec2a43b410`:

1. Build one valid exact benchmark snapshot in which every requested code has at least one persisted row, but every row falls outside the selected equity `is_open=true` sequence, for example on a persisted closed date within all request/cutoff bounds.
2. Exercise the service/API through the normal explicit equity and benchmark series selectors.
3. Assert:
   - HTTP response remains an intentional audited success unless an existing contract requires a non-success;
   - requested count equals the exact scope;
   - available and aligned counts are zero;
   - all exact requested codes are present in sorted `missing_codes`;
   - every per-code latest close/session is null;
   - every dependent metric is null with bounded diagnostics;
   - session and overall alignment are `partial`;
   - cutoff alignment follows the existing independent cutoff rule;
   - context and provenance effective benchmark session are null;
   - warnings state both outside-calendar exclusion and no eligible requested code;
   - API JSON contains `null`, not the excluded persisted date;
   - page rendering shows an unavailable value and remains DOM-safe.
4. Preserve all previously added gap/window/alignment tests.
5. Preserve migration, persistence, provider, CLI, Dashboard, v0.4A and no-network regressions.

## Required validation

Run and report exact results for:

1. `python -m pytest -q` with the PostgreSQL test URL;
2. focused benchmark calculation/alignment/API/page tests, including the all-ineligible case;
3. focused benchmark contract/persistence/provider/repository tests;
4. PostgreSQL benchmark and Market Cockpit current/as-of tests;
5. PostgreSQL persistence and migration suite;
6. clean Alembic `base -> 20260718_0003`;
7. `20260718_0003 -> 20260718_0002 -> 20260718_0003`;
8. `python -m alembic check`;
9. `python -m scripts.demo_research_flow`;
10. existing persisted equity current/historical demo;
11. benchmark current/historical demo;
12. offline benchmark dry run and repeated idempotent persistence;
13. `python -m compileall -q backend datasource market_cockpit scripts`;
14. import/startup/page/dry-run no-network regressions;
15. `git diff --check`.

Automated validation must remain offline. No migration, dependency, provider-endpoint or version change is expected.

## GitHub synchronization

After implementing and pushing:

1. Update PR #48 body with the new Head SHA, effective-session semantics, changed files and exact validation results.
2. Add a concise Issue #47 completion comment with the same record.
3. Keep PR #48 Draft.
4. Stop for ChatGPT re-review.

## Exclusions and stop conditions

Do not:

- merge PR #48;
- close Issue #47;
- create a release or tag;
- change project version `0.2.0`;
- rewrite, squash, rebase, amend or force-push reviewed commits;
- add a migration unless a separate schema defect is demonstrated and authorized;
- change the AKShare endpoint or add fallbacks;
- add sectors, style, valuation, crowding, relative performance, signals or recommendations;
- add schedulers, background/page-triggered collection or automatic refresh;
- begin v0.5 or any later phase;
- add LLM execution, authentication, deployment, brokers, orders or trading;
- modify, close, rebase or merge unrelated PR #38.

Stop and report instead of improvising if making the effective-session field nullable would break an accepted external contract that cannot be preserved additively.