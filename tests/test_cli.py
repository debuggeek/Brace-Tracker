import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from brace_tracker.cli import ANSI_GREEN, ANSI_RED, ANSI_RESET, ANSI_YELLOW


FORMAT = "%a %b %d %Y %H:%M:%S GMT%z"
CENTRAL = timezone(timedelta(hours=-5))


def format_timestamp(dt: datetime) -> str:
    return dt.strftime(FORMAT) + " (Central Daylight Time)"


def test_cli_reports_device_summary(tmp_path):
    data_dir = tmp_path
    csv_path = data_dir / "ALPHA_log.csv"

    lines = ["", "index,date,temperature"]
    index = 0
    start = datetime(2025, 9, 11, 0, 0, tzinfo=CENTRAL)
    for day in range(7):
        day_start = start + timedelta(days=day)
        for hour in range(24):
            timestamp = day_start + timedelta(hours=hour)
            temp = 95 if hour < 16 else 80
            lines.append(f"{index},{format_timestamp(timestamp)},{temp}")
            index += 1
    csv_path.write_text("\r\n".join(lines), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "brace_tracker",
            "--data-dir",
            str(data_dir),
            "--color",
            "always",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Device: ALPHA" in result.stdout
    assert (
        "7-day avg: "
        f"{ANSI_GREEN}16.0 hr/day{ANSI_RESET}"
        " (based on 7/7 days, meets goal)"
    ) in result.stdout


def test_cli_verbose_reports_below_threshold_hours(tmp_path):
    data_dir = tmp_path
    csv_path = data_dir / "BETA_log.csv"

    lines = ["", "index,date,temperature"]
    index = 0
    start = datetime(2025, 9, 11, 0, 0, tzinfo=CENTRAL)
    for day in range(7):
        day_start = start + timedelta(days=day)
        for hour in range(24):
            timestamp = day_start + timedelta(hours=hour)
            if day == 0 and hour in {0, 1}:
                temp = 80
            elif day > 0 and hour >= 14:
                temp = 80
            else:
                temp = 95
            lines.append(f"{index},{format_timestamp(timestamp)},{temp}")
            index += 1
    csv_path.write_text("\r\n".join(lines), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "brace_tracker",
            "--data-dir",
            str(data_dir),
            "--device",
            "BETA",
            "--verbose",
            "--color",
            "always",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "needs improvement" in result.stdout
    assert "below 90.0°F at: 00:00, 01:00" in result.stdout


def test_cli_colors_daily_hours_relative_to_threshold(tmp_path):
    data_dir = tmp_path
    csv_path = data_dir / "OMEGA_log.csv"

    lines = ["", "index,date,temperature"]
    index = 0
    start = datetime(2025, 9, 11, 0, 0, tzinfo=CENTRAL)
    hour_specs = [24, 15, 13]
    for day, hot_hours in enumerate(hour_specs):
        day_start = start + timedelta(days=day)
        for hour in range(24):
            timestamp = day_start + timedelta(hours=hour)
            temp = 95 if hour < hot_hours else 80
            lines.append(f"{index},{format_timestamp(timestamp)},{temp}")
            index += 1
    csv_path.write_text("\r\n".join(lines), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "brace_tracker",
            "--data-dir",
            str(data_dir),
            "--device",
            "OMEGA",
            "--color",
            "always",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    stdout = result.stdout
    assert f"{ANSI_GREEN}24 hrs{ANSI_RESET}" in stdout
    assert f"{ANSI_YELLOW}15 hrs{ANSI_RESET}" in stdout
    assert f"{ANSI_RED}13 hrs{ANSI_RESET}" in stdout


def test_cli_color_never_disables_escape_codes(tmp_path):
    data_dir = tmp_path
    csv_path = data_dir / "GAMMA_log.csv"

    lines = ["", "index,date,temperature"]
    start = datetime(2025, 9, 11, 0, 0, tzinfo=CENTRAL)
    for index, hour in enumerate(range(24)):
        timestamp = start + timedelta(hours=hour)
        lines.append(f"{index},{format_timestamp(timestamp)},95")
    csv_path.write_text("\r\n".join(lines), encoding="utf-8")

    env = os.environ.copy()
    env.pop("NO_COLOR", None)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "brace_tracker",
            "--data-dir",
            str(data_dir),
            "--color",
            "never",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert "\033[" not in result.stdout
    assert "7-day avg" in result.stdout


def test_cli_respects_no_color_env(tmp_path):
    data_dir = tmp_path
    csv_path = data_dir / "DELTA_log.csv"

    lines = ["", "index,date,temperature"]
    start = datetime(2025, 9, 11, 0, 0, tzinfo=CENTRAL)
    for index, hour in enumerate(range(24)):
        timestamp = start + timedelta(hours=hour)
        lines.append(f"{index},{format_timestamp(timestamp)},95")
    csv_path.write_text("\r\n".join(lines), encoding="utf-8")

    env = os.environ.copy()
    env["NO_COLOR"] = "1"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "brace_tracker",
            "--data-dir",
            str(data_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert "\033[" not in result.stdout

