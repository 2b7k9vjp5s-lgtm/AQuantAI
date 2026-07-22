"""Local bounded JSON runner for Industry Thesis proposal review v1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from backend.database import build_engine, build_session_factory
from industry_alpha.industry_thesis_review import IndustryThesisProposalReviewService
from industry_alpha.industry_thesis_rules import IndustryThesisError

MAX_INPUT_BYTES = 1_048_576


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review exact Industry Thesis candidates and preview an acceptance plan."
    )
    parser.add_argument("--input", required=True, type=Path, help="Local UTF-8 JSON input file")
    parser.add_argument("--dry-run", action="store_true", help="Validate without database writes")
    args = parser.parse_args(argv)
    engine = None
    try:
        raw = _load(args.input)
        engine = build_engine()
        service = IndustryThesisProposalReviewService(build_session_factory(engine))
        result = service.review_candidates(raw, dry_run=args.dry_run)
        print(
            json.dumps(
                {"status": "ok", "result": result},
                ensure_ascii=True,
                sort_keys=True,
                allow_nan=False,
            )
        )
        return 0
    except IndustryThesisError as exc:
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
                        "code": "industry_thesis_command_failed",
                        "message": "Local industry-thesis review failed. Verify input and database configuration.",
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


def _load(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) > MAX_INPUT_BYTES:
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "input file exceeds the 1 MiB limit",
        )
    value = json.loads(data.decode("utf-8"))
    if not isinstance(value, dict):
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "input must be a JSON object",
        )
    return value
