"""Run a deterministic persisted liquidity-context demonstration offline."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from sqlalchemy import create_engine

from backend.database.models import Base
from scripts.demo_market_cockpit import build_persisted_market_cockpit_demo


def build_liquidity_context_demo() -> dict[str, Any]:
    """Persist deterministic fixtures in temporary SQLite and return both cutoff views."""
    with TemporaryDirectory(prefix="aquantai-liquidity-") as directory:
        database_path = Path(directory) / "liquidity-demo.sqlite3"
        database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
        engine = create_engine(database_url)
        try:
            Base.metadata.create_all(engine)
        finally:
            engine.dispose()
        payload = build_persisted_market_cockpit_demo(database_url)
    return {
        "series_key": payload["series_key"],
        "current": payload["current"]["liquidity_context"],
        "historical": payload["historical"]["liquidity_context"],
        "read_only": True,
        "network_access": False,
        "temporary_database_removed": True,
    }


def main() -> None:
    print(json.dumps(build_liquidity_context_demo(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
