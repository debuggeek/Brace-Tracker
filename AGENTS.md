# Repository Guidelines

## Project Structure & Module Organization
Project code lives in `brace_tracker/`: `cli.py` wires the CLI, `config.py` pulls thresholds, `io.py` ingests CSV logs, `metrics.py` calculates rollups, and `__main__.py` exposes the entrypoint. Shared helpers belong in `utils/` to avoid CLI-specific coupling. Tests mirror the package inside `tests/`, with sample logs anchored in `tests/data/` and production-like fixtures under `bt-bracedata/`. Tune runtime thresholds through `brace_tracker.toml`; keep environment overrides out of source control.

## Build, Test, and Development Commands
Activate a local Python 3.11+ virtualenv before running tools. `python -m brace_tracker --data-dir bt-bracedata --verbose` exercises the analyzer against bundled samples and prints incomplete days. `make lint` (alias `ruff check brace_tracker tests`) enforces formatting and import rules. `make test` (alias `pytest`) runs the unit suite; add new fixtures in `tests/data/` when fixing regressions. Extend the `Makefile` with helper targets (e.g., `make fmt`) instead of shell aliases.

## Coding Style & Naming Conventions
Follow Black defaults: 4-space indentation, 88-character lines, double quotes unless escaping is cleaner. Keep modules, functions, and variables in snake_case; reserve PascalCase for classes and kebab-case for CLI flags such as `--data-dir`. Prefer pure functions in metrics and IO layers, leaving orchestration logic in the CLI. Document non-obvious calculations with concise docstrings or inline comments.

## Testing Guidelines
Write pytest functions named for behavior (`test_hour_dedup_keeps_max_temp`). Cover parsing edges, hourly deduplication, metric window math, and CLI output formatting. Use real-world samples when possible and commit trimmed fixtures that reproduce failures. Run `pytest -k <pattern>` to focus on new scenarios before pushing.

## Commit & Pull Request Guidelines
Commits should be imperative and scoped (`Add hourly gap check`). Group related changes and keep refactors separate from feature work. Pull requests need a behavior summary, validation commands, linked issues, and sample CLI output when behavior shifts. Confirm `make lint` and `make test` pass locally before requesting review.

## Security & Configuration Tips
Do not commit proprietary or device-identifiable datasets. Manage thresholds and window lengths via `brace_tracker.toml` rather than hardcoding. Support alternate data roots through the `BRACE_DATA_DIR` environment variable or `--data-dir` flag. Guard against abrupt exits by logging parser errors with file context.
