# Repository Guidelines

## Project Structure & Module Organization
All application code lives under `brace_tracker/`, split into `cli.py` for argument parsing, `config.py` for loading thresholds, `io.py` for CSV ingestion, `metrics.py` for rollups, and `__main__.py` as the CLI entrypoint. Shared utilities belong in `utils/` if they are not specific to a single module. Data fixtures remain in `bt-bracedata/`; keep raw samples in device-named CSV files (e.g., `CB48F0F5_CB48F0F5_log.csv`). Runtime parameters (thresholds, window length) live in `brace_tracker.toml`; keep environment-specific overrides out of version control unless they are shared defaults. Tests mirror the package layout in `tests/`, using `tests/data/` for sample logs.

## Build, Test, and Development Commands
Use a local virtualenv. Typical workflow:
- `python -m brace_tracker --data-dir bt-bracedata` runs the analyzer against bundled samples (use `--verbose` for below-threshold hour detail).
- `make lint` (or `ruff check brace_tracker tests`) enforces style rules.
- `make test` (or `pytest`) executes the unit suite.
Add Make targets as you introduce new steps (e.g., `make fmt`).

## Coding Style & Naming Conventions
Target Python 3.11+. Follow Ruff + Black defaults: 4-space indentation, 88-char lines, double quotes except where escaping is clearer. Modules and packages use snake_case; CLI flags follow kebab-case (`--data-dir`). Pure functions belong in modules; imperative flows stay in the CLI layer. Document non-obvious logic with concise comments.

## Testing Guidelines
Use pytest with descriptive function names (`test_dedup_keeps_highest_temp`). Cover parsing edge cases (blank headers, CRLF endings), hour deduplication, metric windows, and CLI output formatting. Add regression fixtures to `tests/data/` whenever a bug is fixed. Aim for meaningful coverage on `metrics.py` and `io.py`—these modules drive correctness.

## Commit & Pull Request Guidelines
Write commits in imperative present tense (`Add hourly dedup helper`). Group related changes; avoid mixing refactors with feature work. PRs should summarize behavior, list validation commands, and link relevant issues. Include sample CLI output or JSON snippets when behavior changes. Request review once tests and lint pass locally.

## Configuration & Security Notes
Do not commit proprietary datasets. Thresholds and window settings should be adjusted via `brace_tracker.toml` rather than code edits. For alternate data roots, expose environment variables (`BRACE_DATA_DIR`) or CLI flags while keeping defaults safe. Handle parsing errors gracefully and log with context rather than crashing.
