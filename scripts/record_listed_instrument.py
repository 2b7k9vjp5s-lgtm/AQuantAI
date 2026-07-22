"""Record one explicit listed-instrument revision from local JSON."""

from scripts.canonical_price_cli import run


def main(argv: list[str] | None = None) -> int:
    return run("record_listed_instrument", "Record an explicit listed-instrument revision.", argv)


if __name__ == "__main__":
    raise SystemExit(main())
