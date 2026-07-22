"""Record one deterministic normalized expectation-gap revision."""

from industry_alpha.normalized_valuation_cli import run


def main(argv: list[str] | None = None) -> int:
    return run(
        "record_expectation_gap",
        "Record one deterministic normalized expectation-gap revision.",
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
