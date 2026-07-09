"""Lazy Qlib adapter boundary.

Core ML contracts must not import Qlib directly. This adapter is the only
place where a future Qlib import should happen.
"""

from __future__ import annotations

from typing import Any

from ml.base import MLExperimentConfig


class QlibAdapter:
    """Small boundary object for future Qlib-backed experiments."""

    def __init__(self, qlib_module: Any | None = None) -> None:
        self._qlib = qlib_module

    @property
    def qlib(self) -> Any:
        if self._qlib is None:
            try:
                import qlib as qlib_module
            except ImportError as exc:
                raise RuntimeError("Qlib is not installed; install an optional Qlib extra before using this adapter.") from exc
            self._qlib = qlib_module
        return self._qlib

    def is_available(self) -> bool:
        try:
            _ = self.qlib
        except RuntimeError:
            return False
        return True

    def build_experiment_payload(self, config: MLExperimentConfig) -> dict[str, str]:
        """Return a deterministic payload without starting Qlib training."""
        return {
            "experiment_name": config.experiment_name,
            "model_name": config.model_name,
            "universe": config.universe,
            "label_window": config.label_window,
            "adapter": "qlib",
        }
