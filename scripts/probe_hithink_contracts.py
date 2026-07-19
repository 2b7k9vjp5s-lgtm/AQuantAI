"""CLI for the credential-safe Hithink contract acceptance probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable, Sequence

from datasource.hithink.probe import (
    ProbeConfigurationError,
    ProbeOptions,
    ProbeTransport,
    UrllibProbeTransport,
    report_json,
    run_contract_probe,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--allow-network", action="store_true")
    mode.add_argument("--offline-contract", action="store_true")
    parser.add_argument("--representative", action="append", required=True)
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--manifest-evidence", type=Path)
    parser.add_argument("--rights-evidence", type=Path)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    env_getter: Callable[[str], str | None] | None = None,
    transport_factory: Callable[[], ProbeTransport] = UrllibProbeTransport,
) -> int:
    args = _parser().parse_args(argv)
    options = ProbeOptions(
        mode="live" if args.allow_network else "offline",
        representatives=tuple(args.representative),
        start_date=args.start_date,
        end_date=args.end_date,
        manifest_path=args.manifest_evidence,
        rights_path=args.rights_evidence,
    )
    kwargs = {"transport_factory": transport_factory}
    if env_getter is not None:
        kwargs["env_getter"] = env_getter
    try:
        report = run_contract_probe(options, **kwargs)
    except ProbeConfigurationError as error:
        print(
            json.dumps(
                {"error": {"category": error.category, "message": str(error)}},
                sort_keys=True,
            )
        )
        return 2
    print(report_json(report))
    return 0 if report["overall_status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
