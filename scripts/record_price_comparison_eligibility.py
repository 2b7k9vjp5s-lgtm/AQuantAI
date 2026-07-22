"""Record one comparison-eligibility revision from local JSON."""

from scripts.canonical_price_cli import run


def main(argv: list[str] | None = None) -> int:
    return run("record_eligibility", "Record a price comparison-eligibility revision.", argv)


if __name__ == "__main__":
    raise SystemExit(main())
