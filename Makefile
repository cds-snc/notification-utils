.DEFAULT_GOAL := help
SHELL := /bin/bash
DATE = $(shell date +%Y-%m-%d:%H:%M:%S)

BUILD_TAG ?= notifications-utils-manual

.PHONY: help
help:
	@cat $(MAKEFILE_LIST) | grep -E '^[a-zA-Z_-]+:.*?## .*$$' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: dependencies
dependencies: venv ## Install build dependencies
	./venv/bin/pip install -r requirements_for_test.txt

.PHONY: build
build: dependencies ## Build project

.PHONY: test
test: lint-black lint-flake order-check unit-tests

.PHONY: lint-black
lint-black:
	black --check --config pyproject.toml .

.PHONY: lint-flake
lint-flake:
	flake8 .

.PHONY: order-check
order-check:
	mypy .

.PHONY: unit-tests
unit-tests:
	py.test -n4 tests/
