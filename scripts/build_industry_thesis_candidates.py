"""Build deterministic offline industry-thesis candidate proposals."""

from industry_alpha.industry_thesis_cli import run


def main(argv: list[str] | None = None) -> int:
    return run(
        "build_candidates",
        "Build deterministic offline industry-thesis candidate proposals.",
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
