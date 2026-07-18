"""Deterministic selected-sector calculations on exact equity sessions."""

from __future__ import annotations

from datetime import datetime
from math import isfinite, sqrt

import numpy as np
import pandas as pd

from market_cockpit.sector_contracts import SectorMetrics, SectorWindowDiagnostic
from market_cockpit.sector_repository import PersistedSectorSnapshot

MAX_DIAGNOSTIC_SESSIONS = 10


class SectorCalculationError(ValueError):
    """Raised when persisted sector data violates the reviewed contract."""


def calculate_sector_metrics(
    snapshot: PersistedSectorSnapshot,
    *,
    expected_sessions: list[str],
) -> tuple[list[SectorMetrics], list[str]]:
    sessions = _validated_expected_sessions(expected_sessions)
    session_set = set(sessions)
    frame = snapshot.sector_daily.copy()
    frame["trade_date"] = frame["trade_date"].map(_compact_date)
    unexpected = sorted(set(frame["sector_code"].astype(str)) - set(snapshot.sector_codes))
    if unexpected:
        raise SectorCalculationError(f"Sector snapshot contains unexpected codes: {unexpected}.")
    definitions = snapshot.sector_definition.set_index("sector_code")
    if definitions.index.duplicated().any():
        raise SectorCalculationError("Sector snapshot contains duplicate definitions.")

    warnings: list[str] = []
    outside = frame.loc[~frame["trade_date"].isin(session_set)]
    if not outside.empty:
        labels = sorted(outside[["sector_code", "trade_date"]].astype(str).agg(":".join, axis=1).unique())
        warnings.append(_bounded_message(
            "Excluded sector rows outside the selected equity open-session sequence", labels
        ))
    frame = frame.loc[frame["trade_date"].isin(session_set)].copy()
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    duplicate_mask = frame.duplicated(
        ["source", "sector_code", "trade_date"], keep=False
    )
    duplicate_sessions_by_code = {
        code: set(
            frame.loc[
                duplicate_mask & frame["sector_code"].astype(str).eq(code),
                "trade_date",
            ].astype(str)
        )
        for code in snapshot.sector_codes
    }

    metrics: list[SectorMetrics] = []
    for code in sorted(snapshot.sector_codes):
        sector_name = str(definitions.loc[code, "sector_name"])
        code_frame = frame.loc[frame["sector_code"].astype(str).eq(code)].sort_values("trade_date")
        close_by_session: dict[str, float] = {}
        invalid_sessions: set[str] = set(duplicate_sessions_by_code[code])
        for row in code_frame[["trade_date", "close"]].to_dict(orient="records"):
            session = str(row["trade_date"])
            if session in duplicate_sessions_by_code[code]:
                continue
            value = row["close"]
            if pd.isna(value) or not isfinite(float(value)) or float(value) <= 0:
                invalid_sessions.add(session)
            else:
                close_by_session[session] = float(value)
        valid_sessions = [session for session in sessions if session in close_by_session]
        latest_session = valid_sessions[-1] if valid_sessions else None
        latest_close = close_by_session.get(latest_session) if latest_session else None
        latest_window = _window_diagnostic(sessions, latest_session, close_by_session, invalid_sessions, 2)
        return_5_window = _window_diagnostic(sessions, latest_session, close_by_session, invalid_sessions, 6)
        return_20_window = _window_diagnostic(sessions, latest_session, close_by_session, invalid_sessions, 21)
        sma20_window = _window_diagnostic(sessions, latest_session, close_by_session, invalid_sessions, 20)
        risk_window = _window_diagnostic(sessions, latest_session, close_by_session, invalid_sessions, 21)

        latest_return = _endpoint_return(sessions, latest_session, close_by_session, 2, latest_window)
        return_5 = _endpoint_return(sessions, latest_session, close_by_session, 6, return_5_window)
        return_20 = _endpoint_return(sessions, latest_session, close_by_session, 21, return_20_window)
        sma20 = None
        if sma20_window.reason == "available":
            sma20 = float(np.mean(_window_values(sessions, latest_session, close_by_session, 20)))
        volatility = None
        drawdown = None
        if risk_window.reason == "available":
            values = np.asarray(_window_values(sessions, latest_session, close_by_session, 21), dtype=float)
            returns = values[1:] / values[:-1] - 1.0
            volatility = float(returns.std(ddof=1) * sqrt(252))
            wealth = np.concatenate(([1.0], np.cumprod(1.0 + returns)))
            drawdown = float(np.min(wealth / np.maximum.accumulate(wealth) - 1.0))
        diagnostics = {
            "latest_return": latest_window,
            "return_5": return_5_window,
            "return_20": return_20_window,
            "sma20": sma20_window,
            "volatility_drawdown_20": risk_window,
        }
        code_warnings = _window_warnings(code, diagnostics)
        if invalid_sessions:
            code_warnings.append(_bounded_message(
                f"Sector {code} excluded invalid close sessions", sorted(invalid_sessions)
            ))
        metrics.append(SectorMetrics(
            sector_code=code,
            sector_name=sector_name,
            latest_close=latest_close,
            latest_session=latest_session,
            latest_return=latest_return,
            return_5=return_5,
            return_20=return_20,
            sma20=sma20,
            sma20_distance=(latest_close / sma20 - 1.0) if latest_close is not None and sma20 is not None else None,
            above_sma20=(latest_close > sma20) if latest_close is not None and sma20 is not None else None,
            realized_volatility_20=volatility,
            max_drawdown_20=drawdown,
            available_session_count=len(valid_sessions),
            latest_return_window=latest_window,
            return_5_window=return_5_window,
            return_20_window=return_20_window,
            sma20_window=sma20_window,
            risk_window=risk_window,
            warnings=tuple(code_warnings),
        ))
        warnings.extend(code_warnings)
    return metrics, warnings


