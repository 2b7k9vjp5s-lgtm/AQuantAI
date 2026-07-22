"""Append one explicit offline industry-thesis session revision."""

from industry_alpha.industry_thesis_cli import run


def main(argv: list[str] | None = None) -> int:
    return run(
        "revise_session",
        "Append one explicit offline industry-thesis session revision.",
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
