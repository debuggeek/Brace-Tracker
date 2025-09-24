import subprocess
import sys
from datetime import datetime, timedelta, timezone


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
        for hour in range(16):
            timestamp = day_start + timedelta(hours=hour)
            lines.append(f"{index},{format_timestamp(timestamp)},95")
            index += 1
    csv_path.write_text("\r\n".join(lines), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "brace_tracker", "--data-dir", str(data_dir)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Device: ALPHA" in result.stdout
    assert "7-day avg: 16.0 hr/day (meets goal)" in result.stdout
