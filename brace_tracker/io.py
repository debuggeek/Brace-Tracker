"""Input helpers for reading device CSV logs."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, List


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RawRecord:
    """Single CSV row parsed from disk prior to deduplication."""

    device_id: str
    timestamp: datetime
    temperature: float
    source_path: Path


def load_raw_records(source: Path) -> List[RawRecord]:
    """Load CSV logs from a directory or single file into memory."""

    logger.debug("Resolving data source: %s", source)
    if not source.exists():
        raise FileNotFoundError(f"Data source not found: {source}")

    if source.is_file():
        logger.debug("Source identified as file")
        records = _read_csv(source)
        logger.debug("Read %d records from %s", len(records), source)
        return records

    if not source.is_dir():
        raise FileNotFoundError(f"Data source not found: {source}")

    records: List[RawRecord] = []
    for path in sorted(_iter_csv_paths(source)):
        logger.debug("Reading CSV file: %s", path)
        records.extend(_read_csv(path))
    logger.debug("Aggregated %d records from directory %s", len(records), source)
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
                logger.debug("Skipping row with unparsable timestamp in %s", path)
                continue

            try:
                temperature = float(temp_raw)
            except ValueError:
                logger.debug("Skipping row with invalid temperature in %s", path)
                continue

            rows.append(
                RawRecord(
                    device_id=device_id,
                    timestamp=timestamp,
                    temperature=temperature,
                    source_path=path,
                )
            )

    logger.debug("Parsed %d rows for device %s from %s", len(rows), device_id, path)
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
