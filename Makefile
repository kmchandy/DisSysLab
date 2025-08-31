# Makefile at repo root

.PHONY: dev test clean

# Set up venv and install editable package
dev:
	python3 -m venv .venv
	. .venv/bin/activate && python -m pip install --upgrade pip
	. .venv/bin/activate && python -m pip install -e .

# Run tests
test:
	. .venv/bin/activate && pytest -q

# Clean build/test artifacts
clean:
	rm -rf .venv
	rm -rf dsl.egg-info dist build
	find . -type d -name "__pycache__" -exec rm -rf {} +
