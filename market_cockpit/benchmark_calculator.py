"""Deterministic benchmark calculations on exact persisted open-session windows."""

from __future__ import annotations

from datetime import datetime
from math import isfinite, sqrt

import numpy as np
import pandas as pd

from market_cockpit.benchmark_contracts import (
    BenchmarkCodeMetrics,
    BenchmarkWindowDiagnostic,
)
from market_cockpit.benchmark_repository import PersistedBenchmarkSnapshot

MAX_DIAGNOSTIC_SESSIONS = 10


class BenchmarkCalculationError(ValueError):
    """Raised when persisted benchmark data violates the reviewed contract."""


def calculate_benchmark_metrics(
    snapshot: PersistedBenchmarkSnapshot,
    *,
    expected_sessions: list[str],
) -> tuple[list[BenchmarkCodeMetrics], list[str]]:
    """Calculate metrics only from exact consecutive persisted open sessions."""
    sessions = _validated_expected_sessions(expected_sessions)
    session_set = set(sessions)
    frame = snapshot.benchmark_index_daily.copy()
    frame["trade_date"] = frame["trade_date"].map(_compact_date)
    if frame.duplicated(["source", "index_code", "trade_date"]).any():
        raise BenchmarkCalculationError("Benchmark snapshot contains duplicate natural keys.")
    unexpected = sorted(set(frame["index_code"].astype(str)) - set(snapshot.index_codes))
    if unexpected:
        raise BenchmarkCalculationError(
            f"Benchmark snapshot contains unexpected codes: {unexpected}."
        )

    warnings: list[str] = []
    outside_calendar = frame.loc[~frame["trade_date"].isin(session_set)]
    if not outside_calendar.empty:
        labels = sorted(
            outside_calendar[["index_code", "trade_date"]]
            .astype(str)
            .agg(":".join, axis=1)
            .unique()
        )
        warnings.append(
            "Excluded benchmark rows outside the selected equity open-session sequence: "
            f"{labels[:MAX_DIAGNOSTIC_SESSIONS]}"
            + (f" (+{len(labels) - MAX_DIAGNOSTIC_SESSIONS} more)." if len(labels) > MAX_DIAGNOSTIC_SESSIONS else ".")
        )
    frame = frame.loc[frame["trade_date"].isin(session_set)].copy()
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")

    metrics: list[BenchmarkCodeMetrics] = []
    for code in sorted(snapshot.index_codes):
        code_frame = frame.loc[frame["index_code"].astype(str).eq(code)].sort_values(
            "trade_date"
        )
        close_by_session: dict[str, float] = {}
        invalid_sessions: set[str] = set()
        for row in code_frame[["trade_date", "close"]].to_dict(orient="records"):
            session = str(row["trade_date"])
            value = row["close"]
            if pd.isna(value) or not isfinite(float(value)) or float(value) <= 0:
                invalid_sessions.add(session)
            else:
                close_by_session[session] = float(value)

        valid_sessions = [session for session in sessions if session in close_by_session]
        latest_session = valid_sessions[-1] if valid_sessions else None
        latest_close = close_by_session.get(latest_session) if latest_session else None
        latest_window = _window_diagnostic(
            sessions, latest_session, close_by_session, invalid_sessions, 2
        )
        sma20_window = _window_diagnostic(
            sessions, latest_session, close_by_session, invalid_sessions, 20
        )
        sma60_window = _window_diagnostic(
            sessions, latest_session, close_by_session, invalid_sessions, 60
        )
        risk_window = _window_diagnostic(
            sessions, latest_session, close_by_session, invalid_sessions, 21
        )

        latest_return = None
        if latest_window.reason == "available":
            values = _window_values(sessions, latest_session, close_by_session, 2)
            latest_return = values[-1] / values[-2] - 1.0

        sma20 = None
        if sma20_window.reason == "available":
            sma20 = float(
                np.mean(_window_values(sessions, latest_session, close_by_session, 20))
            )

        sma60 = None
        if sma60_window.reason == "available":
            sma60 = float(
                np.mean(_window_values(sessions, latest_session, close_by_session, 60))
            )

        volatility = None
        drawdown = None
        if risk_window.reason == "available":
            values = np.asarray(
                _window_values(sessions, latest_session, close_by_session, 21),
                dtype=float,
            )
            returns = values[1:] / values[:-1] - 1.0
            volatility = float(returns.std(ddof=1) * sqrt(252))
            wealth = np.concatenate(([1.0], np.cumprod(1.0 + returns)))
            drawdown = float(
                np.min(wealth / np.maximum.accumulate(wealth) - 1.0)
            )

        code_warnings = _window_warnings(
            code,
            {
                "latest_return": latest_window,
                "sma20": sma20_window,
                "sma60": sma60_window,
                "volatility_drawdown_20": risk_window,
            },
        )
        if invalid_sessions:
            invalid = sorted(invalid_sessions)
            code_warnings.append(
                f"Benchmark {code} excluded invalid close sessions: "
                f"{invalid[:MAX_DIAGNOSTIC_SESSIONS]}"
                + (f" (+{len(invalid) - MAX_DIAGNOSTIC_SESSIONS} more)." if len(invalid) > MAX_DIAGNOSTIC_SESSIONS else ".")
            )
        metrics.append(
            BenchmarkCodeMetrics(
                index_code=code,
                latest_close=latest_close,
                latest_session=latest_session,
                latest_return=latest_return,
                sma20=sma20,
                above_sma20=(latest_close > sma20)
                if latest_close is not None and sma20 is not None
                else None,
                sma60=sma60,
                above_sma60=(latest_close > sma60)
                if latest_close is not None and sma60 is not None
                else None,
                realized_volatility_20=volatility,
                max_drawdown_20=drawdown,
                available_session_count=len(valid_sessions),
                latest_return_window=latest_window,
                sma20_window=sma20_window,
                sma60_window=sma60_window,
                risk_window=risk_window,
                warnings=tuple(code_warnings),
            )
        )
        warnings.extend(code_warnings)
    return metrics, warnings


