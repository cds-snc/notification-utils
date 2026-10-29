FROM mcr.microsoft.com/vscode/devcontainers/python:3.12@sha256:79a80515d78783e761af1db255e92767c4e887a2d56dbeb85e7753da8c12dc16

ENV POETRY_VERSION="1.7.1"
ENV POETRY_VENV_PATH="/home/vscode/.venv/workspace"

RUN apt-get update \
    && apt-get -y install --no-install-recommends apt-utils 2>&1 \
    && apt-get -y install \
        curl \
        emacs \
        eza \
        fd-find \
        git \
        iproute2 \
        less \
        libsodium-dev \
        lsb-release \
        man-db \
        manpages \
        net-tools \
        openssh-client \
        procps \
        sudo \
        unzip \
        vim \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

RUN pip install poetry==${POETRY_VERSION} \
  && poetry --version

COPY .devcontainer/scripts/notify-dev-entrypoint.sh /usr/local/bin/
