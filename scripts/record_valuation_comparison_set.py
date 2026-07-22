"""Record one frozen historical or peer valuation comparison revision."""

from industry_alpha.normalized_valuation_cli import run


def main(argv: list[str] | None = None) -> int:
    return run(
        "record_comparison_set",
        "Record one frozen historical or peer valuation comparison revision.",
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
