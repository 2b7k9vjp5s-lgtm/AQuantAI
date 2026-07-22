"""Record one explicit Investment Candidate component revision."""

from industry_alpha.investment_candidate_cli import run


def main(argv: list[str] | None = None) -> int:
    return run(
        "record_component",
        "Record one explicit Investment Candidate component revision.",
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
