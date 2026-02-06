# Makefile at repo root
# Use the venv's Python directly, so we don't need 'activate'
PY  := .venv/bin/python
PIP := $(PY) -m pip
.DEFAULT_GOAL := help

.PHONY: dev dev-extras test test-one clean help

help:
	@echo "Targets:"
	@echo "  make dev          - create venv and install package (editable)"
	@echo "  make dev-extras   - create venv and install package with extras: [dev]"
	@echo "  make test         - run all tests via venv python"
	@echo "  make test-one FILE=dsl/tests/test_intro.py"
	@echo "  make clean        - remove venv and build artifacts"

# Ensure venv exists
.venv/bin/python:
	python3 -m venv .venv

# Set up venv and install editable package
dev: .venv/bin/python
	$(PIP) install --upgrade pip
	$(PIP) install -e .

# Same but with developer extras (pytest, etc.)
dev-extras: .venv/bin/python
	$(PIP) install --upgrade pip
	$(PIP) install -e '.[dev]'

# Run tests (uses venv python explicitly)
test: .venv/bin/python
	$(PY) -m pytest -q

# Run a single test file: make test-one FILE=dsl/tests/test_intro.py
test-one: .venv/bin/python
	@if [ -z "$(FILE)" ]; then echo "Usage: make test-one FILE=path/to/test.py"; exit 1; fi
	$(PY) -m pytest -q $(FILE)

# Clean build/test artifacts
clean:
	rm -rf .venv
	rm -rf dsl.egg-info dist build
	find . -type d -name "__pycache__" -exec rm -rf {} +
