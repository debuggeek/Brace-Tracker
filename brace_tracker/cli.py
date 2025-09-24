"""Command-line interface entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, List, Sequence

from . import __version__
from .config import load_config
from .io import load_raw_records
from .metrics import DeviceUsage, compute_device_usage, normalize_records

DEFAULT_DATA_DIR = Path("bt-bracedata")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Brace usage analyzer")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing device CSV logs",
    )
    parser.add_argument(
        "--device",
        action="append",
        dest="devices",
        help="Limit analysis to one or more device IDs",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON instead of text",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show below-threshold hours for each day",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to TOML config file (defaults to brace_tracker.toml)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"brace-tracker {__version__}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        raw_records = load_raw_records(args.data_dir)
    except FileNotFoundError as exc:
        parser.error(str(exc))
        return

    if not raw_records:
        print("No records found", file=sys.stderr)
        sys.exit(1)

    try:
        config = load_config(args.config)
    except FileNotFoundError as exc:
        parser.error(str(exc))
        return

    hourly_records = normalize_records(raw_records)
    if args.devices:
        device_filter = set(args.devices)
        hourly_records = [r for r in hourly_records if r.device_id in device_filter]
        if not hourly_records:
            print("No matching device data", file=sys.stderr)
            sys.exit(1)

    usages = compute_device_usage(
        hourly_records,
        usage_threshold=config.usage_threshold_hours_per_day,
        temperature_threshold=config.temperature_threshold_fahrenheit,
        window_days=config.window_days,
    )

    if args.json:
        print(_render_json(usages))
    else:
        print(
            _render_text(
                usages,
                verbose=args.verbose,
                temp_threshold=config.temperature_threshold_fahrenheit,
            )
        )


def _render_json(usages: Iterable[DeviceUsage]) -> str:
    payload = []
    for usage in usages:
        entry = asdict(usage)
        entry["days"] = [asdict(day) for day in usage.days]
        payload.append(entry)
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def _render_text(
    usages: Iterable[DeviceUsage],
    *,
    verbose: bool = False,
    temp_threshold: float,
) -> str:
    lines: List[str] = []
    for usage in usages:
        status = "meets goal" if usage.threshold_met else "needs improvement"
        lines.append(f"Device: {usage.device_id}")
        total_days = len(usage.days)
        lines.append(
            f"7-day avg: {usage.average_hours_per_day:.1f} hr/day (based on {usage.complete_days}/{total_days} days, {status})"
        )
        for day in usage.days:
            weekday = day.day.strftime("%a %Y-%m-%d")
            hours = day.hours_in_use
            suffix = "hr" if hours == 1 else "hrs"
            note = ""
            if not day.is_complete:
                note = f" (incomplete: {day.samples_present}/24 hours logged)"
            lines.append(f"  {weekday}: {hours} {suffix}{note}")
            if verbose and day.below_threshold_hours:
                times = ", ".join(h.strftime("%H:%M") for h in day.below_threshold_hours)
                lines.append(
                    f"    below {temp_threshold:.1f}°F at: {times}"
                )
        lines.append("")
    return "\n".join(lines).strip()
