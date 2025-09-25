"""Transform raw records into usage metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Sequence

from .io import RawRecord


@dataclass(frozen=True)
class HourlyRecord:
    device_id: str
    hour: datetime
    temperature: float


@dataclass(frozen=True)
class DailyUsage:
    day: date
    hours_in_use: int
    below_threshold_hours: Sequence[datetime]
    samples_present: int
    is_complete: bool


@dataclass(frozen=True)
class DeviceUsage:
    device_id: str
    seven_day_average_hours_per_day: float
    overall_average_hours_per_day: float
    days: Sequence[DailyUsage]
    threshold_met: bool
    complete_days_last_seven: int
    complete_days_overall: int


def normalize_records(records: Iterable[RawRecord]) -> List[HourlyRecord]:
    """Collapse raw readings down to one record per device/hour."""

    collapsed: Dict[tuple[str, datetime], HourlyRecord] = {}

    for record in records:
        floored = record.timestamp.replace(minute=0, second=0, microsecond=0)
        key = (record.device_id, floored)
        existing = collapsed.get(key)
        if existing is None or record.temperature > existing.temperature:
            collapsed[key] = HourlyRecord(
                device_id=record.device_id,
                hour=floored,
                temperature=record.temperature,
            )

    return sorted(collapsed.values(), key=lambda r: (r.device_id, r.hour))


def compute_device_usage(
    hourly_records: Iterable[HourlyRecord],
    *,
    usage_threshold: float,
    temperature_threshold: float,
    window_days: int,
) -> List[DeviceUsage]:
    """Summarize usage for each device over the trailing window."""

    per_device: Dict[str, List[HourlyRecord]] = {}
    for record in hourly_records:
        per_device.setdefault(record.device_id, []).append(record)

    summaries: List[DeviceUsage] = []
    for device_id, device_records in sorted(per_device.items()):
        device_records.sort(key=lambda r: r.hour)
        summaries.append(
            _summarize_device(
                device_id=device_id,
                records=device_records,
                usage_threshold=usage_threshold,
                temperature_threshold=temperature_threshold,
                window_days=window_days,
            )
        )

    return summaries


def _summarize_device(
    *,
    device_id: str,
    records: Sequence[HourlyRecord],
    usage_threshold: float,
    temperature_threshold: float,
    window_days: int,
) -> DeviceUsage:
    hours_in_use_by_day: Dict[date, int] = {}
    below_threshold_by_day: Dict[date, List[datetime]] = {}

    for record in records:
        local_day = record.hour.date()
        if record.temperature > temperature_threshold:
            hours_in_use_by_day[local_day] = hours_in_use_by_day.get(local_day, 0) + 1
        else:
            below_threshold_by_day.setdefault(local_day, []).append(record.hour)

    if not records:
        return DeviceUsage(
            device_id=device_id,
            seven_day_average_hours_per_day=0.0,
            overall_average_hours_per_day=0.0,
            days=(),
            threshold_met=False,
            complete_days_last_seven=0,
            complete_days_overall=0,
        )

    anchor_day = records[-1].hour.date()
    window: List[DailyUsage] = []

    for offset in range(window_days):
        target_day = anchor_day - timedelta(days=window_days - 1 - offset)
        hours_in_use = hours_in_use_by_day.get(target_day, 0)
        below_hours = tuple(sorted(below_threshold_by_day.get(target_day, ())))
        sample_count = hours_in_use + len(below_hours)
        meets_sample_requirement = sample_count == 24

        window.append(
            DailyUsage(
                day=target_day,
                hours_in_use=hours_in_use,
                below_threshold_hours=below_hours,
                samples_present=sample_count,
                is_complete=meets_sample_requirement,
            )
        )

    complete_days_overall = sum(1 for day in window if day.is_complete)
    total_hours_overall = sum(day.hours_in_use for day in window if day.is_complete)
    overall_average = (
        total_hours_overall / complete_days_overall if complete_days_overall else 0.0
    )

    recent_window_size = min(7, len(window))
    recent_days = window[-recent_window_size:] if window else []
    complete_days_recent = sum(1 for day in recent_days if day.is_complete)
    total_hours_recent = sum(day.hours_in_use for day in recent_days if day.is_complete)
    seven_day_average = (
        total_hours_recent / complete_days_recent if complete_days_recent else 0.0
    )

    return DeviceUsage(
        device_id=device_id,
        seven_day_average_hours_per_day=seven_day_average,
        overall_average_hours_per_day=overall_average,
        days=tuple(window),
        threshold_met=complete_days_recent > 0 and seven_day_average >= usage_threshold,
        complete_days_last_seven=complete_days_recent,
        complete_days_overall=complete_days_overall,
    )
