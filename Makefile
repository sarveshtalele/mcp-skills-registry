.PHONY: install test lint format run docker-build clean

install:
	pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check .
	black --check src tests scripts app.py

format:
	ruff check --fix .
	black src tests scripts app.py

run:
	skill-registry

docker-build:
	docker build -t mcp-skill-registry .

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache data *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