def _endpoint_return(
    sessions: list[str],
    latest_session: str | None,
    closes: dict[str, float],
    required: int,
    diagnostic: SectorWindowDiagnostic,
) -> float | None:
    if diagnostic.reason != "available":
        return None
    values = _window_values(sessions, latest_session, closes, required)
    return values[-1] / values[0] - 1.0


def _validated_expected_sessions(values: list[str]) -> list[str]:
    if not isinstance(values, list) or not values:
        raise SectorCalculationError(
            "Sector calculation requires a non-empty persisted equity open-session sequence."
        )
    sessions = [_compact_date(value) for value in values]
    if sessions != sorted(sessions) or len(sessions) != len(set(sessions)):
        raise SectorCalculationError(
            "Persisted equity open-session sequence must be unique and strictly ordered."
        )
    return sessions


def _window_diagnostic(
    sessions: list[str],
    latest_session: str | None,
    closes: dict[str, float],
    invalid_sessions: set[str],
    required: int,
) -> SectorWindowDiagnostic:
    if latest_session is None:
        return SectorWindowDiagnostic(required, 0, None, None, required, (), 0, (), "insufficient_history")
    latest_index = sessions.index(latest_session)
    if latest_index + 1 < required:
        candidate = sessions[: latest_index + 1]
        present = sum(session in closes for session in candidate)
        invalid = sorted(session for session in candidate if session in invalid_sessions)
        missing = sorted(session for session in candidate if session not in closes and session not in invalid_sessions)
        return SectorWindowDiagnostic(
            required, present, None, latest_session, max(required - present - len(invalid), 0),
            tuple(missing[:MAX_DIAGNOSTIC_SESSIONS]), len(invalid),
            tuple(invalid[:MAX_DIAGNOSTIC_SESSIONS]), "insufficient_history",
        )
    window = sessions[latest_index - required + 1 : latest_index + 1]
    missing = sorted(session for session in window if session not in closes and session not in invalid_sessions)
    invalid = sorted(session for session in window if session in invalid_sessions)
    reason = "invalid_close" if invalid else "missing_expected_session" if missing else "available"
    return SectorWindowDiagnostic(
        required, sum(session in closes for session in window), window[0], window[-1],
        len(missing), tuple(missing[:MAX_DIAGNOSTIC_SESSIONS]), len(invalid),
        tuple(invalid[:MAX_DIAGNOSTIC_SESSIONS]), reason,
    )


def _window_values(
    sessions: list[str], latest_session: str | None, closes: dict[str, float], required: int
) -> list[float]:
    if latest_session is None:
        raise SectorCalculationError("Available window has no latest session.")
    latest_index = sessions.index(latest_session)
    return [closes[session] for session in sessions[latest_index - required + 1 : latest_index + 1]]


def _window_warnings(code: str, diagnostics: dict[str, SectorWindowDiagnostic]) -> list[str]:
    return [
        f"Sector {code} {metric} unavailable: reason={diagnostic.reason}; "
        f"required={diagnostic.required_session_count}; present_valid={diagnostic.present_valid_session_count}; "
        f"missing_count={diagnostic.missing_session_count}; missing={list(diagnostic.missing_sessions)}; "
        f"invalid_count={diagnostic.invalid_session_count}; invalid={list(diagnostic.invalid_sessions)}."
        for metric, diagnostic in diagnostics.items()
        if diagnostic.reason != "available"
    ]


def _bounded_message(prefix: str, values: list[str]) -> str:
    suffix = f" (+{len(values) - MAX_DIAGNOSTIC_SESSIONS} more)" if len(values) > MAX_DIAGNOSTIC_SESSIONS else ""
    return f"{prefix}: {values[:MAX_DIAGNOSTIC_SESSIONS]}{suffix}."


def _compact_date(value: object) -> str:
    normalized = str(value).strip().replace("-", "")
    try:
        return datetime.strptime(normalized, "%Y%m%d").strftime("%Y%m%d")
    except ValueError as exc:
        raise SectorCalculationError(
            "Sector and expected session dates must use YYYYMMDD format."
        ) from exc
