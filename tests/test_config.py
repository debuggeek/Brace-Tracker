from pathlib import Path

import pytest

from brace_tracker.config import AnalysisConfig, load_config


def test_load_config_returns_defaults_when_missing(tmp_path):
    config = load_config(path=None)
    assert isinstance(config, AnalysisConfig)
    assert config.usage_threshold_hours_per_day == 16.0
    assert config.temperature_threshold_fahrenheit == 90.0
    assert config.window_days == 7


def test_load_config_from_file(tmp_path):
    config_path = tmp_path / "custom.toml"
    config_path.write_text(
        """
[analysis]
usage_threshold_hours_per_day = 12.5
temperature_threshold_fahrenheit = 87.0
window_days = 5
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.usage_threshold_hours_per_day == 12.5
    assert config.temperature_threshold_fahrenheit == 87.0
    assert config.window_days == 5


def test_load_config_raises_for_missing_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "missing.toml")
