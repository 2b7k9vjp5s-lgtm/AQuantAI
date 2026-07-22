"""Record one canonical price-series contract revision from local JSON."""

from scripts.canonical_price_cli import run


def main(argv: list[str] | None = None) -> int:
    return run("record_series", "Record a canonical price-series contract revision.", argv)


if __name__ == "__main__":
    raise SystemExit(main())
