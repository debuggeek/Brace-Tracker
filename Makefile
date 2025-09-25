.PHONY: install lint fmt test run run-verbose run-30

DATA_DIR ?= bt-bracedata
INPUT_FILE ?=
BRACE_TRACKER_CMD = . .venv/bin/activate && python -m brace_tracker
DATA_ARGS = $(if $(INPUT_FILE),--input-file "$(INPUT_FILE)",--data-dir $(DATA_DIR))

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -U pip && pip install -e .[dev]

lint:
	. .venv/bin/activate && ruff check brace_tracker tests

fmt:
	. .venv/bin/activate && black brace_tracker tests

test:
	. .venv/bin/activate && pytest

run:
	$(BRACE_TRACKER_CMD) $(DATA_ARGS)

run-verbose:
	$(BRACE_TRACKER_CMD) $(DATA_ARGS) --verbose

run-30:
	$(BRACE_TRACKER_CMD) $(DATA_ARGS) --days 30
