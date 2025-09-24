from pathlib import Path

from brace_tracker.io import RawRecord, load_raw_records


def test_load_raw_records_parses_timestamps(tmp_path):
    sample = (
        "\n"
        "index,date,temperature\r\n"
        "0,Thu Sep 11 2025 10:54:11 GMT-0500 (Central Daylight Time),91.5\r\n"
        "1,Thu Sep 11 2025 11:54:11 GMT-0500 (Central Daylight Time),92.5\r\n"
    )
    csv_path = tmp_path / "DEVICE_sample_log.csv"
    csv_path.write_text(sample, encoding="utf-8")

    records = load_raw_records(tmp_path)

    assert len(records) == 2
    first = records[0]
    assert isinstance(first, RawRecord)
    assert first.device_id == "DEVICE"
    assert first.timestamp.tzinfo is not None
    assert first.temperature == 91.5
    assert first.source_path == csv_path
