"""Command-line interface entrypoint."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, List, Sequence, TextIO

from . import __version__
from .config import load_config
from .io import load_raw_records
from .metrics import DeviceUsage, compute_device_usage, normalize_records

DEFAULT_DATA_DIR = Path("bt-bracedata")

ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_RED = "\033[31m"
ANSI_RESET = "\033[0m"
NEAR_THRESHOLD_BUFFER_HOURS = 2.0


COLOR_AUTO = "auto"
COLOR_ALWAYS = "always"
COLOR_NEVER = "never"


logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Brace usage analyzer")
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing device CSV logs",
    )
    source_group.add_argument(
        "--input-file",
        type=Path,
        help="Path to a single device CSV log",
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
        "--color",
        choices=(COLOR_AUTO, COLOR_ALWAYS, COLOR_NEVER),
        default=COLOR_AUTO,
        help="Colorize CLI output: auto (default) only when writing to a TTY",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show below-threshold hours for each day",
    )
    parser.add_argument(
        "--days",
        type=int,
        help="Override the trailing window length in days",
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
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable verbose debug logging to stderr",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.days is not None and args.days <= 0:
        parser.error("--days must be a positive integer")

    _configure_logging(args.trace)
    if args.trace:
        logger.debug("Trace logging enabled")

    data_source = args.input_file if args.input_file is not None else args.data_dir

    logger.debug("Loading raw records from %s", data_source)
    try:
        raw_records = load_raw_records(data_source)
    except FileNotFoundError:
        if args.input_file:
            parser.error(f"Data file not found: {args.input_file}")
        else:
            parser.error(f"Data directory not found: {args.data_dir}")
        return

    if not raw_records:
        logger.debug("No records found at %s", data_source)
        print("No records found", file=sys.stderr)
        sys.exit(1)

    logger.debug("Loaded %d raw records", len(raw_records))

    logger.debug(
        "Loading configuration from %s",
        args.config if args.config is not None else "default config",
    )
    try:
        config = load_config(args.config)
    except FileNotFoundError as exc:
        parser.error(str(exc))
        return

    hourly_records = normalize_records(raw_records)
    logger.debug("Normalized to %d hourly records", len(hourly_records))
    if args.devices:
        device_filter = set(args.devices)
        logger.debug("Filtering to devices: %s", ", ".join(sorted(device_filter)))
        hourly_records = [r for r in hourly_records if r.device_id in device_filter]
        logger.debug("Filtered to %d hourly records after device selection", len(hourly_records))
        if not hourly_records:
            print("No matching device data", file=sys.stderr)
            sys.exit(1)

    window_days = args.days if args.days is not None else config.window_days
    logger.debug(
        "Computing usage metrics (window=%d days, usage_threshold=%.1f, temp_threshold=%.1f)",
        window_days,
        config.usage_threshold_hours_per_day,
        config.temperature_threshold_fahrenheit,
    )

    usages = compute_device_usage(
        hourly_records,
        usage_threshold=config.usage_threshold_hours_per_day,
        temperature_threshold=config.temperature_threshold_fahrenheit,
        window_days=window_days,
    )
    logger.debug("Computed usage for %d devices", len(usages))

    if args.json:
        logger.debug("Rendering JSON output")
        print(_render_json(usages))
    else:
        logger.debug("Rendering text output (verbose=%s)", args.verbose)
        print(
            _render_text(
                usages,
                verbose=args.verbose,
                temp_threshold=config.temperature_threshold_fahrenheit,
                usage_threshold=config.usage_threshold_hours_per_day,
                use_color=_should_use_color(args.color, sys.stdout),
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
    usage_threshold: float,
    use_color: bool,
) -> str:
    lines: List[str] = []
    for usage in usages:
        status = "meets goal" if usage.threshold_met else "needs improvement"
        lines.append(f"Device: {usage.device_id}")
        total_days = len(usage.days)
        recent_days = min(7, total_days)
        seven_day_text = f"{usage.seven_day_average_hours_per_day:.1f} hr/day"
        overall_text = f"{usage.overall_average_hours_per_day:.1f} hr/day"
        seven_day_fragment = _colorize_hours_text(
            seven_day_text,
            hours=usage.seven_day_average_hours_per_day,
            threshold=usage_threshold,
            use_color=use_color,
        )
        overall_fragment = _colorize_hours_text(
            overall_text,
            hours=usage.overall_average_hours_per_day,
            threshold=usage_threshold,
            use_color=use_color,
        )
        avg_line = (
            "7-day avg: "
            f"{seven_day_fragment} (based on {usage.complete_days_last_seven}/{recent_days} days, {status})"
            f" | overall avg ({total_days} days): "
            f"{overall_fragment} (based on {usage.complete_days_overall}/{total_days} days, {status})"
        )
        lines.append(avg_line)
        for day in usage.days:
            weekday = day.day.strftime("%a %Y-%m-%d")
            hours = day.hours_in_use
            suffix = "hr" if hours == 1 else "hrs"
            note = ""
            if not day.is_complete:
                note = f" (incomplete: {day.samples_present}/24 hours logged)"
            hours_text = f"{hours} {suffix}"
            line = (
                f"  {weekday}: "
                f"{_colorize_hours_text(hours_text, hours=float(hours), threshold=usage_threshold, use_color=use_color)}"
                f"{note}"
            )
            lines.append(line)
            if verbose and day.below_threshold_hours:
                times = ", ".join(h.strftime("%H:%M") for h in day.below_threshold_hours)
                lines.append(
                    f"    below {temp_threshold:.1f}°F at: {times}"
                )
        lines.append("")
    return "\n".join(lines).strip()


def _colorize_hours_text(
    text: str,
    *,
    hours: float,
    threshold: float,
    use_color: bool,
) -> str:
    """Wrap an ``hours`` display fragment in ANSI color codes."""

    if not use_color:
        return text

    color = _color_for_hours(hours, threshold)
    return f"{color}{text}{ANSI_RESET}"


def _color_for_hours(hours: float, threshold: float) -> str:
    """Return the ANSI escape sequence for ``hours`` relative to ``threshold``."""

    delta = hours - threshold
    if delta >= 0:
        return ANSI_GREEN
    if delta >= -NEAR_THRESHOLD_BUFFER_HOURS:
        return ANSI_YELLOW
    return ANSI_RED


def _should_use_color(mode: str, stream: TextIO = sys.stdout) -> bool:
    """Determine whether CLI output should include ANSI colors."""

    if mode == COLOR_ALWAYS:
        return True
    if mode == COLOR_NEVER:
        return False
    if os.environ.get("NO_COLOR") is not None:
        return False
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def _configure_logging(enable_trace: bool) -> None:
    if not enable_trace:
        return

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s %(name)s: %(message)s",
        force=True,
    )
