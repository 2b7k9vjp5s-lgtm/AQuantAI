"""Record one deterministic normalized valuation metric revision."""

from industry_alpha.normalized_valuation_cli import run


def main(argv: list[str] | None = None) -> int:
    return run(
        "record_metric",
        "Record one deterministic normalized valuation metric revision.",
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
