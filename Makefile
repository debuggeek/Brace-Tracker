.PHONY: install lint fmt test run

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
	. .venv/bin/activate && python -m brace_tracker --data-dir bt-bracedata
