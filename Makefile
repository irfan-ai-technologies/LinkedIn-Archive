.PHONY: install build serve sync import validate stats test lint format typecheck check clean

install:
	uv sync --extra dev

build:
	uv run linkedin-archive build

serve:
	uv run linkedin-archive serve

sync:
	uv run linkedin-archive sync

import:
	uv run linkedin-archive import $(FILE)

validate:
	uv run linkedin-archive validate

stats:
	uv run linkedin-archive stats

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy .

check: lint
	uv run ruff format --check .
	$(MAKE) typecheck
	$(MAKE) test

clean:
	rm -rf dist .pytest_cache .mypy_cache .ruff_cache
