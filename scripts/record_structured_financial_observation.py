"""Record one explicit structured financial observation revision."""

from industry_alpha.normalized_valuation_cli import run


def main(argv: list[str] | None = None) -> int:
    return run(
        "record_observation",
        "Record one explicit structured financial observation revision.",
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
