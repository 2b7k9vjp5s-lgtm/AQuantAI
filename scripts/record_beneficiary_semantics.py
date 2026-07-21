"""Record one typed beneficiary semantic revision from explicit local JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from backend.database import build_engine, build_session_factory
from industry_alpha.beneficiary_semantics_commands import (
    BeneficiarySemanticCommandService,
)
from industry_alpha.errors import EvidenceLedgerError

MAX_INPUT_BYTES = 1_000_000


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record one append-only typed beneficiary semantic profile revision."
    )
    parser.add_argument("--input", required=True, type=Path, help="Local UTF-8 JSON file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate exact frozen inputs without writing database rows",
    )
    return parser


def _load(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds the 1,000,000-byte local limit")
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("input must contain one JSON object")
    return parsed


def _emit(payload: dict[str, Any], *, stream: Any = sys.stdout) -> None:
    print(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, allow_nan=False),
        file=stream,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = _load(args.input)
        engine = build_engine()
        try:
            service = BeneficiarySemanticCommandService(build_session_factory(engine))
            result = service.validate(payload) if args.dry_run else service.record(payload)
        finally:
            engine.dispose()
    except EvidenceLedgerError as exc:
        _emit(
            {"status": "error", "error": "semantic_validation_failed", "detail": str(exc)},
            stream=sys.stderr,
        )
        return 3
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        _emit(
            {"status": "error", "error": "invalid_input", "detail": str(exc)},
            stream=sys.stderr,
        )
        return 2
    except (RuntimeError, SQLAlchemyError):
        _emit(
            {
                "status": "error",
                "error": "database_unavailable",
                "detail": "Verify DATABASE_URL and run Alembic migrations.",
            },
            stream=sys.stderr,
        )
        return 4
    _emit({"status": "ok", "result": result})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
