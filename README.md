# Brace Tracker CLI

Brace Tracker analyzes hourly temperature logs exported as CSV files and reports whether each device meets the weekly wear-time target of 16 hours per day. The tool deduplicates overlapping records to one reading per hour, evaluates the last seven complete days, and summarizes daily hours alongside the 7-day average.

## Project Structure
- `brace_tracker/`: Python package containing the CLI (`cli.py`), configuration loader (`config.py`), CSV ingestion (`io.py`), and metric calculations (`metrics.py`).
- `bt-bracedata/`: Sample data directory holding device CSV exports.
- `tests/`: Pytest suite with fixtures and coverage for ingestion, aggregation, and CLI behavior.
- `brace_tracker.toml`: Default thresholds and window length for local runs.

## Setup
Brace Tracker targets Python 3.11+. Create a virtual environment and install dependencies:

```bash
make install
```

This command creates `.venv/`, upgrades `pip`, and installs the package in editable mode with development tools (`pytest`, `ruff`, `black`). Activate the environment for manual commands:

```bash
source .venv/bin/activate
```

## Usage
Run the CLI against the bundled sample data or your own CSV folder:

```bash
python -m brace_tracker --data-dir bt-bracedata
```

Optional flags:
- `--device ID` (repeatable) limits output to selected device IDs.
- `--json` emits structured JSON rather than formatted text.
- `--verbose` lists the hours each day that fell below the temperature threshold.
- `--config path/to/config.toml` loads thresholds from a specific TOML file.

A convenience target mirrors the default run:

```bash
make run
```

## Configuration
Runtime thresholds live in `brace_tracker.toml`:

```toml
[analysis]
usage_threshold_hours_per_day = 16.0
temperature_threshold_fahrenheit = 90.0
window_days = 7
```

Override values by editing this file or pointing `--config` at an alternate TOML (e.g., `brace_tracker.toml.local`, which is ignored by git). Invalid paths raise a clear CLI error.

## Quality Checks
Execute the full test suite after changes:

```bash
make test
```

Lint and format code before opening a pull request:

```bash
make lint
make fmt
```

Refer to `AGENTS.md` for contributor expectations and the detailed workflow.
