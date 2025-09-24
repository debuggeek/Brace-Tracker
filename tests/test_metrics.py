from datetime import datetime, timedelta
from pathlib import Path

from brace_tracker.io import RawRecord
from brace_tracker.metrics import (
    DeviceUsage,
    HourlyRecord,
    compute_device_usage,
    normalize_records,
)

FMT = "%Y-%m-%d %H:%M%z"

def dt(value: str) -> datetime:
    return datetime.strptime(value, FMT)


def build_record(device: str, value: str, temperature: float) -> RawRecord:
    return RawRecord(
        device_id=device,
        timestamp=dt(value),
        temperature=temperature,
        source_path=Path(f"{device}.csv"),
    )


def test_normalize_records_keeps_highest_temperature():
    records = [
        build_record("alpha", "2025-09-11 10:15-0500", 85.0),
        build_record("alpha", "2025-09-11 10:45-0500", 95.0),
    ]

    normalized = normalize_records(records)

    assert len(normalized) == 1
    assert normalized[0].temperature == 95.0
    assert normalized[0].hour == dt("2025-09-11 10:00-0500")


def test_compute_device_usage_returns_window_with_missing_days_filled():
    records = [
        build_record("alpha", "2025-09-11 10:00-0500", 95.0),
        build_record("alpha", "2025-09-12 09:00-0500", 95.0),
        build_record("alpha", "2025-09-17 21:00-0500", 95.0),
    ]

    normalized = normalize_records(records)

    usages = compute_device_usage(
        normalized,
        usage_threshold=16.0,
        temperature_threshold=90.0,
        window_days=7,
    )

    assert len(usages) == 1
    usage = usages[0]
    assert usage.device_id == "alpha"
    assert usage.average_hours_per_day == 0
    assert usage.complete_days == 0
    assert usage.days[0].day == dt("2025-09-11 00:00-0500").date()
    assert usage.days[-1].day == dt("2025-09-17 00:00-0500").date()
    hours = [day.hours_in_use for day in usage.days]
    assert hours.count(1) == 3
    assert hours.count(0) == 4
    assert all(day.samples_present in {0, 1} for day in usage.days)
    assert all(not day.is_complete for day in usage.days)
    assert usage.threshold_met is False


def test_compute_device_usage_handles_multiple_devices():
    records = []
    start = dt("2025-09-11 00:00-0500")
    for day_offset in range(7):
        for hour_offset in range(24):
            timestamp = start + timedelta(days=day_offset, hours=hour_offset)
            temp = 95.0 if hour_offset < 16 else 80.0
            records.append(
                RawRecord(
                    device_id="beta",
                    timestamp=timestamp,
                    temperature=temp,
                    source_path=Path("beta.csv"),
                )
            )
    # gamma has only a single hourly sample on the last day
    records.append(build_record("gamma", "2025-09-17 10:00-0500", 80.0))

    normalized = normalize_records(records)
    usages = compute_device_usage(
        normalized,
        usage_threshold=16.0,
        temperature_threshold=90.0,
        window_days=7,
    )

    assert {u.device_id for u in usages} == {"beta", "gamma"}

    beta_usage = next(u for u in usages if u.device_id == "beta")
    assert beta_usage.threshold_met is True
    assert abs(beta_usage.average_hours_per_day - 16.0) < 1e-6
    assert beta_usage.complete_days == 7
    assert all(day.samples_present == 24 for day in beta_usage.days)
    assert all(len(day.below_threshold_hours) == 8 for day in beta_usage.days)

    gamma_usage = next(u for u in usages if u.device_id == "gamma")
    assert gamma_usage.average_hours_per_day == 0
    assert gamma_usage.complete_days == 0
    below_counts = [len(day.below_threshold_hours) for day in gamma_usage.days]
    assert sum(below_counts) == 1
    assert any(
        hour == dt("2025-09-17 10:00-0500") for day in gamma_usage.days for hour in day.below_threshold_hours
    )
