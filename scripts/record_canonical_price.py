"""Record one canonical price revision from an exact local source row."""

from scripts.canonical_price_cli import run


def main(argv: list[str] | None = None) -> int:
    return run("record_price", "Record a canonical price revision.", argv)


if __name__ == "__main__":
    raise SystemExit(main())
