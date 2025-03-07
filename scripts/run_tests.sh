#!/bin/bash
#
# Run project tests
#
# NOTE: This script expects to be run from the project root with
# ./scripts/run_tests.sh

# Use default environment vars for localhost if not already set

set -o pipefail

function display_result {
  RESULT=$1
  EXIT_STATUS=$2
  TEST=$3

  if [ $RESULT -ne 0 ]; then
    echo -e "\033[31m$TEST failed\033[0m"
    exit $EXIT_STATUS
  else
    echo -e "\033[32m$TEST passed\033[0m"
  fi
}

ruff check .
display_result $? 1 "Code style check"

ruff check --select I .
display_result $? 1 "Import order check"

ruff format --check .
display_result $? 1 "Code format check"

mypy .
display_result $? 1 "Static type check"

## Code coverage
#py.test --cov=client tests/
#display_result $? 2 "Code coverage"

py.test -n4 tests/
display_result $? 3 "Unit tests"

poetry build
