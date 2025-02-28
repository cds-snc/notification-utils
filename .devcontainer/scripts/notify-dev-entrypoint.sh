#!/bin/bash
set -ex

###################################################################
# This script will get executed *once* the Docker container has
# been built. Commands that need to be executed with all available
# tools and the filesystem mount enabled should be located here.
###################################################################

# Poetry autocomplete
echo -e "fpath+=/.zfunc" >> ~/.zshrc
echo -e "autoload -Uz compinit && compinit"

pip install poetry==${POETRY_VERSION} poetry-plugin-sort \
  && poetry --version


# Disable poetry auto-venv creation
poetry config virtualenvs.create false

# Initialize poetry autocompletions
mkdir ~/.zfunc
touch ~/.zfunc/_poetry
poetry completions zsh > ~/.zfunc/_poetry

# Manually create and activate a virtual environment with a static path
python -m venv "${POETRY_VENV_PATH}"
source "${POETRY_VENV_PATH}/bin/activate"

# Ensure newly created shells activate the poetry venv
echo "source ${POETRY_VENV_PATH}/bin/activate" >> ~/.zshrc

# Install dependencies
poetry install

# Set up git blame to ignore certain revisions e.g. sweeping code formatting changes.
git config blame.ignoreRevsFile .git-blame-ignore-revs

# Install pre-commit hooks
git config --global --add safe.directory /workspaces/notification-utils
poetry run pre-commit install