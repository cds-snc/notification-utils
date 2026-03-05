.DEFAULT_GOAL := help
SHELL := /bin/bash
DATE = $(shell date +%Y-%m-%d:%H:%M:%S)

BUILD_TAG ?= notifications-utils-manual
DOCKER_BUILDER_IMAGE_NAME = govuk/notifications-utils-builder
DOCKER_CONTAINER_PREFIX = ${USER}-${BUILD_TAG}

.PHONY: help
help:
	@cat $(MAKEFILE_LIST) | grep -E '^[a-zA-Z_-]+:.*?## .*$$' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: dependencies
dependencies:
	poetry install

.PHONY: build
build: dependencies ## Build project

.PHONY: test
test: ## Run tests
	poetry run ./scripts/run_tests.sh

.PHONY: freeze-requirements
freeze-requirements:
	poetry lock --no-update

.PHONY: prepare-docker-build-image
prepare-docker-build-image: ## Prepare the Docker builder image
	make -C docker build

.PHONY: build-with-docker
build-with-docker: prepare-docker-build-image ## Build inside a Docker container
	@docker run -i --rm \
		--name "${DOCKER_CONTAINER_PREFIX}-build" \
		-v "`pwd`:/var/project" \
		-e http_proxy="${HTTP_PROXY}" \
		-e HTTP_PROXY="${HTTP_PROXY}" \
		-e https_proxy="${HTTPS_PROXY}" \
		-e HTTPS_PROXY="${HTTPS_PROXY}" \
		-e NO_PROXY="${NO_PROXY}" \
		${DOCKER_BUILDER_IMAGE_NAME} \
		make build

.PHONY: test-with-docker
test-with-docker: prepare-docker-build-image ## Run tests inside a Docker container
	@docker run -i --rm \
		--name "${DOCKER_CONTAINER_PREFIX}-test" \
		-v "`pwd`:/var/project" \
		-e http_proxy="${HTTP_PROXY}" \
		-e HTTP_PROXY="${HTTP_PROXY}" \
		-e https_proxy="${HTTPS_PROXY}" \
		-e HTTPS_PROXY="${HTTPS_PROXY}" \
		-e NO_PROXY="${NO_PROXY}" \
		${DOCKER_BUILDER_IMAGE_NAME} \
		make test

.PHONY: clean-docker-containers
clean-docker-containers: ## Clean up any remaining docker containers
	docker rm -f $(shell docker ps -q -f "name=${DOCKER_CONTAINER_PREFIX}") 2> /dev/null || true

.PHONY: format
format:
	ruff check --fix .
	ruff check
	ruff format .
	poetry run mypy .
	poetry sort

clean:
	rm -rf cache venv

.PHONY: update-rates
update-rates: ## Regenerate `notifications_utils/international_billing_rates.yml`. `PRICE_FILE` must be provided.
	@/bin/bash -c 'if [ -z """$(PRICE_FILE)""" ]; then echo "ERROR: PRICE_FILE is required. Example: make update-rates PRICE_FILE=scripts/sms_pricing/aws_prices_sms_mar_2026.csv"; exit 1; fi'
	python3 scripts/sms_pricing/international_billing_rates_updater.py --price-file $(PRICE_FILE)

.PHONY: refresh-dlr-snapshot
refresh-dlr-snapshot: ## Rebuild `scripts/sms_pricing/dlr_snapshot.yml` from current output YAML
	python3 -c 'from scripts.sms_pricing.international_billing_rates_updater import DEFAULT_DLR_SNAPSHOT_PATH, DEFAULT_OUTPUT_PATH, build_dlr_snapshot, write_yaml_file; write_yaml_file(build_dlr_snapshot(DEFAULT_OUTPUT_PATH), DEFAULT_DLR_SNAPSHOT_PATH)'