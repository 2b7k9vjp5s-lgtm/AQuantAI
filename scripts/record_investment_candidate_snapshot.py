"""Record one complete-universe Investment Candidate snapshot revision."""

from industry_alpha.investment_candidate_cli import run


def main(argv: list[str] | None = None) -> int:
    return run(
        "record_snapshot",
        "Record one complete-universe Investment Candidate snapshot revision.",
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
