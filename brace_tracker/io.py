"""Input helpers for reading device CSV logs."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, List


@dataclass(frozen=True)
class RawRecord:
    """Single CSV row parsed from disk prior to deduplication."""

    device_id: str
    timestamp: datetime
    temperature: float
    source_path: Path


def load_raw_records(data_dir: Path) -> List[RawRecord]:
    """Load all CSV logs from ``data_dir`` into memory."""

    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    records: List[RawRecord] = []
    for path in sorted(_iter_csv_paths(data_dir)):
        records.extend(_read_csv(path))
    return records


def _iter_csv_paths(data_dir: Path) -> Iterable[Path]:
    yield from (p for p in data_dir.glob("*.csv") if p.is_file())


def _read_csv(path: Path) -> List[RawRecord]:
    device_id = _infer_device_id(path)
    rows: List[RawRecord] = []

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(_strip_leading_blank_lines(handle))
        for row in reader:
            date_raw = (row.get("date") or "").strip()
            temp_raw = (row.get("temperature") or "").strip()
            if not date_raw or not temp_raw:
                continue

            try:
                timestamp = _parse_timestamp(date_raw)
            except ValueError:
                # Skip rows we cannot interpret.
                continue

            try:
                temperature = float(temp_raw)
            except ValueError:
                continue

            rows.append(
                RawRecord(
                    device_id=device_id,
                    timestamp=timestamp,
                    temperature=temperature,
                    source_path=path,
                )
            )

    return rows


def _strip_leading_blank_lines(handle: Iterable[str]) -> Iterator[str]:
    """Yield CSV lines after skipping an optional blank header row."""

    iterator = iter(handle)
    for line in iterator:
        if line.strip():
            yield line
            break
    else:
        return

    for line in iterator:
        yield line


def _parse_timestamp(raw: str) -> datetime:
    """Parse the exported timestamp into a timezone-aware datetime."""

    # Example: Thu Sep 11 2025 10:54:11 GMT-0500 (Central Daylight Time)
    cleaned = raw.split(" (")[0]
    return datetime.strptime(cleaned, "%a %b %d %Y %H:%M:%S GMT%z")


def _infer_device_id(path: Path) -> str:
    stem = path.stem
    return stem.split("_")[0] if "_" in stem else stem
