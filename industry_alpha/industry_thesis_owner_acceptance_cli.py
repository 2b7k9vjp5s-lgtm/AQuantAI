"""Local JSON-only runner for Industry Thesis owner acceptance and exact reads."""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from backend.database import build_engine, build_session_factory
from industry_alpha.industry_thesis_owner_acceptance import (
    IndustryThesisOwnerAcceptanceService,
)
from industry_alpha.industry_thesis_owner_acceptance_query import (
    IndustryThesisAcceptedOutputQueryService,
)
from industry_alpha.industry_thesis_rules import IndustryThesisError

MAX_INPUT_BYTES = 1_048_576
_ACTIONS = ("preview", "commit", "output", "result", "readiness")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or commit exact Industry Thesis owner acceptance, "
            "or read one exact accepted output."
        )
    )
    parser.add_argument("--action", required=True, choices=_ACTIONS)
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Local UTF-8 JSON input file",
    )
    args = parser.parse_args(argv)
    engine = None
    try:
        raw = _load(args.input)
        engine = build_engine()
        session_factory = build_session_factory(engine)
        if args.action == "preview":
            result = IndustryThesisOwnerAcceptanceService(session_factory).preview(raw)
        elif args.action == "commit":
            result = IndustryThesisOwnerAcceptanceService(session_factory).commit(raw)
        else:
            output_id, cutoff, recorded = _read_selector(raw)
            with session_factory() as session:
                query = IndustryThesisAcceptedOutputQueryService(session)
                if args.action == "output":
                    result = query.get_output(
                        output_id,
                        as_of_cutoff=cutoff,
                        as_of_recorded_at_utc=recorded,
                    )
                elif args.action == "result":
                    result = query.get_result(
                        output_id,
                        as_of_cutoff=cutoff,
                        as_of_recorded_at_utc=recorded,
                    )
                else:
                    result = query.get_readiness(
                        output_id,
                        as_of_cutoff=cutoff,
                        as_of_recorded_at_utc=recorded,
                    )
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
                {
                    "status": "error",
                    "error": {
                        "code": exc.code,
                        "message": str(exc),
                    },
                },
                ensure_ascii=True,
                sort_keys=True,
                allow_nan=False,
            )
        )
        return 2
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        RuntimeError,
        SQLAlchemyError,
        TypeError,
        ValueError,
    ):
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": {
                        "code": "industry_thesis_owner_acceptance_command_failed",
                        "message": (
                            "Local owner-acceptance command failed. "
                            "Verify exact identifiers, as-of boundaries, input, "
                            "and database migration state."
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


def _read_selector(raw: dict) -> tuple[UUID, date, datetime]:
    if set(raw) != {
        "output_link_revision_id",
        "as_of_cutoff",
        "as_of_recorded_at_utc",
    }:
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "exact reads require only output_link_revision_id and both as-of boundaries",
        )
    return (
        UUID(str(raw["output_link_revision_id"])),
        date.fromisoformat(str(raw["as_of_cutoff"])),
        datetime.fromisoformat(str(raw["as_of_recorded_at_utc"])),
    )
