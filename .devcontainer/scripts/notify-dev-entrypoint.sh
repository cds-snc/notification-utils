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

pip install poetry==${POETRY_VERSION} \
  && poetry --version

# Initialize poetry autocompletions
mkdir ~/.zfunc
touch ~/.zfunc/_poetry
poetry completions zsh > ~/.zfunc/_poetry

# Install dependencies
poetry install
