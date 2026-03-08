.PHONY: lint format test typecheck check install-hooks build clean

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

test:
	uv run pytest -q

typecheck:
	uvx ty check src/

check: lint format test typecheck

install-hooks:
	uv run pre-commit install

build:
	uv build

clean:
	rm -rf dist/ build/ *.egg-info
