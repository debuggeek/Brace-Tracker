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
    average_hours_per_day: float
    days: Sequence[DailyUsage]
    threshold_met: bool
    complete_days: int


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
            average_hours_per_day=0.0,
            days=(),
            threshold_met=False,
            complete_days=0,
        )

    anchor_day = records[-1].hour.date()
    window: List[DailyUsage] = []
    total_hours = 0.0
    complete_days = 0

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

        if meets_sample_requirement:
            total_hours += hours_in_use
            complete_days += 1

    average = total_hours / complete_days if complete_days else 0.0

    return DeviceUsage(
        device_id=device_id,
        average_hours_per_day=average,
        days=tuple(window),
        threshold_met=complete_days > 0 and average >= usage_threshold,
        complete_days=complete_days,
    )
