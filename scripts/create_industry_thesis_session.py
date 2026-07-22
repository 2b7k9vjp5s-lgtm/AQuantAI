"""Create one explicit offline industry-thesis session."""

from industry_alpha.industry_thesis_cli import run


def main(argv: list[str] | None = None) -> int:
    return run(
        "create_session",
        "Create one explicit offline industry-thesis session.",
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
