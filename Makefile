.PHONY: install lint test

install:
	pip install -e ".[dev]"

lint:
	ruff check .

test:
	pytest --cov=app --cov-report=term-missing
