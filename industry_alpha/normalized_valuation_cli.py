"""Local bounded JSON command runner for normalized valuation Slice 5."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.exc import SQLAlchemyError

from backend.database import build_engine, build_session_factory
from industry_alpha.normalized_financial_rules import NormalizedMetricError
from industry_alpha.normalized_valuation_service import NormalizedValuationCommandService

MAX_INPUT_BYTES = 1_048_576


def run(method_name: str, description: str, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--input", required=True, type=Path, help="Local UTF-8 JSON input file")
    parser.add_argument("--dry-run", action="store_true", help="Validate without database writes")
    args = parser.parse_args(argv)
    engine = None
    try:
        raw = _load(args.input)
        engine = build_engine()
        service = NormalizedValuationCommandService(build_session_factory(engine))
        method: Callable[..., dict[str, Any]] = getattr(service, method_name)
        result = method(raw, dry_run=args.dry_run)
        print(
            json.dumps(
                {"status": "ok", "result": result},
                ensure_ascii=True,
                sort_keys=True,
                allow_nan=False,
            )
        )
        return 0
    except NormalizedMetricError as exc:
        print(
            json.dumps(
                {"status": "error", "error": {"code": exc.code, "message": str(exc)}},
                ensure_ascii=True,
                sort_keys=True,
                allow_nan=False,
            )
        )
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError, SQLAlchemyError):
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": {
                        "code": "normalized_metric_command_failed",
                        "message": (
                            "Local normalized-metric command failed. Verify input and database "
                            "configuration."
                        ),
                    },
                },
                ensure_ascii=True,
                sort_keys=True,
                allow_nan=False,
            )
        )
        return 2
    finally:
        if engine is not None:
            engine.dispose()


def _load(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) > MAX_INPUT_BYTES:
        raise NormalizedMetricError(
            "normalized_metric_input_invalid", "input file exceeds the 1 MiB limit"
        )
    value = json.loads(data.decode("utf-8"))
    if not isinstance(value, dict):
        raise NormalizedMetricError(
            "normalized_metric_input_invalid", "input must be a JSON object"
        )
    return value