def _validated_expected_sessions(values: list[str]) -> list[str]:
    if not isinstance(values, list) or not values:
        raise BenchmarkCalculationError(
            "Benchmark calculation requires a non-empty persisted equity open-session sequence."
        )
    sessions = [_compact_date(value) for value in values]
    if sessions != sorted(sessions) or len(sessions) != len(set(sessions)):
        raise BenchmarkCalculationError(
            "Persisted equity open-session sequence must be unique and strictly ordered."
        )
    return sessions


def _window_diagnostic(
    sessions: list[str],
    latest_session: str | None,
    close_by_session: dict[str, float],
    invalid_sessions: set[str],
    required: int,
) -> BenchmarkWindowDiagnostic:
    if latest_session is None:
        return BenchmarkWindowDiagnostic(
            required, 0, None, None, required, (), 0, (), "insufficient_history"
        )
    latest_index = sessions.index(latest_session)
    if latest_index + 1 < required:
        candidate = sessions[: latest_index + 1]
        present = sum(session in close_by_session for session in candidate)
        invalid = sorted(session for session in candidate if session in invalid_sessions)
        known_missing = sorted(
            session
            for session in candidate
            if session not in close_by_session and session not in invalid_sessions
        )
        return BenchmarkWindowDiagnostic(
            required_session_count=required,
            present_valid_session_count=present,
            window_start_session=None,
            window_end_session=latest_session,
            missing_session_count=max(required - present - len(invalid), 0),
            missing_sessions=tuple(known_missing[:MAX_DIAGNOSTIC_SESSIONS]),
            invalid_session_count=len(invalid),
            invalid_sessions=tuple(invalid[:MAX_DIAGNOSTIC_SESSIONS]),
            reason="insufficient_history",
        )
    window = sessions[latest_index - required + 1 : latest_index + 1]
    missing = sorted(
        session
        for session in window
        if session not in close_by_session and session not in invalid_sessions
    )
    invalid = sorted(session for session in window if session in invalid_sessions)
    present = sum(session in close_by_session for session in window)
    reason = (
        "invalid_close"
        if invalid
        else "missing_expected_session"
        if missing
        else "available"
    )
    return BenchmarkWindowDiagnostic(
        required_session_count=required,
        present_valid_session_count=present,
        window_start_session=window[0],
        window_end_session=window[-1],
        missing_session_count=len(missing),
        missing_sessions=tuple(missing[:MAX_DIAGNOSTIC_SESSIONS]),
        invalid_session_count=len(invalid),
        invalid_sessions=tuple(invalid[:MAX_DIAGNOSTIC_SESSIONS]),
        reason=reason,
    )


def _window_values(
    sessions: list[str],
    latest_session: str | None,
    close_by_session: dict[str, float],
    required: int,
) -> list[float]:
    if latest_session is None:
        raise BenchmarkCalculationError("Available window has no latest session.")
    latest_index = sessions.index(latest_session)
    window = sessions[latest_index - required + 1 : latest_index + 1]
    return [close_by_session[session] for session in window]


def _window_warnings(
    code: str,
    diagnostics: dict[str, BenchmarkWindowDiagnostic],
) -> list[str]:
    warnings: list[str] = []
    for metric, diagnostic in diagnostics.items():
        if diagnostic.reason == "available":
            continue
        warnings.append(
            f"Benchmark {code} {metric} unavailable: reason={diagnostic.reason}; "
            f"required={diagnostic.required_session_count}; "
            f"present_valid={diagnostic.present_valid_session_count}; "
            f"missing_count={diagnostic.missing_session_count}; "
            f"missing={list(diagnostic.missing_sessions)}; "
            f"invalid_count={diagnostic.invalid_session_count}; "
            f"invalid={list(diagnostic.invalid_sessions)}."
        )
    return warnings


def _compact_date(value: object) -> str:
    normalized = str(value).strip().replace("-", "")
    try:
        return datetime.strptime(normalized, "%Y%m%d").strftime("%Y%m%d")
    except ValueError as exc:
        raise BenchmarkCalculationError(
            "Benchmark and expected session dates must use YYYYMMDD format."
        ) from exc
