# Development Guide

## Python Version

Use Python 3.12.

## Dependency Management

Dependencies are managed in `pyproject.toml`.

Install runtime and development dependencies with:

```bash
pip install -e ".[dev]"
```

## Branch Rules

- `main`: stable branch
- `dev`: development branch
- `feature/*`: feature branches
- `fix/*`: fix branches

## Commit Message Rules

Use concise conventional-style commit messages.

Examples:

- `chore: initialize project structure`
- `feat: add akshare data provider`
- `fix: handle missing financial data`
- `docs: update roadmap`
- `test: add factor calculation tests`

## Testing Rules

- Use `pytest`.
- Add or update tests for behavior changes.
- Keep Phase 0 tests limited to application boot and health checks.
- Keep integration tests local and fixture-based.
- Do not add network, broker, trading, or production deployment requirements to tests.

## v0.1 Release Readiness Checks

Before opening or updating a v0.1 release-readiness pull request, run:

```bash
python -m pytest
python -m scripts.demo_research_flow
```

The checks must remain local and fixture-based. They must not require live data, LLM credentials, broker credentials, trading access, external paid services, or production deployment.

## Configuration Management

- Use environment variables for local configuration.
- Keep secrets out of Git.
- Use `.env.example` as the public template.

## Environment Variables

Required placeholders:

- `DATABASE_URL`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `APP_ENV`

## Pull Request Flow

1. Create work from `dev` or a `feature/*` branch.
2. Keep the sprint scope aligned with the current roadmap phase.
3. Run tests before opening a pull request.
4. Open a pull request after each completed sprint.
5. In the pull request description, include completed work, test results, and unfinished items.
6. Wait for ChatGPT review before moving to the next phase.
7. Address required review changes before moving to the next phase.

## GitHub Review Issue Flow

GitHub is the single source of truth for task synchronization.

Before each sprint, Codex must read:

- Latest GitHub Review Issue
- `docs/roadmap.md`
- `docs/architecture.md`
- `docs/development.md`
- Relevant domain docs such as `docs/factors.md`, `docs/backtesting.md`, `docs/ml.md`, `docs/agent.md`, and `docs/dashboard.md`

After ChatGPT reviews a sprint, review feedback should be synchronized to GitHub in this priority order:

1. GitHub Issue
2. Pull Request review comment
3. `docs/review.md`

Review Issue titles should use:

```text
Sprint N Review & Next Tasks
```

Each Review Issue should include:

- Current review scope
- Review conclusion
- Issues found
- Architecture risks
- Required fixes
- Next phase tasks
- Codex execution requirements
- Completion standards
