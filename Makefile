.PHONY: lint format test typecheck check install-hooks

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

test:
	uv run pytest -q

typecheck:
	uv run mypy src/

check: lint format test typecheck

install-hooks:
	uv run pre-commit install
