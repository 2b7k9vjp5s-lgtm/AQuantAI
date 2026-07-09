"""Placeholder entrypoint for future data ingestion workflows."""

from datasource.akshare import AkshareDataProvider


def main() -> None:
    provider = AkshareDataProvider()
    print("AQuantAI Phase 1 data script placeholder")
    print("Planned actions: validate provider contracts, then add guarded ingestion in later phases.")
    print(f"Configured provider: {provider.source_name}")


if __name__ == "__main__":
    main()
