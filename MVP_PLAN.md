# MVP Roadmap

## Objective
Deliver a Python CLI that scans hourly CSV logs in `./bt-bracedata`, deduplicates overlapping samples, and reports whether each device maintains at least 16 hours/day of use (temperature > 90°F) over the last seven complete days.

## Phase 1 – Foundations
- Scaffold package structure (`brace_tracker/__init__.py`, `cli.py`, `io.py`, `metrics.py`, `__main__.py`).
- Establish configuration defaults: data directory (`./bt-bracedata`), usage threshold (16 hr/day), temperature threshold (90°F), rolling window (7 days).

## Phase 2 – Data Ingestion
- Discover `*.csv` files in the data directory and infer device IDs from filenames.
- Parse CSVs with robust date handling (timezone offsets, carriage returns, blank header row).
- Normalize timestamps to UTC hours; drop duplicates by keeping the highest temperature reading per device/hour.
- Cache clean records in memory keyed by device and hour.

## Phase 3 – Metrics & Aggregation
- For each device, count hours per day with temperature > 90°F.
- Compute 7-day totals ending at the most recent fully captured day; derive average hours/day.
- Prepare per-day breakdowns for reporting.

## Phase 4 – CLI Experience
- Implement `python -m brace_tracker --data-dir ./bt-bracedata` command.
- Display per-device summary including 7-day average, pass/fail status, and daily hour table.
- Support optional filters (`--device`, `--json` for structured output) if multiple devices are present.

## Phase 5 – Quality & Tooling
- Create pytest suites covering parsing edge cases, deduplication, metric calculations, and CLI smoke tests.
- Add linting (e.g., Ruff) and convenience scripts or Make targets (`make test`, `make lint`, `make run`).

## Phase 6 – Documentation & Iteration
- Document usage, configuration, and data expectations in `README.md` and `AGENTS.md`.
- Gather feedback from initial runs; plan enhancements (streaming for large files, alerting, additional metrics).
