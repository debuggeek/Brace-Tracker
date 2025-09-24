"""Configuration handling for brace tracker."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import tomllib


DEFAULT_CONFIG_PATH = Path("brace_tracker.toml")


@dataclass(frozen=True)
class AnalysisConfig:
    """Analysis parameters for determining brace usage."""

    usage_threshold_hours_per_day: float = 16.0
    temperature_threshold_fahrenheit: float = 90.0
    window_days: int = 7


DEFAULTS = AnalysisConfig()


def load_config(path: Path | None = None) -> AnalysisConfig:
    """Load analysis configuration from ``path`` or fall back to defaults."""

    if path is not None:
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        data = _load_toml(path)
    elif DEFAULT_CONFIG_PATH.exists():
        data = _load_toml(DEFAULT_CONFIG_PATH)
    else:
        return AnalysisConfig()

    analysis = data.get("analysis", {}) if isinstance(data, Mapping) else {}

    return AnalysisConfig(
        usage_threshold_hours_per_day=float(
            analysis.get("usage_threshold_hours_per_day", DEFAULTS.usage_threshold_hours_per_day)
        ),
        temperature_threshold_fahrenheit=float(
            analysis.get(
                "temperature_threshold_fahrenheit",
                DEFAULTS.temperature_threshold_fahrenheit,
            )
        ),
        window_days=int(analysis.get("window_days", DEFAULTS.window_days)),
    )


def _load_toml(path: Path) -> Mapping[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)
